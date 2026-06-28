use std::env;
use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;

fn main() {
    println!("🚀 Aether IDE Launcher starting...");

    // Get directory of the executable
    let current_dir = match env::current_exe() {
        Ok(exe_path) => exe_path.parent().unwrap().to_path_buf(),
        Err(_) => env::current_dir().unwrap(),
    };
    
    // Check if we are running from IDE/bin or IDE/ or workspace root
    let mut ide_dir = current_dir.clone();
    if ide_dir.file_name().map_or(false, |n| n == "bin" || n == "release" || n == "debug") {
        ide_dir.pop();
    }
    
    let vscode_dir = ide_dir.join("vscode");
    if !vscode_dir.exists() {
        eprintln!("[ERROR] vscode directory not found at {:?}", vscode_dir);
        std::process::exit(1);
    }

    println!("📂 vscode directory resolved: {:?}", vscode_dir);

    // Update PATH to include common Node.js path
    if let Ok(path_val) = env::var("PATH") {
        let new_path = format!("{};C:\\Program Files\\nodejs", path_val);
        env::set_var("PATH", new_path);
    }

    // Check for node_modules
    let node_modules_dir = vscode_dir.join("node_modules");
    if !node_modules_dir.exists() {
        println!("[INFO] Installing dependencies via npm (this may take a few minutes)...");
        let status = Command::new("cmd")
            .args(&["/c", "npm install"])
            .current_dir(&vscode_dir)
            .status();
        
        match status {
            Ok(s) if s.success() => println!("[OK] Dependencies installed successfully."),
            _ => {
                eprintln!("[ERROR] Failed to install dependencies.");
                std::process::exit(1);
            }
        }
    }

    // Start watch process in a separate console window on Windows
    println!("[BUILD] Starting Aether IDE build watch loop in a separate window...");
    
    let watch_status = Command::new("cmd")
        .args(&[
            "/c",
            "start",
            "cmd.exe",
            "/k",
            "title Aether IDE Build Watch && npm run watch"
        ])
        .current_dir(&vscode_dir)
        .status();

    if let Err(e) = watch_status {
        eprintln!("[WARNING] Could not spawn watch console automatically: {}", e);
    }

    // Wait for the initial compilation to generate out/main.js
    let main_js = vscode_dir.join("out").join("main.js");
    if !main_js.exists() {
        println!("[INFO] Waiting for the initial compilation to finish and generate out\\main.js...");
        let timeout = 180; // 3 minutes
        let mut elapsed = 0;
        while !main_js.exists() && elapsed < timeout {
            thread::sleep(Duration::from_secs(2));
            elapsed += 2;
            print!(".");
            use std::io::{self, Write};
            let _ = io::stdout().flush();
        }
        println!();
        if !main_js.exists() {
            eprintln!("[ERROR] Compilation timed out. Please check the build watch window for errors.");
            std::process::exit(1);
        }
        println!("[OK] Compilation finished successfully.");
    }

    println!("[RUN] Launching Aether IDE...");
    
    // Run code.bat
    let code_bat = vscode_dir.join("scripts").join("code.bat");
    let status = Command::new("cmd")
        .arg("/c")
        .arg(&code_bat)
        .current_dir(&vscode_dir)
        .status();

    match status {
        Ok(s) if s.success() => println!("[OK] Aether IDE finished running."),
        Ok(s) => eprintln!("[INFO] Aether IDE exited with status: {}", s),
        Err(e) => eprintln!("[ERROR] Failed to run code.bat: {}", e),
    }
}

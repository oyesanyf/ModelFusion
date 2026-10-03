use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    #[cfg(windows)]
    {
        let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
        let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
        let icon_path = manifest_dir.join("../../IDE/hugos.ico");
        let rc_path = out_dir.join("cli_icon.rc");
        let res_path = out_dir.join("cli_icon.res");
        let obj_path = out_dir.join("cli_icon.o");

        let rc_content = format!("1 ICON \"{}\"\n", icon_path.display().to_string().replace('\\', "/"));
        std::fs::write(&rc_path, rc_content).expect("Failed to write rc file");

        let llvm_rc = r"C:\Program Files\LLVM\bin\llvm-rc.exe";
        let windres = r"C:\Users\oyesanyf\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.MSVCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\windres.exe";

        let mut compiled = false;
        if std::path::Path::new(llvm_rc).exists() {
            let status = Command::new(llvm_rc)
                .arg(format!("/fo{}", res_path.display()))
                .arg(&rc_path)
                .status();
            if let Ok(s) = status {
                if s.success() {
                    println!("cargo:rustc-link-arg={}", res_path.display());
                    compiled = true;
                }
            }
        }

        if !compiled && std::path::Path::new(windres).exists() {
            let status = Command::new(windres)
                .arg("-i")
                .arg(&rc_path)
                .arg("-o")
                .arg(&obj_path)
                .status();
            if let Ok(s) = status {
                if s.success() {
                    println!("cargo:rustc-link-arg={}", obj_path.display());
                    compiled = true;
                }
            }
        }

        if !compiled {
            eprintln!("cargo:warning=Failed to compile icon resource into binary");
        } else {
            println!("cargo:rerun-if-changed={}", icon_path.display());
        }
    }
}

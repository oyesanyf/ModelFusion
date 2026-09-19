#!/usr/bin/env python3
"""
HugOS IDE Ollama PATH and Hardware Scaling Patch Script
Ensures Ollama binary is discovered and permanently added to the process and system PATH,
dynamically scales Ollama models based on runtime available/free memory,
and hardens the background incremental model update watcher.
"""

import os
import sys
import re
import shutil
import subprocess

def find_node_executable():
    """Locate node.exe on the system."""
    candidate_paths = [
        r"D:\tools\nodejs\node.exe",
        shutil.which("node"),
        shutil.which("node.exe"),
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ]
    for p in candidate_paths:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None

def validate_js_syntax(file_path, node_path):
    """Run node --check to validate JavaScript syntax."""
    if not node_path or not os.path.isfile(node_path):
        print(f"  [WARN] node.exe not found; skipping syntax validation for {os.path.basename(file_path)}")
        return True
    try:
        res = subprocess.run(
            [node_path, "--check", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if res.returncode != 0:
            print(f"  [SYNTAX ERROR] Validation failed for {file_path}:")
            print(res.stderr[:500])
            return False
        return True
    except Exception as e:
        print(f"  [SYNTAX ERROR] Exception running node --check: {e}")
        return False

def patch_extension_js(ext_js_path, node_path):
    """Patch dist/extension.js with Ollama PATH helper, available RAM scaling, and watcher output."""
    if not os.path.isfile(ext_js_path):
        return False, False

    print(f"\n[PATCH] Processing extension.js: {ext_js_path}")
    with open(ext_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # -------------------------------------------------------------------------
    # 1. Helper: _ensureOllamaInPath(ollamaExePath)
    # -------------------------------------------------------------------------
    ensure_helper_code = '''      _ensureOllamaInPath(ollamaExePath) {
        if (!ollamaExePath || ollamaExePath === "ollama") {
          return;
        }
        try {
          const ollamaDir = path3.dirname(ollamaExePath);
          if (!fs3.existsSync(ollamaDir)) {
            return;
          }
          const currentPath = process.env["PATH"] || "";
          if (!currentPath.toLowerCase().includes(ollamaDir.toLowerCase())) {
            process.env["PATH"] = `${ollamaDir}${path3.delimiter}${currentPath}`;
            this._outputChannel.appendLine(`[OLLAMA] Prepended ${ollamaDir} to runtime process.env.PATH`);
          }
          const envColl = this._context?.environmentVariableCollection || this._extensionContext?.environmentVariableCollection || this.context?.environmentVariableCollection;
          if (envColl) {
            envColl.prepend("PATH", `${ollamaDir}${path3.delimiter}`);
            this._outputChannel.appendLine(`[OLLAMA] Prepended ${ollamaDir} to environmentVariableCollection`);
          }
          if (process.platform === "win32") {
            const escapedDir = ollamaDir.replace(/'/g, "''");
            const psCmd = `powershell -NoProfile -Command "$dir = '${escapedDir}'; $p = [Environment]::GetEnvironmentVariable('Path', 'User'); if (-not $p) { [Environment]::SetEnvironmentVariable('Path', $dir, 'User') } elseif ($p -notlike ('*' + $dir + '*')) { [Environment]::SetEnvironmentVariable('Path', $p.TrimEnd(';') + ';' + $dir, 'User') }"`;
            child_process2.exec(psCmd, (err) => {
              if (!err) {
                this._outputChannel.appendLine(`[OLLAMA] Ensured ${ollamaDir} in User PATH registry.`);
              }
            });
          }
        } catch (e) {
          this._outputChannel.appendLine(`[OLLAMA] Error configuring Ollama in PATH: ${e.message}`);
        }
      }
'''

    if "_ensureOllamaInPath(" not in content:
        target_pos = content.find("      _checkOllamaInstallation() {")
        if target_pos != -1:
            content = content[:target_pos] + ensure_helper_code + content[target_pos:]
            changed = True
            print("  [APPLIED] Added _ensureOllamaInPath() helper method.")
        else:
            print("  [WARN] Could not find _checkOllamaInstallation() insertion point.")
    else:
        print("  [OK] _ensureOllamaInPath() already present.")

    # -------------------------------------------------------------------------
    # 2. Call _ensureOllamaInPath in _checkOllamaInstallation()
    # -------------------------------------------------------------------------
    chk_target = 'if (foundPath) {\n              this._outputChannel.appendLine(`[OLLAMA] Found Ollama at ${foundPath} (not in PATH). Starting...`);'
    chk_replacement = 'if (foundPath) {\n              this._outputChannel.appendLine(`[OLLAMA] Found Ollama at ${foundPath} (not in PATH). Starting...`);\n              this._ensureOllamaInPath(foundPath);'

    if chk_replacement in content or "this._ensureOllamaInPath(foundPath);" in content:
        print("  [OK] _checkOllamaInstallation() already calls _ensureOllamaInPath(foundPath).")
    elif chk_target in content:
        content = content.replace(chk_target, chk_replacement, 1)
        changed = True
        print("  [APPLIED] Hooked _ensureOllamaInPath(foundPath) into _checkOllamaInstallation().")
    else:
        print("  [WARN] Could not match foundPath pattern in _checkOllamaInstallation().")

    # -------------------------------------------------------------------------
    # 3. Call _ensureOllamaInPath in _onOllamaInstalled()
    # -------------------------------------------------------------------------
    inst_target = 'const actualPath = fs3.existsSync(ollamaPath) ? ollamaPath : fallbackPath;\n        this._startOllama(actualPath);'
    inst_replacement = 'const actualPath = fs3.existsSync(ollamaPath) ? ollamaPath : fallbackPath;\n        this._ensureOllamaInPath(actualPath);\n        this._startOllama(actualPath);'

    if inst_replacement in content or "this._ensureOllamaInPath(actualPath);" in content:
        print("  [OK] _onOllamaInstalled() already calls _ensureOllamaInPath(actualPath).")
    elif inst_target in content:
        content = content.replace(inst_target, inst_replacement, 1)
        changed = True
        print("  [APPLIED] Hooked _ensureOllamaInPath(actualPath) into _onOllamaInstalled().")
    else:
        print("  [WARN] Could not match _onOllamaInstalled() actualPath pattern.")

    # -------------------------------------------------------------------------
    # 4. Update _selectModelForSystem() to scale based on available/free memory
    # -------------------------------------------------------------------------
    # Matches the entire method body of _selectModelForSystem
    model_sel_re = re.compile(
        r'_selectModelForSystem\s*\(\)\s*\{[\s\S]*?this\._outputChannel\.appendLine\([^\)]*\);\s*if\s*\([\s\S]*?return\s*\{\s*model:\s*"qwen2\.5:7b"[\s\S]*?\};?\s*\}',
        re.MULTILINE
    )

    new_model_sel = '''_selectModelForSystem() {
        const os16 = require("os");
        const freeRAM_GB = Math.round(os16.freemem() / (1024 * 1024 * 1024));
        const totalRAM_GB = Math.round(os16.totalmem() / (1024 * 1024 * 1024));
        this._outputChannel.appendLine(`[OLLAMA] System Memory: ${freeRAM_GB} GB available / ${totalRAM_GB} GB total`);
        if (freeRAM_GB >= 48) {
          return { model: "qwen2.5:32b", label: `qwen2.5:32b (${freeRAM_GB}GB RAM available \u2014 workstation high performance)` };
        } else if (freeRAM_GB >= 24) {
          return { model: "qwen2.5:14b", label: `qwen2.5:14b (${freeRAM_GB}GB RAM available \u2014 high performance)` };
        } else if (freeRAM_GB >= 12) {
          return { model: "qwen2.5:7b", label: `qwen2.5:7b (${freeRAM_GB}GB RAM available \u2014 recommended)` };
        } else if (freeRAM_GB >= 6) {
          return { model: "qwen2.5:3b", label: `qwen2.5:3b (${freeRAM_GB}GB RAM available \u2014 standard)` };
        } else if (freeRAM_GB >= 3) {
          return { model: "qwen2.5:1.5b", label: `qwen2.5:1.5b (${freeRAM_GB}GB RAM available \u2014 balanced)` };
        } else {
          return { model: "qwen2.5:0.5b", label: `qwen2.5:0.5b (${freeRAM_GB}GB RAM available \u2014 lightweight)` };
        }
      }'''

    if "qwen2.5:32b" in content and "freeRAM_GB" in content:
        print("  [OK] _selectModelForSystem() already scales with runtime available RAM.")
    elif model_sel_re.search(content):
        content = model_sel_re.sub(new_model_sel, content, count=1)
        changed = True
        print("  [APPLIED] Upgraded _selectModelForSystem() to runtime available memory scaling tiers.")
    else:
        print("  [WARN] Could not match _selectModelForSystem() pattern.")

    # -------------------------------------------------------------------------
    # 5. Harden _runDatabaseUpdate() (safe os.setPriority, watcher output forwarding)
    # -------------------------------------------------------------------------
    # Fix os.setPriority -> require("os").setPriority
    if 'os.setPriority(child.pid, 19);' in content:
        content = content.replace('os.setPriority(child.pid, 19);', 'require("os").setPriority(child.pid, 19);')
        changed = True
        print("  [APPLIED] Safe require('os').setPriority in _runDatabaseUpdate().")

    # Output forwarding for watcher stdout
    old_stdout = '''              if (line.trim()) {
                this._logService.info(`ModelFusionProvider [Watcher stdout]: ${line.trim()}`);
              }'''
    new_stdout = '''              if (line.trim()) {
                this._logService.info(`ModelFusionProvider [Watcher stdout]: ${line.trim()}`);
                this._outputChannel.appendLine(`[Watcher] ${line.trim()}`);
              }'''
    if old_stdout in content:
        content = content.replace(old_stdout, new_stdout, 1)
        changed = True
        print("  [APPLIED] Output channel forwarding for watcher stdout.")

    # Output forwarding for watcher stderr
    old_stderr = '''              if (line.trim()) {
                this._logService.warn(`ModelFusionProvider [Watcher stderr]: ${line.trim()}`);
              }'''
    new_stderr = '''              if (line.trim()) {
                this._logService.warn(`ModelFusionProvider [Watcher stderr]: ${line.trim()}`);
                this._outputChannel.appendLine(`[Watcher] ${line.trim()}`);
              }'''
    if old_stderr in content:
        content = content.replace(old_stderr, new_stderr, 1)
        changed = True
        print("  [APPLIED] Output channel forwarding for watcher stderr.")

    # Output forwarding for watcher close
    old_close = '''            if (code === 0) {
              this._logService.info("ModelFusionProvider: Background database update completed successfully.");
            } else {
              this._logService.error(`ModelFusionProvider: Background database update failed with exit code ${code}.`);
            }'''
    new_close = '''            if (code === 0) {
              this._logService.info("ModelFusionProvider: Background database update completed successfully.");
              this._outputChannel.appendLine("[Watcher] Background model & database update completed successfully.");
            } else {
              this._logService.error(`ModelFusionProvider: Background database update failed with exit code ${code}.`);
              this._outputChannel.appendLine(`[Watcher] Background model & database update exited with code ${code}.`);
            }'''
    if old_close in content:
        content = content.replace(old_close, new_close, 1)
        changed = True
        print("  [APPLIED] Completion status logging to output channel on watcher close.")

    if changed:
        with open(ext_js_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  [SUCCESS] Written updated extension.js.")
    else:
        print("  [NO CHANGES] File already up to date.")

    # Validate syntax with node --check
    valid = validate_js_syntax(ext_js_path, node_path)
    if not valid:
        return False, False
    return True, changed

def main():
    print("============================================================")
    print("[HUGOS] Patching extension.js (Ollama PATH & Scaling)")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skip_installed = any(arg.lower() in ("--skip-installed", "--check-installed=false") for arg in sys.argv)
    pack_dir_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pack_dir = (
        os.path.abspath(pack_dir_args[0].strip().strip('\"\''))
        if pack_dir_args
        else os.path.join(script_dir, "VSCode-win32-x64")
    )
    print(f"  Target packaging directory: {pack_dir}")

    node_path = find_node_executable()
    if node_path:
        print(f"  Using Node.js at: {node_path}")
    else:
        print(f"  [WARNING] node.exe not found! Syntax checks will be skipped.")

    targets = [
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "dist", "extension.js"),
    ]

    base_dirs = [pack_dir]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        hugos_installed = os.path.join(local_app_data, "HugOS IDE")
        base_dirs.append(hugos_installed)
        targets.append(os.path.join(hugos_installed, "resources", "app", "extensions", "copilot", "dist", "extension.js"))

    # Scan for versioned runtime directories ([0-9a-f]{7,40})
    for b in base_dirs:
        if b and os.path.isdir(b):
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        v_ext = os.path.join(sub, "resources", "app", "extensions", "copilot", "dist", "extension.js")
                        if v_ext not in targets:
                            targets.append(v_ext)

    seen = set()
    error_count = 0
    modified_count = 0
    for t in targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_extension_js(t, node_path)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    if error_count > 0:
        print(f"\n[ERROR] extension.js patching failed with {error_count} error(s)!")
        sys.exit(1)

    print(f"\n[SUCCESS] extension.js patching complete! ({len(seen)} validated, {modified_count} modified)")
    sys.exit(0)

if __name__ == "__main__":
    main()

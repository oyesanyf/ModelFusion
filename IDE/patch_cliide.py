#!/usr/bin/env python3
"""
Patch copilot dist/extension.js to support cliide.exe with fallback to cli.exe.
"""

import os
import sys
import subprocess

TARGETS = [
    r"IDE/vscode/extensions/copilot/dist/extension.js",
    r"IDE/VSCode-win32-x64/resources/app/extensions/copilot/dist/extension.js",
    r"IDE/VSCode-win32-x64/7e7950df89/resources/app/extensions/copilot/dist/extension.js",
]

def patch_file(fpath):
    if not os.path.isfile(fpath):
        print(f"[SKIP] Not found: {fpath}")
        return

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Update _findCliBinary (first occurrence)
    old_block1 = """_findCliBinary() {
        const relativePath2 = path3.resolve(__dirname, "..", "..", "..", "..", "..", "bin", "cli.exe");
        if (fs3.existsSync(relativePath2)) {
          return relativePath2;
        }
        const hardcodedPath = "D:\\\\harfile\\\\ModelFusion\\\\IDE\\\\bin\\\\cli.exe";
        if (fs3.existsSync(hardcodedPath)) {
          return hardcodedPath;
        }
        let currentDir = __dirname;
        for (let i9 = 0; i9 < 10; i9++) {
          const checkPath = path3.join(currentDir, "IDE", "bin", "cli.exe");
          if (fs3.existsSync(checkPath)) {
            return checkPath;
          }
          const checkPath2 = path3.join(currentDir, "bin", "cli.exe");
          if (fs3.existsSync(checkPath2)) {
            return checkPath2;
          }
          const parentDir = path3.dirname(currentDir);
          if (parentDir === currentDir) {
            break;
          }
          currentDir = parentDir;
        }
        return "cli.exe";
      }"""

    new_block1 = """_findCliBinary() {
        for (const bName of ["cliide.exe", "cli.exe"]) {
          const relativePath2 = path3.resolve(__dirname, "..", "..", "..", "..", "..", "bin", bName);
          if (fs3.existsSync(relativePath2)) {
            return relativePath2;
          }
          const hardcodedPath = `D:\\\\harfile\\\\ModelFusion\\\\IDE\\\\bin\\\\${bName}`;
          if (fs3.existsSync(hardcodedPath)) {
            return hardcodedPath;
          }
          let currentDir = __dirname;
          for (let i9 = 0; i9 < 10; i9++) {
            const checkPath = path3.join(currentDir, "IDE", "bin", bName);
            if (fs3.existsSync(checkPath)) {
              return checkPath;
            }
            const checkPath2 = path3.join(currentDir, "bin", bName);
            if (fs3.existsSync(checkPath2)) {
              return checkPath2;
            }
            const parentDir = path3.dirname(currentDir);
            if (parentDir === currentDir) {
              break;
            }
            currentDir = parentDir;
          }
        }
        return "cliide.exe";
      }"""

    if old_block1 in content:
        content = content.replace(old_block1, new_block1)
        print(f"[PATCHED] _findCliBinary (1) in {fpath}")
    else:
        print(f"[INFO] _findCliBinary (1) already patched or not matched in {fpath}")

    # 2. Update _findCliBinary (second occurrence / factory)
    old_block2 = """_findCliBinary() {
    const relativePath2 = path15.resolve(__dirname, "..", "..", "..", "..", "..", "bin", "cli.exe");
    if (fs19.existsSync(relativePath2)) {
      return relativePath2;
    }
    const hardcodedPath = "D:\\\\harfile\\\\ModelFusion\\\\IDE\\\\bin\\\\cli.exe";
    if (fs19.existsSync(hardcodedPath)) {
      return hardcodedPath;
    }
    let currentDir = __dirname;
    for (let i9 = 0; i9 < 10; i9++) {
      const checkPath = path15.join(currentDir, "IDE", "bin", "cli.exe");
      if (fs19.existsSync(checkPath)) {
        return checkPath;
      }
      const checkPath2 = path15.join(currentDir, "bin", "cli.exe");
      if (fs19.existsSync(checkPath2)) {
        return checkPath2;
      }
      const parentDir = path15.dirname(currentDir);
      if (parentDir === currentDir) {
        break;
      }
      currentDir = parentDir;
    }
    return "cli.exe";
  }"""

    new_block2 = """_findCliBinary() {
    for (const bName of ["cliide.exe", "cli.exe"]) {
      const relativePath2 = path15.resolve(__dirname, "..", "..", "..", "..", "..", "bin", bName);
      if (fs19.existsSync(relativePath2)) {
        return relativePath2;
      }
      const hardcodedPath = `D:\\\\harfile\\\\ModelFusion\\\\IDE\\\\bin\\\\${bName}`;
      if (fs19.existsSync(hardcodedPath)) {
        return hardcodedPath;
      }
      let currentDir = __dirname;
      for (let i9 = 0; i9 < 10; i9++) {
        const checkPath = path15.join(currentDir, "IDE", "bin", bName);
        if (fs19.existsSync(checkPath)) {
          return checkPath;
        }
        const checkPath2 = path15.join(currentDir, "bin", bName);
        if (fs19.existsSync(checkPath2)) {
          return checkPath2;
        }
        const parentDir = path15.dirname(currentDir);
        if (parentDir === currentDir) {
          break;
        }
        currentDir = parentDir;
      }
    }
    return "cliide.exe";
  }"""

    if old_block2 in content:
        content = content.replace(old_block2, new_block2)
        print(f"[PATCHED] _findCliBinary (2) in {fpath}")
    else:
        print(f"[INFO] _findCliBinary (2) already patched or not matched in {fpath}")

    # 3. Update Find-RealCopilot powershell script
    old_ps = """    # Check if we have our IDE's own cli.exe first (highest priority)
    $LocalCli = Join-Path $env:LOCALAPPDATA "HugOS IDE\\\\bin\\\\cli.exe"
    if (Test-Path $LocalCli) {
        return $LocalCli
    }"""

    new_ps = """    # Check if we have our IDE's own cliide.exe or cli.exe first (highest priority)
    $LocalCli = Join-Path $env:LOCALAPPDATA "HugOS IDE\\\\bin\\\\cliide.exe"
    if (-not (Test-Path $LocalCli)) {
        $LocalCli = Join-Path $env:LOCALAPPDATA "HugOS IDE\\\\bin\\\\cli.exe"
    }
    if (Test-Path $LocalCli) {
        return $LocalCli
    }"""

    if old_ps in content:
        content = content.replace(old_ps, new_ps)
        print(f"[PATCHED] Find-RealCopilot in {fpath}")
    else:
        print(f"[INFO] Find-RealCopilot already patched or not matched in {fpath}")

    if content != original:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[SAVED] {fpath}")

        # Syntax check
        node_exe = r"D:\tools\nodejs\node.exe"
        if not os.path.isfile(node_exe):
            node_exe = "node"
        res = subprocess.run([node_exe, "--check", fpath], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SYNTAX OK] {fpath}")
        else:
            print(f"[SYNTAX ERROR] {fpath}:\n{res.stderr}")
            sys.exit(1)

def main():
    repo_root = r"D:\harfile\ModelFusion"
    for rel in TARGETS:
        patch_file(os.path.join(repo_root, rel))

if __name__ == "__main__":
    main()

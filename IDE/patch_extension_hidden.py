import os, sys, re

def patch_file(file_path):
    if not os.path.isfile(file_path):
        print(f"Skipping non-existent: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Match 1: ollama list
    content = content.replace(
        'child_process.execSync("ollama list", { encoding: "utf-8", timeout: 1e4 })',
        'child_process.execSync("ollama list", { encoding: "utf-8", timeout: 1e4, windowsHide: true })'
    )

    # 2. Match 2: _serverProcess cliPath spawn
    content = re.sub(
        r'child_process2\.spawn\(cliPath,\s*serverArgs,\s*\{\s*cwd:\s*spawnCwd,\s*// Use pipe so we can forward stdout/stderr to the output channel\.\s*stdio:\s*"pipe",\s*env:\s*spawnEnv\s*\}\)',
        'child_process2.spawn(cliPath, serverArgs, { cwd: spawnCwd, stdio: "pipe", env: spawnEnv, windowsHide: true })',
        content
    )
    # Also handle alternate formatting without comment
    content = re.sub(
        r'child_process2\.spawn\(cliPath,\s*serverArgs,\s*\{\s*cwd:\s*spawnCwd,\s*stdio:\s*"pipe",\s*env:\s*spawnEnv\s*\}\)',
        'child_process2.spawn(cliPath, serverArgs, { cwd: spawnCwd, stdio: "pipe", env: spawnEnv, windowsHide: true })',
        content
    )

    # 3. Match 3: cliPath args2 spawn
    content = re.sub(
        r'child_process2\.spawn\(cliPath,\s*args2,\s*\{\s*cwd:\s*spawnCwd\s*\}\)',
        'child_process2.spawn(cliPath, args2, { cwd: spawnCwd, windowsHide: true })',
        content
    )

    # 4. Match 4: openevolve spawnSync
    content = re.sub(
        r'child_process2\.spawnSync\("python",\s*\["-c",\s*"import openevolve"\],\s*\{\s*timeout:\s*2e3,\s*shell:\s*process\.platform\s*===\s*"win32",\s*stdio:\s*"ignore"\s*\}\)',
        'child_process2.spawnSync("python", ["-c", "import openevolve"], { timeout: 2e3, shell: process.platform === "win32", stdio: "ignore", windowsHide: true })',
        content
    )

    # 5. Match 5: openEvolveDir spawn
    content = re.sub(
        r'child_process2\.spawn\(cmd,\s*args2,\s*\{\s*cwd:\s*openEvolveDir,\s*env:\s*\{\s*\.\.\.process\.env,\s*PYTHONIOENCODING:\s*"utf-8",\s*PYTHONUTF8:\s*"1"\s*\},\s*shell:\s*true\s*\}\)',
        'child_process2.spawn(cmd, args2, { cwd: openEvolveDir, env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" }, shell: true, windowsHide: true })',
        content
    )

    # 6. Match 6: avoDir spawn
    content = re.sub(
        r'child_process2\.spawn\(cmd,\s*args2,\s*\{\s*env:\s*env36,\s*cwd:\s*avoDir,\s*shell:\s*true\s*\}\)',
        'child_process2.spawn(cmd, args2, { env: env36, cwd: avoDir, shell: true, windowsHide: true })',
        content
    )

    # 7. Match 7: cliPath args2 spawn with spawnEnv
    content = re.sub(
        r'child_process2\.spawn\(cliPath,\s*args2,\s*\{\s*cwd:\s*spawnCwd,\s*env:\s*spawnEnv\s*\}\)',
        'child_process2.spawn(cliPath, args2, { cwd: spawnCwd, env: spawnEnv, windowsHide: true })',
        content
    )

    # 8. Match 8: psCmd exec
    content = re.sub(
        r'child_process2\.exec\(psCmd,\s*\(err\)\s*=>',
        'child_process2.exec(psCmd, { windowsHide: true }, (err) =>',
        content
    )

    # 9. Match 9: where ollama exec
    content = re.sub(
        r'child_process2\.exec\(cmd,\s*\(err2\)\s*=>',
        'child_process2.exec(cmd, { windowsHide: true }, (err2) =>',
        content
    )

    # 10. Match 11: nvidia-smi execSync
    content = re.sub(
        r'child_process2\.execSync\("nvidia-smi",\s*\{\s*stdio:\s*"ignore",\s*timeout:\s*2e3\s*\}\)',
        'child_process2.execSync("nvidia-smi", { stdio: "ignore", timeout: 2e3, windowsHide: true })',
        content
    )

    # 11. Match 12: wmic execSync
    content = re.sub(
        r'child_process2\.execSync\("wmic path win32_videocard get name",\s*\{\s*encoding:\s*"utf8",\s*timeout:\s*2e3\s*\}\)',
        'child_process2.execSync("wmic path win32_videocard get name", { encoding: "utf8", timeout: 2e3, windowsHide: true })',
        content
    )

    # 12. Match 13: ollamaPath pull exec
    content = re.sub(
        r'child_process2\.exec\(`"\$\{ollamaPath\}" pull \$\{model\}`, \{ timeout: 6e5 \},',
        'child_process2.exec(`"${ollamaPath}" pull ${model}`, { timeout: 6e5, windowsHide: true },',
        content
    )

    # 13. Match 14: installerPath /SILENT exec
    content = re.sub(
        r'child_process2\.exec\(`"\$\{installerPath\}" /SILENT /NORESTART`, \{ timeout: 3e5 \},',
        'child_process2.exec(`"${installerPath}" /SILENT /NORESTART`, { timeout: 3e5, windowsHide: true },',
        content
    )

    # 14. Match 15: installerPath /VERYSILENT exec
    content = re.sub(
        r'child_process2\.exec\(`"\$\{installerPath\}" /VERYSILENT /NORESTART`, \{ timeout: 3e5 \},',
        'child_process2.exec(`"${installerPath}" /VERYSILENT /NORESTART`, { timeout: 3e5, windowsHide: true },',
        content
    )

    # 15. Match 16: installerPath exec
    content = re.sub(
        r'child_process2\.exec\(`"\$\{installerPath\}"`, \{ timeout: 6e5 \}\);',
        'child_process2.exec(`"${installerPath}"`, { timeout: 6e5, windowsHide: true });',
        content
    )

    # 16. Match 17: cliPath --sys-info execSync
    content = re.sub(
        r'child_process2\.execSync\(`"\$\{cliPath\}" --sys-info`, \{ encoding: "utf8", timeout: 5e3 \}\)',
        'child_process2.execSync(`"${cliPath}" --sys-info`, { encoding: "utf8", timeout: 5e3, windowsHide: true })',
        content
    )

    # 17. Match 18: reg query DriverDesc execSync
    content = re.sub(
        r'child_process2\.execSync\(\'reg query "HKLM\\\\SYSTEM\\\\CurrentControlSet\\\\Control\\\\Class\\\\\{4d36e968-e325-11ce-bfc1-08002be10318\}" /s /v DriverDesc\', \{ encoding: "utf8", timeout: 2e3 \}\)',
        'child_process2.execSync(\'reg query "HKLM\\\\SYSTEM\\\\CurrentControlSet\\\\Control\\\\Class\\\\{4d36e968-e325-11ce-bfc1-08002be10318}" /s /v DriverDesc\', { encoding: "utf8", timeout: 2e3, windowsHide: true })',
        content
    )

    # 18. Match 22: POWERSHELL_PATH spawn
    content = re.sub(
        r'child_process4\.spawn\(FileAccessControl2\.POWERSHELL_PATH,\s*\["-Command",\s*"\[System\.Security\.Principal\.WindowsIdentity\]::GetCurrent\(\)\.Name"\],\s*\{\s*\}\)',
        'child_process4.spawn(FileAccessControl2.POWERSHELL_PATH, ["-Command", "[System.Security.Principal.WindowsIdentity]::GetCurrent().Name"], { windowsHide: true })',
        content
    )

    # 19. Match 23: POWERSHELL_PATH spawnSync
    content = re.sub(
        r'child_process4\.spawnSync\(FileAccessControl2\.POWERSHELL_PATH,\s*\["-Command",\s*"\[System\.Security\.Principal\.WindowsIdentity\]::GetCurrent\(\)\.Name"\],\s*\{\s*\}\)',
        'child_process4.spawnSync(FileAccessControl2.POWERSHELL_PATH, ["-Command", "[System.Security.Principal.WindowsIdentity]::GetCurrent().Name"], { windowsHide: true })',
        content
    )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Patched unhidden child_process calls in {file_path}")
        return True
    else:
        print(f"[NO CHANGES] {file_path}")
        return False

if __name__ == "__main__":
    targets = [
        "IDE/vscode/extensions/copilot/dist/extension.js",
        "IDE/VSCode-win32-x64/resources/app/extensions/copilot/dist/extension.js",
        "IDE/VSCode-win32-x64/7e7950df89/resources/app/extensions/copilot/dist/extension.js"
    ]
    for t in targets:
        patch_file(t)

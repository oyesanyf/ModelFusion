import os
import shutil
import hashlib
import re

import subprocess
import glob

src = os.path.abspath("target/release/cli.exe")

def ensure_signed(exe_path):
    if not os.path.exists(exe_path):
        return
    try:
        check = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"(Get-AuthenticodeSignature '{exe_path}').Status.ToString()"],
            capture_output=True, text=True, timeout=10
        )
        if "Valid" in check.stdout:
            print(f"[SIGN] {exe_path} is already signed with a valid signature.")
            return
    except Exception:
        pass

    pfx = os.path.abspath("IDE/hugos-signing-cert.pfx")
    if not os.path.exists(pfx):
        print(f"[SIGN WARN] Certificate {pfx} not found, skipping signing.")
        return

    signtool_candidates = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe"
    ]
    signtool = next((s for s in signtool_candidates if os.path.isfile(s)), None)
    if not signtool:
        kits = glob.glob(r"C:\Program Files (x86)\Windows Kits\10\**\signtool.exe", recursive=True)
        signtool = next((s for s in kits if "x64" in s), kits[0] if kits else None)

    if signtool:
        print(f"[SIGN] Signing {exe_path} with {signtool}...")
        res = subprocess.run([
            signtool, "sign",
            "/f", pfx,
            "/p", "HugOSPassword123!",
            "/fd", "SHA256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            exe_path
        ], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SIGN OK] Successfully signed {exe_path}")
            return
        # Retry without timestamp if offline/blocked
        res = subprocess.run([
            signtool, "sign",
            "/f", pfx,
            "/p", "HugOSPassword123!",
            "/fd", "SHA256",
            exe_path
        ], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SIGN OK] Successfully signed (without timestamp) {exe_path}")
            return
        print(f"[SIGN WARN] signtool failed: {res.stderr}")

ensure_signed(src)

def get_sha256(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None

src_hash = get_sha256(src)
print(f"Authoritative Source Hash: {src_hash}")

localappdata = os.environ.get("LOCALAPPDATA", r"C:\Users\oyesanyf\AppData\Local")

destinations = [
    os.path.abspath(r"target\release\clibrowser.exe"),
    os.path.abspath(r"IDE\bin\cli.exe"),
    os.path.abspath(r"IDE\bin\cliide.exe"),
    os.path.abspath(r"IDE\VSCode-win32-x64\bin\cli.exe"),
    os.path.abspath(r"IDE\VSCode-win32-x64\bin\cliide.exe"),
    os.path.abspath(r"browser\bin\cli.exe"),
    os.path.abspath(r"browser\bin\clibrowser.exe"),
    os.path.join(localappdata, r"HugOS IDE\bin\cli.exe"),
    os.path.join(localappdata, r"HugOS IDE\bin\cliide.exe"),
    os.path.join(localappdata, r"HugOS Browser\bin\cli.exe"),
    os.path.join(localappdata, r"HugOS Browser\bin\clibrowser.exe"),
    os.path.abspath(r"browser\dist\win-unpacked\resources\bin\cli.exe"),
    os.path.abspath(r"browser\dist\win-unpacked\resources\bin\clibrowser.exe"),
    os.path.abspath(r"target\release\climcp.exe"),
    os.path.abspath(r"mcp\bin\climcp.exe"),
    os.path.abspath(r"mcp\bin\cli.exe"),
    os.path.join(localappdata, r"HugOS MCP\bin\climcp.exe"),
    os.path.join(localappdata, r"HugOS MCP\bin\cli.exe"),
    os.path.join(localappdata, r"Programs\ModelFusion\cli.exe"),
]

for dst in destinations:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and get_sha256(dst) == src_hash:
        print(f"[MATCH (Already in Parity)] {dst}")
        continue
    try:
        shutil.copy2(src, dst)
        match = (get_sha256(dst) == src_hash)
        print(f"[{'MATCH' if match else 'FAIL'}] {dst}")
    except (PermissionError, OSError) as e:
        if os.path.exists(dst) and get_sha256(dst) == src_hash:
            print(f"[MATCH (File in use, hash matched)] {dst}")
        else:
            try:
                old_path = dst + ".old"
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
                os.replace(dst, old_path)
                shutil.copy2(src, dst)
                match = (get_sha256(dst) == src_hash)
                print(f"[{'MATCH (Replaced via NTFS rename)' if match else 'FAIL'}] {dst}")
            except Exception as rename_err:
                print(f"[WARN: Locked by running process] {dst} ({rename_err})")

# Mirror browser UI files across all targets (IDE, Browser, and packaged distributions)
ui_destinations = [
    os.path.join(localappdata, r"HugOS Browser\ui"),
    os.path.join(localappdata, r"HugOS IDE\ui"),
    os.path.join(localappdata, r"HugOS IDE\browser\ui"),
    os.path.abspath(r"IDE\VSCode-win32-x64\ui"),
    os.path.abspath(r"IDE\VSCode-win32-x64\browser\ui"),
]
ui_files = ["app.js", "index.html", "styles.css", "favicon.svg", "favicon.ico", "favicon-32x32.png", "favicon-16x16.png", "icon-48.png", "icon-64.png", "icon-128.png", "icon-192.png", "icon-256.png", "icon-512.png", "hugos_browser.ico", "manifest.webmanifest", "sw.js"]

for target_ui_dir in ui_destinations:
    os.makedirs(target_ui_dir, exist_ok=True)
    for f in ui_files:
        src_ui = os.path.join(os.path.abspath("browser/ui"), f)
        dst_ui = os.path.join(target_ui_dir, f)
        if os.path.exists(src_ui):
            try:
                is_ide_target = ("IDE" in target_ui_dir or "VSCode" in target_ui_dir)
                if f == "index.html" and is_ide_target:
                    with open(src_ui, "r", encoding="utf-8") as fin:
                        html_content = fin.read()
                    # Remove tool_apply_jobs from IDE's index.html
                    html_content = re.sub(
                        r'<button[^>]*data-tool-id="tool_apply_jobs"[^>]*>[\s\S]*?</button>\s*',
                        '',
                        html_content
                    )
                    with open(dst_ui, "w", encoding="utf-8") as fout:
                        fout.write(html_content)
                    print(f"[MIRRORED IDE UI (Stripped tool_apply_jobs)] {dst_ui}")
                    continue
                if os.path.exists(dst_ui) and get_sha256(dst_ui) == get_sha256(src_ui):
                    print(f"[MATCH UI (Already in Parity)] {dst_ui}")
                    continue
                shutil.copy2(src_ui, dst_ui)
                print(f"[COPIED UI] {src_ui} -> {dst_ui}")
            except Exception as e:
                if os.path.exists(dst_ui):
                    try:
                        if get_sha256(dst_ui) == get_sha256(src_ui):
                            print(f"[MATCH UI (File in use, hash matched)] {dst_ui}")
                            continue
                    except Exception:
                        pass
                print(f"[ERROR COPYING UI] {src_ui} -> {dst_ui}: {e}")

# Mirror launcher scripts & browser icon
launcher_dst = os.path.join(localappdata, r"HugOS Browser\Chromium-win32-x64")
if os.path.exists(launcher_dst):
    for f in ["hugos-browser.bat", "hugos-browser.vbs", "hugos-splash.hta", "run_hidden.vbs", "hugos_browser.ico"]:
        src_l = os.path.join(os.path.abspath("browser/Chromium-win32-x64"), f)
        if not os.path.exists(src_l) and f == "hugos_browser.ico":
            src_l = os.path.join(os.path.abspath("browser/ui"), f)
        dst_l = os.path.join(launcher_dst, f)
        if os.path.exists(src_l):
            try:
                shutil.copy2(src_l, dst_l)
                print(f"[COPIED LAUNCHER] {src_l} -> {dst_l}")
            except Exception as e:
                print(f"[ERROR COPYING LAUNCHER] {src_l} -> {dst_l}: {e}")

# Mirror extension files
ext_dst = os.path.join(localappdata, r"HugOS Browser\extension")
if os.path.exists(ext_dst):
    for f in ["background.js", "content.js", "manifest.json", "sidepanel.html", "sidepanel.js", "styles.css"]:
        src_e = os.path.join(os.path.abspath("browser/extension"), f)
        dst_e = os.path.join(ext_dst, f)
        if os.path.exists(src_e):
            try:
                shutil.copy2(src_e, dst_e)
                print(f"[COPIED EXTENSION] {src_e} -> {dst_e}")
            except Exception as e:
                print(f"[ERROR COPYING EXTENSION] {src_e} -> {dst_e}: {e}")

# Mirror copilot extension files
copilot_src_dir = os.path.abspath("IDE/vscode/extensions/copilot")
copilot_dests = [
    os.path.abspath(r"IDE\VSCode-win32-x64\resources\app\extensions\copilot"),
    os.path.abspath(r"IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot"),
    os.path.join(localappdata, r"HugOS IDE\resources\app\extensions\copilot"),
    os.path.join(localappdata, r"HugOS IDE\7e7950df89\resources\app\extensions\copilot"),
]
copilot_files = [
    "package.json",
    os.path.join("dist", "extension.js"),
]

for c_dst in copilot_dests:
    for cf in copilot_files:
        src_cf = os.path.join(copilot_src_dir, cf)
        dst_cf = os.path.join(c_dst, cf)
        if os.path.exists(src_cf):
            try:
                os.makedirs(os.path.dirname(dst_cf), exist_ok=True)
                if os.path.exists(dst_cf) and get_sha256(dst_cf) == get_sha256(src_cf):
                    print(f"[MATCH COPILOT EXTENSION] {dst_cf}")
                    continue
                shutil.copy2(src_cf, dst_cf)
                print(f"[COPIED COPILOT EXTENSION] {src_cf} -> {dst_cf}")
            except Exception as e:
                print(f"[ERROR COPYING COPILOT EXTENSION] {src_cf} -> {dst_cf}: {e}")





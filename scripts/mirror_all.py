import os
import shutil
import hashlib

src = os.path.abspath("target/release/cli.exe")

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
            print(f"[WARN: Locked by running process] {dst} ({e})")

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
    for f in ["hugos-browser.bat", "hugos-browser.vbs", "run_hidden.vbs", "hugos_browser.ico"]:
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



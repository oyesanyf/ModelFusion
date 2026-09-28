import os
import shutil
import hashlib

src = os.path.abspath("target/release/cli.exe")

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

src_hash = get_sha256(src)
print(f"Authoritative Source Hash: {src_hash}")

localappdata = os.environ.get("LOCALAPPDATA", r"C:\Users\oyesanyf\AppData\Local")

destinations = [
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
    except PermissionError:
        if os.path.exists(dst) and get_sha256(dst) == src_hash:
            print(f"[MATCH (File in use, hash matched)] {dst}")
        else:
            print(f"[WARN: Locked by running process] {dst}")

# Mirror browser UI files
ui_dst = os.path.join(localappdata, r"HugOS Browser\ui")
if os.path.exists(ui_dst):
    for f in ["app.js", "index.html", "styles.css"]:
        src_ui = os.path.join(os.path.abspath("browser/ui"), f)
        dst_ui = os.path.join(ui_dst, f)
        try:
            shutil.copy2(src_ui, dst_ui)
            print(f"[COPIED UI] {src_ui} -> {dst_ui}")
        except Exception as e:
            print(f"[ERROR COPYING UI] {src_ui} -> {dst_ui}: {e}")


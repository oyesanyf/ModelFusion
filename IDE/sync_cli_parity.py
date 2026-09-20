#!/usr/bin/env python3
import os
import shutil
import hashlib

src = os.path.abspath(r"d:\harfile\ModelFusion\target\release\cli.exe")
if not os.path.isfile(src):
    print(f"Source not found: {src}")
    exit(1)

localapp = os.environ.get("LOCALAPPDATA", r"C:\Users\oyesanyf\AppData\Local")
targets = [
    os.path.abspath(r"d:\harfile\ModelFusion\IDE\bin\cli.exe"),
    os.path.abspath(r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\bin\cli.exe"),
    os.path.join(localapp, r"HugOS IDE\bin\cli.exe"),
]

for t in targets:
    os.makedirs(os.path.dirname(t), exist_ok=True)
    print(f"Copying to {t}...")
    try:
        shutil.copy2(src, t)
    except (PermissionError, OSError):
        # On Windows, locked binaries can be renamed then replaced
        old_path = t + ".old"
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        try:
            os.rename(t, old_path)
            shutil.copy2(src, t)
            print(f"  (Replaced locked binary via rename: {t})")
        except Exception as e:
            print(f"  [ERROR] Failed copying to {t}: {e}")
            raise

all_paths = [src] + targets
hashes = {}
sizes = {}

for p in all_paths:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            chunk = f.read(1024*1024*4)
            if not chunk:
                break
            h.update(chunk)
    digest = h.hexdigest().upper()
    size = os.path.getsize(p)
    hashes[p] = digest
    sizes[p] = size
    print(f"{p} -> Size: {size} bytes, SHA256: {digest}")

unique_hashes = set(hashes.values())
if len(unique_hashes) == 1:
    print("\n[SUCCESS] 4-way cryptographic binary parity verified 100% identical!")
else:
    print("\n[ERROR] Hash mismatch across targets!")
    exit(1)

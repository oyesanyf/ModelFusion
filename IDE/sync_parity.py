#!/usr/bin/env python3
import os
import sys
import shutil
import hashlib

def sha256(path):
    if not os.path.isfile(path):
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, "target", "release", "cli.exe")
    if not os.path.isfile(src):
        print(f"Error: source cli.exe not found at {src}")
        sys.exit(1)

    targets = [
        os.path.join(root, "IDE", "bin", "cli.exe"),
        os.path.join(root, "IDE", "VSCode-win32-x64", "bin", "cli.exe"),
    ]

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        inst_dir = os.path.join(local_app_data, "HugOS IDE", "bin")
        if os.path.isdir(inst_dir):
            targets.append(os.path.join(inst_dir, "cli.exe"))

    src_hash = sha256(src)
    print(f"Authoritative ({src}):\n  SHA256: {src_hash}\n  Size: {os.path.getsize(src)} bytes\n")

    for dst in targets:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        dst_hash = sha256(dst)
        match = "MATCH" if dst_hash == src_hash else "MISMATCH"
        print(f"[{match}] {dst}\n  SHA256: {dst_hash}")

    print("\nParity verification complete.")

if __name__ == "__main__":
    main()

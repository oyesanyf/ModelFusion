#!/usr/bin/env python3
"""
clean_untrusted_signatures.py

Strips self-signed 'CN=HugOS IDE' Authenticode signatures from official VS Code
native node modules (.node), DLLs, and third-party executables inside the IDE packaging
directory (excluding ModelFusion's own binaries in bin/).

Signing official VS Code native modules with an untrusted self-signed certificate causes
Windows Defender and Smart App Control to detect an untrusted publisher inside
Microsoft-signed HugOS.exe (Code.exe) and block components like keymapping.node.
"""

import os
import sys
import ctypes

def clean_file_signature(filepath: str, imagehlp, kernel32) -> bool:
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return False

    if b"HugOS IDE" not in data:
        return False

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 1
    OPEN_EXISTING = 3

    h_file = kernel32.CreateFileW(filepath, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, None, OPEN_EXISTING, 0, None)
    if h_file == -1 or h_file == 0xFFFFFFFFFFFFFFFF:
        err = kernel32.GetLastError()
        print(f"[WARN] Failed to open {filepath} for signature removal: error {err}")
        return False

    try:
        res = imagehlp.ImageRemoveCertificate(h_file, 0)
        return bool(res)
    finally:
        kernel32.CloseHandle(h_file)

def clean_directory(root_dir: str):
    if not os.path.isdir(root_dir):
        print(f"[ERROR] Directory does not exist: {root_dir}")
        return

    if sys.platform != "win32":
        print("[INFO] Not running on Windows; skipping signature cleaning.")
        return

    imagehlp = ctypes.windll.imagehlp
    kernel32 = ctypes.windll.kernel32

    cleaned_count = 0
    scanned_count = 0

    print(f"[INFO] Scanning {root_dir} for files incorrectly signed with CN=HugOS IDE...")

    for root, dirs, files in os.walk(root_dir):
        # Skip ModelFusion's own binaries in bin/
        rel = os.path.relpath(root, root_dir).lower()
        if rel == "bin" or rel.startswith("bin" + os.sep):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in (".node", ".dll", ".exe"):
                scanned_count += 1
                full_path = os.path.join(root, file)
                if clean_file_signature(full_path, imagehlp, kernel32):
                    cleaned_count += 1
                    print(f"  [CLEANED] Stripped untrusted signature: {os.path.relpath(full_path, root_dir)}")

    print(f"[OK] Cleaned {cleaned_count} files (scanned {scanned_count} candidate binaries).")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "VSCode-win32-x64")
    clean_directory(os.path.abspath(target))

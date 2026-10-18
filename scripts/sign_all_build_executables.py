#!/usr/bin/env python3
import os
import glob
import subprocess
import time

REPO_ROOT = r"D:\harfile\ModelFusion"
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
SIGNTOOL_EXE = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

def sign_file(file_path):
    try:
        res = subprocess.run([
            SIGNTOOL_EXE, "sign",
            "/f", PFX_PATH,
            "/p", "HugOSPassword123!",
            "/fd", "SHA256",
            file_path
        ], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def sign_all_in_dir(directory):
    count = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".exe"):
                full_path = os.path.join(root, f)
                if sign_file(full_path):
                    count += 1
    return count

if __name__ == "__main__":
    target_build = os.path.join(REPO_ROOT, "target", "release", "build")
    if os.path.exists(target_build):
        print(f"Signing existing binaries in {target_build}...")
        signed = sign_all_in_dir(target_build)
        print(f"Successfully signed {signed} executables.")

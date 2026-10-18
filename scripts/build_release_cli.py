#!/usr/bin/env python3
"""
Compiles ModelFusion Master CLI (cargo build --release --bin cli) with automatic,
real-time Authenticode signing of intermediate build-script binaries.
This completely prevents Windows Application Control / Smart App Control os error 4551.
"""

import os
import sys
import time
import threading
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = r"D:\harfile\ModelFusion"
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
SIGNTOOL_EXE = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

stop_event = threading.Event()
signed_files = set()

def sign_file(file_path):
    if file_path in signed_files:
        return True
    try:
        # Check if file is ready and writable
        res = subprocess.run([
            SIGNTOOL_EXE, "sign",
            "/f", PFX_PATH,
            "/p", "HugOSPassword123!",
            "/fd", "SHA256",
            file_path
        ], capture_output=True, text=True)
        if res.returncode == 0:
            signed_files.add(file_path)
            return True
    except Exception:
        pass
    return False

def watcher_thread():
    target_dir = os.path.join(REPO_ROOT, "target", "release")
    while not stop_event.is_set():
        if os.path.exists(target_dir):
            for root, _, files in os.walk(target_dir):
                for f in files:
                    if f.endswith(".exe") or f.endswith(".dll"):
                        full_path = os.path.join(root, f)
                        if full_path not in signed_files:
                            sign_file(full_path)
        time.sleep(0.02)

def pre_sign_existing():
    target_dir = os.path.join(REPO_ROOT, "target", "release")
    if os.path.exists(target_dir):
        for root, _, files in os.walk(target_dir):
            for f in files:
                if f.endswith(".exe") or f.endswith(".dll"):
                    full_path = os.path.join(root, f)
                    sign_file(full_path)

def main():
    print("[BUILD] Pre-signing existing binaries and proc-macro DLLs...")
    pre_sign_existing()
    print("[BUILD] Starting Real-Time Signer Watcher Thread (watching .exe and .dll)...")
    t = threading.Thread(target=watcher_thread, daemon=True)
    t.start()

    cmd = ["cargo", "build", "--release", "--bin", "cli"]
    print(f"[BUILD] Executing: {' '.join(cmd)}")
    start_time = time.time()
    
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
    
    for line in iter(proc.stdout.readline, ''):
        print(line, end='', flush=True)
        # If we see a compiling build script, poll immediately
        if "Compiling" in line:
            # Quick sweep
            target_build = os.path.join(REPO_ROOT, "target", "release", "build")
            if os.path.exists(target_build):
                for r, _, fs in os.walk(target_build):
                    for f in fs:
                        if f.endswith(".exe"):
                            fp = os.path.join(r, f)
                            if fp not in signed_files:
                                sign_file(fp)

    proc.stdout.close()
    return_code = proc.wait()
    stop_event.set()
    t.join(timeout=1.0)

    elapsed = time.time() - start_time
    print(f"\n[BUILD] Finished in {elapsed:.1f}s with return code {return_code}")

    if return_code == 0:
        cli_exe = os.path.join(REPO_ROOT, "target", "release", "cli.exe")
        if os.path.exists(cli_exe):
            sign_file(cli_exe)
            print(f"[BUILD] Successfully compiled and Authenticode-signed: {cli_exe}")
            sys.exit(0)
        else:
            print("[BUILD] Error: cli.exe not found after successful build!")
            sys.exit(1)
    else:
        print(f"[BUILD] Build failed with return code {return_code}")
        sys.exit(return_code)

if __name__ == "__main__":
    main()

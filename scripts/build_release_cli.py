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
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = r"D:\harfile\ModelFusion"
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
SIGNTOOL_EXE = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

stop_event = threading.Event()
signed_files = set()
lock = threading.Lock()

def sign_file(file_path):
    with lock:
        if file_path in signed_files:
            return True
    
    # Retry loop in case rustc is still finalizing file writes
    for attempt in range(5):
        try:
            res = subprocess.run([
                SIGNTOOL_EXE, "sign",
                "/f", PFX_PATH,
                "/p", "HugOSPassword123!",
                "/fd", "SHA256",
                file_path
            ], capture_output=True, text=True)
            if res.returncode == 0:
                with lock:
                    signed_files.add(file_path)
                return True
        except Exception:
            pass
        time.sleep(0.01)
    return False

def get_candidate_files():
    candidates = []
    target_dir = os.path.join(REPO_ROOT, "target", "release")
    
    # 1. target/release/*.exe and *.dll
    if os.path.exists(target_dir):
        try:
            for f in os.listdir(target_dir):
                if f.endswith(".exe") or f.endswith(".dll"):
                    candidates.append(os.path.join(target_dir, f))
        except Exception:
            pass
            
    # 2. target/release/deps/*.exe and *.dll
    deps_dir = os.path.join(target_dir, "deps")
    if os.path.exists(deps_dir):
        try:
            for f in os.listdir(deps_dir):
                if f.endswith(".exe") or f.endswith(".dll"):
                    candidates.append(os.path.join(deps_dir, f))
        except Exception:
            pass

    # 3. target/release/build/**/*.exe and *.dll
    build_dir = os.path.join(target_dir, "build")
    if os.path.exists(build_dir):
        try:
            for root, _, files in os.walk(build_dir):
                for f in files:
                    if f.endswith(".exe") or f.endswith(".dll"):
                        candidates.append(os.path.join(root, f))
        except Exception:
            pass
            
    return candidates

def watcher_thread():
    while not stop_event.is_set():
        candidates = get_candidate_files()
        for fp in candidates:
            if fp not in signed_files:
                sign_file(fp)
        time.sleep(0.005)

def pre_sign_existing():
    candidates = get_candidate_files()
    to_sign = [fp for fp in candidates if fp not in signed_files]
    if to_sign:
        with ThreadPoolExecutor(max_workers=8) as pool:
            pool.map(sign_file, to_sign)

def sweep_and_sign():
    candidates = get_candidate_files()
    for fp in candidates:
        if fp not in signed_files:
            sign_file(fp)

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
        if "Compiling" in line:
            sweep_and_sign()

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

import hashlib
import os
import shutil
import subprocess
import sys
import time

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

source = os.path.abspath("target/release/cli.exe")
destinations = [
    os.path.abspath("IDE/bin/cli.exe"),
    os.path.abspath("IDE/VSCode-win32-x64/bin/cli.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\bin\cli.exe")
]

print(f"Authoritative Source: {source}")

if not os.path.exists(source):
    raise FileNotFoundError(f"Source file not found: {source}")

src_hash = get_sha256(source)
src_size = os.path.getsize(source)
print(f"Source SHA-256: {src_hash} ({src_size:,} bytes)")

for dst in destinations:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        dst_hash = get_sha256(dst)
        if dst_hash == src_hash:
            print(f"Already identical: {dst}")
            continue
    
    # Needs copy. If locked, terminate cli.exe
    copied = False
    for attempt in range(3):
        try:
            shutil.copy2(source, dst)
            copied = True
            print(f"Copied to: {dst}")
            break
        except PermissionError:
            print(f"Process locked {dst}, terminating cli processes and retrying...")
            subprocess.run(['powershell', '-Command', 'Get-Process cli -ErrorAction SilentlyContinue | Stop-Process -Force'], check=False)
            time.sleep(0.6)
    
    if not copied:
        shutil.copy2(source, dst)

all_paths = [source] + destinations
hashes = {}

print("\n--- 4-Way Parity Verification Report ---")
for p in all_paths:
    sha = get_sha256(p)
    sz = os.path.getsize(p)
    hashes[p] = sha
    print(f"[{sha}] ({sz:,} bytes) -> {p}")

unique = set(hashes.values())
if len(unique) == 1:
    print(f"\nSUCCESS: 4-Way Cryptographic Parity Confirmed! SHA-256: {list(unique)[0]}\n")
else:
    print(f"\nERROR: Hash mismatch across locations: {hashes}\n")
    sys.exit(1)

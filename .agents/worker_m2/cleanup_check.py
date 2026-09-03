import os
import sys

print("Hello from standard python!", flush=True)
lock_path = r"C:\Users\oyesa\.hugos-ide\.inference.lock"
print(f"Lock exists: {os.path.exists(lock_path)}", flush=True)
if os.path.exists(lock_path):
    try:
        os.remove(lock_path)
        print("Removed stale lock file successfully.", flush=True)
    except Exception as e:
        print(f"Could not remove lock file: {e}", flush=True)

# Run tasklist via subprocess
import subprocess
out = subprocess.run(["taskkill", "/F", "/IM", "cli.exe"], capture_output=True, text=True)
print(f"Taskkill stdout: {out.stdout.strip()}", flush=True)
print(f"Taskkill stderr: {out.stderr.strip()}", flush=True)
print("Done.", flush=True)

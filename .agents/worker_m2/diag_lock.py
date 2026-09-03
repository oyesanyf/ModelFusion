import os
import sys

lock_path = r"C:\Users\oyesa\.hugos-ide\.inference.lock"
print(f"Lock path: {lock_path}", flush=True)
if os.path.exists(lock_path):
    print("Lock file exists on disk.", flush=True)
    try:
        # Try to open exclusively
        with open(lock_path, "r+") as f:
            print("Successfully opened lock file read/write (not exclusively locked by another process).", flush=True)
    except Exception as e:
        print(f"Lock file is LOCKED by another process: {e}", flush=True)
else:
    print("Lock file does not exist on disk.", flush=True)

# Try removing it if possible
try:
    if os.path.exists(lock_path):
        os.remove(lock_path)
        print("Removed lock file.", flush=True)
except Exception as e:
    print(f"Could not remove lock file: {e}", flush=True)

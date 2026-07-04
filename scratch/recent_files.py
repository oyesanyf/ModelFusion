import os
import time
from datetime import datetime, timedelta

def find_recent_files(root_dir, days=2):
    cutoff = datetime.now() - timedelta(days=days)
    recent_files = []
    
    # Skip target directory because it contains too many build files
    for root, dirs, files in os.walk(root_dir):
        if 'target' in dirs:
            dirs.remove('target')
        if '.git' in dirs:
            dirs.remove('.git')
        if '.system_generated' in dirs:
            dirs.remove('.system_generated')
            
        for file in files:
            filepath = os.path.join(root, file)
            try:
                mtime = os.path.getmtime(filepath)
                mtime_dt = datetime.fromtimestamp(mtime)
                if mtime_dt > cutoff:
                    recent_files.append((filepath, mtime_dt, os.path.getsize(filepath)))
            except Exception as e:
                pass
                
    recent_files.sort(key=lambda x: x[1], reverse=True)
    return recent_files

if __name__ == "__main__":
    root_dir = r"d:\harfile\ModelFusion"
    print("Finding files modified in the last 2 days...")
    files = find_recent_files(root_dir, days=2)
    for path, mtime, size in files[:40]:
        print(f"{mtime} | {size:10} bytes | {path}")

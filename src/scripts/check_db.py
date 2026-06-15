
import sqlite3
import os

db_paths = [
    "d:/harfile/HFOrchestra/src/db/hf_models.db",
    "d:/harfile/HFOrchestra/db/hf_models.db",
    "d:/harfile/HFOrchestra/src/hforchestra/db/hf_models.db"
]

for p in db_paths:
    if os.path.exists(p):
        print(f"Checking {p} (Size: {os.path.getsize(p)/1024/1024:.2f} MB)...")
        try:
            conn = sqlite3.connect(p)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchall()
            print(f"Result: {result}")
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Path {p} does not exist.")

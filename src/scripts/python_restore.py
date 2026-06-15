
import subprocess
import os
import sys
import time

def recover_database():
    db_path = "db/hf_models.db"
    sql_path = "db/recovered.sql"
    
    # Check paths
    if not os.path.exists(sql_path):
        print(f"❌ SQL file not found: {sql_path}")
        return False
        
    print(f"📦 SQL Dump Size: {os.path.getsize(sql_path) / (1024*1024*1024):.2f} GB")
    
    # Remove existing 0-byte DB if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"🗑️ Removed existing {db_path}")
        except Exception as e:
            print(f"⚠️ Could not remove existing DB: {e}")
            
    print("🚀 Starting Restore Process via sqlite3...")
    start_time = time.time()
    
    # streaming load to avoid memory issues and shell quirks
    try:
        with open(sql_path, 'rb') as f_in:
            # Open sqlite3 process
            process = subprocess.Popen(
                ['sqlite3', db_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Pipe data
            total_bytes = os.path.getsize(sql_path)
            bytes_sent = 0
            chunk_size = 1024 * 1024 * 64 # 64MB chunks
            
            while True:
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    process.stdin.write(chunk)
                    # flush slightly risky if buffer full, but normally ok
                except BrokenPipeError:
                    print("❌ Broken Pipe - sqlite3 process died")
                    break
                    
                bytes_sent += len(chunk)
                if bytes_sent % (chunk_size * 5) == 0:
                     print(f"   ⏳ Progress: {bytes_sent/total_bytes*100:.1f}% ({bytes_sent/(1024*1024):.0f} MB)")
            
            process.stdin.close()
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"❌ sqlite3 error: {stderr.decode()}")
                return False
                
    except Exception as e:
        print(f"❌ Python Error: {e}")
        return False
        
    elapsed = time.time() - start_time
    print(f"✅ Restore Complete in {elapsed:.1f}s")
    
    if os.path.exists(db_path):
        print(f"🎉 New DB Size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")
        return True
    else:
        print("❌ DB file was not created!")
        return False

if __name__ == "__main__":
    success = recover_database()
    sys.exit(0 if success else 1)

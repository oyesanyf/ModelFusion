
import sqlite3
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from hforchestra.core.comprehensive_model_populator import ComprehensiveHFModelPopulator
except ImportError:
    # Try alternate path if running from src
    sys.path.append(os.getcwd())
    try:
        from hforchestra.core.comprehensive_model_populator import ComprehensiveHFModelPopulator
    except:
        # Last resort fallback if imports verify complex
        # We manually create schema
        ComprehensiveHFModelPopulator = None

SRC_DB = "d:/harfile/HFOrchestra/src/db/hf_models.db"
DST_DB = "d:/harfile/HFOrchestra/src/db/hf_models_recovered.db"

def manual_init_dst(db_path):
    # Fallback to manual schema if class import fails
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Simplified schema creation - good enough for recovery dump
    # We will try to copy schema from source if possible using .schema? 
    # But .schema might be corrupt.
    # So we assume the schema from the file we viewed earlier (Step 1213)
    # ... logic omitted for brevity in thought, I'll rely on import success ...
    pass

def init_dst():
    if os.path.exists(DST_DB):
        os.remove(DST_DB)
    
    if ComprehensiveHFModelPopulator:
        # This creates schema using the class
        p = ComprehensiveHFModelPopulator(db_path=DST_DB)
        logger.info("Initialized new database schema using ComprehensiveHFModelPopulator.")
    else:
        logger.error("Could not import ComprehensiveHFModelPopulator. Cannot init schema.")
        sys.exit(1)

def recover_table(table_name, src_conn, dst_conn):
    logger.info(f"Recovering table: {table_name}")
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()
    
    # Get columns/schema
    insert_sql = ""
    try:
        # Try to get column names from pragma table_info
        src_cur.execute(f"PRAGMA table_info({table_name})")
        cols_info = src_cur.fetchall()
        if not cols_info:
             logger.warning(f"No info for table {table_name}")
             return
        
        col_names = [c[1] for c in cols_info]
        col_list = ",".join(col_names)
        placeholders = ",".join(["?"]*len(col_names))
        insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
        logger.info(f"Columns: {col_list}")
    except Exception as e:
        logger.error(f"Cannot read schema for {table_name}: {e}")
        return

    # Scan
    max_rowid = 3000000
    try:
        src_cur.execute(f"SELECT MAX(rowid) FROM {table_name}")
        r = src_cur.fetchone()
        if r and r[0]: max_rowid = r[0]
    except:
        pass
        
    logger.info(f"Scanning up to rowid {max_rowid}...")
    
    chunk_size = 1000
    total_recovered = 0
    
    for start in range(1, max_rowid + 1, chunk_size):
        end = start + chunk_size - 1
        try:
            src_cur.execute(f"SELECT * FROM {table_name} WHERE rowid BETWEEN ? AND ?", (start, end))
            rows = src_cur.fetchall()
            if rows:
                dst_cur.executemany(insert_sql, rows)
                total_recovered += len(rows)
            
            if start % 50000 < chunk_size:
                logger.info(f"Scanned {start}/{max_rowid} (Recovered: {total_recovered})")
                dst_conn.commit()
                
        except Exception as e:
            # Batch failed, try individual
            logger.warning(f"Corruption in batch {start}-{end}. Retrying row-by-row.")
            for r in range(start, end + 1):
                try:
                    src_cur.execute(f"SELECT * FROM {table_name} WHERE rowid=?", (r,))
                    row = src_cur.fetchone()
                    if row:
                        dst_cur.execute(insert_sql, row)
                        total_recovered += 1
                except:
                    pass
            dst_conn.commit()

    dst_conn.commit()
    logger.info(f"Recovered {total_recovered} rows from {table_name}")

def main():
    if not os.path.exists(SRC_DB):
        logger.error(f"Source DB not found: {SRC_DB}")
        return

    init_dst()
    
    try:
        src_conn = sqlite3.connect(SRC_DB)
        dst_conn = sqlite3.connect(DST_DB)
        
        recover_table('metadata', src_conn, dst_conn)
        recover_table('models', src_conn, dst_conn)
        
        src_conn.close()
        dst_conn.close()
        
        logger.info("Recovery complete.")
        try:
            s_size = os.path.getsize(SRC_DB)/1024/1024
            d_size = os.path.getsize(DST_DB)/1024/1024
            logger.info(f"Original size: {s_size:.2f} MB")
            logger.info(f"Recovered size: {d_size:.2f} MB")
        except: pass
        
    except Exception as e:
        logger.error(f"Recovery failed: {e}")

if __name__ == "__main__":
    main()

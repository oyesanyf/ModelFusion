#!/usr/bin/env python3
"""
Check Database Structure
Examine the database structure before making changes
"""

import sqlite3
import os

def check_database_structure():
    """Check the database structure."""
    db_path = "db/hf_models.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("🔍 Database Structure Analysis")
            print("=" * 50)
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"📋 Tables found: {[table[0] for table in tables]}")
            
            # Check models table structure
            if ('models',) in tables:
                print("\n📊 Models table structure:")
                cursor.execute("PRAGMA table_info(models)")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
                
                # Check total models
                cursor.execute("SELECT COUNT(*) FROM models")
                total_models = cursor.fetchone()[0]
                print(f"\n📈 Total models in database: {total_models:,}")
                
                # Check sample data
                print("\n📝 Sample data (first 3 rows):")
                cursor.execute("SELECT model_id, pipeline_tag, downloads FROM models LIMIT 3")
                samples = cursor.fetchall()
                for sample in samples:
                    print(f"  {sample[0]} | {sample[1]} | {sample[2]} downloads")
                
                # Check pipeline tags
                cursor.execute("SELECT DISTINCT pipeline_tag FROM models WHERE pipeline_tag IS NOT NULL AND pipeline_tag != '' ORDER BY pipeline_tag LIMIT 10")
                pipeline_tags = cursor.fetchall()
                print(f"\n🏷️  Sample pipeline tags (first 10):")
                for tag in pipeline_tags:
                    print(f"  {tag[0]}")
                
                # Check for security/malware related tags
                print(f"\n🔒 Security/Malware related pipeline tags:")
                cursor.execute("""
                    SELECT DISTINCT pipeline_tag 
                    FROM models 
                    WHERE pipeline_tag LIKE '%malware%' 
                    OR pipeline_tag LIKE '%security%' 
                    OR pipeline_tag LIKE '%ember%'
                    OR pipeline_tag LIKE '%threat%'
                    OR pipeline_tag LIKE '%vulnerability%'
                    ORDER BY pipeline_tag
                """)
                security_tags = cursor.fetchall()
                if security_tags:
                    for tag in security_tags:
                        print(f"  {tag[0]}")
                else:
                    print("  No security-related pipeline tags found")
                
            else:
                print("❌ Models table not found!")
                
    except Exception as e:
        print(f"❌ Error examining database: {e}")

if __name__ == "__main__":
    check_database_structure() 
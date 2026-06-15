#!/usr/bin/env python3
import sqlite3

def simple_check():
    try:
        with sqlite3.connect("db/hf_models.db") as conn:
            cursor = conn.cursor()
            
            # Check total models
            cursor.execute("SELECT COUNT(*) FROM models")
            total = cursor.fetchone()[0]
            print(f"Total models in database: {total:,}")
            
            # Check for malware models
            cursor.execute("SELECT model_id, pipeline_tag, downloads FROM models WHERE model_id LIKE '%malware%' ORDER BY downloads DESC LIMIT 5")
            malware_models = cursor.fetchall()
            print(f"\nMalware models found: {len(malware_models)}")
            for model in malware_models:
                print(f"  - {model[0]} ({model[1]}) - {model[2]:,} downloads")
            
            # Check for specific models
            specific_models = [
                "sibumi/DISTILBERT_static_malware-detection",
                "llmrails/ember-v1",
                "ZySec-AI/SecurityLLM"
            ]
            
            print(f"\nChecking specific models:")
            for model_name in specific_models:
                cursor.execute("SELECT model_id, pipeline_tag, downloads FROM models WHERE model_id = ?", (model_name,))
                result = cursor.fetchone()
                if result:
                    print(f"  ✅ {result[0]} ({result[1]}) - {result[2]:,} downloads")
                else:
                    print(f"  ❌ {model_name} - NOT FOUND")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simple_check() 
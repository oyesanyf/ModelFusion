#!/usr/bin/env python3
"""
Check what security and malware models exist in the database
"""

import sqlite3
import json

def check_security_models():
    """Check for security and malware models in the database."""
    try:
        with sqlite3.connect("db/hf_models.db") as conn:
            cursor = conn.cursor()
            
            print("🔍 Checking for security and malware models in database...")
            print("=" * 60)
            
            # Check for models with security-related pipeline tags
            security_pipelines = [
                'malware-detection', 'security-analysis', 'threat-detection',
                'vulnerability-analysis', 'ember', 'malware', 'security'
            ]
            
            for pipeline in security_pipelines:
                cursor.execute("""
                    SELECT model_id, pipeline_tag, downloads, likes 
                    FROM models 
                    WHERE pipeline_tag LIKE ? 
                    AND downloads > 10
                    ORDER BY downloads DESC
                    LIMIT 5
                """, (f'%{pipeline}%',))
                
                models = cursor.fetchall()
                if models:
                    print(f"\n📊 Models with pipeline containing '{pipeline}':")
                    for model in models:
                        print(f"  • {model[0]} ({model[1]}) - {model[2]} downloads")
                else:
                    print(f"\n❌ No models found with pipeline containing '{pipeline}'")
            
            # Check for models with security-related tags
            print(f"\n🔍 Checking for models with security-related tags...")
            cursor.execute("""
                SELECT model_id, pipeline_tag, downloads, likes, tags
                FROM models 
                WHERE tags LIKE '%malware%' 
                OR tags LIKE '%security%' 
                OR tags LIKE '%ember%'
                OR tags LIKE '%threat%'
                OR tags LIKE '%vulnerability%'
                AND downloads > 10
                ORDER BY downloads DESC
                LIMIT 10
            """)
            
            models = cursor.fetchall()
            if models:
                print(f"\n📊 Models with security-related tags:")
                for model in models:
                    model_id, pipeline_tag, downloads, likes, tags = model
                    print(f"  • {model_id} ({pipeline_tag}) - {downloads} downloads")
                    if tags:
                        try:
                            tag_list = json.loads(tags) if isinstance(tags, str) else tags
                            security_tags = [tag for tag in tag_list if any(sec in tag.lower() for sec in ['malware', 'security', 'ember', 'threat', 'vulnerability'])]
                            if security_tags:
                                print(f"    Tags: {', '.join(security_tags)}")
                        except:
                            pass
            else:
                print(f"\n❌ No models found with security-related tags")
            
            # Check for specific known malware models
            print(f"\n🔍 Checking for specific known malware models...")
            known_models = [
                'sibumi/DISTILBERT_static_malware-detection',
                'llmrails/ember-v1',
                'microsoft/big-vul',
                'CyberPeace/Malware-Classification-using-BERT',
                'imthean/MalConv2',
                'avast/ember-bodmas',
                'BoredGenius/ember-malware-detector',
                'stefan-story/malware-detect-by-pe-imports'
            ]
            
            for model_id in known_models:
                cursor.execute("""
                    SELECT model_id, pipeline_tag, downloads, likes 
                    FROM models 
                    WHERE model_id = ?
                """, (model_id,))
                
                model = cursor.fetchone()
                if model:
                    print(f"  ✅ {model[0]} ({model[1]}) - {model[2]} downloads")
                else:
                    print(f"  ❌ {model_id} - NOT FOUND")
            
            # Check total models in database
            cursor.execute("SELECT COUNT(*) FROM models")
            total_models = cursor.fetchone()[0]
            print(f"\n📊 Total models in database: {total_models:,}")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_security_models() 
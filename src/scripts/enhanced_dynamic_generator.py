#!/usr/bin/env python3
"""
Enhanced Dynamic Task Model Generator
Downloads database from HuggingFace and extracts ALL categories and models to create comprehensive task_models.json
"""

import sqlite3
import json
import time
import requests
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDynamicTaskGenerator:
    """Enhanced generator that downloads database from HuggingFace and extracts ALL categories and models."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.output_path = Path("config/task_models.json")
        self.db_url = "https://huggingface.co/datasets/huggingface-hub/hf-models-db/resolve/main/hf_models.db"
        
    def download_database(self) -> bool:
        """Download the latest database from HuggingFace."""
        try:
            print("🌐 Downloading latest database from HuggingFace...")
            
            # Create db directory if it doesn't exist
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(exist_ok=True)
            
            # Create backup of existing database
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.backup"
                shutil.copy2(self.db_path, backup_path)
                print(f"📁 Created backup: {backup_path}")
            
            # Download the database
            print(f"⬇️  Downloading from: {self.db_url}")
            response = requests.get(self.db_url, stream=True)
            response.raise_for_status()
            
            # Save the database
            with open(self.db_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Database downloaded successfully: {self.db_path}")
            
            # Verify the database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM models")
                model_count = cursor.fetchone()[0]
                print(f"📊 Database contains {model_count:,} models")
            
            return True
            
        except Exception as e:
            logger.error(f"Error downloading database: {e}")
            print(f"❌ Failed to download database: {e}")
            
            # Restore backup if download failed
            backup_path = f"{self.db_path}.backup"
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.db_path)
                print(f"🔄 Restored database from backup")
            
            return False
        
    def get_all_pipeline_categories(self) -> Dict[str, List[str]]:
        """Get all pipeline categories and their task types from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all unique pipeline tags
                cursor.execute("""
                    SELECT DISTINCT pipeline_tag 
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL 
                    AND pipeline_tag != ''
                    ORDER BY pipeline_tag
                """)
                
                pipeline_tags = [row[0] for row in cursor.fetchall()]
                
                # Categorize pipeline tags into logical groups
                categories = {
                    "text_processing": [],
                    "image_processing": [],
                    "audio_processing": [],
                    "video_processing": [],
                    "multimodal_processing": [],
                    "security": [],
                    "legal": [],
                    "special_tasks": [],
                    "other": []
                }
                
                # Define category mappings
                text_pipelines = [
                    'text-classification', 'text-generation', 'text2text-generation',
                    'fill-mask', 'token-classification', 'question-answering',
                    'summarization', 'translation', 'sentence-similarity',
                    'text-ranking', 'text-retrieval', 'table-question-answering',
                    'table-to-text', 'multiple-choice', 'zero-shot-classification'
                ]
                
                image_pipelines = [
                    'image-classification', 'image-segmentation', 'object-detection',
                    'image-to-image', 'image-to-text', 'image-to-3d',
                    'image-to-video', 'image-feature-extraction', 'keypoint-detection',
                    'mask-generation', 'zero-shot-image-classification',
                    'visual-question-answering', 'visual-document-retrieval',
                    'unconditional-image-generation', 'text-to-image'
                ]
                
                audio_pipelines = [
                    'automatic-speech-recognition', 'audio-classification',
                    'audio-to-audio', 'text-to-speech', 'text-to-audio',
                    'audio-text-to-text', 'voice-activity-detection'
                ]
                
                video_pipelines = [
                    'video-classification', 'video-text-to-text', 'video-to-video'
                ]
                
                multimodal_pipelines = [
                    'any-to-any', 'document-question-answering', 'graph-ml',
                    'image-text-to-text', 'time-series-forecasting'
                ]
                
                security_pipelines = [
                    'malware', 'security', 'ember', 'vulnerability', 'threat', 'cybersecurity'
                ]
                
                legal_pipelines = [
                    'legal', 'compliance', 'regulation', 'privacy', 'gdpr', 'contract'
                ]
                
                # Categorize each pipeline
                for pipeline in pipeline_tags:
                    if pipeline in text_pipelines:
                        categories["text_processing"].append(pipeline)
                    elif pipeline in image_pipelines:
                        categories["image_processing"].append(pipeline)
                    elif pipeline in audio_pipelines:
                        categories["audio_processing"].append(pipeline)
                    elif pipeline in video_pipelines:
                        categories["video_processing"].append(pipeline)
                    elif pipeline in multimodal_pipelines:
                        categories["multimodal_processing"].append(pipeline)
                                         elif any(sec in pipeline.lower() for sec in security_pipelines):
                         categories["security"].append(pipeline)
                     elif any(legal in pipeline.lower() for legal in legal_pipelines):
                         categories["legal"].append(pipeline)
                    elif pipeline in ['feature-extraction', 'robotics', 'reinforcement-learning']:
                        categories["special_tasks"].append(pipeline)
                    else:
                        categories["other"].append(pipeline)
                
                # Also check for security models by querying the database directly
                print("🔍 Checking for security and malware models...")
                cursor.execute("""
                    SELECT DISTINCT pipeline_tag 
                    FROM models 
                    WHERE (pipeline_tag LIKE '%malware%' 
                           OR pipeline_tag LIKE '%security%' 
                           OR pipeline_tag LIKE '%ember%'
                           OR pipeline_tag LIKE '%threat%'
                           OR pipeline_tag LIKE '%vulnerability%')
                    AND pipeline_tag IS NOT NULL 
                    AND pipeline_tag != ''
                """)
                
                                 security_pipeline_tags = [row[0] for row in cursor.fetchall()]
                 for pipeline in security_pipeline_tags:
                     if pipeline not in categories["security"]:
                         categories["security"].append(pipeline)
                         print(f"  ✅ Added security pipeline: {pipeline}")
                 
                 # Also check for legal models
                 print("🔍 Checking for legal models...")
                 cursor.execute("""
                     SELECT DISTINCT pipeline_tag 
                     FROM models 
                     WHERE (pipeline_tag LIKE '%legal%' 
                            OR pipeline_tag LIKE '%compliance%' 
                            OR pipeline_tag LIKE '%regulation%'
                            OR pipeline_tag LIKE '%privacy%'
                            OR pipeline_tag LIKE '%gdpr%'
                            OR pipeline_tag LIKE '%contract%')
                     AND pipeline_tag IS NOT NULL 
                     AND pipeline_tag != ''
                 """)
                 
                 legal_pipeline_tags = [row[0] for row in cursor.fetchall()]
                 for pipeline in legal_pipeline_tags:
                     if pipeline not in categories["legal"]:
                         categories["legal"].append(pipeline)
                         print(f"  ✅ Added legal pipeline: {pipeline}")
                
                # Remove empty categories
                categories = {k: v for k, v in categories.items() if v}
                
                return categories
                
        except Exception as e:
            logger.error(f"Error getting pipeline categories: {e}")
            return {}
    
    def get_best_models_for_pipeline(self, pipeline_tag: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the best models for a specific pipeline from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query for best models by pipeline tag
                cursor.execute("""
                    SELECT model_id, author, pipeline_tag, downloads, likes, 
                           last_modified, description, tags
                    FROM models 
                    WHERE pipeline_tag = ? 
                    AND downloads > 10
                    ORDER BY downloads DESC, likes DESC
                    LIMIT ?
                """, (pipeline_tag, limit))
                
                models = cursor.fetchall()
                
                result = []
                for model in models:
                    model_id, author, pipeline_tag, downloads, likes, last_modified, description, tags = model
                    
                    # Parse tags if they exist
                    tag_list = []
                    if tags:
                        try:
                            tag_list = json.loads(tags) if isinstance(tags, str) else tags
                        except:
                            tag_list = []
                    
                    result.append({
                        'model_id': model_id,
                        'author': author,
                        'pipeline_tag': pipeline_tag,
                        'downloads': downloads,
                        'likes': likes,
                        'last_modified': last_modified,
                        'description': description,
                        'tags': tag_list,
                        'score': self._calculate_model_score(downloads, likes, last_modified)
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting models for pipeline {pipeline_tag}: {e}")
            return []
    
    def _calculate_model_score(self, downloads: int, likes: int, last_modified: str) -> float:
        """Calculate a score for model ranking."""
        try:
            # Recency score (newer models get higher score)
            if last_modified:
                last_modified_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                days_old = (datetime.now().astimezone() - last_modified_dt).days
                recency_score = max(0.1, 1.0 - (days_old / 365))  # Decay over 1 year
            else:
                recency_score = 0.5
            
            # Popularity score
            popularity_score = min(1.0, (downloads / 1000000) + (likes / 10000))
            
            # Combined score
            return (popularity_score * 0.7) + (recency_score * 0.3)
            
        except:
            return 0.5
    
    def generate_task_config(self, pipeline_tag: str, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate task configuration for a pipeline."""
        if not models:
            return {}
        
        best_model = models[0]
        
        # Generate description based on pipeline
        descriptions = {
            'text-classification': 'Classify text into categories',
            'text-generation': 'Generate text content',
            'image-classification': 'Classify images into categories',
            'object-detection': 'Detect objects in images',
            'automatic-speech-recognition': 'Convert speech to text',
            'translation': 'Translate text between languages',
            'summarization': 'Summarize text content',
            'question-answering': 'Answer questions based on context',
            'feature-extraction': 'Extract features from data',
            'malware-detection': 'Detect malware and malicious content',
            'security-analysis': 'Analyze security threats and vulnerabilities'
        }
        
        description = descriptions.get(pipeline_tag, f'Process {pipeline_tag} tasks')
        
        # Generate example text
        examples = {
            'text-classification': 'This is a sample text for classification.',
            'text-generation': 'Generate a story about',
            'image-classification': 'Classify this image',
            'object-detection': 'Detect objects in this image',
            'automatic-speech-recognition': 'Convert this audio to text',
            'translation': 'Translate this text',
            'summarization': 'Summarize this document',
            'question-answering': 'What is the answer to this question?',
            'feature-extraction': 'Extract features from this data',
            'malware-detection': 'Is this file safe?',
            'security-analysis': 'Analyze this for security threats'
        }
        
        example_text = examples.get(pipeline_tag, f'Sample input for {pipeline_tag}')
        
        return {
            "pipeline": pipeline_tag,
            "description": description,
            "supports_file": True,
            "example_text": example_text,
            "best_model": best_model['model_id'],
            "model_author": best_model['author'],
            "downloads": best_model['downloads'],
            "likes": best_model['likes'],
            "score": best_model['score'],
            "last_updated": best_model['last_modified'],
            "alternative_models": [
                {
                    "model_id": model['model_id'],
                    "author": model['author'],
                    "score": model['score'],
                    "downloads": model['downloads']
                }
                for model in models[1:4]  # Top 3 alternatives
            ],
            "requires_prompt": pipeline_tag in ['question-answering', 'text-generation', 'translation']
        }
    
    def generate_comprehensive_task_models(self) -> Dict[str, Any]:
        """Generate comprehensive task_models.json with ALL categories."""
        try:
            print("🔍 Extracting ALL categories from database...")
            
            # Get all pipeline categories
            categories = self.get_all_pipeline_categories()
            
            print(f"📊 Found {len(categories)} main categories:")
            for category, pipelines in categories.items():
                print(f"  {category}: {len(pipelines)} pipeline types")
            
            # Generate task models for each category
            task_models = {}
            
            for category_name, pipeline_tags in categories.items():
                print(f"\n🔄 Processing category: {category_name}")
                category_tasks = {}
                
                for pipeline_tag in pipeline_tags:
                    print(f"  Processing: {pipeline_tag}")
                    
                    # Get models for this pipeline
                    models = self.get_best_models_for_pipeline(pipeline_tag, limit=5)
                    
                    if models:
                        # Generate task config
                        task_config = self.generate_task_config(pipeline_tag, models)
                        
                        if task_config:
                            # Use pipeline tag as task name, but clean it up
                            task_name = pipeline_tag.replace('-', '_')
                            category_tasks[task_name] = task_config
                            print(f"    ✅ Added {task_name} with {len(models)} models")
                        else:
                            print(f"    ⚠️  No config generated for {pipeline_tag}")
                    else:
                        print(f"    ❌ No models found for {pipeline_tag}")
                
                if category_tasks:
                    task_models[category_name] = category_tasks
                    print(f"  📝 Added {len(category_tasks)} tasks to {category_name}")
            
            # Add metadata
            task_models["_metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "total_categories": len(categories),
                "total_tasks": sum(len(tasks) for tasks in task_models.values() if isinstance(tasks, dict)),
                "database_path": self.db_path,
                "generator_version": "2.0",
                "note": "Generated from database with ALL categories and models"
            }
            
            return task_models
            
        except Exception as e:
            logger.error(f"Error generating comprehensive task models: {e}")
            return {}
    
    def save_task_models(self, task_models: Dict[str, Any]) -> bool:
        """Save task models to JSON file."""
        try:
            # Create backup if file exists
            if self.output_path.exists():
                backup_path = self.output_path.with_suffix('.json.backup')
                # Remove existing backup if it exists
                if backup_path.exists():
                    backup_path.unlink()
                self.output_path.rename(backup_path)
                print(f"📁 Created backup: {backup_path}")
            
            # Save new file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(task_models, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Successfully generated: {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving task models: {e}")
            return False
    
    def run(self, download_db: bool = True) -> bool:
        """Run the enhanced dynamic task generator."""
        try:
            print("🚀 Enhanced Dynamic Task Generator v3.0")
            print("=" * 60)
            
            # Download database if requested
            if download_db:
                if not self.download_database():
                    print("⚠️  Continuing with existing database...")
            
            # Generate comprehensive task models
            task_models = self.generate_comprehensive_task_models()
            
            if not task_models:
                print("❌ Failed to generate task models")
                return False
            
            # Save to file
            success = self.save_task_models(task_models)
            
            if success:
                print("\n🎉 Generation Complete!")
                print("=" * 60)
                
                # Print summary
                metadata = task_models.get("_metadata", {})
                print(f"Generated {metadata.get('total_categories', 0)} categories")
                print(f"Total tasks configured: {metadata.get('total_tasks', 0)}")
                
                # Show categories
                for category, tasks in task_models.items():
                    if category != "_metadata" and isinstance(tasks, dict):
                        print(f"  {category}: {len(tasks)} tasks")
                
                print(f"\n📁 Check {self.output_path} for the generated configuration")
                return True
            else:
                print("❌ Failed to save task models")
                return False
                
        except Exception as e:
            logger.error(f"Error in enhanced dynamic task generation: {e}")
            return False

def main():
    """Main function to run the enhanced generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Dynamic Task Generator')
    parser.add_argument('--no-download', action='store_true', 
                       help='Skip database download and use existing database')
    
    args = parser.parse_args()
    
    generator = EnhancedDynamicTaskGenerator()
    success = generator.run(download_db=not args.no_download)
    
    if success:
        print("✅ Enhanced dynamic task models generated successfully!")
    else:
        print("❌ Failed to generate enhanced dynamic task models")
        print("🔍 Check the logs for more details")

if __name__ == "__main__":
    main() 
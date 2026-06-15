#!/usr/bin/env python3
"""
Dynamic Task Model Generator
Automatically generates task_models.json from database with best models for each task.
No hardcoded configurations - everything comes from the database.
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicTaskGenerator:
    """Generates task_models.json dynamically from database with best models."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.output_path = Path("config/task_models.json")
        
    def get_best_models_for_task(self, task_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the best models for a specific task from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query for best models by task type
                cursor.execute("""
                    SELECT model_id, author, pipeline_tag, downloads, likes, 
                           last_modified, description, tags
                    FROM models 
                    WHERE pipeline_tag = ? 
                    AND downloads > 100
                    ORDER BY downloads DESC, likes DESC
                    LIMIT ?
                """, (task_type, limit))
                
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
            logger.error(f"Error getting models for task {task_type}: {e}")
            return []
    
    def _calculate_model_score(self, downloads: int, likes: int, last_modified: str) -> float:
        """Calculate a score for model ranking."""
        try:
            # Recency score (newer models get higher score)
            last_modified_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            days_old = (datetime.now().astimezone() - last_modified_dt).days
            recency_score = max(0.1, 1.0 - (days_old / 365))  # Decay over 1 year
            
            # Popularity score
            popularity_score = min(1.0, (downloads / 1000000) + (likes / 10000))
            
            # Combined score
            return (popularity_score * 0.7) + (recency_score * 0.3)
            
        except:
            return 0.5
    
    def get_all_task_types(self) -> List[str]:
        """Get all available task types from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT pipeline_tag 
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL 
                    AND pipeline_tag != ''
                    ORDER BY pipeline_tag
                """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting task types: {e}")
            return []
    
    def generate_task_config(self, task_type: str, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate configuration for a specific task type."""
        if not models:
            return {}
        
        best_model = models[0]  # Top model by score
        
        # Determine file types based on task
        file_types = self._get_file_types_for_task(task_type)
        
        # Generate example text based on task
        example_text = self._generate_example_text(task_type)
        
        # Determine if task requires special handling
        requires_prompt = task_type in ['question-answering', 'visual-question-answering', 'document-question-answering']
        requires_labels = task_type in ['zero-shot-classification', 'zero-shot-image-classification']
        
        config = {
            "pipeline": task_type,
            "description": self._generate_description(task_type),
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
                    'model_id': m['model_id'],
                    'author': m['author'],
                    'score': m['score'],
                    'downloads': m['downloads']
                }
                for m in models[1:4]  # Top 3 alternatives
            ]
        }
        
        if file_types:
            config["file_types"] = file_types
        
        if requires_prompt:
            config["requires_prompt"] = True
            
        if requires_labels:
            config["requires_labels"] = True
            
        # Add task-specific options
        if task_type == 'token-classification':
            config["options"] = {"grouped_entities": True}
        elif task_type == 'text-generation':
            config["options"] = {"max_length": 50, "num_return_sequences": 1}
        elif task_type in ['grammar-correction', 'paraphrase-generation']:
            config["prefix"] = f"{task_type.replace('-', ' ')}: "
            
        return config
    
    def _get_file_types_for_task(self, task_type: str) -> List[str]:
        """Get supported file types for a task."""
        file_type_mapping = {
            'image-classification': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'object-detection': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'image-segmentation': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'visual-question-answering': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'document-question-answering': ['jpg', 'jpeg', 'png', 'pdf'],
            'zero-shot-image-classification': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'depth-estimation': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'automatic-speech-recognition': ['wav', 'mp3', 'flac', 'm4a'],
            'audio-classification': ['wav', 'mp3', 'flac', 'm4a'],
            'video-classification': ['mp4', 'avi', 'mov', 'mkv'],
            'table-question-answering': ['csv', 'json']
        }
        return file_type_mapping.get(task_type, [])
    
    def _generate_example_text(self, task_type: str) -> str:
        """Generate example text for a task type."""
        examples = {
            'text-classification': 'I love using Hugging Face models!',
            'token-classification': 'Hugging Face Inc. is based in New York.',
            'question-answering': 'Hugging Face Inc. is based in New York.',
            'text-generation': 'The future of AI is',
            'summarization': 'Hugging Face democratizes access to AI tools and models.',
            'translation': 'Hugging Face is an AI company.',
            'fill-mask': 'Hugging Face is creating a [MASK] tool.',
            'text2text-generation': 'translate English to German: The house is wonderful.',
            'zero-shot-classification': 'This is a tutorial about AI.',
            'feature-extraction': 'def add(a,b): return a+b',
            'spam-detection': 'Congratulations! You\'ve won a free cruise. Call now!',
            'phishing-detection': 'Your account has been locked. Please verify your identity here.',
            'hate-speech-detection': 'I hate those people and they should be punished.',
            'fake-news-detection': 'The earth is flat and NASA is lying to you.',
            'emotion-detection': 'I\'m so excited for my vacation next week!',
            'sarcasm-detection': 'Oh great, another Monday morning meeting!',
            'code-vulnerability-detection': 'eval(input())',
            'financial-ner': 'The revenue for Q4 exceeded $1 million, according to the CFO.',
            'legal-ner': 'Plaintiff John Doe filed a motion in the District Court of California.',
            'biomedical-ner': 'Aspirin is used to reduce fever and relieve pain.',
            'grammar-correction': 'She no went to the store.',
            'paraphrase-generation': 'Can you help me with this task?',
            'causal-language-modeling': 'The sky was full of stars and',
            'code-summary-generation': 'def add(a, b): return a + b',
            'code-clone-detection': 'def sum(a, b): return a + b'
        }
        return examples.get(task_type, 'Sample text for analysis')
    
    def _generate_description(self, task_type: str) -> str:
        """Generate description for a task type."""
        descriptions = {
            'text-classification': 'Classify text into predefined categories',
            'token-classification': 'Extract named entities from text',
            'question-answering': 'Answer questions based on context',
            'text-generation': 'Generate text continuations',
            'summarization': 'Summarize long text',
            'translation': 'Translate text between languages',
            'fill-mask': 'Fill masked tokens in text',
            'text2text-generation': 'Text-to-text generation tasks',
            'zero-shot-classification': 'Classify text without training data',
            'feature-extraction': 'Extract feature embeddings from text',
            'spam-detection': 'Detect spam in text messages',
            'phishing-detection': 'Detect phishing attempts',
            'hate-speech-detection': 'Detect hate speech in text',
            'fake-news-detection': 'Detect fake news',
            'emotion-detection': 'Detect emotions in text',
            'sarcasm-detection': 'Detect sarcasm in text',
            'code-vulnerability-detection': 'Detect vulnerabilities in code',
            'financial-ner': 'Extract financial entities',
            'legal-ner': 'Extract legal entities',
            'biomedical-ner': 'Extract biomedical entities',
            'grammar-correction': 'Correct grammar in text',
            'paraphrase-generation': 'Generate paraphrases of text',
            'causal-language-modeling': 'Generate text using causal language models',
            'code-summary-generation': 'Generate code summaries',
            'code-clone-detection': 'Detect code clones'
        }
        return descriptions.get(task_type, f'Perform {task_type.replace("-", " ")} analysis')
    
    def categorize_tasks(self, task_types: List[str]) -> Dict[str, List[str]]:
        """Categorize tasks into logical groups."""
        categories = {
            'text_processing': [],
            'security_legal': [],
            'specialized_domains': [],
            'content_analysis': [],
            'code_analysis': [],
            'image_processing': [],
            'audio_processing': [],
            'video_processing': [],
            'special_tasks': []
        }
        
        for task in task_types:
            if task in ['text-classification', 'token-classification', 'question-answering', 
                       'text-generation', 'summarization', 'translation', 'fill-mask', 
                       'text2text-generation', 'zero-shot-classification', 'feature-extraction',
                       'grammar-correction', 'paraphrase-generation', 'causal-language-modeling']:
                categories['text_processing'].append(task)
            elif task in ['spam-detection', 'phishing-detection', 'hate-speech-detection', 
                         'fake-news-detection']:
                categories['security_legal'].append(task)
            elif task in ['financial-ner', 'legal-ner', 'biomedical-ner']:
                categories['specialized_domains'].append(task)
            elif task in ['emotion-detection', 'sarcasm-detection']:
                categories['content_analysis'].append(task)
            elif task in ['code-vulnerability-detection', 'code-summary-generation', 'code-clone-detection']:
                categories['code_analysis'].append(task)
            elif task in ['image-classification', 'object-detection', 'image-segmentation', 
                         'visual-question-answering', 'document-question-answering', 
                         'zero-shot-image-classification', 'depth-estimation']:
                categories['image_processing'].append(task)
            elif task in ['automatic-speech-recognition', 'audio-classification']:
                categories['audio_processing'].append(task)
            elif task in ['video-classification']:
                categories['video_processing'].append(task)
            else:
                categories['special_tasks'].append(task)
        
        return categories
    
    def generate_dynamic_task_models(self) -> Dict[str, Any]:
        """Generate the complete task_models.json structure from database."""
        logger.info("Starting dynamic task model generation from database...")
        
        # Get all task types from database
        task_types = self.get_all_task_types()
        logger.info(f"Found {len(task_types)} task types in database")
        
        # Categorize tasks
        categorized_tasks = self.categorize_tasks(task_types)
        
        # Generate the complete structure
        result = {}
        
        for category, tasks in categorized_tasks.items():
            if not tasks:
                continue
                
            result[category] = {}
            
            for task_type in tasks:
                logger.info(f"Processing task: {task_type}")
                
                # Get best models for this task
                models = self.get_best_models_for_task(task_type, limit=5)
                
                if models:
                    # Generate configuration for this task
                    task_config = self.generate_task_config(task_type, models)
                    result[category][task_type] = task_config
                    logger.info(f"  ✓ Found {len(models)} models for {task_type}")
                else:
                    logger.warning(f"  ⚠ No models found for {task_type}")
        
        # Add metadata
        result['_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'total_tasks': len(task_types),
            'database_path': self.db_path,
            'generator_version': '1.0.0',
            'note': 'This file is generated dynamically from the database. Do not edit manually.'
        }
        
        return result
    
    def save_task_models(self, task_models: Dict[str, Any]) -> bool:
        """Save the generated task models to JSON file."""
        try:
            # Create backup of existing file with proper error handling
            if self.output_path.exists():
                backup_path = self.output_path.with_suffix('.json.backup')
                try:
                    # Remove existing backup if it exists
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"Removed existing backup: {backup_path}")
                    
                    # Create new backup
                    import shutil
                    shutil.copy2(self.output_path, backup_path)
                    logger.info(f"Created backup: {backup_path}")
                    
                except PermissionError as e:
                    logger.warning(f"Permission error creating backup: {e}")
                    logger.info("Continuing without backup...")
                except Exception as e:
                    logger.warning(f"Error creating backup: {e}")
                    logger.info("Continuing without backup...")
            
            # Save new file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(task_models, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully generated: {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving task models: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete dynamic task generation process."""
        try:
            logger.info("=== Dynamic Task Model Generator ===")
            
            # Check if database exists
            if not Path(self.db_path).exists():
                logger.error(f"Database not found: {self.db_path}")
                return False
            
            # Generate task models
            task_models = self.generate_dynamic_task_models()
            
            if not task_models:
                logger.error("No task models generated")
                return False
            
            # Save to file
            success = self.save_task_models(task_models)
            
            if success:
                logger.info("=== Generation Complete ===")
                logger.info(f"Generated {len(task_models) - 1} categories")  # -1 for metadata
                total_tasks = sum(len(cat) for cat in task_models.values() if isinstance(cat, dict))
                logger.info(f"Total tasks configured: {total_tasks}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in dynamic task generation: {e}")
            return False

def main():
    """Main function to run the dynamic task generator."""
    generator = DynamicTaskGenerator()
    success = generator.run()
    
    if success:
        print("✅ Dynamic task models generated successfully!")
        print("📁 Check config/task_models.json for the generated configuration")
    else:
        print("❌ Failed to generate dynamic task models")
        print("🔍 Check the logs for more details")

if __name__ == "__main__":
    main() 
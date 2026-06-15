#!/usr/bin/env python3
"""
Dynamic Model Configuration Generator
Automatically generates model_configs.json from database with best models for each task.
No hardcoded configurations - everything comes from the database.
"""

import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Try to import langextract for language and content analysis
try:
    import langextract as lx
    import textwrap
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    print("[WARN] langextract not available. Install with: pip install langextract")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicModelConfigGenerator:
    """Generates model_configs.json dynamically from database with best models."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.output_path = Path("config/model_configs.json")
        
    def get_best_models_for_task(self, task_type: str, limit: int = 3) -> List[Dict[str, Any]]:
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
                    AND downloads > 100
                    ORDER BY pipeline_tag
                """)
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting task types: {e}")
            return []
    
    def generate_model_config(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration for a specific model."""
        model_id = model['model_id']
        pipeline_tag = model['pipeline_tag']
        
        # Determine API provider based on model_id
        if model_id.startswith('openai/'):
            api_provider = 'openai'
        elif model_id.startswith('anthropic/'):
            api_provider = 'anthropic'
        elif model_id.startswith('google/'):
            api_provider = 'gemini'
        elif model_id in ['openai-community/gpt2', 'distilbert/distilgpt2', 'bert-base-uncased', 'roberta-base']:
            # These models have HuggingFace Inference Endpoints
            api_provider = 'huggingface_inference'
        else:
            api_provider = 'huggingface'
        
        # Determine max_tokens based on task type
        max_tokens = self._get_max_tokens_for_task(pipeline_tag)
        
        # Determine timeout based on model size/popularity
        timeout_seconds = self._get_timeout_for_model(model)
        
        # Determine temperature based on provider and model
        temperature = self._get_temperature_for_model(model_id, api_provider)
        
        config = {
            "name": model_id,
            "api_provider": api_provider,
            "model_id": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "cost_per_1k_tokens": 0.0,  # Local models are free
            "rate_limit_per_minute": 60,
            "timeout_seconds": timeout_seconds
        }
        
        return config
    
    def _get_max_tokens_for_task(self, task_type: str) -> int:
        """Get appropriate max_tokens for task type."""
        task_tokens = {
            'text-generation': 500,
            'text-classification': 100,
            'question-answering': 300,
            'summarization': 200,
            'translation': 200,
            'image-classification': 50,
            'object-detection': 100,
            'automatic-speech-recognition': 200,
            'text-to-speech': 100,
            'feature-extraction': 100,
            'fill-mask': 50,
            'token-classification': 100,
            'table-question-answering': 200,
            'document-question-answering': 300,
            'visual-question-answering': 200,
            'zero-shot-classification': 100,
            'zero-shot-image-classification': 50,
            'image-segmentation': 100,
            'image-to-text': 200,
            'text-to-image': 100,
            'audio-classification': 50,
            'audio-to-audio': 100,
            'automatic-speech-recognition': 200,
            'text-to-speech': 100,
            'voice-activity-detection': 50
        }
        
        return task_tokens.get(task_type, 500)
    
    def _get_temperature_for_model(self, model_id: str, api_provider: str) -> float:
        """Get appropriate temperature for model based on provider and model type."""
        # OpenAI models that only support default temperature (1.0)
        openai_default_only_models = ['gpt-5-mini', 'gpt-5-mini-vision', 'gpt-5-mini-128k']
        
        if api_provider == 'openai' and model_id in openai_default_only_models:
            return 1.0
        elif api_provider == 'openai':
            return 0.7  # Default for other OpenAI models
        else:
            return 0.7  # Default for other providers
    
    def _get_timeout_for_model(self, model: Dict[str, Any]) -> int:
        """Get appropriate timeout for model based on popularity/size."""
        downloads = model.get('downloads', 0)
        
        if downloads > 1000000:  # Very popular models
            return 60
        elif downloads > 100000:  # Popular models
            return 45
        elif downloads > 10000:  # Medium popularity
            return 30
        else:  # Less popular models
            return 20
    
    def get_models_for_prompt_and_file(self, prompt: str, file_path: str = None) -> List[str]:
        """Intelligently select models based on prompt content and file type using langextract analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Analyze prompt content using langextract-enhanced analysis
                task_type = self._analyze_prompt_task(prompt)
                
                # Determine file type if provided
                file_type = None
                if file_path:
                    file_type = self._analyze_file_type(file_path)
                
                print(f"[ANALYSIS] Task type: {task_type}, File type: {file_type}")
                
                # Build query based on analysis
                query = """
                    SELECT model_id, pipeline_tag, downloads, likes
                    FROM models 
                    WHERE downloads > 1000
                """
                params = []
                
                # Add task type filter if determined
                if task_type:
                    query += " AND pipeline_tag = ?"
                    params.append(task_type)
                
                # Add file type specific filters
                if file_type:
                    if file_type == 'image':
                        query += " AND (pipeline_tag IN ('image-classification', 'object-detection', 'image-segmentation', 'image-to-text'))"
                    elif file_type == 'audio':
                        query += " AND (pipeline_tag IN ('automatic-speech-recognition', 'audio-classification', 'text-to-speech'))"
                    elif file_type == 'code':
                        query += " AND (pipeline_tag IN ('text-generation', 'text-classification'))"
                    elif file_type == 'text':
                        query += " AND (pipeline_tag IN ('text-generation', 'text-classification', 'summarization', 'translation'))"
                
                query += " ORDER BY downloads DESC, likes DESC LIMIT 5"
                
                cursor.execute(query, params)
                models = cursor.fetchall()
                
                selected_models = [model[0] for model in models]
                print(f"[SELECTION] Found {len(selected_models)} models: {selected_models}")
                
                return selected_models
                
        except Exception as e:
            logger.error(f"Error getting models for prompt: {e}")
            return []
    
    def _analyze_prompt_task(self, prompt: str) -> str:
        """Analyze prompt content to determine task type and language using langextract."""
        prompt_lower = prompt.lower()
        
        # Use langextract to analyze prompt content if available
        detected_language = 'en'  # Default to English
        task_type = 'text-generation'  # Default task type
        
        if LANGEXTRACT_AVAILABLE:
            try:
                # Define extraction prompt for language and task analysis
                analysis_prompt = textwrap.dedent("""\
                Extract the language and task type from the given text.
                Use exact text for extractions. Provide meaningful attributes for context.
                Focus on identifying the primary language and the type of task being requested.""")

                # Define examples for language and task extraction
                examples = [
                    lx.data.ExampleData(
                        text="explain this code",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="language",
                                extraction_text="explain this code",
                                attributes={"detected_language": "en"},
                            ),
                            lx.data.Extraction(
                                extraction_class="task_type",
                                extraction_text="explain",
                                attributes={"task": "text-generation", "context": "code explanation"},
                            ),
                        ],
                    ),
                    lx.data.ExampleData(
                        text="classify the sentiment of this text",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="language",
                                extraction_text="classify the sentiment of this text",
                                attributes={"detected_language": "en"},
                            ),
                            lx.data.Extraction(
                                extraction_class="task_type",
                                extraction_text="classify",
                                attributes={"task": "text-classification", "context": "sentiment analysis"},
                            ),
                        ],
                    ),
                    lx.data.Extraction(
                        extraction_class="task_type",
                        extraction_text="summarize",
                        attributes={"task": "summarization", "context": "text summarization"},
                    ),
                ]

                # Run extraction on the prompt
                from hforchestra.utils.langextract_wrapper import extract_with_config
                result = extract_with_config(
                    lx,
                    text_or_documents=prompt,
                    prompt_description=analysis_prompt,
                    examples=examples
                )
                
                # Extract language and task information
                for extraction in result.extractions:
                    if extraction.extraction_class == "language":
                        detected_language = extraction.attributes.get("detected_language", "en")
                        print(f"[LANG] Detected language: {detected_language}")
                    elif extraction.extraction_class == "task_type":
                        task_type = extraction.attributes.get("task", "text-generation")
                        context = extraction.attributes.get("context", "")
                        print(f"[TASK] Detected task: {task_type} ({context})")
                
            except Exception as e:
                print(f"[WARN] Langextract analysis failed: {e}")
                # Fallback to keyword-based analysis
                task_type = self._fallback_task_analysis(prompt_lower)
        else:
            # Fallback to keyword-based analysis
            task_type = self._fallback_task_analysis(prompt_lower)
        
        return task_type
    
    def _fallback_task_analysis(self, prompt_lower: str) -> str:
        """Fallback task analysis using keyword matching."""
        if any(word in prompt_lower for word in ['explain', 'what', 'how', 'why', 'describe']):
            return 'text-generation'
        elif any(word in prompt_lower for word in ['classify', 'categorize', 'sentiment', 'positive', 'negative']):
            return 'text-classification'
        elif any(word in prompt_lower for word in ['summarize', 'summary', 'brief']):
            return 'summarization'
        elif any(word in prompt_lower for word in ['translate', 'language']):
            return 'translation'
        elif any(word in prompt_lower for word in ['detect', 'find', 'identify']):
            return 'object-detection'
        elif any(word in prompt_lower for word in ['speech', 'audio', 'voice']):
            return 'automatic-speech-recognition'
        else:
            return 'text-generation'  # Default
    
    def _analyze_file_type(self, file_path: str) -> str:
        """Analyze file type from extension."""
        import os
        ext = os.path.splitext(file_path)[1].lower()
        
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        audio_exts = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg']
        code_exts = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs', '.swift']
        text_exts = ['.txt', '.md', '.json', '.xml', '.html', '.css', '.sql']
        
        if ext in image_exts:
            return 'image'
        elif ext in audio_exts:
            return 'audio'
        elif ext in code_exts:
            return 'code'
        elif ext in text_exts:
            return 'text'
        else:
            return 'unknown'
    
    def generate_dynamic_model_configs(self) -> Dict[str, Any]:
        """Generate complete model_configs.json from database with intelligent model selection."""
        try:
            print("[DYNAMIC] Generating model configs from database...")
            
            # Get all task types
            task_types = self.get_all_task_types()
            print(f"[INFO] Found {len(task_types)} task types in database")
            
            configs = {}
            
            # Add essential API models first
            configs["gpt-3.5-turbo"] = {
                "name": "gpt-3.5-turbo",
                "api_provider": "openai",
                "model_id": "gpt-3.5-turbo",
                "max_tokens": 2000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.002,
                "rate_limit_per_minute": 100,
                "timeout_seconds": 180
            }
            
            # Priority task types for better model selection
            priority_tasks = [
                'text-generation',      # For code explanation, general text
                'text-classification',  # For sentiment analysis, categorization
                'question-answering',   # For Q&A tasks
                'summarization',        # For summarization tasks
                'translation',          # For translation tasks
                'image-classification', # For image analysis
                'object-detection',     # For object detection
                'automatic-speech-recognition', # For speech tasks
                'feature-extraction',   # For embedding generation
                'fill-mask',           # For masked language modeling
                'token-classification' # For NER, POS tagging
            ]
            
            # Generate configs for priority tasks first
            for task_type in priority_tasks:
                if task_type in task_types:
                    models = self.get_best_models_for_task(task_type, limit=3)  # Get top 3 models per priority task
                    
                    for i, model in enumerate(models):
                        model_id = model['model_id']
                        
                        # Skip if already added
                        if model_id in configs:
                            continue
                        
                        # Generate config for this model
                        config = self.generate_model_config(model)
                        configs[model_id] = config
                        
                        print(f"[OK] Generated config for {model_id} ({task_type})")
            
            # Generate configs for remaining task types
            remaining_tasks = [task for task in task_types if task not in priority_tasks]
            for task_type in remaining_tasks:
                models = self.get_best_models_for_task(task_type, limit=1)  # Get top 1 model per remaining task
                
                for model in models:
                    model_id = model['model_id']
                    
                    # Skip if already added
                    if model_id in configs:
                        continue
                    
                    # Generate config for this model
                    config = self.generate_model_config(model)
                    configs[model_id] = config
                    
                    print(f"[OK] Generated config for {model_id} ({task_type})")
            
            print(f"[OK] Generated {len(configs)} model configurations")
            return configs
            
        except Exception as e:
            logger.error(f"Error generating model configs: {e}")
            return self._get_fallback_configs()
    
    def _get_fallback_configs(self) -> Dict[str, Any]:
        """Get fallback configurations when database is not available."""
        return {
            "gpt-3.5-turbo": {
                "name": "gpt-3.5-turbo",
                "api_provider": "openai",
                "model_id": "gpt-3.5-turbo",
                "max_tokens": 2000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.002,
                "rate_limit_per_minute": 100,
                "timeout_seconds": 180
            },
            "gpt2": {
                "name": "gpt2",
                "api_provider": "huggingface_inference",
                "model_id": "openai-community/gpt2",
                "max_tokens": 500,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.0,
                "rate_limit_per_minute": 60,
                "timeout_seconds": 30
            }
        }
    
    def save_model_configs(self, configs: Dict[str, Any]) -> bool:
        """Save model configurations to JSON file."""
        try:
            # Create config directory if it doesn't exist
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Saved {len(configs)} model configs to {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model configs: {e}")
            return False
    
    def run(self) -> bool:
        """Run the complete dynamic model config generation process."""
        try:
            print("[DYNAMIC] Starting dynamic model config generation...")
            
            # Generate configs from database
            configs = self.generate_dynamic_model_configs()
            
            if not configs:
                print("[WARN] No configs generated, using fallback")
                configs = self._get_fallback_configs()
            
            # Save to file
            success = self.save_model_configs(configs)
            
            if success:
                print("[DYNAMIC] Model config generation completed successfully")
            else:
                print("[ERROR] Failed to save model configs")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in model config generation: {e}")
            return False

def main():
    """Main function to run the dynamic model config generator."""
    generator = DynamicModelConfigGenerator()
    success = generator.run()
    
    if success:
        print("✅ Dynamic model config generation completed successfully")
        exit(0)
    else:
        print("❌ Dynamic model config generation failed")
        exit(1)

if __name__ == "__main__":
    main() 
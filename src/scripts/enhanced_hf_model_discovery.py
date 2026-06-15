#!/usr/bin/env python3
"""
Enhanced HuggingFace Model Discovery System
Comprehensive model discovery with SQLite storage and orchestration integration
"""

import sqlite3
import json
import time
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive keywords for model discovery
KEYWORDS = [
    # Hugging Face Official Tasks (2025, comprehensive)
    "text-classification", "token-classification", "question-answering", "text-generation",
    "fill-mask", "summarization", "translation", "sentence-similarity", "text2text-generation",
    "conversational", "text-to-speech", "speech-to-text", "automatic-speech-recognition",
    "speech-enhancement", "image-classification", "object-detection", "image-segmentation",
    "depth-estimation", "image-to-text", "text-to-image", "image-to-image",
    "visual-question-answering", "image-captioning", "audio-classification", "audio-to-audio",
    "speaker-diarization", "voice-activity-detection", "zero-shot-image-classification",
    "document-question-answering", "table-question-answering", "tabular-classification",
    "tabular-regression", "structured-data-generation", "reinforcement-learning",
    "code-completion", "time-series-forecasting", "optical-character-recognition",
    "document-understanding", "speech-segmentation", "translation-automatic-post-editing",

    # Major Domains & Industries
    "finance", "financial", "economics", "banking", "accounting", "trading", "investment",
    "fintech", "medical", "medicine", "health", "healthcare", "clinical", "biomedical",
    "pharmaceutical", "diagnosis", "treatment", "genomics", "radiology", "oncology",
    "epidemiology", "drug", "patient", "doctor", "biology", "chemistry", "chemical",
    "physics", "astronomy", "engineering", "robotics", "energy", "battery", "climate",
    "environment", "geology", "meteorology", "agriculture", "nutrition", "food", "ecology",

    "cybersecurity", "security", "malware", "phishing", "threat", "privacy", "forensics",
    "insurance", "actuarial", "risk", "geospatial", "gis", "mapping", "satellite", "remote sensing",
    "cartography", "retail", "ecommerce", "supply chain", "logistics", "inventory",
    "manufacturing", "industrial", "automation", "factory", "marketing", "advertising",
    "recommender", "news", "politics", "policy", "law", "legal", "regulation", "compliance",
    "contract", "jurisdiction", "court", "patent", "intellectual property",

    # Education, Social, Media, Sports, Miscellaneous
    "education", "academic", "teaching", "student", "pedagogy", "social media", "sentiment",
    "opinion", "emotion", "dialogue", "conversation", "chatbot", "multilingual", "translation",
    "sports", "gaming", "esports", "music", "audio", "video", "multimodal", "ocr"
]

@dataclass
class ModelMetrics:
    """Enhanced model metrics with comprehensive information."""
    model_id: str
    author: str
    pipeline_tag: str
    tags: List[str]
    description: str
    downloads: int
    likes: int
    last_modified: str
    license: str
    task_keywords: List[str]
    decision_score: float = 0.0
    capability_score: float = 0.0
    efficiency_score: float = 0.0
    popularity_score: float = 0.0
    
    def calculate_recency_score(self) -> float:
        """Calculate recency score based on last modified date."""
        try:
            from datetime import datetime
            last_modified = datetime.fromisoformat(self.last_modified.replace('Z', '+00:00'))
            days_old = (datetime.now().astimezone() - last_modified).days
            return max(0.1, 1.0 - (days_old / 365))  # Decay over 1 year
        except:
            return 0.5

class HuggingFaceModelDatabase:
    """SQLite database for storing HuggingFace model information."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create models table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
                    author TEXT,
                    pipeline_tag TEXT,
                    tags TEXT,
                    description TEXT,
                    downloads INTEGER,
                    likes INTEGER,
                    last_modified TEXT,
                    license TEXT,
                    task_keywords TEXT,
                    decision_score REAL,
                    capability_score REAL,
                    efficiency_score REAL,
                    popularity_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create keywords table for tracking search terms
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    keyword TEXT PRIMARY KEY,
                    last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    models_found INTEGER DEFAULT 0
                )
            ''')
            
            # Create model_tasks table for task-model mappings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_tasks (
                    model_id TEXT,
                    task_type TEXT,
                    confidence REAL,
                    PRIMARY KEY (model_id, task_type),
                    FOREIGN KEY (model_id) REFERENCES models (model_id)
                )
            ''')
            
            conn.commit()
    
    def save_model(self, model: ModelMetrics):
        """Save a model to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO models 
                (model_id, author, pipeline_tag, tags, description, downloads, likes, 
                 last_modified, license, task_keywords, decision_score, capability_score, 
                 efficiency_score, popularity_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                model.model_id, model.author, model.pipeline_tag, 
                json.dumps(model.tags), model.description, model.downloads, 
                model.likes, model.last_modified, model.license, 
                json.dumps(model.task_keywords), model.decision_score,
                model.capability_score, model.efficiency_score, model.popularity_score
            ))
            
            conn.commit()
    
    def get_models_by_task(self, task_type: str, limit: int = 10) -> List[ModelMetrics]:
        """Get models by task type, ordered by decision score."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT model_id, author, pipeline_tag, tags, description, downloads, 
                       likes, last_modified, license, task_keywords, decision_score,
                       capability_score, efficiency_score, popularity_score
                FROM models 
                WHERE task_keywords LIKE ? OR pipeline_tag LIKE ?
                ORDER BY decision_score DESC
                LIMIT ?
            ''', (f'%{task_type}%', f'%{task_type}%', limit))
            
            models = []
            for row in cursor.fetchall():
                model = ModelMetrics(
                    model_id=row[0],
                    author=row[1],
                    pipeline_tag=row[2],
                    tags=json.loads(row[3]) if row[3] else [],
                    description=row[4],
                    downloads=row[5],
                    likes=row[6],
                    last_modified=row[7],
                    license=row[8],
                    task_keywords=json.loads(row[9]) if row[9] else [],
                    decision_score=row[10],
                    capability_score=row[11],
                    efficiency_score=row[12],
                    popularity_score=row[13]
                )
                models.append(model)
            
            return models
    
    def get_model_count(self) -> int:
        """Get total number of models in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM models')
            return cursor.fetchone()[0]
    
    def update_keyword_search(self, keyword: str, models_found: int):
        """Update keyword search tracking."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO keywords (keyword, last_searched, models_found)
                VALUES (?, CURRENT_TIMESTAMP, ?)
            ''', (keyword, models_found))
            conn.commit()

class EnhancedHuggingFaceDiscovery:
    """Enhanced HuggingFace model discovery with SQLite storage."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db = HuggingFaceModelDatabase(db_path)
        self.hf_api = None
        self._init_api()
    
    def _init_api(self):
        """Initialize HuggingFace API."""
        try:
            from huggingface_hub import HfApi
            self.hf_api = HfApi()
            logger.info("✅ HuggingFace API initialized successfully")
        except ImportError:
            logger.warning("⚠️ huggingface_hub not available. Install with: pip install huggingface_hub")
            self.hf_api = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize HuggingFace API: {e}")
            self.hf_api = None
    
    async def discover_models_comprehensive(self, force_update: bool = False) -> Dict[str, Any]:
        """Comprehensive model discovery using all keywords."""
        if not self.hf_api:
            logger.error("❌ HuggingFace API not available")
            return {"error": "HuggingFace API not available"}
        
        logger.info("🚀 Starting comprehensive model discovery...")
        
        total_models = 0
        new_models = 0
        seen_models = set()
        
        for keyword in KEYWORDS:
            logger.info(f"🔎 Searching for: {keyword}")
            
            try:
                models = list(self.hf_api.list_models(search=keyword, limit=1000, full=True))
                keyword_models = 0
                
                for model in models:
                    if model.modelId not in seen_models:
                        seen_models.add(model.modelId)
                        
                        try:
                            # Get detailed model info
                            model_info = self.hf_api.model_info(model.modelId)
                            
                            # Create ModelMetrics object
                            model_metrics = ModelMetrics(
                                model_id=model_info.modelId,
                                author=getattr(model_info, 'author', 'Unknown'),
                                pipeline_tag=getattr(model_info, 'pipeline_tag', ''),
                                tags=getattr(model_info, 'tags', []),
                                description=model_info.cardData.get('summary', 'No description') if hasattr(model_info, 'cardData') and model_info.cardData else 'No description',
                                downloads=getattr(model_info, 'downloads', 0),
                                likes=getattr(model_info, 'likes', 0),
                                last_modified=str(getattr(model_info, 'lastModified', '')),
                                license=getattr(model_info, 'license', ''),
                                task_keywords=[keyword]
                            )
                            
                            # Calculate scores
                            self._calculate_model_scores(model_metrics)
                            
                            # Save to database
                            self.db.save_model(model_metrics)
                            keyword_models += 1
                            new_models += 1
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing model {model.modelId}: {e}")
                            continue
                
                # Update keyword tracking
                self.db.update_keyword_search(keyword, keyword_models)
                total_models += keyword_models
                
                logger.info(f"✅ Found {keyword_models} models for '{keyword}'")
                
                # Be gentle to the API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Error searching for '{keyword}': {e}")
                continue
        
        logger.info(f"🎉 Discovery completed! Total models: {total_models}, New models: {new_models}")
        
        return {
            "total_models": total_models,
            "new_models": new_models,
            "total_in_db": self.db.get_model_count()
        }
    
    def _calculate_model_scores(self, model: ModelMetrics):
        """Calculate various scores for model ranking."""
        # Popularity score (based on downloads and likes)
        downloads_norm = min(1.0, model.downloads / 1000000)  # Normalize to 1M downloads
        likes_norm = min(1.0, model.likes / 10000)  # Normalize to 10K likes
        model.popularity_score = (downloads_norm * 0.7) + (likes_norm * 0.3)
        
        # Capability score (based on model size indicators)
        size_indicators = ['large', 'xl', 'xxl', '2b', '3b', '7b', '13b', '30b', '70b']
        capability = 0.5  # Base capability
        for indicator in size_indicators:
            if indicator in model.model_id.lower():
                capability += 0.1
        model.capability_score = min(1.0, capability)
        
        # Efficiency score (inverse of capability for fast models)
        model.efficiency_score = 1.0 - model.capability_score
        
        # Decision score (weighted combination)
        model.decision_score = (
            model.popularity_score * 0.4 +
            model.capability_score * 0.3 +
            model.efficiency_score * 0.2 +
            model.calculate_recency_score() * 0.1
        )
    
    def get_best_model_for_task(self, task: str, top_n: int = 5) -> List[ModelMetrics]:
        """Get the best models for a specific task from database."""
        logger.info(f"🎯 Finding best models for task: {task}")
        
        # Map task to search terms
        task_mapping = {
            'general_qa': ['question-answering', 'text-generation'],
            'code_analysis': ['code-completion', 'text-generation'],
            'medical_analysis': ['medical', 'health', 'text-classification'],
            'financial_analysis': ['finance', 'financial', 'text-classification'],
            'creative_writing': ['text-generation', 'conversational'],
            'cybersecurity_malware': ['cybersecurity', 'security', 'text-classification']
        }
        
        search_terms = task_mapping.get(task, [task])
        all_models = []
        
        for search_term in search_terms:
            models = self.db.get_models_by_task(search_term, top_n * 2)
            all_models.extend(models)
        
        # Remove duplicates and sort by decision score
        unique_models = {model.model_id: model for model in all_models}
        sorted_models = sorted(unique_models.values(), key=lambda x: x.decision_score, reverse=True)
        
        return sorted_models[:top_n]
    
    def get_model_recommendations(self, prompt: str, limit: int = 5) -> List[ModelMetrics]:
        """Get model recommendations based on prompt content."""
        # Simple keyword-based task detection
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['code', 'program', 'script', 'function']):
            task = 'code_analysis'
        elif any(word in prompt_lower for word in ['medical', 'health', 'diagnosis']):
            task = 'medical_analysis'
        elif any(word in prompt_lower for word in ['finance', 'investment', 'trading']):
            task = 'financial_analysis'
        elif any(word in prompt_lower for word in ['creative', 'story', 'write']):
            task = 'creative_writing'
        elif any(word in prompt_lower for word in ['security', 'malware', 'threat']):
            task = 'cybersecurity_malware'
        else:
            task = 'general_qa'
        
        return self.get_best_model_for_task(task, limit)

# Enhanced decision engine with database integration
class ModelDecisionEngine:
    """Enhanced decision engine with database-backed model selection."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.discovery = EnhancedHuggingFaceDiscovery(db_path)
        self.weights = {
            'popularity': 0.40,
            'recency': 0.20,
            'reliability': 0.25,
            'efficiency': 0.15
        }
    
    def calculate_decision_score(self, model: ModelMetrics) -> float:
        """Calculate comprehensive decision score."""
        pop_score = min(1.0, (model.downloads / 100000) * 0.7 + (model.likes / 1000) * 0.3)
        recency_score = model.calculate_recency_score()
        reliability_score = 0.8 if 'transformers' in str(model.tags).lower() else 0.5
        efficiency_score = 0.8 if 'mini' in model.model_id.lower() or 'small' in model.model_id.lower() else 0.6
        
        decision_score = (
            pop_score * self.weights['popularity'] +
            recency_score * self.weights['recency'] +
            reliability_score * self.weights['reliability'] +
            efficiency_score * self.weights['efficiency']
        )
        
        return round(decision_score, 3)

# Enhanced task detector with keyword mapping
class IntelligentTaskDetector:
    """Enhanced task detector with comprehensive keyword mapping."""
    
    def __init__(self):
        self.task_patterns = {
            'general_qa': {
                'keywords': ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'explain', 'tell me'],
                'context_patterns': [r'what is', r'how does', r'explain', r'tell me about'],
                'priority_multiplier': 1.0
            },
            'code_analysis': {
                'keywords': ['code', 'script', 'program', 'function', 'algorithm', 'bug', 'error', 'debug'],
                'context_patterns': [r'code', r'program', r'function', r'algorithm'],
                'priority_multiplier': 1.2
            },
            'medical_analysis': {
                'keywords': ['medical', 'health', 'diagnosis', 'treatment', 'patient', 'symptoms'],
                'context_patterns': [r'medical', r'health', r'diagnosis'],
                'priority_multiplier': 1.3
            },
            'financial_analysis': {
                'keywords': ['finance', 'investment', 'trading', 'market', 'stock', 'portfolio'],
                'context_patterns': [r'finance', r'investment', r'trading'],
                'priority_multiplier': 1.2
            },
            'creative_writing': {
                'keywords': ['story', 'creative', 'write', 'narrative', 'fiction', 'poem'],
                'context_patterns': [r'story', r'creative', r'write'],
                'priority_multiplier': 1.1
            },
            'cybersecurity_malware': {
                'keywords': ['security', 'malware', 'threat', 'attack', 'vulnerability', 'cybersecurity'],
                'context_patterns': [r'security', r'malware', r'threat'],
                'priority_multiplier': 1.4
            }
        }
    
    def detect_task_type(self, prompt: str) -> Tuple[str, float]:
        """Detect task type with enhanced accuracy."""
        prompt_lower = prompt.lower()
        
        task_scores = {}
        
        for task_type, config in self.task_patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in prompt_lower)
            keyword_score = min(0.8, keyword_matches / max(len(config['keywords']) * 0.05, 1))
            
            # Context pattern matching
            context_score = 0.0
            for pattern in config['context_patterns']:
                if re.search(pattern, prompt_lower):
                    context_score += 0.4
            context_score = min(1.0, context_score)
            
            # Calculate weighted score
            base_score = (keyword_score * 0.6) + (context_score * 0.4)
            final_score = base_score * config['priority_multiplier']
            
            task_scores[task_type] = final_score
        
        # Return best matching task
        if task_scores:
            best_task = max(task_scores.items(), key=lambda x: x[1])
            return best_task[0], best_task[1]
        
        return 'general_qa', 0.5

# Enhanced smart model selector with database integration
class SmartModelSelector:
    """Enhanced smart model selector with database-backed recommendations."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.task_detector = IntelligentTaskDetector()
        self.discovery = EnhancedHuggingFaceDiscovery(db_path)
        
        # Fallback to fast models if database is empty
        self.fallback_models = {
            'general_qa': ['microsoft/DialoGPT-small', 'distilgpt2', 'gpt2'],
            'code_analysis': ['microsoft/DialoGPT-small', 'gpt2', 'distilgpt2'],
            'medical_analysis': ['microsoft/DialoGPT-small', 'gpt2', 'distilgpt2'],
            'financial_analysis': ['microsoft/DialoGPT-small', 'gpt2', 'distilgpt2'],
            'creative_writing': ['microsoft/DialoGPT-medium', 'microsoft/DialoGPT-small', 'gpt2'],
            'cybersecurity_malware': ['microsoft/DialoGPT-small', 'gpt2', 'distilgpt2']
        }
    
    def select_best_model(self, prompt: str, available_models: Optional[Dict] = None) -> Tuple[str, str, float]:
        """Select best model using database-backed recommendations."""
        # Detect task type
        detected_task, confidence = self.task_detector.detect_task_type(prompt)
        
        # Try to get recommendations from database
        try:
            recommendations = self.discovery.get_model_recommendations(prompt, 5)
            if recommendations:
                best_model = recommendations[0]
                reasoning = f"Detected as '{detected_task}' with {confidence:.1%} confidence. Selected via database: {best_model.model_id}."
                return best_model.model_id, reasoning, confidence
        except Exception as e:
            logger.warning(f"Database lookup failed: {e}")
        
        # Fallback to fast models
        fallback_models = self.fallback_models.get(detected_task, self.fallback_models['general_qa'])
        
        # Find first available fallback model
        for model_id in fallback_models:
            if not available_models or model_id in available_models:
                reasoning = f"Detected as '{detected_task}' with {confidence:.1%} confidence. Using fallback: {model_id}."
                return model_id, reasoning, confidence
        
        # Ultimate fallback
        fallback_model = fallback_models[0]
        reasoning = f"Detected as '{detected_task}' with {confidence:.1%} confidence. Using ultimate fallback: {fallback_model}."
        return fallback_model, reasoning, confidence

# CLI interface for model discovery
async def main():
    """Main function for model discovery and management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced HuggingFace Model Discovery")
    parser.add_argument("--update", action="store_true", help="Update model database")
    parser.add_argument("--search", type=str, help="Search for models by task")
    parser.add_argument("--db-path", type=str, default="db/hf_models.db", help="Database path")
    parser.add_argument("--limit", type=int, default=10, help="Number of models to return")
    
    args = parser.parse_args()
    
    discovery = EnhancedHuggingFaceDiscovery(args.db_path)
    
    if args.update:
        print("🔄 Updating model database...")
        result = await discovery.discover_models_comprehensive(force_update=True)
        print(f"✅ Update completed: {result}")
    
    elif args.search:
        print(f"🔍 Searching for models matching: {args.search}")
        models = discovery.get_best_model_for_task(args.search, args.limit)
        
        for i, model in enumerate(models, 1):
            print(f"\n{i}. {model.model_id}")
            print(f"   Score: {model.decision_score:.3f}")
            print(f"   Downloads: {model.downloads:,}")
            print(f"   Description: {model.description[:100]}...")
    
    else:
        print("📊 Model Database Statistics:")
        print(f"Total models: {discovery.db.get_model_count()}")
        print("\nUsage:")
        print("  --update    Update model database")
        print("  --search    Search for models by task")

if __name__ == "__main__":
    import re
    asyncio.run(main()) 
"""
Enhanced HuggingFace Model Discovery System.

This module provides comprehensive model discovery capabilities with SQLite storage
and orchestration integration.
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
                    popularity_score REAL
                )
            ''')
            
            # Create keyword search tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keyword_searches (
                    keyword TEXT PRIMARY KEY,
                    models_found INTEGER,
                    last_searched TEXT
                )
            ''')
            
            conn.commit()
    
    def save_model(self, model: ModelMetrics):
        """Save a model to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model.model_id, model.author, model.pipeline_tag,
                json.dumps(model.tags), model.description, model.downloads,
                model.likes, model.last_modified, model.license,
                json.dumps(model.task_keywords), model.decision_score,
                model.capability_score, model.efficiency_score, model.popularity_score
            ))
            conn.commit()
    
    def get_models_by_task(self, task_type: str, limit: int = 10) -> List[ModelMetrics]:
        """Get models by task type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM models 
                WHERE pipeline_tag = ? OR task_keywords LIKE ?
                ORDER BY decision_score DESC, downloads DESC
                LIMIT ?
            ''', (task_type, f'%{task_type}%', limit))
            
            models = []
            for row in cursor.fetchall():
                model = ModelMetrics(
                    model_id=row[0], author=row[1], pipeline_tag=row[2],
                    tags=json.loads(row[3]), description=row[4], downloads=row[5],
                    likes=row[6], last_modified=row[7], license=row[8],
                    task_keywords=json.loads(row[9]), decision_score=row[10],
                    capability_score=row[11], efficiency_score=row[12], popularity_score=row[13]
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
        """Update keyword search statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO keyword_searches VALUES (?, ?, ?)
            ''', (keyword, models_found, datetime.now().isoformat()))
            conn.commit()


class EnhancedHuggingFaceDiscovery:
    """Enhanced model discovery with comprehensive search capabilities."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db = HuggingFaceModelDatabase(db_path)
        self._init_api()
    
    def _init_api(self):
        """Initialize HuggingFace API client."""
        try:
            from huggingface_hub import HfApi
            self.api = HfApi()
            self.api_available = True
        except ImportError:
            logger.warning("huggingface_hub not available, using limited functionality")
            self.api_available = False
    
    async def discover_models_comprehensive(self, force_update: bool = False) -> Dict[str, Any]:
        """Comprehensive model discovery across all keywords."""
        if not self.api_available:
            return {"error": "HuggingFace API not available"}
        
        results = {}
        total_models = 0
        
        for keyword in KEYWORDS:
            try:
                logger.info(f"Discovering models for keyword: {keyword}")
                models = self.api.list_models(filter=keyword, limit=50, full=True)
                
                keyword_models = []
                for model in models:
                    model_metrics = ModelMetrics(
                        model_id=model.modelId,
                        author=model.author,
                        pipeline_tag=model.pipeline_tag or "",
                        tags=model.tags or [],
                        description=model.description or "",
                        downloads=model.downloads or 0,
                        likes=model.likes or 0,
                        last_modified=model.lastModified,
                        license=model.license or "",
                        task_keywords=[keyword]
                    )
                    
                    self._calculate_model_scores(model_metrics)
                    self.db.save_model(model_metrics)
                    keyword_models.append(model_metrics)
                
                results[keyword] = len(keyword_models)
                total_models += len(keyword_models)
                self.db.update_keyword_search(keyword, len(keyword_models))
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error discovering models for {keyword}: {e}")
                results[keyword] = 0
        
        return {
            "total_models_discovered": total_models,
            "keyword_results": results,
            "database_total": self.db.get_model_count()
        }
    
    def _calculate_model_scores(self, model: ModelMetrics):
        """Calculate various scores for model evaluation."""
        # Capability score based on downloads and likes
        model.capability_score = min(10.0, (model.downloads / 1000) + (model.likes / 100))
        
        # Efficiency score based on recency and license
        recency_score = model.calculate_recency_score()
        license_score = 1.0 if model.license and "mit" in model.license.lower() else 0.5
        model.efficiency_score = (recency_score + license_score) / 2
        
        # Popularity score
        model.popularity_score = min(10.0, (model.downloads / 10000) + (model.likes / 500))
        
        # Overall decision score
        model.decision_score = (
            model.capability_score * 0.4 +
            model.efficiency_score * 0.3 +
            model.popularity_score * 0.3
        )
    
    def get_best_model_for_task(self, task: str, top_n: int = 5) -> List[ModelMetrics]:
        """Get the best models for a specific task."""
        return self.db.get_models_by_task(task, top_n)
    
    def get_model_recommendations(self, prompt: str, limit: int = 5) -> List[ModelMetrics]:
        """Get model recommendations based on a prompt."""
        # Simple keyword matching for now
        prompt_lower = prompt.lower()
        matching_tasks = []
        
        for keyword in KEYWORDS:
            if keyword in prompt_lower:
                matching_tasks.append(keyword)
        
        if not matching_tasks:
            matching_tasks = ["text-generation"]  # Default fallback
        
        all_models = []
        for task in matching_tasks[:3]:  # Limit to top 3 matching tasks
            models = self.db.get_models_by_task(task, limit)
            all_models.extend(models)
        
        # Sort by decision score and remove duplicates
        unique_models = {model.model_id: model for model in all_models}.values()
        return sorted(unique_models, key=lambda x: x.decision_score, reverse=True)[:limit]


class SmartModelSelector:
    """Intelligent model selection based on task requirements."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db = HuggingFaceModelDatabase(db_path)
        self.task_detector = IntelligentTaskDetector()
    
    def select_best_model(self, prompt: str, available_models: Optional[Dict] = None) -> Tuple[str, str, float]:
        """Select the best model for a given prompt."""
        # Detect task type
        task_type, confidence = self.task_detector.detect_task_type(prompt)
        
        # Get best models for the task
        models = self.db.get_models_by_task(task_type, 5)
        
        if not models:
            return "gpt2", "text-generation", 0.5
        
        # Select the best model
        best_model = models[0]
        return best_model.model_id, task_type, best_model.decision_score


class IntelligentTaskDetector:
    """Detects task type from natural language prompts."""
    
    def __init__(self):
        self.task_patterns = {
            "text-classification": [
                r"classify", r"categorize", r"sentiment", r"emotion", r"topic",
                r"spam", r"fake", r"real", r"positive", r"negative"
            ],
            "text-generation": [
                r"generate", r"write", r"create", r"compose", r"story",
                r"poem", r"article", r"essay", r"text", r"content"
            ],
            "translation": [
                r"translate", r"convert", r"language", r"english", r"spanish",
                r"french", r"german", r"chinese", r"japanese"
            ],
            "summarization": [
                r"summarize", r"summary", r"brief", r"condense", r"extract",
                r"key points", r"main idea"
            ],
            "question-answering": [
                r"answer", r"question", r"what is", r"how to", r"why",
                r"explain", r"describe", r"define"
            ],
            "image-classification": [
                r"image", r"picture", r"photo", r"visual", r"object",
                r"scene", r"identify", r"recognize"
            ]
        }
    
    def detect_task_type(self, prompt: str) -> Tuple[str, float]:
        """Detect the most likely task type from a prompt."""
        prompt_lower = prompt.lower()
        scores = {}
        
        for task_type, patterns in self.task_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    score += 1
            scores[task_type] = score
        
        if not any(scores.values()):
            return "text-generation", 0.5
        
        best_task = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_task] / 3.0)  # Normalize confidence
        
        return best_task, confidence 
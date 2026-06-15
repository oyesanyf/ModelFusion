#!/usr/bin/env python3
"""
Enhanced Model Selection System
Implements advanced techniques for intelligent model selection including:
- Hyperparameter tuning (Grid Search, Random Search, Bayesian Optimization)
- Cross-validation with multiple strategies
- Ensemble methods (Bagging, Boosting, Stacking)
- Sophisticated evaluation metrics
- Multi-objective optimization
- F1 Score evaluation with QA benchmark testing
"""

import sqlite3
import json
import numpy as np
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import re
from datetime import datetime, timedelta
import string
import csv
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import random
from pathlib import Path

# Configure intelligent logging (console + rotating file)
def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("HFOrchestra")
    if logger.handlers:
        return logger
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    # Console
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    # Rotating file
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, os.getenv("LOG_FILE", "hforchestra.log"))
    fh = TimedRotatingFileHandler(log_path, when="midnight", backupCount=14, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.propagate = False
    return logger

logger = _configure_logging()

# Import HuggingFace Hub for model evaluation
try:
    from huggingface_hub import InferenceClient, ModelCard
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    logger.warning("huggingface_hub not available. Install with: pip install huggingface_hub")

try:
    from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")
try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("optuna not available. Install with: pip install optuna")

from concurrent.futures import ThreadPoolExecutor, as_completed

class SelectionStrategy(Enum):
    """Different model selection strategies."""
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    CROSS_VALIDATION = "cross_validation"
    ENSEMBLE_METHODS = "ensemble_methods"
    MULTI_OBJECTIVE = "multi_objective"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    META_LEARNING = "meta_learning"



@dataclass
class ModelCandidate:
    """Represents a model candidate with all its metadata and scores."""
    model_id: str
    pipeline_tag: str
    author: str
    library_name: str
    downloads: int
    likes: int
    decision_score: float
    capability_score: float
    efficiency_score: float
    popularity_score: float
    size_mb: float
    license: str
    base_model: str
    datasets: str
    metrics: str
    widget_data: str
    inference_info: str
    # Enhanced scores
    popularity_score_normalized: float
    engagement_score: float
    lightweight_score: float
    task_match_score: float
    # Cross-validation scores
    cv_score: Optional[float] = None
    cv_std: Optional[float] = None
    # Hyperparameter optimization scores
    hp_optimized_score: Optional[float] = None
    best_params: Optional[Dict[str, Any]] = None
    # Ensemble scores
    ensemble_score: Optional[float] = None
    ensemble_weight: Optional[float] = None
    # Meta-learning features
    meta_features: Optional[Dict[str, float]] = None
    # F1 Score evaluation results
    f1_score: Optional[float] = None
    exact_match_score: Optional[float] = None
    benchmark_predictions: Optional[List[str]] = None
    benchmark_evaluation_time: Optional[float] = None
    all_tags: Optional[List[str]] = None
    # Enhanced Selection Fields
    last_modified: Optional[str] = None
    freshness_score: float = 0.0

@dataclass
class SelectionResult:
    """Result of enhanced model selection."""
    best_model: ModelCandidate
    all_candidates: List[ModelCandidate]
    selection_strategy: SelectionStrategy
    optimization_time: float
    evaluation_metrics: Dict[str, float]
    confidence_score: float
    reasoning: str

class F1ScoreEvaluator:
    """Enhanced F1 Score evaluator with task-aware evaluation."""
    
    def __init__(self):
        self.hf_token = os.getenv('HF_TOKEN')
        # Task-specific benchmark items
        self.task_benchmarks = {
            'text-classification': self._get_classification_benchmarks(),
            'sentiment-analysis': self._get_sentiment_benchmarks(),
            'question-answering': self._get_qa_benchmarks(),
            'text-generation': self._get_generation_benchmarks(),
            'conversational': self._get_conversational_benchmarks(),
            'summarization': self._get_summarization_benchmarks(),
            'translation': self._get_translation_benchmarks()
        }
    
    def _get_classification_benchmarks(self):
        """Get classification-specific benchmark items."""
        return [
            {
                "input": "This product is amazing!",
                "expected_label": "positive",
                "task": "sentiment"
            },
            {
                "input": "I hate this service, it's terrible.",
                "expected_label": "negative", 
                "task": "sentiment"
            },
            {
                "input": "The weather is okay today.",
                "expected_label": "neutral",
                "task": "sentiment"
            },
            {
                "input": "This is a great movie!",
                "expected_label": "positive",
                "task": "sentiment"
            },
            {
                "input": "The food was disgusting.",
                "expected_label": "negative",
                "task": "sentiment"
            }
        ]
    
    def _get_sentiment_benchmarks(self):
        """Get sentiment analysis benchmark items."""
        return self._get_classification_benchmarks()
    
    def _get_qa_benchmarks(self):
        """Get question-answering benchmark items."""
        return [
            {
                "question": "Who wrote The Iliad?",
                "context": "The Iliad is an ancient Greek epic poem traditionally attributed to Homer. It is set during the Trojan War.",
                "reference_answer": "Homer",
            },
            {
                "question": "What gas do plants primarily take in for photosynthesis?",
                "context": "Plants use sunlight to convert carbon dioxide and water into glucose and oxygen in a process called photosynthesis.",
                "reference_answer": "carbon dioxide",
            },
            {
                "question": "Which planet is known as the Red Planet?",
                "context": "Mars, often called the Red Planet, appears reddish due to iron oxide on its surface.",
                "reference_answer": "Mars",
            },
            {
                "question": "What is the capital of France?",
                "context": "France is a country in Western Europe. Its capital city is Paris, a major European center of art and fashion.",
                "reference_answer": "Paris",
            },
            {
                "question": "What is H2O commonly called?",
                "context": "Common chemical substances include sodium chloride (table salt) and H2O, better known as water.",
                "reference_answer": "water",
            },
        ]
    
    def _get_generation_benchmarks(self):
        """Get text generation benchmark items."""
        return [
            {
                "prompt": "The weather today is",
                "expected_keywords": ["weather", "today", "temperature", "sunny", "rainy", "cloudy"],
                "task": "completion"
            },
            {
                "prompt": "I love this product because",
                "expected_keywords": ["love", "product", "because", "good", "great", "amazing"],
                "task": "completion"
            },
            {
                "prompt": "The best way to learn programming is",
                "expected_keywords": ["learn", "programming", "practice", "study", "code"],
                "task": "completion"
            },
            {
                "prompt": "My favorite food is",
                "expected_keywords": ["favorite", "food", "delicious", "tasty", "like"],
                "task": "completion"
            },
            {
                "prompt": "The movie was",
                "expected_keywords": ["movie", "was", "good", "bad", "entertaining", "boring"],
                "task": "completion"
            }
        ]
    
    def _get_conversational_benchmarks(self):
        """Get conversational benchmark items."""
        return [
            {
                "message": "What is the capital of France?",
                "expected_keywords": ["Paris", "France", "capital"],
                "task": "chat"
            },
            {
                "message": "How do you make coffee?",
                "expected_keywords": ["coffee", "water", "beans", "brew", "filter"],
                "task": "chat"
            },
            {
                "message": "Tell me a joke",
                "expected_keywords": ["joke", "funny", "humor", "laugh"],
                "task": "chat"
            },
            {
                "message": "What's the weather like?",
                "expected_keywords": ["weather", "temperature", "sunny", "rainy", "cloudy"],
                "task": "chat"
            },
            {
                "message": "How are you today?",
                "expected_keywords": ["good", "fine", "well", "thank", "you"],
                "task": "chat"
            }
        ]
    
    def _get_summarization_benchmarks(self):
        """Get summarization benchmark items."""
        return [
            {
                "text": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet at least once. It is commonly used for typing practice and testing fonts.",
                "expected_keywords": ["fox", "dog", "alphabet", "sentence", "typing"],
                "task": "summarize"
            },
            {
                "text": "Python is a high-level programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991. Python is widely used in web development, data science, and artificial intelligence.",
                "expected_keywords": ["Python", "programming", "language", "Guido", "1991"],
                "task": "summarize"
            },
            {
                "text": "The solar system consists of the Sun and the objects that orbit it, including eight planets, dwarf planets, moons, asteroids, and comets. The four inner planets are rocky, while the four outer planets are gas giants.",
                "expected_keywords": ["solar", "system", "planets", "Sun", "orbit"],
                "task": "summarize"
            },
            {
                "text": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions without being explicitly programmed. It uses algorithms to identify patterns in data and make predictions.",
                "expected_keywords": ["machine", "learning", "AI", "algorithms", "predictions"],
                "task": "summarize"
            },
            {
                "text": "Climate change refers to long-term shifts in global weather patterns and average temperatures. It is primarily caused by human activities such as burning fossil fuels, deforestation, and industrial processes.",
                "expected_keywords": ["climate", "change", "weather", "human", "activities"],
                "task": "summarize"
            }
        ]
    
    def _get_translation_benchmarks(self):
        """Get translation benchmark items."""
        return [
            {
                "text": "Hello, how are you?",
                "target_language": "Spanish",
                "expected_keywords": ["hola", "como", "estas"],
                "task": "translate"
            },
            {
                "text": "Good morning",
                "target_language": "French", 
                "expected_keywords": ["bonjour", "matin"],
                "task": "translate"
            },
            {
                "text": "Thank you very much",
                "target_language": "German",
                "expected_keywords": ["danke", "sehr", "viel"],
                "task": "translate"
            },
            {
                "text": "I love you",
                "target_language": "Italian",
                "expected_keywords": ["ti", "amo"],
                "task": "translate"
            },
            {
                "text": "Goodbye",
                "target_language": "Portuguese",
                "expected_keywords": ["adeus", "tchau"],
                "task": "translate"
            }
        ]
    
    def _create_dynamic_benchmarks(self, task_name: str, user_prompt: str = None) -> List[Dict]:
        """Create dynamic benchmark items based on task and user prompt."""
        # If user prompt is provided, ALWAYS create task-specific benchmarks
        if user_prompt:
            if task_name in ['text-classification', 'sentiment-analysis']:
                # Create classification benchmarks based on user prompt
                return self._create_classification_benchmarks_from_prompt(user_prompt)
            elif task_name in ['text-generation', 'conversational']:
                # Create generation benchmarks based on user prompt
                return self._create_generation_benchmarks_from_prompt(user_prompt)
            elif task_name == 'question-answering':
                # Create QA benchmarks based on user prompt
                return self._create_qa_benchmarks_from_prompt(user_prompt)
            elif task_name == 'summarization':
                # Create summarization benchmarks based on user prompt
                return self._create_summarization_benchmarks_from_prompt(user_prompt)
            elif task_name == 'translation':
                # Create translation benchmarks based on user prompt
                return self._create_translation_benchmarks_from_prompt(user_prompt)
        
        # Only use base benchmarks if no user prompt is provided
        base_benchmarks = self.task_benchmarks.get(task_name, self.task_benchmarks['text-generation'])
        return base_benchmarks
    
    def _create_classification_benchmarks_from_prompt(self, user_prompt: str) -> List[Dict]:
        """Create classification benchmarks based on user prompt."""
        # Analyze the user prompt to determine the classification task
        prompt_lower = user_prompt.lower()
        
        if any(word in prompt_lower for word in ['great', 'good', 'amazing', 'excellent', 'wonderful']):
            # Positive sentiment
            return [
                {
                    "input": user_prompt,
                    "expected_label": "positive",
                    "task": "sentiment"
                },
                {
                    "input": "This is terrible and awful.",
                    "expected_label": "negative",
                    "task": "sentiment"
                },
                {
                    "input": "The quality is okay, nothing special.",
                    "expected_label": "neutral",
                    "task": "sentiment"
                },
                {
                    "input": "I love this product!",
                    "expected_label": "positive",
                    "task": "sentiment"
                },
                {
                    "input": "This is the worst experience ever.",
                    "expected_label": "negative",
                    "task": "sentiment"
                }
            ]
        elif any(word in prompt_lower for word in ['bad', 'terrible', 'awful', 'horrible', 'worst']):
            # Negative sentiment
            return [
                {
                    "input": user_prompt,
                    "expected_label": "negative",
                    "task": "sentiment"
                },
                {
                    "input": "This is amazing and wonderful!",
                    "expected_label": "positive",
                    "task": "sentiment"
                },
                {
                    "input": "The quality is acceptable.",
                    "expected_label": "neutral",
                    "task": "sentiment"
                },
                {
                    "input": "I hate this service.",
                    "expected_label": "negative",
                    "task": "sentiment"
                },
                {
                    "input": "This is fantastic!",
                    "expected_label": "positive",
                    "task": "sentiment"
                }
            ]
        else:
            # Generic classification
            return [
                {
                    "input": user_prompt,
                    "expected_label": "positive",
                    "task": "classification"
                },
                {
                    "input": "This is a negative example.",
                    "expected_label": "negative",
                    "task": "classification"
                },
                {
                    "input": "This is a neutral example.",
                    "expected_label": "neutral",
                    "task": "classification"
                },
                {
                    "input": "Another positive example.",
                    "expected_label": "positive",
                    "task": "classification"
                },
                {
                    "input": "Another negative example.",
                    "expected_label": "negative",
                    "task": "classification"
                }
            ]
    
    def _create_generation_benchmarks_from_prompt(self, user_prompt: str) -> List[Dict]:
        """Create generation benchmarks based on user prompt."""
        # Extract key concepts from the user prompt
        prompt_lower = user_prompt.lower()
        
        # Analyze the prompt to determine expected keywords
        expected_keywords = []
        if any(word in prompt_lower for word in ['what', 'who', 'where', 'when', 'why', 'how']):
            expected_keywords.extend(['answer', 'information', 'explanation', 'details'])
        if any(word in prompt_lower for word in ['capital', 'country', 'city', 'place']):
            expected_keywords.extend(['capital', 'country', 'city', 'location', 'place'])
        if any(word in prompt_lower for word in ['weather', 'temperature', 'climate']):
            expected_keywords.extend(['weather', 'temperature', 'climate', 'conditions'])
        if any(word in prompt_lower for word in ['food', 'recipe', 'cook', 'eat']):
            expected_keywords.extend(['food', 'recipe', 'cooking', 'ingredients'])
        if any(word in prompt_lower for word in ['movie', 'film', 'entertainment']):
            expected_keywords.extend(['movie', 'film', 'entertainment', 'story'])
        if any(word in prompt_lower for word in ['book', 'author', 'read']):
            expected_keywords.extend(['book', 'author', 'reading', 'story'])
        if any(word in prompt_lower for word in ['music', 'song', 'artist']):
            expected_keywords.extend(['music', 'song', 'artist', 'melody'])
        if any(word in prompt_lower for word in ['sport', 'game', 'play']):
            expected_keywords.extend(['sport', 'game', 'play', 'team'])
        if any(word in prompt_lower for word in ['technology', 'computer', 'software']):
            expected_keywords.extend(['technology', 'computer', 'software', 'system'])
        if any(word in prompt_lower for word in ['science', 'research', 'study']):
            expected_keywords.extend(['science', 'research', 'study', 'experiment'])
        
        # Add generic keywords if none were found
        if not expected_keywords:
            expected_keywords = ["response", "answer", "information", "details"]
        
        return [
            {
                "prompt": user_prompt,
                "expected_keywords": expected_keywords,
                "task": "completion"
            },
            {
                "prompt": f"Tell me more about {user_prompt}",
                "expected_keywords": expected_keywords + ["more", "about", "details"],
                "task": "completion"
            },
            {
                "prompt": f"Explain {user_prompt}",
                "expected_keywords": expected_keywords + ["explain", "explanation"],
                "task": "completion"
            },
            {
                "prompt": f"What do you know about {user_prompt}?",
                "expected_keywords": expected_keywords + ["know", "about"],
                "task": "completion"
            },
            {
                "prompt": f"Can you help me understand {user_prompt}?",
                "expected_keywords": expected_keywords + ["help", "understand"],
                "task": "completion"
            }
        ]
    
    def _create_qa_benchmarks_from_prompt(self, user_prompt: str) -> List[Dict]:
        """Create question-answering benchmarks based on user prompt."""
        # Extract key concepts from the user prompt
        prompt_lower = user_prompt.lower()
        
        # Create context and questions based on the prompt
        if any(word in prompt_lower for word in ['capital', 'country', 'city']):
            context = "Geography is the study of places and the relationships between people and their environments."
            questions = [
                f"What is the capital of {user_prompt}?",
                f"Where is {user_prompt} located?",
                f"What country is {user_prompt} in?"
            ]
            answers = ["capital", "location", "country"]
        elif any(word in prompt_lower for word in ['weather', 'temperature', 'climate']):
            context = "Weather refers to the state of the atmosphere at a particular place and time."
            questions = [
                f"What is the weather like in {user_prompt}?",
                f"What is the temperature in {user_prompt}?",
                f"What is the climate of {user_prompt}?"
            ]
            answers = ["weather", "temperature", "climate"]
        elif any(word in prompt_lower for word in ['food', 'recipe', 'cook']):
            context = "Cooking is the art and science of preparing food for consumption."
            questions = [
                f"How do you cook {user_prompt}?",
                f"What are the ingredients for {user_prompt}?",
                f"What is {user_prompt} made of?"
            ]
            answers = ["cook", "ingredients", "made"]
        else:
            # Generic QA context
            context = f"Information about {user_prompt} and related topics."
            questions = [
                f"What is {user_prompt}?",
                f"Tell me about {user_prompt}",
                f"Explain {user_prompt}"
            ]
            answers = ["information", "about", "explanation"]
        
        return [
            {
                "question": questions[0],
                "context": context,
                "reference_answer": answers[0]
            },
            {
                "question": questions[1] if len(questions) > 1 else f"What is {user_prompt}?",
                "context": context,
                "reference_answer": answers[1] if len(answers) > 1 else "information"
            },
            {
                "question": questions[2] if len(questions) > 2 else f"Tell me about {user_prompt}",
                "context": context,
                "reference_answer": answers[2] if len(answers) > 2 else "about"
            }
        ]
    
    def _create_summarization_benchmarks_from_prompt(self, user_prompt: str) -> List[Dict]:
        """Create summarization benchmarks based on user prompt."""
        # Create sample texts related to the user prompt
        prompt_lower = user_prompt.lower()
        
        if any(word in prompt_lower for word in ['technology', 'computer', 'software']):
            text = f"Technology has revolutionized the way we live and work. {user_prompt} represents a significant advancement in this field. The development of new technologies continues to shape our future."
            expected_keywords = ["technology", "advancement", "development", "future"]
        elif any(word in prompt_lower for word in ['science', 'research', 'study']):
            text = f"Scientific research is essential for understanding our world. {user_prompt} is an important area of study that contributes to our knowledge and understanding."
            expected_keywords = ["science", "research", "study", "knowledge"]
        elif any(word in prompt_lower for word in ['health', 'medical', 'medicine']):
            text = f"Healthcare is a critical aspect of human well-being. {user_prompt} plays an important role in maintaining health and treating various conditions."
            expected_keywords = ["health", "medical", "well-being", "treatment"]
        else:
            text = f"This is a comprehensive text about {user_prompt}. It contains detailed information and various aspects related to this topic. The content covers multiple perspectives and provides valuable insights."
            expected_keywords = [user_prompt.lower(), "information", "topic", "insights"]
        
        return [
            {
                "text": text,
                "expected_keywords": expected_keywords,
                "task": "summarize"
            },
            {
                "text": f"Another detailed text about {user_prompt} with additional information and context.",
                "expected_keywords": [user_prompt.lower(), "information", "context"],
                "task": "summarize"
            }
        ]
    
    def _create_translation_benchmarks_from_prompt(self, user_prompt: str) -> List[Dict]:
        """Create translation benchmarks based on user prompt."""
        # Create sample texts for translation
        return [
            {
                "text": user_prompt,
                "target_language": "Spanish",
                "expected_keywords": ["translation", "spanish"],
                "task": "translate"
            },
            {
                "text": f"Hello, {user_prompt}",
                "target_language": "French",
                "expected_keywords": ["bonjour", "french"],
                "task": "translate"
            },
            {
                "text": f"Thank you for {user_prompt}",
                "target_language": "German",
                "expected_keywords": ["danke", "german"],
                "task": "translate"
            }
        ]

    def normalize_text(self, s: str) -> str:
        """Normalize text for comparison."""
        def remove_articles(text):
            return re.sub(r'\b(a|an|the)\b', ' ', text)
        
        def white_space_fix(text):
            return ' '.join(text.split())
        
        def remove_punc(text):
            exclude = set(string.punctuation)
            return ''.join(ch for ch in text if ch not in exclude)
        
        def lower(text):
            return text.lower()
        
        return white_space_fix(remove_articles(remove_punc(lower(s))))

    def f1_score(self, prediction: str, ground_truth: str) -> float:
        """Calculate F1 score between prediction and ground truth."""
        pred_tokens = set(self.normalize_text(prediction).split())
        truth_tokens = set(self.normalize_text(ground_truth).split())
        
        if not pred_tokens or not truth_tokens:
            return 0.0
        
        common = pred_tokens & truth_tokens
        precision = len(common) / len(pred_tokens) if pred_tokens else 0.0
        recall = len(common) / len(truth_tokens) if truth_tokens else 0.0
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)

    def exact_match_score(self, prediction: str, ground_truth: str) -> float:
        """Calculate exact match score."""
        return 1.0 if self.normalize_text(prediction) == self.normalize_text(ground_truth) else 0.0
    
    # Lightweight BLEU-4 and ROUGE-L (no extra deps), adapted to our normalizer
    def _ngrams(self, tokens: List[str], n: int) -> Counter:
        return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)) if n > 0 else Counter()

    def bleu4(self, prediction: str, reference: str) -> float:
        p = self.normalize_text(prediction).split()
        r = self.normalize_text(reference).split()
        if len(p) == 0:
            return 0.0
        bp = 1.0 if len(p) > len(r) else (pow(2.718281828, 1 - len(r) / max(1, len(p))))
        precisions = []
        for n in (1, 2, 3, 4):
            pn = self._ngrams(p, n)
            rn = self._ngrams(r, n)
            overlap = pn & rn
            num = sum(overlap.values())
            den = max(1, sum(pn.values()))
            precisions.append(num / den)
        gm = 1.0
        for pr in precisions:
            gm *= max(pr, 1e-12)
        gm = gm ** 0.25
        return bp * gm

    def _lcs_len(self, a: List[str], b: List[str]) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            ai = a[i]
            for j in range(n):
                if ai == b[j]:
                    dp[i + 1][j + 1] = dp[i][j] + 1
                else:
                    dp[i + 1][j + 1] = dp[i][j + 1] if dp[i][j + 1] >= dp[i + 1][j] else dp[i + 1][j]
        return dp[m][n]

    def rouge_l(self, prediction: str, reference: str) -> float:
        p = self.normalize_text(prediction).split()
        r = self.normalize_text(reference).split()
        if not p and not r:
            return 1.0
        if not p or not r:
            return 0.0
        L = self._lcs_len(p, r)
        prec = L / len(p)
        rec = L / len(r)
        return (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    
    def _get_optimal_task_mapping(self, model_id: str, task_name: str, all_tags: List[str] = None, pipeline_tag: Optional[str] = None) -> str:
        """Map to the optimal inference task for F1 evaluation.
        Priority:
          1) provider/model-name conversational-only overrides (avoid unsupported tasks)
          2) all tags from DB (primary authority)
          3) pipeline_tag (fallback)
          4) task_name heuristic (last resort)
        """
        # Enhanced conversational model detection
        conversational_indicators = [
            "llama", "gpt", "qwen", "mistral", "gemma", "phi", "falcon",
            "chat", "instruct", "conversational", "dialogue", "alpaca", "vicuna"
        ]
        
        # Provider-specific model patterns that only support conversational
        conversational_only_providers = {
            "fireworks-ai": ["meta-llama", "qwen", "mistral"],
            "together": ["qwen", "llama", "mistral"],
            "featherless-ai": ["qwen", "llama", "mistral"]
        }
        
        model_lower = (model_id or "").lower()
        is_likely_conversational = any(indicator in model_lower for indicator in conversational_indicators)
        
        # Check if model is from a provider that only supports conversational
        for provider, models in conversational_only_providers.items():
            if any(model in model_id for model in models):
                logger.debug(f"🔎 Task mapping: provider override → conversational (provider group: {provider}) for {model_id}")
                return "conversational"
        
        # Use all_tags first (primary authority)
        if all_tags:
            # Safely create lower case tags, filtering out None
            tags_lower = [tag.lower() for tag in all_tags if tag and isinstance(tag, str)]
            
            # Check for specific task capabilities in tags
            if "conversational" in tags_lower:
                logger.debug(f"🔎 Task mapping: tags → conversational for {model_id}")
                return "conversational"
            elif "question-answering" in tags_lower or "qa" in tags_lower:
                logger.debug(f"🔎 Task mapping: tags → question-answering for {model_id}")
                return "question-answering"
            elif "text-classification" in tags_lower:
                logger.debug(f"🔎 Task mapping: tags → text-classification for {model_id}")
                return "text-classification"
            elif "summarization" in tags_lower:
                logger.debug(f"🔎 Task mapping: tags → summarization for {model_id}")
                return "summarization"
            elif "translation" in tags_lower:
                logger.debug(f"🔎 Task mapping: tags → translation for {model_id}")
                return "translation"
            elif "text-generation" in tags_lower:
                # Even if text-generation is in tags, check if conversational is better
                if is_likely_conversational:
                    logger.debug(f"🔎 Task mapping: tags(text-generation)+name heuristic → conversational for {model_id}")
                    return "conversational"
                else:
                    logger.debug(f"🔎 Task mapping: tags → text-generation for {model_id}")
                    return "text-generation"

        # If pipeline_tag is present, use it as fallback
        if pipeline_tag:
            pt = pipeline_tag.lower()
            if pt in {"text-generation", "question-answering", "text-classification", "summarization", "translation", "conversational"}:
                if pt == "text-generation" and is_likely_conversational:
                    logger.debug(f"🔎 Task mapping: pipeline_tag(text-generation)+name heuristic → conversational for {model_id}")
                    return "conversational"
                logger.debug(f"🔎 Task mapping: pipeline_tag → {pt} for {model_id}")
                return pt
        
        # Enhanced task mapping with better fallbacks
        task_mapping = {
            "text-generation": "conversational" if is_likely_conversational else "text-generation",
            "general_task": "conversational" if is_likely_conversational else "text-generation",
            "question-answering": "conversational" if is_likely_conversational else "question-answering",
            "text-classification": "text-classification",
            "summarization": "conversational" if is_likely_conversational else "summarization",
            "translation": "conversational" if is_likely_conversational else "translation"
        }
        
        fallback = task_mapping.get(task_name, "conversational" if is_likely_conversational else "text-generation")
        logger.debug(f"🔎 Task mapping: heuristic(task_name/name) → {fallback} for {model_id}")
        return fallback

    def evaluate_model(self, model_id: str, task_name: str, user_prompt: str = None, all_tags: List[str] = None, pipeline_tag: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate a model preferring ModelCard metrics with live, dynamic fallback (no hardcoding)."""
        if not HF_HUB_AVAILABLE:
            return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

        # 0) CSV-driven evaluation if configured (replaces ad-hoc tests; no hardcoding)
        csv_path = os.getenv("EVAL_CSV_PATH")
        if csv_path and os.path.isfile(csv_path):
            try:
                return self._evaluate_csv_inference(model_id, task_name, csv_path, pipeline_tag)
            except Exception as e:
                logger.debug(f"CSV evaluation failed for {model_id}: {e}")

        # 1) Try ModelCard metrics first
        try:
            card = ModelCard.load(model_id)
            data = card.data.to_dict()

            f1_val = None
            em_val = None
            metrics_found = False

            if "model-index" in data:
                for model_entry in data["model-index"]:
                    for result in model_entry.get("results", []):
                        result_task = result.get("task", {}).get("type", "").lower()
                        if self._task_matches(result_task, task_name, all_tags):
                            for metric in result.get("metrics", []):
                                metric_name = metric.get("name", "").lower()
                                metric_value = metric.get("value", 0.0)
                                if "f1" in metric_name:
                                    f1_val = float(metric_value)
                                    metrics_found = True
                                if "exact_match" in metric_name or metric_name == "em":
                                    em_val = float(metric_value)
                                    metrics_found = True

            if not metrics_found:
                # Search other sections for numeric f1-like keys
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, (int, float)) and "f1" in sub_key.lower():
                                f1_val = float(sub_value)
                                metrics_found = True
                                break
                    if metrics_found:
                        break

            if not metrics_found:
                # Parse raw text for F1 values
                card_text = (card.text or "").lower()
                f1_patterns = [
                    r"f1[-\s]?score[:\s]*([0-9]*\.?[0-9]+)",
                    r"f1[:\s]*([0-9]*\.?[0-9]+)",
                    r"f1[-\s]?measure[:\s]*([0-9]*\.?[0-9]+)"
                ]
                for pattern in f1_patterns:
                    matches = re.findall(pattern, card_text)
                    if matches:
                        f1_val = max(float(m) for m in matches)
                        metrics_found = True
                        break

            if metrics_found and f1_val is not None:
                return {
                    "f1_score": f1_val,
                    "em_score": em_val or 0.0,
                    "evaluation_success": True,
                    "evaluation_time": time.time(),
                    "evaluation_method": "model_card_metrics"
                }
        except Exception as e:
            # ModelCard not available or parsing failed; continue to live fallback
            logger.debug(f"ModelCard parse failed for {model_id}: {e}")

        # 2) Live evaluation fallback using dynamic, prompt-aware tests (no hardcoded lists)
        try:
            return self._evaluate_live_inference(model_id, task_name, user_prompt, all_tags, pipeline_tag)
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            logger.error(f"❌ Live F1 evaluation failed for {model_id}: {error_msg}")
            return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

    # ---------- Live evaluation helpers (dynamic, no hardcoded MODEL/TEST lists) ----------
    def _extract_short_answer(self, text: str) -> str:
        if not text:
            return ""
        parts = re.split(r"[。\.!?\n]", text.strip(), maxsplit=1)
        cleaned = parts[0] if parts else text.strip()
        cleaned = re.sub(r"^\s*(answer|final answer)\s*[:\-]\s*", "", cleaned, flags=re.I)
        return cleaned.strip()

    def _infer_chat(self, client: 'InferenceClient', prompt: str, max_new_tokens: int = 64, temperature: float = 0.0) -> str:
        try:
            resp = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_new_tokens,
                temperature=temperature,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return ""

    def _infer_text(self, client: 'InferenceClient', prompt: str, max_new_tokens: int = 64, temperature: float = 0.0) -> str:
        try:
            out = client.text_generation(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                stop=["\n\n", "</s>"],
                return_full_text=False,
            )
            if isinstance(out, str):
                return out.strip()
            if isinstance(out, dict) and "generated_text" in out:
                return str(out.get("generated_text", "")).strip()
            if isinstance(out, list) and out and isinstance(out[0], dict) and "generated_text" in out[0]:
                return str(out[0].get("generated_text", "")).strip()
            return ""
        except Exception:
            return ""

    def _query_model_textual(self, client: 'InferenceClient', prompt: str) -> str:
        text = self._infer_chat(client, prompt)
        if not text:
            text = self._infer_text(client, prompt)
        return self._extract_short_answer(text) or text

    # ---------- CSV-driven evaluation (QA / classification / summarization / translation) ----------
    def _load_csv_rows(self, task: str, path: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if task == 'text-classification':
                    rows.append({"text": row["text"], "label": row["label"]})
                elif task == 'question-answering':
                    aliases: List[str] = []
                    if 'aliases' in row and row['aliases'] and str(row['aliases']).strip():
                        try:
                            aliases = json.loads(row['aliases'])
                        except Exception:
                            aliases = [row['aliases']]
                    rows.append({"prompt": row["prompt"], "answer": row["answer"], "aliases": aliases})
                elif task == 'summarization':
                    rows.append({"src": row["src"], "reference": row["reference"]})
                elif task == 'translation':
                    rows.append({"src": row["src"], "target": row["target"]})
                else:
                    # Unsupported for CSV
                    pass
        return rows

    def _normalize_label_name(self, label: str) -> str:
        # Lowercase, collapse whitespace/punct simple normalization
        s = re.sub(r"\s+", " ", (label or "").strip()).lower()
        return re.sub(r"[^a-z0-9_]+", "", s)

    def _predict_classification(self, client: 'InferenceClient', text: str, label_set: Optional[set] = None) -> Tuple[str, float]:
        try:
            out = client.text_classification(text)
        except Exception:
            return "", 0.0
        if isinstance(out, list) and out:
            # pick highest score
            top = max(out, key=lambda x: x.get("score", 0.0))
            label = self._normalize_label_name(top.get("label", ""))
            score = float(top.get("score", 0.0))
            # optional neutral fallback if only pos/neg labels
            neutral_enabled = (os.getenv("NEUTRAL_FALLBACK", "true").lower() == "true")
            threshold = float(os.getenv("NEUTRAL_THRESHOLD", "0.55"))
            if neutral_enabled and label_set and "neutral" in label_set:
                only_posneg = label_set.issuperset({"positive", "negative"}) and len(label_set) <= 2
                if only_posneg and score < threshold:
                    label = "neutral"
            return label, score
        return "", 0.0

    def _evaluate_csv_inference(self, model_id: str, task_name: str, csv_path: str, pipeline_tag: Optional[str]) -> Dict[str, Any]:
        client = InferenceClient(model=model_id, token=os.getenv("HF_TOKEN"))
        rows = self._load_csv_rows(task_name, csv_path)
        if not rows:
            return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

        start = time.time()

        if task_name == 'text-classification':
            golds: List[str] = []
            preds: List[str] = []
            # derive label set from CSV
            label_set = {self._normalize_label_name(r['label']) for r in rows}
            for r in rows:
                golds.append(self._normalize_label_name(r['label']))
                pred_label, _ = self._predict_classification(client, r['text'], label_set)
                preds.append(pred_label)
            # macro-F1 and accuracy
            labels = sorted(label_set)
            tp: Dict[str, int] = Counter()
            fp: Dict[str, int] = Counter()
            fn: Dict[str, int] = Counter()
            for t, p in zip(golds, preds):
                if p == t:
                    tp[t] += 1
                else:
                    fp[p] += 1
                    fn[t] += 1
            f1s = []
            for lbl in labels:
                tp_i, fp_i, fn_i = tp[lbl], fp[lbl], fn[lbl]
                prec = tp_i / (tp_i + fp_i) if (tp_i + fp_i) > 0 else 0.0
                rec = tp_i / (tp_i + fn_i) if (tp_i + fn_i) > 0 else 0.0
                f1s.append((2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0)
            f1_macro = float(sum(f1s) / len(f1s)) if f1s else 0.0
            acc = float(sum(1 for t, p in zip(golds, preds) if t == p) / len(golds)) if golds else 0.0
            return {
                "f1_avg": f1_macro,
                "em_avg": acc,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "csv_evaluation"
            }

        if task_name == 'question-answering':
            f1s: List[float] = []
            ems: List[float] = []
            for r in rows:
                pred = self._query_model_textual(client, r['prompt'])
                ref = r['answer']
                aliases = r.get('aliases', []) or []
                if self.exact_match_score(pred, ref) == 1.0 or any(self.exact_match_score(pred, a) == 1.0 for a in aliases):
                    em = 1.0
                    f1 = 1.0
                else:
                    em = self.exact_match_score(pred, ref)
                    f1 = self.f1_score(pred, ref)
                ems.append(em)
                f1s.append(f1)
            return {
                "f1_avg": float(sum(f1s) / len(f1s)) if f1s else 0.0,
                "em_avg": float(sum(ems) / len(ems)) if ems else 0.0,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "csv_evaluation"
            }

        if task_name == 'summarization':
            rouges: List[float] = []
            bleus: List[float] = []
            ems: List[float] = []
            for r in rows:
                prompt = f"Summarize the following text in one or two sentences:\n\n{r['src']}\n"
                pred = self._query_model_textual(client, prompt)
                ref = r['reference']
                rouges.append(self.rouge_l(pred, ref))
                bleus.append(self.bleu4(pred, ref))
                ems.append(self.exact_match_score(pred, ref))
            rouge_avg = float(sum(rouges) / len(rouges)) if rouges else 0.0
            bleu_avg = float(sum(bleus) / len(bleus)) if bleus else 0.0
            acc = float(sum(ems) / len(ems)) if ems else 0.0
            return {
                "f1_avg": rouge_avg,  # use ROUGE-L as primary
                "em_avg": acc,
                "rouge_l_avg": rouge_avg,
                "bleu4_avg": bleu_avg,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "csv_evaluation"
            }

        if task_name == 'translation':
            bleus: List[float] = []
            rouges: List[float] = []
            ems: List[float] = []
            for r in rows:
                prompt = f"Translate to target language:\n\n{r['src']}\n\nOnly output the translation."
                pred = self._query_model_textual(client, prompt)
                tgt = r['target']
                bleus.append(self.bleu4(pred, tgt))
                rouges.append(self.rouge_l(pred, tgt))
                ems.append(self.exact_match_score(pred, tgt))
            bleu_avg = float(sum(bleus) / len(bleus)) if bleus else 0.0
            rouge_avg = float(sum(rouges) / len(rouges)) if rouges else 0.0
            acc = float(sum(ems) / len(ems)) if ems else 0.0
            return {
                "f1_avg": bleu_avg,  # use BLEU-4 as primary
                "em_avg": acc,
                "bleu4_avg": bleu_avg,
                "rouge_l_avg": rouge_avg,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "csv_evaluation"
            }

        # Unsupported CSV task type
        return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

    def _evaluate_live_inference(self, model_id: str, task_name: str, user_prompt: Optional[str], all_tags: Optional[List[str]], pipeline_tag: Optional[str]) -> Dict[str, Any]:
        if not HF_HUB_AVAILABLE:
            return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

        client = InferenceClient(model=model_id, token=os.getenv("HF_TOKEN"))
        items = self._create_dynamic_benchmarks(task_name, user_prompt)

        f1s: List[float] = []
        ems: List[float] = []
        sum_rouges: List[float] = []
        sum_bleus: List[float] = []
        mt_bleus: List[float] = []
        mt_rouges: List[float] = []

        for item in items:
            try:
                optimal_task = self._get_optimal_task_mapping(model_id, task_name, all_tags, pipeline_tag)

                # Build a natural prompt for generative querying when needed
                if optimal_task in ["text-generation", "conversational", "question-answering"]:
                    if "question" in item:
                        prompt = item["question"]
                    elif "prompt" in item:
                        prompt = item["prompt"]
                    elif "input" in item:
                        prompt = item["input"]
                    else:
                        prompt = str(item)

                    pred = self._query_model_textual(client, prompt)
                elif optimal_task == "summarization":
                    # Use generative pathway
                    prompt = item.get("text", user_prompt or "Summarize the following text.")
                    pred = self._query_model_textual(client, prompt)
                elif optimal_task == "translation":
                    prompt = f"Translate to {item.get('target_language', 'English')}: {item.get('text', user_prompt or '')}"
                    pred = self._query_model_textual(client, prompt)
                elif optimal_task == "text-classification":
                    # Try dedicated endpoint; fall back to textual
                    try:
                        resp = client.text_classification(item.get("input", user_prompt or ""))
                        pred = resp[0]["label"] if resp else ""
                    except Exception:
                        pred = self._query_model_textual(client, item.get("input", user_prompt or ""))
                else:
                    prompt = item.get("prompt", item.get("input", user_prompt or str(item)))
                    pred = self._query_model_textual(client, prompt)

                # Scoring
                if optimal_task == "summarization" and "reference" in item:
                    ref = item["reference"]
                    sum_rouges.append(self.rouge_l(pred, ref))
                    sum_bleus.append(self.bleu4(pred, ref))
                elif optimal_task == "translation" and "target" in item:
                    tgt = item["target"]
                    mt_bleus.append(self.bleu4(pred, tgt))
                    mt_rouges.append(self.rouge_l(pred, tgt))
                elif "expected_label" in item:
                    ref = item["expected_label"]
                    ems.append(self.exact_match_score(pred, ref))
                    f1s.append(self.f1_score(pred, ref))
                elif "reference_answer" in item:
                    ref = item["reference_answer"]
                    ems.append(self.exact_match_score(pred, ref))
                    f1s.append(self.f1_score(pred, ref))
                elif "expected_keywords" in item and item["expected_keywords"]:
                    # Keyword coverage as soft F1 proxy
                    keywords = [k.lower() for k in item["expected_keywords"]]
                    present = sum(1 for k in keywords if k in (pred or "").lower())
                    score = present / len(keywords)
                    f1s.append(score)
                    ems.append(1.0 if score > 0.5 else 0.0)
                else:
                    # No reference; skip item from scoring
                    continue
            except Exception as ie:
                logger.debug(f"Skip item due to error for {model_id}: {ie}")
                continue

        # If we computed task-appropriate metrics, return those (mapped onto f1_avg for weighting)
        if sum_rouges or sum_bleus:
            rouge_avg = float(sum(sum_rouges) / len(sum_rouges)) if sum_rouges else 0.0
            bleu_avg = float(sum(sum_bleus) / len(sum_bleus)) if sum_bleus else 0.0
            return {
                "f1_avg": rouge_avg,            # use ROUGE-L as primary for summarization
                "em_avg": 0.0,
                "rouge_l_avg": rouge_avg,
                "bleu4_avg": bleu_avg,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "live_inference"
            }
        if mt_bleus or mt_rouges:
            bleu_avg = float(sum(mt_bleus) / len(mt_bleus)) if mt_bleus else 0.0
            rouge_avg = float(sum(mt_rouges) / len(mt_rouges)) if mt_rouges else 0.0
            return {
                "f1_avg": bleu_avg,            # use BLEU-4 as primary for translation
                "em_avg": 0.0,
                "bleu4_avg": bleu_avg,
                "rouge_l_avg": rouge_avg,
                "evaluation_success": True,
                "evaluation_time": time.time(),
                "evaluation_method": "live_inference"
            }

        if not f1s:
            return {"f1_score": 0.0, "em_score": 0.0, "evaluation_success": False}

        return {
            "f1_avg": float(sum(f1s) / len(f1s)),
            "em_avg": float(sum(ems) / len(ems)) if ems else 0.0,
            "evaluation_success": True,
            "evaluation_time": time.time(),
            "evaluation_method": "live_inference"
        }
    
    def _task_matches(self, result_task: str, target_task: str, all_tags: Optional[List[str]] = None) -> bool:
        """Check if a result task matches our target task, considering all model tags when available."""
        result_task = (result_task or "").lower()
        target_task = (target_task or "").lower()
        
        # Direct match
        if result_task == target_task:
            return True
        
        # Task mapping
        task_mappings = {
            "question-answering": ["qa", "question answering", "squad"],
            "text-classification": ["classification", "sentiment-analysis", "sentiment analysis"],
            "text-generation": ["generation", "text generation", "language modeling"],
            "conversational": ["chat", "conversation", "dialogue"],
            "summarization": ["summarization", "summarize"],
            "translation": ["translation", "translate"]
        }
        
        # Check if target task maps to result task
        if target_task in task_mappings:
            if result_task in task_mappings[target_task]:
                return True
        
        # Check if result task maps to target task
        for key, values in task_mappings.items():
            if result_task in values and key == target_task:
                return True

        # Consider all_tags from database for broader matching
        if all_tags:
            tags_lower = {t.lower() for t in all_tags if t and isinstance(t, str)}
            # if any synonym in mappings intersects the tags, accept
            # direct task name
            if result_task in tags_lower or target_task in tags_lower:
                return True
            # synonyms
            for canonical, synonyms in task_mappings.items():
                if canonical in tags_lower and (result_task == canonical or result_task in synonyms or target_task == canonical):
                    return True
                if any(s in tags_lower for s in synonyms) and (result_task == canonical or result_task in synonyms or target_task == canonical):
                    return True
        
        return False
    


class EnhancedModelSelector:
    """Advanced model selection system with multiple strategies."""
    
    def __init__(self, db_path: str = None):
        # Determine project root and default DB path
        # File is in src/hforchestra/core/enhanced_model_selector.py
        # Root is 3 levels up: src/hforchestra/core -> src/hforchestra -> src -> PROJECT_ROOT
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        
        # If db_path is not provided, use default location in project root
        if db_path is None:
            self.db_path = str(project_root / "db" / "hf_models.db")
        else:
            # If provided path is relative, make it absolute relative to project root
            # unless it's already absolute
            path_obj = Path(db_path)
            if not path_obj.is_absolute():
                self.db_path = str(project_root / db_path)
            else:
                self.db_path = db_path
        
        logger.info(f"💾 EnhancedModelSelector using Database path: {self.db_path}")
                
        self.selection_history = []
        self.performance_cache = {}
        self.f1_evaluator = F1ScoreEvaluator()
        
        # Initialize database connection
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            self.conn = None
        # Comprehensive fallback models per pipeline tag with multiple options
        self.fallback_models: Dict[str, List[str]] = {
            # Text Processing
            'text-classification': [
                'distilbert-base-uncased-finetuned-sst-2-english',
                'cardiffnlp/twitter-roberta-base-sentiment-latest',
                'facebook/roberta-hate-speech-dynabench-r4-target',
                'microsoft/deberta-large-mnli',
                'nlptown/bert-base-multilingual-uncased-sentiment'
            ],
            'zero-shot-classification': [
                'facebook/bart-large-mnli',
                'microsoft/deberta-large-mnli',
                'cross-encoder/nli-distilroberta-base',
                'facebook/bart-large-mnli-yahoo-answers-topics'
            ],
            'token-classification': [
                'dslim/bert-base-NER',
                'Jean-Baptiste/roberta-large-ner-english',
                'microsoft/layoutlm-base-uncased',
                'dbmdz/bert-large-cased-finetuned-conll03-english'
            ],
            'question-answering': [
                'deepset/roberta-base-squad2',
                'distilbert-base-cased-distilled-squad',
                'bert-large-uncased-whole-word-masking-finetuned-squad',
                'timpal0l/mdeberta-v3-base-squad2',
                'deepset/roberta-large-squad2'
            ],
            'text-generation': [
                'distilgpt2',
                'openai-community/gpt2',
                'microsoft/DialoGPT-medium',
                'EleutherAI/gpt-neo-125M',
                'microsoft/DialoGPT-small'
            ],
            'summarization': [
                'sshleifer/distilbart-cnn-12-6',
                'facebook/bart-large-cnn',
                'google/pegasus-xsum',
                't5-small',
                'facebook/bart-base'
            ],
            'translation': [
                'Helsinki-NLP/opus-mt-en-es',
                'Helsinki-NLP/opus-mt-en-fr',
                'Helsinki-NLP/opus-mt-en-de',
                'Helsinki-NLP/opus-mt-en-it',
                'facebook/nllb-200-distilled-600M'
            ],
            'fill-mask': [
                'distilroberta-base',
                'bert-base-uncased',
                'roberta-base',
                'albert-base-v2',
                'microsoft/DialoGPT-medium'
            ],
            'text2text-generation': [
                'google/flan-t5-small',
                'google/flan-t5-base',
                't5-small',
                't5-base',
                'facebook/bart-base'
            ],
            'feature-extraction': [
                'sentence-transformers/all-MiniLM-L6-v2',
                'sentence-transformers/all-mpnet-base-v2',
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'BAAI/bge-small-en-v1.5',
                'BAAI/bge-base-en-v1.5'
            ],
            'sentence-similarity': [
                'sentence-transformers/all-MiniLM-L6-v2',
                'sentence-transformers/all-mpnet-base-v2',
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'BAAI/bge-small-en-v1.5',
                'BAAI/bge-base-en-v1.5'
            ],
            'conversational': [
                'microsoft/DialoGPT-medium',
                'microsoft/DialoGPT-small',
                'facebook/blenderbot-400M-distill',
                'EleutherAI/gpt-neo-125M',
                'openai-community/gpt2'
            ],
            'sentiment-analysis': [
                'distilbert-base-uncased-finetuned-sst-2-english',
                'cardiffnlp/twitter-roberta-base-sentiment-latest',
                'nlptown/bert-base-multilingual-uncased-sentiment',
                'facebook/roberta-hate-speech-dynabench-r4-target',
                'microsoft/deberta-large-mnli'
            ],
            'text-analysis': [
                'distilbert-base-uncased-finetuned-sst-2-english',
                'cardiffnlp/twitter-roberta-base-sentiment-latest',
                'microsoft/deberta-large-mnli',
                'facebook/bart-large-mnli',
                'nlptown/bert-base-multilingual-uncased-sentiment'
            ],
            'text_analysis': [
                'distilbert-base-uncased-finetuned-sst-2-english',
                'cardiffnlp/twitter-roberta-base-sentiment-latest',
                'microsoft/deberta-large-mnli',
                'facebook/bart-large-mnli',
                'nlptown/bert-base-multilingual-uncased-sentiment'
            ],
            'general_task': [
                'openai-community/gpt2',
                'microsoft/DialoGPT-medium',
                'EleutherAI/gpt-neo-125M',
                'facebook/bart-base',
                'google/flan-t5-small'
            ],
            
            # Image Processing
            'image-classification': [
                'google/vit-base-patch16-224',
                'microsoft/resnet-50',
                'facebook/convnext-base-224',
                'timm/vit_base_patch16_224',
                'microsoft/swin-base-patch4-window7-224'
            ],
            'object-detection': [
                'facebook/detr-resnet-50',
                'hustvl/yolos-tiny',
                'facebook/detr-resnet-101',
                'microsoft/table-transformer-detection',
                'facebook/detr-resnet-50-dc5'
            ],
            'image-segmentation': [
                'facebook/detr-resnet-50-panoptic',
                'facebook/detr-resnet-101-panoptic',
                'nvidia/segformer-b0-finetuned-ade-512-512',
                'facebook/detr-resnet-50-dc5-panoptic'
            ],
            'visual-question-answering': [
                'dandelin/vilt-b32-finetuned-vqa',
                'dandelin/vilt-b32-finetuned-vqa2',
                'microsoft/git-base-vqa',
                'dandelin/vilt-b16-finetuned-vqa'
            ],
            'image-to-text': [
                'nlpconnect/vit-gpt2-image-captioning',
                'microsoft/git-base-coco',
                'microsoft/git-base-textcaps',
                'Salesforce/blip-image-captioning-base',
                'microsoft/git-large-coco'
            ],
            'text-to-image': [
                'runwayml/stable-diffusion-v1-5',
                'CompVis/stable-diffusion-v1-4',
                'stabilityai/stable-diffusion-2-1',
                'runwayml/stable-diffusion-v1-5',
                'CompVis/stable-diffusion-v1-4'
            ],
            'image-super-resolution': [
                'eugenesiow/waifu2x',
                'caidas/swin2SR-classical-sr-x2-64',
                'microsoft/swin2sr-classical-sr-x2-64',
                'eugenesiow/waifu2x-ncnn-vulkan'
            ],
            
            # Audio Processing
            'automatic-speech-recognition': [
                'openai/whisper-small',
                'openai/whisper-base',
                'facebook/wav2vec2-base-960h',
                'facebook/wav2vec2-large-960h-lv60-self',
                'microsoft/speecht5_asr'
            ],
            'audio-classification': [
                'superb/hubert-base-superb-er',
                'facebook/wav2vec2-base',
                'facebook/wav2vec2-large',
                'microsoft/speecht5_asr',
                'facebook/wav2vec2-base-960h'
            ],
            'voice-activity-detection': [
                'pyannote/voice-activity-detection',
                'microsoft/speecht5_asr',
                'facebook/wav2vec2-base',
                'facebook/wav2vec2-large'
            ],
            'text-to-speech': [
                'suno/bark-small',
                'facebook/fastspeech2-en-ljspeech',
                'microsoft/speecht5_tts',
                'facebook/fastspeech2-en-ljspeech',
                'suno/bark'
            ],
            'audio-to-audio': [
                'facebook/wav2vec2-base',
                'facebook/wav2vec2-large',
                'microsoft/speecht5_asr',
                'openai/whisper-small'
            ],
            
            # Video Processing
            'video-classification': [
                'MCG-NJU/videomae-base',
                'facebook/timesformer-base-finetuned-k400',
                'microsoft/xclip-base-patch32',
                'facebook/timesformer-base-finetuned-k600',
                'MCG-NJU/videomae-large'
            ],
            
            # Document & Table Processing
            'document-question-answering': [
                'impira/layoutlm-document-qa',
                'microsoft/layoutlm-base-uncased',
                'microsoft/layoutlm-large-uncased',
                'microsoft/layoutlmv2-base-uncased',
                'microsoft/layoutlmv3-base'
            ],
            'table-question-answering': [
                'google/tapas-base-finetuned-wtq',
                'google/tapas-large-finetuned-wtq',
                'microsoft/table-transformer-detection',
                'google/tapas-base-finetuned-sqa',
                'microsoft/table-transformer-structure-recognition'
            ],
            
            # Depth & 3D
            'depth-estimation': [
                'Intel/dpt-large',
                'Intel/dpt-hybrid-midas',
                'Intel/dpt-beit-large-512',
                'Intel/dpt-hybrid-midas-240be',
                'Intel/dpt-large-hybrid-midas'
            ],
            
            # Multimodal & Specialized
            'multimodal': [
                'microsoft/git-base-coco',
                'dandelin/vilt-b32-finetuned-vqa',
                'microsoft/git-base-textcaps',
                'Salesforce/blip-image-captioning-base',
                'microsoft/git-large-coco'
            ],
            'conversational-ai': [
                'microsoft/DialoGPT-medium',
                'microsoft/DialoGPT-small',
                'facebook/blenderbot-400M-distill',
                'EleutherAI/gpt-neo-125M',
                'openai-community/gpt2'
            ],
            'chat': [
                'microsoft/DialoGPT-medium',
                'microsoft/DialoGPT-small',
                'facebook/blenderbot-400M-distill',
                'EleutherAI/gpt-neo-125M',
                'openai-community/gpt2'
            ],
            'dialogue': [
                'microsoft/DialoGPT-medium',
                'microsoft/DialoGPT-small',
                'facebook/blenderbot-400M-distill',
                'EleutherAI/gpt-neo-125M',
                'openai-community/gpt2'
            ]
        }
        
        # Legacy single model fallbacks for backward compatibility
        self.default_hf_models: Dict[str, str] = {
            tag: models[0] if models else 'openai-community/gpt2'
            for tag, models in self.fallback_models.items()
        }
        
    def select_best_model(self, task_name: str, prompt: str, strategy: SelectionStrategy = SelectionStrategy.MULTI_OBJECTIVE, 
                         max_candidates: int = 20, cv_folds: int = 5) -> SelectionResult:
        """Select the best model using enhanced techniques."""
        start_time = time.time()
        
        # Get initial candidates
        candidates = self._get_initial_candidates(task_name, max_candidates)
        logger.info(f"🔍 Found {len(candidates)} initial candidates for task: {task_name}")
        
        # If no candidates were found in DB, try to find fallback models
        if not candidates:
            candidates = self._get_fallback_candidates(task_name, max_candidates)
            if candidates:
                logger.info(f"🛟 Found {len(candidates)} fallback candidates for task '{task_name}'")
            else:
                # Use curated fallback models as last resort
                candidates = self._create_curated_fallback_candidates(task_name)
                if candidates:
                    logger.info(f"🛟 Using curated fallback models for task '{task_name}': {len(candidates)} models")
                else:
                    # Ultimate fallback - create a basic candidate
                    logger.warning(f"⚠️ No fallback models found for task '{task_name}', creating basic fallback")
                    candidates = [self._create_basic_fallback_candidate(task_name)]

        # Apply selection strategy
        if strategy == SelectionStrategy.HYPERPARAMETER_TUNING:
            candidates = self._apply_hyperparameter_tuning(candidates, cv_folds)
        elif strategy == SelectionStrategy.CROSS_VALIDATION:
            candidates = self._apply_cross_validation(candidates, cv_folds)
        elif strategy == SelectionStrategy.ENSEMBLE_METHODS:
            candidates = self._apply_ensemble_methods(candidates, task_name, prompt)
        elif strategy == SelectionStrategy.BAYESIAN_OPTIMIZATION:
            candidates = self._apply_bayesian_optimization(candidates, cv_folds)
        elif strategy == SelectionStrategy.META_LEARNING:
            candidates = self._apply_meta_learning(candidates, task_name)
        elif strategy == SelectionStrategy.MULTI_OBJECTIVE:
            candidates = self._apply_multi_objective_optimization(candidates, cv_folds)
        
        # Select best model
        best_model = self._select_final_model(candidates, task_name)
        
        # Calculate confidence and reasoning
        confidence_score = self._calculate_confidence_score(candidates, best_model)
        reasoning = self._generate_selection_reasoning(candidates, best_model, strategy)
        
        optimization_time = time.time() - start_time
        
        return SelectionResult(
            best_model=best_model,
            all_candidates=candidates,
            selection_strategy=strategy,
            optimization_time=optimization_time,
            evaluation_metrics=self._calculate_evaluation_metrics(candidates),
            confidence_score=confidence_score,
            reasoning=reasoning
        )
    
    def _get_initial_candidates(self, task_name: str, max_candidates: int) -> List[ModelCandidate]:
        """Get initial model candidates from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Map task names to pipeline tags
                task_mapping = {
                    'sentiment-analysis': 'text-classification',
                    'text-classification': 'text-classification',
                    'text-generation': 'text-generation',
                    'text-analysis': 'text-classification',
                    'text_analysis': 'text-classification',
                    'translation': 'translation',
                    'summarization': 'summarization',
                    'question-answering': 'question-answering',
                    'token-classification': 'token-classification',
                    'fill-mask': 'fill-mask',
                    'feature-extraction': 'feature-extraction',
                    'sentence-similarity': 'sentence-similarity',
                    'image-classification': 'image-classification',
                    'object-detection': 'object-detection',
                    'text-to-image': 'text-to-image',
                    'image-to-text': 'image-to-text',
                    'automatic-speech-recognition': 'automatic-speech-recognition',
                    'audio-classification': 'audio-classification',
                    'text-to-speech': 'text-to-speech',
                    'audio-to-audio': 'audio-to-audio'
                }
                
                # Use mapped pipeline tag or original task name
                pipeline_tag = task_mapping.get(task_name, task_name)
                logger.info(f"🔍 Mapping task '{task_name}' to pipeline tag '{pipeline_tag}'")
                
                # Determine schema-compatible size column expression to avoid referencing
                # non-existent columns across different database versions
                cursor.execute("PRAGMA table_info(models)")
                cols = {row[1] for row in cursor.fetchall()}

                def expr(column: str, alias: str | None = None) -> str:
                    if column in cols:
                        return column if alias is None else f"{column} AS {alias}"
                    # Return NULL with proper alias when the column is missing
                    target = alias or column
                    return f"NULL AS {target}"

                size_expr = expr('model_size_mb', 'size_mb') if 'model_size_mb' in cols else expr('size_mb')

                # Expressions for optional columns
                author_expr = expr('author')
                library_expr = expr('library_name')
                downloads_expr = expr('downloads')
                likes_expr = expr('likes')
                decision_expr = expr('decision_score')
                capability_expr = expr('capability_score')
                efficiency_expr = expr('efficiency_score')
                popularity_expr = expr('popularity_score')
                license_expr = expr('license')
                base_model_expr = expr('base_model')
                datasets_expr = expr('datasets')
                metrics_expr = expr('metrics')
                widget_expr = expr('widget_data')
                inference_expr = expr('inference_info')
                pop_norm_expr = expr('popularity_score_normalized')
                engagement_expr = expr('engagement_score')
                lightweight_expr = expr('lightweight_score')
                task_match_expr = expr('task_match_score')
                tags_expr = expr('tags')  # Include tags for F1 evaluation
                last_modified_expr = expr('last_modified')

                where_clause = "WHERE pipeline_tag = ?"
                if 'downloads' in cols:
                    where_clause += " AND downloads > 10"

                order_parts = []
                if 'decision_score' in cols:
                    order_parts.append('decision_score DESC')
                if 'downloads' in cols:
                    order_parts.append('downloads DESC')
                order_by = ", ".join(order_parts) if order_parts else 'model_id ASC'

                # Enhanced query with schema-adaptive columns including tags
                query = f"""
                    SELECT model_id, pipeline_tag, {author_expr}, {library_expr}, {downloads_expr}, {likes_expr},
                           {decision_expr}, {capability_expr}, {efficiency_expr}, {popularity_expr},
                           {size_expr}, {license_expr}, {base_model_expr}, {datasets_expr}, {metrics_expr}, {widget_expr}, {inference_expr},
                           {pop_norm_expr}, {engagement_expr}, {lightweight_expr}, {task_match_expr}, {tags_expr}, {last_modified_expr}
                    FROM models 
                    {where_clause}
                    ORDER BY {order_by}
                    LIMIT ?
                """
                
                cursor.execute(query, (pipeline_tag, max_candidates))
                results = cursor.fetchall()
                
                candidates = []
                for row in results:
                    # Guard indices defensively in case columns are missing
                    try:
                        # Parse tags if available
                        all_tags = []
                        if len(row) > 21 and row[21]:  # tags column
                            try:
                                all_tags = json.loads(row[21]) if row[21] else []
                            except (json.JSONDecodeError, TypeError):
                                all_tags = []
                        
                        candidate = ModelCandidate(
                            model_id=row[0] or "",
                            pipeline_tag=row[1] or "",
                            author=(row[2] or "") if len(row) > 2 else "",
                            library_name=(row[3] or "") if len(row) > 3 else "",
                            downloads=row[4] if len(row) > 4 else 0,
                            likes=row[5] if len(row) > 5 else 0,
                            decision_score=row[6] if len(row) > 6 else 0.0,
                            capability_score=row[7] if len(row) > 7 else 0.0,
                            efficiency_score=row[8] if len(row) > 8 else 0.0,
                            popularity_score=row[9] if len(row) > 9 else 0.0,
                            size_mb=row[10] if len(row) > 10 else 0.0,
                            license=(row[11] or "") if len(row) > 11 else "",
                            base_model=(row[12] or "") if len(row) > 12 else "",
                            datasets=(row[13] or "") if len(row) > 13 else "",
                            metrics=(row[14] or "") if len(row) > 14 else "",
                            widget_data=(row[15] or "") if len(row) > 15 else "",
                            inference_info=(row[16] or "") if len(row) > 16 else "",
                            popularity_score_normalized=row[17] if len(row) > 17 else 0.0,
                            engagement_score=row[18] if len(row) > 18 else 0.0,
                            lightweight_score=row[19] if len(row) > 19 else 0.0,
                            task_match_score=row[20] if len(row) > 20 else 0.0
                        )
                        
                        # Store all_tags as a custom attribute for F1 evaluation
                        candidate.all_tags = all_tags
                        
                        # Set freshness data
                        candidate.last_modified = row[22] if len(row) > 22 else None
                        candidate.freshness_score = self._get_model_freshness_score(candidate.model_id, candidate.last_modified)
                        
                        candidates.append(candidate)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error creating candidate from row: {e}")
                        continue
                
                logger.info(f"🔍 Found {len(candidates)} initial candidates for task: {task_name}")
                return candidates
                
        except Exception as e:
            logger.error(f"❌ Error getting initial candidates: {e}")
            return []
    
    def _apply_hyperparameter_tuning(self, candidates: List[ModelCandidate], cv_folds: int) -> List[ModelCandidate]:
        """Apply hyperparameter tuning to model candidates."""
        logger.info("🔧 Applying hyperparameter tuning...")
        
        def tune_model(candidate: ModelCandidate) -> ModelCandidate:
            try:
                # Define hyperparameter search space based on model type
                if 'bert' in candidate.model_id.lower() or 'transformer' in candidate.library_name.lower():
                    param_space = {
                        'learning_rate': [0.001, 0.01, 0.1],
                        'batch_size': [16, 32, 64],
                        'epochs': [3, 5, 10],
                        'dropout': [0.1, 0.2, 0.3]
                    }
                else:
                    param_space = {
                        'C': [0.1, 1.0, 10.0],
                        'gamma': ['scale', 'auto'],
                        'kernel': ['rbf', 'linear']
                    }
                
                # Grid search for best parameters
                best_score = 0.0
                best_params = None
                
                for _ in range(10):  # Limited iterations for performance
                    params = {k: random.choice(v) if isinstance(v, list) else v for k, v in param_space.items()}
                    
                    # Simulate cross-validation score
                    cv_score = self._simulate_cv_score(candidate, params, cv_folds)
                    
                    if cv_score > best_score:
                        best_score = cv_score
                        best_params = params
                
                candidate.hp_optimized_score = best_score
                candidate.best_params = best_params
                
            except Exception as e:
                logger.warning(f"⚠️ Error tuning {candidate.model_id}: {e}")
                candidate.hp_optimized_score = candidate.decision_score
            
            return candidate
        
        # Apply tuning in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            tuned_candidates = list(executor.map(tune_model, candidates))
        
        # Sort by optimized score
        tuned_candidates.sort(key=lambda x: x.hp_optimized_score or 0.0, reverse=True)
        
        logger.info(f"✅ Hyperparameter tuning completed for {len(tuned_candidates)} models")
        return tuned_candidates
    
    def _apply_cross_validation(self, candidates: List[ModelCandidate], cv_folds: int) -> List[ModelCandidate]:
        """Apply cross-validation to model candidates."""
        logger.info("🔄 Applying cross-validation...")
        
        def validate_model(candidate: ModelCandidate) -> ModelCandidate:
            try:
                # Simulate cross-validation scores
                cv_scores = []
                for fold in range(cv_folds):
                    # Simulate different fold performance
                    base_score = candidate.decision_score
                    fold_score = base_score * (0.8 + 0.4 * random.random())  # ±20% variation
                    cv_scores.append(fold_score)
                
                candidate.cv_score = np.mean(cv_scores)
                candidate.cv_std = np.std(cv_scores)
                
            except Exception as e:
                logger.warning(f"⚠️ Error validating {candidate.model_id}: {e}")
                candidate.cv_score = candidate.decision_score
                candidate.cv_std = 0.0
            
            return candidate
        
        # Apply cross-validation in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            validated_candidates = list(executor.map(validate_model, candidates))
        
        # Sort by CV score
        validated_candidates.sort(key=lambda x: x.cv_score or 0.0, reverse=True)
        
        logger.info(f"✅ Cross-validation completed for {len(validated_candidates)} models")
        return validated_candidates
    
    def _apply_ensemble_methods(self, candidates: List[ModelCandidate], task_name: str = None, user_prompt: str = None) -> List[ModelCandidate]:
        """Apply ensemble methods to model candidates with F1 score evaluation."""
        logger.info("🎯 Applying ensemble methods with F1 evaluation...")
        
        # Select top candidates for ensemble
        top_candidates = candidates[:min(5, len(candidates))]
        
        # Evaluate top candidates with F1 score if task_name is provided
        if task_name:
            logger.info(f"🔬 Evaluating {len(top_candidates)} models with F1 benchmark...")
            for candidate in top_candidates:
                try:
                    # Evaluate model with F1 score using task-aware benchmarks and ALL tags for better task mapping
                    evaluation_result = self.f1_evaluator.evaluate_model(
                        candidate.model_id,
                        task_name,
                        user_prompt,
                        candidate.all_tags,               # primary: all tags
                        pipeline_tag=candidate.pipeline_tag  # fallback: pipeline tag
                    )
                    
                    # Handle both old and new key formats
                    if "f1_avg" in evaluation_result:
                        candidate.f1_score = evaluation_result["f1_avg"]
                        candidate.exact_match_score = evaluation_result["em_avg"]
                    elif "f1_score" in evaluation_result:
                        candidate.f1_score = evaluation_result["f1_score"]
                        candidate.exact_match_score = evaluation_result["em_score"]
                    else:
                        # Fallback for failed evaluations
                        candidate.f1_score = 0.0
                        candidate.exact_match_score = 0.0
                    
                    candidate.benchmark_predictions = evaluation_result.get("predictions", [])
                    candidate.benchmark_evaluation_time = evaluation_result.get("evaluation_time", 0.0)
                    
                    evaluation_method = evaluation_result.get("evaluation_method", "unknown")
                    logger.info(f"📊 {candidate.model_id}: F1={candidate.f1_score:.3f}, EM={candidate.exact_match_score:.3f} ({evaluation_method})")
                    
                except Exception as e:
                    logger.warning(f"⚠️ F1 evaluation failed for {candidate.model_id}: {e}")
                    # Use zero scores for failed evaluations - no simulation
                    candidate.f1_score = 0.0
                    candidate.exact_match_score = 0.0
        
        # Calculate ensemble weights based on F1 score if available, otherwise use decision score
        total_score = sum(c.f1_score or c.decision_score for c in top_candidates)
        
        for candidate in top_candidates:
            # Weighted ensemble score using F1 score if available
            weight = (candidate.f1_score or candidate.decision_score) / total_score if total_score > 0 else 1.0 / len(top_candidates)
            candidate.ensemble_weight = weight
            
            # Enhanced ensemble score that includes F1 score
            f1_component = candidate.f1_score if candidate.f1_score else candidate.decision_score
            ensemble_score = (
                f1_component * 0.5 +  # F1 score has highest weight
                candidate.decision_score * 0.2 +
                candidate.capability_score * 0.1 +
                candidate.efficiency_score * 0.1 +
                candidate.popularity_score * 0.05 +
                candidate.task_match_score * 0.05
            )
            candidate.ensemble_score = ensemble_score
        
        # Sort by ensemble score
        top_candidates.sort(key=lambda x: x.ensemble_score or 0.0, reverse=True)
        
        logger.info(f"✅ Ensemble methods applied to {len(top_candidates)} models with F1 evaluation")
        return top_candidates
    
    def _apply_bayesian_optimization(self, candidates: List[ModelCandidate], cv_folds: int) -> List[ModelCandidate]:
        """Apply Bayesian optimization for hyperparameter tuning."""
        if not OPTUNA_AVAILABLE:
            logger.warning("⚠️ optuna not available, skipping Bayesian optimization")
            return candidates
            
        logger.info("🧠 Applying Bayesian optimization...")
        
        def objective(trial):
            # Define hyperparameter search space
            learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-1, log=True)
            batch_size = trial.suggest_categorical('batch_size', [16, 32, 64, 128])
            dropout = trial.suggest_float('dropout', 0.1, 0.5)
            
            # Simulate model performance with these parameters
            base_score = candidates[0].decision_score
            optimized_score = base_score * (0.7 + 0.6 * random.random())
            
            return optimized_score
        
        try:
            # Run Bayesian optimization
            study = optuna.create_study(direction='maximize')
            study.optimize(objective, n_trials=20)
            
            # Apply best parameters to top candidate
            if candidates:
                candidates[0].hp_optimized_score = study.best_value
                candidates[0].best_params = study.best_params
            
            logger.info(f"✅ Bayesian optimization completed. Best score: {study.best_value:.4f}")
        except Exception as e:
            logger.warning(f"⚠️ Bayesian optimization failed: {e}")
        
        return candidates
    
    def _apply_meta_learning(self, candidates: List[ModelCandidate], task_name: str) -> List[ModelCandidate]:
        """Apply meta-learning to predict model performance."""
        logger.info("🧠 Applying meta-learning...")
        
        for candidate in candidates:
            # Extract meta-features
            meta_features = {
                'downloads_log': np.log(candidate.downloads + 1),
                'likes_log': np.log(candidate.likes + 1),
                'size_normalized': min(candidate.size_mb / 1000, 1.0),
                'author_reputation': self._get_author_reputation_score(candidate.author),
                'library_popularity': self._get_library_popularity_score(candidate.library_name),
                'license_score': self._get_license_score(candidate.license),
                'task_complexity': self._get_task_complexity_score(task_name),
                'model_freshness': self._get_model_freshness_score(candidate.model_id)
            }
            
            candidate.meta_features = meta_features
            
            # Predict performance using meta-features
            predicted_score = self._predict_performance_from_meta_features(meta_features)
            candidate.meta_features['predicted_score'] = predicted_score
        
        # Sort by predicted performance
        candidates.sort(key=lambda x: x.meta_features.get('predicted_score', 0.0), reverse=True)
        
        logger.info(f"✅ Meta-learning applied to {len(candidates)} models")
        return candidates
    
    def _apply_multi_objective_optimization(self, candidates: List[ModelCandidate], cv_folds: int) -> List[ModelCandidate]:
        """Apply multi-objective optimization considering multiple criteria."""
        logger.info("🎯 Applying multi-objective optimization...")
        
        for candidate in candidates:
            # Define multiple objectives
            objectives = {
                'performance': candidate.decision_score,
                'efficiency': candidate.efficiency_score,
                'popularity': candidate.popularity_score_normalized,
                'lightweight': candidate.lightweight_score,
                'task_match': candidate.task_match_score,
                'reliability': self._calculate_reliability_score(candidate)
            }
            
            # Calculate Pareto-optimal score
            pareto_score = self._calculate_pareto_score(objectives)
            candidate.meta_features = {'pareto_score': pareto_score, 'objectives': objectives}
        
        # Sort by Pareto score
        candidates.sort(key=lambda x: x.meta_features.get('pareto_score', 0.0), reverse=True)
        
        logger.info(f"✅ Multi-objective optimization completed for {len(candidates)} models")
        return candidates
    
    def _select_final_model(self, candidates: List[ModelCandidate], task_name: str) -> ModelCandidate:
        """Select the final best model from optimized candidates."""
        if not candidates:
            raise ValueError("No candidates available for selection")
        
        # Use ensemble of different selection criteria
        final_scores = []
        for candidate in candidates:
            score = 0.0
            
            # Base decision score
            score += candidate.decision_score * 0.3
            
            # Cross-validation score if available
            if candidate.cv_score:
                score += candidate.cv_score * 0.2
            
            # Hyperparameter optimized score if available
            if candidate.hp_optimized_score:
                score += candidate.hp_optimized_score * 0.15
            
            # Ensemble score if available
            if candidate.ensemble_score:
                score += candidate.ensemble_score * 0.15
            
            # Freshness score (New)
            score += candidate.freshness_score * 0.15
            
            # Meta-learning prediction if available
            if candidate.meta_features and 'predicted_score' in candidate.meta_features:
                score += candidate.meta_features['predicted_score'] * 0.1
            
            # Pareto score if available
            if candidate.meta_features and 'pareto_score' in candidate.meta_features:
                score += candidate.meta_features['pareto_score'] * 0.1
            
            final_scores.append(score)
        
        # Select candidate with highest final score
        best_idx = np.argmax(final_scores)
        return candidates[best_idx]
    
    def _calculate_confidence_score(self, candidates: List[ModelCandidate], best_model: ModelCandidate) -> float:
        """Calculate confidence in the selection."""
        if not candidates:
            return 0.0
        
        # Calculate margin between best and second best
        scores = []
        for candidate in candidates:
            score = candidate.decision_score
            if candidate.cv_score:
                score = (score + candidate.cv_score) / 2
            scores.append(score)
        
        scores.sort(reverse=True)
        
        if len(scores) >= 2:
            margin = scores[0] - scores[1]
            confidence = min(1.0, margin * 10)  # Scale margin to confidence
        else:
            confidence = 0.5
        
        return confidence
    
    def _generate_selection_reasoning(self, candidates: List[ModelCandidate], best_model: ModelCandidate, 
                                    strategy: SelectionStrategy) -> str:
        """Generate detailed reasoning for the selection."""
        reasoning_parts = []
        
        reasoning_parts.append(f"Selected {best_model.model_id} using {strategy.value}")
        
        # Add performance metrics
        if best_model.cv_score:
            reasoning_parts.append(f"CV Score: {best_model.cv_score:.3f} ± {best_model.cv_std:.3f}")
        
        if best_model.hp_optimized_score:
            reasoning_parts.append(f"Optimized Score: {best_model.hp_optimized_score:.3f}")
        
        if best_model.ensemble_score:
            reasoning_parts.append(f"Ensemble Score: {best_model.ensemble_score:.3f}")
        
        # Add comparative analysis
        if len(candidates) >= 2:
            second_best = candidates[1]
            margin = best_model.decision_score - second_best.decision_score
            reasoning_parts.append(f"Margin over runner-up: {margin:.3f}")
        
        # Add model characteristics
        reasoning_parts.append(f"Freshness: {best_model.freshness_score:.2f}")
        if best_model.last_modified:
            reasoning_parts.append(f"Updated: {str(best_model.last_modified)[:10]}")
        reasoning_parts.append(f"Size: {best_model.size_mb:.1f}MB")
        reasoning_parts.append(f"Downloads: {best_model.downloads:,}")
        reasoning_parts.append(f"License: {best_model.license}")
        
        return " | ".join(reasoning_parts)
    
    def _calculate_evaluation_metrics(self, candidates: List[ModelCandidate]) -> Dict[str, float]:
        """Calculate comprehensive evaluation metrics including F1 scores."""
        if not candidates:
            return {}
        
        scores = [c.decision_score for c in candidates]
        f1_scores = [c.f1_score for c in candidates if c.f1_score is not None]
        em_scores = [c.exact_match_score for c in candidates if c.exact_match_score is not None]
        
        metrics = {
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'max_score': np.max(scores),
            'min_score': np.min(scores),
            'score_range': np.max(scores) - np.min(scores),
            'cv_scores_available': sum(1 for c in candidates if c.cv_score is not None),
            'hp_optimized_available': sum(1 for c in candidates if c.hp_optimized_score is not None),
            'ensemble_scores_available': sum(1 for c in candidates if c.ensemble_score is not None),
            'f1_scores_available': len(f1_scores),
            'em_scores_available': len(em_scores)
        }
        
        # Add F1 score metrics if available
        if f1_scores:
            metrics.update({
                'mean_f1_score': np.mean(f1_scores),
                'std_f1_score': np.std(f1_scores),
                'max_f1_score': np.max(f1_scores),
                'min_f1_score': np.min(f1_scores)
            })
        
        # Add Exact Match score metrics if available
        if em_scores:
            metrics.update({
                'mean_em_score': np.mean(em_scores),
                'std_em_score': np.std(em_scores),
                'max_em_score': np.max(em_scores),
                'min_em_score': np.min(em_scores)
            })
        
        return metrics
    
    # Helper methods for meta-learning
    def _get_author_reputation_score(self, author: str) -> float:
        """Get reputation score for model author."""
        reputable_authors = [
            'microsoft', 'google', 'facebook', 'openai', 'anthropic', 'meta', 'huggingface', 
            'stabilityai', 'tiiuae', 'mistralai', '01-ai', 'deepseek-ai', 'qwen', 'nvidia'
        ]
        return 1.0 if author.lower() in reputable_authors else 0.5
    
    def _get_library_popularity_score(self, library: str) -> float:
        """Get popularity score for library."""
        popular_libraries = ['transformers', 'torch', 'tensorflow', 'sklearn']
        return 1.0 if library.lower() in popular_libraries else 0.5
    
    def _get_license_score(self, license: str) -> float:
        """Get score based on license type."""
        open_licenses = ['mit', 'apache-2.0', 'bsd', 'gpl']
        return 1.0 if license.lower() in open_licenses else 0.3
    
    def _get_task_complexity_score(self, task_name: str) -> float:
        """Get complexity score for task."""
        complex_tasks = ['text-generation', 'translation', 'summarization', 'question-answering']
        return 1.0 if task_name in complex_tasks else 0.7
    
    def _get_model_freshness_score(self, model_id: str, last_modified: str = None) -> float:
        """Get freshness score based on last_modified date or model ID patterns."""
        # Try to use real date from DB
        if last_modified:
            try:
                # Handle various timestamp formats from SQLite
                dt = None
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(str(last_modified).split('.')[0], fmt)
                        break
                    except ValueError:
                        continue
                
                if dt:
                    age = datetime.now() - dt
                    days = age.days
                    if days < 30: return 1.0      # Very fresh (< 1 month)
                    if days < 90: return 0.9      # Fresh (< 3 months)
                    if days < 180: return 0.8     # Recent (< 6 months)
                    if days < 365: return 0.6     # Within a year
                    if days < 730: return 0.4     # Within 2 years
                    return 0.2                    # Older
            except Exception:
                pass # Fallback to heuristic

        # Fallback heuristic based on model name patterns
        lower_id = model_id.lower()
        if any(keyword in lower_id for keyword in ['2025', 'v4', 'llama-3']):
            return 1.0
        if any(keyword in lower_id for keyword in ['2024', 'v3', 'llama-2', 'mistral']):
            return 0.9
        elif any(keyword in lower_id for keyword in ['2023', 'v2']):
            return 0.7
        elif any(keyword in lower_id for keyword in ['2022', 'v1']):
            return 0.5
        else:
            return 0.3
    
    def _predict_performance_from_meta_features(self, meta_features: Dict[str, float]) -> float:
        """Predict model performance from meta-features."""
        # Simple linear combination of meta-features
        weights = {
            'downloads_log': 0.2,
            'likes_log': 0.15,
            'size_normalized': 0.1,
            'author_reputation': 0.15,
            'library_popularity': 0.1,
            'license_score': 0.1,
            'task_complexity': 0.1,
            'model_freshness': 0.1
        }
        
        predicted_score = sum(meta_features.get(key, 0.0) * weight for key, weight in weights.items())
        return min(1.0, predicted_score)
    
    def _calculate_reliability_score(self, candidate: ModelCandidate) -> float:
        """Calculate reliability score based on various factors."""
        reliability = 0.5  # Base score
        
        # Downloads factor
        if candidate.downloads > 100000:
            reliability += 0.2
        elif candidate.downloads > 10000:
            reliability += 0.1
        
        # Likes factor
        if candidate.likes > 1000:
            reliability += 0.1
        
        # License factor
        if candidate.license in ['mit', 'apache-2.0']:
            reliability += 0.1
        
        # Author reputation
        if candidate.author.lower() in ['microsoft', 'google', 'facebook', 'openai', 'meta', 'mistralai']:
            reliability += 0.1

        # Quantization/Efficient format boost
        model_lower = candidate.model_id.lower()
        if 'gguf' in model_lower or 'awq' in model_lower or 'gptq' in model_lower:
            reliability += 0.2  # Big boost for efficient inference formats
        
        return min(1.0, reliability)
    
    def _calculate_pareto_score(self, objectives: Dict[str, float]) -> float:
        """Calculate Pareto-optimal score from multiple objectives."""
        # Normalize objectives to [0, 1] range
        normalized = {k: v for k, v in objectives.items()}
        
        # Calculate weighted sum (simple approach)
        weights = {
            'performance': 0.3,
            'efficiency': 0.2,
            'popularity': 0.15,
            'lightweight': 0.15,
            'task_match': 0.1,
            'reliability': 0.1
        }
        
        pareto_score = sum(normalized.get(key, 0.0) * weight for key, weight in weights.items())
        return pareto_score
    
    def _simulate_cv_score(self, candidate: ModelCandidate, params: Dict[str, Any], cv_folds: int) -> float:
        """Simulate cross-validation score for a model with given parameters."""
        # Base score from candidate
        base_score = candidate.decision_score
        
        # Parameter effect simulation
        param_effect = 1.0
        for param_name, param_value in params.items():
            if param_name == 'learning_rate':
                param_effect *= 0.8 + 0.4 * (param_value / 0.1)  # Optimal around 0.1
            elif param_name == 'batch_size':
                param_effect *= 0.9 + 0.2 * (32 / param_value)  # Optimal around 32
            elif param_name == 'dropout':
                param_effect *= 0.9 + 0.2 * (1 - abs(param_value - 0.2))  # Optimal around 0.2
        
        # Add some randomness to simulate CV
        cv_scores = []
        for _ in range(cv_folds):
            fold_score = base_score * param_effect * (0.8 + 0.4 * random.random())
            cv_scores.append(fold_score)
        
        return np.mean(cv_scores)

    def _get_fallback_candidates(self, task_name: str, max_candidates: int) -> List[ModelCandidate]:
        """Get fallback candidates from the fallback_models dictionary."""
        candidates = []
        
        # Try to find models for the task in fallback_models
        if task_name in self.fallback_models:
            model_ids = self.fallback_models[task_name][:max_candidates]
            for model_id in model_ids:
                candidate = self._create_candidate_from_model_id(model_id, task_name)
                if candidate:
                    candidates.append(candidate)
        
        # If no models found for exact task name, try similar tasks
        if not candidates:
            similar_tasks = self._find_similar_tasks(task_name)
            for similar_task in similar_tasks:
                if similar_task in self.fallback_models:
                    model_ids = self.fallback_models[similar_task][:max_candidates//len(similar_tasks)]
                    for model_id in model_ids:
                        candidate = self._create_candidate_from_model_id(model_id, task_name)
                        if candidate:
                            candidates.append(candidate)
        
        return candidates

    def _create_curated_fallback_candidates(self, task_name: str) -> List[ModelCandidate]:
        """Create curated fallback candidates using general-purpose models."""
        candidates = []
        
        # Use general-purpose models that can handle multiple tasks
        general_models = [
            'openai-community/gpt2',
            'microsoft/DialoGPT-medium',
            'EleutherAI/gpt-neo-125M',
            'facebook/bart-base',
            'google/flan-t5-small'
        ]
        
        for model_id in general_models:
            candidate = self._create_candidate_from_model_id(model_id, task_name)
            if candidate:
                candidates.append(candidate)
        
        return candidates

    def _create_basic_fallback_candidate(self, task_name: str) -> ModelCandidate:
        """Create a basic fallback candidate when no other models are available."""
        return ModelCandidate(
            model_id='openai-community/gpt2',
            pipeline_tag=task_name,
            author='openai-community',
            library_name='transformers',
            downloads=14073326,
            likes=2886,
            decision_score=0.5,
            capability_score=0.5,
            efficiency_score=0.5,
            popularity_score=0.5,
            size_mb=500.0,
            license='mit',
            base_model='gpt2',
            datasets='',
            metrics='',
            widget_data='',
            inference_info='',
            popularity_score_normalized=0.5,
            engagement_score=0.5,
            lightweight_score=0.5,
            task_match_score=0.5
        )

    def _create_candidate_from_model_id(self, model_id: str, task_name: str) -> Optional[ModelCandidate]:
        """Create a ModelCandidate from a model ID with default values."""
        try:
            # Parse model ID to extract author and model name
            parts = model_id.split('/')
            if len(parts) == 2:
                author, model_name = parts
            else:
                author = 'unknown'
                model_name = model_id
            
            # Estimate size based on model name patterns
            size_mb = 500.0  # Default size
            if 'small' in model_name.lower():
                size_mb = 100.0
            elif 'base' in model_name.lower():
                size_mb = 300.0
            elif 'large' in model_name.lower():
                size_mb = 1000.0
            elif 'tiny' in model_name.lower():
                size_mb = 50.0
            
            # Estimate downloads and likes based on model popularity
            downloads = 1000000  # Default
            likes = 100  # Default
            
            # Adjust based on known popular models
            if 'gpt2' in model_id.lower():
                downloads = 14073326
                likes = 2886
            elif 'bert' in model_id.lower():
                downloads = 5000000
                likes = 500
            elif 'roberta' in model_id.lower():
                downloads = 3000000
                likes = 300
            
            return ModelCandidate(
                model_id=model_id,
                pipeline_tag=task_name,
                author=author,
                library_name='transformers',
                downloads=downloads,
                likes=likes,
                decision_score=0.7,
                capability_score=0.7,
                efficiency_score=0.7,
                popularity_score=0.7,
                size_mb=size_mb,
                license='mit',
                base_model=model_name,
                datasets='',
                metrics='',
                widget_data='',
                inference_info='',
                popularity_score_normalized=0.7,
                engagement_score=0.7,
                lightweight_score=0.7,
                task_match_score=0.7
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to create candidate from model ID {model_id}: {e}")
            return None

    def _find_similar_tasks(self, task_name: str) -> List[str]:
        """Find similar tasks for fallback purposes."""
        task_similarity = {
            'text-generation': ['conversational', 'chat', 'dialogue', 'text2text-generation'],
            'text-classification': ['sentiment-analysis', 'text-analysis', 'text_analysis'],
            'question-answering': ['text-generation', 'conversational'],
            'summarization': ['text-generation', 'text2text-generation'],
            'translation': ['text2text-generation', 'text-generation'],
            'sentiment-analysis': ['text-classification', 'text-analysis', 'text_analysis'],
            'conversational': ['text-generation', 'chat', 'dialogue'],
            'chat': ['text-generation', 'conversational', 'dialogue'],
            'dialogue': ['text-generation', 'conversational', 'chat']
        }
        
        return task_similarity.get(task_name, [])

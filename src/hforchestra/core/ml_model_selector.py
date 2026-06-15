"""
Machine Learning-based Model Selector for HFOrchestra

This module implements an intelligent model selection system that learns from
past performance data to make better model choices for different tasks.
"""

import json
import pickle
import sqlite3
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.neural_network import MLPRegressor
import joblib

logger = logging.getLogger(__name__)

@dataclass
class TaskFeatures:
    """Features extracted from task characteristics."""
    task_type: str
    prompt_length: int
    prompt_complexity: float  # Based on keywords, structure, etc.
    language: str
    domain: str  # e.g., 'technical', 'creative', 'analytical'
    urgency_level: float  # 0-1 scale
    quality_requirement: float  # 0-1 scale
    resource_constraint: float  # 0-1 scale
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    has_code: bool = False
    has_math: bool = False
    has_tables: bool = False
    has_images: bool = False

@dataclass
class ModelPerformance:
    """Performance metrics for a model on a specific task."""
    model_id: str
    task_type: str
    execution_time: float
    accuracy_score: float
    quality_score: float  # User-rated quality
    resource_usage: float  # Memory/CPU usage
    cost: float
    success_rate: float
    timestamp: float
    task_features: TaskFeatures

@dataclass
class ModelSelectionResult:
    """Result of ML-based model selection."""
    selected_model: str
    confidence_score: float
    predicted_performance: Dict[str, float]
    alternative_models: List[Tuple[str, float]]
    reasoning: str
    feature_importance: Dict[str, float]

class MLModelSelector:
    """
    Machine Learning-based model selector that learns from historical performance data.
    """
    
    def __init__(self, db_path: str = "db/ml_model_selector.db", model_path: str = "models/ml_selector.pkl"):
        self.db_path = db_path
        self.model_path = model_path
        self.performance_history: List[ModelPerformance] = []
        self.ml_models: Dict[str, Any] = {}
        self.feature_scalers: Dict[str, StandardScaler] = {}
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_importance: Dict[str, Dict[str, float]] = {}
        
        # Initialize database and load existing data
        self._init_database()
        self._load_performance_history()
        self._load_or_train_models()
    
    def _init_database(self):
        """Initialize SQLite database for storing performance data."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    execution_time REAL,
                    accuracy_score REAL,
                    quality_score REAL,
                    resource_usage REAL,
                    cost REAL,
                    success_rate REAL,
                    timestamp REAL,
                    task_features TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_task ON model_performance(model_id, task_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON model_performance(timestamp)
            """)
    
    def _load_performance_history(self):
        """Load historical performance data from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT model_id, task_type, execution_time, accuracy_score, 
                           quality_score, resource_usage, cost, success_rate, 
                           timestamp, task_features
                    FROM model_performance
                    ORDER BY timestamp DESC
                """)
                
                for row in cursor.fetchall():
                    task_features = TaskFeatures(**json.loads(row[9])) if row[9] else None
                    performance = ModelPerformance(
                        model_id=row[0],
                        task_type=row[1],
                        execution_time=row[2],
                        accuracy_score=row[3],
                        quality_score=row[4],
                        resource_usage=row[5],
                        cost=row[6],
                        success_rate=row[7],
                        timestamp=row[8],
                        task_features=task_features
                    )
                    self.performance_history.append(performance)
            
            logger.info(f"Loaded {len(self.performance_history)} performance records")
            
        except Exception as e:
            logger.error(f"Error loading performance history: {e}")
            self.performance_history = []
    
    def _load_or_train_models(self):
        """Load existing ML models or train new ones if insufficient data."""
        try:
            if Path(self.model_path).exists():
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.ml_models = model_data.get('models', {})
                    self.feature_scalers = model_data.get('scalers', {})
                    self.label_encoders = model_data.get('encoders', {})
                    self.feature_importance = model_data.get('importance', {})
                logger.info("Loaded existing ML models")
            else:
                logger.info("No existing models found, will train new ones")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self.ml_models = {}
        
        # Train models if we have sufficient data
        if len(self.performance_history) >= 50:  # Minimum samples for training
            self._train_models()
        else:
            logger.info(f"Insufficient data for training ({len(self.performance_history)} samples), using fallback selection")
    
    def _extract_task_features(self, task_type: str, prompt: str, **kwargs) -> TaskFeatures:
        """Extract features from task characteristics."""
        # Basic features
        prompt_length = len(prompt)
        prompt_complexity = self._calculate_prompt_complexity(prompt)
        language = self._detect_language(prompt)
        domain = self._detect_domain(prompt, task_type)
        
        # Resource and quality constraints from kwargs
        urgency_level = kwargs.get('urgency_level', 0.5)
        quality_requirement = kwargs.get('quality_requirement', 0.7)
        resource_constraint = kwargs.get('resource_constraint', 0.5)
        
        # File-related features
        file_type = kwargs.get('file_type')
        file_size = kwargs.get('file_size')
        
        # Content analysis
        has_code = self._has_code_content(prompt)
        has_math = self._has_math_content(prompt)
        has_tables = self._has_table_content(prompt)
        has_images = kwargs.get('has_images', False)
        
        return TaskFeatures(
            task_type=task_type,
            prompt_length=prompt_length,
            prompt_complexity=prompt_complexity,
            language=language,
            domain=domain,
            urgency_level=urgency_level,
            quality_requirement=quality_requirement,
            resource_constraint=resource_constraint,
            file_type=file_type,
            file_size=file_size,
            has_code=has_code,
            has_math=has_math,
            has_tables=has_tables,
            has_images=has_images
        )
    
    def _calculate_prompt_complexity(self, prompt: str) -> float:
        """Calculate prompt complexity score."""
        complexity = 0.0
        
        # Length factor
        complexity += min(0.3, len(prompt) / 1000 * 0.3)
        
        # Keyword complexity
        complex_keywords = ['analyze', 'compare', 'evaluate', 'synthesize', 'optimize', 'debug', 'refactor']
        complexity += sum(0.1 for keyword in complex_keywords if keyword in prompt.lower())
        
        # Question complexity
        question_count = prompt.count('?')
        complexity += min(0.2, question_count * 0.05)
        
        # Code presence
        if '```' in prompt or 'def ' in prompt or 'class ' in prompt:
            complexity += 0.2
        
        return min(1.0, complexity)
    
    def _detect_language(self, prompt: str) -> str:
        """Detect primary language of the prompt."""
        # Simple language detection based on common words
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le']
        french_words = ['le', 'la', 'de', 'et', 'à', 'un', 'il', 'que', 'ne', 'se', 'ce', 'pas', 'son', 'avec']
        
        prompt_lower = prompt.lower()
        
        english_score = sum(1 for word in english_words if word in prompt_lower)
        spanish_score = sum(1 for word in spanish_words if word in prompt_lower)
        french_score = sum(1 for word in french_words if word in prompt_lower)
        
        if spanish_score > english_score and spanish_score > french_score:
            return 'es'
        elif french_score > english_score and french_score > spanish_score:
            return 'fr'
        else:
            return 'en'
    
    def _detect_domain(self, prompt: str, task_type: str) -> str:
        """Detect domain of the task."""
        prompt_lower = prompt.lower()
        
        # Technical domain indicators
        tech_keywords = ['code', 'programming', 'algorithm', 'function', 'class', 'api', 'database', 'server']
        if any(keyword in prompt_lower for keyword in tech_keywords):
            return 'technical'
        
        # Creative domain indicators
        creative_keywords = ['story', 'poem', 'creative', 'artistic', 'imagine', 'design', 'write']
        if any(keyword in prompt_lower for keyword in creative_keywords):
            return 'creative'
        
        # Analytical domain indicators
        analytical_keywords = ['analyze', 'data', 'statistics', 'research', 'study', 'report', 'analysis']
        if any(keyword in prompt_lower for keyword in analytical_keywords):
            return 'analytical'
        
        # Business domain indicators
        business_keywords = ['business', 'marketing', 'sales', 'strategy', 'management', 'finance']
        if any(keyword in prompt_lower for keyword in business_keywords):
            return 'business'
        
        return 'general'
    
    def _has_code_content(self, prompt: str) -> bool:
        """Check if prompt contains code."""
        code_indicators = ['```', 'def ', 'class ', 'import ', 'function', 'var ', 'let ', 'const ']
        return any(indicator in prompt for indicator in code_indicators)
    
    def _has_math_content(self, prompt: str) -> bool:
        """Check if prompt contains mathematical content."""
        math_indicators = ['equation', 'formula', 'calculate', 'solve', 'x =', 'y =', 'f(x)', 'derivative', 'integral']
        return any(indicator in prompt.lower() for indicator in math_indicators)
    
    def _has_table_content(self, prompt: str) -> bool:
        """Check if prompt contains tabular data."""
        table_indicators = ['|', 'table', 'row', 'column', 'csv', 'spreadsheet']
        return any(indicator in prompt.lower() for indicator in table_indicators)
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML models."""
        if len(self.performance_history) < 10:
            return np.array([]), np.array([])
        
        # Extract features and targets
        features = []
        targets = []
        
        for perf in self.performance_history:
            if perf.task_features is None:
                continue
                
            # Feature vector
            feature_vector = [
                len(perf.task_features.task_type),  # Task type length as proxy
                perf.task_features.prompt_length,
                perf.task_features.prompt_complexity,
                len(perf.task_features.language),
                len(perf.task_features.domain),
                perf.task_features.urgency_level,
                perf.task_features.quality_requirement,
                perf.task_features.resource_constraint,
                int(perf.task_features.has_code),
                int(perf.task_features.has_math),
                int(perf.task_features.has_tables),
                int(perf.task_features.has_images),
                len(perf.model_id),  # Model ID length as proxy
            ]
            
            # Add file size if available
            if perf.task_features.file_size:
                feature_vector.append(perf.task_features.file_size)
            else:
                feature_vector.append(0)
            
            features.append(feature_vector)
            
            # Composite target score (weighted combination of metrics)
            target_score = (
                0.3 * perf.accuracy_score +
                0.3 * perf.quality_score +
                0.2 * (1.0 - perf.execution_time / 60.0) +  # Normalize execution time
                0.1 * (1.0 - perf.resource_usage) +
                0.1 * perf.success_rate
            )
            targets.append(target_score)
        
        return np.array(features), np.array(targets)
    
    def _train_models(self):
        """Train ML models for model selection."""
        try:
            X, y = self._prepare_training_data()
            
            if len(X) == 0:
                logger.warning("No training data available")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train multiple models
            models = {
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
                'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
                'linear_regression': Ridge(alpha=1.0),
                'neural_network': MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=500, random_state=42)
            }
            
            best_model = None
            best_score = -np.inf
            
            for name, model in models.items():
                try:
                    # Train model
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluate
                    y_pred = model.predict(X_test_scaled)
                    score = r2_score(y_test, y_pred)
                    
                    logger.info(f"Model {name} R² score: {score:.3f}")
                    
                    if score > best_score:
                        best_score = score
                        best_model = (name, model)
                        
                except Exception as e:
                    logger.error(f"Error training {name}: {e}")
                    continue
            
            if best_model:
                self.ml_models['primary'] = best_model[1]
                self.feature_scalers['primary'] = scaler
                
                # Store feature importance if available
                if hasattr(best_model[1], 'feature_importances_'):
                    feature_names = [
                        'task_type_len', 'prompt_length', 'prompt_complexity', 'language_len',
                        'domain_len', 'urgency_level', 'quality_requirement', 'resource_constraint',
                        'has_code', 'has_math', 'has_tables', 'has_images', 'model_id_len', 'file_size'
                    ]
                    self.feature_importance['primary'] = dict(zip(feature_names, best_model[1].feature_importances_))
                
                # Save models
                self._save_models()
                
                logger.info(f"Trained and saved best model: {best_model[0]} with R² score: {best_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
    
    def _save_models(self):
        """Save trained models to disk."""
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            
            model_data = {
                'models': self.ml_models,
                'scalers': self.feature_scalers,
                'encoders': self.label_encoders,
                'importance': self.feature_importance
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def record_performance(self, model_id: str, task_type: str, task_features: TaskFeatures,
                          execution_time: float, accuracy_score: float, quality_score: float,
                          resource_usage: float, cost: float, success_rate: float):
        """Record performance data for a model on a specific task."""
        try:
            performance = ModelPerformance(
                model_id=model_id,
                task_type=task_type,
                execution_time=execution_time,
                accuracy_score=accuracy_score,
                quality_score=quality_score,
                resource_usage=resource_usage,
                cost=cost,
                success_rate=success_rate,
                timestamp=time.time(),
                task_features=task_features
            )
            
            # Add to memory
            self.performance_history.append(performance)
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO model_performance 
                    (model_id, task_type, execution_time, accuracy_score, quality_score,
                     resource_usage, cost, success_rate, timestamp, task_features)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    model_id, task_type, execution_time, accuracy_score, quality_score,
                    resource_usage, cost, success_rate, time.time(),
                    json.dumps(asdict(task_features))
                ))
            
            # Retrain models periodically
            if len(self.performance_history) % 20 == 0:
                self._train_models()
            
            logger.info(f"Recorded performance for {model_id} on {task_type}")
            
        except Exception as e:
            logger.error(f"Error recording performance: {e}")
    
    def select_best_model(self, task_type: str, prompt: str, available_models: List[str], **kwargs) -> ModelSelectionResult:
        """Select the best model using ML-based approach."""
        try:
            # Extract task features
            task_features = self._extract_task_features(task_type, prompt, **kwargs)
            
            # If we have trained models, use them
            if 'primary' in self.ml_models and 'primary' in self.feature_scalers:
                return self._ml_based_selection(task_features, available_models)
            else:
                # Fallback to rule-based selection
                return self._rule_based_selection(task_features, available_models)
                
        except Exception as e:
            logger.error(f"Error in model selection: {e}")
            # Ultimate fallback
            return ModelSelectionResult(
                selected_model=available_models[0] if available_models else "gpt2",
                confidence_score=0.5,
                predicted_performance={},
                alternative_models=[],
                reasoning="Fallback selection due to error",
                feature_importance={}
            )
    
    def _ml_based_selection(self, task_features: TaskFeatures, available_models: List[str]) -> ModelSelectionResult:
        """Use trained ML models for model selection."""
        try:
            # Prepare feature vector
            feature_vector = [
                len(task_features.task_type),
                task_features.prompt_length,
                task_features.prompt_complexity,
                len(task_features.language),
                len(task_features.domain),
                task_features.urgency_level,
                task_features.quality_requirement,
                task_features.resource_constraint,
                int(task_features.has_code),
                int(task_features.has_math),
                int(task_features.has_tables),
                int(task_features.has_images),
                0,  # Model ID length placeholder
                task_features.file_size or 0
            ]
            
            # Scale features
            X = np.array(feature_vector).reshape(1, -1)
            X_scaled = self.feature_scalers['primary'].transform(X)
            
            # Predict performance for each available model
            model_scores = {}
            for model_id in available_models:
                # Update model ID length in feature vector
                X_scaled[0, 12] = len(model_id)
                
                # Predict performance
                predicted_score = self.ml_models['primary'].predict(X_scaled)[0]
                model_scores[model_id] = predicted_score
            
            # Select best model
            best_model = max(model_scores.items(), key=lambda x: x[1])
            selected_model = best_model[0]
            confidence_score = min(1.0, max(0.0, best_model[1]))
            
            # Create alternative models list
            alternative_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)[1:4]
            
            # Generate reasoning
            reasoning = self._generate_reasoning(task_features, selected_model, confidence_score)
            
            return ModelSelectionResult(
                selected_model=selected_model,
                confidence_score=confidence_score,
                predicted_performance=model_scores,
                alternative_models=alternative_models,
                reasoning=reasoning,
                feature_importance=self.feature_importance.get('primary', {})
            )
            
        except Exception as e:
            logger.error(f"Error in ML-based selection: {e}")
            return self._rule_based_selection(task_features, available_models)
    
    def _rule_based_selection(self, task_features: TaskFeatures, available_models: List[str]) -> ModelSelectionResult:
        """Fallback rule-based model selection."""
        # Simple rule-based selection based on task type and features
        model_preferences = {
            'text-generation': ['gpt2', 'gpt2-medium', 'distilgpt2'],
            'text-classification': ['distilbert-base-uncased', 'bert-base-uncased'],
            'summarization': ['facebook/bart-large-cnn', 't5-base'],
            'translation': ['Helsinki-NLP/opus-mt-en-es', 't5-base'],
            'question-answering': ['distilbert-base-cased-distilled-squad', 'bert-base-cased'],
        }
        
        # Find best available model
        preferred_models = model_preferences.get(task_features.task_type, available_models)
        selected_model = None
        
        for model in preferred_models:
            if model in available_models:
                selected_model = model
                break
        
        if not selected_model:
            selected_model = available_models[0] if available_models else "gpt2"
        
        return ModelSelectionResult(
            selected_model=selected_model,
            confidence_score=0.6,
            predicted_performance={model: 0.6 for model in available_models},
            alternative_models=[(model, 0.5) for model in available_models[1:4]],
            reasoning=f"Rule-based selection for {task_features.task_type}",
            feature_importance={}
        )
    
    def _generate_reasoning(self, task_features: TaskFeatures, selected_model: str, confidence: float) -> str:
        """Generate human-readable reasoning for model selection."""
        reasoning_parts = []
        
        reasoning_parts.append(f"Selected {selected_model} for {task_features.task_type} task")
        reasoning_parts.append(f"Confidence: {confidence:.2f}")
        
        if task_features.prompt_complexity > 0.7:
            reasoning_parts.append("High complexity prompt detected")
        
        if task_features.has_code:
            reasoning_parts.append("Code content detected")
        
        if task_features.urgency_level > 0.8:
            reasoning_parts.append("High urgency task")
        
        if task_features.quality_requirement > 0.8:
            reasoning_parts.append("High quality requirement")
        
        return ". ".join(reasoning_parts) + "."
    
    def get_performance_analytics(self) -> Dict[str, Any]:
        """Get analytics on model performance."""
        if not self.performance_history:
            return {"message": "No performance data available"}
        
        # Convert to DataFrame for analysis
        data = []
        for perf in self.performance_history:
            data.append({
                'model_id': perf.model_id,
                'task_type': perf.task_type,
                'execution_time': perf.execution_time,
                'accuracy_score': perf.accuracy_score,
                'quality_score': perf.quality_score,
                'resource_usage': perf.resource_usage,
                'cost': perf.cost,
                'success_rate': perf.success_rate,
                'timestamp': perf.timestamp
            })
        
        df = pd.DataFrame(data)
        
        analytics = {
            'total_records': len(df),
            'unique_models': df['model_id'].nunique(),
            'unique_tasks': df['task_type'].nunique(),
            'avg_accuracy': df['accuracy_score'].mean(),
            'avg_quality': df['quality_score'].mean(),
            'avg_execution_time': df['execution_time'].mean(),
            'best_performing_model': df.groupby('model_id')['accuracy_score'].mean().idxmax(),
            'most_used_model': df['model_id'].mode().iloc[0] if not df.empty else None,
            'performance_by_task': df.groupby('task_type')['accuracy_score'].mean().to_dict(),
            'performance_by_model': df.groupby('model_id')['accuracy_score'].mean().to_dict()
        }
        
        return analytics

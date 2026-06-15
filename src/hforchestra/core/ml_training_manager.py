"""
ML Training Manager for collecting training data and managing model persistence.

This module handles the collection of training data, model training, and persistence
for the machine learning-based model selection system.
"""

import json
import pickle
import sqlite3
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
import queue

from .ml_model_selector import MLModelSelector, TaskFeatures, ModelPerformance

logger = logging.getLogger(__name__)

@dataclass
class TrainingDataPoint:
    """A single training data point."""
    task_type: str
    prompt: str
    selected_model: str
    actual_performance: Dict[str, float]
    task_features: TaskFeatures
    timestamp: float
    user_feedback: Optional[Dict[str, Any]] = None

@dataclass
class ModelTrainingConfig:
    """Configuration for model training."""
    min_samples: int = 50
    retrain_interval_hours: int = 24
    validation_split: float = 0.2
    cross_validation_folds: int = 5
    feature_selection_threshold: float = 0.01
    model_types: List[str] = None
    
    def __post_init__(self):
        if self.model_types is None:
            self.model_types = ['random_forest', 'gradient_boosting', 'linear_regression', 'neural_network']

class MLTrainingManager:
    """
    Manages training data collection, model training, and persistence.
    """
    
    def __init__(self, 
                 db_path: str = "db/ml_training.db",
                 model_path: str = "models/ml_models.pkl",
                 config: Optional[ModelTrainingConfig] = None):
        self.db_path = db_path
        self.model_path = model_path
        self.config = config or ModelTrainingConfig()
        self.ml_selector = MLModelSelector(db_path)
        
        # Training data collection
        self.training_data_queue = queue.Queue()
        self.collection_active = True
        self.collection_thread = None
        
        # Model training
        self.last_training_time = 0
        self.training_in_progress = False
        self.training_lock = threading.Lock()
        
        # Initialize
        self._init_database()
        self._start_data_collection()
        
    def _init_database(self):
        """Initialize database for training data."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Training data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    selected_model TEXT NOT NULL,
                    actual_performance TEXT NOT NULL,
                    task_features TEXT NOT NULL,
                    user_feedback TEXT,
                    timestamp REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model performance tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    training_time REAL,
                    validation_score REAL,
                    timestamp REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Training sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    model_type TEXT NOT NULL,
                    training_samples INTEGER NOT NULL,
                    validation_score REAL,
                    training_time REAL,
                    feature_importance TEXT,
                    config TEXT,
                    timestamp REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_training_task_type ON training_data(task_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_training_timestamp ON training_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_model ON model_performance_tracking(model_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON training_sessions(timestamp)")
    
    def _start_data_collection(self):
        """Start background thread for data collection."""
        self.collection_thread = threading.Thread(target=self._data_collection_worker, daemon=True)
        self.collection_thread.start()
        logger.info("Started training data collection thread")
    
    def _data_collection_worker(self):
        """Background worker for processing training data."""
        while self.collection_active:
            try:
                # Process data from queue
                if not self.training_data_queue.empty():
                    data_point = self.training_data_queue.get(timeout=1)
                    self._store_training_data(data_point)
                    self.training_data_queue.task_done()
                
                # Check if retraining is needed
                if self._should_retrain():
                    self._schedule_retraining()
                
                time.sleep(1)  # Check every second
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in data collection worker: {e}")
                time.sleep(5)  # Wait before retrying
    
    def collect_training_data(self, 
                            task_type: str, 
                            prompt: str, 
                            selected_model: str,
                            actual_performance: Dict[str, float],
                            task_features: TaskFeatures,
                            user_feedback: Optional[Dict[str, Any]] = None):
        """Collect training data for model improvement."""
        try:
            data_point = TrainingDataPoint(
                task_type=task_type,
                prompt=prompt,
                selected_model=selected_model,
                actual_performance=actual_performance,
                task_features=task_features,
                timestamp=time.time(),
                user_feedback=user_feedback
            )
            
            # Add to queue for background processing
            self.training_data_queue.put(data_point)
            
            logger.debug(f"Queued training data for {task_type} with {selected_model}")
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
    
    def _store_training_data(self, data_point: TrainingDataPoint):
        """Store training data in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO training_data 
                    (task_type, prompt, selected_model, actual_performance, task_features, user_feedback, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data_point.task_type,
                    data_point.prompt,
                    data_point.selected_model,
                    json.dumps(data_point.actual_performance),
                    json.dumps(asdict(data_point.task_features)),
                    json.dumps(data_point.user_feedback) if data_point.user_feedback else None,
                    data_point.timestamp
                ))
            
            logger.debug(f"Stored training data for {data_point.task_type}")
            
        except Exception as e:
            logger.error(f"Error storing training data: {e}")
    
    def _should_retrain(self) -> bool:
        """Check if models should be retrained."""
        if self.training_in_progress:
            return False
        
        # Check time interval
        time_since_training = time.time() - self.last_training_time
        if time_since_training < self.config.retrain_interval_hours * 3600:
            return False
        
        # Check if we have enough new data
        new_data_count = self._count_new_training_data()
        if new_data_count < self.config.min_samples:
            return False
        
        return True
    
    def _count_new_training_data(self) -> int:
        """Count new training data since last training."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM training_data 
                    WHERE timestamp > ?
                """, (self.last_training_time,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting new training data: {e}")
            return 0
    
    def _schedule_retraining(self):
        """Schedule model retraining."""
        if self.training_in_progress:
            return
        
        # Start retraining in a separate thread
        retrain_thread = threading.Thread(target=self._retrain_models, daemon=True)
        retrain_thread.start()
    
    def _retrain_models(self):
        """Retrain ML models with new data."""
        with self.training_lock:
            if self.training_in_progress:
                return
            
            self.training_in_progress = True
            
        try:
            logger.info("Starting model retraining...")
            start_time = time.time()
            
            # Load training data
            training_data = self._load_training_data()
            
            if len(training_data) < self.config.min_samples:
                logger.warning(f"Insufficient training data: {len(training_data)} < {self.config.min_samples}")
                return
            
            # Train models
            training_results = self._train_models_with_data(training_data)
            
            # Save results
            self._save_training_results(training_results, time.time() - start_time)
            
            # Update ML selector
            self.ml_selector._train_models()
            
            self.last_training_time = time.time()
            logger.info(f"Model retraining completed in {time.time() - start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during model retraining: {e}")
        finally:
            self.training_in_progress = False
    
    def _load_training_data(self) -> List[TrainingDataPoint]:
        """Load training data from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT task_type, prompt, selected_model, actual_performance, 
                           task_features, user_feedback, timestamp
                    FROM training_data
                    ORDER BY timestamp DESC
                """)
                
                training_data = []
                for row in cursor.fetchall():
                    data_point = TrainingDataPoint(
                        task_type=row[0],
                        prompt=row[1],
                        selected_model=row[2],
                        actual_performance=json.loads(row[3]),
                        task_features=TaskFeatures(**json.loads(row[4])),
                        user_feedback=json.loads(row[5]) if row[5] else None,
                        timestamp=row[6]
                    )
                    training_data.append(data_point)
                
                return training_data
                
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return []
    
    def _train_models_with_data(self, training_data: List[TrainingDataPoint]) -> Dict[str, Any]:
        """Train models with collected data."""
        try:
            # Convert to DataFrame for easier processing
            data = []
            for point in training_data:
                features = asdict(point.task_features)
                features.update({
                    'selected_model': point.selected_model,
                    'actual_accuracy': point.actual_performance.get('accuracy', 0.0),
                    'actual_quality': point.actual_performance.get('quality', 0.0),
                    'actual_execution_time': point.actual_performance.get('execution_time', 0.0),
                    'actual_resource_usage': point.actual_performance.get('resource_usage', 0.0),
                    'actual_cost': point.actual_performance.get('cost', 0.0),
                    'actual_success_rate': point.actual_performance.get('success_rate', 0.0)
                })
                data.append(features)
            
            df = pd.DataFrame(data)
            
            # Prepare features and targets
            feature_columns = [
                'prompt_length', 'prompt_complexity', 'urgency_level', 
                'quality_requirement', 'resource_constraint', 'has_code', 
                'has_math', 'has_tables', 'has_images'
            ]
            
            # Add model-specific features
            model_encoder = LabelEncoder()
            df['model_encoded'] = model_encoder.fit_transform(df['selected_model'])
            feature_columns.append('model_encoded')
            
            # Add task type features
            task_encoder = LabelEncoder()
            df['task_encoded'] = task_encoder.fit_transform(df['task_type'])
            feature_columns.append('task_encoded')
            
            X = df[feature_columns].values
            y = df['actual_accuracy'].values  # Use accuracy as primary target
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.validation_split, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train models
            results = {}
            for model_type in self.config.model_types:
                try:
                    model = self._create_model(model_type)
                    
                    # Train
                    start_time = time.time()
                    model.fit(X_train_scaled, y_train)
                    training_time = time.time() - start_time
                    
                    # Evaluate
                    y_pred = model.predict(X_test_scaled)
                    validation_score = r2_score(y_test, y_pred)
                    
                    # Cross-validation
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, 
                                              cv=self.config.cross_validation_folds)
                    
                    results[model_type] = {
                        'model': model,
                        'validation_score': validation_score,
                        'cv_mean': cv_scores.mean(),
                        'cv_std': cv_scores.std(),
                        'training_time': training_time,
                        'feature_importance': self._get_feature_importance(model, feature_columns)
                    }
                    
                    logger.info(f"Trained {model_type}: validation_score={validation_score:.3f}, "
                              f"cv_mean={cv_scores.mean():.3f}±{cv_scores.std():.3f}")
                    
                except Exception as e:
                    logger.error(f"Error training {model_type}: {e}")
                    continue
            
            # Select best model
            if results:
                best_model_type = max(results.keys(), key=lambda k: results[k]['validation_score'])
                results['best_model'] = best_model_type
                results['scaler'] = scaler
                results['feature_columns'] = feature_columns
                results['model_encoder'] = model_encoder
                results['task_encoder'] = task_encoder
            
            return results
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return {}
    
    def _create_model(self, model_type: str):
        """Create a model instance based on type."""
        from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
        from sklearn.linear_model import Ridge
        from sklearn.neural_network import MLPRegressor
        
        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'linear_regression': Ridge(alpha=1.0),
            'neural_network': MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=500, random_state=42)
        }
        
        return models.get(model_type, RandomForestRegressor(n_estimators=100, random_state=42))
    
    def _get_feature_importance(self, model, feature_columns: List[str]) -> Dict[str, float]:
        """Get feature importance from trained model."""
        if hasattr(model, 'feature_importances_'):
            return dict(zip(feature_columns, model.feature_importances_))
        elif hasattr(model, 'coef_'):
            return dict(zip(feature_columns, abs(model.coef_)))
        else:
            return {}
    
    def _save_training_results(self, results: Dict[str, Any], total_time: float):
        """Save training results to database."""
        try:
            session_id = f"training_{int(time.time())}"
            
            with sqlite3.connect(self.db_path) as conn:
                for model_type, result in results.items():
                    if model_type in ['best_model', 'scaler', 'feature_columns', 'model_encoder', 'task_encoder']:
                        continue
                    
                    conn.execute("""
                        INSERT INTO training_sessions 
                        (session_id, model_type, training_samples, validation_score, 
                         training_time, feature_importance, config, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        model_type,
                        len(self._load_training_data()),
                        result['validation_score'],
                        result['training_time'],
                        json.dumps(result['feature_importance']),
                        json.dumps(asdict(self.config)),
                        time.time()
                    ))
            
            # Save models to disk
            self._save_models_to_disk(results)
            
            logger.info(f"Saved training results for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving training results: {e}")
    
    def _save_models_to_disk(self, results: Dict[str, Any]):
        """Save trained models to disk."""
        try:
            Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save the best model and related data
            save_data = {
                'best_model_type': results.get('best_model'),
                'models': {k: v for k, v in results.items() if k not in ['best_model', 'scaler', 'feature_columns', 'model_encoder', 'task_encoder']},
                'scaler': results.get('scaler'),
                'feature_columns': results.get('feature_columns'),
                'model_encoder': results.get('model_encoder'),
                'task_encoder': results.get('task_encoder'),
                'config': asdict(self.config),
                'timestamp': time.time()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(save_data, f)
            
            logger.info("Saved models to disk")
            
        except Exception as e:
            logger.error(f"Error saving models to disk: {e}")
    
    def load_models_from_disk(self) -> Dict[str, Any]:
        """Load trained models from disk."""
        try:
            if not Path(self.model_path).exists():
                logger.info("No saved models found")
                return {}
            
            with open(self.model_path, 'rb') as f:
                save_data = pickle.load(f)
            
            logger.info("Loaded models from disk")
            return save_data
            
        except Exception as e:
            logger.error(f"Error loading models from disk: {e}")
            return {}
    
    def get_training_analytics(self) -> Dict[str, Any]:
        """Get analytics on training data and model performance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Training data statistics
                cursor = conn.execute("SELECT COUNT(*) FROM training_data")
                total_samples = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT task_type) FROM training_data")
                unique_tasks = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT selected_model) FROM training_data")
                unique_models = cursor.fetchone()[0]
                
                # Recent training sessions
                cursor = conn.execute("""
                    SELECT model_type, validation_score, training_time, timestamp
                    FROM training_sessions
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)
                recent_sessions = cursor.fetchall()
                
                # Performance by task type
                cursor = conn.execute("""
                    SELECT task_type, COUNT(*) as count, AVG(CAST(json_extract(actual_performance, '$.accuracy') AS REAL)) as avg_accuracy
                    FROM training_data
                    GROUP BY task_type
                    ORDER BY count DESC
                """)
                task_performance = cursor.fetchall()
                
                return {
                    'total_training_samples': total_samples,
                    'unique_task_types': unique_tasks,
                    'unique_models': unique_models,
                    'recent_training_sessions': [
                        {
                            'model_type': row[0],
                            'validation_score': row[1],
                            'training_time': row[2],
                            'timestamp': row[3]
                        } for row in recent_sessions
                    ],
                    'task_performance': [
                        {
                            'task_type': row[0],
                            'sample_count': row[1],
                            'avg_accuracy': row[2]
                        } for row in task_performance
                    ],
                    'last_training_time': self.last_training_time,
                    'training_in_progress': self.training_in_progress,
                    'queue_size': self.training_data_queue.qsize()
                }
                
        except Exception as e:
            logger.error(f"Error getting training analytics: {e}")
            return {'error': str(e)}
    
    def force_retrain(self):
        """Force immediate model retraining."""
        if not self.training_in_progress:
            retrain_thread = threading.Thread(target=self._retrain_models, daemon=True)
            retrain_thread.start()
            logger.info("Forced model retraining started")
        else:
            logger.warning("Training already in progress")
    
    def stop_data_collection(self):
        """Stop background data collection."""
        self.collection_active = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("Stopped training data collection")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old training data."""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM training_data WHERE timestamp < ?", (cutoff_time,))
                deleted_count = cursor.rowcount
                
                cursor = conn.execute("DELETE FROM training_sessions WHERE timestamp < ?", (cutoff_time,))
                deleted_sessions = cursor.rowcount
                
                conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old training data points and {deleted_sessions} old training sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

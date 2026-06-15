#!/usr/bin/env python3
"""
Advanced Data Science Model Selection System
Uses sophisticated algorithms to dynamically select the best models based on multiple criteria.
"""

import sqlite3
import pandas as pd
import numpy as np
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ModelSelectionCriteria:
    """Criteria for model selection with weights."""
    popularity_weight: float = 0.35      # Downloads importance
    engagement_weight: float = 0.25      # Likes/downloads ratio importance
    performance_weight: float = 0.20     # Decision/capability scores importance
    efficiency_weight: float = 0.10      # Model size/speed importance
    license_weight: float = 0.05         # Open license preference
    recency_weight: float = 0.05         # How recent the model is

@dataclass
class ModelScore:
    """Comprehensive model scoring result."""
    model_id: str
    final_score: float
    popularity_score: float
    engagement_score: float
    performance_score: float
    efficiency_score: float
    license_score: float
    recency_score: float
    confidence: float
    ranking: int
    metadata: Dict[str, Any]

class AdvancedModelSelector:
    """Advanced model selection using data science techniques."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.criteria = ModelSelectionCriteria()
        
        # Preferred licenses (open source)
        self.open_licenses = {
            "apache-2.0", "mit", "cc-by-4.0", "cc0-1.0", "openrail", "openrail++", 
            "bsd-3-clause", "gpl-3.0", "lgpl-3.0", "cc-by-sa-4.0", "unlicense"
        }
        
        # Task complexity weights (more complex tasks need better models)
        self.task_complexity = {
            'text-generation': 0.9,
            'question-answering': 0.8,
            'summarization': 0.8,
            'translation': 0.7,
            'text-classification': 0.6,
            'sentiment-analysis': 0.5,
            'token-classification': 0.6,
            'fill-mask': 0.5,
            'zero-shot-classification': 0.7,
            'image-classification': 0.7,
            'object-detection': 0.8,
            'automatic-speech-recognition': 0.8,
            'audio-classification': 0.6
        }
    
    def update_criteria(self, **kwargs):
        """Update selection criteria weights."""
        for key, value in kwargs.items():
            if hasattr(self.criteria, key):
                setattr(self.criteria, key, value)
                logger.info(f"Updated {key} to {value}")
    
    async def get_models_from_database(self, task_name: str, limit: int = 50) -> pd.DataFrame:
        """Get models from database with enhanced data."""
        try:
            # Map task names to database pipeline tags
            task_mapping = {
                'text-classification': ['text-classification', 'text_classification'],
                'sentiment': ['sentiment-analysis', 'sentiment_analysis', 'text-classification'],
                'sentiment-analysis': ['sentiment-analysis', 'sentiment_analysis', 'text-classification'],
                'question-answering': ['question-answering', 'question_answering'],
                'question': ['question-answering', 'question_answering'],
                'summarization': ['summarization', 'text2text-generation'],
                'summary': ['summarization', 'text2text-generation'],
                'translation': ['translation', 'text2text-generation'],
                'ner': ['token-classification', 'named-entity-recognition'],
                'image-classification': ['image-classification'],
                'object-detection': ['object-detection'],
                'speech-recognition': ['automatic-speech-recognition'],
                'automatic-speech-recognition': ['automatic-speech-recognition'],
                'audio-classification': ['audio-classification'],
                'text-generation': ['text-generation', 'text2text-generation'],
                'zero-shot-classification': ['zero-shot-classification', 'text-classification'],
                'fill-mask': ['fill-mask'],
                'token-classification': ['token-classification']
            }
            
            pipeline_tags = task_mapping.get(task_name, [task_name])
            
            with sqlite3.connect(self.db_path) as conn:
                # Enhanced query with more fields
                placeholders = ','.join(['?' for _ in pipeline_tags])
                query = f"""
                    SELECT 
                        model_id, 
                        pipeline_tag,
                        downloads,
                        likes,
                        decision_score,
                        capability_score,
                        efficiency_score,
                        popularity_score,
                        description,
                        author,
                        model_type,
                        library_name,
                        last_modified,
                        created_at,
                        tags
                    FROM models 
                    WHERE pipeline_tag IN ({placeholders})
                    AND downloads > 10
                    AND model_id NOT LIKE '%nsfw%'
                    AND model_id NOT LIKE '%adult%'
                    ORDER BY downloads DESC, likes DESC
                    LIMIT ?
                """
                
                df = pd.read_sql_query(query, conn, params=pipeline_tags + [limit])
                
                if df.empty:
                    logger.warning(f"No models found for task: {task_name}")
                    return pd.DataFrame()
                
                logger.info(f"Found {len(df)} models for task: {task_name}")
                return df
                
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return pd.DataFrame()
    
    def calculate_popularity_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate popularity score using log-normal distribution."""
        downloads = df['downloads'].fillna(0)
        if downloads.max() == 0:
            return pd.Series([0.0] * len(df))
        
        # Use log scale for downloads (popular models have exponentially more downloads)
        log_downloads = np.log1p(downloads)  # log(1 + x) to handle zeros
        normalized = (log_downloads - log_downloads.min()) / (log_downloads.max() - log_downloads.min())
        
        return normalized.fillna(0.0)
    
    def calculate_engagement_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate engagement score (likes per download ratio)."""
        downloads = df['downloads'].fillna(0)
        likes = df['likes'].fillna(0)
        
        # Prevent division by zero
        engagement = likes / (downloads + 1)  # Add 1 to avoid division by zero
        
        if engagement.max() == 0:
            return pd.Series([0.0] * len(df))
        
        # Normalize engagement scores
        normalized = (engagement - engagement.min()) / (engagement.max() - engagement.min())
        return normalized.fillna(0.0)
    
    def calculate_performance_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate performance score from model metrics."""
        # Combine different performance metrics
        decision_score = df['decision_score'].fillna(0.0)
        capability_score = df['capability_score'].fillna(0.0)
        
        # Weighted combination of scores
        performance = (decision_score * 0.6 + capability_score * 0.4)
        
        if performance.max() == 0:
            return pd.Series([0.0] * len(df))
        
        # Normalize to 0-1 range
        normalized = performance / performance.max()
        return normalized.fillna(0.0)
    
    def calculate_efficiency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate efficiency score based on model characteristics."""
        efficiency_score = df['efficiency_score'].fillna(0.5)  # Default neutral score
        
        # Additional efficiency factors
        efficiency_factors = pd.Series([0.0] * len(df))
        
        # Boost score for models with efficiency indicators in name/description
        for idx, row in df.iterrows():
            model_id = str(row['model_id']).lower()
            description = str(row['description']).lower() if pd.notna(row['description']) else ""
            
            # Check for efficiency keywords
            if any(keyword in model_id or keyword in description for keyword in 
                   ['distil', 'mobile', 'tiny', 'small', 'light', 'fast', 'efficient']):
                efficiency_factors.iloc[idx] += 0.3
            
            # Check for model type efficiency
            if 'distilbert' in model_id or 'mobilenet' in model_id or 'efficientnet' in model_id:
                efficiency_factors.iloc[idx] += 0.2
        
        # Combine database efficiency score with calculated factors
        final_efficiency = (efficiency_score + efficiency_factors).clip(0, 1)
        
        return final_efficiency
    
    def calculate_license_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate license score based on openness."""
        # Note: License info might not be in current database schema
        # This is a placeholder that can be enhanced when license data is available
        
        license_scores = pd.Series([0.5] * len(df))  # Default neutral score
        
        # Enhanced scoring based on model characteristics that often correlate with open licenses
        for idx, row in df.iterrows():
            model_id = str(row['model_id']).lower()
            author = str(row['author']).lower() if pd.notna(row['author']) else ""
            
            # Boost score for known open organizations
            if any(org in author for org in ['huggingface', 'google', 'facebook', 'microsoft', 'openai']):
                license_scores.iloc[idx] = 0.8
            
            # Boost for community models (often more open)
            if any(keyword in model_id for keyword in ['community', 'open', 'free']):
                license_scores.iloc[idx] = 0.9
        
        return license_scores
    
    def calculate_recency_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate recency score based on last modification date."""
        try:
            # Convert timestamp to datetime
            last_modified = pd.to_datetime(df['last_modified'], errors='coerce')
            current_time = pd.Timestamp.now()
            
            # Calculate days since last modification
            days_since = (current_time - last_modified).dt.days.fillna(365)  # Default to 1 year if unknown
            
            # Exponential decay: newer models get higher scores
            # Models modified in last 30 days get full score, older models decay
            recency = np.exp(-days_since / 180)  # 180-day half-life
            
            return recency.fillna(0.3)  # Default score for unknown dates
            
        except Exception as e:
            logger.warning(f"Error calculating recency score: {e}")
            return pd.Series([0.5] * len(df))  # Default neutral score
    
    def apply_task_complexity_adjustment(self, scores: pd.DataFrame, task_name: str) -> pd.DataFrame:
        """Adjust scores based on task complexity."""
        complexity = self.task_complexity.get(task_name, 0.7)
        
        # For complex tasks, boost performance and efficiency more
        if complexity > 0.7:
            scores['performance_score'] *= 1.2
            scores['efficiency_score'] *= 1.1
        
        # For simple tasks, popularity and engagement matter more
        elif complexity < 0.6:
            scores['popularity_score'] *= 1.1
            scores['engagement_score'] *= 1.1
        
        return scores
    
    def calculate_confidence_score(self, scores: pd.DataFrame) -> pd.Series:
        """Calculate confidence in the selection based on score variance and data quality."""
        confidence_scores = pd.Series([0.0] * len(scores))
        
        for idx, row in scores.iterrows():
            # Base confidence on score consistency
            score_values = [
                row['popularity_score'],
                row['engagement_score'], 
                row['performance_score'],
                row['efficiency_score']
            ]
            
            # Higher confidence if scores are consistently high or low
            score_variance = np.var(score_values)
            mean_score = np.mean(score_values)
            
            # Confidence increases with score consistency and higher means
            base_confidence = max(0.1, 1.0 - score_variance)
            score_boost = min(0.3, mean_score * 0.3)
            
            # Data quality factors
            data_quality = 0.0
            if row.get('downloads', 0) > 1000:
                data_quality += 0.2
            if row.get('likes', 0) > 10:
                data_quality += 0.1
            if pd.notna(row.get('description', '')):
                data_quality += 0.1
            
            final_confidence = min(1.0, base_confidence + score_boost + data_quality)
            confidence_scores.iloc[idx] = final_confidence
        
        return confidence_scores
    
    async def select_best_models(
        self, 
        task_name: str, 
        top_k: int = 5,
        custom_criteria: Optional[ModelSelectionCriteria] = None
    ) -> List[ModelScore]:
        """Select best models using advanced data science techniques."""
        
        try:
            logger.info(f"🔬 [DATA SCIENCE] Starting advanced model selection for task: {task_name}")
            
            # Use custom criteria if provided
            criteria = custom_criteria or self.criteria
            
            # Get models from database
            df = await self.get_models_from_database(task_name)
            
            if df.empty:
                logger.warning(f"No models found for task: {task_name}")
                return []
            
            # Calculate individual scores
            logger.info("📊 Calculating individual score components...")
            
            scores_df = df.copy()
            scores_df['popularity_score'] = self.calculate_popularity_score(df)
            scores_df['engagement_score'] = self.calculate_engagement_score(df)
            scores_df['performance_score'] = self.calculate_performance_score(df)
            scores_df['efficiency_score'] = self.calculate_efficiency_score(df)
            scores_df['license_score'] = self.calculate_license_score(df)
            scores_df['recency_score'] = self.calculate_recency_score(df)
            
            # Apply task complexity adjustments
            scores_df = self.apply_task_complexity_adjustment(scores_df, task_name)
            
            # Calculate final weighted score
            logger.info("🧮 Computing weighted final scores...")
            scores_df['final_score'] = (
                criteria.popularity_weight * scores_df['popularity_score'] +
                criteria.engagement_weight * scores_df['engagement_score'] +
                criteria.performance_weight * scores_df['performance_score'] +
                criteria.efficiency_weight * scores_df['efficiency_score'] +
                criteria.license_weight * scores_df['license_score'] +
                criteria.recency_weight * scores_df['recency_score']
            )
            
            # Calculate confidence scores
            scores_df['confidence'] = self.calculate_confidence_score(scores_df)
            
            # Sort by final score and confidence
            scores_df = scores_df.sort_values(
                by=['final_score', 'confidence'], 
                ascending=[False, False]
            )
            
            # Create ModelScore objects for top models
            results = []
            for idx, (_, row) in enumerate(scores_df.head(top_k).iterrows()):
                model_score = ModelScore(
                    model_id=row['model_id'],
                    final_score=row['final_score'],
                    popularity_score=row['popularity_score'],
                    engagement_score=row['engagement_score'],
                    performance_score=row['performance_score'],
                    efficiency_score=row['efficiency_score'],
                    license_score=row['license_score'],
                    recency_score=row['recency_score'],
                    confidence=row['confidence'],
                    ranking=idx + 1,
                    metadata={
                        'downloads': row.get('downloads', 0),
                        'likes': row.get('likes', 0),
                        'pipeline_tag': row.get('pipeline_tag', ''),
                        'author': row.get('author', ''),
                        'description': row.get('description', ''),
                        'library_name': row.get('library_name', ''),
                        'task_complexity': self.task_complexity.get(task_name, 0.7)
                    }
                )
                results.append(model_score)
            
            logger.info(f"✅ [DATA SCIENCE] Selected {len(results)} models using advanced algorithms")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in advanced model selection: {e}")
            return []
    
    def explain_selection(self, model_scores: List[ModelScore]) -> str:
        """Generate explanation for model selection decisions."""
        if not model_scores:
            return "No models selected."
        
        explanation = ["🔬 DATA SCIENCE MODEL SELECTION EXPLANATION", "=" * 60]
        
        best_model = model_scores[0]
        explanation.append(f"\n🏆 SELECTED MODEL: {best_model.model_id}")
        explanation.append(f"   Final Score: {best_model.final_score:.3f}")
        explanation.append(f"   Confidence: {best_model.confidence:.3f}")
        explanation.append(f"   Downloads: {best_model.metadata['downloads']:,}")
        explanation.append(f"   Likes: {best_model.metadata['likes']:,}")
        
        explanation.append(f"\n📊 SCORE BREAKDOWN:")
        explanation.append(f"   Popularity:  {best_model.popularity_score:.3f} (weight: {self.criteria.popularity_weight:.2f})")
        explanation.append(f"   Engagement:  {best_model.engagement_score:.3f} (weight: {self.criteria.engagement_weight:.2f})")
        explanation.append(f"   Performance: {best_model.performance_score:.3f} (weight: {self.criteria.performance_weight:.2f})")
        explanation.append(f"   Efficiency:  {best_model.efficiency_score:.3f} (weight: {self.criteria.efficiency_weight:.2f})")
        explanation.append(f"   License:     {best_model.license_score:.3f} (weight: {self.criteria.license_weight:.2f})")
        explanation.append(f"   Recency:     {best_model.recency_score:.3f} (weight: {self.criteria.recency_weight:.2f})")
        
        if len(model_scores) > 1:
            explanation.append(f"\n🔄 ALTERNATIVE MODELS:")
            for model in model_scores[1:4]:  # Show top 3 alternatives
                explanation.append(f"   {model.ranking}. {model.model_id} (score: {model.final_score:.3f})")
        
        explanation.append(f"\n📈 SELECTION METHODOLOGY:")
        explanation.append(f"   • Used weighted scoring across {len(self.criteria.__dict__)} criteria")
        explanation.append(f"   • Task complexity factor: {self.task_complexity.get('unknown', 0.7):.2f}")
        explanation.append(f"   • Analyzed {len(model_scores)} top candidates")
        explanation.append(f"   • Applied data science normalization and confidence scoring")
        
        return "\n".join(explanation)

# Create global instance
advanced_model_selector = AdvancedModelSelector()
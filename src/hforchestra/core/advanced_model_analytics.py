#!/usr/bin/env python3
"""
Advanced SQLite Model Analytics and Query Patterns
==================================================

This module provides sophisticated querying, analytics, and optimization
patterns for your stored Hugging Face model data.
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime, timedelta
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class AdvancedModelAnalytics:
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.setup_advanced_features()
    
    def setup_advanced_features(self):
        """Set up advanced SQLite features and indexes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                
                # Optimize for performance
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                
                # Create advanced indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_models_score_desc ON models(final_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_task_score ON models(pipeline_tag, final_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_downloads_likes ON models(downloads, likes)",
                    "CREATE INDEX IF NOT EXISTS idx_models_size_license ON models(size_mb, license_score)",
                    "CREATE INDEX IF NOT EXISTS idx_models_last_modified ON models(last_modified)",
                    "CREATE INDEX IF NOT EXISTS idx_models_download_date ON models(download_date)",
                    # Composite index for common filtering patterns
                    "CREATE INDEX IF NOT EXISTS idx_models_composite ON models(pipeline_tag, license_score, size_mb, final_score DESC)",
                    # Performance optimization indexes
                    "CREATE INDEX IF NOT EXISTS idx_models_performance ON models(downloads DESC, likes DESC, final_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_efficiency ON models(size_mb ASC, final_score DESC)"
                ]
                
                for idx in indexes:
                    try:
                        conn.execute(idx)
                    except sqlite3.Error as e:
                        logger.warning(f"Index creation warning: {e}")
                
                logger.info("✅ Advanced SQLite features and indexes set up successfully")
                
        except Exception as e:
            logger.error(f"❌ Error setting up advanced features: {e}")
    
    def dynamic_model_ranking(self, 
                            task: str = None,
                            min_downloads: int = None,
                            max_size_mb: float = None,
                            open_license_only: bool = False,
                            custom_weights: Dict[str, float] = None,
                            limit: int = 10) -> pd.DataFrame:
        """
        Dynamic re-ranking with custom criteria and weights
        """
        try:
            base_query = """
            SELECT model_id, pipeline_tag, downloads, likes, license, size_mb, 
                   last_modified, tags, final_score, popularity_score, engagement_score,
                   license_score, lightweight, download_date,
                   -- Dynamic scoring with custom weights
                   CASE 
                       WHEN ? IS NOT NULL THEN 
                           (? * (downloads * 1.0 / NULLIF(MAX(downloads) OVER(), 0))) +
                           (? * (likes * 1.0 / NULLIF(downloads, 0))) +
                           (? * license_score) +
                           (? * CASE WHEN size_mb < 500 THEN 1 ELSE 0 END) +
                           (? * task_match)
                       ELSE final_score 
                   END as dynamic_score
            FROM models
            WHERE 1=1
            """
            
            conditions = []
            params = []
            
            # Custom weights (if provided)
            if custom_weights:
                params.extend([
                    1,  # Flag to use custom weights
                    custom_weights.get('popularity', 0.4),
                    custom_weights.get('engagement', 0.25),
                    custom_weights.get('license', 0.15),
                    custom_weights.get('lightweight', 0.1),
                    custom_weights.get('task_match', 0.1)
                ])
            else:
                params.extend([None] * 6)
            
            # Add filtering conditions
            if task:
                conditions.append("AND pipeline_tag = ?")
                params.append(task)
            
            if min_downloads:
                conditions.append("AND downloads >= ?")
                params.append(min_downloads)
            
            if max_size_mb:
                conditions.append("AND (size_mb IS NULL OR size_mb <= ?)")
                params.append(max_size_mb)
            
            if open_license_only:
                conditions.append("AND license_score = 1")
            
            query = base_query + " ".join(conditions) + " ORDER BY dynamic_score DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
                
        except Exception as e:
            logger.error(f"❌ Error in dynamic model ranking: {e}")
            return pd.DataFrame()
    
    def model_trend_analysis(self, days_back: int = 30) -> pd.DataFrame:
        """
        Analyze model trends over time
        """
        try:
            query = """
            WITH trend_data AS (
                SELECT 
                    pipeline_tag,
                    DATE(COALESCE(last_modified, download_date)) as mod_date,
                    COUNT(*) as models_updated,
                    AVG(downloads) as avg_downloads,
                    AVG(likes) as avg_likes,
                    AVG(final_score) as avg_score
                FROM models 
                WHERE COALESCE(last_modified, download_date) >= date('now', '-{} days')
                GROUP BY pipeline_tag, DATE(COALESCE(last_modified, download_date))
            )
            SELECT 
                pipeline_tag,
                COUNT(*) as active_days,
                SUM(models_updated) as total_updates,
                AVG(avg_downloads) as trend_avg_downloads,
                AVG(avg_score) as trend_avg_score,
                -- Calculate momentum (recent activity)
                SUM(CASE WHEN mod_date >= date('now', '-7 days') 
                         THEN models_updated ELSE 0 END) as recent_activity
            FROM trend_data
            GROUP BY pipeline_tag
            ORDER BY recent_activity DESC, trend_avg_score DESC
            """.format(days_back)
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn)
                
        except Exception as e:
            logger.error(f"❌ Error in trend analysis: {e}")
            return pd.DataFrame()
    
    def similarity_clustering(self, model_id: str, top_k: int = 5) -> pd.DataFrame:
        """
        Find similar models using feature-based similarity
        """
        try:
            query = """
            WITH target_model AS (
                SELECT downloads, likes, size_mb, license_score, pipeline_tag, final_score
                FROM models WHERE model_id = ?
            ),
            similarity_scores AS (
                SELECT 
                    m.model_id,
                    m.pipeline_tag,
                    m.downloads,
                    m.likes,
                    m.final_score,
                    -- Calculate similarity score using normalized differences
                    (1.0 - COALESCE(ABS(
                        (m.downloads - t.downloads) * 1.0 / NULLIF(GREATEST(m.downloads, t.downloads), 0)
                    ), 0)) * 0.4 +
                    (1.0 - COALESCE(ABS(
                        (COALESCE(m.size_mb, 0) - COALESCE(t.size_mb, 0)) / NULLIF(GREATEST(COALESCE(m.size_mb, 1), COALESCE(t.size_mb, 1)), 0)
                    ), 0)) * 0.3 +
                    (CASE WHEN m.license_score = t.license_score THEN 1 ELSE 0 END) * 0.2 +
                    (CASE WHEN m.pipeline_tag = t.pipeline_tag THEN 1 ELSE 0 END) * 0.1
                    as similarity_score
                FROM models m, target_model t
                WHERE m.model_id != ?
            )
            SELECT model_id, pipeline_tag, downloads, likes, final_score, similarity_score
            FROM similarity_scores
            WHERE similarity_score > 0.1  -- Filter out very dissimilar models
            ORDER BY similarity_score DESC
            LIMIT ?
            """
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=[model_id, model_id, top_k])
                
        except Exception as e:
            logger.error(f"❌ Error in similarity clustering: {e}")
            return pd.DataFrame()
    
    def advanced_aggregations(self) -> Dict[str, pd.DataFrame]:
        """
        Compute advanced analytics and insights
        """
        results = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # License distribution and quality metrics
                results['license_analysis'] = pd.read_sql_query("""
                    SELECT 
                        COALESCE(license, 'Unknown') as license,
                        COUNT(*) as model_count,
                        AVG(downloads) as avg_downloads,
                        AVG(final_score) as avg_score,
                        SUM(downloads) as total_downloads,
                        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM models), 2) as percentage
                    FROM models
                    GROUP BY COALESCE(license, 'Unknown')
                    ORDER BY model_count DESC
                """, conn)
                
                # Size distribution analysis
                results['size_analysis'] = pd.read_sql_query("""
                    SELECT 
                        CASE 
                            WHEN size_mb IS NULL THEN 'Unknown'
                            WHEN size_mb < 100 THEN 'Small (<100MB)'
                            WHEN size_mb < 500 THEN 'Medium (100-500MB)'
                            WHEN size_mb < 2000 THEN 'Large (500MB-2GB)'
                            ELSE 'Very Large (>2GB)'
                        END as size_category,
                        COUNT(*) as model_count,
                        AVG(downloads) as avg_downloads,
                        AVG(final_score) as avg_score
                    FROM models
                    GROUP BY size_category
                    ORDER BY avg_score DESC
                """, conn)
                
                # Task performance metrics
                results['task_performance'] = pd.read_sql_query("""
                    SELECT 
                        COALESCE(pipeline_tag, 'Unknown') as pipeline_tag,
                        COUNT(*) as model_count,
                        AVG(final_score) as avg_score,
                        MAX(final_score) as max_score,
                        AVG(downloads) as avg_downloads,
                        MAX(downloads) as max_downloads,
                        -- Quality distribution
                        SUM(CASE WHEN final_score > 0.8 THEN 1 ELSE 0 END) as high_quality_count,
                        SUM(CASE WHEN license_score = 1 THEN 1 ELSE 0 END) as open_license_count
                    FROM models
                    GROUP BY COALESCE(pipeline_tag, 'Unknown')
                    HAVING model_count >= 5  -- Only include tasks with sufficient data
                    ORDER BY avg_score DESC
                """, conn)
                
                # Engagement analysis
                results['engagement_analysis'] = pd.read_sql_query("""
                    SELECT 
                        model_id,
                        COALESCE(pipeline_tag, 'Unknown') as pipeline_tag,
                        downloads,
                        likes,
                        ROUND(likes * 1.0 / NULLIF(downloads, 0), 6) as engagement_ratio,
                        final_score,
                        CASE 
                            WHEN likes * 1.0 / NULLIF(downloads, 0) > 0.001 THEN 'High Engagement'
                            WHEN likes * 1.0 / NULLIF(downloads, 0) > 0.0001 THEN 'Medium Engagement'
                            ELSE 'Low Engagement'
                        END as engagement_category
                    FROM models
                    WHERE downloads > 100  -- Filter out models with very low downloads
                    ORDER BY engagement_ratio DESC
                    LIMIT 20
                """, conn)
                
                # Download trends (if download_date is available)
                results['download_trends'] = pd.read_sql_query("""
                    SELECT 
                        DATE(download_date) as download_day,
                        COUNT(*) as models_downloaded,
                        AVG(final_score) as avg_score_downloaded
                    FROM models
                    WHERE download_date IS NOT NULL
                    GROUP BY DATE(download_date)
                    ORDER BY download_day DESC
                    LIMIT 30
                """, conn)
                
        except Exception as e:
            logger.error(f"❌ Error in advanced aggregations: {e}")
            
        return results
    
    def create_model_recommendation_system(self, user_preferences: Dict) -> pd.DataFrame:
        """
        Advanced recommendation system based on user preferences
        
        user_preferences = {
            'tasks': ['text-generation', 'text-classification'],
            'max_size_mb': 1000,
            'min_downloads': 1000,
            'license_preference': 'open',  # 'open', 'any'
            'performance_weight': 0.6,     # vs popularity weight
        }
        """
        try:
            tasks = user_preferences.get('tasks', [])
            if not tasks:
                return pd.DataFrame()
            
            # Build dynamic query based on preferences
            task_placeholders = ','.join(['?'] * len(tasks))
            base_query = f"""
            SELECT 
                model_id, pipeline_tag, downloads, likes, license, size_mb, final_score,
                -- Custom recommendation score
                (final_score * ?) + 
                (downloads * 1.0 / NULLIF(MAX(downloads) OVER(), 0) * ?) +
                (CASE WHEN pipeline_tag IN ({task_placeholders}) THEN 0.2 ELSE 0 END) as rec_score
            FROM models
            WHERE 1=1
            """
            
            conditions = []
            params = [
                user_preferences.get('performance_weight', 0.6),
                1 - user_preferences.get('performance_weight', 0.6)
            ]
            
            # Add task preferences
            params.extend(tasks)
            
            # Add other filters
            if user_preferences.get('max_size_mb'):
                conditions.append("AND (size_mb IS NULL OR size_mb <= ?)")
                params.append(user_preferences['max_size_mb'])
            
            if user_preferences.get('min_downloads'):
                conditions.append("AND downloads >= ?")
                params.append(user_preferences['min_downloads'])
            
            if user_preferences.get('license_preference') == 'open':
                conditions.append("AND license_score = 1")
            
            query = base_query + " ".join(conditions) + " ORDER BY rec_score DESC LIMIT 15"
            
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)
                
        except Exception as e:
            logger.error(f"❌ Error in recommendation system: {e}")
            return pd.DataFrame()
    
    async def get_enhanced_models_for_task(self, task_name: str, limit: int = 10, 
                                         custom_weights: Dict[str, float] = None) -> List[Dict]:
        """
        Enhanced model selection using advanced analytics
        """
        try:
            # Use dynamic ranking for better results
            df = self.dynamic_model_ranking(
                task=task_name,
                min_downloads=10,  # Filter out unused models
                custom_weights=custom_weights,
                limit=limit
            )
            
            if df.empty:
                return []
            
            # Convert to list of dictionaries
            models = []
            for _, row in df.iterrows():
                model = {
                    'model_id': row['model_id'],
                    'pipeline_tag': row['pipeline_tag'],
                    'downloads': row['downloads'],
                    'likes': row['likes'],
                    'final_score': row.get('dynamic_score', row.get('final_score', 0.0)),
                    'size_mb': row.get('size_mb'),
                    'license': row.get('license'),
                    'license_score': row.get('license_score', 0),
                    'enhanced_selection': True  # Mark as enhanced
                }
                models.append(model)
            
            logger.info(f"🔬 Enhanced selection found {len(models)} models for task: {task_name}")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced model selection: {e}")
            return []
    
    def get_model_insights(self, model_id: str) -> Dict:
        """
        Get comprehensive insights about a specific model
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get model details
                model_query = """
                SELECT * FROM models WHERE model_id = ?
                """
                model_df = pd.read_sql_query(model_query, conn, params=[model_id])
                
                if model_df.empty:
                    return {'error': 'Model not found'}
                
                model = model_df.iloc[0].to_dict()
                
                # Get similar models
                similar_df = self.similarity_clustering(model_id, top_k=3)
                
                # Get ranking in task category
                if model.get('pipeline_tag'):
                    rank_query = """
                    SELECT COUNT(*) + 1 as rank
                    FROM models 
                    WHERE pipeline_tag = ? AND final_score > ?
                    """
                    rank_result = conn.execute(rank_query, [model['pipeline_tag'], model['final_score']]).fetchone()
                    task_rank = rank_result[0] if rank_result else None
                else:
                    task_rank = None
                
                return {
                    'model_details': model,
                    'similar_models': similar_df.to_dict('records') if not similar_df.empty else [],
                    'task_rank': task_rank,
                    'insights': {
                        'engagement_ratio': model.get('likes', 0) / max(model.get('downloads', 1), 1),
                        'size_category': 'Small' if (model.get('size_mb') or 0) < 500 else 'Large',
                        'license_quality': 'Open' if model.get('license_score') == 1 else 'Restricted'
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting model insights: {e}")
            return {'error': str(e)}


# Initialize the analytics system
analytics = AdvancedModelAnalytics()
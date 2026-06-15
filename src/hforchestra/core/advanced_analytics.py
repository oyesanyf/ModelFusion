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
                
                # Create advanced indexes (using our actual column names)
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_models_score_desc ON models(decision_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_task_score ON models(pipeline_tag, decision_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_downloads_likes ON models(downloads, likes)",
                    "CREATE INDEX IF NOT EXISTS idx_models_size_license ON models(size_mb, license)",
                    "CREATE INDEX IF NOT EXISTS idx_models_last_modified ON models(last_modified)",
                    # Composite index for common filtering patterns
                    "CREATE INDEX IF NOT EXISTS idx_models_composite ON models(pipeline_tag, license_score, size_mb, decision_score DESC)",
                    # Additional performance indexes
                    "CREATE INDEX IF NOT EXISTS idx_models_download_date ON models(download_date)",
                    "CREATE INDEX IF NOT EXISTS idx_models_architecture ON models(architecture)",
                    "CREATE INDEX IF NOT EXISTS idx_models_license_score ON models(license_score)",
                    "CREATE INDEX IF NOT EXISTS idx_models_performance ON models(downloads DESC, likes DESC, decision_score DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_models_efficiency ON models(size_mb ASC, decision_score DESC)"
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
            # Adapted for our database schema
            base_query = """
            SELECT model_id, pipeline_tag, downloads, likes, license, model_size_mb as size_mb, 
                   last_modified, tags, decision_score as score, architecture, license_score,
                   -- Dynamic scoring with custom weights
                   CASE 
                       WHEN ? IS NOT NULL THEN 
                           (? * (downloads * 1.0 / NULLIF((SELECT MAX(downloads) FROM models), 0))) +
                           (? * (likes * 1.0 / NULLIF(downloads, 0))) +
                           (? * COALESCE(license_score, 0)) +
                           (? * CASE WHEN COALESCE(model_size_mb, 1000) < 500 THEN 1 ELSE 0 END) +
                           (? * CASE WHEN pipeline_tag = ? THEN 1 ELSE 0 END)
                       ELSE decision_score 
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
                    custom_weights.get('task_match', 0.1),
                    task or ''  # Task for task_match calculation
                ])
            else:
                params.extend([None] + [0] * 5 + [''])
            
            # Add filtering conditions
            if task:
                conditions.append("AND pipeline_tag = ?")
                params.append(task)
            
            if min_downloads:
                conditions.append("AND downloads >= ?")
                params.append(min_downloads)
            
            if max_size_mb:
                conditions.append("AND (model_size_mb IS NULL OR model_size_mb <= ?)")
                params.append(max_size_mb)
            
            if open_license_only:
                conditions.append("AND license_score = 1")
            
            query = base_query + " ".join(conditions) + " ORDER BY dynamic_score DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, sqlite3.connect(self.db_path), params=params)
            
        except Exception as e:
            logger.error(f"❌ Error in dynamic model ranking: {e}")
            return pd.DataFrame()
    
    def model_trend_analysis(self, days_back: int = 30) -> pd.DataFrame:
        """
        Analyze model trends over time using download_date
        """
        try:
            query = """
            WITH trend_data AS (
                SELECT 
                    pipeline_tag,
                    DATE(COALESCE(download_date, last_modified)) as mod_date,
                    COUNT(*) as models_updated,
                    AVG(downloads) as avg_downloads,
                    AVG(likes) as avg_likes,
                    AVG(decision_score) as avg_score
                FROM models 
                WHERE COALESCE(download_date, last_modified) >= date('now', '-{} days')
                GROUP BY pipeline_tag, DATE(COALESCE(download_date, last_modified))
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
            
            return pd.read_sql_query(query, sqlite3.connect(self.db_path))
            
        except Exception as e:
            logger.error(f"❌ Error in model trend analysis: {e}")
            return pd.DataFrame()
    
    def similarity_clustering(self, model_id: str, top_k: int = 5) -> pd.DataFrame:
        """
        Find similar models using feature-based similarity
        """
        try:
            query = """
            WITH target_model AS (
                SELECT downloads, likes, size_mb, license_score, pipeline_tag
                FROM models WHERE model_id = ?
            ),
            similarity_scores AS (
                SELECT 
                    m.model_id,
                    m.pipeline_tag,
                    m.downloads,
                    m.likes,
                    m.decision_score as score,

                    -- Calculate similarity score using normalized differences
                    (1.0 - ABS(
                        (m.downloads - t.downloads) * 1.0 / NULLIF(CASE WHEN m.downloads > t.downloads THEN m.downloads ELSE t.downloads END, 0)
                    )) * 0.4 +
                    (1.0 - ABS(
                        (COALESCE(m.size_mb, 0) - COALESCE(t.size_mb, 0)) / NULLIF(CASE WHEN COALESCE(m.size_mb, 1) > COALESCE(t.size_mb, 1) THEN COALESCE(m.size_mb, 1) ELSE COALESCE(t.size_mb, 1) END, 0)
                    )) * 0.3 +
                    (CASE WHEN COALESCE(m.license_score, 0) = COALESCE(t.license_score, 0) THEN 1 ELSE 0 END) * 0.2 +
                    (CASE WHEN m.pipeline_tag = t.pipeline_tag THEN 1 ELSE 0 END) * 0.1

                    as similarity_score
                FROM models m, target_model t
                WHERE m.model_id != ?
            )
            SELECT model_id, pipeline_tag, downloads, likes, score, similarity_score
            FROM similarity_scores
            ORDER BY similarity_score DESC
            LIMIT ?
            """
            
            return pd.read_sql_query(query, sqlite3.connect(self.db_path), 
                                   params=[model_id, model_id, top_k])
                                   
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
                        COALESCE(license, 'unknown') as license,
                        COUNT(*) as model_count,
                        AVG(downloads) as avg_downloads,
                        AVG(decision_score) as avg_score,
                        SUM(downloads) as total_downloads,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
                    FROM models
                    GROUP BY COALESCE(license, 'unknown')
                    ORDER BY model_count DESC
                """, conn)
                
                # Size distribution analysis
                results['size_analysis'] = pd.read_sql_query("""
                    SELECT 
                        CASE 
                            WHEN model_size_mb IS NULL THEN 'Unknown'
                            WHEN model_size_mb < 100 THEN 'Small (<100MB)'
                            WHEN model_size_mb < 500 THEN 'Medium (100-500MB)'
                            WHEN model_size_mb < 2000 THEN 'Large (500MB-2GB)'
                            ELSE 'Very Large (>2GB)'
                        END as size_category,
                        COUNT(*) as model_count,
                        AVG(downloads) as avg_downloads,
                        AVG(decision_score) as avg_score
                    FROM models
                    GROUP BY size_category
                    ORDER BY avg_score DESC
                """, conn)
                
                # Architecture distribution analysis
                results['architecture_analysis'] = pd.read_sql_query("""
                    SELECT 
                        COALESCE(architecture, 'unknown') as architecture,
                        COUNT(*) as model_count,
                        AVG(downloads) as avg_downloads,
                        AVG(decision_score) as avg_score,
                        AVG(COALESCE(model_size_mb, 0)) as avg_size_mb
                    FROM models
                    GROUP BY COALESCE(architecture, 'unknown')
                    HAVING model_count >= 5
                    ORDER BY model_count DESC
                """, conn)
                
                # Task performance metrics
                results['task_performance'] = pd.read_sql_query("""
                    SELECT 
                        pipeline_tag,
                        COUNT(*) as model_count,
                        AVG(decision_score) as avg_score,
                        MAX(decision_score) as max_score,
                        AVG(downloads) as avg_downloads,
                        MAX(downloads) as max_downloads,
                        -- Quality distribution
                        SUM(CASE WHEN decision_score > 0.8 THEN 1 ELSE 0 END) as high_quality_count,
                        SUM(CASE WHEN license_score = 1 THEN 1 ELSE 0 END) as open_license_count,
                        -- Architecture diversity
                        COUNT(DISTINCT COALESCE(architecture, 'unknown')) as architecture_count
                    FROM models
                    WHERE pipeline_tag IS NOT NULL AND pipeline_tag != ''
                    GROUP BY pipeline_tag
                    HAVING model_count >= 5  -- Only include tasks with sufficient data
                    ORDER BY avg_score DESC
                """, conn)
                
                # Engagement analysis
                results['engagement_analysis'] = pd.read_sql_query("""
                    SELECT 
                        model_id,
                        pipeline_tag,
                        downloads,
                        likes,
                        ROUND(likes * 1.0 / NULLIF(downloads, 0), 6) as engagement_ratio,
                        decision_score as score,
                        architecture,
                        license,
                        CASE 
                            WHEN likes * 1.0 / NULLIF(downloads, 0) > 0.001 THEN 'High Engagement'
                            WHEN likes * 1.0 / NULLIF(downloads, 0) > 0.0001 THEN 'Medium Engagement'
                            ELSE 'Low Engagement'
                        END as engagement_category
                    FROM models
                    WHERE downloads > 100  -- Filter out models with very low downloads
                    ORDER BY engagement_ratio DESC
                    LIMIT 50
                """, conn)
                
                # Download trends (if download_date is available)
                results['download_trends'] = pd.read_sql_query("""
                    SELECT 
                        DATE(download_date) as download_day,
                        COUNT(*) as models_added,
                        AVG(downloads) as avg_downloads_at_time,
                        SUM(downloads) as total_downloads
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
            'architectures': ['bert', 'gpt']  # optional
        }
        """
        try:
            # Build dynamic query based on preferences
            task_placeholders = ','.join(['?'] * len(user_preferences.get('tasks', [])))
            
            base_query = f"""
            SELECT 
                model_id, pipeline_tag, downloads, likes, license, model_size_mb as size_mb, 
                decision_score as score, architecture, license_score,
                -- Custom recommendation score
                (decision_score * ?) + 
                (downloads * 1.0 / NULLIF((SELECT MAX(downloads) FROM models), 0) * ?) +
                (CASE WHEN pipeline_tag IN ({task_placeholders}) THEN 0.2 ELSE 0 END) +
                (CASE WHEN COALESCE(architecture, 'unknown') IN ({task_placeholders}) THEN 0.1 ELSE 0 END)
                as rec_score
            FROM models
            WHERE 1=1
            """
            
            conditions = []
            params = [
                user_preferences.get('performance_weight', 0.6),
                1 - user_preferences.get('performance_weight', 0.6)
            ]
            
            # Add task preferences (for both task and architecture matching)
            tasks = user_preferences.get('tasks', [])
            architectures = user_preferences.get('architectures', [])
            params.extend(tasks)
            params.extend(architectures)
            
            # Add other filters
            if user_preferences.get('max_size_mb'):
                conditions.append("AND (model_size_mb IS NULL OR model_size_mb <= ?)")
                params.append(user_preferences['max_size_mb'])
            
            if user_preferences.get('min_downloads'):
                conditions.append("AND downloads >= ?")
                params.append(user_preferences['min_downloads'])
            
            if user_preferences.get('license_preference') == 'open':
                conditions.append("AND license_score = 1")
            
            # Filter by tasks if specified
            if tasks:
                task_filter = "AND pipeline_tag IN ({})".format(','.join(['?'] * len(tasks)))
                conditions.append(task_filter)
                params.extend(tasks)
            
            query = base_query + " ".join(conditions) + " ORDER BY rec_score DESC LIMIT 15"
            
            return pd.read_sql_query(query, sqlite3.connect(self.db_path), params=params)
            
        except Exception as e:
            logger.error(f"❌ Error in recommendation system: {e}")
            return pd.DataFrame()
    
    def get_model_statistics(self) -> Dict[str, any]:
        """Get comprehensive model statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Basic stats
                cursor.execute("SELECT COUNT(*) FROM models")
                total_models = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT pipeline_tag) FROM models WHERE pipeline_tag IS NOT NULL")
                total_tasks = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT COALESCE(architecture, 'unknown')) FROM models")
                total_architectures = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT COALESCE(license, 'unknown')) FROM models")
                total_licenses = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(decision_score), AVG(downloads), AVG(likes) FROM models")
                avg_stats = cursor.fetchone()
                
                return {
                    'total_models': total_models,
                    'total_tasks': total_tasks,
                    'total_architectures': total_architectures,
                    'total_licenses': total_licenses,
                    'avg_decision_score': avg_stats[0] or 0,
                    'avg_downloads': avg_stats[1] or 0,
                    'avg_likes': avg_stats[2] or 0
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting model statistics: {e}")
            return {}

# Usage Examples and Testing
def run_analytics_examples(db_path: str = "db/hf_models.db"):
    """Run examples of the analytics functionality"""
    try:
        # Initialize analytics
        analytics = AdvancedModelAnalytics(db_path)
        
        print("🔬 Advanced Model Analytics Examples")
        print("=" * 50)
        
        # Get basic statistics
        stats = analytics.get_model_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"   Total Models: {stats.get('total_models', 0):,}")
        print(f"   Total Tasks: {stats.get('total_tasks', 0):,}")
        print(f"   Total Architectures: {stats.get('total_architectures', 0):,}")
        print(f"   Total Licenses: {stats.get('total_licenses', 0):,}")
        print(f"   Avg Decision Score: {stats.get('avg_decision_score', 0):.3f}")
        
        # Example 1: Dynamic ranking with custom weights
        print(f"\n🏆 Dynamic Ranking Example:")
        custom_weights = {
            'popularity': 0.5,
            'engagement': 0.3,
            'license': 0.2,
            'lightweight': 0.0,
            'task_match': 0.0
        }
        
        top_models = analytics.dynamic_model_ranking(
            task="text-generation",
            min_downloads=1000,
            max_size_mb=2000,
            open_license_only=False,
            custom_weights=custom_weights,
            limit=5
        )
        
        if not top_models.empty:
            print("   Top Models:")
            for _, model in top_models.head().iterrows():
                print(f"     • {model['model_id']}")
                print(f"       Score: {model.get('dynamic_score', 0):.3f}, Downloads: {model.get('downloads', 0):,}")
        
        # Example 2: Advanced analytics
        print(f"\n📈 Advanced Analytics:")
        insights = analytics.advanced_aggregations()
        
        if 'license_analysis' in insights and not insights['license_analysis'].empty:
            print("   Top Licenses:")
            for _, license_info in insights['license_analysis'].head(3).iterrows():
                print(f"     • {license_info['license']}: {license_info['model_count']:,} models")
        
        if 'task_performance' in insights and not insights['task_performance'].empty:
            print("   Top Performing Tasks:")
            for _, task_info in insights['task_performance'].head(3).iterrows():
                print(f"     • {task_info['pipeline_tag']}: {task_info['model_count']:,} models, avg score: {task_info['avg_score']:.3f}")
        
        # Example 3: Recommendation system
        print(f"\n🎯 Recommendation System Example:")
        user_prefs = {
            'tasks': ['text-generation', 'text-classification'],
            'max_size_mb': 1000,
            'min_downloads': 500,
            'license_preference': 'any',
            'performance_weight': 0.7
        }
        
        recommendations = analytics.create_model_recommendation_system(user_prefs)
        if not recommendations.empty:
            print("   Personalized Recommendations:")
            for _, rec in recommendations.head(3).iterrows():
                print(f"     • {rec['model_id']}")
                print(f"       Task: {rec['pipeline_tag']}, Score: {rec.get('rec_score', 0):.3f}")
        
        print(f"\n✅ Analytics examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running analytics examples: {e}")

if __name__ == "__main__":
    import os
    # Initialize analytics with proper database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "hf_models.db")
    print(f"Using database path: {db_path}")
    analytics = AdvancedModelAnalytics(db_path)
    
    # Example 1: Dynamic ranking with custom weights
    custom_weights = {
        'popularity': 0.5,
        'engagement': 0.3,
        'license': 0.2,
        'lightweight': 0.0,
        'task_match': 0.0
    }
    
    top_models = analytics.dynamic_model_ranking(
        task="text-generation",
        min_downloads=1000,
        max_size_mb=2000,
        open_license_only=True,
        custom_weights=custom_weights,
        limit=10
    )
    print("Custom Ranked Models:")
    if not top_models.empty:
        print(top_models[['model_id', 'dynamic_score', 'downloads', 'size_mb']].head())
    else:
        print("No models found with current criteria")
    
    # Example 2: Find similar models
    if not top_models.empty:
        similar = analytics.similarity_clustering(top_models.iloc[0]['model_id'])
        print(f"\nSimilar to {top_models.iloc[0]['model_id']}:")
        if not similar.empty:
            print(similar[['model_id', 'similarity_score']].head())
        else:
            print("No similar models found")
    else:
        print("\nNo models available for similarity analysis")
    
    # Example 3: Advanced analytics
    insights = analytics.advanced_aggregations()
    print("\nLicense Distribution:")
    if 'license_analysis' in insights and not insights['license_analysis'].empty:
        print(insights['license_analysis'].head())
    else:
        print("No license analysis data available")
    
    print("\nTask Performance:")
    if 'task_performance' in insights and not insights['task_performance'].empty:
        print(insights['task_performance'].head())
    else:
        print("No task performance data available")
    
    # Example 4: Recommendation system
    user_prefs = {
        'tasks': ['text-generation', 'text-classification'],
        'max_size_mb': 1000,
        'min_downloads': 500,
        'license_preference': 'open',
        'performance_weight': 0.7
    }
    
    recommendations = analytics.create_model_recommendation_system(user_prefs)
    print("\nPersonalized Recommendations:")
    if not recommendations.empty:
        print(recommendations[['model_id', 'rec_score', 'pipeline_tag']].head())
    else:
        print("No recommendations found with current preferences")
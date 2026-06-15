#!/usr/bin/env python3
"""
Fixed HuggingFace Model Database Population
Handles the current API without deprecated offset parameter
"""

import sqlite3
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FixedHFModelPopulator:
    """Fixed HuggingFace model database populator that works with current API."""
    
    def __init__(self, db_path: str = "db/hf_models.db", batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.total_models = 0
        self.processed_models = 0
        self.failed_models = 0
        
        # Create database directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with proper schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create models table with all necessary columns
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS models (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT UNIQUE NOT NULL,
                        author TEXT,
                        pipeline_tag TEXT,
                        tags TEXT,
                        description TEXT,
                        downloads INTEGER DEFAULT 0,
                        likes INTEGER DEFAULT 0,
                        last_modified TEXT,
                        license TEXT,
                        task_keywords TEXT,
                        decision_score REAL DEFAULT 0.0,
                        capability_score REAL DEFAULT 0.0,
                        efficiency_score REAL DEFAULT 0.0,
                        popularity_score REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        model_type TEXT,
                        library_name TEXT,
                        architecture TEXT,
                        input_size TEXT,
                        num_classes INTEGER,
                        model_size_mb REAL
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_id ON models(model_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_tag ON models(pipeline_tag)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads ON models(downloads)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_likes ON models(likes)")
                
                conn.commit()
                logger.info("✅ Database initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def populate_models_with_limit(self, max_models: int = 100000):
        """Populate database with a limited number of models using proper pagination."""
        try:
            from huggingface_hub import HfApi
            
            api = HfApi()
            logger.info("🔗 Connected to HuggingFace API")
            logger.info(f"📥 Fetching up to {max_models:,} models from HuggingFace...")
            
            # Initialize counters
            self.total_models = max_models
            self.processed_models = 0
            self.failed_models = 0
            
            # Track progress
            start_time = time.time()
            last_progress_time = start_time
            total_fetched = 0
            
            # Use proper pagination - fetch models in batches
            while total_fetched < max_models:
                try:
                    # Calculate batch size
                    remaining = max_models - total_fetched
                    current_batch_size = min(self.batch_size, remaining)
                    
                    logger.info(f"📥 Fetching batch {total_fetched:,} to {total_fetched + current_batch_size:,}...")
                    
                    # Fetch models using the correct API call
                    models_page = list(api.list_models(limit=current_batch_size))
                    
                    if not models_page:
                        logger.info("✅ No more models to fetch")
                        break
                    
                    # Process this batch
                    self._process_models_batch(models_page)
                    
                    # Update counters
                    total_fetched += len(models_page)
                    
                    # Progress update
                    current_time = time.time()
                    if (total_fetched % (self.batch_size * 10) == 0 or 
                        current_time - last_progress_time > 300):
                        
                        elapsed = current_time - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        progress = (total_fetched / max_models) * 100
                        
                        logger.info(f"📈 Progress: {progress:.1f}% ({total_fetched:,}/{max_models:,})")
                        logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                        logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                        logger.info(f"   ✅ Processed: {self.processed_models:,}")
                        logger.info(f"   ❌ Failed: {self.failed_models:,}")
                        
                        last_progress_time = current_time
                    
                    # Rate limiting
                    time.sleep(1)  # 1 second delay between requests
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching batch at {total_fetched:,}: {e}")
                    time.sleep(5)  # Wait longer on error
                    continue
            
            # Final statistics
            elapsed = time.time() - start_time
            logger.info(f"✅ Database population completed!")
            logger.info(f"   📊 Total fetched: {total_fetched:,}")
            logger.info(f"   ✅ Processed: {self.processed_models:,}")
            logger.info(f"   ❌ Failed: {self.failed_models:,}")
            logger.info(f"   ⏱️ Total time: {elapsed/60:.1f} minutes")
            logger.info(f"   🚀 Average rate: {total_fetched/elapsed:.1f} models/second")
            
        except ImportError:
            logger.error("❌ HuggingFace Hub not available. Install with: pip install huggingface_hub")
        except Exception as e:
            logger.error(f"❌ Error populating models: {e}")
    
    def populate_all_models(self):
        """Populate database with ALL available models."""
        try:
            from huggingface_hub import HfApi
            
            api = HfApi()
            logger.info("🔗 Connected to HuggingFace API")
            logger.info("📥 Fetching ALL models from HuggingFace (this may take hours)...")
            
            # Initialize counters
            self.processed_models = 0
            self.failed_models = 0
            
            # Track progress
            start_time = time.time()
            last_progress_time = start_time
            total_fetched = 0
            
            # Fetch all models using proper pagination
            while True:
                try:
                    logger.info(f"📥 Fetching batch {total_fetched:,} to {total_fetched + self.batch_size:,}...")
                    
                    # Fetch models using the correct API call
                    models_page = list(api.list_models(limit=self.batch_size))
                    
                    if not models_page:
                        logger.info("✅ No more models to fetch")
                        break
                    
                    # Process this batch
                    self._process_models_batch(models_page)
                    
                    # Update counters
                    total_fetched += len(models_page)
                    
                    # Progress update every 10 batches or every 5 minutes
                    current_time = time.time()
                    if (total_fetched % (self.batch_size * 10) == 0 or 
                        current_time - last_progress_time > 300):
                        
                        elapsed = current_time - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        
                        logger.info(f"📈 Progress: {total_fetched:,} models processed")
                        logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                        logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                        logger.info(f"   ✅ Processed: {self.processed_models:,}")
                        logger.info(f"   ❌ Failed: {self.failed_models:,}")
                        
                        last_progress_time = current_time
                    
                    # Rate limiting
                    time.sleep(1)  # 1 second delay between requests
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching batch at {total_fetched:,}: {e}")
                    time.sleep(5)  # Wait longer on error
                    continue
            
            # Final statistics
            elapsed = time.time() - start_time
            logger.info(f"✅ Database population completed!")
            logger.info(f"   📊 Total fetched: {total_fetched:,}")
            logger.info(f"   ✅ Processed: {self.processed_models:,}")
            logger.info(f"   ❌ Failed: {self.failed_models:,}")
            logger.info(f"   ⏱️ Total time: {elapsed/60:.1f} minutes")
            logger.info(f"   🚀 Average rate: {total_fetched/elapsed:.1f} models/second")
            
        except ImportError:
            logger.error("❌ HuggingFace Hub not available. Install with: pip install huggingface_hub")
        except Exception as e:
            logger.error(f"❌ Error populating models: {e}")
    
    def _process_models_batch(self, models_list: List[Any]):
        """Process a batch of models and insert them into the database."""
        batch = []
        
        for model in models_list:
            try:
                model_data = self._extract_model_data(model)
                if model_data:
                    batch.append(model_data)
                    self.processed_models += 1
                else:
                    self.failed_models += 1
            except Exception as e:
                logger.error(f"❌ Error processing model: {e}")
                self.failed_models += 1
        
        if batch:
            self._insert_batch(batch)
            logger.info(f"💾 Inserted batch of {len(batch)} models")
    
    def _extract_model_data(self, model: Any) -> Optional[Dict[str, Any]]:
        """Extract model data from HuggingFace model object."""
        try:
            # Handle different model object types
            if hasattr(model, 'modelId'):
                model_id = model.modelId
                author = model_id.split('/')[0] if '/' in model_id else None
            elif hasattr(model, 'id'):
                model_id = model.id
                author = model_id.split('/')[0] if '/' in model_id else None
            else:
                return None
            
            # Extract basic information
            data = {
                'model_id': model_id,
                'author': author,
                'pipeline_tag': getattr(model, 'pipeline_tag', None),
                'tags': json.dumps(getattr(model, 'tags', [])) if hasattr(model, 'tags') else None,
                'description': getattr(model, 'description', None),
                'downloads': getattr(model, 'downloads', 0),
                'likes': getattr(model, 'likes', 0),
                'last_modified': getattr(model, 'last_modified', None),
                'license': getattr(model, 'license', None),
                'task_keywords': json.dumps(getattr(model, 'task_keywords', [])) if hasattr(model, 'task_keywords') else None,
                'model_type': getattr(model, 'model_type', None),
                'library_name': getattr(model, 'library_name', None),
                'architecture': getattr(model, 'architecture', None),
                'input_size': getattr(model, 'input_size', None),
                'num_classes': getattr(model, 'num_classes', None),
                'model_size_mb': getattr(model, 'model_size_mb', None)
            }
            
            # Calculate scores
            data['decision_score'] = self._calculate_decision_score(model)
            data['capability_score'] = self._calculate_capability_score(model)
            data['efficiency_score'] = self._calculate_efficiency_score(model)
            data['popularity_score'] = self._calculate_popularity_score(model)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error extracting model data: {e}")
            return None
    
    def _calculate_decision_score(self, model: Any) -> float:
        """Calculate decision score based on model quality indicators."""
        score = 0.0
        
        # Downloads weight (40%)
        downloads = getattr(model, 'downloads', 0)
        if downloads > 100000:
            score += 40
        elif downloads > 10000:
            score += 30
        elif downloads > 1000:
            score += 20
        elif downloads > 100:
            score += 10
        
        # Likes weight (30%)
        likes = getattr(model, 'likes', 0)
        if likes > 1000:
            score += 30
        elif likes > 100:
            score += 20
        elif likes > 10:
            score += 10
        
        # Pipeline tag weight (20%)
        pipeline = getattr(model, 'pipeline_tag', '')
        if pipeline:
            score += 20
        
        # License weight (10%)
        license_info = getattr(model, 'license', '')
        if license_info and 'mit' in license_info.lower():
            score += 10
        
        return score
    
    def _calculate_capability_score(self, model: Any) -> float:
        """Calculate capability score based on model features."""
        score = 0.0
        
        # Model type weight
        model_type = getattr(model, 'model_type', '')
        if model_type in ['text-generation', 'text-classification', 'translation']:
            score += 30
        
        # Architecture weight
        architecture = getattr(model, 'architecture', '')
        if architecture:
            score += 20
        
        # Input size weight
        input_size = getattr(model, 'input_size', '')
        if input_size:
            score += 20
        
        # Task keywords weight
        task_keywords = getattr(model, 'task_keywords', [])
        if task_keywords:
            score += 30
        
        return score
    
    def _calculate_efficiency_score(self, model: Any) -> float:
        """Calculate efficiency score based on model size and performance."""
        score = 0.0
        
        # Model size weight (smaller is better)
        model_size = getattr(model, 'model_size_mb', 0)
        if model_size:
            if model_size < 100:  # < 100MB
                score += 40
            elif model_size < 500:  # < 500MB
                score += 30
            elif model_size < 1000:  # < 1GB
                score += 20
            else:
                score += 10
        
        # Downloads per MB (efficiency metric)
        downloads = getattr(model, 'downloads', 0)
        if model_size and model_size > 0:
            downloads_per_mb = downloads / model_size
            if downloads_per_mb > 1000:
                score += 30
            elif downloads_per_mb > 100:
                score += 20
            elif downloads_per_mb > 10:
                score += 10
        
        # Library efficiency
        library = getattr(model, 'library_name', '')
        if library in ['transformers', 'torch', 'tensorflow']:
            score += 30
        
        return score
    
    def _calculate_popularity_score(self, model: Any) -> float:
        """Calculate popularity score based on community engagement."""
        score = 0.0
        
        # Downloads weight (50%)
        downloads = getattr(model, 'downloads', 0)
        if downloads > 1000000:
            score += 50
        elif downloads > 100000:
            score += 40
        elif downloads > 10000:
            score += 30
        elif downloads > 1000:
            score += 20
        elif downloads > 100:
            score += 10
        
        # Likes weight (30%)
        likes = getattr(model, 'likes', 0)
        if likes > 1000:
            score += 30
        elif likes > 100:
            score += 20
        elif likes > 10:
            score += 10
        
        # Recent activity weight (20%)
        last_modified = getattr(model, 'last_modified', None)
        if last_modified:
            try:
                # Parse date and calculate recency
                if isinstance(last_modified, str):
                    if 'T' in last_modified:
                        mod_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                    else:
                        mod_date = datetime.strptime(last_modified, '%Y-%m-%d')
                    
                    days_old = (datetime.now() - mod_date).days
                    if days_old < 30:  # Less than 1 month
                        score += 20
                    elif days_old < 90:  # Less than 3 months
                        score += 15
                    elif days_old < 365:  # Less than 1 year
                        score += 10
            except:
                pass
        
        return score
    
    def _insert_batch(self, batch: List[Dict[str, Any]]):
        """Insert a batch of models into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for model_data in batch:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO models (
                                model_id, author, pipeline_tag, tags, description,
                                downloads, likes, last_modified, license, task_keywords,
                                decision_score, capability_score, efficiency_score, popularity_score,
                                model_type, library_name, architecture, input_size, num_classes, model_size_mb
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            model_data['model_id'],
                            model_data['author'],
                            model_data['pipeline_tag'],
                            model_data['tags'],
                            model_data['description'],
                            model_data['downloads'],
                            model_data['likes'],
                            model_data['last_modified'],
                            model_data['license'],
                            model_data['task_keywords'],
                            model_data['decision_score'],
                            model_data['capability_score'],
                            model_data['efficiency_score'],
                            model_data['popularity_score'],
                            model_data['model_type'],
                            model_data['library_name'],
                            model_data['architecture'],
                            model_data['input_size'],
                            model_data['num_classes'],
                            model_data['model_size_mb']
                        ))
                    except Exception as e:
                        logger.error(f"❌ Error inserting model {model_data.get('model_id', 'unknown')}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error inserting batch: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM models")
                total_models = cursor.fetchone()[0]
                
                # Get top models by downloads
                cursor.execute("""
                    SELECT model_id, downloads, likes, pipeline_tag 
                    FROM models 
                    ORDER BY downloads DESC 
                    LIMIT 10
                """)
                top_models = cursor.fetchall()
                
                # Get pipeline distribution
                cursor.execute("""
                    SELECT pipeline_tag, COUNT(*) 
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL 
                    GROUP BY pipeline_tag 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 10
                """)
                pipeline_dist = cursor.fetchall()
                
                return {
                    'total_models': total_models,
                    'top_models': top_models,
                    'pipeline_distribution': pipeline_dist
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

def main():
    """Main function with menu system."""
    print("🚀 Fixed HuggingFace Model Database Population")
    print("=" * 60)
    
    # Initialize populator
    populator = FixedHFModelPopulator()
    
    # Show current database state
    stats = populator.get_database_stats()
    print(f"📊 Current database has {stats.get('total_models', 0):,} models")
    
    if stats.get('top_models'):
        print("📝 Top model:", stats['top_models'][0][0])
    
    print("\n📋 Choose population strategy:")
    print("1. Test mode (1,000 models) - Quick test")
    print("2. Small mode (10,000 models) - Small dataset")
    print("3. Medium mode (100,000 models) - Medium dataset")
    print("4. Large mode (1,000,000 models) - Large dataset")
    print("5. All models (1.9M+ models) - Complete dataset (very long)")
    
    try:
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == "1":
            print("🧪 Starting test mode (1,000 models)...")
            populator.populate_models_with_limit(1000)
        elif choice == "2":
            print("📦 Starting small mode (10,000 models)...")
            populator.populate_models_with_limit(10000)
        elif choice == "3":
            print("📦 Starting medium mode (100,000 models)...")
            populator.populate_models_with_limit(100000)
        elif choice == "4":
            print("📦 Starting large mode (1,000,000 models)...")
            populator.populate_models_with_limit(1000000)
        elif choice == "5":
            print("🌍 Starting complete mode (ALL models - 1.9M+)...")
            print("⚠️  This will take a very long time (hours/days)")
            confirm = input("Are you sure? (yes/no): ").strip().lower()
            if confirm == "yes":
                populator.populate_all_models()
            else:
                print("❌ Operation cancelled")
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        print("💡 You can resume later using the same script")

if __name__ == "__main__":
    main() 
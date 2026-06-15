#!/usr/bin/env python3
"""
Comprehensive HuggingFace Model Discovery and Database Population
Downloads and stores ALL available models from HuggingFace Hub
"""

import asyncio
import sqlite3
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HuggingFaceDatabasePopulator:
    """Comprehensive HuggingFace model database population system."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.db_path = db_path
        self.db_dir = Path(db_path).parent
        self.db_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database with proper schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create comprehensive model table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
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
                    architecture TEXT,
                    input_size TEXT,
                    num_classes INTEGER,
                    model_size_mb REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pipeline_tag ON models(pipeline_tag)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads ON models(downloads)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decision_score ON models(decision_score)')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def get_total_model_count(self) -> int:
        """Get total number of models on HuggingFace Hub."""
        try:
            from huggingface_hub import list_models
            
            logger.info("🔍 Counting total models on HuggingFace Hub...")
            model_count = 0
            
            # Count all models (this may take a while)
            for _ in list_models():
                model_count += 1
                if model_count % 1000 == 0:
                    logger.info(f"   Counted {model_count} models so far...")
            
            logger.info(f"✅ Total models on HuggingFace Hub: {model_count}")
            return model_count
            
        except Exception as e:
            logger.error(f"❌ Failed to count models: {e}")
            return 0
    
    def discover_and_populate_models(self, limit: Optional[int] = None, 
                                   pipeline_tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Discover and populate models in the database."""
        try:
            from huggingface_hub import list_models
            
            logger.info("🚀 Starting comprehensive model discovery...")
            
            # Get model count if limit not specified
            if limit is None:
                total_count = self.get_total_model_count()
                limit = total_count
                logger.info(f"📊 Will process all {limit} models")
            else:
                logger.info(f"📊 Will process {limit} models")
            
            # Prepare model filter
            model_filter = {}
            if pipeline_tags:
                model_filter['pipeline_tag'] = pipeline_tags
                logger.info(f"🎯 Filtering by pipeline tags: {pipeline_tags}")
            
            # Initialize counters
            processed_count = 0
            inserted_count = 0
            updated_count = 0
            error_count = 0
            
            # Process models
            start_time = time.time()
            
            for model in list_models(limit=limit, **model_filter):
                try:
                    processed_count += 1
                    
                    if processed_count % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = processed_count / elapsed
                        logger.info(f"📈 Processed {processed_count}/{limit} models ({rate:.1f} models/sec)")
                    
                    # Extract model data
                    model_data = self._extract_model_data(model)
                    
                    # Insert or update in database
                    result = self._insert_or_update_model(model_data)
                    
                    if result == 'inserted':
                        inserted_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.warning(f"⚠️ Error processing model {getattr(model, 'modelId', 'unknown')}: {e}")
                    continue
            
            # Calculate statistics
            elapsed_time = time.time() - start_time
            total_models_in_db = self.get_database_model_count()
            
            stats = {
                'total_processed': processed_count,
                'total_inserted': inserted_count,
                'total_updated': updated_count,
                'total_errors': error_count,
                'total_in_database': total_models_in_db,
                'elapsed_time_seconds': elapsed_time,
                'processing_rate': processed_count / elapsed_time if elapsed_time > 0 else 0
            }
            
            logger.info("✅ Model discovery completed!")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Processed: {stats['total_processed']}")
            logger.info(f"   Inserted: {stats['total_inserted']}")
            logger.info(f"   Updated: {stats['total_updated']}")
            logger.info(f"   Errors: {stats['total_errors']}")
            logger.info(f"   Total in DB: {stats['total_in_database']}")
            logger.info(f"   Time: {stats['elapsed_time_seconds']:.1f}s")
            logger.info(f"   Rate: {stats['processing_rate']:.1f} models/sec")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Model discovery failed: {e}")
            raise
    
    def _extract_model_data(self, model) -> Dict[str, Any]:
        """Extract relevant data from a HuggingFace model."""
        try:
            # Calculate scores
            downloads = getattr(model, 'downloads', 0) or 0
            likes = getattr(model, 'likes', 0) or 0
            
            # Calculate popularity score (0-1)
            popularity_score = min(1.0, downloads / 1000000) if downloads > 0 else 0.0
            
            # Calculate capability score based on tags and downloads
            capability_score = 0.0
            tags = getattr(model, 'tags', []) or []
            
            # Boost score for specific capabilities
            if 'text-generation' in tags:
                capability_score += 0.3
            if 'image-classification' in tags:
                capability_score += 0.3
            if 'question-answering' in tags:
                capability_score += 0.2
            if 'translation' in tags:
                capability_score += 0.2
            if 'summarization' in tags:
                capability_score += 0.2
            if 'text-classification' in tags:
                capability_score += 0.2
            if 'image-to-text' in tags:
                capability_score += 0.3
            if 'object-detection' in tags:
                capability_score += 0.3
            
            # Normalize capability score
            capability_score = min(1.0, capability_score)
            
            # Calculate efficiency score (based on model size and downloads)
            efficiency_score = min(1.0, downloads / 100000) if downloads > 0 else 0.0
            
            # Calculate decision score (weighted combination)
            decision_score = (
                capability_score * 0.4 +
                popularity_score * 0.3 +
                efficiency_score * 0.3
            )
            
            return {
                'model_id': getattr(model, 'modelId', ''),
                'author': getattr(model, 'author', ''),
                'pipeline_tag': getattr(model, 'pipeline_tag', ''),
                'tags': json.dumps(tags),
                'description': getattr(model, 'description', ''),
                'downloads': downloads,
                'likes': likes,
                'last_modified': str(getattr(model, 'lastModified', '')),
                'license': getattr(model, 'license', ''),
                'task_keywords': json.dumps(tags),  # Use tags as task keywords
                'decision_score': decision_score,
                'capability_score': capability_score,
                'efficiency_score': efficiency_score,
                'popularity_score': popularity_score,
                'architecture': self._detect_architecture(tags, getattr(model, 'modelId', '')),
                'input_size': self._detect_input_size(tags),
                'num_classes': self._detect_num_classes(tags),
                'model_size_mb': self._estimate_model_size(tags, getattr(model, 'modelId', ''))
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting model data: {e}")
            return {}
    
    def _detect_architecture(self, tags: List[str], model_id: str) -> str:
        """Detect model architecture from tags and model ID."""
        model_id_lower = model_id.lower()
        tags_lower = [tag.lower() for tag in tags]
        
        if any(arch in model_id_lower for arch in ['bert', 'roberta', 'distilbert']):
            return 'transformer'
        elif any(arch in model_id_lower for arch in ['gpt', 'llama', 'mistral', 'phi']):
            return 'decoder'
        elif any(arch in model_id_lower for arch in ['t5', 'bart']):
            return 'encoder-decoder'
        elif any(arch in model_id_lower for arch in ['vit', 'swin']):
            return 'vision-transformer'
        elif any(arch in model_id_lower for arch in ['resnet', 'mobilenet', 'efficientnet']):
            return 'cnn'
        elif any(arch in model_id_lower for arch in ['clip']):
            return 'multimodal'
        else:
            return 'unknown'
    
    def _detect_input_size(self, tags: List[str]) -> str:
        """Detect input size from tags."""
        for tag in tags:
            if '224' in tag:
                return '224x224'
            elif '384' in tag:
                return '384x384'
            elif '512' in tag:
                return '512x512'
        return 'variable'
    
    def _detect_num_classes(self, tags: List[str]) -> int:
        """Detect number of classes from tags."""
        for tag in tags:
            if '1000' in tag:
                return 1000
            elif '100' in tag:
                return 100
            elif '10' in tag:
                return 10
        return 0
    
    def _estimate_model_size(self, tags: List[str], model_id: str) -> float:
        """Estimate model size in MB."""
        model_id_lower = model_id.lower()
        
        # Base size estimates
        if 'base' in model_id_lower:
            return 500.0
        elif 'large' in model_id_lower:
            return 1500.0
        elif 'small' in model_id_lower:
            return 250.0
        elif 'tiny' in model_id_lower:
            return 100.0
        else:
            return 500.0  # Default estimate
    
    def _insert_or_update_model(self, model_data: Dict[str, Any]) -> str:
        """Insert or update model in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if model exists
            cursor.execute('SELECT model_id FROM models WHERE model_id = ?', (model_data['model_id'],))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing model
                update_sql = '''
                    UPDATE models SET
                        author = ?, pipeline_tag = ?, tags = ?, description = ?,
                        downloads = ?, likes = ?, last_modified = ?, license = ?,
                        task_keywords = ?, decision_score = ?, capability_score = ?,
                        efficiency_score = ?, popularity_score = ?, architecture = ?,
                        input_size = ?, num_classes = ?, model_size_mb = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE model_id = ?
                '''
                
                cursor.execute(update_sql, (
                    model_data['author'], model_data['pipeline_tag'], model_data['tags'],
                    model_data['description'], model_data['downloads'], model_data['likes'],
                    model_data['last_modified'], model_data['license'], model_data['task_keywords'],
                    model_data['decision_score'], model_data['capability_score'],
                    model_data['efficiency_score'], model_data['popularity_score'],
                    model_data['architecture'], model_data['input_size'],
                    model_data['num_classes'], model_data['model_size_mb'],
                    model_data['model_id']
                ))
                
                conn.commit()
                conn.close()
                return 'updated'
            else:
                # Insert new model
                insert_sql = '''
                    INSERT INTO models (
                        model_id, author, pipeline_tag, tags, description,
                        downloads, likes, last_modified, license, task_keywords,
                        decision_score, capability_score, efficiency_score, popularity_score,
                        architecture, input_size, num_classes, model_size_mb
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                cursor.execute(insert_sql, (
                    model_data['model_id'], model_data['author'], model_data['pipeline_tag'],
                    model_data['tags'], model_data['description'], model_data['downloads'],
                    model_data['likes'], model_data['last_modified'], model_data['license'],
                    model_data['task_keywords'], model_data['decision_score'],
                    model_data['capability_score'], model_data['efficiency_score'],
                    model_data['popularity_score'], model_data['architecture'],
                    model_data['input_size'], model_data['num_classes'], model_data['model_size_mb']
                ))
                
                conn.commit()
                conn.close()
                return 'inserted'
                
        except Exception as e:
            logger.error(f"❌ Database operation failed: {e}")
            return 'error'
    
    def get_database_model_count(self) -> int:
        """Get total number of models in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM models')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"❌ Failed to get database count: {e}")
            return 0
    
    def export_to_csv(self, output_path: str = "huggingface_models_complete.csv"):
        """Export all models to CSV for analysis."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query('SELECT * FROM models', conn)
            conn.close()
            
            df.to_csv(output_path, index=False)
            logger.info(f"✅ Exported {len(df)} models to {output_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ CSV export failed: {e}")
            return None
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """Get comprehensive model statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic counts
            cursor.execute('SELECT COUNT(*) FROM models')
            total_models = cursor.fetchone()[0]
            
            # Get pipeline tag distribution
            cursor.execute('''
                SELECT pipeline_tag, COUNT(*) as count 
                FROM models 
                WHERE pipeline_tag IS NOT NULL AND pipeline_tag != ''
                GROUP BY pipeline_tag 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            pipeline_distribution = dict(cursor.fetchall())
            
            # Get top models by downloads
            cursor.execute('''
                SELECT model_id, downloads, likes, decision_score
                FROM models 
                ORDER BY downloads DESC 
                LIMIT 10
            ''')
            top_by_downloads = cursor.fetchall()
            
            # Get top models by decision score
            cursor.execute('''
                SELECT model_id, downloads, likes, decision_score
                FROM models 
                ORDER BY decision_score DESC 
                LIMIT 10
            ''')
            top_by_score = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_models': total_models,
                'pipeline_distribution': pipeline_distribution,
                'top_by_downloads': top_by_downloads,
                'top_by_score': top_by_score
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {}

async def main():
    """Main function to run the comprehensive model discovery."""
    print("🚀 HuggingFace Model Discovery and Database Population")
    print("=" * 60)
    
    # Initialize populator
    populator = HuggingFaceDatabasePopulator()
    
    # Get current database count
    current_count = populator.get_database_model_count()
    print(f"📊 Current models in database: {current_count}")
    
    # Ask user for configuration
    print("\n🔧 Configuration Options:")
    print("1. Full discovery (all models - may take hours)")
    print("2. Limited discovery (first 1000 models)")
    print("3. Specific pipeline tags only")
    print("4. Just get model count")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n🚀 Starting FULL model discovery...")
        print("⚠️  This may take several hours!")
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm == 'y':
            stats = populator.discover_and_populate_models()
        else:
            print("❌ Cancelled by user")
            return
            
    elif choice == "2":
        print("\n🚀 Starting LIMITED model discovery (1000 models)...")
        stats = populator.discover_and_populate_models(limit=1000)
        
    elif choice == "3":
        print("\n🎯 Specific pipeline tags discovery")
        tags_input = input("Enter pipeline tags (comma-separated): ").strip()
        pipeline_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        if pipeline_tags:
            stats = populator.discover_and_populate_models(pipeline_tags=pipeline_tags)
        else:
            print("❌ No valid tags provided")
            return
            
    elif choice == "4":
        print("\n🔍 Getting total model count...")
        total_count = populator.get_total_model_count()
        print(f"📊 Total models on HuggingFace Hub: {total_count}")
        return
        
    else:
        print("❌ Invalid choice")
        return
    
    # Display final statistics
    print("\n📊 Final Statistics:")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Total inserted: {stats['total_inserted']}")
    print(f"   Total updated: {stats['total_updated']}")
    print(f"   Total errors: {stats['total_errors']}")
    print(f"   Total in database: {stats['total_in_database']}")
    print(f"   Processing time: {stats['elapsed_time_seconds']:.1f} seconds")
    print(f"   Processing rate: {stats['processing_rate']:.1f} models/second")
    
    # Export to CSV
    print("\n💾 Exporting to CSV...")
    df = populator.export_to_csv()
    
    # Get detailed statistics
    print("\n📈 Getting detailed statistics...")
    detailed_stats = populator.get_model_statistics()
    
    print(f"\n🏆 Top Pipeline Tags:")
    for tag, count in list(detailed_stats['pipeline_distribution'].items())[:5]:
        print(f"   {tag}: {count} models")
    
    print(f"\n🔥 Top Models by Downloads:")
    for i, (model_id, downloads, likes, score) in enumerate(detailed_stats['top_by_downloads'][:5]):
        print(f"   {i+1}. {model_id}: {downloads:,} downloads, {likes:,} likes, score: {score:.3f}")
    
    print(f"\n⭐ Top Models by Decision Score:")
    for i, (model_id, downloads, likes, score) in enumerate(detailed_stats['top_by_score'][:5]):
        print(f"   {i+1}. {model_id}: score: {score:.3f}, {downloads:,} downloads, {likes:,} likes")
    
    print(f"\n✅ Database population completed successfully!")
    print(f"📁 Database location: {populator.db_path}")
    print(f"📄 CSV export: huggingface_models_complete.csv")

if __name__ == "__main__":
    asyncio.run(main()) 
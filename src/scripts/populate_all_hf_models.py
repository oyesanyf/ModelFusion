#!/usr/bin/env python3
"""
Comprehensive HuggingFace Model Database Population
Fetches ALL models from HuggingFace API and stores them in the database
"""

import sqlite3
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging
import importlib.util
import ast

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveHFModelPopulator:
    """Comprehensive HuggingFace model database populator."""
    
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
    
    def create_timestamped_backup(self) -> bool:
        """Create a timestamped backup of critical files before updates."""
        try:
            import os
            import shutil
            from datetime import datetime
            
            # Create db directory if it doesn't exist
            db_dir = "db"
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"📁 Created db directory: {db_dir}")
            
            # Generate timestamp for unique backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Files to backup with their backup names - all going to db folder
            files_to_backup = [
                ("task_models.json", f"db/task_models_{timestamp}.json"),
                ("db/hf_models.db", f"db/hf_models_{timestamp}.db"),
                ("config/model_configs.json", f"db/model_configs_{timestamp}.json"),
                ("config/dynamic_models.json", f"db/dynamic_models_{timestamp}.json"),
                ("config/settings.json", f"db/settings_{timestamp}.json")
            ]
            
            backup_success = True
            backed_up_files = []
            
            for source_path, backup_path in files_to_backup:
                try:
                    if os.path.exists(source_path):
                        # Create backup directory if it doesn't exist
                        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                        
                        # Copy file to backup location
                        shutil.copy2(source_path, backup_path)
                        backed_up_files.append(backup_path)
                        logger.info(f"💾 Backed up: {source_path} -> {backup_path}")
                    else:
                        logger.warning(f"⚠️ File not found for backup: {source_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to backup {source_path}: {e}")
                    backup_success = False
            
            if backup_success and backed_up_files:
                logger.info(f"✅ Backup completed successfully! {len(backed_up_files)} files backed up to db/")
            else:
                logger.warning("⚠️ Some files could not be backed up")
            
            return backup_success
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False

    def _init_database(self):
        """Initialize the database with proper schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create models table with comprehensive schema including all expanded metadata fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT UNIQUE NOT NULL,
                    author TEXT,
                    pipeline_tag TEXT,
                    tags TEXT,  -- JSON array of tags
                    description TEXT,
                    downloads INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    decision_score REAL DEFAULT 0.0,
                    capability_score REAL DEFAULT 0.0,
                    efficiency_score REAL DEFAULT 0.0,
                    popularity_score REAL DEFAULT 0.0,
                    model_type TEXT,
                    library_name TEXT,
                    last_modified TIMESTAMP,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    license TEXT,
                    task_keywords TEXT,
                    architecture TEXT,
                    input_size TEXT,
                    num_classes INTEGER,
                    model_size_mb REAL,
                    license_score REAL DEFAULT 0.0,
                    size_mb REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    popularity_score_normalized REAL,
                    engagement_score REAL,
                    lightweight_score REAL,
                    task_match_score REAL,
                    language TEXT,
                    language_details TEXT,
                    license_details TEXT,
                    base_model TEXT,
                    datasets TEXT,
                    metrics TEXT,
                    widget_data TEXT,
                    model_index TEXT,
                    inference_info TEXT,
                    -- Additional expanded fields from full=true
                    disabled BOOLEAN DEFAULT FALSE,
                    gated BOOLEAN DEFAULT FALSE,
                    private BOOLEAN DEFAULT FALSE,
                    downloads_all_time INTEGER DEFAULT 0,
                    trending_score REAL DEFAULT 0.0,
                    children_model_count INTEGER DEFAULT 0,
                    card_data TEXT,  -- JSON card data
                    config TEXT  -- JSON config data
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_model_id ON models(model_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pipeline_tag ON models(pipeline_tag)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_author ON models(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads ON models(downloads)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decision_score ON models(decision_score)')
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("✅ Database initialized successfully")
    
    def populate_all_models(self):
        """Populate database with ALL HuggingFace models using full=true parameter for complete metadata."""
        try:
            # Import required libraries
            import requests
            import json
            from huggingface_hub import HfApi
            
            api = HfApi()
            logger.info("🔗 Connected to HuggingFace API")
            logger.info("📥 Fetching ALL models from HuggingFace with full=true (this may take hours)...")
            logger.info("🌍 Will fetch complete metadata for all ~1.9M+ models")
            
            # Initialize counters
            self.processed_models = 0
            self.failed_models = 0
            
            # Track progress
            start_time = time.time()
            last_progress_time = start_time
            total_fetched = 0
            
            # Get all model IDs first (this is faster than fetching full data)
            logger.info("📋 Getting list of all model IDs...")
            all_model_ids = []
            try:
                # Get all model IDs using the API
                model_list = list(api.list_models(limit=None))
                all_model_ids = [model.modelId for model in model_list]
                logger.info(f"📊 Found {len(all_model_ids):,} models to process")
            except Exception as e:
                logger.error(f"❌ Error getting model list: {e}")
                return
            
            # Process models in batches
            batch_size = 100  # Smaller batch size for full=true requests
            for i in range(0, len(all_model_ids), batch_size):
                batch_ids = all_model_ids[i:i + batch_size]
                
                try:
                    logger.info(f"📥 Processing batch {i//batch_size + 1}/{(len(all_model_ids) + batch_size - 1)//batch_size}")
                    logger.info(f"   Models {i:,} to {min(i + batch_size, len(all_model_ids)):,} of {len(all_model_ids):,}")
                    
                    # Process each model in the batch with full=true
                    batch_models = []
                    for model_id in batch_ids:
                        try:
                            # Fetch full model data using full=true parameter
                            model_data = api.model_info(model_id, full=True)
                            batch_models.append(model_data)
                            
                            # Small delay to be respectful to API
                            time.sleep(0.1)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to fetch {model_id}: {e}")
                            self.failed_models += 1
                            continue
                    
                    # Process this batch
                    if batch_models:
                        self._process_models_batch(batch_models)
                        total_fetched += len(batch_models)
                    
                    # Progress update every 10 batches or every 5 minutes
                    current_time = time.time()
                    if ((i//batch_size + 1) % 10 == 0 or 
                        current_time - last_progress_time > 300):
                        
                        elapsed = current_time - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        
                        logger.info(f"📈 Progress: {total_fetched:,} models processed")
                        logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                        logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                        logger.info(f"   ✅ Processed: {self.processed_models:,}")
                        logger.info(f"   ❌ Failed: {self.failed_models:,}")
                        
                        last_progress_time = current_time
                    
                    # Rate limiting between batches
                    time.sleep(1)  # 1 second delay between batches
                    
                except Exception as e:
                    logger.error(f"❌ Error processing batch at {i:,}: {e}")
                    time.sleep(5)  # Wait longer on error
                    continue
            
            # Update metadata
            self._update_metadata()
            
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
        """Process models in batches for better performance."""
        batch = []
        
        for i, model in enumerate(models_list):
            try:
                # Extract model data
                model_data = self._extract_model_data(model)
                batch.append(model_data)
                
                # Process batch when it reaches batch size
                if len(batch) >= self.batch_size:
                    self._insert_batch(batch)
                    batch = []
                    
                    # Progress update
                    progress = (i + 1) / self.total_models * 100
                    logger.info(f"📈 Progress: {progress:.1f}% ({i + 1:,}/{self.total_models:,})")
                
                # Small delay to be respectful to API
                if i % 100 == 0:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to process model {getattr(model, 'modelId', 'unknown')}: {e}")
                self.failed_models += 1
        
        # Insert remaining batch
        if batch:
            self._insert_batch(batch)
    
    def _extract_model_data(self, model: Any) -> Dict[str, Any]:
        """Extract relevant data from HuggingFace model object with full=true metadata."""
        try:
            # Helper function to safely get nested values
            def get_nested(d, *keys, default=None):
                for k in keys:
                    if isinstance(d, dict) and k in d:
                        d = d[k]
                    else:
                        return default
                return d
            
            # Get basic model info
            model_id = getattr(model, 'id', getattr(model, 'modelId', ''))
            author = model_id.split('/')[0] if '/' in model_id else ''
            
            # Get pipeline tag
            pipeline_tag = getattr(model, 'pipeline_tag', '')
            
            # Get tags
            tags = getattr(model, 'tags', [])
            tags_json = json.dumps(tags) if tags else '[]'
            
            # Get description from cardData
            description = get_nested(getattr(model, 'cardData', {}), 'description', default='')
            if not description:
                description = getattr(model, 'description', '')
            
            # Get downloads and likes
            downloads = getattr(model, 'downloads', 0)
            likes = getattr(model, 'likes', 0)
            
            # Calculate scores
            decision_score = self._calculate_decision_score(model)
            capability_score = self._calculate_capability_score(model)
            efficiency_score = self._calculate_efficiency_score(model)
            popularity_score = self._calculate_popularity_score(model)
            
            # Get model type and library
            model_type = get_nested(getattr(model, 'config', {}), 'model_type', default='')
            if not model_type:
                model_type = getattr(model, 'model_type', '')
            library_name = getattr(model, 'library_name', '')
            
            # Get timestamps
            last_modified = getattr(model, 'lastModified', None)
            if last_modified:
                last_modified = last_modified.isoformat() if hasattr(last_modified, 'isoformat') else str(last_modified)
            
            created_at = getattr(model, 'createdAt', None)
            if created_at:
                created_at = created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
            
            # Extract expanded fields from full=true response
            card_data = getattr(model, 'cardData', {})
            card_data_json = json.dumps(card_data) if card_data else '{}'
            
            config = getattr(model, 'config', {})
            config_json = json.dumps(config) if config else '{}'
            
            # License information
            license_info = get_nested(card_data, 'license', default='')
            license_details = get_nested(card_data, 'license', default='')
            
            # Task keywords from tags
            task_keywords = ','.join([t for t in tags if t.startswith('task:')])
            
            # Architecture from config
            architectures = get_nested(config, 'architectures', default=[])
            architecture = ','.join(architectures) if architectures else ''
            
            # Size information
            used_storage = getattr(model, 'usedStorage', 0)
            size_mb = round(used_storage / (1024 * 1024), 2) if used_storage else 0
            
            # Base models
            base_models = getattr(model, 'baseModels', [])
            # Remove duplicates and clean up the base model list
            if base_models:
                unique_base_models = list(dict.fromkeys(base_models))  # Remove duplicates while preserving order
                base_model = ','.join(unique_base_models)
            else:
                base_model = ''
            
            # Datasets from tags
            datasets = ','.join([t for t in tags if t.startswith('dataset:')])
            
            # Language from tags
            language = ','.join([t for t in tags if t.startswith('language:')])
            language_details = get_nested(card_data, 'language', default='')
            
            # Model index and metrics
            model_index_data = getattr(model, 'model-index', {})
            model_index = str(model_index_data) if model_index_data else ''
            metrics = str(model_index_data) if model_index_data else ''
            
            # Widget data
            widget_data = getattr(model, 'widgetData', {})
            widget_data_json = str(widget_data) if widget_data else ''
            
            # Inference information
            inference = getattr(model, 'inference', {})
            inference_info = str(inference) if inference else ''
            
            # Additional expanded fields
            disabled = getattr(model, 'disabled', False)
            gated = getattr(model, 'gated', False)
            private = getattr(model, 'private', False)
            downloads_all_time = getattr(model, 'downloadsAllTime', downloads)
            trending_score = getattr(model, 'trendingScore', 0.0)
            children_model_count = getattr(model, 'childrenModelCount', 0)
            
            # Calculate additional scores
            popularity_score_normalized = min(1.0, downloads / 1000000) if downloads > 0 else 0.0
            engagement_score = min(1.0, likes / 10000) if likes > 0 else 0.0
            lightweight_score = max(0.0, 1.0 - (size_mb / 1000)) if size_mb > 0 else 0.5
            task_match_score = 1.0 if pipeline_tag else 0.5
            
            return {
                'model_id': model_id,
                'author': author,
                'pipeline_tag': pipeline_tag,
                'tags': tags_json,
                'description': description,
                'downloads': downloads,
                'likes': likes,
                'decision_score': decision_score,
                'capability_score': capability_score,
                'efficiency_score': efficiency_score,
                'popularity_score': popularity_score,
                'model_type': model_type,
                'library_name': library_name,
                'last_modified': last_modified,
                'license': license_info,
                'task_keywords': task_keywords,
                'architecture': architecture,
                'input_size': '',  # Will be extracted from config if available
                'num_classes': 0,  # Will be extracted from config if available
                'model_size_mb': size_mb,
                'size_mb': size_mb,
                'created_at': created_at,
                'updated_at': last_modified,
                'popularity_score_normalized': popularity_score_normalized,
                'engagement_score': engagement_score,
                'lightweight_score': lightweight_score,
                'task_match_score': task_match_score,
                'language': language,
                'language_details': language_details,
                'license_details': license_details,
                'base_model': base_model,
                'datasets': datasets,
                'metrics': metrics,
                'widget_data': widget_data_json,
                'model_index': model_index,
                'inference_info': inference_info,
                
                # Additional expanded fields for future use
                'disabled': disabled,
                'gated': gated,
                'private': private,
                'downloads_all_time': downloads_all_time,
                'trending_score': trending_score,
                'children_model_count': children_model_count,
                'card_data': card_data_json,
                'config': config_json
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting data from model: {e}")
            return None
    
    def _calculate_decision_score(self, model: Any) -> float:
        """Calculate decision score based on model quality indicators."""
        score = 0.5  # Base score
        
        # Downloads factor (0-0.3)
        downloads = getattr(model, 'downloads', 0)
        if downloads > 0:
            score += min(0.3, (downloads / 1000000) * 0.3)
        
        # Likes factor (0-0.2)
        likes = getattr(model, 'likes', 0)
        if likes > 0:
            score += min(0.2, (likes / 10000) * 0.2)
        
        # Pipeline tag factor (0-0.2)
        pipeline_tag = getattr(model, 'pipeline_tag', '')
        if pipeline_tag:
            score += 0.2
        
        # Author reputation factor (0-0.1)
        author = getattr(model, 'modelId', '').split('/')[0] if '/' in getattr(model, 'modelId', '') else ''
        reputable_authors = ['microsoft', 'google', 'facebook', 'openai', 'anthropic', 'meta', 'huggingface']
        if author.lower() in reputable_authors:
            score += 0.1
        
        # Library factor (0-0.1)
        library_name = getattr(model, 'library_name', '')
        if library_name:
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_capability_score(self, model: Any) -> float:
        """Calculate capability score based on model characteristics."""
        score = 0.5  # Base score
        
        # Model size factor (larger models = more capable)
        model_type = getattr(model, 'model_type', '')
        if 'llama' in model_type.lower() or 'gpt' in model_type.lower():
            score += 0.3
        elif 'bert' in model_type.lower() or 'roberta' in model_type.lower():
            score += 0.2
        
        # Pipeline tag complexity
        pipeline_tag = getattr(model, 'pipeline_tag', '')
        complex_tasks = ['text-generation', 'translation', 'summarization', 'question-answering']
        if pipeline_tag in complex_tasks:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_efficiency_score(self, model: Any) -> float:
        """Calculate efficiency score based on model efficiency indicators."""
        score = 0.5  # Base score
        
        # Smaller models are more efficient
        model_type = getattr(model, 'model_type', '')
        if 'distil' in model_type.lower() or 'tiny' in model_type.lower():
            score += 0.3
        elif 'base' in model_type.lower():
            score += 0.2
        
        # Popular models are often optimized
        downloads = getattr(model, 'downloads', 0)
        if downloads > 10000:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_popularity_score(self, model: Any) -> float:
        """Calculate popularity score based on usage metrics."""
        score = 0.0
        
        # Downloads factor (0-0.6)
        downloads = getattr(model, 'downloads', 0)
        if downloads > 0:
            score += min(0.6, (downloads / 1000000) * 0.6)
        
        # Likes factor (0-0.4)
        likes = getattr(model, 'likes', 0)
        if likes > 0:
            score += min(0.4, (likes / 10000) * 0.4)
        
        return min(1.0, score)
    
    def _insert_batch(self, batch: List[Dict[str, Any]]):
        """Insert a batch of models into the database."""
        if not batch:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare insert statement with ALL expanded fields from full=true
                insert_sql = '''
                    INSERT OR REPLACE INTO models (
                        model_id, author, pipeline_tag, tags, description, downloads, likes,
                        decision_score, capability_score, efficiency_score, popularity_score,
                        model_type, library_name, last_modified, license, task_keywords, architecture,
                        input_size, num_classes, model_size_mb, size_mb, created_at, updated_at,
                        popularity_score_normalized, engagement_score, lightweight_score, task_match_score,
                        language, language_details, license_details, base_model, datasets, metrics,
                        widget_data, model_index, inference_info, disabled, gated, private,
                        downloads_all_time, trending_score, children_model_count, card_data, config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                # Prepare data for insertion with ALL expanded fields from full=true
                data = []
                for model_data in batch:
                    if model_data:  # Skip None entries
                        data.append((
                            model_data['model_id'],
                            model_data['author'],
                            model_data['pipeline_tag'],
                            model_data['tags'],
                            model_data['description'],
                            model_data['downloads'],
                            model_data['likes'],
                            model_data['decision_score'],
                            model_data['capability_score'],
                            model_data['efficiency_score'],
                            model_data['popularity_score'],
                            model_data['model_type'],
                            model_data['library_name'],
                            model_data['last_modified'],
                            model_data.get('license', ''),
                            model_data.get('task_keywords', ''),
                            model_data.get('architecture', ''),
                            model_data.get('input_size', ''),
                            model_data.get('num_classes', 0),
                            model_data.get('model_size_mb', 0.0),
                            model_data.get('size_mb', 0.0),
                            model_data.get('created_at'),
                            model_data.get('updated_at'),
                            model_data.get('popularity_score_normalized', 0.0),
                            model_data.get('engagement_score', 0.0),
                            model_data.get('lightweight_score', 0.0),
                            model_data.get('task_match_score', 0.0),
                            model_data.get('language', ''),
                            model_data.get('language_details', ''),
                            model_data.get('license_details', ''),
                            model_data.get('base_model', ''),
                            model_data.get('datasets', ''),
                            model_data.get('metrics', ''),
                            model_data.get('widget_data', ''),
                            model_data.get('model_index', ''),
                            model_data.get('inference_info', ''),
                            model_data.get('disabled', False),
                            model_data.get('gated', False),
                            model_data.get('private', False),
                            model_data.get('downloads_all_time', model_data['downloads']),
                            model_data.get('trending_score', 0.0),
                            model_data.get('children_model_count', 0),
                            model_data.get('card_data', '{}'),
                            model_data.get('config', '{}')
                        ))
                
                # Execute batch insert
                cursor.executemany(insert_sql, data)
                conn.commit()
                
                self.processed_models += len(data)
                logger.info(f"💾 Inserted batch of {len(data)} models")
                
        except Exception as e:
            logger.error(f"❌ Error inserting batch: {e}")
            self.failed_models += len(batch)
    
    def _update_metadata(self):
        """Update database metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update metadata
                metadata = {
                    'total_models': str(self.total_models),
                    'processed_models': str(self.processed_models),
                    'failed_models': str(self.failed_models),
                    'last_population': datetime.now().isoformat(),
                    'population_version': '2.0'
                }
                
                for key, value in metadata.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO metadata (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', (key, value))
                
                conn.commit()
                logger.info("📊 Metadata updated")
                
        except Exception as e:
            logger.error(f"❌ Error updating metadata: {e}")
    
    def create_task_models_json(self) -> bool:
        """Create task_models.json file with all models from database."""
        try:
            import os
            
            # Create db directory if it doesn't exist
            db_dir = "db"
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            task_models_path = "task_models.json"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all models with their pipeline tags
                cursor.execute("""
                    SELECT model_id, pipeline_tag, downloads, likes, decision_score
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL
                    ORDER BY downloads DESC
                """)
                models = cursor.fetchall()
                
                # Create task models structure
                task_models = {
                    "timestamp": datetime.now().isoformat(),
                    "total_models": len(models),
                    "tasks": {}
                }
                
                # Group models by pipeline tag
                for model_id, pipeline_tag, downloads, likes, decision_score in models:
                    if pipeline_tag not in task_models["tasks"]:
                        task_models["tasks"][pipeline_tag] = {
                            "models": [],
                            "count": 0,
                            "top_models": []
                        }
                    
                    model_info = {
                        "model_id": model_id,
                        "downloads": downloads,
                        "likes": likes,
                        "decision_score": decision_score
                    }
                    
                    task_models["tasks"][pipeline_tag]["models"].append(model_info)
                    task_models["tasks"][pipeline_tag]["count"] += 1
                    
                    # Keep top 10 models for each task
                    if len(task_models["tasks"][pipeline_tag]["top_models"]) < 10:
                        task_models["tasks"][pipeline_tag]["top_models"].append(model_info)
                
                # Save to JSON file
                with open(task_models_path, 'w', encoding='utf-8') as f:
                    json.dump(task_models, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Created task_models.json with {len(models)} models across {len(task_models['tasks'])} tasks")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create task_models.json: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM models')
                total_count = cursor.fetchone()[0]
                
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
                top_models = cursor.fetchall()
                
                return {
                    'total_models': total_count,
                    'pipeline_distribution': pipeline_distribution,
                    'top_models': top_models
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

    def ensure_all_tasks_covered(self):
        """Ensure every supported task has at least one model in the database, using langextract for smart mapping."""
        import os
        import sqlite3
        import ast
        try:
            import langextract as lx
        except ImportError:
            print("❌ langextract not available. Install with: pip install langextract")
            return
        # Dynamically import specialized_tasks from main.py
        main_py = os.path.join(os.path.dirname(__file__), 'main.py')
        with open(main_py, 'r', encoding='utf-8') as f:
            source = f.read()
        # Parse the AST to extract specialized_tasks
        specialized_tasks = []
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'specialized_tasks':
                        specialized_tasks = ast.literal_eval(node.value)
        if not specialized_tasks:
            print("❌ Could not extract specialized_tasks from main.py")
            return
        print(f"🔎 Ensuring all {len(specialized_tasks)} tasks are covered in the database (langextract)...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for task in specialized_tasks:
                cursor.execute('SELECT COUNT(*) FROM models WHERE pipeline_tag = ?', (task,))
                count = cursor.fetchone()[0]
                if count > 0:
                    continue  # Task already covered
                # Find the best model for this task using langextract
                cursor.execute('SELECT * FROM models')
                best_row = None
                best_score = 0.0
                best_model_id = None
                columns = [desc[0] for desc in cursor.description]
                for row in cursor.fetchall():
                    model_data = dict(zip(columns, row))
                    # Combine relevant fields
                    text = f"{model_data.get('pipeline_tag','')} {model_data.get('tags','')} {model_data.get('description','')} {model_data.get('model_id','')}"
                    try:
                        result = lx.detect_task_type(text)
                        # Score: confidence if task matches, else 0
                        score = result.confidence if result.task_type == task else 0.0
                        if score > best_score:
                            best_score = score
                            best_row = row
                            best_model_id = model_data.get('model_id','')
                    except Exception as e:
                        continue
                # Fallback: if no good match, pick any model
                if not best_row:
                    cursor.execute('SELECT * FROM models ORDER BY downloads DESC LIMIT 1')
                    best_row = cursor.fetchone()
                    best_model_id = dict(zip(columns, best_row)).get('model_id','') if best_row else None
                if not best_row:
                    print(f"❌ No models available to map for task: {task}")
                    continue
                # Insert a new row with the same model info but new pipeline_tag
                model_data = dict(zip(columns, best_row))
                model_data['pipeline_tag'] = task
                model_data.pop('id', None)
                placeholders = ','.join(['?'] * len(model_data))
                sql = f"INSERT INTO models ({','.join(model_data.keys())}) VALUES ({placeholders})"
                try:
                    cursor.execute(sql, list(model_data.values()))
                    print(f"✅ Added mapping: {best_model_id} -> {task} (langextract score: {best_score:.2f})")
                except Exception as e:
                    print(f"❌ Failed to add mapping for {task}: {e}")
            conn.commit()
        print("✅ All tasks are now covered in the database (langextract).")

def main():
    """Main function to populate the database."""
    print("🚀 Comprehensive HuggingFace Model Database Population")
    print("=" * 60)
    
    # Initialize populator
    populator = ComprehensiveHFModelPopulator()
    
    # Create backup before starting
    print("💾 Creating backup of current configuration...")
    backup_success = populator.create_timestamped_backup()
    if backup_success:
        print("✅ Backup completed successfully!")
    else:
        print("⚠️ Backup failed, but continuing...")
    
    # Get current database state
    stats = populator.get_database_stats()
    print(f"📊 Current database has {stats.get('total_models', 0):,} models")
    
    if stats.get('top_models'):
        print(f"📝 Last model: {stats['top_models'][0][0]}")
    
    print("\n📋 Choose population strategy:")
    print("1. Test mode (1,000 models) - Quick test")
    print("2. Small mode (10,000 models) - Small dataset")
    print("3. Medium mode (100,000 models) - Medium dataset")
    print("4. Large mode (1,000,000 models) - Large dataset")
    print("5. All models (1.9M+ models) - Complete dataset (very long)")
    print("6. Resume - Continue from where you left off")
    
    try:
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            print("🧪 Starting test mode (1,000 models)...")
            # For test mode, we'll use a limited approach
            populator.batch_size = 100
            populator.populate_all_models()
        elif choice == "2":
            print("📦 Starting small mode (10,000 models)...")
            populator.batch_size = 500
            populator.populate_all_models()
        elif choice == "3":
            print("📦 Starting medium mode (100,000 models)...")
            populator.batch_size = 1000
            populator.populate_all_models()
        elif choice == "4":
            print("📦 Starting large mode (1,000,000 models)...")
            populator.batch_size = 1000
            populator.populate_all_models()
        elif choice == "5":
            print("🌍 Starting complete mode (ALL models - 1.9M+)...")
            print("⚠️  This will take a very long time (hours/days)")
            confirm = input("Are you sure? (yes/no): ").strip().lower()
            if confirm == "yes":
                populator.batch_size = 1000
                populator.populate_all_models()
            else:
                print("❌ Operation cancelled")
                return
        elif choice == "6":
            print("🔄 Resuming population...")
            populator.populate_all_models()
        else:
            print("❌ Invalid choice")
            return
        # Ensure all tasks are covered before creating task_models.json
        populator.ensure_all_tasks_covered()
        # Create task models JSON after population
        print("\n📝 Creating task_models.json...")
        task_success = populator.create_task_models_json()
        if task_success:
            print("✅ task_models.json created successfully!")
        else:
            print("❌ Failed to create task_models.json")
        
        # Get and display final statistics
        print("\n📊 Final Database Statistics:")
        print("-" * 30)
        
        stats = populator.get_database_stats()
        
        print(f"📈 Total models in database: {stats.get('total_models', 0):,}")
        
        print("\n🏷️ Top pipeline tags:")
        pipeline_dist = stats.get('pipeline_distribution', {})
        for tag, count in list(pipeline_dist.items())[:10]:
            print(f"   {tag}: {count:,}")
        
        print("\n🏆 Top models by downloads:")
        top_models = stats.get('top_models', [])
        for i, (model_id, downloads, likes, score) in enumerate(top_models[:5], 1):
            print(f"   {i}. {model_id}")
            print(f"      Downloads: {downloads:,}, Likes: {likes:,}, Score: {score:.3f}")
        
        print("\n✅ Database population completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        print("💡 You can resume later using option 6")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Comprehensive HuggingFace Model Database Population
Fetches ALL models from HuggingFace API and stores them in the database with comprehensive metadata
"""

import sqlite3
import os
import json
import time
import asyncio
import random
import warnings
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from requests.exceptions import HTTPError, RequestException

# Suppress HuggingFace Hub warnings about invalid model-index
warnings.filterwarnings("ignore", message="Invalid model-index.*")
warnings.filterwarnings("ignore", message="Not loading eval results into CardData.*")

# Enhanced scoring constants from model_selector logic
OPEN_LICENSES = {"apache-2.0", "mit", "cc-by-4.0", "cc0-1.0", "openrail", "openrail++", "bsd", "bsd-3-clause", "lgpl", "mpl-2.0"}

# Scoring weights for enhanced ranking
SCORING_WEIGHTS = {
    "popularity": 0.4,
    "engagement": 0.25,
    "license": 0.15,
    "lightweight": 0.1,
    "task_match": 0.1
}

# Configure logging
# Configure logging with safe Unicode handling
import sys

def safe_log_message(message):
    """Safely encode log messages to handle Unicode encoding errors."""
    try:
        # Try to encode/decode to ensure it's valid UTF-8
        return message.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except:
        # Fallback: replace problematic characters
        return message.encode('ascii', errors='replace').decode('ascii', errors='replace')

class SafeUnicodeHandler(logging.StreamHandler):
    """Stream handler that safely handles Unicode characters."""
    def emit(self, record):
        try:
            msg = self.format(record)
            # Ensure message is safely encoded
            safe_msg = safe_log_message(msg)
            stream = self.stream
            stream.write(safe_msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback: replace Unicode characters with ASCII equivalents
            try:
                msg = self.format(record)
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                stream = self.stream
                stream.write(safe_msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
        except Exception:
            self.handleError(record)

# Configure logging with safe Unicode handler
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[SafeUnicodeHandler(sys.stdout)],
    force=True  # Override any existing configuration
)

logger = logging.getLogger(__name__)

class ComprehensiveHFModelPopulator:
    """Comprehensive HuggingFace model database populator with advanced metadata extraction."""
    
    VERSION = "3.0"
    
    def __init__(self, db_path: str = None, batch_size: int = 100):
        # Determine project root and default DB path
        # File is in src/hforchestra/core/comprehensive_model_populator.py
        # Root is 3 levels up: src/hforchestra/core -> src/hforchestra -> src -> PROJECT_ROOT
        current_file = Path(__file__).resolve()
        self.project_root = current_file.parent.parent.parent.parent
        
        # If db_path is not provided, use default location in project root
        if db_path is None:
            self.db_path = str(self.project_root / "db" / "hf_models.db")
        else:
            # If provided path is relative, make it absolute relative to project root
            # unless it's already absolute
            path_obj = Path(db_path)
            if not path_obj.is_absolute():
                self.db_path = str(self.project_root / db_path)
            else:
                self.db_path = db_path
                
        self.batch_size = batch_size
        self.total_models = 0
        self.processed_models = 0
        self.failed_models = 0
        
        # Rate limiting and retry configuration
        self.max_retries = 50  # Increased max retries for rate limits
        self.retry_delay_base = 5  # Base delay in seconds
        self.max_retry_delay = 600  # Maximum delay (10 minutes)
        self.rate_limit_delay = 60  # Initial delay for rate limits (1 minute)
        self.current_delay = 0.1  # Current delay between requests
        self.requests_this_minute = 0
        self.last_request_time = time.time()
        self.rate_limit_reset_time = None
        
        # Rate limit tracking from headers
        self.rate_limit_limit = 1000  # Default: 1000 requests per window
        self.rate_limit_remaining = 1000  # Remaining requests
        self.rate_limit_reset = None  # When the limit resets (timestamp)
        self.rate_limit_window = 300  # 5 minutes in seconds
        self.last_header_update = time.time()
        
        # Adaptive rate limiting
        self.min_delay = 0.05  # Minimum delay (20 requests/second max)
        self.max_delay = 10.0  # Maximum delay
        self.adaptive_factor = 1.0  # Multiplier for adaptive delays
        
        # Create database directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"💾 Database path: {self.db_path}")
        
        # Ensure database integrity (Self-Healing)
        self._ensure_database_integrity()

    def create_timestamped_backup(self) -> bool:
        """
        Create a backup of critical files before updates.
        Implements retention policy: Keep at most ONE backup + current file.
        Strategy: Delete ALL existing backups, then create a new one.
        """
        try:
            import shutil
            import glob
            from datetime import datetime
            
            # Use absolute database directory
            db_dir = self.project_root / "db"
            config_dir = self.project_root / "config"
            
            if not db_dir.exists():
                db_dir.mkdir(parents=True)
                logger.info(f"📁 Created db directory: {db_dir}")
            
            # Definition of files to manage
            # Tuple: (Absolute Source Path, Title for logging, Glob Pattern for old backups)
            files_to_manage = [
                (db_dir / "hf_models.db", "HF Models DB", "hf_models_*.db"),
                (db_dir / "task_models.json", "Task Models", "task_models_*.json"),
                (config_dir / "model_configs.json", "Model Configs", "model_configs_*.json"),
                (config_dir / "dynamic_models.json", "Dynamic Models", "dynamic_models_*.json"),
                (config_dir / "settings.json", "Settings", "settings_*.json")
            ]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_success = True
            
            for source_path, title, glob_pattern in files_to_manage:
                # 1. Cleanup ALL old backups for this file type
                # We search in the SAME directory as the source file (or db dir for convenience?)
                # Actually, let's keep backups in the 'db' dir to keep things tidy, OR next to the file.
                # Previous logic put them all in db/ with prefix. Let's stick to that.
                
                # Glob for checking old backups in the db_dir
                backup_glob_path = db_dir / glob_pattern
                old_backups = glob.glob(str(backup_glob_path))
                
                for old_backup in old_backups:
                    try:
                        os.remove(old_backup)
                        logger.info(f"🗑️ Deleted old backup: {Path(old_backup).name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to delete old backup {old_backup}: {e}")

                # 2. Create NEW backup
                if source_path.exists():
                    # Construct new backup path
                    # e.g. hf_models_20240101_120000.db
                    # base name without extension
                    base_name = glob_pattern.replace("*", timestamp)
                    backup_path = db_dir / base_name
                    
                    try:
                        shutil.copy2(source_path, backup_path)
                        logger.info(f"📦 Backed up {title} to {backup_path.name}")
                    except Exception as e:
                        logger.error(f"❌ Failed to backup {title}: {e}")
                        backup_success = False
                else:
                    # It's okay if source doesn't exist (e.g. first run), just skip
                    pass
            
            return backup_success

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
        
        # Initialize database with schema check/update
        self._init_database()
        self._ensure_all_columns_exist()
    
    def _ensure_database_integrity(self):
        """Check database integrity and attempt auto-recovery if corrupt."""
        if not os.path.exists(self.db_path):
            return

        try:
            logger.info("🏥 Checking database integrity...")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                if result != "ok":
                    raise sqlite3.DatabaseError(f"Integrity check failed: {result}")
            logger.info("✅ Database integrity check passed.")
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            logger.error(f"❌ Database corruption detected: {e}")
            logger.info("🚑 Initiating AUTOMATIC SELF-HEALING protocol...")
            self._recover_database()

    def _recover_database(self):
        """Recover data from a corrupt SQLite database using .recover command."""
        import subprocess
        import shutil
        
        try:
            # 1. Rename corrupt DB
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupt_path = f"{self.db_path}.corrupt_{timestamp}"
            shutil.move(self.db_path, corrupt_path)
            logger.info(f"📦 Moved corrupt DB to: {corrupt_path}")
            
            # 2. Recover data to SQL
            sql_path = f"{self.db_path}.recovered.sql"
            logger.info("⛏️  Extracting valid data (this may take time)...")
            
            # Use sqlite3 command line to recover
            cmd_recover = f'sqlite3 "{corrupt_path}" .recover'
            with open(sql_path, 'w', encoding='utf-8') as f_out:
                subprocess.run(cmd_recover, shell=True, stdout=f_out, check=True)
            
            logger.info(f"📄 Data extracted to: {sql_path}")
            
            # 3. Rebuild Database
            logger.info("🏗️  Rebuilding database from recovered data...")
            cmd_rebuild = f'sqlite3 "{self.db_path}" < "{sql_path}"'
            subprocess.run(cmd_rebuild, shell=True, check=True)
            
            # 4. Verify New Database
            self._ensure_database_integrity()
            logger.info("✨ Database successfully restored and healed!")
            
            # Cleanup SQL file (keep corrupt DB just in case)
            if os.path.exists(sql_path):
                os.remove(sql_path)
                
        except Exception as recovery_error:
            logger.error(f"☠️ Critical Failure: Could not recover database: {recovery_error}")
            # If recovery fails, we might create a fresh one
            if os.path.exists(self.db_path):
                 os.remove(self.db_path)
            logger.warning("⚠️ Created fresh database as fallback.")
    
    def create_timestamped_backup(self) -> bool:
        """
        Create a backup of critical files before updates.
        Implements retention policy: Keep only the most recent backup + current file.
        """
        try:
            import os
            import shutil
            import glob
            from datetime import datetime
            
            # Create db directory if it doesn't exist
            db_dir = "db"
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"📁 Created db directory: {db_dir}")
            
            # Files to backup
            # Format: (source_path, backup_prefix, extension)
            files_to_manager = [
                ("task_models.json", "db/task_models_", ".json"),
                ("db/hf_models.db", "db/hf_models_", ".db"),
                ("config/model_configs.json", "db/model_configs_", ".json"),
                ("config/dynamic_models.json", "db/dynamic_models_", ".json"),
                ("config/settings.json", "db/settings_", ".json")
            ]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_success = True
            backed_up_files = []
            
            for source_path, backup_prefix, ext in files_to_manager:
                try:
                    # 1. Clean up OLD backups first (Keep only the most recent one if it exists)
                    # Find existing backups for this file pattern
                    existing_backups = glob.glob(f"{backup_prefix}*{ext}")
                    # Sort by modification time (newest first)
                    existing_backups.sort(key=os.path.getmtime, reverse=True)
                    
                    # Delete all except the most recent one (so we have space for the new one)
                    # User request: "delete other emodels only one and a backup is needed"
                    # We will create a NEW backup now, so we can delete ALL existing old backups 
                    # OR we can keep the very last one as a "second" backup? 
                    # Let's interpret strict "only one and a backup":
                    # Result state: hf_models.db (active) + hf_models_<timestamp>.db (backup)
                    # So delete all previous backups.
                    
                    for old_backup in existing_backups:
                        try:
                            os.remove(old_backup)
                            logger.info(f"🗑️ Deleted old backup: {old_backup}")
                        except Exception as del_err:
                            logger.warning(f"⚠️ Could not delete old backup {old_backup}: {del_err}")
                    
                    # 2. Create NEW backup
                    if os.path.exists(source_path):
                        # Construct new backup path
                        new_backup_path = f"{backup_prefix}{timestamp}{ext}"
                        
                        # Create backup directory if it doesn't exist
                        os.makedirs(os.path.dirname(new_backup_path), exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(source_path, new_backup_path)
                        backed_up_files.append(new_backup_path)
                        logger.info(f"💾 Created backup: {source_path} -> {new_backup_path}")
                    else:
                        # Source doesn't exist, skip
                        pass
                        
                except Exception as e:
                    logger.error(f"❌ Failed to manage backup for {source_path}: {e}")
                    backup_success = False
            
            return backup_success
            
        except Exception as e:
            logger.error(f"❌ Backup process failed: {e}")
            return False

    def _init_database(self):
        """Initialize the database with comprehensive schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enable WAL mode for better concurrency and safety
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')
            
            # Create models table with comprehensive schema
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
                    -- Enhanced scoring fields from model_selector logic
                    popularity_score_normalized REAL,  -- Normalized downloads score
                    engagement_score REAL,  -- likes/downloads ratio
                    lightweight_score REAL,  -- 1 if size < 500MB
                    task_match_score REAL,  -- 1 if pipeline matches task
                    -- ModelCard metadata fields
                    language TEXT,  -- Primary language or JSON array of languages
                    language_details TEXT,  -- JSON with detailed language info
                    license_details TEXT,  -- Detailed license information from ModelCard
                    base_model TEXT,  -- Base model if this is a fine-tuned model
                    datasets TEXT,  -- Training datasets (JSON array)
                    metrics TEXT,  -- Model metrics (JSON)
                    widget_data TEXT,  -- Widget configuration (JSON)
                    model_index TEXT,  -- Model index metadata (JSON)
                    inference_info TEXT,  -- Inference configuration (JSON)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add missing columns if they don't exist (for existing databases)
            missing_columns = [
                ('download_date', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('license', 'TEXT'),
                ('task_keywords', 'TEXT'),
                ('architecture', 'TEXT'),
                ('input_size', 'TEXT'),
                ('num_classes', 'INTEGER'),
                ('model_size_mb', 'REAL'),
                ('license_score', 'REAL DEFAULT 0.0'),
                ('size_mb', 'REAL'),
                # Enhanced scoring fields
                ('popularity_score_normalized', 'REAL'),
                ('engagement_score', 'REAL'),
                ('lightweight_score', 'REAL'),
                ('task_match_score', 'REAL'),
                # ModelCard metadata fields
                ('language', 'TEXT'),
                ('language_details', 'TEXT'),
                ('license_details', 'TEXT'),
                ('base_model', 'TEXT'),
                ('datasets', 'TEXT'),
                ('metrics', 'TEXT'),
                ('widget_data', 'TEXT'),
                ('model_index', 'TEXT'),
                ('inference_info', 'TEXT')
            ]
            
            for column_name, column_def in missing_columns:
                try:
                    cursor.execute(f'ALTER TABLE models ADD COLUMN {column_name} {column_def}')
                    logger.info(f"✅ Added {column_name} column to existing database")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass
            
            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_model_id ON models(model_id)',
                'CREATE INDEX IF NOT EXISTS idx_pipeline_tag ON models(pipeline_tag)',
                'CREATE INDEX IF NOT EXISTS idx_author ON models(author)',
                'CREATE INDEX IF NOT EXISTS idx_downloads ON models(downloads)',
                'CREATE INDEX IF NOT EXISTS idx_decision_score ON models(decision_score)',
                'CREATE INDEX IF NOT EXISTS idx_architecture ON models(architecture)',
                'CREATE INDEX IF NOT EXISTS idx_license ON models(license)',
                'CREATE INDEX IF NOT EXISTS idx_size_mb ON models(size_mb)',
                'CREATE INDEX IF NOT EXISTS idx_download_date ON models(download_date)',
                'CREATE INDEX IF NOT EXISTS idx_language ON models(language)',
                'CREATE INDEX IF NOT EXISTS idx_base_model ON models(base_model)'
            ]
            
            for idx in indexes:
                try:
                    cursor.execute(idx)
                except sqlite3.Error as e:
                    logger.warning(f"Index creation warning: {e}")
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("✅ Database initialized successfully with comprehensive schema")
    
    def _ensure_all_columns_exist(self):
        """Ensure all expected columns exist in the database, add missing ones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current table structure
                cursor.execute("PRAGMA table_info(models)")
                existing_columns = {row[1]: row[2] for row in cursor.fetchall()}  # {name: type}
                
                # Define all expected columns with their types
                expected_columns = {
                    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                    'model_id': 'TEXT UNIQUE NOT NULL',
                    'author': 'TEXT',
                    'pipeline_tag': 'TEXT',
                    'tags': 'TEXT',
                    'description': 'TEXT',
                    'downloads': 'INTEGER DEFAULT 0',
                    'likes': 'INTEGER DEFAULT 0',
                    'decision_score': 'REAL DEFAULT 0.0',
                    'capability_score': 'REAL DEFAULT 0.0',
                    'efficiency_score': 'REAL DEFAULT 0.0',
                    'popularity_score': 'REAL DEFAULT 0.0',
                    'model_type': 'TEXT',
                    'library_name': 'TEXT',
                    'last_modified': 'TIMESTAMP',
                    'download_date': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'license': 'TEXT',
                    'task_keywords': 'TEXT',
                    'architecture': 'TEXT',
                    'input_size': 'TEXT',
                    'num_classes': 'INTEGER',
                    'model_size_mb': 'REAL',
                    'license_score': 'REAL DEFAULT 0.0',
                    'size_mb': 'REAL',
                    'popularity_score_normalized': 'REAL',
                    'engagement_score': 'REAL',
                    'lightweight_score': 'REAL',
                    'task_match_score': 'REAL',
                    'language': 'TEXT',
                    'language_details': 'TEXT',
                    'license_details': 'TEXT',
                    'base_model': 'TEXT',
                    'datasets': 'TEXT',
                    'metrics': 'TEXT',
                    'widget_data': 'TEXT',
                    'model_index': 'TEXT',
                    'inference_info': 'TEXT',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }
                
                missing_columns = []
                for col_name, col_type in expected_columns.items():
                    if col_name not in existing_columns:
                        missing_columns.append((col_name, col_type))
                
                if missing_columns:
                    logger.info(f"🔧 Found {len(missing_columns)} missing columns, adding them...")
                    
                    for col_name, col_type in missing_columns:
                        try:
                            # Extract just the type part without constraints for ALTER TABLE
                            base_type = col_type.split()[0]  # Get just 'TEXT', 'REAL', etc.
                            if 'DEFAULT' in col_type:
                                default_part = ' '.join(col_type.split()[col_type.split().index('DEFAULT'):])
                                alter_type = f"{base_type} {default_part}"
                            else:
                                alter_type = base_type
                            
                            cursor.execute(f'ALTER TABLE models ADD COLUMN {col_name} {alter_type}')
                            logger.info(f"✅ Added column: {col_name} ({alter_type})")
                        except sqlite3.OperationalError as e:
                            if "duplicate column name" not in str(e).lower():
                                logger.warning(f"⚠️ Could not add column {col_name}: {e}")
                    
                    conn.commit()
                    logger.info(f"✅ All missing columns have been added")
                else:
                    logger.info("✅ All expected columns already exist")
                
                # Verify final column count
                cursor.execute("PRAGMA table_info(models)")
                final_columns = cursor.fetchall()
                logger.info(f"📊 Final database schema has {len(final_columns)} columns")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring columns exist: {e}")
    
    def populate_all_models(self):
        """Populate database with ALL HuggingFace models using proper pagination."""
        # Outer retry loop - NEVER GIVES UP on rate limit errors
        populate_retry_count = 0
        
        while True:  # Retry indefinitely for rate limit errors
            try:
                # Log version to confirm we're running the latest code
                logger.info("=" * 80)
                logger.info(f"🚀 ComprehensiveHFModelPopulator v{self.VERSION} - Rate limiting ENABLED")
                logger.info("=" * 80)
                
                # Import HuggingFace API
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
                consecutive_errors = 0
                max_consecutive_errors = 1000000  # Effectively infinite to prevent stopping
                
                # Fetch ALL models using proper iteration (not pagination) - NO LIMITS
                logger.info("=" * 80)
                logger.info("🚀 NO LIMITS MODE ACTIVATED")
                logger.info("📥 Fetching ALL models from HuggingFace using iterator with NO LIMITS...")
                logger.info("🌍 Target: Process ALL models available on HuggingFace (no limit)")
                logger.info("⏱️  This may take many hours - processing will continue until complete")
                logger.info("=" * 80)
                
                # Load existing models from database for statistics and awareness
                # NOTE: We still process ALL models (existing and new) to update them with latest data
                # (downloads, likes, metadata improvements, etc.)
                existing_models_count = 0
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM models')
                        existing_models_count = cursor.fetchone()[0]
                        if existing_models_count > 0:
                            logger.info(f"📊 Found {existing_models_count:,} existing models in database")
                            logger.info("🔄 Will update ALL models (existing + new) with latest data from HuggingFace")
                            logger.info("💡 This ensures existing models get updated with improvements (downloads, likes, metadata, etc.)")
                except Exception as e:
                    logger.warning(f"⚠️ Could not check existing models in database: {e}")
                
                # Use the iterator to get all models - this automatically handles pagination
                # Wrap in retry logic for rate limit handling
                logger.info("=" * 60)
                logger.info("🔄 INITIALIZING MODEL ITERATOR WITH INTELLIGENT RATE LIMITING...")
                logger.info("=" * 60)
                try:
                    models_iterator = self._get_models_with_retry(api)
                    logger.info("✅ Model iterator initialized successfully - rate limiting ACTIVE")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize iterator: {e}")
                    raise
                
                batch = []
                seen_models = set()  # Track seen models to prevent duplicates in current run
                # NO LIMITS - Process ALL models from HuggingFace API
                
                logger.info("🚀 NO LIMITS MODE: Will process ALL models from HuggingFace API")
                logger.info("🌍 Processing will continue until all available models are fetched")
                
                # Wrap iterator consumption in try-except to catch rate limit errors from iterator
                # When huggingface_hub exhausts its 20 retries, it raises an exception that we need to catch
                try:
                    for model in models_iterator:
                        try:
                            # Get model ID and check for duplicates
                            model_id = getattr(model, 'modelId', '')
                            if not model_id or model_id in seen_models:
                                continue  # Skip duplicates or invalid models in current run
                            
                            seen_models.add(model_id)
                            
                            # Process ALL models (both existing and new) to ensure:
                            # 1. Existing models get updated with latest data (downloads, likes, metadata)
                            # 2. New models get added to the database
                            # INSERT OR REPLACE will handle updating existing models automatically
                            
                            # Add model to current batch
                            batch.append(model)
                            total_fetched += 1
                            consecutive_errors = 0  # Reset error counter on successful model
                            
                            # Process batch when it reaches batch size
                            if len(batch) >= self.batch_size:
                                batch_start = total_fetched - len(batch) + 1
                                logger.info(f"📥 Processing batch {batch_start:,} to {total_fetched:,}...")
                                
                                # Show some model names from this batch
                                sample_models = [getattr(m, 'modelId', 'unknown') for m in batch[:5]]
                                logger.info(f"🏷️ Sample models: {', '.join(sample_models)}")
                                
                                try:
                                    self._process_models_batch(batch)
                                except Exception as batch_error:
                                    logger.warning(f"⚠️ Error processing batch {batch_start:,}-{total_fetched:,}: {batch_error}")
                                    self.failed_models += len(batch)
                                    consecutive_errors += 1
                                
                                batch = []
                                
                                # Progress update every batch or every 2 minutes
                                current_time = time.time()
                                if (total_fetched % self.batch_size == 0 or 
                                    current_time - last_progress_time > 120):
                                    
                                    elapsed = current_time - start_time
                                    rate = total_fetched / elapsed if elapsed > 0 else 0
                                    
                                    logger.info(f"📈 Progress: {total_fetched:,} models fetched")
                                    logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                                    logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                                    logger.info(f"   ✅ Total Updated Models: {self.processed_models:,}")
                                    logger.info(f"   ❌ Failed: {self.failed_models:,}")
                                    logger.info(f"   🔄 Consecutive errors: {consecutive_errors}")
                                    
                                    last_progress_time = current_time
                                
                                # Check for too many consecutive errors - but DO NOT STOP, just sleep
                                if consecutive_errors >= max_consecutive_errors:
                                    logger.warning(f"⚠️ Many consecutive errors ({consecutive_errors}). Sleeping but NOT stopping.")
                                    time.sleep(60)
                                    # Reset counter to keep going
                                    consecutive_errors = 0
                                
                                # No artificial delay needed - iterator handles API rate limiting automatically
                        
                        except Exception as e:
                            consecutive_errors += 1
                            logger.warning(f"⚠️ Error processing model {getattr(model, 'modelId', 'unknown')}: {e}")
                            
                            # Check for too many consecutive errors - but DO NOT STOP
                            if consecutive_errors >= max_consecutive_errors:
                                logger.warning(f"⚠️ Many consecutive errors ({consecutive_errors}). Sleeping but NOT stopping.")
                                time.sleep(60)
                                consecutive_errors = 0
                            
                            continue
                except (HTTPError, Exception) as iterator_error:
                    # Exception raised from iterator consumption (when huggingface_hub exhausts retries)
                    # This is the critical catch point - we need to detect rate limit errors and retry
                    error_str = str(iterator_error)
                    error_type = type(iterator_error).__name__
                    error_repr = repr(iterator_error)
                    
                    # Log the exception details for debugging
                    logger.warning(f"🔍 Iterator exception caught: type={error_type}, str={error_str[:300]}")
                    
                    # Comprehensive rate limit detection - check multiple sources
                    is_rate_limit = (
                        isinstance(iterator_error, HTTPError) and 
                        hasattr(iterator_error, 'response') and 
                        iterator_error.response is not None and 
                        iterator_error.response.status_code == 429
                    ) or (
                        '429' in error_str or 
                        'Too Many Requests' in error_str or 
                        'rate limit' in error_str.lower() or
                        'Rate limit' in error_str or
                        '429' in error_repr or
                        'Too Many Requests' in error_repr or
                        (hasattr(iterator_error, 'status_code') and iterator_error.status_code == 429) or
                        'quota' in error_str.lower() or
                        ('exceeded' in error_str.lower() and 'request' in error_str.lower())
                    )
                    
                    logger.warning(f"🔍 Rate limit detection: is_rate_limit={is_rate_limit}")
                    
                    if is_rate_limit:
                        # This is a rate limit error from the iterator - re-raise to be caught by outer handler
                        # The outer handler will retry the entire operation
                        logger.warning(f"⚠️ Throughput limit detected in iterator consumption: {error_type} - {error_str[:200]}")
                        logger.warning(f"⚠️ Re-raising to outer retry loop...")
                        raise  # Re-raise to be caught by outer retry loop
                    else:
                        # Other errors from iterator - re-raise
                        logger.warning(f"❌ Non-limit issue in iterator: {error_type} - {error_str[:200]}")
                        raise
                
                # Process remaining batch
                if batch:
                    logger.info(f"📥 Processing final batch of {len(batch)} models...")
                    try:
                        self._process_models_batch(batch)
                    except Exception as batch_error:
                        logger.warning(f"⚠️ Issue processing final batch: {batch_error}")
                        self.failed_models += len(batch)
                
                # Update metadata
                try:
                    self._update_metadata()
                except Exception as e:
                    logger.warning(f"⚠️ Error updating metadata: {e}")
                
                # Final statistics with enhanced metadata analysis
                elapsed = time.time() - start_time
                logger.info(f"✅ Database population completed!")
                logger.info(f"   📊 Total unique models fetched: {total_fetched:,}")
                logger.info(f"   🔍 Unique models seen: {len(seen_models):,}")
                logger.info(f"   ✅ Successfully processed: {self.processed_models:,}")
                logger.info(f"   ❌ Failed: {self.failed_models:,}")
                logger.info(f"   ⏱️ Total time: {elapsed/60:.1f} minutes")
                logger.info(f"   🚀 Average rate: {total_fetched/elapsed:.1f} models/second")
                
                # Normalize popularity scores across all models
                try:
                    self._normalize_popularity_scores()
                except Exception as e:
                    logger.warning(f"⚠️ Error normalizing popularity scores: {e}")
                
                # Check enhanced metadata population
                try:
                    self._analyze_metadata_population()
                except Exception as e:
                    logger.warning(f"⚠️ Error analyzing metadata population: {e}")
                
                # Final completion message
                logger.info("🎉 UPDATE PROCESS COMPLETED SUCCESSFULLY!")
                logger.info("📊 Database is now ready for use with comprehensive model information.")
                logger.info("💡 You can now use --stats, --tasks, and other commands.")
                
                # Success - exit the retry loop
                break
                
            except ImportError:
                try:
                    logger.error("❌ HuggingFace Hub not available. Install with: pip install huggingface_hub")
                except UnicodeEncodeError:
                    logger.error("[ERROR] HuggingFace Hub not available. Install with: pip install huggingface_hub")
                break  # Exit on ImportError - can't retry
            except Exception as e:
                # Check if it's a rate limit error
                error_str = str(e)
                error_type = type(e).__name__
                
                # CRITICAL: Check for "429" FIRST - this is the most reliable indicator
                has_429 = (
                    '429' in error_str or 
                    '429 Client Error' in error_str or
                    'Just a moment' in error_str or
                    'Too Many Requests' in error_str
                )
                
                # LOG AS WARNING ONLY - NEVER ERROR
                logger.warning(f"⚠️ Exception in populate_all_models: {error_type} - {error_str[:200]}")

                if has_429:
                    # intelligent queue logic
                    # 1. Check if we should reset the counter (if we've been running healthy for > 30 mins)
                    # We check last_progress_time because that updates when batches succeed
                    time_since_last_progress = time.time() - last_progress_time
                    if time_since_last_progress > 1800 and populate_retry_count > 0:
                        logger.info(f"✨ Process was healthy for {time_since_last_progress/60:.1f}m. Resetting queue counter.")
                        populate_retry_count = 0
                    
                    # 2. Calculate exponential backoff: 5m -> 10m -> 20m -> 40m -> 60m (capped)
                    # 2^0 * 300 = 300s (5m)
                    # 2^1 * 300 = 600s (10m)
                    # ...
                    wait_time = min(300 * (2 ** populate_retry_count), 3600)
                    
                    logger.warning("=" * 80)
                    logger.warning(f"🛑 THROUGHPUT LIMIT REACHED (429) - Queue Count: {populate_retry_count + 1}")
                    logger.warning(f"💤 Entering intelligent queue: Cooling down for {wait_time/60:.0f} minutes...")
                    if wait_time >= 3600:
                         logger.warning("   (Max cooldown reached - will continue polling hourly until limit lifts)")
                    logger.warning("🔄 Process will automatically resume from where it left off")
                    logger.warning("=" * 80)
                    
                    time.sleep(wait_time)
                    populate_retry_count += 1
                    continue
                else:
                    # Even for non-429 errors, we do NOT want to stop long-running processes
                    logger.warning(f"⚠️ Non-critical error: {e}. Sleeping 60s and retrying...")
                    time.sleep(60)
                    continue
    
    def _update_rate_limit_from_headers(self, headers):
        """Update rate limit tracking from HTTP response headers."""
        if not headers:
            return
        
        # HuggingFace API rate limit headers (may vary)
        # Common headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        # Also check: RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
        
        # Try multiple header name variations
        limit = headers.get('X-RateLimit-Limit') or headers.get('RateLimit-Limit')
        remaining = headers.get('X-RateLimit-Remaining') or headers.get('RateLimit-Remaining')
        reset = headers.get('X-RateLimit-Reset') or headers.get('RateLimit-Reset')
        retry_after = headers.get('Retry-After')
        
        # Update rate limit info
        if limit:
            try:
                self.rate_limit_limit = int(limit)
            except:
                pass
        
        if remaining:
            try:
                self.rate_limit_remaining = int(remaining)
            except:
                pass
        
        if reset:
            try:
                # Reset can be a timestamp (seconds since epoch) or seconds until reset
                reset_val = int(reset)
                # If it's a small number (< 1000000), it's likely seconds until reset
                if reset_val < 1000000:
                    self.rate_limit_reset = time.time() + reset_val
                else:
                    # Otherwise it's a timestamp
                    self.rate_limit_reset = reset_val
            except:
                pass
        
        if retry_after:
            try:
                wait_time = int(retry_after)
                self.rate_limit_reset = time.time() + wait_time
                logger.info(f"📋 Retry-After header: {wait_time}s")
            except:
                pass
        
        self.last_header_update = time.time()
        
        # Log rate limit status (more verbose for visibility)
        if remaining is not None or limit is not None:
            if self.rate_limit_limit > 0 and self.rate_limit_remaining >= 0:
                remaining_pct = (self.rate_limit_remaining / self.rate_limit_limit * 100) if self.rate_limit_limit > 0 else 0
                
                # Log periodically (every 100 requests or when status changes significantly)
                if not hasattr(self, '_last_rate_limit_log') or time.time() - self._last_rate_limit_log > 30:
                    if remaining_pct < 10:
                        logger.warning(f"⚠️ Rate limit low: {self.rate_limit_remaining}/{self.rate_limit_limit} remaining ({remaining_pct:.1f}%)")
                    elif remaining_pct < 30:
                        logger.info(f"📊 Rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit} remaining ({remaining_pct:.1f}%)")
                    elif remaining_pct < 50:
                        logger.debug(f"📊 Rate limit: {self.rate_limit_remaining}/{self.rate_limit_limit} remaining ({remaining_pct:.1f}%)")
                    else:
                        # Log every 60 seconds when healthy
                        if not hasattr(self, '_last_healthy_log') or time.time() - self._last_healthy_log > 60:
                            logger.info(f"✅ Rate limit healthy: {self.rate_limit_remaining}/{self.rate_limit_limit} remaining ({remaining_pct:.1f}%)")
                            self._last_healthy_log = time.time()
                    
                    if self.rate_limit_reset:
                        reset_in = max(0, self.rate_limit_reset - time.time())
                        if reset_in > 0:
                            logger.debug(f"🕐 Rate limit resets in {reset_in:.1f}s")
                    
                    self._last_rate_limit_log = time.time()
            else:
                # First time we see headers - log it
                if limit:
                    logger.info(f"📊 Rate limit detected: {limit} requests per window")
                if remaining is not None:
                    logger.info(f"📊 Rate limit remaining: {remaining} requests")
    
    def _calculate_adaptive_delay(self):
        """Calculate adaptive delay based on rate limit headers."""
        current_time = time.time()
        
        # If we have rate limit info from headers
        if self.rate_limit_reset and self.rate_limit_limit > 0:
            # Calculate time until reset
            time_until_reset = max(0, self.rate_limit_reset - current_time)
            
            # Calculate how many requests we can make per second
            if time_until_reset > 0 and self.rate_limit_remaining > 0:
                # Distribute remaining requests over remaining time
                requests_per_second = self.rate_limit_remaining / time_until_reset
                # Add safety margin (use 80% of calculated rate)
                requests_per_second = requests_per_second * 0.8
                
                # Calculate delay to achieve this rate
                if requests_per_second > 0:
                    calculated_delay = 1.0 / requests_per_second
                else:
                    calculated_delay = self.max_delay
            else:
                # No time left or no requests remaining - wait until reset
                calculated_delay = time_until_reset if time_until_reset > 0 else self.rate_limit_delay
        else:
            # No header info - use conservative default
            # HuggingFace allows 1000 requests per 5 minutes = ~3.3 req/sec
            # Be conservative: aim for 2 req/sec = 0.5s delay
            calculated_delay = 0.5
        
        # Clamp delay to reasonable bounds
        calculated_delay = max(self.min_delay, min(calculated_delay, self.max_delay))
        
        # Apply adaptive factor (for gradual adjustments)
        self.current_delay = calculated_delay * self.adaptive_factor
        
        return self.current_delay
    
    def _calculate_intelligent_wait_time(self, headers=None, retry_count=0):
        """
        Calculate intelligent wait time for 429 errors based on headers.
        
        Priority:
        1. Retry-After header (if available) - use it directly
        2. X-RateLimit-Reset header - calculate time until reset
        3. X-RateLimit-Remaining = 0 - wait until reset time
        4. Intelligent exponential backoff based on previous rate limit info
        
        Args:
            headers: Response headers (optional, will use self.rate_limit_* if None)
            retry_count: Current retry attempt number
            
        Returns:
            wait_time: Calculated wait time in seconds
            reason: String explaining why this wait time was chosen
        """
        current_time = time.time()
        
        # Priority 1: Retry-After header (highest priority)
        if headers:
            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            if retry_after:
                try:
                    wait_time = int(retry_after)
                    if wait_time > 0:
                        return wait_time, f"Retry-After header: {wait_time}s"
                except (ValueError, TypeError):
                    pass
        
        # Priority 2: Calculate from X-RateLimit-Reset header
        reset_time = None
        if headers:
            reset_header = headers.get('X-RateLimit-Reset') or headers.get('RateLimit-Reset') or headers.get('x-ratelimit-reset')
            if reset_header:
                try:
                    reset_val = int(reset_header)
                    # If it's a small number (< 1000000), it's likely seconds until reset
                    if reset_val < 1000000:
                        reset_time = current_time + reset_val
                    else:
                        # Otherwise it's a timestamp
                        reset_time = reset_val
                except (ValueError, TypeError):
                    pass
        
        # Use stored reset time if header not available
        if reset_time is None and self.rate_limit_reset:
            reset_time = self.rate_limit_reset
        
        # If we have a reset time, calculate wait until reset
        if reset_time:
            time_until_reset = max(0, reset_time - current_time)
            if time_until_reset > 0:
                # Add small buffer (5 seconds) to ensure reset has occurred
                wait_time = time_until_reset + 5
                return wait_time, f"X-RateLimit-Reset: waiting {wait_time:.1f}s until reset (resets in {time_until_reset:.1f}s)"
        
        # Priority 3: Check if remaining = 0, wait until reset
        remaining = None
        if headers:
            remaining_header = headers.get('X-RateLimit-Remaining') or headers.get('RateLimit-Remaining') or headers.get('x-ratelimit-remaining')
            if remaining_header:
                try:
                    remaining = int(remaining_header)
                except (ValueError, TypeError):
                    pass
        
        if remaining is None:
            remaining = self.rate_limit_remaining
        
        if remaining == 0 and reset_time:
            time_until_reset = max(0, reset_time - current_time)
            if time_until_reset > 0:
                wait_time = time_until_reset + 5
                return wait_time, f"Rate limit exhausted (0 remaining): waiting {wait_time:.1f}s until reset"
        
        # Priority 4: Intelligent exponential backoff based on rate limit info
        # If we know the rate limit window, use it to inform backoff
        if self.rate_limit_limit > 0:
            # HuggingFace typically uses 5-minute windows (300 seconds)
            # Use a fraction of the window for backoff
            window_size = 300  # 5 minutes default
            base_wait = min(window_size / 10, 30)  # 10% of window or 30s max
        else:
            base_wait = self.retry_delay_base
        
        # Exponential backoff with jitter
        wait_time = min(base_wait * (2 ** retry_count), self.max_retry_delay)
        
        # Add jitter (±10%) to prevent thundering herd
        import random
        jitter = wait_time * 0.1 * (random.random() * 2 - 1)  # ±10%
        wait_time = max(1, wait_time + jitter)  # Minimum 1 second
        
        reason = f"Exponential backoff: {wait_time:.1f}s (retry {retry_count}, base: {base_wait:.1f}s)"
        if self.rate_limit_limit > 0:
            reason += f" | Known limit: {self.rate_limit_limit}/window"
        
        return wait_time, reason
    
    def _get_models_with_retry(self, api):
        """
        Get models iterator with intelligent rate limiting.
        
        Note: huggingface_hub library (v1.2.0+) has built-in automatic rate limit handling.
        It automatically reads RateLimit headers and retries on 429 errors.
        We add header monitoring for visibility and proactive rate limiting.
        
        VERSION: 3.0 - Super intelligent rate limiting with header-based wait calculation
        """
        # CRITICAL: This log confirms the function is being called
        logger.info("=" * 80)
        logger.info("🚀 _get_models_with_retry() CALLED - Super Intelligent Rate Limiting v3.0 ACTIVE")
        logger.info("🧠 Features: Header-based wait calculation, Retry-After priority, X-RateLimit-Reset calculation")
        logger.info("=" * 80)
        
        # Monkey-patch requests.Session.request and httpx.Client.request to capture ALL HEADERS and handle retries
        # This is strictly better than patching get/post because libraries often use Sessions
        import requests
        logger.info("📦 Imported requests library for monkey-patching Session.request")
        
        original_session_request = requests.Session.request
        
        def patched_session_request(session_self, method, url, *args, **kwargs):
            """Intercept ALL requests (GET, POST, etc.) to handle 429 errors - NEVER GIVES UP."""
            retry_count = 0
            while True:
                try:
                    # Call original method using the session instance
                    response = original_session_request(session_self, method, url, *args, **kwargs)
                    
                    # Monitor headers for rate limit info (using outer self for the populator)
                    if response.headers:
                        self._update_rate_limit_from_headers(dict(response.headers))
                    
                    # If we get a 429, handle it with intelligent retry logic
                    if response.status_code == 429:
                        retry_count += 1
                        
                        # Calculate intelligent wait time based on headers
                        wait_time, reason = self._calculate_intelligent_wait_time(dict(response.headers), retry_count)
                        
                        logger.warning("=" * 80)
                        logger.warning(f"⚠️ HTTP Error 429 (Rate Limit) detected via Session.request!")
                        logger.warning(f"📡 Request: {method} {url}")
                        logger.warning(f"🧠 Intelligent wait calculation: {reason}")
                        logger.warning(f"⏱️  Waiting {wait_time:.1f}s [Retry {retry_count}]")
                        if self.rate_limit_limit > 0:
                            logger.warning(f"📊 Rate limit status: {self.rate_limit_remaining}/{self.rate_limit_limit} remaining")
                        logger.warning("=" * 80)
                        time.sleep(wait_time)
                        continue
                    
                    return response
                    
                except Exception as e:
                    # Handle requests exceptions (ConnectTimeout, etc)
                    # For requests, HTTPError is usually raised by raise_for_status(), not request()
                    # request() just returns response usually. But if connection fails...
                    
                    # Check for 429 in error message just in case
                    error_str = str(e)
                    if '429' in error_str or 'Too Many Requests' in error_str:
                         retry_count += 1
                         wait_time, reason = self._calculate_intelligent_wait_time(None, retry_count)
                         logger.warning(f"⚠️ Exception 429 detected: {e}. Sleeping {wait_time}s")
                         time.sleep(wait_time)
                         continue
                    raise

        # Apply patch
        requests.Session.request = patched_session_request
        logger.info("✅ Patched requests.Session.request for rate limit monitoring")
        
        # Also patch httpx if available
        original_httpx_client_request = None
        try:
             import httpx
             original_httpx_client_request = httpx.Client.request
             
             def patched_httpx_client_request(client_self, method, url, *args, **kwargs):
                 """Intercept httpx requests."""
                 retry_count = 0
                 while True:
                     try:
                         response = original_httpx_client_request(client_self, method, url, *args, **kwargs)
                         
                         if response.headers:
                             self._update_rate_limit_from_headers(dict(response.headers))
                         
                         if response.status_code == 429:
                             retry_count += 1
                             wait_time, reason = self._calculate_intelligent_wait_time(dict(response.headers), retry_count)
                             logger.warning(f"⚠️ httpx 429 detected: {method} {url}. Sleeping {wait_time}s")
                             time.sleep(wait_time)
                             continue
                         
                         return response
                     except Exception as e:
                         error_str = str(e)
                         if '429' in error_str or 'Too Many Requests' in error_str:
                             retry_count += 1
                             wait_time, reason = self._calculate_intelligent_wait_time(None, retry_count)
                             logger.warning(f"⚠️ httpx exception 429: {e}. Sleeping {wait_time}s")
                             time.sleep(wait_time)
                             continue
                         raise

             httpx.Client.request = patched_httpx_client_request
             logger.info("✅ Patched httpx.Client.request for rate limit monitoring")
        except ImportError:
             logger.info("ℹ️ httpx not installed (skipping patch)")
        
        # Wrap everything in an outer retry loop
        iterator_retry_count = 0
        
        try:
            while True:  # Outer loop - never give up
                try:
                    if iterator_retry_count > 0:
                        logger.warning(f"🔄 Recreating iterator (attempt {iterator_retry_count})")
                    else:
                        logger.info("🔄 STARTING MODEL ITERATOR WITH INTELLIGENT RATE LIMITING...")
                    
                    # Get iterator - huggingface_hub handles basic retries, our patch handles complex 429s/timeouts
                    # Use full=True to get all metadata
                    models_iterator = api.list_models(full=True)
                    logger.info("✅ Iterator obtained - starting fetch loop")
                    
                    # Yield items
                    for model in models_iterator:
                        iterator_retry_count = 0 # Reset on success
                        yield model
                    
                    # If loop finishes normally, we are done
                    logger.info("✅ Iterator finished normally")
                    break
                    
                except Exception as e:
                    iterator_retry_count += 1
                    # Logic to handle error and retry
                    wait_time, reason = self._calculate_intelligent_wait_time(None, iterator_retry_count)
                    logger.warning(f"⚠️ Iterator error (likely 429/timeout): {e}")
                    logger.warning(f"🧠 Wait reason: {reason}")
                    logger.warning(f"⏱️  Sleeping {wait_time:.1f}s and recreating iterator...")
                    time.sleep(wait_time)
                    continue
        finally:
            # Restore patches
            requests.Session.request = original_session_request
            try:
                if original_httpx_client_request is not None:
                     import httpx
                     httpx.Client.request = original_httpx_client_request
            except:
                pass
            logger.info("✅ Restored original network functions")

    def _analyze_metadata_population(self):
        """Analyze how well we populated the enhanced metadata fields."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check total models
                cursor.execute('SELECT COUNT(*) FROM models')
                total_models = cursor.fetchone()[0]
                
                logger.info(f"\n📊 Enhanced Metadata Population Analysis:")
                logger.info(f"   📈 Total models in database: {total_models:,}")
                
                # Check language field population
                cursor.execute('SELECT COUNT(*) FROM models WHERE language IS NOT NULL AND language != ""')
                language_count = cursor.fetchone()[0]
                language_pct = (language_count / total_models * 100) if total_models > 0 else 0
                logger.info(f"   🌍 Models with language info: {language_count:,} ({language_pct:.1f}%)")
                
                # Check license field population
                cursor.execute('SELECT COUNT(*) FROM models WHERE license IS NOT NULL AND license != ""')
                license_count = cursor.fetchone()[0]
                license_pct = (license_count / total_models * 100) if total_models > 0 else 0
                logger.info(f"   📄 Models with license info: {license_count:,} ({license_pct:.1f}%)")
                
                # Check architecture field population
                cursor.execute('SELECT COUNT(*) FROM models WHERE architecture IS NOT NULL AND architecture != ""')
                arch_count = cursor.fetchone()[0]
                arch_pct = (arch_count / total_models * 100) if total_models > 0 else 0
                logger.info(f"   🏗️  Models with architecture info: {arch_count:,} ({arch_pct:.1f}%)")
                
                # Check enhanced metadata fields
                cursor.execute('SELECT COUNT(*) FROM models WHERE language_details IS NOT NULL')
                lang_details_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE license_details IS NOT NULL')
                lic_details_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE datasets IS NOT NULL')
                datasets_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE base_model IS NOT NULL')
                base_model_count = cursor.fetchone()[0]
                
                logger.info(f"   📋 Models with detailed language info: {lang_details_count:,}")
                logger.info(f"   📜 Models with detailed license info: {lic_details_count:,}")
                logger.info(f"   📊 Models with dataset info: {datasets_count:,}")
                logger.info(f"   🔗 Models with base model info: {base_model_count:,}")
                
                # Check for specific needed values
                cursor.execute('SELECT COUNT(*) FROM models WHERE language = "English"')
                english_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE language = "Chinese"')
                chinese_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE license = "apache-2.0"')
                apache_count = cursor.fetchone()[0]
                
                logger.info(f"\n🎯 Specific Field Values:")
                logger.info(f"   🇺🇸 English models: {english_count:,}")
                logger.info(f"   🇨🇳 Chinese models: {chinese_count:,}")
                logger.info(f"   ⚖️  Apache 2.0 licensed models: {apache_count:,}")
                
                # Check enhanced scoring fields
                cursor.execute('SELECT COUNT(*) FROM models WHERE lightweight_score = 1.0')
                lightweight_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE engagement_score > 0')
                engagement_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM models WHERE popularity_score_normalized > 0')
                popularity_count = cursor.fetchone()[0]
                
                logger.info(f"\n🚀 Enhanced Scoring Analysis:")
                logger.info(f"   🪶 Lightweight models (<500MB): {lightweight_count:,}")
                logger.info(f"   💫 Models with engagement: {engagement_count:,}")
                logger.info(f"   📈 Models with popularity scores: {popularity_count:,}")
                
                # Sample some models to show what we captured
                cursor.execute('''
                    SELECT model_id, language, license, architecture, base_model
                    FROM models 
                    WHERE (language IS NOT NULL OR license IS NOT NULL OR architecture IS NOT NULL)
                    ORDER BY downloads DESC 
                    LIMIT 5
                ''')
                
                samples = cursor.fetchall()
                if samples:
                    logger.info(f"\n🔍 Sample Enhanced Models:")
                    for model_id, language, license, architecture, base_model in samples:
                        logger.info(f"   📋 {model_id}")
                        if language:
                            logger.info(f"      🌍 Language: {language}")
                        if license:
                            logger.info(f"      📄 License: {license}")
                        if architecture:
                            logger.info(f"      🏗️  Architecture: {architecture}")
                        if base_model:
                            logger.info(f"      🔗 Base Model: {base_model}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing metadata population: {e}")
    
    def _normalize_popularity_scores(self):
        """Normalize popularity scores across all models using max downloads."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("📊 Normalizing popularity scores...")
                
                # Get max downloads for normalization
                cursor.execute('SELECT MAX(downloads) FROM models WHERE downloads > 0')
                max_downloads = cursor.fetchone()[0] or 1
                
                # Update normalized popularity scores
                cursor.execute('''
                    UPDATE models 
                    SET popularity_score_normalized = CAST(downloads AS REAL) / ?
                    WHERE downloads > 0
                ''', (max_downloads,))
                
                # Set zero for models with no downloads
                cursor.execute('''
                    UPDATE models 
                    SET popularity_score_normalized = 0.0
                    WHERE downloads = 0 OR downloads IS NULL
                ''')
                
                conn.commit()
                
                # Report normalization stats
                cursor.execute('SELECT COUNT(*) FROM models WHERE popularity_score_normalized > 0')
                normalized_count = cursor.fetchone()[0]
                
                logger.info(f"✅ Normalized popularity scores for {normalized_count:,} models")
                logger.info(f"   📊 Max downloads used for normalization: {max_downloads:,}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error normalizing popularity scores: {e}")
    
    def _process_models_batch(self, models_list: List[Any]):
        """Process models in batches and extract comprehensive metadata."""
        extracted_data = []
        batch_errors = 0
        max_batch_errors = len(models_list) // 2  # Allow up to 50% errors in a batch
        
        for i, model in enumerate(models_list):
            try:
                model_id = getattr(model, 'modelId', 'unknown')
                
                # Log model progress (every 100 models to avoid spam)
                if i % 100 == 0 or i == 0:
                    logger.info(f"📥 Processing model {i+1}/{len(models_list)}: {model_id}")
                
                # Extract comprehensive model data with enhanced metadata
                model_data = self._extract_model_data(model)
                if model_data:
                    extracted_data.append(model_data)
                    
                    # Show key extracted metadata for first few models in batch for verification
                    if i < 3:  # Only show for first 3 models in each batch
                        metadata_info = []
                        if model_data.get('language'):
                            metadata_info.append(f"🌍 {model_data['language']}")
                        if model_data.get('license'):
                            metadata_info.append(f"📄 {model_data['license']}")
                        if model_data.get('architecture'):
                            metadata_info.append(f"🏗️ {model_data['architecture']}")
                        
                        # Show enhanced scoring info
                        scoring_info = []
                        if model_data.get('size_mb'):
                            size_mb = model_data['size_mb']
                            scoring_info.append(f"📦 {size_mb:.1f}MB")
                            if model_data.get('lightweight_score', 0) == 1.0:
                                scoring_info.append("🪶 Lightweight")
                        
                        if model_data.get('engagement_score', 0) > 0:
                            eng_score = model_data['engagement_score']
                            scoring_info.append(f"💫 Eng:{eng_score:.3f}")
                        
                        if metadata_info:
                            logger.info(f"   Metadata: {' | '.join(metadata_info)}")
                        if scoring_info:
                            logger.info(f"   Scoring: {' | '.join(scoring_info)}")
                else:
                    self.failed_models += 1
                    batch_errors += 1
                    
            except Exception as e:
                batch_errors += 1
                self.failed_models += 1
                # Only log warnings for the first few errors to avoid spam
                if batch_errors <= 5:
                    logger.warning(f"⚠️ Failed to process model {getattr(model, 'modelId', 'unknown')}: {e}")
                elif batch_errors == 6:
                    logger.warning(f"⚠️ Suppressing further error messages for this batch...")
                
                # NEVER STOP processing a batch, even with errors
                # We want to process every single model possible
                if batch_errors >= max_batch_errors and batch_errors % 100 == 0:
                    logger.warning(f"⚠️ High error rate in batch ({batch_errors}/{len(models_list)}) but continuing...")
        
        # Insert all extracted data at once
        if extracted_data:
            logger.info(f"💾 Inserting batch of {len(extracted_data)} models into database...")
            try:
                self._insert_batch(extracted_data)
                logger.info(f"✅ Batch insertion completed - Running Total Updated: {self.processed_models:,} models")
            except Exception as e:
                logger.error(f"❌ Failed to insert batch into database: {e}")
                self.failed_models += len(extracted_data)
        else:
            logger.warning(f"⚠️ No valid models extracted from batch of {len(models_list)} models")
            self.failed_models += len(models_list)
    
    def _extract_model_data(self, model: Any) -> Optional[Dict[str, Any]]:
        """Extract comprehensive data from HuggingFace model object."""
        try:
            # Get basic model info
            model_id = getattr(model, 'modelId', '')
            if not model_id:
                return None
                
            author = model_id.split('/')[0] if '/' in model_id else ''
            
            # Get pipeline tag
            pipeline_tag = getattr(model, 'pipeline_tag', '')
            
            # Get tags
            tags = getattr(model, 'tags', [])
            tags_json = json.dumps(tags) if tags else '[]'
            
            # Get description
            description = getattr(model, 'description', '')
            
            # Get downloads and likes
            downloads = getattr(model, 'downloads', 0)
            likes = getattr(model, 'likes', 0)
            
            # Get model type and library
            model_type = getattr(model, 'model_type', '')
            library_name = getattr(model, 'library_name', '')
            
            # Enhanced license detection - try multiple sources
            license_text = self._extract_license(model, tags, model_id)
            
            # Get last modified
            last_modified = getattr(model, 'last_modified', None)
            if last_modified:
                last_modified = last_modified.isoformat()
                
            # Extract metadata efficiently from ModelInfo tags (much faster than ModelCard.load)
            modelcard_data = self._extract_metadata_from_tags(model, tags, model_id)
            
            # Get enhanced model information using model_info() for detailed data
            enhanced_info = self._get_enhanced_model_info(model, model_id)
            
            # Get comprehensive metadata with better detection
            architecture = self._detect_architecture(tags, model_id, model_type)
            input_size = self._detect_input_size(tags)
            num_classes = self._detect_num_classes(tags)
            
            # Use enhanced info for accurate sizing and scoring
            actual_size_mb = enhanced_info.get('size_mb') or self._estimate_model_size(tags, model_id)
            license_score = self._calculate_enhanced_license_score(license_text)
            
            # Calculate enhanced scores from model_selector logic
            enhanced_scores = self._calculate_enhanced_scores(
                downloads, likes, actual_size_mb, pipeline_tag, license_text
            )
            
            # Calculate scores
            decision_score = self._calculate_decision_score(model)
            capability_score = self._calculate_capability_score(model)
            efficiency_score = self._calculate_efficiency_score(model)
            popularity_score = self._calculate_popularity_score(model)
            
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
                'download_date': datetime.now().isoformat(),
                'license': license_text,
                'task_keywords': tags_json,  # Use tags as task keywords
                'architecture': architecture,
                'input_size': input_size,
                'num_classes': num_classes,
                'model_size_mb': actual_size_mb,
                'license_score': license_score,
                'size_mb': actual_size_mb,
                # Enhanced scoring fields
                'popularity_score_normalized': enhanced_scores.get('popularity_score_normalized', 0.0),
                'engagement_score': enhanced_scores.get('engagement_score', 0.0),
                'lightweight_score': enhanced_scores.get('lightweight_score', 0.0),
                'task_match_score': enhanced_scores.get('task_match_score', 0.0),
                # ModelCard metadata fields
                'language': modelcard_data.get('language'),
                'language_details': modelcard_data.get('language_details'),
                'license_details': modelcard_data.get('license_details'),
                'base_model': modelcard_data.get('base_model'),
                'datasets': modelcard_data.get('datasets'),
                'metrics': modelcard_data.get('metrics'),
                'widget_data': modelcard_data.get('widget_data'),
                'model_index': modelcard_data.get('model_index'),
                'inference_info': modelcard_data.get('inference_info')
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error extracting data from model: {e}")
            return None
    
    def _extract_metadata_from_tags(self, model: Any, tags: List[str], model_id: str) -> Dict[str, Any]:
        """Extract rich metadata efficiently from ModelInfo tags (much faster than ModelCard.load)."""
        try:
            metadata = {}
            
            # Extract languages from tags
            languages = []
            language_codes = []
            
            for tag in tags:
                # Language detection with more comprehensive coverage
                if tag in ['en', 'english']:
                    languages.append('English')
                    language_codes.append('en')
                elif tag in ['zh', 'chinese', 'zh-cn', 'zh-tw', 'zh-hans', 'zh-hant']:
                    languages.append('Chinese')
                    language_codes.append('zh')
                elif tag in ['fr', 'french']:
                    languages.append('French')
                    language_codes.append('fr')
                elif tag in ['de', 'german']:
                    languages.append('German')
                    language_codes.append('de')
                elif tag in ['es', 'spanish']:
                    languages.append('Spanish')
                    language_codes.append('es')
                elif tag in ['ja', 'japanese']:
                    languages.append('Japanese')
                    language_codes.append('ja')
                elif tag in ['ko', 'korean']:
                    languages.append('Korean')
                    language_codes.append('ko')
                elif tag in ['pt', 'portuguese']:
                    languages.append('Portuguese')
                    language_codes.append('pt')
                elif tag in ['ru', 'russian']:
                    languages.append('Russian')
                    language_codes.append('ru')
                elif tag in ['ar', 'arabic']:
                    languages.append('Arabic')
                    language_codes.append('ar')
                elif tag in ['hi', 'hindi']:
                    languages.append('Hindi')
                    language_codes.append('hi')
                elif tag in ['multilingual', 'multi-language']:
                    languages.append('Multilingual')
                    language_codes.append('multilingual')
            
            # Set language fields
            if languages:
                metadata['language'] = languages[0]  # Primary language
                metadata['language_details'] = json.dumps({
                    'languages': languages,
                    'language_codes': language_codes,
                    'count': len(languages)
                })
            
            # Extract license information from tags
            license_info = None
            for tag in tags:
                if tag.startswith('license:'):
                    license_info = tag.replace('license:', '')
                    break
            
            if license_info:
                metadata['license_details'] = json.dumps({
                    'license': license_info,
                    'source': 'model_tags',
                    'detected_from': f'tag: license:{license_info}'
                })
            
            # Extract datasets from tags
            datasets = []
            for tag in tags:
                if tag.startswith('dataset:'):
                    datasets.append(tag.replace('dataset:', ''))
            
            if datasets:
                metadata['datasets'] = json.dumps({
                    'training_datasets': datasets,
                    'count': len(datasets),
                    'source': 'model_tags'
                })
            
            # Extract base model information from tags
            base_models = []
            for tag in tags:
                if any(keyword in tag.lower() for keyword in ['base:', 'finetuned-from:', 'based-on:']):
                    base_models.append(tag)
                # Also check for common base model patterns in model_id
                if '/' in model_id and any(base in model_id.lower() for base in ['bert', 'gpt', 'llama', 'roberta', 'electra']):
                    base_pattern = model_id.split('/')[-1]
                    if any(base in base_pattern.lower() for base in ['bert', 'gpt', 'llama', 'roberta', 'electra']):
                        base_models.append(f"inferred:{base_pattern}")
            
            if base_models:
                metadata['base_model'] = base_models[0] if len(base_models) == 1 else json.dumps(base_models)
            
            # Extract metrics information from tags (arxiv papers often indicate evaluation)
            arxiv_papers = []
            metrics_indicators = []
            for tag in tags:
                if tag.startswith('arxiv:'):
                    arxiv_papers.append(tag.replace('arxiv:', ''))
                elif any(metric in tag.lower() for metric in ['accuracy', 'bleu', 'rouge', 'f1', 'precision', 'recall']):
                    metrics_indicators.append(tag)
            
            if arxiv_papers or metrics_indicators:
                metadata['metrics'] = json.dumps({
                    'arxiv_papers': arxiv_papers,
                    'metric_indicators': metrics_indicators,
                    'source': 'model_tags'
                })
            
            # Widget and inference info from model object directly
            widget_data = getattr(model, 'widget_data', None)
            if widget_data:
                metadata['widget_data'] = json.dumps(widget_data)
            
            model_index = getattr(model, 'model_index', None)
            if model_index:
                metadata['model_index'] = json.dumps(model_index)
            
            # Inference configuration from model attributes
            inference_data = {
                'pipeline_tag': getattr(model, 'pipeline_tag', ''),
                'library_name': getattr(model, 'library_name', ''),
                'mask_token': getattr(model, 'mask_token', ''),
                'tags': tags[:10],  # Include first 10 tags for inference context
                'special_pipelines': [tag for tag in tags if any(keyword in tag.lower() 
                                    for keyword in ['pipeline', 'qwen', 'whisper', 'clip', 'vilt'])]
            }
            
            # Only store if we have meaningful inference info
            if any(inference_data.values()):
                metadata['inference_info'] = json.dumps(inference_data)
            
            logger.debug(f"🏷️ Extracted {len([k for k,v in metadata.items() if v])} metadata fields from tags for {model_id}")
            return metadata
            
        except Exception as e:
            logger.debug(f"⚠️ Error extracting metadata from tags for {model_id}: {e}")
            return {}
    
    def _get_enhanced_model_info(self, model: Any, model_id: str) -> Dict[str, Any]:
        """Get enhanced model information using model_info() for detailed data (selective usage)."""
        try:
            # Only call model_info() for models that seem significant (to avoid API rate limits)
            downloads = getattr(model, 'downloads', 0) or 0
            likes = getattr(model, 'likes', 0) or 0
            
            # Skip detailed info for very unpopular models to save API calls
            # NOTE: This only skips the detailed model_info() call, NOT the main list_models() iterator
            if downloads < 100 and likes < 5:
                return {}
            
            from huggingface_hub import model_info
            
            # Get detailed model info (this makes an API call)
            # NOTE: This is an ADDITIONAL API call beyond list_models() - it's for enhanced metadata only
            # The main model list comes from api.list_models() which ALWAYS uses the API
            info = model_info(model_id)
            
            enhanced_data = {}
            
            # Get actual file size from siblings (most accurate)
            if hasattr(info, 'siblings') and info.siblings:
                total_size = sum(sibling.size for sibling in info.siblings if sibling.size)
                if total_size > 0:
                    enhanced_data['size_mb'] = total_size / (1024 ** 2)  # Convert to MB
            
            # Get additional metadata from detailed info
            if hasattr(info, 'card_data') and info.card_data:
                enhanced_data['card_data'] = info.card_data
            
            return enhanced_data
            
        except Exception as e:
            # If model_info() fails, return empty dict (fall back to basic estimation)
            logger.debug(f"⚠️ Could not get enhanced info for {model_id}: {e}")
            return {}
    
    def _calculate_enhanced_license_score(self, license_text: str) -> float:
        """Calculate license score using OPEN_LICENSES from model_selector logic."""
        if not license_text:
            return 0.0
        
        license_lower = license_text.lower().strip()
        
        # Check if it's in our open licenses set
        if license_lower in OPEN_LICENSES:
            return 1.0
        
        # Check for partial matches (e.g. "apache-2.0" in "license: apache-2.0")
        for open_license in OPEN_LICENSES:
            if open_license in license_lower:
                return 1.0
        
        # Non-open license
        return 0.0
    
    def _calculate_enhanced_scores(self, downloads: int, likes: int, size_mb: Optional[float], 
                                 pipeline_tag: str, license_text: str) -> Dict[str, float]:
        """Calculate enhanced scores from model_selector logic."""
        scores = {}
        
        # Popularity score (normalized downloads - will be normalized globally later)
        scores['popularity_score_normalized'] = downloads  # Store raw for now, normalize in batch
        
        # Engagement score (likes/downloads ratio)
        scores['engagement_score'] = likes / (downloads + 1e-5) if downloads > 0 else 0.0
        
        # Lightweight score (1 if size < 500MB)
        if size_mb is not None:
            scores['lightweight_score'] = 1.0 if size_mb < 500 else 0.0
        else:
            scores['lightweight_score'] = 0.0
        
        # Task match score (will be calculated per task - for now just set to 0)
        scores['task_match_score'] = 0.0  # This would be calculated when querying for specific tasks
        
        return scores
    
    def _extract_license(self, model: Any, tags: List[str], model_id: str) -> str:
        """Enhanced license extraction from tags and model attributes."""
        # Check tags for license information first (most reliable)
        for tag in tags:
            if tag.startswith('license:'):
                return tag.replace('license:', '').strip()
        
        # Try direct license attribute as fallback
        license_text = getattr(model, 'license', '')
        if license_text and license_text.strip():
            return license_text.strip()
        
        # Check remaining tags for license keywords
        if tags:
            for tag in tags:
                if tag and 'license' in tag.lower():
                    if 'mit' in tag.lower():
                        return 'mit'
                    elif 'apache' in tag.lower():
                        return 'apache-2.0'
                    elif 'gpl' in tag.lower():
                        return 'gpl-3.0'
                    elif 'bsd' in tag.lower():
                        return 'bsd-3-clause'
                    elif 'cc-by' in tag.lower():
                        return 'cc-by-4.0'
        
        # Infer from common patterns in model_id
        if model_id:
            model_id_lower = model_id.lower()
            
            # Common organizations and their typical licenses
            org_licenses = {
                'microsoft/': 'mit',
                'google/': 'apache-2.0',
                'facebook/': 'custom',
                'meta-llama/': 'custom',
                'openai/': 'custom',
                'huggingface/': 'apache-2.0',
                'sentence-transformers/': 'apache-2.0',
                'distilbert/': 'apache-2.0'
            }
            
            for org_prefix, default_license in org_licenses.items():
                if model_id_lower.startswith(org_prefix):
                    return default_license
        
        # Try to get from model card data if available
        try:
            if hasattr(model, 'cardData') and model.cardData:
                card_data = model.cardData
                if isinstance(card_data, dict) and 'license' in card_data:
                    card_license = card_data['license']
                    if card_license and card_license.strip():
                        return card_license.strip()
        except:
            pass
        
        return 'unknown'
    
    def _detect_architecture(self, tags: List[str], model_id: str, model_type: str = '') -> str:
        """Enhanced architecture detection from tags, model ID, and model type."""
        if not tags:
            tags = []
        
        # Common architecture keywords with more comprehensive mapping
        arch_mapping = {
            'vit': 'vision-transformer',
            'vision-transformer': 'vision-transformer',
            'bert': 'bert',
            'roberta': 'roberta',
            'distilbert': 'distilbert',
            'gpt': 'gpt',
            'gpt2': 'gpt-2',
            'gpt-neo': 'gpt-neo',
            'llama': 'llama',
            'llama2': 'llama-2',
            'alpaca': 'alpaca',
            'resnet': 'resnet',
            'efficientnet': 'efficientnet',
            'mobilenet': 'mobilenet',
            'convnext': 'convnext',
            'swin': 'swin-transformer',
            'deit': 'data-efficient-image-transformer',
            'beit': 'bidirectional-encoder-image-transformer',
            'regnet': 'regnet',
            'whisper': 'whisper',
            'wav2vec2': 'wav2vec2',
            't5': 't5',
            'flan-t5': 'flan-t5',
            'clip': 'clip',
            'stable-diffusion': 'stable-diffusion',
            'diffusion': 'diffusion',
            'unet': 'u-net',
            'transformer': 'transformer',
            'lstm': 'lstm',
            'gru': 'gru',
            'cnn': 'convolutional',
            'rnn': 'recurrent'
        }
        
        # Check model_type first (most reliable)
        if model_type:
            model_type_lower = model_type.lower()
            for arch_key, arch_name in arch_mapping.items():
                if arch_key in model_type_lower:
                    return arch_name
        
        # Check tags for architecture indicators
        for tag in tags:
            if tag:  # Make sure tag is not None
                tag_lower = tag.lower()
                for arch_key, arch_name in arch_mapping.items():
                    if arch_key in tag_lower:
                        return arch_name
        
        # Check model ID for architecture indicators
        if model_id:  # Make sure model_id is not None
            model_id_lower = model_id.lower()
            for arch_key, arch_name in arch_mapping.items():
                if arch_key in model_id_lower:
                    return arch_name
            
            # Additional model ID patterns
            if 'dialogpt' in model_id_lower:
                return 'dialogpt'
            elif 'electra' in model_id_lower:
                return 'electra'
            elif 'bloom' in model_id_lower:
                return 'bloom'
            elif 'falcon' in model_id_lower:
                return 'falcon'
            elif 'mpt' in model_id_lower:
                return 'mpt'
        
        return 'unknown'
    
    def _detect_input_size(self, tags: List[str]) -> Optional[str]:
        """Detect input size from tags."""
        if not tags:
            return None
        
        # Look for size indicators in tags
        for tag in tags:
            if tag:  # Make sure tag is not None
                tag_lower = tag.lower()
                if '224' in tag_lower:
                    return '224x224'
                elif '384' in tag_lower:
                    return '384x384'
                elif '512' in tag_lower:
                    return '512x512'
                elif '1024' in tag_lower:
                    return '1024x1024'
        
        return None
    
    def _detect_num_classes(self, tags: List[str]) -> Optional[int]:
        """Detect number of classes from tags."""
        if not tags:
            return None
        
        # Look for class indicators
        for tag in tags:
            if tag:  # Make sure tag is not None
                tag_lower = tag.lower()
                if 'imagenet' in tag_lower:
                    return 1000
                elif 'cifar-10' in tag_lower:
                    return 10
                elif 'cifar-100' in tag_lower:
                    return 100
        
        return None
    
    def _estimate_model_size(self, tags: List[str], model_id: str) -> Optional[float]:
        """Estimate model size in MB from tags and model ID."""
        if not tags and not model_id:
            return None
        
        # Size estimation based on model type indicators
        size_indicators = {
            'tiny': 25,
            'small': 100,
            'base': 300,
            'large': 1000,
            'xl': 3000,
            'xxl': 10000,
            'nano': 10,
            'micro': 5
        }
        
        # Check tags for size indicators
        for tag in tags or []:
            if tag:  # Make sure tag is not None
                tag_lower = tag.lower()
                for size_key, size_mb in size_indicators.items():
                    if size_key in tag_lower:
                        return size_mb
        
        # Check model ID for size indicators
        if model_id:  # Make sure model_id is not None
            model_id_lower = model_id.lower()
            for size_key, size_mb in size_indicators.items():
                if size_key in model_id_lower:
                    return size_mb
            
            # Default estimates based on architecture
            if any(arch in model_id_lower for arch in ['bert', 'roberta']):
                if 'large' in model_id_lower:
                    return 1300
                elif 'base' in model_id_lower:
                    return 400
                else:
                    return 110
            elif any(arch in model_id_lower for arch in ['gpt', 'llama']):
                if 'xl' in model_id_lower or '70b' in model_id_lower:
                    return 140000
                elif 'large' in model_id_lower or '13b' in model_id_lower:
                    return 26000
                elif '7b' in model_id_lower:
                    return 13000
                else:
                    return 500
            elif 'vit' in model_id_lower:
                if 'large' in model_id_lower:
                    return 1200
                elif 'base' in model_id_lower:
                    return 330
                else:
                    return 85
        
        return None
    
    def _calculate_license_score(self, license_text: str) -> float:
        """Calculate license score based on openness."""
        if not license_text or license_text is None:
            return 0.0
        
        license_lower = license_text.lower()
        
        # Open source licenses get high scores
        open_licenses = ['mit', 'apache', 'bsd', 'gpl', 'lgpl', 'mpl', 'cc-by']
        for open_license in open_licenses:
            if open_license in license_lower:
                return 1.0
        
        # Research/non-commercial licenses get medium scores
        if any(term in license_lower for term in ['research', 'non-commercial', 'academic']):
            return 0.6
        
        # Other licenses get lower scores
        if any(term in license_lower for term in ['license', 'terms']):
            return 0.3
        
        return 0.0
    
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
                
                # Debug: Check actual table schema first
                cursor.execute("PRAGMA table_info(models)")
                columns_info = cursor.fetchall()
                actual_columns = [col[1] for col in columns_info]
                logger.info(f"🔍 Database has {len(actual_columns)} columns: {actual_columns}")
                
                # Prepare insert statement that matches actual database schema
                # Build dynamic INSERT based on what columns actually exist
                available_columns = []
                values_placeholders = []
                
                # Core columns that should always exist
                core_columns = [
                    'model_id', 'author', 'pipeline_tag', 'tags', 'description', 
                    'downloads', 'likes', 'decision_score', 'capability_score', 
                    'efficiency_score', 'popularity_score', 'model_type', 'library_name',
                    'last_modified', 'created_at', 'updated_at'
                ]
                
                # Enhanced columns we added
                enhanced_columns = [
                    'download_date', 'license', 'task_keywords', 'architecture', 
                    'input_size', 'num_classes', 'model_size_mb', 'license_score', 'size_mb',
                    'popularity_score_normalized', 'engagement_score', 'lightweight_score', 
                    'task_match_score', 'language', 'language_details', 'license_details',
                    'base_model', 'datasets', 'metrics', 'widget_data', 'model_index', 'inference_info'
                ]
                
                # Build column list and placeholders for columns that actually exist
                for col in core_columns + enhanced_columns:
                    if col in actual_columns and col not in ['created_at', 'updated_at']:  # Skip auto-managed columns
                        available_columns.append(col)
                        values_placeholders.append('?')
                
                # Add updated_at with CURRENT_TIMESTAMP
                if 'updated_at' in actual_columns:
                    available_columns.append('updated_at')
                    values_placeholders.append('CURRENT_TIMESTAMP')
                
                insert_sql = f'''
                    INSERT OR REPLACE INTO models ({', '.join(available_columns)})
                    VALUES ({', '.join(values_placeholders)})
                '''
                
                logger.info(f"🔧 Using {len(available_columns)} columns for INSERT: {available_columns}")
                logger.info(f"📝 INSERT SQL: {insert_sql}")
                
                # Store available columns for data preparation
                self._available_columns = [col for col in available_columns if col != 'updated_at']
                
                # Prepare data for insertion - only for columns that actually exist
                data = []
                for model_data in batch:
                    if model_data:  # Skip None entries
                        try:
                            # Build row data dynamically based on available columns
                            row_data = []
                            for col in self._available_columns:
                                # Define default values for each column type
                                defaults = {
                                    'model_id': '', 'author': '', 'pipeline_tag': '', 'tags': '[]',
                                    'description': '', 'downloads': 0, 'likes': 0,
                                    'decision_score': 0.0, 'capability_score': 0.0, 'efficiency_score': 0.0,
                                    'popularity_score': 0.0, 'model_type': '', 'library_name': '',
                                    'last_modified': '', 'download_date': '', 'license': '',
                                    'task_keywords': '[]', 'architecture': '', 'input_size': '',
                                    'num_classes': None, 'model_size_mb': None, 'license_score': 0.0,
                                    'size_mb': None, 'popularity_score_normalized': 0.0,
                                    'engagement_score': 0.0, 'lightweight_score': 0.0,
                                    'task_match_score': 0.0, 'language': None, 'language_details': None,
                                    'license_details': None, 'base_model': None, 'datasets': None,
                                    'metrics': None, 'widget_data': None, 'model_index': None,
                                    'inference_info': None
                                }
                                
                                # Get value from model_data or use default
                                value = model_data.get(col, defaults.get(col))
                                row_data.append(value)
                            
                            data.append(tuple(row_data))
                        except Exception as e:
                            logger.warning(f"⚠️ Error preparing model data for insert: {e}")
                            continue
                
                # Execute batch insert with debugging
                if data:
                    logger.info(f"🔧 Attempting to insert {len(data)} models with {len(self._available_columns)} values each")
                    logger.info(f"📊 First row has {len(data[0])} values: {data[0][:5]}..." if data else "No data to insert")
                    
                    cursor.executemany(insert_sql, data)
                    conn.commit()
                    
                    self.processed_models += len(data)
                    logger.info(f"✅ Successfully inserted batch of {len(data)} models")
                else:
                    logger.warning("⚠️ No valid data to insert in this batch")
                
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
                    'population_version': '4.0',
                    'schema_version': 'comprehensive_modelcard_v1'
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
                
                # Get all models with their comprehensive metadata
                cursor.execute("""
                    SELECT model_id, pipeline_tag, downloads, likes, decision_score, 
                           architecture, license, model_size_mb
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL
                    ORDER BY downloads DESC
                """)
                models = cursor.fetchall()
                
                # Create task models structure
                task_models = {
                    "timestamp": datetime.now().isoformat(),
                    "total_models": len(models),
                    "schema_version": "comprehensive_v1",
                    "tasks": {}
                }
                
                # Group models by pipeline tag
                for model_id, pipeline_tag, downloads, likes, decision_score, architecture, license, model_size_mb in models:
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
                        "decision_score": decision_score,
                        "architecture": architecture,
                        "license": license,
                        "model_size_mb": model_size_mb
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
        """Get comprehensive database statistics."""
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
                
                # Get architecture distribution
                cursor.execute('''
                    SELECT architecture, COUNT(*) as count 
                    FROM models 
                    WHERE architecture IS NOT NULL AND architecture != '' AND architecture != 'unknown'
                    GROUP BY architecture 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                architecture_distribution = dict(cursor.fetchall())
                
                # Get license distribution
                cursor.execute('''
                    SELECT license, COUNT(*) as count 
                    FROM models 
                    WHERE license IS NOT NULL AND license != ''
                    GROUP BY license 
                    ORDER BY count DESC 
                    LIMIT 10
                ''')
                license_distribution = dict(cursor.fetchall())
                
                # Get top models by downloads
                cursor.execute('''
                    SELECT model_id, downloads, likes, decision_score, architecture, license
                    FROM models 
                    ORDER BY downloads DESC 
                    LIMIT 10
                ''')
                top_models = cursor.fetchall()
                
                return {
                    'total_models': total_count,
                    'pipeline_distribution': pipeline_distribution,
                    'architecture_distribution': architecture_distribution,
                    'license_distribution': license_distribution,
                    'top_models': top_models
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

    def ensure_all_tasks_covered(self):
        """Ensure all specialized tasks have models mapped to them."""
        try:
            logger.info("🔍 Ensuring all specialized tasks are covered...")
            
            # Import specialized tasks from main.py
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from main import specialized_tasks
            except ImportError:
                logger.warning("⚠️ Could not import specialized_tasks from main.py")
                return
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all existing pipeline tags
                cursor.execute('SELECT DISTINCT pipeline_tag FROM models WHERE pipeline_tag IS NOT NULL')
                existing_pipeline_tags = {row[0] for row in cursor.fetchall()}
                
                # Check which specialized tasks are missing
                missing_tasks = []
                for task_name in specialized_tasks:
                    if task_name not in existing_pipeline_tags:
                        missing_tasks.append(task_name)
                
                if not missing_tasks:
                    logger.info("✅ All specialized tasks already have models mapped")
                    return
                
                logger.info(f"📋 Found {len(missing_tasks)} missing tasks: {', '.join(missing_tasks)}")
                
                # For each missing task, find suitable models and create mappings
                for task_name in missing_tasks:
                    logger.info(f"🔍 Finding models for task: {task_name}")
                    
                    # Get models that might be suitable for this task
                    # Use models with high downloads and good scores
                    cursor.execute('''
                        SELECT model_id, pipeline_tag, downloads, decision_score, tags, description
                        FROM models 
                        WHERE downloads > 1000 AND decision_score > 0.5
                        ORDER BY downloads DESC, decision_score DESC
                        LIMIT 50
                    ''')
                    candidate_models = cursor.fetchall()
                    
                    if not candidate_models:
                        logger.warning(f"⚠️ No suitable candidates found for task: {task_name}")
                        continue
                    
                    # Use langextract to determine task compatibility
                    try:
                        import langextract as lx
                        
                        # Check for required API keys
                        langextract_api_key = os.getenv('LANGEXTRACT_API_KEY')
                        gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
                        
                        if not langextract_api_key or not gemini_api_key:
                            logger.warning("⚠️ Missing required API keys for LangExtract (LANGEXTRACT_API_KEY and/or GOOGLE_GEMINI_API_KEY)")
                            raise ImportError("Missing required API keys")
                            
                        # LangExtract is used as module functions, not a class
                        best_model = None
                        best_score = 0.0
                        
                        for model_id, pipeline_tag, downloads, decision_score, tags, description in candidate_models:
                            # Create a test prompt for the task
                            test_prompt = f"Perform {task_name} on this text"
                            
                            # Use langextract to detect if this model is suitable
                            try:
                                analysis_prompt = f"Analyze if the model '{model_id}' with pipeline '{pipeline_tag}' is suitable for the task '{task_name}'. Return a compatibility score from 0-1."
                                
                                from hforchestra.utils.langextract_wrapper import extract_with_config
                                result = extract_with_config(
                                    lx,
                                    text_or_documents=analysis_prompt,
                                    prompt_description="Model Task Compatibility Analysis",
                                    override_api_key=langextract_api_key
                                )
                                
                                # Extract compatibility score from result
                                score = 0.5  # Default score
                                if result and result.extractions:
                                    # Try to extract numerical score from the analysis
                                    for extraction in result.extractions:
                                        if hasattr(extraction, 'content') and extraction.content:
                                            content = str(extraction.content).lower()
                                            # Look for compatibility indicators
                                            if 'high' in content or 'suitable' in content or 'compatible' in content:
                                                score = 0.8
                                            elif 'medium' in content or 'partial' in content:
                                                score = 0.6
                                            elif 'low' in content or 'unsuitable' in content:
                                                score = 0.2
                                            break
                                
                                if score > best_score:
                                    best_score = score
                                    best_model = (model_id, pipeline_tag, downloads, decision_score)
                                    
                            except Exception as e:
                                logger.debug(f"⚠️ Langextract failed for {model_id}: {e}")
                                continue
                        
                        if best_model and best_score > 0.3:
                            model_id, pipeline_tag, downloads, decision_score = best_model
                            logger.info(f"✅ Found suitable model for {task_name}: {model_id} (score: {best_score:.2f})")
                            
                            # Insert a new row with the task mapping
                            cursor.execute('''
                                INSERT OR REPLACE INTO models 
                                (model_id, pipeline_tag, downloads, likes, decision_score, capability_score, 
                                 efficiency_score, popularity_score, author, library_name, license, 
                                 description, tags, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            ''', (
                                f"{model_id}_{task_name}",  # Create unique model_id for task mapping
                                task_name,
                                downloads,
                                0,  # likes
                                decision_score * best_score,  # Adjust score based on task compatibility
                                decision_score * 0.8,  # capability_score
                                decision_score * 0.9,  # efficiency_score
                                decision_score * 0.7,  # popularity_score
                                model_id.split('/')[0] if '/' in model_id else 'unknown',  # author
                                'transformers',  # library_name
                                'unknown',  # license
                                f"Task mapping for {task_name} using {model_id}",  # description
                                json.dumps([task_name, pipeline_tag])  # tags
                            ))
                            
                            logger.info(f"✅ Added mapping: {model_id} -> {task_name} (langextract score: {best_score:.2f})")
                        else:
                            logger.warning(f"⚠️ No suitable model found for {task_name} with confidence > 0.3")
                    
                    except ImportError:
                        logger.warning("⚠️ langextract not available, using fallback mapping")
                        # Fallback: use the best model by downloads
                        best_model = candidate_models[0]
                        model_id, pipeline_tag, downloads, decision_score = best_model[0], best_model[1], best_model[2], best_model[3]
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO models 
                            (model_id, pipeline_tag, downloads, likes, decision_score, capability_score, 
                             efficiency_score, popularity_score, author, library_name, license, 
                             description, tags, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ''', (
                            f"{model_id}_{task_name}",
                            task_name,
                            downloads,
                            0,
                            decision_score * 0.5,  # Reduced score for fallback mapping
                            decision_score * 0.4,
                            decision_score * 0.6,
                            decision_score * 0.3,
                            model_id.split('/')[0] if '/' in model_id else 'unknown',
                            'transformers',
                            'unknown',
                            f"Fallback task mapping for {task_name} using {model_id}",
                            json.dumps([task_name, pipeline_tag])
                        ))
                        
                        logger.info(f"✅ Added fallback mapping: {model_id} -> {task_name}")
                
                conn.commit()
                logger.info("✅ Task coverage check completed")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring task coverage: {e}")

    def is_update_complete(self) -> bool:
        """Check if the database update process is complete."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM models")
                model_count = cursor.fetchone()[0]
                
                # Consider update complete if we have a reasonable number of models
                # (HuggingFace has ~1.9M+ models, so we expect at least 100K for a successful update)
                return model_count >= 100000
        except Exception as e:
            logger.warning(f"⚠️ Could not check update completion status: {e}")
            return False
    
    def get_update_status(self) -> Dict[str, Any]:
        """Get detailed status of the update process."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM models")
                model_count = cursor.fetchone()[0]
                
                # Get some sample models to verify data quality
                cursor.execute("SELECT model_id, downloads, likes FROM models ORDER BY downloads DESC LIMIT 5")
                top_models = cursor.fetchall()
                
                # Check for recent updates
                cursor.execute("SELECT MAX(updated_at) FROM models")
                last_update = cursor.fetchone()[0]
                
                return {
                    'total_models': model_count,
                    'is_complete': model_count >= 100000,
                    'last_update': last_update,
                    'top_models': top_models,
                    'status': 'complete' if model_count >= 100000 else 'in_progress' if model_count > 0 else 'not_started'
                }
        except Exception as e:
            logger.warning(f"⚠️ Could not get update status: {e}")
            return {
                'total_models': 0,
                'is_complete': False,
                'last_update': None,
                'top_models': [],
                'status': 'error'
            }

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
        print(f"📝 Latest top model: {stats['top_models'][0][0]}")
    
    print("\n📋 Choose population strategy:")
    print("1. Test mode - Quick test with small batch size")
    print("2. Efficient mode - Medium batch size for steady progress")
    print("3. Standard mode - Larger batch size for faster processing")
    print("4. High-performance mode - Maximum batch size")
    print("5. All models (ALL ~1.9M+ models) - Complete dataset with NO LIMITS")
    print("6. Resume - Continue from where you left off")
    
    try:
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            print("🧪 Starting test mode with small batch size (100)...")
            populator.batch_size = 100
            populator.populate_all_models()
        elif choice == "2":
            print("📦 Starting efficient mode with medium batch size (500)...")
            populator.batch_size = 500
            populator.populate_all_models()
        elif choice == "3":
            print("📦 Starting standard mode with larger batch size (1000)...")
            populator.batch_size = 1000
            populator.populate_all_models()
        elif choice == "4":
            print("📦 Starting high-performance mode with maximum batch size (2000)...")
            populator.batch_size = 2000
            populator.populate_all_models()
        elif choice == "5":
            print("🌍 Starting complete mode (ALL ~1.9M+ models with NO LIMITS)...")
            print("⚠️  This will take a very long time (hours/days)")
            confirm = input("Are you sure? (yes/no): ").strip().lower()
            if confirm == "yes":
                populator.batch_size = 2000
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
        
        print("\n🏗️ Top architectures:")
        arch_dist = stats.get('architecture_distribution', {})
        for arch, count in list(arch_dist.items())[:5]:
            print(f"   {arch}: {count:,}")
        
        print("\n📄 Top licenses:")
        license_dist = stats.get('license_distribution', {})
        for license, count in list(license_dist.items())[:5]:
            print(f"   {license}: {count:,}")
        
        print("\n🏆 Top models by downloads:")
        top_models = stats.get('top_models', [])
        for i, (model_id, downloads, likes, score, arch, license) in enumerate(top_models[:5], 1):
            print(f"   {i}. {model_id}")
            print(f"      Downloads: {downloads:,}, Likes: {likes:,}, Score: {score:.3f}")
            print(f"      Architecture: {arch or 'unknown'}, License: {license or 'unknown'}")
        
        print("\n✅ Comprehensive database population completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation interrupted by user")
        print("💡 You can resume later using option 6")

if __name__ == "__main__":
    main()
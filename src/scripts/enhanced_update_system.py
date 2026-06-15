#!/usr/bin/env python3
"""
Enhanced Update System for HuggingFace Orchestrator
Downloads ALL models from HuggingFace API and generates comprehensive task_models.json
Handles models without tags and creates separate security/legal categories
"""

import sqlite3
import json
import time
import requests
import os
import shutil
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedUpdateSystem:
    """Comprehensive update system for HuggingFace Orchestrator."""
    
    def __init__(self, db_path: str = "db/hf_models.db", batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.total_models = 0
        self.processed_models = 0
        self.failed_models = 0
        
        # Rate limiting and retry configuration
        self.base_delay = 0.5  # Base delay between requests
        self.max_delay = 30.0  # Maximum delay on rate limiting
        self.current_delay = self.base_delay
        self.consecutive_failures = 0
        self.max_retries = 5
        self.retry_delay_base = 2.0
        
        # API rate limit tracking
        self.requests_this_minute = 0
        self.last_request_time = time.time()
        self.rate_limit_reset_time = time.time() + 60
        
        # Create database directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def create_timestamped_backup(self) -> bool:
        """
        Create timestamped backups of critical files before update.
        Returns True if backup was successful, False otherwise.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        files_to_backup = [
            ("config/task_models.json", f"task_models_{timestamp}.json"),
            ("db/hf_models.db", f"hf_models_{timestamp}.db"),
            ("config/model_configs.json", f"model_configs_{timestamp}.json"),
            ("config/dynamic_models.json", f"dynamic_models_{timestamp}.json"),
            ("config/settings.json", f"settings_{timestamp}.json")
        ]
        
        backup_success = True
        backed_up_files = []
        
        logger.info(f"💾 Creating timestamped backups (timestamp: {timestamp})...")
        
        for source_path, backup_filename in files_to_backup:
            source_file = Path(source_path)
            backup_file = backup_dir / backup_filename
            
            if source_file.exists():
                try:
                    # For database files, use copy2 to preserve metadata
                    if source_file.suffix == '.db':
                        shutil.copy2(source_file, backup_file)
                    else:
                        # For JSON files, copy content
                        shutil.copy2(source_file, backup_file)
                    
                    file_size = backup_file.stat().st_size
                    backed_up_files.append(f"✅ {source_path} -> {backup_filename} ({file_size:,} bytes)")
                    logger.info(f"💾 Backed up: {source_path} -> {backup_filename}")
                    
                except PermissionError as e:
                    error_msg = f"❌ Permission error backing up {source_path}: {e}"
                    logger.error(error_msg)
                    backed_up_files.append(error_msg)
                    backup_success = False
                except Exception as e:
                    error_msg = f"❌ Error backing up {source_path}: {e}"
                    logger.error(error_msg)
                    backed_up_files.append(error_msg)
                    backup_success = False
            else:
                logger.info(f"ℹ️ Skipping {source_path} (file does not exist)")
        
        # Create backup summary file
        try:
            summary_file = backup_dir / f"backup_summary_{timestamp}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Backup Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Backup Directory: {backup_dir.absolute()}\n")
                f.write(f"Success: {backup_success}\n\n")
                f.write("Files Backed Up:\n")
                f.write("-" * 50 + "\n")
                for status in backed_up_files:
                    f.write(f"{status}\n")
            
            logger.info(f"📋 Backup summary saved: {summary_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not create backup summary: {e}")
        
        if backup_success:
            logger.info(f"✅ All critical files backed up successfully to {backup_dir}")
            logger.info(f"📁 Backup timestamp: {timestamp}")
        else:
            logger.warning(f"⚠️ Some files failed to backup. Check logs for details.")
        
        return backup_success
    
    def _adjust_rate_limit(self, response: requests.Response = None, error: Exception = None):
        """Dynamically adjust rate limiting based on API response."""
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time - self.last_request_time >= 60:
            self.requests_this_minute = 0
            self.rate_limit_reset_time = current_time + 60
        
        # Check for rate limiting in response headers
        if response:
            # Check for rate limit headers
            remaining = response.headers.get('X-RateLimit-Remaining')
            reset_time = response.headers.get('X-RateLimit-Reset')
            
            if remaining and int(remaining) < 10:
                # Approaching rate limit, increase delay
                self.current_delay = min(self.max_delay, self.current_delay * 1.5)
                logger.info(f"⚠️ Approaching rate limit ({remaining} remaining), increased delay to {self.current_delay:.1f}s")
            
            elif remaining and int(remaining) > 50:
                # Plenty of requests left, decrease delay
                self.current_delay = max(self.base_delay, self.current_delay * 0.9)
                logger.info(f"✅ Rate limit healthy ({remaining} remaining), decreased delay to {self.current_delay:.1f}s")
            
            # Check for 429 (Too Many Requests) or 503 (Service Unavailable)
            if response.status_code in [429, 503]:
                self.consecutive_failures += 1
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = min(self.retry_delay_base * (2 ** self.consecutive_failures), 60)
                
                logger.warning(f"🛑 Rate limited (429/503). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                self.current_delay = min(self.max_delay, self.current_delay * 2)
                return True  # Indicate retry needed
        
        # Handle other errors
        if error:
            self.consecutive_failures += 1
            if "timeout" in str(error).lower():
                logger.warning(f"⏱️ Timeout error, increasing delay...")
                self.current_delay = min(self.max_delay, self.current_delay * 1.2)
            elif "connection" in str(error).lower():
                logger.warning(f"🔌 Connection error, increasing delay...")
                self.current_delay = min(self.max_delay, self.current_delay * 1.3)
        
        # Reset consecutive failures on success
        if response and response.status_code == 200:
            self.consecutive_failures = 0
            self.current_delay = max(self.base_delay, self.current_delay * 0.95)
        
        return False  # No retry needed
    
    def _make_api_request_with_retry(self, url: str, params: dict, max_retries: int = None) -> Optional[requests.Response]:
        """Make API request with retry logic and rate limiting."""
        if max_retries is None:
            max_retries = self.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                # Apply rate limiting
                time.sleep(self.current_delay)
                
                # Make request with timeout
                response = requests.get(
                    url, 
                    params=params, 
                    timeout=30,
                    headers={
                        'User-Agent': 'HuggingFace-Orchestrator/1.0 (https://github.com/huggingface/hub)'
                    }
                )
                
                # Check if we need to retry due to rate limiting
                if self._adjust_rate_limit(response=response):
                    if attempt < max_retries:
                        continue
                    else:
                        logger.error(f"❌ Max retries reached for rate limiting")
                        return None
                
                # Handle other error status codes
                if response.status_code != 200:
                    if response.status_code in [429, 503]:
                        # Already handled by _adjust_rate_limit
                        continue
                    elif response.status_code == 404:
                        logger.error(f"❌ API endpoint not found (404)")
                        return None
                    elif response.status_code >= 500:
                        logger.warning(f"⚠️ Server error {response.status_code}, retrying...")
                        if attempt < max_retries:
                            time.sleep(self.retry_delay_base * (2 ** attempt))
                            continue
                        else:
                            logger.error(f"❌ Max retries reached for server error")
                            return None
                    else:
                        logger.error(f"❌ API request failed: {response.status_code}")
                        return None
                
                # Success
                self.requests_this_minute += 1
                self.last_request_time = time.time()
                return response
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"⏱️ Request timeout (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(self.retry_delay_base * (2 ** attempt))
                    continue
                else:
                    logger.error(f"❌ Max retries reached for timeout")
                    self._adjust_rate_limit(error=e)
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Connection error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(self.retry_delay_base * (2 ** attempt))
                    continue
                else:
                    logger.error(f"❌ Max retries reached for connection error")
                    self._adjust_rate_limit(error=e)
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                self._adjust_rate_limit(error=e)
                return None
        
        return None

    def _parse_api_response(self, response_data):
        """Parse API response and handle different data formats, ensuring all items are dictionaries."""
        if not response_data:
            return []
        
        parsed_models = []
        string_count = 0
        dict_count = 0
        other_count = 0
        
        for item in response_data:
            if isinstance(item, str):
                string_count += 1
                logger.warning(f"⚠️ API returned string item: {item[:100]}... Converting to model dict.")
                
                # Try to parse as JSON first
                try:
                    parsed_item = json.loads(item)
                    if isinstance(parsed_item, dict):
                        parsed_models.append(parsed_item)
                        continue
                    else:
                        logger.warning(f"⚠️ Parsed JSON is not a dict: {type(parsed_item)}")
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"⚠️ Failed to parse as JSON, treating as model ID: {item[:100]}...")
                
                # Convert string to model dictionary
                if '/' in item:
                    author, model_name = item.split('/', 1)
                else:
                    author = 'unknown'
                    model_name = item
                
                model_obj = {
                    'id': item,
                    'author': {'name': author},
                    'pipeline_tag': '',
                    'tags': [],
                    'description': '',
                    'downloads': 0,
                    'likes': 0,
                    'model_type': '',
                    'library_name': '',
                    'last_modified': None
                }
                parsed_models.append(model_obj)
                
            elif isinstance(item, dict):
                dict_count += 1
                parsed_models.append(item)
                
            else:
                other_count += 1
                logger.warning(f"⚠️ Unexpected data type for item: {type(item)}, content: {str(item)[:100]}... Creating minimal dict.")
                # Create a minimal dictionary for unexpected types to prevent downstream errors
                parsed_models.append({
                    'id': str(item), 
                    'author': {'name': 'unknown'}, 
                    'pipeline_tag': 'unknown', 
                    'tags': [], 
                    'description': '', 
                    'downloads': 0, 
                    'likes': 0, 
                    'model_type': '', 
                    'library_name': '', 
                    'last_modified': None
                })
        
        # Log summary of what was processed
        total_items = len(response_data)
        logger.info(f"📊 API response processing summary:")
        logger.info(f"   - Total items: {total_items}")
        logger.info(f"   - Strings converted: {string_count}")
        logger.info(f"   - Dictionaries: {dict_count}")
        logger.info(f"   - Other types: {other_count}")
        logger.info(f"   - Final parsed models: {len(parsed_models)}")
        
        # Final verification - ensure ALL items are dictionaries
        non_dict_items = [i for i in parsed_models if not isinstance(i, dict)]
        if non_dict_items:
            logger.error(f"❌ CRITICAL: Found {len(non_dict_items)} non-dict items after parsing!")
            logger.error(f"   Types: {[type(item) for item in non_dict_items[:5]]}")
            # Convert any remaining non-dict items to dicts
            for i, item in enumerate(parsed_models):
                if not isinstance(item, dict):
                    parsed_models[i] = {
                        'id': str(item), 
                        'author': {'name': 'unknown'}, 
                        'pipeline_tag': 'unknown', 
                        'tags': [], 
                        'description': '', 
                        'downloads': 0, 
                        'likes': 0, 
                        'model_type': '', 
                        'library_name': '', 
                        'last_modified': None
                    }
            logger.info(f"✅ Converted all non-dict items to dictionaries")
        
        if parsed_models:
            logger.info(f"✅ API response successfully processed. All {len(parsed_models)} items are dictionaries.")
        else:
            logger.warning(f"⚠️ No models parsed from API response")
            
        return parsed_models

    def _init_database(self):
        """Initialize the database with comprehensive schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def download_models_with_limit(self, max_models: int = 100000, page_size: int = 1000):
        """Download a limited number of models from HuggingFace API for testing."""
        logger.info(f"📥 Starting limited model download from HuggingFace (max: {max_models:,})...")
        
        try:
            # Clear existing data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM models')
                conn.commit()
                logger.info("🗑️ Cleared existing database")
            
            # Initialize counters
            self.total_models = max_models
            self.processed_models = 0
            self.failed_models = 0
            
            # Pagination parameters
            offset = 0
            total_fetched = 0
            
            # Track progress
            start_time = time.time()
            last_progress_time = start_time
            
            while total_fetched < max_models:
                try:
                    # Calculate how many models to fetch in this batch
                    remaining = max_models - total_fetched
                    current_batch_size = min(page_size, remaining)
                    
                    logger.info(f"📄 Fetching models {offset:,} to {offset + current_batch_size:,}...")
                    
                    # Fetch a page of models using direct API with retry logic
                    url = "https://huggingface.co/api/models"
                    params = {
                        "full": "true",
                        "limit": current_batch_size,
                        "offset": offset
                    }
                    
                    response = self._make_api_request_with_retry(url, params)
                    if response is None:
                        logger.error(f"❌ Failed to fetch models at offset {offset}")
                        # Continue with next page
                        offset += current_batch_size
                        continue
                    
                    models = response.json()
                    if not models:
                        logger.info("✅ No more models to fetch")
                        break
                    
                    # Parse and handle the API response
                    models = self._parse_api_response(models)
                    
                    # Process this page immediately
                    self._process_models_batch(models)
                    
                    # Update counters
                    total_fetched += len(models)
                    offset += current_batch_size
                    
                    # Progress update every 10 pages or every 5 minutes
                    current_time = time.time()
                    if (offset % (page_size * 10) == 0 or 
                        current_time - last_progress_time > 300):
                        
                        elapsed = current_time - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        progress = (total_fetched / max_models) * 100
                        
                        logger.info(f"📈 Progress: {progress:.1f}% ({total_fetched:,}/{max_models:,})")
                        logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                        logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                        logger.info(f"   ✅ Processed: {self.processed_models:,}")
                        logger.info(f"   ❌ Failed: {self.failed_models:,}")
                        logger.info(f"   🐌 Current delay: {self.current_delay:.1f}s")
                        
                        last_progress_time = current_time
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching page at offset {offset}: {e}")
                    # Continue with next page
                    offset += current_batch_size
                    time.sleep(2)  # Wait longer on error
            
            # Update metadata
            self._update_metadata()
            
            # Final statistics
            elapsed = time.time() - start_time
            logger.info(f"✅ Limited model download completed!")
            logger.info(f"   📊 Total fetched: {total_fetched:,}")
            logger.info(f"   ✅ Processed: {self.processed_models:,}")
            logger.info(f"   ❌ Failed: {self.failed_models:,}")
            logger.info(f"   ⏱️ Total time: {elapsed/60:.1f} minutes")
            logger.info(f"   🚀 Average rate: {total_fetched/elapsed:.1f} models/second")
            logger.info(f"   🐌 Final delay: {self.current_delay:.1f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error downloading models: {e}")
            return False

    def download_all_models(self):
        """Download ALL models from HuggingFace API using pagination."""
        logger.info("📥 Starting comprehensive model download from HuggingFace using pagination...")
        
        try:
            # Clear existing data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM models')
                conn.commit()
                logger.info("🗑️ Cleared existing database")
            
            # Initialize counters
            self.total_models = 0
            self.processed_models = 0
            self.failed_models = 0
            
            # Pagination parameters
            page_size = 1000  # Maximum per request
            offset = 0
            total_fetched = 0
            
            # Track progress
            start_time = time.time()
            last_progress_time = start_time
            
            while True:
                try:
                    logger.info(f"📄 Fetching models {offset:,} to {offset + page_size:,}...")
                    
                    # Fetch a page of models using direct API with retry logic
                    url = "https://huggingface.co/api/models"
                    params = {
                        "full": "true",
                        "limit": page_size,
                        "offset": offset
                    }
                    
                    response = self._make_api_request_with_retry(url, params)
                    if response is None:
                        logger.error(f"❌ Failed to fetch models at offset {offset}")
                        # Continue with next page
                        offset += page_size
                        continue
                    
                    models = response.json()
                    if not models:
                        logger.info("✅ No more models to fetch")
                        break
                    
                    # Parse and handle the API response
                    models = self._parse_api_response(models)
                    
                    # Process this page immediately
                    self._process_models_batch(models)
                    
                    # Update counters
                    total_fetched += len(models)
                    offset += page_size
                    
                    # Progress update every 10 pages or every 5 minutes
                    current_time = time.time()
                    if (offset % (page_size * 10) == 0 or 
                        current_time - last_progress_time > 300):
                        
                        elapsed = current_time - start_time
                        rate = total_fetched / elapsed if elapsed > 0 else 0
                        
                        logger.info(f"📈 Progress: {total_fetched:,} models processed")
                        logger.info(f"   ⏱️ Elapsed: {elapsed/60:.1f} minutes")
                        logger.info(f"   🚀 Rate: {rate:.1f} models/second")
                        logger.info(f"   ✅ Processed: {self.processed_models:,}")
                        logger.info(f"   ❌ Failed: {self.failed_models:,}")
                        logger.info(f"   🐌 Current delay: {self.current_delay:.1f}s")
                        
                        last_progress_time = current_time
                    
                    # Safety check - limit to reasonable number for testing
                    if total_fetched >= 100000:  # Limit to 100k for testing
                        logger.info(f"🛑 Reached test limit of {total_fetched:,} models")
                        break
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching page at offset {offset}: {e}")
                    # Continue with next page
                    offset += page_size
                    time.sleep(2)  # Wait longer on error
            
            # Update metadata
            self._update_metadata()
            
            # Final statistics
            elapsed = time.time() - start_time
            logger.info(f"✅ Model download completed!")
            logger.info(f"   📊 Total fetched: {total_fetched:,}")
            logger.info(f"   ✅ Processed: {self.processed_models:,}")
            logger.info(f"   ❌ Failed: {self.failed_models:,}")
            logger.info(f"   ⏱️ Total time: {elapsed/60:.1f} minutes")
            logger.info(f"   🚀 Average rate: {total_fetched/elapsed:.1f} models/second")
            logger.info(f"   🐌 Final delay: {self.current_delay:.1f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error downloading models: {e}")
            return False
    
    def _process_models_batch(self, models_list: List[Dict[str, Any]]):
        """Process models in batches for better performance."""
        batch = []
        
        for i, model in enumerate(models_list):
            try:
                # Extract model data
                model_data = self._extract_model_data(model)
                if model_data:
                    batch.append(model_data)
                    self.processed_models += 1
                
                # Process batch when it reaches batch size
                if len(batch) >= self.batch_size:
                    self._insert_batch(batch)
                    batch = []
                    
                    # Progress update
                    logger.info(f"📈 Processed batch: {self.processed_models:,} models so far")
                
                # Small delay to be respectful to API
                if i % 100 == 0:
                    time.sleep(0.1)
                    
            except Exception as e:
                # Handle case where model might be a string or other type
                if isinstance(model, dict):
                    model_id = model.get('id', 'unknown')
                else:
                    model_id = str(model)[:50] if model else 'unknown'
                logger.warning(f"⚠️ Failed to process model {model_id}: {e}")
                self.failed_models += 1
        
        # Insert remaining batch
        if batch:
            self._insert_batch(batch)
            logger.info(f"📈 Final batch processed: {len(batch)} models")
            logger.info(f"📊 Total processed in this batch: {self.processed_models:,} models")
    
    def _extract_model_data(self, model: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant data from HuggingFace model object."""
        try:
            # Handle case where model is a string instead of dict
            if isinstance(model, str):
                logger.warning(f"⚠️ Received string instead of dict for model: {model[:100]}...")
                # Convert string to basic model object
                if '/' in model:
                    author, model_name = model.split('/', 1)
                else:
                    author = 'unknown'
                    model_name = model
                
                model = {
                    'id': model,
                    'author': {'name': author},
                    'pipeline_tag': '',
                    'tags': [],
                    'description': '',
                    'downloads': 0,
                    'likes': 0,
                    'model_type': '',
                    'library_name': '',
                    'last_modified': None
                }
            
            # Ensure model is a dictionary
            if not isinstance(model, dict):
                logger.warning(f"⚠️ Received non-dict object for model: {type(model)}")
                return None
            
            model_id = model.get('id', '')
            author = model.get('author', {}).get('name', '') if model.get('author') else ''
            pipeline_tag = model.get('pipeline_tag', '')
            tags = model.get('tags', [])
            description = model.get('description', '')
            downloads = model.get('downloads', 0)
            likes = model.get('likes', 0)
            model_type = model.get('model_type', '')
            library_name = model.get('library_name', '')
            last_modified = model.get('last_modified', None)
            
            # Extract author from model_id if not available
            if not author and '/' in model_id:
                author = model_id.split('/')[0]
            
            # Handle tags
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = [tags] if tags else []
            elif not isinstance(tags, list):
                tags = []
            
            tags_json = json.dumps(tags) if tags else '[]'
            
            # Calculate scores
            decision_score = self._calculate_decision_score(model_id, pipeline_tag, downloads, likes, author, library_name)
            capability_score = self._calculate_capability_score(model_type, pipeline_tag)
            efficiency_score = self._calculate_efficiency_score(model_type, downloads)
            popularity_score = self._calculate_popularity_score(downloads, likes)
            
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
                'last_modified': last_modified
            }
            
        except Exception as e:
            # Provide more detailed error information
            if isinstance(model, dict):
                model_id = model.get('id', 'unknown')
            else:
                model_id = str(model)[:50] if model else 'unknown'
            logger.warning(f"⚠️ Error extracting data from model {model_id}: {e}")
            return None
    
    def _calculate_decision_score(self, model_id: str, pipeline_tag: str, downloads: int, likes: int, author: str, library_name: str) -> float:
        """Calculate decision score based on model quality indicators."""
        score = 0.5  # Base score
        
        # Downloads factor (0-0.3)
        if downloads > 0:
            score += min(0.3, (downloads / 1000000) * 0.3)
        
        # Likes factor (0-0.2)
        if likes > 0:
            score += min(0.2, (likes / 10000) * 0.2)
        
        # Pipeline tag factor (0-0.2)
        if pipeline_tag:
            score += 0.2
        
        # Author reputation factor (0-0.1)
        reputable_authors = ['microsoft', 'google', 'facebook', 'openai', 'anthropic', 'meta', 'huggingface', 'stabilityai', 'eleutherai']
        if author.lower() in reputable_authors:
            score += 0.1
        
        # Library factor (0-0.1)
        if library_name:
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_capability_score(self, model_type: str, pipeline_tag: str) -> float:
        """Calculate capability score based on model characteristics."""
        score = 0.5  # Base score
        
        # Model size factor (larger models = more capable)
        if model_type:
            if any(x in model_type.lower() for x in ['llama', 'gpt', 'claude', 'gemini']):
                score += 0.3
            elif any(x in model_type.lower() for x in ['bert', 'roberta', 'distilbert']):
                score += 0.2
        
        # Pipeline tag complexity
        complex_tasks = ['text-generation', 'translation', 'summarization', 'question-answering', 'text2text-generation']
        if pipeline_tag in complex_tasks:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_efficiency_score(self, model_type: str, downloads: int) -> float:
        """Calculate efficiency score based on model efficiency indicators."""
        score = 0.5  # Base score
        
        # Smaller models are more efficient
        if model_type:
            if any(x in model_type.lower() for x in ['distil', 'tiny', 'small']):
                score += 0.3
            elif 'base' in model_type.lower():
                score += 0.2
        
        # Popular models are often optimized
        if downloads > 10000:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_popularity_score(self, downloads: int, likes: int) -> float:
        """Calculate popularity score based on usage metrics."""
        score = 0.0
        
        # Downloads factor (0-0.6)
        if downloads > 0:
            score += min(0.6, (downloads / 1000000) * 0.6)
        
        # Likes factor (0-0.4)
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
                
                # Prepare insert statement
                insert_sql = '''
                    INSERT OR REPLACE INTO models (
                        model_id, author, pipeline_tag, tags, description, downloads, likes,
                        decision_score, capability_score, efficiency_score, popularity_score,
                        model_type, library_name, last_modified, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                '''
                
                # Prepare data for insertion
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
                            model_data['last_modified']
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
                    'population_version': '3.0'
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
    
    def generate_task_models_json(self):
        """Generate comprehensive task_models.json from database."""
        logger.info("🔄 Generating task_models.json from database...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all unique pipeline tags
                cursor.execute('''
                    SELECT DISTINCT pipeline_tag 
                    FROM models 
                    WHERE pipeline_tag IS NOT NULL AND pipeline_tag != ''
                    ORDER BY pipeline_tag
                ''')
                pipeline_tags = [row[0] for row in cursor.fetchall()]
                
                # Get models without pipeline tags
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM models 
                    WHERE pipeline_tag IS NULL OR pipeline_tag = ''
                ''')
                models_without_tags = cursor.fetchone()[0]
                
                logger.info(f"📊 Found {len(pipeline_tags)} pipeline tags and {models_without_tags:,} models without tags")
                
                # Create task configuration
                tasks_config = {}
                
                # Process each pipeline tag
                for pipeline_tag in pipeline_tags:
                    # Get best models for this pipeline
                    cursor.execute('''
                        SELECT model_id, downloads, likes, decision_score, description, tags
                        FROM models 
                        WHERE pipeline_tag = ?
                        ORDER BY decision_score DESC, downloads DESC
                        LIMIT 10
                    ''', (pipeline_tag,))
                    
                    models = cursor.fetchall()
                    
                    if models:
                        # Determine category based on pipeline tag and tags
                        category = self._determine_category(pipeline_tag, models)
                        
                        if category not in tasks_config:
                            tasks_config[category] = {}
                        
                        # Create task entry
                        task_name = pipeline_tag.replace('-', '_')
                        best_model = models[0][0]  # model_id of best model
                        alternative_models = [model[0] for model in models[1:5]]  # Next 4 models
                        
                        # Get file types for this task
                        file_types = self._get_file_types_for_task(pipeline_tag)
                        
                        # Get description
                        description = self._get_task_description(pipeline_tag)
                        
                        tasks_config[category][task_name] = {
                            "pipeline": pipeline_tag,
                            "description": description,
                            "supported_file_types": file_types,
                            "best_model": best_model,
                            "alternative_models": alternative_models
                        }
                
                # Handle models without pipeline tags
                if models_without_tags > 0:
                    cursor.execute('''
                        SELECT model_id, downloads, likes, decision_score, description, tags
                        FROM models 
                        WHERE pipeline_tag IS NULL OR pipeline_tag = ''
                        ORDER BY decision_score DESC, downloads DESC
                        LIMIT 50
                    ''')
                    
                    untagged_models = cursor.fetchall()
                    
                    if untagged_models:
                        if 'general' not in tasks_config:
                            tasks_config['general'] = {}
                        
                        tasks_config['general']['untagged_models'] = {
                            "pipeline": "general",
                            "description": f"General models without specific pipeline tags ({models_without_tags:,} total models)",
                            "supported_file_types": ["*"],
                            "best_model": untagged_models[0][0],
                            "alternative_models": [model[0] for model in untagged_models[1:10]]
                        }
                
                # Save to file
                self._save_task_models_json(tasks_config)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error generating task_models.json: {e}")
            return False
    
    def _determine_category(self, pipeline_tag: str, models: List[tuple]) -> str:
        """Determine category based on pipeline tag and model tags."""
        # Security and legal keywords
        security_keywords = ['security', 'malware', 'threat', 'vulnerability', 'cyber', 'attack', 'defense', 'forensic']
        legal_keywords = ['legal', 'law', 'compliance', 'regulation', 'contract', 'privacy', 'gdpr', 'ccpa']
        
        # Check pipeline tag
        pipeline_lower = pipeline_tag.lower()
        if any(keyword in pipeline_lower for keyword in security_keywords):
            return 'security'
        elif any(keyword in pipeline_lower for keyword in legal_keywords):
            return 'legal'
        
        # Check model tags and descriptions
        for model in models:
            tags = model[5]  # tags column
            description = model[4]  # description column
            
            if tags:
                try:
                    tag_list = json.loads(tags)
                    for tag in tag_list:
                        tag_lower = tag.lower()
                        if any(keyword in tag_lower for keyword in security_keywords):
                            return 'security'
                        elif any(keyword in tag_lower for keyword in legal_keywords):
                            return 'legal'
                except:
                    pass
            
            if description:
                desc_lower = description.lower()
                if any(keyword in desc_lower for keyword in security_keywords):
                    return 'security'
                elif any(keyword in desc_lower for keyword in legal_keywords):
                    return 'legal'
        
        # Default categories based on pipeline
        category_mapping = {
            'text-generation': 'text_generation',
            'text-classification': 'text_classification',
            'translation': 'translation',
            'summarization': 'summarization',
            'question-answering': 'question_answering',
            'text2text-generation': 'text_generation',
            'token-classification': 'text_classification',
            'image-classification': 'computer_vision',
            'object-detection': 'computer_vision',
            'image-segmentation': 'computer_vision',
            'image-to-text': 'multimodal',
            'text-to-image': 'multimodal',
            'audio-classification': 'audio',
            'automatic-speech-recognition': 'audio',
            'text-to-speech': 'audio',
            'feature-extraction': 'feature_extraction',
            'fill-mask': 'text_classification',
            'zero-shot-classification': 'text_classification',
            'sentiment-analysis': 'text_classification',
            'named-entity-recognition': 'text_classification',
            'part-of-speech-tagging': 'text_classification',
            'mask-generation': 'computer_vision',
            'depth-estimation': 'computer_vision',
            'image-to-image': 'computer_vision',
            'unconditional-image-generation': 'computer_vision',
            'video-classification': 'video',
            'text-to-video': 'video',
            'tabular-classification': 'tabular',
            'tabular-regression': 'tabular',
            'reinforcement-learning': 'reinforcement_learning',
            'robotics': 'robotics',
            'time-series-forecasting': 'time_series',
            'graph-ml': 'graph_ml',
            'other': 'other'
        }
        
        return category_mapping.get(pipeline_tag, 'other')
    
    def _get_file_types_for_task(self, pipeline_tag: str) -> List[str]:
        """Get supported file types for a given task."""
        file_type_mapping = {
            'text-generation': ['txt', 'md', 'json', 'csv'],
            'text-classification': ['txt', 'md', 'json', 'csv'],
            'translation': ['txt', 'md', 'json'],
            'summarization': ['txt', 'md', 'json'],
            'question-answering': ['txt', 'md', 'json', 'pdf'],
            'text2text-generation': ['txt', 'md', 'json'],
            'token-classification': ['txt', 'md', 'json'],
            'image-classification': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'object-detection': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'image-segmentation': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'image-to-text': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'text-to-image': ['txt', 'md', 'json'],
            'audio-classification': ['wav', 'mp3', 'flac', 'ogg'],
            'automatic-speech-recognition': ['wav', 'mp3', 'flac', 'ogg'],
            'text-to-speech': ['txt', 'md', 'json'],
            'feature-extraction': ['*'],
            'fill-mask': ['txt', 'md', 'json'],
            'zero-shot-classification': ['txt', 'md', 'json'],
            'sentiment-analysis': ['txt', 'md', 'json'],
            'named-entity-recognition': ['txt', 'md', 'json'],
            'part-of-speech-tagging': ['txt', 'md', 'json'],
            'mask-generation': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'depth-estimation': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'image-to-image': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
            'unconditional-image-generation': ['txt', 'md', 'json'],
            'video-classification': ['mp4', 'avi', 'mov', 'mkv'],
            'text-to-video': ['txt', 'md', 'json'],
            'tabular-classification': ['csv', 'xlsx', 'json'],
            'tabular-regression': ['csv', 'xlsx', 'json'],
            'reinforcement-learning': ['*'],
            'robotics': ['*'],
            'time-series-forecasting': ['csv', 'json'],
            'graph-ml': ['*'],
            'other': ['*']
        }
        
        return file_type_mapping.get(pipeline_tag, ['*'])
    
    def _get_task_description(self, pipeline_tag: str) -> str:
        """Get description for a given task."""
        descriptions = {
            'text-generation': 'Generate text based on input prompts',
            'text-classification': 'Classify text into categories',
            'translation': 'Translate text between languages',
            'summarization': 'Create summaries of longer texts',
            'question-answering': 'Answer questions based on context',
            'text2text-generation': 'Transform text from one form to another',
            'token-classification': 'Classify individual tokens in text',
            'image-classification': 'Classify images into categories',
            'object-detection': 'Detect and locate objects in images',
            'image-segmentation': 'Segment images into regions',
            'image-to-text': 'Generate text descriptions of images',
            'text-to-image': 'Generate images from text descriptions',
            'audio-classification': 'Classify audio into categories',
            'automatic-speech-recognition': 'Convert speech to text',
            'text-to-speech': 'Convert text to speech',
            'feature-extraction': 'Extract features from data',
            'fill-mask': 'Fill in masked tokens in text',
            'zero-shot-classification': 'Classify text without training examples',
            'sentiment-analysis': 'Analyze sentiment in text',
            'named-entity-recognition': 'Identify named entities in text',
            'part-of-speech-tagging': 'Tag parts of speech in text',
            'mask-generation': 'Generate masks for images',
            'depth-estimation': 'Estimate depth from images',
            'image-to-image': 'Transform images from one form to another',
            'unconditional-image-generation': 'Generate images without input',
            'video-classification': 'Classify videos into categories',
            'text-to-video': 'Generate videos from text descriptions',
            'tabular-classification': 'Classify tabular data',
            'tabular-regression': 'Perform regression on tabular data',
            'reinforcement-learning': 'Reinforcement learning tasks',
            'robotics': 'Robotics-related tasks',
            'time-series-forecasting': 'Forecast time series data',
            'graph-ml': 'Graph machine learning tasks',
            'other': 'Other machine learning tasks'
        }
        
        return descriptions.get(pipeline_tag, f'Task for {pipeline_tag} pipeline')
    
    def _save_task_models_json(self, tasks_config: Dict[str, Any]):
        """Save task_models.json."""
        config_path = Path("config/task_models.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save new configuration
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(tasks_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved task_models.json with {len(tasks_config)} categories")
            
            # Display statistics
            total_tasks = sum(len(tasks) for tasks in tasks_config.values())
            logger.info(f"📊 Total tasks: {total_tasks}")
            for category, tasks in tasks_config.items():
                logger.info(f"   {category}: {len(tasks)} tasks")
                
        except Exception as e:
            logger.error(f"❌ Error saving task_models.json: {e}")
            raise
    
    def run_complete_update(self):
        """Run the complete update process."""
        logger.info("🚀 Starting complete update process...")
        
        # Step 1: Download all models
        logger.info("📥 Step 1: Downloading all models from HuggingFace...")
        if not self.download_all_models():
            logger.error("❌ Failed to download models")
            return False
        
        # Step 2: Generate task_models.json
        logger.info("🔄 Step 2: Generating task_models.json...")
        if not self.generate_task_models_json():
            logger.error("❌ Failed to generate task_models.json")
            return False
        
        logger.info("✅ Complete update process finished successfully!")
        return True

def main():
    """Main function for the enhanced update system."""
    print("🚀 Enhanced HuggingFace Orchestrator Update System")
    print("=" * 60)
    
    # Check if input is being piped (non-interactive mode)
    import sys
    import select
    
    # Check if stdin is connected to a pipe or if we're in non-interactive mode
    is_piped = not sys.stdin.isatty()
    
    if is_piped:
        print("🔧 Non-interactive mode detected (piped input)")
        # Read choice from stdin
        try:
            choice = input().strip()
        except EOFError:
            choice = "5"  # Default to all models if no input provided
            print(f"⚠️ No input provided, using default choice: {choice}")
    else:
        # Get user input for update strategy
        print("\n📋 Choose update strategy:")
        print("1. Test mode (1,000 models) - Quick test")
        print("2. Small mode (10,000 models) - Small dataset")
        print("3. Medium mode (100,000 models) - Medium dataset")
        print("4. Large mode (1,000,000 models) - Large dataset")
        print("5. All models (8M+ models) - Complete dataset (very long)")
        choice = input("\nEnter your choice (1-5): ").strip()
    
    try:
        # Initialize update system
        update_system = EnhancedUpdateSystem()
        
        # Create timestamped backup before any updates
        print("\n💾 Creating backup of current configuration...")
        backup_success = update_system.create_timestamped_backup()
        
        if not backup_success:
            if is_piped:
                print("⚠️ Warning: Some files failed to backup, but continuing in non-interactive mode...")
            else:
                print("⚠️ Warning: Some files failed to backup. Continue anyway? (y/n): ", end="")
                continue_choice = input().strip().lower()
                if continue_choice not in ['y', 'yes']:
                    print("❌ Operation cancelled due to backup failure")
                    return 1
                print("⚠️ Continuing without complete backup...")
        else:
            print("✅ Backup completed successfully!")
        
        if choice == "1":
            print("🧪 Starting test mode (1,000 models)...")
            success = update_system.download_models_with_limit(max_models=1000, page_size=100)
        elif choice == "2":
            print("📊 Starting small mode (10,000 models)...")
            success = update_system.download_models_with_limit(max_models=10000, page_size=500)
        elif choice == "3":
            print("📈 Starting medium mode (100,000 models)...")
            success = update_system.download_models_with_limit(max_models=100000, page_size=1000)
        elif choice == "4":
            print("🚀 Starting large mode (1,000,000 models)...")
            success = update_system.download_models_with_limit(max_models=1000000, page_size=1000)
        elif choice == "5":
            print("🌍 Starting complete mode (ALL models - 8M+)...")
            print("⚠️  This will take a very long time (hours/days)")
            
            if is_piped:
                print("🔧 Non-interactive mode: Auto-confirming complete mode...")
                success = update_system.download_all_models()
            else:
                confirm = input("Are you sure? (yes/no): ").strip().lower()
                if confirm == "yes":
                    success = update_system.download_all_models()
                else:
                    print("❌ Operation cancelled")
                    return 1
        else:
            print("❌ Invalid choice. Using test mode (1,000 models)...")
            success = update_system.download_models_with_limit(max_models=1000, page_size=100)
        
        if success:
            # Generate task_models.json
            print("\n🔄 Generating task_models.json...")
            if update_system.generate_task_models_json():
                print("\n✅ Update completed successfully!")
                print("📁 Database updated with models from HuggingFace")
                print("📁 task_models.json generated with categories")
                print("🔒 Security and legal models properly categorized")
                print("📊 Models without tags included in general category")
                print(f"🐌 Final rate limit delay: {update_system.current_delay:.1f}s")
                return 0
            else:
                print("\n❌ Failed to generate task_models.json!")
                return 1
        else:
            print("\n❌ Update failed!")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your internet connection and try again")
        return 1

if __name__ == "__main__":
    exit(main()) 
#!/usr/bin/env python3
"""
Dynamic Model Configuration System
Creates model configurations dynamically from database - NO HARDCODED MODELS
"""

import os
import sqlite3
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class DynamicModelConfig:
    """Dynamic model configuration created from database"""
    name: str
    api_provider: str
    model_id: str
    max_tokens: int = 1000
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    rate_limit_per_minute: int = 1000
    timeout_seconds: int = 30

def create_default_configs() -> Dict[str, DynamicModelConfig]:
    """
    Create dynamic model configurations from database.
    NO HARDCODED MODELS - everything comes from database.
    """
    configs = {}
    
    try:
        # Connect to the HuggingFace models database
        conn = sqlite3.connect("db/hf_models.db")
        cursor = conn.cursor()
        
        # Get the best models for different tasks from database
        cursor.execute("""
            SELECT model_id, pipeline_tag, downloads, likes 
            FROM models 
            WHERE downloads > 1000 
            ORDER BY downloads DESC, likes DESC 
            LIMIT 10
        """)
        
        models = cursor.fetchall()
        conn.close()
        
        if not models:
            # If database is empty, create minimal API-only configs
            print("⚠️ No models found in database, creating API-only configs")
            configs = create_api_only_configs()
        else:
            # Create dynamic configs from database models
            for i, (model_id, pipeline_tag, downloads, likes) in enumerate(models):
                config_name = f"dynamic_model_{i+1}"
                
                # Determine provider based on model_id
                if model_id.startswith('openai/'):
                    provider = 'openai'
                elif model_id.startswith('anthropic/'):
                    provider = 'anthropic'
                elif model_id.startswith('google/'):
                    provider = 'gemini'
                else:
                    provider = 'huggingface'
                
                # Create dynamic configuration
                configs[config_name] = DynamicModelConfig(
                    name=config_name,
                    api_provider=provider,
                    model_id=model_id,
                    max_tokens=1000,
                    temperature=0.7,
                    cost_per_1k_tokens=0.0,
                    rate_limit_per_minute=1000,
                    timeout_seconds=30
                )
                
                print(f"🎯 Created dynamic config: {config_name} -> {model_id}")
        
    except Exception as e:
        print(f"⚠️ Database error: {str(e)}, creating API-only configs")
        configs = create_api_only_configs()
    
    return configs

def create_api_only_configs() -> Dict[str, DynamicModelConfig]:
    """
    Create API-only configurations when database is not available.
    These are provider placeholders, not specific models.
    """
    configs = {}
    
    # Check which API keys are available
    available_apis = []
    
    if os.getenv('OPENAI_API_KEY'):
        available_apis.append('openai')
    if os.getenv('ANTHROPIC_API_KEY'):
        available_apis.append('anthropic')
    if os.getenv('GOOGLE_GEMINI_API_KEY'):
        available_apis.append('gemini')
    
    # Create dynamic configs for available APIs
    for i, provider in enumerate(available_apis):
        config_name = f"api_{provider}_{i+1}"
        
        configs[config_name] = DynamicModelConfig(
            name=config_name,
            api_provider=provider,
            model_id=f"dynamic_{provider}_model",  # Will be selected dynamically
            max_tokens=1000,
            temperature=0.7,
            cost_per_1k_tokens=0.0,
            rate_limit_per_minute=1000,
            timeout_seconds=30
        )
        
        print(f"🎯 Created API config: {config_name} -> {provider}")
    
    return configs

def get_best_model_for_task(task_category: str, pipeline_tag: str = None) -> Optional[DynamicModelConfig]:
    """
    Get the best model for a specific task from the database.
    """
    try:
        conn = sqlite3.connect("db/hf_models.db")
        cursor = conn.cursor()
        
        if pipeline_tag:
            # Query by specific pipeline tag
            cursor.execute("""
                SELECT model_id, pipeline_tag, downloads, likes 
                FROM models 
                WHERE pipeline_tag = ? AND downloads > 1000
                ORDER BY downloads DESC, likes DESC 
                LIMIT 1
            """, (pipeline_tag,))
        else:
            # Query by task category
            cursor.execute("""
                SELECT model_id, pipeline_tag, downloads, likes 
                FROM models 
                WHERE pipeline_tag LIKE ? AND downloads > 1000
                ORDER BY downloads DESC, likes DESC 
                LIMIT 1
            """, (f"%{task_category}%",))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            model_id, pipeline_tag, downloads, likes = result
            
            # Determine provider
            if model_id.startswith('openai/'):
                provider = 'openai'
            elif model_id.startswith('anthropic/'):
                provider = 'anthropic'
            elif model_id.startswith('google/'):
                provider = 'gemini'
            else:
                provider = 'huggingface'
            
            return DynamicModelConfig(
                name=f"best_{task_category}",
                api_provider=provider,
                model_id=model_id,
                max_tokens=1000,
                temperature=0.7,
                cost_per_1k_tokens=0.0,
                rate_limit_per_minute=1000,
                timeout_seconds=30
            )
        
    except Exception as e:
        print(f"⚠️ Error getting best model for {task_category}: {str(e)}")
    
    return None

def create_task_specific_configs() -> Dict[str, DynamicModelConfig]:
    """
    Create configurations for specific tasks using database models.
    """
    task_configs = {}
    
    # Common task categories
    tasks = [
        'text-generation',
        'automatic-speech-recognition', 
        'image-classification',
        'text-classification',
        'translation',
        'summarization',
        'question-answering'
    ]
    
    for task in tasks:
        config = get_best_model_for_task(task)
        if config:
            task_configs[f"best_{task}"] = config
            print(f"🎯 Created task config: best_{task} -> {config.model_id}")
    
    return task_configs 
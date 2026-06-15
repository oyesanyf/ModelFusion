"""
System Configuration Module
Provides centralized configuration management for the Sagamu LLM Orchestrator.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class SystemConfig:
    """System configuration with default values and environment overrides."""
    
    # Model defaults
    model_defaults: Dict[str, Any] = field(default_factory=lambda: {
        'max_tokens': 1000,
        'temperature': 0.7,
        'cost_per_1k_tokens': 0.0,
        'rate_limit_per_minute': 1000,
        'timeout_seconds': 30
    })
    
    # NLP processing parameters
    nlp_params: Dict[str, Any] = field(default_factory=lambda: {
        'sentence_transformer_model': 'all-MiniLM-L6-v2',
        'clustering_threshold': 0.7,
        'anomaly_threshold': 0.8,
        'max_cluster_size': 100,
        'min_cluster_size': 5
    })
    
    # ML/RL parameters
    ml_params: Dict[str, Any] = field(default_factory=lambda: {
        'state_vector_size': 10,
        'action_space_size': 50,
        'learning_rate': 0.001,
        'batch_size': 32,
        'memory_size': 10000,
        'epsilon_start': 1.0,
        'epsilon_end': 0.01,
        'epsilon_decay': 0.995,
        'discount_factor': 0.99
    })
    
    # Embedding parameters
    embedding_params: Dict[str, Any] = field(default_factory=lambda: {
        'default_dimension': 384,
        'hash_modulo': 1000,
        'openai_model': 'text-embedding-3-small',
        'max_batch_size': 100,
        'similarity_threshold': 0.7,
        'art_threshold': 0.85,  # Adaptive Resonance Theory threshold
        'art_vigilance': 0.9,   # ART vigilance parameter
        'art_learning_rate': 0.1
    })
    
    # Performance and caching
    performance_params: Dict[str, Any] = field(default_factory=lambda: {
        'cache_size': 500,  # Reduced from 1000
        'max_memory_usage_mb': 1024,  # Reduced from 2048
        'enable_gpu': False,  # Disabled for faster startup
        'max_concurrent_requests': 5,  # Reduced from 10
        'request_timeout': 15,  # Reduced from 30
        'model_loading_timeout': 10,  # New: timeout for model loading
        'enable_lazy_loading': True,  # New: enable lazy loading
        'preload_common_models': False,  # New: disable preloading
        'use_smaller_models': True,  # New: prefer smaller models
        'max_tokens_default': 300,  # New: smaller default token limit
        'enable_model_caching': True,  # New: enable model caching
        'cache_cleanup_interval': 300  # New: cleanup cache every 5 minutes
    })
    
    # HuggingFace specific parameters
    huggingface_params: Dict[str, Any] = field(default_factory=lambda: {
        'default_models_per_task': 10,
        'max_models_per_task': 50,
        'include_model_descriptions': True,
        'description_max_length': 500,
        'filter_private_models': True,
        'filter_gated_models': False,
        'sort_by': 'downloads',  # 'downloads', 'updated', 'created'
        'download_threshold': 100  # Minimum downloads to include model
    })
    
    # Logging configuration
    logging_params: Dict[str, Any] = field(default_factory=lambda: {
        'log_level': 'INFO',
        'max_log_size_mb': 100,
        'backup_count': 5,
        'enable_file_logging': True,
        'enable_console_logging': True
    })
    
    def __post_init__(self):
        """Load configuration from environment variables and config files."""
        self._load_from_env()
        self._load_from_config_file()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Model defaults from env
        if os.getenv('SAGAMU_MAX_TOKENS'):
            self.model_defaults['max_tokens'] = int(os.getenv('SAGAMU_MAX_TOKENS'))
        if os.getenv('SAGAMU_TEMPERATURE'):
            self.model_defaults['temperature'] = float(os.getenv('SAGAMU_TEMPERATURE'))
        
        # Performance from env
        if os.getenv('SAGAMU_MAX_MEMORY_MB'):
            self.performance_params['max_memory_usage_mb'] = int(os.getenv('SAGAMU_MAX_MEMORY_MB'))
        if os.getenv('SAGAMU_ENABLE_GPU'):
            self.performance_params['enable_gpu'] = os.getenv('SAGAMU_ENABLE_GPU').lower() == 'true'
        
        # HuggingFace from env
        if os.getenv('SAGAMU_HF_MODELS_PER_TASK'):
            self.huggingface_params['default_models_per_task'] = int(os.getenv('SAGAMU_HF_MODELS_PER_TASK'))
    
    def _load_from_config_file(self):
        """Load configuration from config file if it exists."""
        config_path = Path('config') / 'system_config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    
                # Update dictionaries with config file values
                for key, value in config_data.items():
                    if hasattr(self, key) and isinstance(getattr(self, key), dict):
                        getattr(self, key).update(value)
                        
            except Exception as e:
                print(f"⚠️ Error loading config file: {e}")
    
    def get_model_default(self, key: str, default: Any = None) -> Any:
        """Get a model default value."""
        return self.model_defaults.get(key, default)
    
    def get_nlp_param(self, key: str, default: Any = None) -> Any:
        """Get an NLP parameter."""
        return self.nlp_params.get(key, default)
    
    def get_ml_param(self, key: str, default: Any = None) -> Any:
        """Get an ML parameter."""
        return self.ml_params.get(key, default)
    
    def get_embedding_param(self, key: str, default: Any = None) -> Any:
        """Get an embedding parameter."""
        return self.embedding_params.get(key, default)
    
    def get_performance_param(self, key: str, default: Any = None) -> Any:
        """Get a performance parameter."""
        return self.performance_params.get(key, default)
    
    def get_huggingface_param(self, key: str, default: Any = None) -> Any:
        """Get a HuggingFace parameter."""
        return self.huggingface_params.get(key, default)
    
    def get_logging_param(self, key: str, default: Any = None) -> Any:
        """Get a logging parameter."""
        return self.logging_params.get(key, default)
    
    def get_system_param(self, key: str, default: Any = None) -> Any:
        """Get a system parameter (alias for convenience)."""
        # Check in multiple parameter dictionaries for backward compatibility
        if key in self.performance_params:
            return self.performance_params[key]
        elif key in self.logging_params:
            return self.logging_params[key]
        elif key in self.model_defaults:
            return self.model_defaults[key]
        else:
            return default
    
    def get_decision_param(self, key: str, default: Any = None) -> Any:
        """Get a decision parameter."""
        # Support nested key access with dot notation
        keys = key.split('.')
        value = self.embedding_params  # Default to embedding params for decision-related stuff
        
        # Add decision-specific parameters
        decision_params = {
            'weights': {
                'criticality': 100,
                'reliability': 50,
                'cost_efficiency': 30,
                'latency': 20,
                'success_rate': 40,
                'ml_confidence': 25
            },
            'anomaly_penalty_multiplier': 10,
            'utility_threshold': 0.0,
            'real_options': {
                'option_value_weight': 0.3,
                'volatility_factor': 0.2,
                'time_to_expiry': 1.0,
                'risk_free_rate': 0.05,
                'backup_option_cost': 0.1,
                'option_exercise_threshold': 0.7
            },
            'delegation': {
                'max_delegation_depth': 3,
                'delegation_confidence_threshold': 0.8,
                'subtask_cost_multiplier': 0.5,
                'delegation_timeout': 60,
                'specialization_bonus': 0.2
            },
            'recursion': {
                'max_recursion_depth': 5,
                'recursion_cost_multiplier': 0.3,
                'base_case_threshold': 0.1,
                'recursion_timeout': 120,
                'memory_limit': 1000
            }
        }
        
        value = decision_params
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_reputation_param(self, key: str, default: Any = None) -> Any:
        """Get a reputation parameter."""
        reputation_params = {
            'initial_reliability': 0.9,
            'initial_success_rate': 0.9,
            'initial_cost_efficiency': 1.0,
            'success_rate_alpha': 0.9,
            'success_rate_beta': 0.1,
            'reliability_success_increment': 0.1,
            'reliability_failure_decrement': 0.3,
            'min_reliability': 0.1,
            'max_reliability': 0.99,
            'latency_weight': 1000
        }
        return reputation_params.get(key, default)
    
    def get_category_models(self, category: str) -> List[str]:
        """Get models for a specific category - OPTIMIZED FOR SPEED."""
        category_models = {
            'general_purpose': ['fast_general', 'ultra_fast_general', 'fast_text_generator', 'general_assistant', 'phi3_general', 'mistral_general', 'llama3_general', 'openai_gpt3'],
            'code_generation': ['code_generator', 'codellama_code', 'deepseek_code', 'starcoder_code', 'wizardcoder_code', 'phi3_code'],
            'creative_writing': ['creative_writer', 'storyteller', 'fast_text_generator', 'llama3_general', 'mistral_general'],
            'analysis_research': ['fast_qa', 'analyst', 'researcher', 'openai_gpt3', 'llama3_general', 'mistral_general'],
            'medical_health': ['fast_qa', 'medical_advisor', 'clinical_assistant', 'llama3_general'],
            'financial_business': ['fast_financial', 'financial_advisor', 'business_analyst', 'llama3_general'],
            'scientific_technical': ['scientist', 'technical_writer', 'qwen_general', 'llama3_general'],
            'translation': ['fast_translation', 'fast_multilingual'],
            'sentiment_analysis': ['fast_sentiment', 'fast_financial'],
            'embeddings': ['fast_embeddings', 'fast_multilingual'],
            'general_qa': ['fast_general', 'ultra_fast_general', 'fast_text_generator', 'general_assistant', 'phi3_general']
        }
        return category_models.get(category, ['fast_general', 'ultra_fast_general', 'general_assistant', 'phi3_general', 'mistral_general', 'llama3_general'])
    
    def get_task_info(self, model_name: str) -> Dict[str, Any]:
        """Get task information for a model."""
        task_info = {
            'openai_general': {
                'task': 'Answer general knowledge questions',
                'criticality': 0.8,
                'output_variable': 'information_output',
                'needs_review': False,
                'type': 'explanation'
            },
            'openai_factual': {
                'task': 'Answer factual and knowledge-based questions',
                'criticality': 0.9,
                'output_variable': 'factual_output',
                'needs_review': False,
                'type': 'factual'
            },
            'llama3_general': {
                'task': 'Answer general knowledge questions',
                'criticality': 0.7,
                'output_variable': 'information_output',
                'needs_review': False,
                'type': 'explanation'
            },
            'creative_writer': {
                'task': 'Write creative content',
                'criticality': 0.5,
                'output_variable': 'creative_output',
                'needs_review': False,
                'type': 'creative_writing'
            },
            'code_generator': {
                'task': 'Generate code',
                'criticality': 0.8,
                'output_variable': 'code_output',
                'needs_review': True,
                'type': 'code_generation'
            },
            'analyst': {
                'task': 'Analyze and provide insights',
                'criticality': 0.7,
                'output_variable': 'analysis_output',
                'needs_review': False,
                'type': 'analysis'
            },
            'medical_advisor': {
                'task': 'Provide medical information',
                'criticality': 0.9,
                'output_variable': 'medical_output',
                'needs_review': True,
                'type': 'medical'
            },
            'financial_advisor': {
                'task': 'Provide financial advice',
                'criticality': 0.8,
                'output_variable': 'financial_output',
                'needs_review': True,
                'type': 'financial'
            },
            'scientist': {
                'task': 'Provide scientific analysis',
                'criticality': 0.8,
                'output_variable': 'scientific_output',
                'needs_review': True,
                'type': 'scientific'
            }
        }
        return task_info.get(model_name, {
            'task': 'General assistance',
            'criticality': 0.5,
            'output_variable': 'general_output',
            'needs_review': False,
            'type': 'general'
        })
    
    def get_rl_param(self, key: str, default: Any = None) -> Any:
        """Get a reinforcement learning parameter."""
        rl_params = {
            'learning_rate': 0.001,
            'epsilon': 0.1,
            'memory_size': 10000,
            'discount_factor': 0.99,
            'network_layers': [128, 64],
            'batch_size': 32
        }
        return rl_params.get(key, default)
    
    def get_ml_param(self, key: str, default: Any = None) -> Any:
        """Get a machine learning parameter."""
        ml_params = {
            'state_vector_size': 10,
            'clustering_n_clusters': 5,
            'clustering_random_state': 42,
            'anomaly_contamination': 0.1,
            'anomaly_random_state': 42,
            'classifier_n_neighbors': 3
        }
        return ml_params.get(key, default)
    
    def get_novel_ai_param(self, key: str, default: Any = None) -> Any:
        """Get a novel AI parameter."""
        # Support nested key access with dot notation
        keys = key.split('.')
        
        # Define novel AI parameters
        novel_ai_params = {
            'adaptive_learning': {
                'feedback_memory_size': 1000,
                'learning_rate': 0.1,
                'adaptation_threshold': 0.8,
                'feedback_weight': 0.3,
                'update_frequency': 10
            },
            'collaborative_ai': {
                'max_collaborators': 5,
                'collaboration_threshold': 0.7,
                'knowledge_sharing_rate': 0.2,
                'cross_domain_weight': 0.4,
                'collaboration_timeout': 30
            },
            'knowledge_graph': {
                'max_nodes': 10000,
                'embedding_dimension': 384,
                'relationship_types': ['similar', 'related', 'opposite', 'contains'],
                'confidence_threshold': 0.6,
                'update_frequency': 100
            },
            'semantic_memory': {
                'memory_size': 5000,
                'importance_threshold': 0.5,
                'decay_rate': 0.01,
                'consolidation_frequency': 50,
                'retrieval_limit': 10
            },
            'dynamic_optimization': {
                'priority_weight': 0.4,
                'cost_weight': 0.3,
                'latency_weight': 0.3,
                'optimization_frequency': 20,
                'resource_threshold': 0.8
            },
            'human_ai_collaboration': {
                'max_session_time': 3600,
                'expert_weight': 0.6,
                'ai_weight': 0.4,
                'consensus_threshold': 0.7,
                'collaboration_modes': ['advisory', 'collaborative', 'autonomous']
            },
            'security': {
                'privacy_level': 'medium',
                'differential_privacy_epsilon': 1.0,
                'encryption_strength': 'strong',
                'audit_frequency': 100,
                'security_threshold': 0.9
            }
        }
        
        value = novel_ai_params
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def save_to_file(self, filepath: Optional[str] = None):
        """Save current configuration to file."""
        if filepath is None:
            filepath = 'config/system_config.json'
        
        config_data = {
            'model_defaults': self.model_defaults,
            'nlp_params': self.nlp_params,
            'ml_params': self.ml_params,
            'embedding_params': self.embedding_params,
            'performance_params': self.performance_params,
            'huggingface_params': self.huggingface_params,
            'logging_params': self.logging_params
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def update_param(self, category: str, key: str, value: Any):
        """Update a specific parameter."""
        if hasattr(self, category):
            param_dict = getattr(self, category)
            if isinstance(param_dict, dict):
                param_dict[key] = value
            else:
                raise ValueError(f"Category {category} is not a dictionary")
        else:
            raise ValueError(f"Category {category} not found")

# Create default system configuration
DEFAULT_SYSTEM_CONFIG = SystemConfig()

# Convenience function to get the global config
def get_system_config() -> SystemConfig:
    """Get the global system configuration."""
    return DEFAULT_SYSTEM_CONFIG 
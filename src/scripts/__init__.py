"""
HFOrchestra - A comprehensive HuggingFace model orchestration system.

This package provides a modular framework for discovering, evaluating, and managing
HuggingFace models with advanced features including:
- Model discovery and evaluation
- PE header analysis and malware detection
- Dynamic model configuration
- Multi-provider LLM orchestration
- Security monitoring with ATLAS framework
- Performance optimization and caching

Author: Sagamu Team
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Sagamu Team"
__description__ = "Advanced HuggingFace Model Orchestration System"

# Core imports
from .core import (
    HuggingFaceOrchestrator, 
    OrchestrationResult,
    UniversalTaskProcessor,
    TaskResult,
    LLMProvider, 
    OpenAIProvider, 
    AnthropicProvider, 
    GeminiProvider,
    HuggingFaceProvider,
    ModelConfig,
    create_provider
)

# Security and monitoring
from .security.atlas_detector import ATLASThreatDetector
from .monitoring.tree_monitor import EnhancedTreeMonitor, DecisionMetrics

# Model management
from .models.discovery import EnhancedHuggingFaceDiscovery, SmartModelSelector
from .models.database import HuggingFaceModelDatabase, ModelMetrics
from .models.selector import HybridModelSelector

# Task processing - commented out missing modules
# from .tasks.processor import UniversalTaskProcessor
# from .tasks.delegation import DelegationManager, DelegationTask
# from .tasks.recursive import RecursiveTaskManager, RecursiveTask

# Configuration and utilities
# from .config.settings import SettingsLoader
# from .config.model_config import ModelConfig, DynamicModelConfigGenerator
from .utils.folder_manager import FolderManager
from .utils.performance import PerformanceMonitor
# from .utils.performance import AdaptiveRateLimiter

# PE Analysis
from .analysis.pe_extractor import CompletePEHeaderExtractor
from .analysis.malware_detector import PEAnalyzer

# CLI Interface - commented out missing module
# from .interface.cli import CLIInterface

__all__ = [
    # Core
    'HuggingFaceOrchestrator',
    
    # Providers
    'LLMProvider', 'OpenAIProvider', 'AnthropicProvider', 'GeminiProvider',
    'HuggingFaceProvider',
    
    # Security
    'ATLASThreatDetector',
    
    # Monitoring
    'EnhancedTreeMonitor', 'DecisionMetrics',
    
    # Models
    'EnhancedHuggingFaceDiscovery', 'SmartModelSelector',
    'HuggingFaceModelDatabase', 'ModelMetrics', 'HybridModelSelector',
    
    # Utilities
    'FolderManager', 'PerformanceMonitor',
    
    # Analysis
    'CompletePEHeaderExtractor', 'PEAnalyzer',
] 
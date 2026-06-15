"""
ML Integration module that seamlessly integrates the machine learning model selection
system with the existing HFOrchestra infrastructure.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .ml_model_selector import MLModelSelector, TaskFeatures
from .ml_enhanced_orchestrator import MLEnhancedOrchestrator
from .ensemble_model_selector import EnsembleModelSelector, EnsembleMethod
from .ml_training_manager import MLTrainingManager, ModelTrainingConfig
from .enhanced_model_selector import EnhancedModelSelector, SelectionStrategy
from .task_handler import TaskHandlerResult

logger = logging.getLogger(__name__)

@dataclass
class MLIntegrationConfig:
    """Configuration for ML integration."""
    enable_ml_selection: bool = True
    enable_ensemble_methods: bool = True
    enable_learning: bool = True
    default_ensemble_method: EnsembleMethod = EnsembleMethod.WEIGHTED_VOTING
    training_config: Optional[ModelTrainingConfig] = None
    fallback_to_enhanced: bool = True
    performance_tracking: bool = True

class MLIntegrationManager:
    """
    Main integration manager that coordinates all ML-based model selection components
    and provides a unified interface to the existing HFOrchestra system.
    """
    
    def __init__(self, config: Optional[MLIntegrationConfig] = None):
        self.config = config or MLIntegrationConfig()
        
        # Initialize components
        self.ml_selector = MLModelSelector()
        self.ml_orchestrator = MLEnhancedOrchestrator()
        self.ensemble_selector = EnsembleModelSelector()
        self.training_manager = MLTrainingManager(
            config=self.config.training_config or ModelTrainingConfig()
        )
        self.enhanced_selector = EnhancedModelSelector()
        
        # Performance tracking
        self.performance_stats = {
            'total_requests': 0,
            'ml_selections': 0,
            'ensemble_selections': 0,
            'fallback_selections': 0,
            'successful_selections': 0,
            'average_confidence': 0.0,
            'average_execution_time': 0.0
        }
        
        logger.info("ML Integration Manager initialized")
    
    async def select_best_model(self, 
                              task_name: str, 
                              prompt: str, 
                              selection_strategy: str = "ml_enhanced",
                              **kwargs) -> Dict[str, Any]:
        """
        Main entry point for ML-enhanced model selection.
        """
        start_time = time.time()
        self.performance_stats['total_requests'] += 1
        
        try:
            logger.info(f"🤖 [ML-INTEGRATION] Processing model selection for '{task_name}'")
            
            # Determine selection approach
            if self.config.enable_ml_selection and selection_strategy.startswith('ml_'):
                result = await self._ml_based_selection(task_name, prompt, selection_strategy, **kwargs)
            elif self.config.enable_ensemble_methods and selection_strategy in ['ensemble', 'voting', 'consensus']:
                result = await self._ensemble_based_selection(task_name, prompt, selection_strategy, **kwargs)
            elif self.config.fallback_to_enhanced:
                result = await self._enhanced_fallback_selection(task_name, prompt, selection_strategy, **kwargs)
            else:
                result = await self._basic_fallback_selection(task_name, prompt, **kwargs)
            
            # Update performance stats
            execution_time = time.time() - start_time
            self._update_performance_stats(result, execution_time)
            
            # Record performance for learning
            if self.config.performance_tracking and result.get('success', False):
                await self._record_performance_for_learning(task_name, prompt, result, execution_time, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in ML model selection: {e}")
            return await self._error_fallback_selection(task_name, prompt, str(e))
    
    async def _ml_based_selection(self, 
                                task_name: str, 
                                prompt: str, 
                                selection_strategy: str,
                                **kwargs) -> Dict[str, Any]:
        """ML-based model selection."""
        try:
            self.performance_stats['ml_selections'] += 1
            
            # Use ML-enhanced orchestrator
            result = await self.ml_orchestrator.process_task_with_ml_selection(
                task_name, prompt, selection_strategy, **kwargs
            )
            
            return {
                'success': result.success,
                'selected_model': result.selected_model,
                'confidence_score': result.confidence_score,
                'execution_time': result.execution_time,
                'reasoning': result.ml_reasoning,
                'performance_metrics': result.performance_metrics,
                'method': 'ml_enhanced',
                'content': result.content,
                'error_message': result.error_message
            }
            
        except Exception as e:
            logger.error(f"Error in ML-based selection: {e}")
            raise
    
    async def _ensemble_based_selection(self, 
                                      task_name: str, 
                                      prompt: str, 
                                      selection_strategy: str,
                                      **kwargs) -> Dict[str, Any]:
        """Ensemble-based model selection."""
        try:
            self.performance_stats['ensemble_selections'] += 1
            
            # Map strategy to ensemble method
            ensemble_method_map = {
                'ensemble': EnsembleMethod.WEIGHTED_VOTING,
                'voting': EnsembleMethod.VOTING,
                'consensus': EnsembleMethod.CONSENSUS,
                'stacking': EnsembleMethod.STACKING,
                'adaptive': EnsembleMethod.ADAPTIVE
            }
            
            ensemble_method = ensemble_method_map.get(selection_strategy, self.config.default_ensemble_method)
            
            # Get available models
            available_models = await self._get_available_models(task_name, **kwargs)
            
            # Use ensemble selector
            ensemble_result = self.ensemble_selector.select_best_model_ensemble(
                task_name, prompt, available_models, ensemble_method, **kwargs
            )
            
            # Process with selected model
            task_result = await self._process_with_model(task_name, prompt, ensemble_result.selected_model, **kwargs)
            
            return {
                'success': task_result.success,
                'selected_model': ensemble_result.selected_model,
                'confidence_score': ensemble_result.confidence_score,
                'execution_time': time.time() - time.time(),  # Will be updated by caller
                'reasoning': ensemble_result.reasoning,
                'performance_metrics': {
                    'consensus_strength': ensemble_result.consensus_strength,
                    'ensemble_scores': ensemble_result.ensemble_scores
                },
                'method': f'ensemble_{ensemble_method.value}',
                'content': task_result.content,
                'error_message': task_result.error_message,
                'ensemble_details': {
                    'method': ensemble_method.value,
                    'individual_results': len(ensemble_result.individual_results),
                    'consensus_strength': ensemble_result.consensus_strength
                }
            }
            
        except Exception as e:
            logger.error(f"Error in ensemble-based selection: {e}")
            raise
    
    async def _enhanced_fallback_selection(self, 
                                         task_name: str, 
                                         prompt: str, 
                                         selection_strategy: str,
                                         **kwargs) -> Dict[str, Any]:
        """Fallback to enhanced model selector."""
        try:
            self.performance_stats['fallback_selections'] += 1
            
            # Map strategy to enhanced selector strategy
            strategy_map = {
                'hyperparameter_tuning': SelectionStrategy.HYPERPARAMETER_TUNING,
                'cross_validation': SelectionStrategy.CROSS_VALIDATION,
                'ensemble_methods': SelectionStrategy.ENSEMBLE_METHODS,
                'multi_objective': SelectionStrategy.MULTI_OBJECTIVE,
                'bayesian_optimization': SelectionStrategy.BAYESIAN_OPTIMIZATION,
                'meta_learning': SelectionStrategy.META_LEARNING
            }
            
            strategy = strategy_map.get(selection_strategy, SelectionStrategy.MULTI_OBJECTIVE)
            
            # Use enhanced selector
            selection_result = self.enhanced_selector.select_best_model(
                task_name, prompt, strategy=strategy, **kwargs
            )
            
            # Process with selected model
            task_result = await self._process_with_model(
                task_name, prompt, selection_result.selected_model, **kwargs
            )
            
            return {
                'success': task_result.success,
                'selected_model': selection_result.selected_model,
                'confidence_score': getattr(selection_result, 'confidence_score', 0.7),
                'execution_time': time.time() - time.time(),  # Will be updated by caller
                'reasoning': f"Enhanced selector with {strategy.value}",
                'performance_metrics': {},
                'method': f'enhanced_{strategy.value}',
                'content': task_result.content,
                'error_message': task_result.error_message
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced fallback selection: {e}")
            raise
    
    async def _basic_fallback_selection(self, 
                                      task_name: str, 
                                      prompt: str, 
                                      **kwargs) -> Dict[str, Any]:
        """Basic fallback selection."""
        try:
            # Simple rule-based selection
            fallback_models = {
                'text-generation': 'gpt2',
                'text-classification': 'distilbert-base-uncased',
                'summarization': 'facebook/bart-large-cnn',
                'translation': 'Helsinki-NLP/opus-mt-en-es',
                'question-answering': 'distilbert-base-cased-distilled-squad',
            }
            
            selected_model = fallback_models.get(task_name, 'gpt2')
            
            # Process with selected model
            task_result = await self._process_with_model(task_name, prompt, selected_model, **kwargs)
            
            return {
                'success': task_result.success,
                'selected_model': selected_model,
                'confidence_score': 0.5,
                'execution_time': time.time() - time.time(),
                'reasoning': f"Basic fallback for {task_name}",
                'performance_metrics': {},
                'method': 'basic_fallback',
                'content': task_result.content,
                'error_message': task_result.error_message
            }
            
        except Exception as e:
            logger.error(f"Error in basic fallback selection: {e}")
            raise
    
    async def _error_fallback_selection(self, 
                                      task_name: str, 
                                      prompt: str, 
                                      error_message: str) -> Dict[str, Any]:
        """Error fallback selection."""
        return {
            'success': False,
            'selected_model': 'gpt2',
            'confidence_score': 0.0,
            'execution_time': 0.0,
            'reasoning': f"Error fallback: {error_message}",
            'performance_metrics': {},
            'method': 'error_fallback',
            'content': f"❌ Error in model selection: {error_message}",
            'error_message': error_message
        }
    
    async def _get_available_models(self, task_name: str, **kwargs) -> List[str]:
        """Get available models for a task."""
        try:
            # Use enhanced selector to get model candidates
            selection_result = self.enhanced_selector.select_best_model(
                task_name, "", SelectionStrategy.MULTI_OBJECTIVE, max_candidates=20
            )
            
            available_models = []
            if hasattr(selection_result, 'selected_model') and selection_result.selected_model:
                available_models.append(selection_result.selected_model)
            
            if hasattr(selection_result, 'alternative_models'):
                for alt_model in selection_result.alternative_models:
                    if isinstance(alt_model, tuple):
                        available_models.append(alt_model[0])
                    else:
                        available_models.append(alt_model)
            
            # Fallback models if none found
            if not available_models:
                fallback_models = {
                    'text-generation': ['gpt2', 'gpt2-medium', 'distilgpt2'],
                    'text-classification': ['distilbert-base-uncased', 'bert-base-uncased'],
                    'summarization': ['facebook/bart-large-cnn', 't5-base'],
                    'translation': ['Helsinki-NLP/opus-mt-en-es', 't5-base'],
                    'question-answering': ['distilbert-base-cased-distilled-squad', 'bert-base-cased'],
                }
                available_models = fallback_models.get(task_name, ['gpt2'])
            
            return available_models[:10]  # Limit to top 10
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return ['gpt2']  # Ultimate fallback
    
    async def _process_with_model(self, 
                                task_name: str, 
                                prompt: str, 
                                selected_model: str,
                                **kwargs) -> TaskHandlerResult:
        """Process task with selected model."""
        try:
            # Use existing task handler
            from .task_handler import ComprehensiveTaskHandler
            task_handler = ComprehensiveTaskHandler()
            
            # Process with the specific model
            result = await task_handler._process_task_with_model(
                task_name, 
                prompt, 
                {'model_id': selected_model}, 
                **kwargs
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing with model {selected_model}: {e}")
            return TaskHandlerResult(
                success=False,
                content=f"Error processing with {selected_model}: {str(e)}",
                error_message=str(e)
            )
    
    def _update_performance_stats(self, result: Dict[str, Any], execution_time: float):
        """Update performance statistics."""
        if result.get('success', False):
            self.performance_stats['successful_selections'] += 1
        
        # Update average confidence
        current_avg = self.performance_stats['average_confidence']
        total_requests = self.performance_stats['total_requests']
        new_confidence = result.get('confidence_score', 0.0)
        
        self.performance_stats['average_confidence'] = (
            (current_avg * (total_requests - 1) + new_confidence) / total_requests
        )
        
        # Update average execution time
        current_avg_time = self.performance_stats['average_execution_time']
        self.performance_stats['average_execution_time'] = (
            (current_avg_time * (total_requests - 1) + execution_time) / total_requests
        )
    
    async def _record_performance_for_learning(self, 
                                             task_name: str, 
                                             prompt: str, 
                                             result: Dict[str, Any],
                                             execution_time: float,
                                             **kwargs):
        """Record performance data for ML learning."""
        try:
            if not self.config.enable_learning:
                return
            
            # Extract task features
            task_features = self.ml_selector._extract_task_features(task_name, prompt, **kwargs)
            
            # Calculate performance metrics
            performance_metrics = result.get('performance_metrics', {})
            accuracy_score = performance_metrics.get('accuracy', 0.8)
            quality_score = performance_metrics.get('quality', 0.8)
            resource_usage = performance_metrics.get('resource_usage', 0.5)
            cost = performance_metrics.get('cost', 0.1)
            success_rate = 1.0 if result.get('success', False) else 0.0
            
            # Record in training manager
            self.training_manager.collect_training_data(
                task_type=task_name,
                prompt=prompt,
                selected_model=result.get('selected_model', 'unknown'),
                actual_performance={
                    'accuracy': accuracy_score,
                    'quality': quality_score,
                    'execution_time': execution_time,
                    'resource_usage': resource_usage,
                    'cost': cost,
                    'success_rate': success_rate
                },
                task_features=task_features
            )
            
            logger.debug(f"Recorded performance data for {task_name} with {result.get('selected_model')}")
            
        except Exception as e:
            logger.error(f"Error recording performance for learning: {e}")
    
    def get_integration_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics from all ML components."""
        return {
            'performance_stats': self.performance_stats,
            'ml_analytics': self.ml_selector.get_performance_analytics(),
            'ensemble_analytics': self.ensemble_selector.get_ensemble_analytics(),
            'training_analytics': self.training_manager.get_training_analytics(),
            'config': {
                'enable_ml_selection': self.config.enable_ml_selection,
                'enable_ensemble_methods': self.config.enable_ensemble_methods,
                'enable_learning': self.config.enable_learning,
                'default_ensemble_method': self.config.default_ensemble_method.value,
                'fallback_to_enhanced': self.config.fallback_to_enhanced,
                'performance_tracking': self.config.performance_tracking
            }
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update integration configuration."""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")
    
    def force_retrain_models(self):
        """Force retraining of all ML models."""
        try:
            self.training_manager.force_retrain()
            logger.info("Forced model retraining initiated")
        except Exception as e:
            logger.error(f"Error forcing model retraining: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old training data."""
        try:
            self.training_manager.cleanup_old_data(days_to_keep)
            logger.info(f"Cleaned up data older than {days_to_keep} days")
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def shutdown(self):
        """Gracefully shutdown the ML integration manager."""
        try:
            self.training_manager.stop_data_collection()
            logger.info("ML Integration Manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global instance for easy access
ml_integration_manager = None

def get_ml_integration_manager(config: Optional[MLIntegrationConfig] = None) -> MLIntegrationManager:
    """Get or create the global ML integration manager instance."""
    global ml_integration_manager
    
    if ml_integration_manager is None:
        ml_integration_manager = MLIntegrationManager(config)
    
    return ml_integration_manager

def initialize_ml_integration(config: Optional[MLIntegrationConfig] = None) -> MLIntegrationManager:
    """Initialize the ML integration system."""
    global ml_integration_manager
    
    ml_integration_manager = MLIntegrationManager(config)
    logger.info("ML Integration system initialized")
    
    return ml_integration_manager

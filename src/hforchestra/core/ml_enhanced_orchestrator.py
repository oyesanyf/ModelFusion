"""
ML-Enhanced Orchestrator that integrates machine learning model selection
with the existing HFOrchestra system.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .ml_model_selector import MLModelSelector, TaskFeatures, ModelSelectionResult
from .enhanced_model_selector import EnhancedModelSelector, SelectionStrategy
from .task_handler import TaskHandlerResult

logger = logging.getLogger(__name__)

@dataclass
class MLOrchestrationResult:
    """Result from ML-enhanced orchestration."""
    success: bool
    content: str
    selected_model: str
    confidence_score: float
    execution_time: float
    performance_metrics: Dict[str, float]
    ml_reasoning: str
    error_message: Optional[str] = None

class MLEnhancedOrchestrator:
    """
    Enhanced orchestrator that uses machine learning to improve model selection
    and learns from performance feedback.
    """
    
    def __init__(self, model_selector: Optional[EnsembleModelSelector] = None, 
                 knowledge_db: str = None):
        
        self.model_selector = model_selector or EnsembleModelSelector()
        
        # Determine project root and default DB path
        # File is in src/hforchestra/core/ml_enhanced_orchestrator.py
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        
        if knowledge_db is None:
            self.knowledge_db = str(project_root / "db" / "ml_training.db")
        else:
            path_obj = Path(knowledge_db)
            if not path_obj.is_absolute():
                self.knowledge_db = str(project_root / knowledge_db)
            else:
                self.knowledge_db = knowledge_db
                
        self.enhanced_selector = EnhancedModelSelector()
        self.performance_tracker = {}
        self.learning_enabled = True
        
    async def process_task_with_ml_selection(self, 
                                           task_name: str, 
                                           prompt: str, 
                                           selection_strategy: str = "ml_enhanced",
                                           **kwargs) -> MLOrchestrationResult:
        """
        Process a task using ML-enhanced model selection.
        """
        start_time = time.time()
        
        try:
            logger.info(f"🤖 [ML-ENHANCED] Processing task '{task_name}' with ML selection")
            
            # Step 1: Get available models using existing enhanced selector
            available_models = await self._get_available_models(task_name, selection_strategy)
            
            if not available_models:
                return MLOrchestrationResult(
                    success=False,
                    content="❌ No suitable models found for this task",
                    selected_model="",
                    confidence_score=0.0,
                    execution_time=time.time() - start_time,
                    performance_metrics={},
                    ml_reasoning="No models available",
                    error_message="No models found"
                )
            
            # Step 2: Use ML selector to choose the best model
            ml_result = self.ml_selector.select_best_model(
                task_name, 
                prompt, 
                available_models, 
                **kwargs
            )
            
            selected_model = ml_result.selected_model
            confidence_score = ml_result.confidence_score
            
            logger.info(f"🎯 [ML] Selected model: {selected_model} (confidence: {confidence_score:.2f})")
            
            # Step 3: Process the task with the selected model
            task_result = await self._process_with_selected_model(
                task_name, 
                prompt, 
                selected_model, 
                **kwargs
            )
            
            # Step 4: Record performance for learning
            if self.learning_enabled and task_result.success:
                await self._record_performance_feedback(
                    task_name, 
                    prompt, 
                    selected_model, 
                    task_result, 
                    time.time() - start_time,
                    **kwargs
                )
            
            # Step 5: Build comprehensive response
            content = self._build_ml_response(
                task_name, 
                prompt, 
                selected_model, 
                ml_result, 
                task_result
            )
            
            execution_time = time.time() - start_time
            
            return MLOrchestrationResult(
                success=task_result.success,
                content=content,
                selected_model=selected_model,
                confidence_score=confidence_score,
                execution_time=execution_time,
                performance_metrics={
                    'accuracy': task_result.accuracy_score if hasattr(task_result, 'accuracy_score') else 0.8,
                    'quality': task_result.quality_score if hasattr(task_result, 'quality_score') else 0.8,
                    'execution_time': execution_time,
                    'resource_usage': 0.5,  # Placeholder
                    'cost': 0.1,  # Placeholder
                    'success_rate': 1.0 if task_result.success else 0.0
                },
                ml_reasoning=ml_result.reasoning,
                error_message=task_result.error_message if hasattr(task_result, 'error_message') else None
            )
            
        except Exception as e:
            logger.error(f"Error in ML-enhanced orchestration: {e}")
            return MLOrchestrationResult(
                success=False,
                content=f"❌ Error in ML-enhanced processing: {str(e)}",
                selected_model="",
                confidence_score=0.0,
                execution_time=time.time() - start_time,
                performance_metrics={},
                ml_reasoning="Error occurred",
                error_message=str(e)
            )
    
    async def _get_available_models(self, task_name: str, selection_strategy: str) -> List[str]:
        """Get available models for the task."""
        try:
            # Use existing enhanced selector to get model candidates
            strategy_map = {
                'ml_enhanced': SelectionStrategy.MULTI_OBJECTIVE,
                'hyperparameter_tuning': SelectionStrategy.HYPERPARAMETER_TUNING,
                'cross_validation': SelectionStrategy.CROSS_VALIDATION,
                'ensemble_methods': SelectionStrategy.ENSEMBLE_METHODS,
                'bayesian_optimization': SelectionStrategy.BAYESIAN_OPTIMIZATION,
                'meta_learning': SelectionStrategy.META_LEARNING
            }
            
            strategy = strategy_map.get(selection_strategy, SelectionStrategy.MULTI_OBJECTIVE)
            
            # Get selection result from enhanced selector
            selection_result = self.enhanced_selector.select_best_model(
                task_name, 
                "",  # Empty prompt for initial selection
                strategy=strategy,
                max_candidates=20
            )
            
            # Extract model IDs from the result
            available_models = []
            if hasattr(selection_result, 'selected_model') and selection_result.selected_model:
                available_models.append(selection_result.selected_model)
            
            if hasattr(selection_result, 'alternative_models'):
                for alt_model in selection_result.alternative_models:
                    if isinstance(alt_model, tuple):
                        available_models.append(alt_model[0])
                    else:
                        available_models.append(alt_model)
            
            # If no models from enhanced selector, use fallback
            if not available_models:
                available_models = self._get_fallback_models(task_name)
            
            return available_models[:10]  # Limit to top 10 models
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return self._get_fallback_models(task_name)
    
    def _get_fallback_models(self, task_name: str) -> List[str]:
        """Get fallback models for a task."""
        fallback_models = {
            'text-generation': ['gpt2', 'gpt2-medium', 'distilgpt2'],
            'text-classification': ['distilbert-base-uncased', 'bert-base-uncased'],
            'summarization': ['facebook/bart-large-cnn', 't5-base'],
            'translation': ['Helsinki-NLP/opus-mt-en-es', 't5-base'],
            'question-answering': ['distilbert-base-cased-distilled-squad', 'bert-base-cased'],
            'sentiment-analysis': ['nlptown/bert-base-multilingual-uncased-sentiment'],
            'named-entity-recognition': ['dbmdz/bert-large-cased-finetuned-conll03-english'],
            'fill-mask': ['bert-base-uncased', 'roberta-base'],
        }
        
        return fallback_models.get(task_name, ['gpt2'])
    
    async def _process_with_selected_model(self, 
                                         task_name: str, 
                                         prompt: str, 
                                         selected_model: str, 
                                         **kwargs) -> TaskHandlerResult:
        """Process the task with the selected model."""
        try:
            # Use existing task handler to process the task
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
            logger.error(f"Error processing with selected model: {e}")
            return TaskHandlerResult(
                success=False,
                content=f"Error processing with {selected_model}: {str(e)}",
                error_message=str(e)
            )
    
    async def _record_performance_feedback(self, 
                                         task_name: str, 
                                         prompt: str, 
                                         selected_model: str, 
                                         task_result: TaskHandlerResult, 
                                         execution_time: float,
                                         **kwargs):
        """Record performance feedback for ML learning."""
        try:
            # Extract task features
            task_features = self.ml_selector._extract_task_features(task_name, prompt, **kwargs)
            
            # Calculate performance metrics
            accuracy_score = self._calculate_accuracy_score(task_result)
            quality_score = self._calculate_quality_score(task_result)
            resource_usage = self._estimate_resource_usage(execution_time, selected_model)
            cost = self._estimate_cost(selected_model, execution_time)
            success_rate = 1.0 if task_result.success else 0.0
            
            # Record performance
            self.ml_selector.record_performance(
                model_id=selected_model,
                task_type=task_name,
                task_features=task_features,
                execution_time=execution_time,
                accuracy_score=accuracy_score,
                quality_score=quality_score,
                resource_usage=resource_usage,
                cost=cost,
                success_rate=success_rate
            )
            
            logger.info(f"📊 [ML] Recorded performance for {selected_model} on {task_name}")
            
        except Exception as e:
            logger.error(f"Error recording performance feedback: {e}")
    
    def _calculate_accuracy_score(self, task_result: TaskHandlerResult) -> float:
        """Calculate accuracy score from task result."""
        # Simple heuristic based on content length and success
        if not task_result.success:
            return 0.0
        
        # If content is substantial and successful, assume good accuracy
        content_length = len(task_result.content) if task_result.content else 0
        if content_length > 100:
            return 0.8 + min(0.2, content_length / 1000 * 0.2)
        else:
            return 0.6
    
    def _calculate_quality_score(self, task_result: TaskHandlerResult) -> float:
        """Calculate quality score from task result."""
        if not task_result.success:
            return 0.0
        
        # Simple quality heuristics
        content = task_result.content or ""
        quality_indicators = [
            'detailed', 'comprehensive', 'thorough', 'accurate', 'precise',
            'well-structured', 'clear', 'informative', 'helpful'
        ]
        
        quality_score = 0.5  # Base score
        
        # Check for quality indicators
        for indicator in quality_indicators:
            if indicator in content.lower():
                quality_score += 0.05
        
        # Length factor
        if len(content) > 200:
            quality_score += 0.1
        
        return min(1.0, quality_score)
    
    def _estimate_resource_usage(self, execution_time: float, model_id: str) -> float:
        """Estimate resource usage based on execution time and model."""
        # Simple heuristic based on execution time and model size
        base_usage = min(1.0, execution_time / 30.0)  # Normalize to 30 seconds
        
        # Model size factor
        large_models = ['gpt2-medium', 'bert-large', 'bart-large', 't5-large']
        if any(large_model in model_id for large_model in large_models):
            base_usage *= 1.5
        
        return min(1.0, base_usage)
    
    def _estimate_cost(self, model_id: str, execution_time: float) -> float:
        """Estimate cost based on model and execution time."""
        # Simple cost estimation
        base_cost = execution_time * 0.01  # $0.01 per second
        
        # Model cost factor
        expensive_models = ['gpt2-medium', 'bert-large', 'bart-large']
        if any(expensive_model in model_id for expensive_model in expensive_models):
            base_cost *= 2.0
        
        return base_cost
    
    def _build_ml_response(self, 
                          task_name: str, 
                          prompt: str, 
                          selected_model: str, 
                          ml_result: ModelSelectionResult, 
                          task_result: TaskHandlerResult) -> str:
        """Build comprehensive response with ML insights."""
        content_parts = []
        
        # Header
        content_parts.append("🤖 ML-Enhanced Model Selection Results")
        content_parts.append("=" * 50)
        content_parts.append("")
        
        # Task information
        content_parts.append(f"📋 Task: {task_name}")
        content_parts.append(f"💬 Input: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        content_parts.append("")
        
        # Model selection details
        content_parts.append("🎯 Model Selection:")
        content_parts.append(f"   Selected: {selected_model}")
        content_parts.append(f"   Confidence: {ml_result.confidence_score:.2f}")
        content_parts.append(f"   Reasoning: {ml_result.reasoning}")
        content_parts.append("")
        
        # Alternative models
        if ml_result.alternative_models:
            content_parts.append("🔄 Alternative Models:")
            for i, (model, score) in enumerate(ml_result.alternative_models[:3], 1):
                content_parts.append(f"   {i}. {model} (score: {score:.2f})")
            content_parts.append("")
        
        # Feature importance
        if ml_result.feature_importance:
            content_parts.append("📊 Key Selection Factors:")
            sorted_features = sorted(
                ml_result.feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            for feature, importance in sorted_features:
                content_parts.append(f"   • {feature}: {importance:.3f}")
            content_parts.append("")
        
        # Task result
        content_parts.append("📝 Task Result:")
        if task_result.success:
            content_parts.append("✅ Success")
            if task_result.content:
                content_parts.append("")
                content_parts.append(task_result.content)
        else:
            content_parts.append("❌ Failed")
            if task_result.error_message:
                content_parts.append(f"Error: {task_result.error_message}")
        
        return "\n".join(content_parts)
    
    def get_ml_analytics(self) -> Dict[str, Any]:
        """Get ML model selection analytics."""
        return self.ml_selector.get_performance_analytics()
    
    def enable_learning(self, enabled: bool = True):
        """Enable or disable learning from performance feedback."""
        self.learning_enabled = enabled
        logger.info(f"ML learning {'enabled' if enabled else 'disabled'}")
    
    def retrain_models(self):
        """Manually trigger model retraining."""
        try:
            self.ml_selector._train_models()
            logger.info("ML models retrained successfully")
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    async def batch_process_tasks(self, 
                                tasks: List[Tuple[str, str]], 
                                selection_strategy: str = "ml_enhanced",
                                **kwargs) -> List[MLOrchestrationResult]:
        """Process multiple tasks in batch for efficient learning."""
        results = []
        
        for task_name, prompt in tasks:
            result = await self.process_task_with_ml_selection(
                task_name, 
                prompt, 
                selection_strategy, 
                **kwargs
            )
            results.append(result)
            
            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)
        
        return results

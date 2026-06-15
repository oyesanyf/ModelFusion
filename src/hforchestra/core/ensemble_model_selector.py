"""
Ensemble Model Selector for robust and reliable model selection.

This module implements various ensemble methods to combine multiple model selection
strategies for more robust and reliable model choices.
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import Counter

from .ml_model_selector import MLModelSelector, ModelSelectionResult, TaskFeatures
from .enhanced_model_selector import EnhancedModelSelector, SelectionStrategy

logger = logging.getLogger(__name__)

class EnsembleMethod(Enum):
    """Available ensemble methods for model selection."""
    VOTING = "voting"
    WEIGHTED_VOTING = "weighted_voting"
    STACKING = "stacking"
    BAGGING = "bagging"
    BOOSTING = "boosting"
    CONSENSUS = "consensus"
    ADAPTIVE = "adaptive"

@dataclass
class EnsembleSelectionResult:
    """Result from ensemble model selection."""
    selected_model: str
    confidence_score: float
    ensemble_scores: Dict[str, float]
    individual_results: List[ModelSelectionResult]
    ensemble_method: EnsembleMethod
    consensus_strength: float
    reasoning: str
    feature_importance: Dict[str, float]

class EnsembleModelSelector:
    """
    Ensemble model selector that combines multiple selection strategies
    for more robust and reliable model selection.
    """
    
    def __init__(self, db_path: str = None):
        # Determine project root and default DB path
        # File is in src/hforchestra/core/ensemble_model_selector.py
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        
        # If db_path is not provided, use default location in project root
        if db_path is None:
            self.db_path = str(project_root / "db" / "ml_model_selector.db")
        else:
             # If provided path is relative, make it absolute relative to project root
            # unless it's already absolute
            path_obj = Path(db_path)
            if not path_obj.is_absolute():
                self.db_path = str(project_root / db_path)
            else:
                self.db_path = db_path
                
        self.ml_selector = MLModelSelector(self.db_path)
        self.enhanced_selector = EnhancedModelSelector()
        self.ensemble_weights = self._initialize_ensemble_weights()
        self.performance_history = []
        
    def _initialize_ensemble_weights(self) -> Dict[str, float]:
        """Initialize weights for different selection methods."""
        return {
            'ml_based': 0.4,
            'rule_based': 0.2,
            'performance_based': 0.2,
            'popularity_based': 0.1,
            'cost_based': 0.1
        }
    
    def select_best_model_ensemble(self, 
                                 task_type: str, 
                                 prompt: str, 
                                 available_models: List[str],
                                 ensemble_method: EnsembleMethod = EnsembleMethod.WEIGHTED_VOTING,
                                 **kwargs) -> EnsembleSelectionResult:
        """
        Select the best model using ensemble methods.
        """
        try:
            logger.info(f"🎭 [ENSEMBLE] Using {ensemble_method.value} for model selection")
            
            # Get individual selection results
            individual_results = self._get_individual_selections(
                task_type, prompt, available_models, **kwargs
            )
            
            # Apply ensemble method
            if ensemble_method == EnsembleMethod.VOTING:
                return self._voting_ensemble(individual_results, available_models)
            elif ensemble_method == EnsembleMethod.WEIGHTED_VOTING:
                return self._weighted_voting_ensemble(individual_results, available_models)
            elif ensemble_method == EnsembleMethod.STACKING:
                return self._stacking_ensemble(individual_results, available_models, task_type, prompt)
            elif ensemble_method == EnsembleMethod.CONSENSUS:
                return self._consensus_ensemble(individual_results, available_models)
            elif ensemble_method == EnsembleMethod.ADAPTIVE:
                return self._adaptive_ensemble(individual_results, available_models, task_type)
            else:
                # Default to weighted voting
                return self._weighted_voting_ensemble(individual_results, available_models)
                
        except Exception as e:
            logger.error(f"Error in ensemble selection: {e}")
            return self._fallback_selection(available_models, str(e))
    
    def _get_individual_selections(self, 
                                 task_type: str, 
                                 prompt: str, 
                                 available_models: List[str],
                                 **kwargs) -> List[ModelSelectionResult]:
        """Get individual selection results from different methods."""
        results = []
        
        try:
            # 1. ML-based selection
            ml_result = self.ml_selector.select_best_model(
                task_type, prompt, available_models, **kwargs
            )
            results.append(ml_result)
            
        except Exception as e:
            logger.warning(f"ML-based selection failed: {e}")
        
        try:
            # 2. Rule-based selection
            rule_result = self._rule_based_selection(task_type, prompt, available_models)
            results.append(rule_result)
            
        except Exception as e:
            logger.warning(f"Rule-based selection failed: {e}")
        
        try:
            # 3. Performance-based selection
            perf_result = self._performance_based_selection(task_type, available_models)
            results.append(perf_result)
            
        except Exception as e:
            logger.warning(f"Performance-based selection failed: {e}")
        
        try:
            # 4. Popularity-based selection
            pop_result = self._popularity_based_selection(task_type, available_models)
            results.append(pop_result)
            
        except Exception as e:
            logger.warning(f"Popularity-based selection failed: {e}")
        
        try:
            # 5. Cost-based selection
            cost_result = self._cost_based_selection(task_type, available_models, **kwargs)
            results.append(cost_result)
            
        except Exception as e:
            logger.warning(f"Cost-based selection failed: {e}")
        
        return results
    
    def _rule_based_selection(self, 
                            task_type: str, 
                            prompt: str, 
                            available_models: List[str]) -> ModelSelectionResult:
        """Rule-based model selection."""
        # Task-specific model preferences
        task_preferences = {
            'text-generation': ['gpt2', 'gpt2-medium', 'distilgpt2'],
            'text-classification': ['distilbert-base-uncased', 'bert-base-uncased'],
            'summarization': ['facebook/bart-large-cnn', 't5-base'],
            'translation': ['Helsinki-NLP/opus-mt-en-es', 't5-base'],
            'question-answering': ['distilbert-base-cased-distilled-squad', 'bert-base-cased'],
            'sentiment-analysis': ['nlptown/bert-base-multilingual-uncased-sentiment'],
            'named-entity-recognition': ['dbmdz/bert-large-cased-finetuned-conll03-english'],
        }
        
        preferred_models = task_preferences.get(task_type, available_models)
        
        # Find best available model
        selected_model = None
        for model in preferred_models:
            if model in available_models:
                selected_model = model
                break
        
        if not selected_model:
            selected_model = available_models[0] if available_models else "gpt2"
        
        return ModelSelectionResult(
            selected_model=selected_model,
            confidence_score=0.7,
            predicted_performance={model: 0.6 for model in available_models},
            alternative_models=[(model, 0.5) for model in available_models[1:3]],
            reasoning=f"Rule-based selection for {task_type}",
            feature_importance={}
        )
    
    def _performance_based_selection(self, 
                                   task_type: str, 
                                   available_models: List[str]) -> ModelSelectionResult:
        """Performance-based model selection using historical data."""
        try:
            # Get performance analytics
            analytics = self.ml_selector.get_performance_analytics()
            
            if 'performance_by_model' in analytics:
                model_performance = analytics['performance_by_model']
                
                # Find best performing model that's available
                best_model = None
                best_score = 0.0
                
                for model in available_models:
                    if model in model_performance:
                        score = model_performance[model]
                        if score > best_score:
                            best_score = score
                            best_model = model
                
                if best_model:
                    return ModelSelectionResult(
                        selected_model=best_model,
                        confidence_score=min(1.0, best_score),
                        predicted_performance=model_performance,
                        alternative_models=[(model, score) for model, score in model_performance.items() 
                                          if model != best_model and model in available_models][:3],
                        reasoning=f"Performance-based selection (historical accuracy: {best_score:.2f})",
                        feature_importance={}
                    )
            
            # Fallback to first available model
            return ModelSelectionResult(
                selected_model=available_models[0] if available_models else "gpt2",
                confidence_score=0.5,
                predicted_performance={},
                alternative_models=[],
                reasoning="Performance-based fallback (no historical data)",
                feature_importance={}
            )
            
        except Exception as e:
            logger.error(f"Error in performance-based selection: {e}")
            return self._fallback_selection(available_models, str(e))
    
    def _popularity_based_selection(self, 
                                  task_type: str, 
                                  available_models: List[str]) -> ModelSelectionResult:
        """Popularity-based model selection."""
        # Model popularity scores (based on downloads, usage, etc.)
        popularity_scores = {
            'gpt2': 0.9,
            'gpt2-medium': 0.8,
            'distilgpt2': 0.7,
            'distilbert-base-uncased': 0.8,
            'bert-base-uncased': 0.9,
            'facebook/bart-large-cnn': 0.7,
            't5-base': 0.6,
            'Helsinki-NLP/opus-mt-en-es': 0.5,
            'distilbert-base-cased-distilled-squad': 0.6,
            'bert-base-cased': 0.7,
            'nlptown/bert-base-multilingual-uncased-sentiment': 0.5,
            'dbmdz/bert-large-cased-finetuned-conll03-english': 0.4,
        }
        
        # Find most popular available model
        best_model = None
        best_score = 0.0
        
        for model in available_models:
            score = popularity_scores.get(model, 0.3)  # Default score for unknown models
            if score > best_score:
                best_score = score
                best_model = model
        
        if not best_model:
            best_model = available_models[0] if available_models else "gpt2"
            best_score = 0.5
        
        return ModelSelectionResult(
            selected_model=best_model,
            confidence_score=best_score,
            predicted_performance={model: popularity_scores.get(model, 0.3) for model in available_models},
            alternative_models=[(model, popularity_scores.get(model, 0.3)) for model in available_models 
                              if model != best_model][:3],
            reasoning=f"Popularity-based selection (popularity score: {best_score:.2f})",
            feature_importance={}
        )
    
    def _cost_based_selection(self, 
                            task_type: str, 
                            available_models: List[str], 
                            **kwargs) -> ModelSelectionResult:
        """Cost-based model selection."""
        # Model cost estimates (relative costs)
        cost_estimates = {
            'gpt2': 0.1,
            'gpt2-medium': 0.3,
            'distilgpt2': 0.05,
            'distilbert-base-uncased': 0.2,
            'bert-base-uncased': 0.4,
            'facebook/bart-large-cnn': 0.5,
            't5-base': 0.3,
            'Helsinki-NLP/opus-mt-en-es': 0.2,
            'distilbert-base-cased-distilled-squad': 0.3,
            'bert-base-cased': 0.4,
            'nlptown/bert-base-multilingual-uncased-sentiment': 0.2,
            'dbmdz/bert-large-cased-finetuned-conll03-english': 0.4,
        }
        
        # Check if cost is a constraint
        cost_constraint = kwargs.get('cost_constraint', 0.5)
        
        # Find cheapest model that meets constraints
        best_model = None
        best_cost = float('inf')
        
        for model in available_models:
            cost = cost_estimates.get(model, 0.3)
            if cost <= cost_constraint and cost < best_cost:
                best_cost = cost
                best_model = model
        
        if not best_model:
            # If no model meets cost constraint, pick the cheapest
            best_model = min(available_models, key=lambda m: cost_estimates.get(m, 0.3))
            best_cost = cost_estimates.get(best_model, 0.3)
        
        return ModelSelectionResult(
            selected_model=best_model,
            confidence_score=1.0 - best_cost,  # Higher confidence for lower cost
            predicted_performance={model: 1.0 - cost_estimates.get(model, 0.3) for model in available_models},
            alternative_models=[(model, 1.0 - cost_estimates.get(model, 0.3)) for model in available_models 
                              if model != best_model][:3],
            reasoning=f"Cost-based selection (cost: {best_cost:.2f})",
            feature_importance={}
        )
    
    def _voting_ensemble(self, 
                        individual_results: List[ModelSelectionResult], 
                        available_models: List[str]) -> EnsembleSelectionResult:
        """Simple voting ensemble."""
        if not individual_results:
            return self._fallback_selection(available_models, "No individual results")
        
        # Count votes for each model
        votes = Counter()
        for result in individual_results:
            votes[result.selected_model] += 1
        
        # Select model with most votes
        selected_model = votes.most_common(1)[0][0]
        vote_count = votes[selected_model]
        confidence_score = vote_count / len(individual_results)
        
        # Calculate consensus strength
        consensus_strength = vote_count / len(individual_results)
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=confidence_score,
            ensemble_scores={model: votes[model] / len(individual_results) for model in available_models},
            individual_results=individual_results,
            ensemble_method=EnsembleMethod.VOTING,
            consensus_strength=consensus_strength,
            reasoning=f"Voting ensemble: {vote_count}/{len(individual_results)} votes",
            feature_importance={}
        )
    
    def _weighted_voting_ensemble(self, 
                                individual_results: List[ModelSelectionResult], 
                                available_models: List[str]) -> EnsembleSelectionResult:
        """Weighted voting ensemble."""
        if not individual_results:
            return self._fallback_selection(available_models, "No individual results")
        
        # Calculate weighted scores
        model_scores = {}
        total_weight = 0.0
        
        for i, result in enumerate(individual_results):
            # Weight based on confidence and method
            weight = result.confidence_score * self.ensemble_weights.get(
                ['ml_based', 'rule_based', 'performance_based', 'popularity_based', 'cost_based'][i % 5], 
                0.2
            )
            total_weight += weight
            
            # Add weighted score
            if result.selected_model not in model_scores:
                model_scores[result.selected_model] = 0.0
            model_scores[result.selected_model] += weight
        
        # Normalize scores
        if total_weight > 0:
            for model in model_scores:
                model_scores[model] /= total_weight
        
        # Select best model
        selected_model = max(model_scores.items(), key=lambda x: x[1])[0]
        confidence_score = model_scores[selected_model]
        
        # Calculate consensus strength
        consensus_strength = confidence_score
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=confidence_score,
            ensemble_scores=model_scores,
            individual_results=individual_results,
            ensemble_method=EnsembleMethod.WEIGHTED_VOTING,
            consensus_strength=consensus_strength,
            reasoning=f"Weighted voting ensemble (weighted score: {confidence_score:.3f})",
            feature_importance={}
        )
    
    def _stacking_ensemble(self, 
                         individual_results: List[ModelSelectionResult], 
                         available_models: List[str],
                         task_type: str,
                         prompt: str) -> EnsembleSelectionResult:
        """Stacking ensemble with meta-learning."""
        if not individual_results:
            return self._fallback_selection(available_models, "No individual results")
        
        # Meta-features for stacking
        meta_features = self._extract_meta_features(task_type, prompt, individual_results)
        
        # Simple meta-learner (could be replaced with actual ML model)
        meta_scores = {}
        
        for result in individual_results:
            # Combine individual confidence with meta-features
            base_score = result.confidence_score
            
            # Adjust based on meta-features
            if meta_features['high_consensus']:
                base_score *= 1.2
            if meta_features['complex_task']:
                base_score *= 0.9
            if meta_features['popular_model']:
                base_score *= 1.1
            
            meta_scores[result.selected_model] = min(1.0, base_score)
        
        # Select best model
        selected_model = max(meta_scores.items(), key=lambda x: x[1])[0]
        confidence_score = meta_scores[selected_model]
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=confidence_score,
            ensemble_scores=meta_scores,
            individual_results=individual_results,
            ensemble_method=EnsembleMethod.STACKING,
            consensus_strength=self._calculate_consensus_strength(individual_results),
            reasoning=f"Stacking ensemble with meta-learning (meta-score: {confidence_score:.3f})",
            feature_importance={}
        )
    
    def _consensus_ensemble(self, 
                          individual_results: List[ModelSelectionResult], 
                          available_models: List[str]) -> EnsembleSelectionResult:
        """Consensus-based ensemble that requires strong agreement."""
        if not individual_results:
            return self._fallback_selection(available_models, "No individual results")
        
        # Count votes
        votes = Counter()
        for result in individual_results:
            votes[result.selected_model] += 1
        
        # Require at least 60% consensus
        total_votes = len(individual_results)
        consensus_threshold = 0.6
        
        # Find models with sufficient consensus
        consensus_models = [
            (model, count) for model, count in votes.items() 
            if count / total_votes >= consensus_threshold
        ]
        
        if consensus_models:
            # Select model with highest consensus
            selected_model, vote_count = max(consensus_models, key=lambda x: x[1])
            confidence_score = vote_count / total_votes
            consensus_strength = confidence_score
        else:
            # Fall back to weighted voting if no consensus
            return self._weighted_voting_ensemble(individual_results, available_models)
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=confidence_score,
            ensemble_scores={model: votes[model] / total_votes for model in available_models},
            individual_results=individual_results,
            ensemble_method=EnsembleMethod.CONSENSUS,
            consensus_strength=consensus_strength,
            reasoning=f"Consensus ensemble: {vote_count}/{total_votes} votes ({confidence_score:.1%} consensus)",
            feature_importance={}
        )
    
    def _adaptive_ensemble(self, 
                         individual_results: List[ModelSelectionResult], 
                         available_models: List[str],
                         task_type: str) -> EnsembleSelectionResult:
        """Adaptive ensemble that adjusts weights based on task type."""
        if not individual_results:
            return self._fallback_selection(available_models, "No individual results")
        
        # Task-specific weight adjustments
        task_weight_adjustments = {
            'text-generation': {'ml_based': 1.2, 'rule_based': 0.8},
            'text-classification': {'ml_based': 1.1, 'performance_based': 1.3},
            'summarization': {'rule_based': 1.1, 'popularity_based': 1.2},
            'translation': {'rule_based': 1.3, 'cost_based': 0.9},
            'question-answering': {'performance_based': 1.2, 'ml_based': 1.1},
        }
        
        # Get adjustments for this task
        adjustments = task_weight_adjustments.get(task_type, {})
        
        # Calculate adaptive scores
        model_scores = {}
        total_weight = 0.0
        
        method_names = ['ml_based', 'rule_based', 'performance_based', 'popularity_based', 'cost_based']
        
        for i, result in enumerate(individual_results):
            method_name = method_names[i % len(method_names)]
            
            # Base weight
            base_weight = self.ensemble_weights.get(method_name, 0.2)
            
            # Apply task-specific adjustment
            adjustment = adjustments.get(method_name, 1.0)
            weight = base_weight * adjustment * result.confidence_score
            
            total_weight += weight
            
            # Add weighted score
            if result.selected_model not in model_scores:
                model_scores[result.selected_model] = 0.0
            model_scores[result.selected_model] += weight
        
        # Normalize scores
        if total_weight > 0:
            for model in model_scores:
                model_scores[model] /= total_weight
        
        # Select best model
        selected_model = max(model_scores.items(), key=lambda x: x[1])[0]
        confidence_score = model_scores[selected_model]
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=confidence_score,
            ensemble_scores=model_scores,
            individual_results=individual_results,
            ensemble_method=EnsembleMethod.ADAPTIVE,
            consensus_strength=self._calculate_consensus_strength(individual_results),
            reasoning=f"Adaptive ensemble for {task_type} (adaptive score: {confidence_score:.3f})",
            feature_importance={}
        )
    
    def _extract_meta_features(self, 
                             task_type: str, 
                             prompt: str, 
                             individual_results: List[ModelSelectionResult]) -> Dict[str, Any]:
        """Extract meta-features for stacking ensemble."""
        # Check for consensus
        selected_models = [result.selected_model for result in individual_results]
        most_common_model = Counter(selected_models).most_common(1)[0][0]
        consensus_ratio = Counter(selected_models)[most_common_model] / len(individual_results)
        
        # Check task complexity
        complex_keywords = ['analyze', 'compare', 'evaluate', 'synthesize', 'optimize']
        complex_task = any(keyword in prompt.lower() for keyword in complex_keywords)
        
        # Check model popularity
        popular_models = ['gpt2', 'bert-base-uncased', 'distilbert-base-uncased']
        popular_model = any(result.selected_model in popular_models for result in individual_results)
        
        return {
            'high_consensus': consensus_ratio >= 0.6,
            'complex_task': complex_task,
            'popular_model': popular_model,
            'consensus_ratio': consensus_ratio
        }
    
    def _calculate_consensus_strength(self, individual_results: List[ModelSelectionResult]) -> float:
        """Calculate the strength of consensus among individual results."""
        if not individual_results:
            return 0.0
        
        selected_models = [result.selected_model for result in individual_results]
        most_common_count = Counter(selected_models).most_common(1)[0][1]
        
        return most_common_count / len(individual_results)
    
    def _fallback_selection(self, available_models: List[str], error_message: str) -> EnsembleSelectionResult:
        """Fallback selection when ensemble methods fail."""
        selected_model = available_models[0] if available_models else "gpt2"
        
        return EnsembleSelectionResult(
            selected_model=selected_model,
            confidence_score=0.3,
            ensemble_scores={model: 0.3 for model in available_models},
            individual_results=[],
            ensemble_method=EnsembleMethod.VOTING,
            consensus_strength=0.0,
            reasoning=f"Fallback selection due to error: {error_message}",
            feature_importance={}
        )
    
    def update_ensemble_weights(self, performance_feedback: Dict[str, float]):
        """Update ensemble weights based on performance feedback."""
        try:
            # Simple weight update based on performance
            for method, performance in performance_feedback.items():
                if method in self.ensemble_weights:
                    # Increase weight for good performance, decrease for poor
                    adjustment = (performance - 0.5) * 0.1  # Small adjustment
                    self.ensemble_weights[method] = max(0.05, min(0.8, 
                        self.ensemble_weights[method] + adjustment))
            
            # Normalize weights
            total_weight = sum(self.ensemble_weights.values())
            for method in self.ensemble_weights:
                self.ensemble_weights[method] /= total_weight
            
            logger.info(f"Updated ensemble weights: {self.ensemble_weights}")
            
        except Exception as e:
            logger.error(f"Error updating ensemble weights: {e}")
    
    def get_ensemble_analytics(self) -> Dict[str, Any]:
        """Get analytics on ensemble performance."""
        return {
            'ensemble_weights': self.ensemble_weights,
            'performance_history_count': len(self.performance_history),
            'available_methods': [method.value for method in EnsembleMethod],
            'ml_analytics': self.ml_selector.get_performance_analytics()
        }

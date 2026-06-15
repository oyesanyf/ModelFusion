"""
Model selector module for hybrid model selection.

This module provides advanced model selection capabilities combining
multiple criteria and providers.
"""

from typing import Dict, List, Optional, Tuple, Any
from .discovery import ModelMetrics, SmartModelSelector


class HybridModelSelector:
    """Hybrid model selector that combines multiple selection strategies."""
    
    def __init__(self, db_path: str = "db/hf_models.db"):
        self.smart_selector = SmartModelSelector(db_path)
        self.selection_history = []
    
    def select_model(self, prompt: str, task_type: Optional[str] = None, 
                    constraints: Optional[Dict[str, Any]] = None) -> Tuple[str, str, float]:
        """Select the best model using hybrid approach."""
        # Use smart selector as base
        model_id, detected_task, confidence = self.smart_selector.select_best_model(prompt)
        
        # Apply constraints if provided
        if constraints:
            model_id, confidence = self._apply_constraints(model_id, constraints, confidence)
        
        # Use provided task type if available
        final_task = task_type or detected_task
        
        # Record selection
        self.selection_history.append({
            'prompt': prompt,
            'selected_model': model_id,
            'task_type': final_task,
            'confidence': confidence,
            'constraints': constraints
        })
        
        return model_id, final_task, confidence
    
    def _apply_constraints(self, model_id: str, constraints: Dict[str, Any], 
                          base_confidence: float) -> Tuple[str, float]:
        """Apply selection constraints to model choice."""
        # This is a simplified implementation
        # In a full implementation, you would check model metadata against constraints
        
        confidence = base_confidence
        
        # Example constraints: size, license, performance requirements
        if 'max_size_gb' in constraints:
            # Would check model size here
            pass
        
        if 'license_type' in constraints:
            # Would check license compatibility here
            pass
        
        return model_id, confidence
    
    def get_selection_history(self) -> List[Dict[str, Any]]:
        """Get the history of model selections."""
        return self.selection_history.copy() 
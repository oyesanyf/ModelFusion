"""
Integration Layer
Core integration hub for all innovation systems.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from .contextual_understanding import ContextualUnderstanding
from .semantic_processing import SemanticProcessor
from .temporal_awareness import TemporalAwareness
from .workflow_intelligence import WorkflowIntelligence
from .predictive_capabilities import PredictiveCapabilities
from .adaptive_learning import AdaptiveLearning
from .api_management import APIManager
from ..result_schema import UnifiedResult, coerce_unified
from ..insights import generate_auto_insights
from ..semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)

@dataclass
class IntegratedResult:
    """Result from integrated processing."""
    success: bool
    context: Dict[str, Any]
    processing_time_ms: float
    error_message: Optional[str] = None

class InnovationHub:
    """Core integration hub for all innovation systems."""
    
    def __init__(self):
        # Initialize API manager
        self.api_manager = APIManager()
        
        # Initialize all innovation systems
        self.contextual_understanding = ContextualUnderstanding()
        self.semantic_processor = SemanticProcessor()
        self.temporal_awareness = TemporalAwareness()
        self.workflow_intelligence = WorkflowIntelligence()
        self.predictive_capabilities = PredictiveCapabilities()
        self.adaptive_learning = AdaptiveLearning()
        
        # State management
        self.active_workflows: Dict[str, Any] = {}
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self.processing_history: List[Dict[str, Any]] = []
        self.semantic_memory = SemanticMemory()
        
    async def process_integrated(self, 
                               content: Union[str, Path, bytes],
                               task: str,
                               context: Optional[Dict[str, Any]] = None,
                               use_openai: bool = False) -> IntegratedResult:
        """Process content using all integrated innovations."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Initialize context
            current_context = self._initialize_context(context)
            
            # When using OpenAI, call innovation modules directly (bypass APIManager)
            if use_openai:
                # 1. Context Understanding
                try:
                    context_result = await self.contextual_understanding.analyze_context(
                        str(content) if isinstance(content, (str, Path)) else content,
                        current_context.get('content_type', 'text-generation')
                    )
                    current_context.update({'context_analysis': context_result})
                except Exception as e:
                    logger.error(f"Error in context analysis: {e}")
                    current_context.update({'context_analysis': {}})
                
                # 2. Semantic Processing
                try:
                    semantic_result = await self.semantic_processor.analyze_semantics(
                        str(content),
                        current_context
                    )
                    current_context.update({'semantic_analysis': semantic_result})
                except Exception as e:
                    logger.error(f"Error in semantic analysis: {e}")
                    current_context.update({'semantic_analysis': {}})
                
                # 3. Create or Get Workflow
                try:
                    workflow_result = await self.workflow_intelligence.create_or_get_workflow(
                        task,
                        current_context
                    )
                    current_context.update({'workflow': workflow_result})
                except Exception as e:
                    logger.error(f"Error creating workflow: {e}")
                    current_context.update({'workflow': None})
                
                # 4. Predictive Analysis
                try:
                    predictions = await self.predictive_capabilities.predict_issues(
                        str(content),
                        current_context
                    )
                    current_context.update({'predictions': predictions})
                except Exception as e:
                    logger.error(f"Error in predictive analysis: {e}")
                    current_context.update({'predictions': {}})
                
                # 5. Temporal Analysis
                try:
                    # Get previous states from context
                    previous_states = self._get_previous_states(current_context)
                    temporal_result = await self.temporal_awareness.analyze_temporal_changes(
                        current_state=str(content),
                        previous_states=previous_states
                    )
                    current_context.update({'temporal_analysis': temporal_result})
                except Exception as e:
                    logger.error(f"Error in temporal analysis: {e}")
                    current_context.update({'temporal_analysis': {}})
                
                # 6. Adaptive Learning
                try:
                    learning_result = await self.adaptive_learning.learn_from_context(
                        context=current_context
                    )
                    current_context.update({'adaptive_learning': learning_result})
                except Exception as e:
                    logger.error(f"Error in adaptive learning: {e}")
                    current_context.update({'adaptive_learning': {}})
            
            else:
                # Use APIManager for Gemini (original behavior)
                # Determine provider based on use_openai flag
                provider = 'openai' if use_openai else 'gemini-2.5-flash'
                
                # 1. Context Understanding with API management
                context_result = await self.api_manager.execute_with_fallback(
                    self.contextual_understanding.analyze_context,
                    provider,
                    str(content) if isinstance(content, (str, Path)) else content,
                    current_context.get('content_type')
                )
                current_context.update({'context_analysis': context_result})
                
                # 2. Semantic Processing
                semantic_result = await self.api_manager.execute_with_fallback(
                    self.semantic_processor.analyze_semantics,
                    provider,
                    str(content),
                    current_context
                )
                current_context.update({'semantic_analysis': semantic_result})
                
                # 3. Create or Get Workflow
                workflow_result = await self._get_or_create_workflow(task, current_context, use_openai)
                current_context.update({'workflow': workflow_result})
                
                # 4. Predictive Analysis
                predictions = await self.api_manager.execute_with_fallback(
                    self.predictive_capabilities.predict_issues,
                    provider,
                    str(content),
                    current_context
                )
                current_context.update({'predictions': predictions})
                
                # 5. Temporal Analysis
                temporal_result = await self._perform_temporal_analysis(content, current_context, use_openai)
                current_context.update({'temporal_analysis': temporal_result})
                
                # 6. Adaptive Learning
                learning_result = await self._perform_adaptive_learning(content, current_context, use_openai)
                current_context.update({'adaptive_learning': learning_result})
            
            # 7. Update integration knowledge
            await self._update_integration_knowledge(current_context)
            
            # Store processing result
            result = IntegratedResult(
                success=True,
                context=current_context,
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
            self._store_processing_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in integrated processing: {e}")
            return IntegratedResult(
                success=False,
                context={},
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                error_message=str(e)
            )
            
    def _initialize_context(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize processing context."""
        base_context = {
            'session_id': str(datetime.now().timestamp()),
            'timestamp': datetime.now(),
            'processing_chain': []
        }
        
        if context:
            base_context.update(context)
            
        return base_context
        
    async def _get_or_create_workflow(self, task: str, context: Dict[str, Any], use_openai: bool = False) -> Any:
        """Get or create workflow for the task."""
        try:
            provider = 'openai' if use_openai else 'gemini-2.5-flash'
            return await self.api_manager.execute_with_fallback(
                self.workflow_intelligence.create_or_get_workflow,
                provider,
                task,
                context
            )
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            return None
        
    async def _perform_temporal_analysis(self, content: Any, context: Dict[str, Any], use_openai: bool = False) -> Any:
        """Perform temporal analysis."""
        try:
            provider = 'openai' if use_openai else 'gemini-2.5-flash'
            previous_states = self._get_previous_states(context)
            return await self.api_manager.execute_with_fallback(
                self.temporal_awareness.analyze_temporal_changes,
                provider,
                str(content),
                previous_states
            )
        except Exception as e:
            logger.error(f"Error in temporal analysis: {e}")
            return None
        
    async def _perform_adaptive_learning(self, content: Any, context: Dict[str, Any], use_openai: bool = False) -> Any:
        """Perform adaptive learning."""
        try:
            provider = 'openai' if use_openai else 'gemini-2.5-flash'
            return await self.api_manager.execute_with_fallback(
                self.adaptive_learning.learn_from_context,
                provider,
                context
            )
        except Exception as e:
            logger.error(f"Error in adaptive learning: {e}")
            return None
        
    def _get_previous_states(self, context: Dict[str, Any]) -> List[tuple]:
        """Get previous states from context history."""
        session_id = context.get('session_id')
        if not session_id:
            return []
            
        previous_states = []
        for record in self.processing_history:
            if record['session_id'] == session_id:
                state = record.get('context', {}).get('current_state')
                if state:
                    previous_states.append((state, record['timestamp']))
                    
        return previous_states
        
    async def _update_integration_knowledge(self, context: Dict[str, Any]) -> None:
        """Update integration knowledge base."""
        try:
            # Update context cache
            self.context_cache[context['session_id']] = context
            
            # Update processing history
            self.processing_history.append({
                'timestamp': datetime.now(),
                'context': context,
                'session_id': context['session_id']
            })
            
            # Trigger learning updates
            await self.api_manager.execute_with_fallback(
                self.adaptive_learning.learn_from_context,
                'gemini-2.5-flash',
                context
            )
            
        except Exception as e:
            logger.error(f"Error updating integration knowledge: {e}")
            
    def _store_processing_result(self, result: IntegratedResult) -> None:
        """Store processing result in history."""
        if result.success:
            self.processing_history.append({
                'timestamp': datetime.now(),
                'result': result.context,
                'processing_time': result.processing_time_ms
            })
"""
Enhanced Orchestrator with Integrated Innovations
Combines HuggingFace model orchestration with advanced innovation systems.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging
from datetime import datetime

from .orchestrator import HuggingFaceOrchestrator
from .innovations import InnovationHub
from .task_detector import task_detector

# Remove module-level langextract import to prevent early initialization
# LANGEXTRACT_AVAILABLE will be checked when needed

logger = logging.getLogger(__name__)

@dataclass
class EnhancedResult:
    """Enhanced result with innovation insights."""
    content: str
    success: bool
    models_used: List[str]
    processing_time_ms: float
    innovation_insights: Dict[str, Any]
    error_message: Optional[str] = None

class EnhancedOrchestrator:
    """Enhanced orchestrator with integrated innovations."""
    
    def __init__(self, budget: float = 10.0, enable_ml: bool = False, verbose: bool = False):
        # Initialize base orchestrator
        self.base_orchestrator = HuggingFaceOrchestrator(
            budget=budget,
            enable_ml=enable_ml,
            verbose=verbose
        )
        
        # Initialize innovation hub
        self.innovation_hub = InnovationHub()
        
        # Check LangExtract availability when needed, not at import time
        self._lang_extract_available = None
        
        # Configuration
        self.budget = budget
        self.enable_ml = enable_ml
        self.verbose = verbose

    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
                logger.info("LangExtract available for enhanced orchestration")
            except ImportError:
                self._lang_extract_available = False
                logger.warning("LangExtract not available. Install with: pip install langextract")
        return self._lang_extract_available

    async def process_task(self, 
                         task_text: str,
                         file_path: Optional[Path] = None,
                         **kwargs) -> EnhancedResult:
        """Process task with enhanced capabilities."""
        start_time = asyncio.get_event_loop().time()

        
        try:
            # Initialize context
            context = self._initialize_context(task_text, file_path, kwargs)
            
            # Use LangExtract for advanced task understanding
            if self._check_langextract_available():
                task_analysis = await self._analyze_task_with_langextract(task_text, context)
                context.update({'task_analysis': task_analysis})
            else:
                # Fallback to basic task detection
                task_analysis = task_detector.detect_task_type(task_text)
                context.update({'task_analysis': {
                    'task_type': task_analysis.task_type,
                    'confidence': task_analysis.confidence
                }})
            
            # Process with innovation hub
            # Handle both dict and object types for task_analysis
            if isinstance(task_analysis, dict):
                task_type = task_analysis.get('task_type', 'text-generation')
            else:
                task_type = getattr(task_analysis, 'task_type', 'text-generation')
            
            # Pass use_openai flag to innovation hub
            use_openai = kwargs.get('use_openai', False)
            innovation_result = await self.innovation_hub.process_integrated(
                task_text,
                task_type,
                context,
                use_openai=use_openai
            )
            
            # Process with base orchestrator (enhanced with innovation insights)
            enhanced_params = self._enhance_parameters(kwargs, innovation_result)
            base_result = await self.base_orchestrator.process_task(
                task_text,
                **enhanced_params
            )
            
            # Extract innovation insights
            innovation_insights = self._extract_innovation_insights(innovation_result)
            
            # Combine results
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return EnhancedResult(
                content=base_result.content,
                success=base_result.success,
                models_used=base_result.models_used,
                processing_time_ms=processing_time,
                innovation_insights=innovation_insights,
                error_message=base_result.error_message
            )
            
        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Error in enhanced orchestration: {e}")
            return EnhancedResult(
                content="",
                success=False,
                models_used=[],
                processing_time_ms=processing_time,
                innovation_insights={},
                error_message=str(e)
            )

    async def _analyze_task_with_langextract(self, 
                                          task_text: str,
                                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task using LangExtract with proper error handling."""
        try:
            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config
            
            # Prepare analysis prompt
            analysis_prompt = f"""
            Analyze the following task and extract key information:
            
            Task: {task_text}
            Context: {self._format_context(context)}
            
            Extract:
            1. Task type (text-generation, text-classification, question-answering, etc.)
            2. Required capabilities
            3. Processing constraints
            4. Quality requirements
            5. Confidence level (0-1)
            """
            
            # Define examples for better extraction using proper LangExtract format
            examples = [
                lx.data.ExampleData(
                    text="What is the capital of France?",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="task_type",
                            extraction_text="question-answering",
                            attributes={"confidence": 0.9}
                        ),
                        lx.data.Extraction(
                            extraction_class="capability",
                            extraction_text="knowledge",
                            attributes={}
                        ),
                        lx.data.Extraction(
                            extraction_class="capability",
                            extraction_text="reasoning",
                            attributes={}
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="Classify this text as positive or negative",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="task_type",
                            extraction_text="text-classification",
                            attributes={"confidence": 0.8}
                        ),
                        lx.data.Extraction(
                            extraction_class="capability",
                            extraction_text="sentiment_analysis",
                            attributes={}
                        )
                    ]
                )
            ]
            
            # Use the wrapper for consistent configuration
            result = extract_with_config(
                lx,
                text_or_documents=task_text,
                prompt_description=analysis_prompt,
                examples=examples
            )
            
            return {
                'task_type': self._extract_task_type(result),
                'capabilities': self._extract_capabilities(result),
                'constraints': self._extract_constraints(result),
                'requirements': self._extract_requirements(result),
                'confidence': self._calculate_confidence(result)
            }
            
        except Exception as e:
            logger.error(f"Error in LangExtract analysis: {e}")
            # Fallback to basic analysis
            return {
                'task_type': 'text-generation',
                'capabilities': ['text_generation'],
                'constraints': {},
                'requirements': {},
                'confidence': 0.5
            }

    def _initialize_context(self, 
                          task_text: str,
                          file_path: Optional[Path],
                          kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize processing context."""
        context = {
            'task_text': task_text,
            'file_path': str(file_path) if file_path else None,
            'timestamp': datetime.now().isoformat(),
            'budget': self.budget,
            'enable_ml': self.enable_ml,
            'verbose': self.verbose
        }
        
        # Add kwargs to context
        context.update(kwargs)
        
        return context

    def _enhance_parameters(self, 
                          params: Dict[str, Any],
                          innovation_result: Any) -> Dict[str, Any]:
        """Enhance processing parameters with innovation insights."""
        # Start with a copy of all original parameters to ensure nothing is lost
        enhanced = params.copy()

        
        if hasattr(innovation_result, 'context'):
            # Add workflow insights
            if 'workflow' in innovation_result.context:
                enhanced['workflow'] = innovation_result.context['workflow']
            
            # Add predictions
            if 'predictions' in innovation_result.context:
                enhanced['predictions'] = innovation_result.context['predictions']
            
            # Add semantic insights
            if 'semantic_analysis' in innovation_result.context:
                enhanced['semantic_insights'] = innovation_result.context['semantic_analysis']
        
        # Ensure chain_of_thought parameter is preserved
        if 'chain_of_thought' in params:
            enhanced['chain_of_thought'] = params['chain_of_thought']
        
        # Ensure SINQ manager is preserved
        if 'sinq_manager' in params:
            enhanced['sinq_manager'] = params['sinq_manager']
        
        return enhanced

    def _extract_innovation_insights(self, result: Any) -> Dict[str, Any]:
        """Extract insights from innovation result."""
        insights = {}
        
        if hasattr(result, 'context'):
            # Extract workflow insights
            if 'workflow' in result.context:
                workflow_data = result.context['workflow']
                if hasattr(workflow_data, 'workflow_type'):
                    insights['workflow'] = {
                        'type': getattr(workflow_data, 'workflow_type', 'unknown'),
                        'steps': len(getattr(workflow_data, 'steps', [])),
                        'optimization_level': getattr(workflow_data, 'optimization_level', 'basic')
                    }
                elif isinstance(workflow_data, dict):
                    insights['workflow'] = {
                        'type': workflow_data.get('type'),
                        'steps': len(workflow_data.get('steps', [])),
                        'optimization_level': workflow_data.get('optimization_level')
                    }
            
            # Extract predictive insights
            if 'predictions' in result.context:
                predictions_data = result.context['predictions']
                if hasattr(predictions_data, 'prediction_type'):
                    insights['predictions'] = {
                        'issues': predictions_data.prediction_type, # Simplified for example
                        'confidence': predictions_data.confidence
                    }
                elif isinstance(predictions_data, dict):
                    insights['predictions'] = {
                        'issues': predictions_data.get('issues', []), # Still keep for dict fallback
                        'confidence': predictions_data.get('confidence')
                    }
            
            # Extract semantic insights
            if 'semantic_analysis' in result.context:
                semantic_data = result.context['semantic_analysis']
                if hasattr(semantic_data, 'concepts'):
                    insights['semantic'] = {
                        'concepts': [c.concept for c in semantic_data.concepts] if semantic_data.concepts else [],
                        'relationships': [r.relation_type for r in semantic_data.relations] if semantic_data.relations else []
                    }
                elif isinstance(semantic_data, dict):
                    insights['semantic'] = {
                        'concepts': semantic_data.get('concepts', []),
                        'relationships': semantic_data.get('relationships', [])
                    }
            
            # Extract temporal insights
            if 'temporal_analysis' in result.context:
                temporal_data = result.context['temporal_analysis']
                if hasattr(temporal_data, 'changes'):
                    insights['temporal'] = {
                        'changes': len(temporal_data.changes) if temporal_data.changes else 0,
                        'patterns': len(temporal_data.patterns) if hasattr(temporal_data, 'patterns') and temporal_data.patterns else 0
                    }
                elif isinstance(temporal_data, dict):
                    insights['temporal'] = {
                        'changes': len(temporal_data.get('changes', [])),
                        'patterns': len(temporal_data.get('patterns', []))
                    }
        
        return insights

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt."""
        return "\n".join(f"{k}: {v}" for k, v in context.items())

    def _extract_task_type(self, result: Any) -> str:
        """Extract task type from LangExtract result."""
        try:
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "task_type":
                        return extraction.extraction_text
            # Fallback: try to extract from content
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    content = getattr(extraction, 'extraction_text', str(extraction))
                    if any(task in content.lower() for task in ['classification', 'analysis', 'generation', 'summarization']):
                        return content.split()[0] if content.split() else 'text-analysis'
        except Exception:
            pass
        return "text-analysis"

    def _extract_capabilities(self, result: Any) -> List[str]:
        """Extract required capabilities from LangExtract result."""
        capabilities = []
        try:
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "capability":
                        capabilities.append(extraction.extraction_text)
        except Exception:
            pass
        return capabilities or ["text_processing"]

    def _extract_constraints(self, result: Any) -> Dict[str, Any]:
        """Extract processing constraints from LangExtract result."""
        constraints = {}
        try:
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "constraint":
                        constraint_type = getattr(extraction, 'attributes', {}).get("type", "unknown")
                        constraints[constraint_type] = getattr(extraction, 'extraction_text', str(extraction))
        except Exception:
            pass
        return constraints

    def _extract_requirements(self, result: Any) -> Dict[str, Any]:
        """Extract quality requirements from LangExtract result."""
        requirements = {}
        try:
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "requirement":
                        req_type = getattr(extraction, 'attributes', {}).get("type", "unknown")
                        requirements[req_type] = {
                            'description': getattr(extraction, 'extraction_text', str(extraction)),
                            'priority': getattr(extraction, 'attributes', {}).get("priority", 0.0)
                        }
        except Exception:
            pass
        return requirements

    def _calculate_confidence(self, result: Any) -> float:
        """Calculate overall confidence from LangExtract result."""
        try:
            confidences = []
            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'attributes') and extraction.attributes:
                        confidence = extraction.attributes.get('confidence', 0.0)
                        if confidence > 0:
                            confidences.append(confidence)
            return sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            return 0.0

"""
SmartFileChain - Intelligent File Processing Chain
Implements AI-powered chaining of file processors.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from ..orchestrator import HuggingFaceOrchestrator
from ..task_detector import task_detector

logger = logging.getLogger(__name__)

@dataclass
class ChainStep:
    """Represents a step in the processing chain."""
    processor_type: str
    task: str
    model_id: Optional[str] = None
    config: Dict[str, Any] = None

@dataclass
class ChainResult:
    """Result from a chain of processing steps."""
    success: bool
    content: str
    steps_completed: List[ChainStep]
    processing_time_ms: float
    error_message: Optional[str] = None

class SmartFileChain:
    """Intelligently chains multiple processors based on content understanding."""
    
    def __init__(self):
        self.orchestrator = HuggingFaceOrchestrator()
        self.processing_history = []
    
    async def _detect_optimal_chain(self, file_path: Path, prompt: str) -> List[ChainStep]:
        """Detect the optimal processing chain for the input."""
        try:
            # Detect initial task
            task_detection = task_detector.detect_task_type(prompt)
            initial_task = task_detection.task_type
            
            # Get file type and content sample
            content_type = await self._analyze_content_type(file_path)
            
            # Build processing chain based on content and task
            chain = []
            
            # Add file type specific preprocessing
            if content_type.get('preprocessing_needed'):
                chain.append(ChainStep(
                    processor_type='preprocessor',
                    task=f"preprocess_{content_type['type']}",
                    config=content_type
                ))
            
            # Add main processing step
            chain.append(ChainStep(
                processor_type='main_processor',
                task=initial_task,
                config={'content_type': content_type}
            ))
            
            # Add postprocessing if needed
            if self._needs_postprocessing(initial_task, content_type):
                chain.append(ChainStep(
                    processor_type='postprocessor',
                    task=f"postprocess_{initial_task}",
                    config={'output_format': 'enhanced'}
                ))
            
            return chain
        except Exception as e:
            logger.error(f"Error detecting optimal chain: {e}")
            # Return a basic chain as fallback
            return [ChainStep(
                processor_type='basic_processor',
                task='basic_processing'
            )]
    
    async def _create_processor(self, step: ChainStep):
        """Create a processor for a chain step."""
        try:
            # Select appropriate model for the step
            if not step.model_id:
                model_selection = await self.orchestrator.select_model(
                    task_name=step.task,
                    requirements=step.config or {}
                )
                step.model_id = model_selection.model_id
            
            # Create processor instance
            processor_class = self._get_processor_class(step.processor_type)
            return processor_class(
                model_id=step.model_id,
                config=step.config
            )
        except Exception as e:
            logger.error(f"Error creating processor: {e}")
            return None
    
    def _build_context(self, prompt: str, chain: List[ChainStep]) -> Dict[str, Any]:
        """Build processing context."""
        return {
            'prompt': prompt,
            'chain_length': len(chain),
            'processing_history': self.processing_history,
            'chain_config': {step.task: step.config for step in chain}
        }
    
    async def _should_adjust_chain(self, result: Any) -> bool:
        """Determine if chain should be adjusted based on intermediate results."""
        if not result or not hasattr(result, 'success'):
            return True
        
        if not result.success:
            return True
        
        # Check if results meet quality threshold
        if hasattr(result, 'confidence') and result.confidence < 0.7:
            return True
        
        return False
    
    async def _replan_chain(self, chain: List[ChainStep], result: Any) -> List[ChainStep]:
        """Replan chain based on intermediate results."""
        try:
            # Analyze failure or low confidence
            issues = self._analyze_issues(result)
            
            # Modify chain based on issues
            new_chain = []
            for step in chain:
                if step in issues:
                    # Replace problematic step
                    alternative = await self._find_alternative_step(step, issues[step])
                    if alternative:
                        new_chain.append(alternative)
                    else:
                        new_chain.append(step)  # Keep original if no alternative
                else:
                    new_chain.append(step)
            
            return new_chain
        except Exception as e:
            logger.error(f"Error replanning chain: {e}")
            return chain  # Return original chain on error
    
    async def process_chain(self, file_path: Path, prompt: str) -> ChainResult:
        """Process file through an intelligent processing chain."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Detect optimal processing chain
            chain = await self._detect_optimal_chain(file_path, prompt)
            
            # Create processors
            processors = []
            for step in chain:
                processor = await self._create_processor(step)
                if processor:
                    processors.append((step, processor))
            
            # Process through chain
            current_input = file_path
            completed_steps = []
            
            for step, processor in processors:
                try:
                    # Process with current processor
                    result = await processor.process(
                        input=current_input,
                        context=self._build_context(prompt, chain)
                    )
                    
                    # Check if chain needs adjustment
                    if await self._should_adjust_chain(result):
                        # Replan remaining chain
                        remaining_chain = await self._replan_chain(
                            chain[len(completed_steps):],
                            result
                        )
                        # Update processors for remaining steps
                        processors = processors[:len(completed_steps)]
                        for new_step in remaining_chain:
                            new_processor = await self._create_processor(new_step)
                            if new_processor:
                                processors.append((new_step, new_processor))
                    
                    # Update for next step
                    current_input = result
                    completed_steps.append(step)
                    
                except Exception as step_error:
                    logger.error(f"Error in chain step {step.task}: {step_error}")
                    # Try to continue with next step
                    continue
            
            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Return final result
            if current_input and hasattr(current_input, 'content'):
                return ChainResult(
                    success=True,
                    content=current_input.content,
                    steps_completed=completed_steps,
                    processing_time_ms=processing_time
                )
            else:
                return ChainResult(
                    success=False,
                    content="Chain processing failed to produce valid output",
                    steps_completed=completed_steps,
                    processing_time_ms=processing_time,
                    error_message="Invalid chain output"
                )
            
        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Chain processing error: {e}")
            return ChainResult(
                success=False,
                content="",
                steps_completed=[],
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def _analyze_content_type(self, file_path: Path) -> Dict[str, Any]:
        """Analyze content type and preprocessing needs."""
        # Implementation would go here
        pass
    
    def _needs_postprocessing(self, task: str, content_type: Dict[str, Any]) -> bool:
        """Determine if postprocessing is needed."""
        # Implementation would go here
        pass
    
    def _get_processor_class(self, processor_type: str):
        """Get processor class by type."""
        # Implementation would go here
        pass
    
    def _analyze_issues(self, result: Any) -> Dict[ChainStep, List[str]]:
        """Analyze issues in chain processing."""
        # Implementation would go here
        pass
    
    async def _find_alternative_step(self, step: ChainStep, issues: List[str]) -> Optional[ChainStep]:
        """Find alternative step to resolve issues."""
        # Implementation would go here
        pass

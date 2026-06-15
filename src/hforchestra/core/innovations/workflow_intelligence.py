"""
Workflow Intelligence System
Uses LangExtract for automatic workflow creation and optimization.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging
import textwrap
from datetime import datetime
from enum import Enum

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

class WorkflowStepType(Enum):
    """Types of workflow steps."""
    PROCESSING = "processing"
    DECISION = "decision"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    INTEGRATION = "integration"
    OUTPUT = "output"

@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    step_id: str
    step_type: WorkflowStepType
    description: str
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    parameters: Dict[str, Any]
    validation_rules: List[Dict[str, Any]]
    optimization_hints: Dict[str, Any]
    confidence: float

@dataclass
class WorkflowPath:
    """Represents a path through the workflow."""
    steps: List[WorkflowStep]
    success_rate: float
    average_duration: float
    resource_requirements: Dict[str, Any]
    optimization_potential: float

@dataclass
class Workflow:
    """Represents a complete workflow."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    paths: List[WorkflowPath]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    metadata: Dict[str, Any]
    version: str
    created_at: datetime
    updated_at: datetime

@dataclass
class WorkflowAnalysisResult:
    """Result of workflow analysis."""
    workflow: Workflow
    optimizations: List[Dict[str, Any]]
    success: bool
    processing_time_ms: float
    error_message: Optional[str] = None

class WorkflowIntelligence:
    """Core system for workflow intelligence using LangExtract."""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        if LANGEXTRACT_AVAILABLE:
            logger.info("LangExtract available for workflow intelligence")
        else:
            logger.warning("LangExtract not available. Install with: pip install langextract")
    
    async def create_workflow(self, task_description: str, context: Dict[str, Any]) -> WorkflowAnalysisResult:
        """Create an optimized workflow for a task."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not LANGEXTRACT_AVAILABLE:
                raise ImportError("LangExtract is required for workflow creation")

            # Create workflow analysis prompt
            analysis_prompt = textwrap.dedent(f"""
            Create an optimized workflow for the task.
            Consider:
            1. Required processing steps
            2. Decision points and conditions
            3. Data transformations
            4. Validation requirements
            5. Integration points
            6. Resource optimization
            7. Error handling
            8. Performance considerations
            
            Task Description:
            {task_description}
            
            Context Information:
            {self._format_context(context)}
            """)

            # Define examples for workflow extraction
            examples = [
                lx.data.ExampleData(
                    text="A task to process and transform data from input to output.",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="workflow_step",
                            extraction_text="initial data ingestion",
                            attributes={
                                "step_type": "PROCESSING",
                                "inputs": ["source_data"],
                                "outputs": ["ingested_data"],
                                "confidence": 0.9
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="workflow_step",
                            extraction_text="data transformation",
                            attributes={
                                "step_type": "TRANSFORMATION",
                                "inputs": ["ingested_data"],
                                "outputs": ["transformed_data"],
                                "parameters": {"transformation_type": "normalization"},
                                "confidence": 0.85
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="workflow_path",
                            extraction_text="execution path example",
                            attributes={
                                "success_rate": 0.95,
                                "duration": "25",
                                "optimization": "dynamic_based_on_text_complexity"
                            }
                        ),
                        lx.data.Extraction(
                            extraction_class="workflow_optimization",
                            extraction_text="optimize for specific resource",
                            attributes={
                                "optimization_type": "resource_allocation",
                                "impact": {"resource_a": "-10%", "cost": "-5%"},
                                "confidence": 0.75
                            }
                        )
                    ]
                )
            ]

            # Get API key
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")
            
            # Use LangExtract for workflow creation
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=task_description,
                prompt_description=analysis_prompt,
                examples=examples,
                override_api_key=lx_api_key
            )

            # Process workflow components
            steps = []
            paths = []
            optimizations = []
            
            for extraction in result.extractions:
                if extraction.extraction_class == "workflow_step":
                    step = self._create_workflow_step(extraction)
                    if step:
                        steps.append(step)
                elif extraction.extraction_class == "workflow_path":
                    path = self._create_workflow_path(extraction)
                    if path:
                        paths.append(path)
                elif extraction.extraction_class == "workflow_optimization":
                    optimization = self._create_optimization(extraction)
                    if optimization:
                        optimizations.append(optimization)

            # Create workflow
            workflow = Workflow(
                workflow_id=self._generate_workflow_id(),
                name=self._extract_workflow_name(task_description),
                description=task_description,
                steps=steps,
                paths=paths,
                input_schema=self._create_input_schema(steps),
                output_schema=self._create_output_schema(steps),
                metadata=context,
                version="1.0",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # Store workflow
            self.workflows[workflow.workflow_id] = workflow

            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return WorkflowAnalysisResult(
                workflow=workflow,
                optimizations=optimizations,
                success=True,
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Error creating workflow: {e}")
            return WorkflowAnalysisResult(
                workflow=None,
                optimizations=[],
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    async def optimize_workflow(self, workflow: Workflow, 
                              optimization_goals: Dict[str, float]) -> WorkflowAnalysisResult:
        """Optimize an existing workflow."""
        try:
            # Create optimization prompt
            optimization_prompt = textwrap.dedent(f"""
            Optimize the workflow based on goals:
            {self._format_optimization_goals(optimization_goals)}
            
            Consider:
            1. Step ordering and dependencies
            2. Resource allocation
            3. Parallel processing opportunities
            4. Caching strategies
            5. Error handling improvements
            
            Current Workflow:
            {self._format_workflow(workflow)}
            """)

            # Get API key
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")
            
            # Use LangExtract for optimization
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=self._format_workflow(workflow),
                prompt_description=optimization_prompt,
                examples=[
                    lx.data.ExampleData(
                        text="Optimize a data processing workflow for speed.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="optimization",
                                extraction_text="implement parallel processing",
                                attributes={
                                    "optimization_type": "performance",
                                    "impact": "reduce_time",
                                    "requirements": "more_cores"
                                }
                            )
                        ]
                    )
                ],
                override_api_key=lx_api_key
            )

            # Process optimizations
            optimizations = self._process_optimization_results(result)
            
            # Apply optimizations
            optimized_workflow = self._apply_optimizations(workflow, optimizations)
            
            return WorkflowAnalysisResult(
                workflow=optimized_workflow,
                optimizations=optimizations,
                success=True,
                processing_time_ms=0
            )

        except Exception as e:
            logger.error(f"Error optimizing workflow: {e}")
            return WorkflowAnalysisResult(
                workflow=workflow,
                optimizations=[],
                success=False,
                processing_time_ms=0,
                error_message=str(e)
            )

    async def analyze_workflow_performance(self, workflow_id: str) -> Dict[str, Any]:
        """Analyze workflow performance."""
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Get execution history
            history = self._get_workflow_history(workflow_id)
            
            # Create analysis prompt
            analysis_prompt = textwrap.dedent(f"""
            Analyze workflow performance based on:
            1. Execution times
            2. Success rates
            3. Resource usage
            4. Error patterns
            5. Optimization opportunities
            
            Workflow:
            {self._format_workflow(workflow)}
            
            Execution History:
            {self._format_execution_history(history)}
            """)

            # Get API key
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")
            
            # Use LangExtract for analysis
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=self._format_workflow(workflow),
                prompt_description=analysis_prompt,
                examples=[
                    lx.data.ExampleData(
                        text="Workflow execution log: Step A took 5s, Step B failed.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="performance_metric",
                                extraction_text="Step B failure rate",
                                attributes={"value": "high", "reason": "input_error"}
                            )
                        ]
                    )
                ],
                override_api_key=lx_api_key
            )

            return self._process_performance_analysis(result)

        except Exception as e:
            logger.error(f"Error analyzing workflow performance: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def create_or_get_workflow(self, task_description: str, context: Dict[str, Any]) -> WorkflowAnalysisResult:
        """Create a new workflow or get existing one for a task."""
        try:
            # Check if we have an existing workflow for this task
            existing_workflow = self._find_existing_workflow(task_description)
            if existing_workflow:
                return WorkflowAnalysisResult(
                    workflow=existing_workflow,
                    optimizations=[],
                    success=True,
                    processing_time_ms=0
                )
            
            # Create new workflow
            return await self.create_workflow(task_description, context)
            
        except Exception as e:
            logger.error(f"Error in create_or_get_workflow: {e}")
            return WorkflowAnalysisResult(
                workflow=None,
                optimizations=[],
                success=False,
                processing_time_ms=0,
                error_message=str(e)
            )

    def _find_existing_workflow(self, task_description: str) -> Optional[Workflow]:
        """Find existing workflow for similar task description."""
        # Simple implementation - could be enhanced with semantic similarity
        for workflow in self.workflows.values():
            if task_description.lower() in workflow.description.lower():
                return workflow
        return None

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)

    def _create_workflow_step(self, extraction: Any) -> Optional[WorkflowStep]:
        """Create workflow step from extraction."""
        try:
            step_type_str = extraction.attributes.get("step_type", "processing").upper()
            step_type = WorkflowStepType.PROCESSING # Default
            if step_type_str in WorkflowStepType.__members__:
                step_type = WorkflowStepType[step_type_str]
            elif "PROCESSING" in step_type_str:
                step_type = WorkflowStepType.PROCESSING
            elif "DECISION" in step_type_str:
                step_type = WorkflowStepType.DECISION
            elif "TRANSFORMATION" in step_type_str:
                step_type = WorkflowStepType.TRANSFORMATION
            elif "VALIDATION" in step_type_str:
                step_type = WorkflowStepType.VALIDATION
            elif "INTEGRATION" in step_type_str:
                step_type = WorkflowStepType.INTEGRATION
            elif "OUTPUT" in step_type_str:
                step_type = WorkflowStepType.OUTPUT
            
            return WorkflowStep(
                step_id=self._generate_step_id(),
                step_type=step_type,
                description=extraction.extraction_text,
                inputs=extraction.attributes.get("inputs", []),
                outputs=extraction.attributes.get("outputs", []),
                dependencies=extraction.attributes.get("dependencies", []),
                parameters=extraction.attributes.get("parameters", {}),
                validation_rules=extraction.attributes.get("validation_rules", []),
                optimization_hints=extraction.attributes.get("optimization_hints", {}),
                confidence=extraction.attributes.get("confidence", 0.0)
            )
        except Exception as e:
            logger.error(f"Error creating workflow step: {e}")
            return None

    def _create_workflow_path(self, extraction: Any) -> Optional[WorkflowPath]:
        """Create workflow path from extraction."""
        try:
            duration_str = str(extraction.attributes.get("duration", "0"))
            average_duration = 0.0
            if duration_str.endswith("s"):
                try:
                    average_duration = float(duration_str.replace("s", ""))
                except ValueError:
                    pass
            else:
                try:
                    average_duration = float(duration_str)
                except ValueError:
                    pass

            return WorkflowPath(
                steps=[],  # Will be populated later
                success_rate=extraction.attributes.get("success_rate", 0.0),
                average_duration=average_duration,
                resource_requirements=extraction.attributes.get("resources", {}),
                optimization_potential=extraction.attributes.get("optimization_potential", 0.0)
            )
        except Exception as e:
            logger.error(f"Error creating workflow path: {e}")
            return None

    def _create_optimization(self, extraction: Any) -> Optional[Dict[str, Any]]:
        """Create optimization from extraction."""
        try:
            return {
                'type': extraction.attributes.get("optimization_type", "unknown"),
                'description': extraction.extraction_text,
                'impact': extraction.attributes.get("impact", {}),
                'requirements': extraction.attributes.get("requirements", {}),
                'confidence': extraction.attributes.get("confidence", 0.0)
            }
        except Exception as e:
            logger.error(f"Error creating optimization: {e}")
            return None

    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        return f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _generate_step_id(self) -> str:
        """Generate unique step ID."""
        return f"step_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def _extract_workflow_name(self, description: str) -> str:
        """Extract workflow name from description."""
        # Implementation would go here
        pass

    def _create_input_schema(self, steps: List[WorkflowStep]) -> Dict[str, Any]:
        """Create input schema from steps."""
        # Implementation would go here
        pass

    def _create_output_schema(self, steps: List[WorkflowStep]) -> Dict[str, Any]:
        """Create output schema from steps."""
        # Implementation would go here
        pass

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information."""
        return "\n".join(f"{k}: {v}" for k, v in context.items())

    def _format_optimization_goals(self, goals: Dict[str, float]) -> str:
        """Format optimization goals."""
        return "\n".join(f"{k}: {v}" for k, v in goals.items())

    def _format_workflow(self, workflow: Workflow) -> str:
        """Format workflow for analysis."""
        # Implementation would go here
        pass

    def _format_execution_history(self, history: List[Dict[str, Any]]) -> str:
        """Format execution history."""
        # Implementation would go here
        pass

    def _process_optimization_results(self, result: Any) -> List[Dict[str, Any]]:
        """Process optimization results."""
        # Implementation would go here
        pass

    def _apply_optimizations(self, workflow: Workflow, 
                           optimizations: List[Dict[str, Any]]) -> Workflow:
        """Apply optimizations to workflow."""
        # Implementation would go here
        pass

    def _get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get execution history for workflow."""
        # Implementation would go here
        pass

    def _process_performance_analysis(self, result: Any) -> Dict[str, Any]:
        """Process performance analysis results."""
        # Implementation would go here
        pass

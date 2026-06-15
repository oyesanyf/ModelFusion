"""
Intelligent Integration System
Uses LangExtract for understanding relationships between files and processes.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class IntegrationResult:
    """Result of integration analysis."""
    relationships: Dict[str, List[str]]
    dependencies: Dict[str, List[str]]
    compatibility_score: float
    integration_points: List[Dict[str, Any]]
    success: bool
    processing_time_ms: float
    error_message: Optional[str] = None

class IntelligentIntegration:
    """Core system for intelligent integration."""
    
    def __init__(self):
        # LangExtract is available as module functions, not a class
        if LANGEXTRACT_AVAILABLE:
            logger.info("LangExtract available for intelligent integration")
        else:
            logger.warning("LangExtract not available. Install with: pip install langextract")
        
        self.integration_history: List[Dict[str, Any]] = []
    
    async def analyze_integration(self, 
                                source: Any,
                                target: Any,
                                context: Dict[str, Any] = None) -> IntegrationResult:
        """Analyze integration between source and target."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not LANGEXTRACT_AVAILABLE:
                raise ImportError("LangExtract is required for integration analysis")

            # Create integration analysis prompt
            analysis_prompt = f"""
            Analyze integration between source and target:
            1. Direct relationships and dependencies
            2. Integration points and interfaces
            3. Compatibility requirements
            4. Potential conflicts
            5. Integration patterns
            
            Source:
            {self._format_content(source)}
            
            Target:
            {self._format_content(target)}
            
            Context:
            {self._format_context(context) if context else 'No additional context'}
            """

            # Get API key
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")
            
            # Use LangExtract for analysis
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=analysis_prompt,
                prompt_description="Integration Analysis",
                examples=self._get_integration_examples(),
                override_api_key=lx_api_key
            )

            # Process results
            relationships = self._extract_relationships(result)
            dependencies = self._extract_dependencies(result)
            compatibility = self._calculate_compatibility(result)
            integration_points = self._extract_integration_points(result)

            # Store in history
            self.integration_history.append({
                'timestamp': datetime.now(),
                'source': str(source),
                'target': str(target),
                'relationships': relationships,
                'compatibility': compatibility
            })

            # Calculate processing time
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return IntegrationResult(
                relationships=relationships,
                dependencies=dependencies,
                compatibility_score=compatibility,
                integration_points=integration_points,
                success=True,
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Error in integration analysis: {e}")
            return IntegrationResult(
                relationships={},
                dependencies={},
                compatibility_score=0.0,
                integration_points=[],
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    async def optimize_integration(self, 
                                 source: Any,
                                 target: Any,
                                 optimization_goals: Dict[str, float]) -> Dict[str, Any]:
        """Optimize integration between source and target."""
        try:
            # Create optimization prompt
            optimization_prompt = f"""
            Optimize integration based on goals:
            {self._format_optimization_goals(optimization_goals)}
            
            Consider:
            1. Performance optimization
            2. Resource efficiency
            3. Error handling
            4. Scalability
            5. Maintainability
            
            Source:
            {self._format_content(source)}
            
            Target:
            {self._format_content(target)}
            """

            # Use LangExtract for optimization
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=optimization_prompt,
                prompt_description="Integration Optimization Analysis",
                examples=[
                    lx.data.ExampleData(
                        text="Optimize integration between Module A and Module B for performance.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="optimization_recommendation",
                                extraction_text="implement caching layer",
                                attributes={
                                    "target": "Module A <-> Module B",
                                    "impact": "latency_reduction",
                                    "confidence": 0.9
                                }
                            )
                        ]
                    )
                ],
                override_api_key=lx_api_key
            )

            return self._process_optimization_results(result)

        except Exception as e:
            logger.error(f"Error optimizing integration: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def validate_integration(self, 
                                 source: Any,
                                 target: Any,
                                 validation_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate integration between source and target."""
        try:
            # Create validation prompt
            validation_prompt = f"""
            Validate integration against rules:
            {self._format_validation_rules(validation_rules)}
            
            Check:
            1. Interface compatibility
            2. Data consistency
            3. Error handling
            4. Performance requirements
            5. Security constraints
            
            Source:
            {self._format_content(source)}
            
            Target:
            {self._format_content(target)}
            """

            # Use LangExtract for validation
            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=validation_prompt,
                prompt_description="Integration Validation Analysis",
                examples=[
                    lx.data.ExampleData(
                        text="Validate integration of API endpoint. Expected: 200 OK. Actual: 500 Internal Server Error.",
                        extractions=[
                            lx.data.Extraction(
                                extraction_class="validation_result",
                                extraction_text="integration failure",
                                attributes={
                                    "status": "failed",
                                    "reason": "server_error",
                                    "confidence": 0.95
                                }
                            )
                        ]
                    )
                ],
                override_api_key=lx_api_key
            )

            return self._process_validation_results(result)

        except Exception as e:
            logger.error(f"Error validating integration: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_integration_history(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get integration history."""
        if source:
            return [
                entry for entry in self.integration_history
                if entry['source'] == source
            ]
        return self.integration_history

    def _format_content(self, content: Any) -> str:
        """Format content for analysis."""
        if isinstance(content, (str, Path)):
            return str(content)
        return str(content)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information."""
        return "\n".join(f"{k}: {v}" for k, v in context.items())

    def _format_optimization_goals(self, goals: Dict[str, float]) -> str:
        """Format optimization goals."""
        return "\n".join(f"{k}: {v}" for k, v in goals.items())

    def _format_validation_rules(self, rules: List[Dict[str, Any]]) -> str:
        """Format validation rules."""
        return "\n".join(
            f"Rule {i+1}: {rule.get('description', '')}"
            for i, rule in enumerate(rules)
        )

    def _get_integration_examples(self) -> List[Any]:
        """Get examples for integration analysis."""
        return [
            lx.data.ExampleData(
                text="Integrate data processing module with storage system",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="relationship",
                        extraction_text="data flow dependency",
                        attributes={
                            "type": "data_dependency",
                            "strength": 0.9
                        }
                    ),
                    lx.data.Extraction(
                        extraction_class="integration_point",
                        extraction_text="data storage interface",
                        attributes={
                            "type": "api",
                            "compatibility": 0.95
                        }
                    )
                ]
            )
        ]

    def _extract_relationships(self, result: Any) -> Dict[str, List[str]]:
        """Extract relationships from analysis result."""
        relationships = {}
        for extraction in result.extractions:
            if extraction.extraction_class == "relationship":
                rel_type = extraction.attributes.get("type", "unknown")
                if rel_type not in relationships:
                    relationships[rel_type] = []
                relationships[rel_type].append(extraction.extraction_text)
        return relationships

    def _extract_dependencies(self, result: Any) -> Dict[str, List[str]]:
        """Extract dependencies from analysis result."""
        dependencies = {}
        for extraction in result.extractions:
            if extraction.extraction_class == "dependency":
                dep_type = extraction.attributes.get("type", "unknown")
                if dep_type not in dependencies:
                    dependencies[dep_type] = []
                dependencies[dep_type].append(extraction.extraction_text)
        return dependencies

    def _calculate_compatibility(self, result: Any) -> float:
        """Calculate compatibility score from analysis result."""
        scores = []
        for extraction in result.extractions:
            if "compatibility" in extraction.attributes:
                scores.append(extraction.attributes["compatibility"])
        return sum(scores) / len(scores) if scores else 0.0

    def _extract_integration_points(self, result: Any) -> List[Dict[str, Any]]:
        """Extract integration points from analysis result."""
        points = []
        for extraction in result.extractions:
            if extraction.extraction_class == "integration_point":
                points.append({
                    'type': extraction.attributes.get("type", "unknown"),
                    'description': extraction.extraction_text,
                    'compatibility': extraction.attributes.get("compatibility", 0.0)
                })
        return points

    def _process_optimization_results(self, result: Any) -> Dict[str, Any]:
        """Process optimization analysis results."""
        optimizations = []
        for extraction in result.extractions:
            if extraction.extraction_class == "optimization":
                optimizations.append({
                    'type': extraction.attributes.get("type", "unknown"),
                    'description': extraction.extraction_text,
                    'impact': extraction.attributes.get("impact", 0.0)
                })
        return {
            'success': True,
            'optimizations': optimizations
        }

    def _process_validation_results(self, result: Any) -> Dict[str, Any]:
        """Process validation results."""
        validations = []
        for extraction in result.extractions:
            if extraction.extraction_class == "validation":
                validations.append({
                    'rule': extraction.attributes.get("rule", "unknown"),
                    'status': extraction.extraction_text,
                    'confidence': extraction.attributes.get("confidence", 0.0)
                })
        return {
            'success': True,
            'validations': validations
        }
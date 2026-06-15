"""
Adaptive Learning System
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import textwrap
from datetime import datetime

# Remove module-level langextract import to prevent early initialization
# LANGEXTRACT_AVAILABLE will be checked when needed

logger = logging.getLogger(__name__)

@dataclass
class LearningResult:
    feedback: Dict[str, Any]
    adaptation_strategy: str
    confidence: float
    error_message: Optional[str] = None

class AdaptiveLearning:
    """Adaptive Learning System that improves based on processing history."""

    def __init__(self):
        self._lang_extract_available = None
        self.learning_history: List[Dict[str, Any]] = []
    
    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
            except ImportError:
                self._lang_extract_available = False
        return self._lang_extract_available

    async def process_with_learning(self,
                                    data: str,
                                    task_description: str,
                                    previous_feedback: Optional[Dict[str, Any]] = None) -> LearningResult:
        """Process data, learn from feedback, and adapt strategy."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for adaptive learning")

            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            learning_prompt = f"""
            Analyze the provided data and task. Given previous feedback, suggest an adaptation strategy.
            Extract feedback analysis, and a proposed adaptation strategy with confidence.

            Data:
            {data}

            Task:
            {task_description}

            Previous Feedback:
            {previous_feedback if previous_feedback else 'No previous feedback'}
            """

            examples = [
                {
                    "data": "High CPU usage",
                    "task": "Optimize performance",
                    "feedback": "Previous attempt failed",
                    "feedback_summary": "Identified root cause as insufficient memory",
                    "adaptation": "increase_memory_allocation",
                    "confidence": 0.95
                },
                {
                    "data": "Normal performance",
                    "task": "Maintain stability",
                    "feedback": "System working well",
                    "feedback_summary": "No changes needed",
                    "adaptation": "no_change",
                    "confidence": 0.8
                }
            ]

            # Use the wrapper for consistent configuration
            result = extract_with_config(
                lx,
                text_or_documents=learning_prompt,
                prompt_description="Adaptive Learning Analysis",
                examples=examples
            )

            feedback_analysis = {}
            adaptation_strategy = "no_change"
            confidence = 0.0

            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "learning_feedback":
                        if hasattr(extraction, 'attributes') and extraction.attributes:
                            attrs = extraction.attributes
                            feedback_analysis = attrs.get('feedback_summary', {}) if isinstance(attrs, dict) else {}
                            adaptation_strategy = attrs.get('adaptation', "no_change") if isinstance(attrs, dict) else "no_change"
                            confidence = attrs.get('confidence', 0.0) if isinstance(attrs, dict) else 0.0
                        break

            return LearningResult(
                feedback=feedback_analysis,
                adaptation_strategy=adaptation_strategy,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error in adaptive learning: {e}")
            return LearningResult(
                feedback={},
                adaptation_strategy="no_change",
                confidence=0.0,
                error_message=str(e)
            )

    async def learn_from_context(self, context: Dict[str, Any]) -> LearningResult:
        """Learn from context and adapt strategies."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for adaptive learning (learn_from_context)")

            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            context_str = str(context)
            learning_prompt = f"""
            Analyze the provided context and extract learning insights.
            Identify patterns, improvements, and adaptation strategies.

            Context:
            {context_str}
            """

            examples = [
                lx.data.ExampleData(
                    text="High error rate in processing",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="learning_insight",
                            extraction_text="Need better error handling",
                            attributes={
                                "insights": "High error rate detected",
                                "adaptation": "implement_retry_logic",
                                "confidence": 0.9
                            }
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="Fast processing, low errors",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="learning_insight",
                            extraction_text="System performing well",
                            attributes={
                                "insights": "System performing optimally",
                                "adaptation": "maintain_current_approach",
                                "confidence": 0.8
                            }
                        )
                    ]
                )
            ]

            # Use the wrapper for consistent configuration
            result = extract_with_config(
                lx,
                text_or_documents=context_str,
                prompt_description="Adaptive Learning Context Analysis",
                examples=examples
            )

            feedback_analysis = {}
            adaptation_strategy = "no_change"
            confidence = 0.0

            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "learning_insight":
                        if hasattr(extraction, 'attributes') and extraction.attributes:
                            attrs = extraction.attributes
                            feedback_analysis = attrs.get('insights', {}) if isinstance(attrs, dict) else {}
                            adaptation_strategy = attrs.get('adaptation', "no_change") if isinstance(attrs, dict) else "no_change"
                            confidence = attrs.get('confidence', 0.0) if isinstance(attrs, dict) else 0.0
                        break

            return LearningResult(
                feedback=feedback_analysis,
                adaptation_strategy=adaptation_strategy,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error in adaptive learning (learn_from_context): {e}")
            return LearningResult(
                feedback={},
                adaptation_strategy="no_change",
                confidence=0.0,
                error_message=str(e)
            )
"""
Predictive Capabilities System
Uses LangExtract for advanced prediction and issue prevention.
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
class PredictionResult:
    prediction_type: str
    predicted_value: Any
    confidence: float
    explanation: str
    error_message: Optional[str] = None

class PredictiveCapabilities:
    """Core system for prediction and issue prevention using LangExtract."""

    def __init__(self):
        self._lang_extract_available = None
        self.prediction_history: List[PredictionResult] = []
    
    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
                logger.info("LangExtract available for predictive analysis")
            except ImportError:
                self._lang_extract_available = False
                logger.warning("LangExtract not available. Install with: pip install langextract")
        return self._lang_extract_available

    async def predict_issues(self,
                             current_state_description: str,
                             historical_data: List[Dict[str, Any]] = None) -> PredictionResult:
        """Predict potential issues based on current state and historical data."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for predictive analysis")

            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config

            analysis_prompt = f"""
            Analyze the current system state and historical data to predict potential issues.
            Extract the issue type, a confidence score, and a brief explanation.

            Current State:
            {current_state_description}

            Historical Data:
            {historical_data if historical_data else 'No historical data provided'}
            """

            # Define examples for prediction extraction using proper LangExtract format
            examples = [
                lx.data.ExampleData(
                    text="High error rate in processing",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="prediction",
                            extraction_text="processing_failure",
                            attributes={
                                "confidence": 0.9,
                                "explanation": "High error rate indicates potential system failure"
                            }
                        )
                    ]
                ),
                lx.data.ExampleData(
                    text="System performance is optimal",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="prediction",
                            extraction_text="stable_performance",
                            attributes={
                                "confidence": 0.8,
                                "explanation": "Optimal performance suggests continued stability"
                            }
                        )
                    ]
                )
            ]

            # Use the wrapper for consistent configuration
            result = extract_with_config(
                lx,
                text_or_documents=current_state_description,
                prompt_description=analysis_prompt,
                examples=examples
            )

            if hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and extraction.extraction_class == "prediction":
                        return PredictionResult(
                            prediction_type=extraction.extraction_text,
                            predicted_value=extraction.extraction_text,
                            confidence=extraction.attributes.get('confidence', 0.0) if hasattr(extraction, 'attributes') else 0.0,
                            explanation=extraction.attributes.get('explanation', '') if hasattr(extraction, 'attributes') else ''
                        )
            return PredictionResult("no_issue_predicted", "N/A", 0.0, "No issues predicted based on current data.")

        except Exception as e:
            logger.error(f"Error in predictive analysis: {e}")
            return PredictionResult("error", str(e), 0.0, "An error occurred during prediction.", error_message=str(e))

    async def analyze_historical_patterns(self,
                                          data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze historical data to identify recurring patterns and trends."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for pattern analysis")
            
            data_text = "\n".join([str(d) for d in data])
            analysis_prompt = textwrap.dedent(f"""
            Analyze the historical data to identify recurring patterns, anomalies, and trends.
            Extract a list of identified patterns with their type and a brief description.

            Historical Data:
            {data_text}
            """)

            examples = [
                lx.data.ExampleData(
                    text="Data: [{ 'temp': 25, 'time': '10:00' }, { 'temp': 28, 'time': '11:00' }, { 'temp': 25, 'time': '12:00' }].",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="pattern",
                            extraction_text="Temperature fluctuation",
                            attributes={"type": "recurring", "description": "Temperature consistently rises then falls."}
                        )
                    ]
                )
            ]

            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")

            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=data_text,
                prompt_description=analysis_prompt,
                examples=examples,
                override_api_key=lx_api_key
            )

            patterns = []
            if result and result.extractions:
                for extraction in result.extractions:
                    if extraction.extraction_class == "pattern":
                        patterns.append({
                            "type": extraction.attributes.get('type', 'unknown'),
                            "description": extraction.extraction_text
                        })
            return patterns

        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
            return []

    async def predict_resource_needs(self,
                                     current_usage: Dict[str, Any],
                                     historical_usage: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict future resource needs based on current and historical usage."""
        try:
            if not self._check_langextract_available():
                raise ImportError("LangExtract is required for resource prediction")
            
            usage_text = f"Current: {current_usage}\nHistorical: {historical_usage}"
            analysis_prompt = textwrap.dedent(f"""
            Analyze current and historical resource usage to predict future resource needs.
            Specify resource (e.g., CPU, Memory, Storage) and predicted amount.

            Usage Data:
            {usage_text}
            """)

            examples = [
                lx.data.ExampleData(
                    text="Current: {'CPU': 0.8}. Historical: [{'CPU': 0.7}, {'CPU': 0.85}].",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="resource_prediction",
                            extraction_text="CPU",
                            attributes={"predicted_amount": 0.9, "unit": "%", "reason": "Increasing trend."}
                        )
                    ]
                )
            ]

            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')
            if not lx_api_key:
                raise ValueError("LANGEXTRACT_API_KEY not set")

            from hforchestra.utils.langextract_wrapper import extract_with_config
            result = extract_with_config(
                lx,
                text_or_documents=usage_text,
                prompt_description=analysis_prompt,
                examples=examples,
                override_api_key=lx_api_key
            )

            predictions = {}
            if result and result.extractions:
                for extraction in result.extractions:
                    if extraction.extraction_class == "resource_prediction":
                        predictions[extraction.extraction_text] = {
                            "amount": extraction.attributes.get('predicted_amount'),
                            "unit": extraction.attributes.get('unit'),
                            "reason": extraction.attributes.get('reason', '')
                        }
            return predictions

        except Exception as e:
            logger.error(f"Error predicting resource needs: {e}")
            return {}

"""
Temporal Awareness System
Uses LangExtract for understanding content evolution and temporal relationships.
"""

import asyncio
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class TemporalChange:
    """Represents a temporal change in content."""
    change_type: str
    before_state: str
    after_state: str
    timestamp: datetime
    impact_level: float
    related_changes: List[str]
    context: Dict[str, Any]
    confidence: float

@dataclass
class TemporalPattern:
    """Represents a detected temporal pattern."""
    pattern_type: str
    frequency: float
    confidence: float
    related_changes: List[str]
    metadata: Dict[str, Any]
    detected_at: datetime

@dataclass
class TemporalAnalysisResult:
    """Result of temporal analysis."""
    changes: List[TemporalChange]
    patterns: List[TemporalPattern]
    success: bool
    processing_time_ms: float
    error_message: Optional[str] = None

class TemporalAwareness:
    """Core system for temporal understanding using LangExtract."""
    
    def __init__(self):
        self.change_history: List[TemporalChange] = []
        self.pattern_history: List[TemporalPattern] = []
        
        if LANGEXTRACT_AVAILABLE:
            logger.info("LangExtract available for temporal analysis")
        else:
            logger.warning("LangExtract not available. Install with: pip install langextract")
    
    async def analyze_temporal_changes(self, 
                                   current_state: str,
                                   previous_states: List[Tuple[str, datetime]] = None) -> TemporalAnalysisResult:
        """Analyze temporal changes and patterns."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not LANGEXTRACT_AVAILABLE:
                raise ImportError("LangExtract is required for temporal analysis")

            if not current_state:
                raise ValueError("Current state cannot be None or empty")

            # Initialize empty lists
            changes = []
            patterns = []

            # Ensure previous_states is a list
            previous_states = previous_states or []

            # Create analysis prompt
            analysis_prompt = textwrap.dedent(f"""
            Analyze temporal changes and patterns in the following content.
            
            Current state:
            {current_state}
            
            Previous states:
            {self._format_previous_states(previous_states)}
            
            Focus on:
            1. Content changes and their types
            2. Impact levels of changes
            3. Related changes and dependencies
            4. Temporal patterns and frequencies
            5. Confidence levels
            """)

            # Prepare minimal examples
            examples = [
                lx.data.ExampleData(
                    text="initial state",
                    extractions=[
                        lx.data.Extraction(
                            extraction_class="temporal_change",
                            extraction_text="change",
                            attributes={}
                        )
                    ]
                )
            ] if LANGEXTRACT_AVAILABLE and hasattr(lx, 'data') else []

            # Resolve API key
            lx_api_key = os.getenv('LANGEXTRACT_API_KEY')

            # Process with LangExtract using correct signature (suppress noisy output)
            import io, contextlib
            buf_out, buf_err = io.StringIO(), io.StringIO()
            # Silence legacy announce prints
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                from hforchestra.utils.langextract_wrapper import extract_with_config
                result = extract_with_config(
                    lx,
                    text_or_documents=current_state,
                    prompt_description=analysis_prompt,
                    examples=examples,
                    override_api_key=lx_api_key
                )
            
            if result and hasattr(result, 'extractions') and result.extractions:
                for extraction in result.extractions:
                    # Object-style extractions (lx.data.Extraction)
                    if hasattr(extraction, 'extraction_class'):
                        ex_class = getattr(extraction, 'extraction_class', '')
                        attrs = getattr(extraction, 'attributes', {}) or {}
                        if ex_class == 'temporal_change':
                            change = self._create_temporal_change({
                                'change_type': attrs.get('change_type', 'unknown'),
                                'before_state': attrs.get('before_state', ''),
                                'after_state': attrs.get('after_state', ''),
                                'impact_level': attrs.get('impact_level', 0.0),
                                'related_changes': attrs.get('related_changes', []),
                                'context': attrs.get('context', {}),
                                'confidence': attrs.get('confidence', 0.0)
                            })
                            if change:
                                changes.append(change)
                                self.change_history.append(change)
                        elif ex_class == 'temporal_pattern':
                            pattern = self._create_temporal_pattern({
                                'pattern_type': attrs.get('pattern_type', 'unknown'),
                                'frequency': attrs.get('frequency', 0.0),
                                'confidence': attrs.get('confidence', 0.0),
                                'related_changes': attrs.get('related_changes', []),
                                'metadata': attrs.get('metadata', {})
                            })
                            if pattern:
                                patterns.append(pattern)
                                self.pattern_history.append(pattern)
                    # Dict-style extractions
                    elif isinstance(extraction, dict):
                        if extraction.get('type') == 'temporal_change':
                            change = self._create_temporal_change(extraction)
                            if change:
                                changes.append(change)
                                self.change_history.append(change)
                        elif extraction.get('type') == 'temporal_pattern':
                            pattern = self._create_temporal_pattern(extraction)
                            if pattern:
                                patterns.append(pattern)
                                self.pattern_history.append(pattern)

            # Ensure we always return lists
            changes = changes if changes is not None else []
            patterns = patterns if patterns is not None else []

            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return TemporalAnalysisResult(
                changes=changes,
                patterns=patterns,
                success=True,
                processing_time_ms=processing_time
            )

        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Error in temporal analysis: {e}")
            return TemporalAnalysisResult(
                changes=[],
                patterns=[],
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    def _format_previous_states(self, states: List[Tuple[str, datetime]]) -> str:
        """Format previous states for analysis."""
        if not states:
            return "No previous states available"
            
        return "\n\n".join(
            f"State at {timestamp}:\n{state}"
            for state, timestamp in states
        )

    def _create_temporal_change(self, extraction: Dict[str, Any]) -> Optional[TemporalChange]:
        """Create a TemporalChange object from extraction data."""
        try:
            return TemporalChange(
                change_type=extraction.get('change_type', 'unknown'),
                before_state=extraction.get('before_state', ''),
                after_state=extraction.get('after_state', ''),
                timestamp=datetime.now(),
                impact_level=float(extraction.get('impact_level', 0.0)),
                related_changes=extraction.get('related_changes', []),
                context=extraction.get('context', {}),
                confidence=float(extraction.get('confidence', 0.0))
            )
        except Exception as e:
            logger.error(f"Error creating temporal change: {e}")
            return None

    def _create_temporal_pattern(self, extraction: Dict[str, Any]) -> Optional[TemporalPattern]:
        """Create a TemporalPattern object from extraction data."""
        try:
            return TemporalPattern(
                pattern_type=extraction.get('pattern_type', 'unknown'),
                frequency=float(extraction.get('frequency', 0.0)),
                confidence=float(extraction.get('confidence', 0.0)),
                related_changes=extraction.get('related_changes', []),
                metadata=extraction.get('metadata', {}),
                detected_at=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error creating temporal pattern: {e}")
            return None

    def get_recent_changes(self, time_window: timedelta = timedelta(hours=24)) -> List[TemporalChange]:
        """Get recent changes within the specified time window."""
        cutoff_time = datetime.now() - time_window
        return [
            change for change in self.change_history
            if change.timestamp >= cutoff_time
        ]

    def get_patterns_by_type(self, pattern_type: str) -> List[TemporalPattern]:
        """Get patterns of a specific type."""
        return [
            pattern for pattern in self.pattern_history
            if pattern.pattern_type == pattern_type
        ]
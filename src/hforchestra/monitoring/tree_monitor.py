"""
Enhanced Tree Monitor for decision tracking and evaluation.

This module provides monitoring capabilities for tracking decision quality,
adaptive threshold management, and ATLAS threat detection integration.
"""

import re
import statistics
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

try:
    from ..security.atlas_detector import ATLASThreatDetector
except ImportError:
    from security.atlas_detector import ATLASThreatDetector


@dataclass
class DecisionMetrics:
    """Enhanced metrics for decision tracking"""
    thought: str
    score: int
    confidence: float
    timestamp: datetime
    depth: int
    branch_id: str
    reason: Optional[str] = None
    category: Optional[str] = None
    recovery_attempted: bool = False
    improvement_suggestion: Optional[str] = None
    atlas_threats: Optional[List[Dict[str, str]]] = None


class AdaptiveThresholdManager:
    """Manages adaptive thresholds for decision quality evaluation."""
    
    def __init__(self, initial_threshold: float = 4.0, adaptation_rate: float = 0.1):
        self.threshold = initial_threshold
        self.adaptation_rate = adaptation_rate
        self.score_history = deque(maxlen=50)

    def update_threshold(self, scores: List[int]):
        """Updates the threshold based on recent score history."""
        self.score_history.extend(scores)
        if len(self.score_history) >= 10:
            mean_score = statistics.mean(self.score_history)
            std_dev = statistics.stdev(self.score_history) if len(self.score_history) > 1 else 1.0
            new_threshold = max(1.0, mean_score - 1.5 * std_dev)
            self.threshold += (new_threshold - self.threshold) * self.adaptation_rate
        return self.threshold


class EnhancedTreeMonitor:
    """The core monitoring system for tracking decision quality and threats."""
    
    def __init__(self, llm, initial_threshold: float = 4.0):
        self.llm = llm
        self.threshold_manager = AdaptiveThresholdManager(initial_threshold)
        self.atlas_detector = ATLASThreatDetector()
        self.decisions_log: List[DecisionMetrics] = []
        self.session_stats = defaultdict(int)
        self.session_stats['start_time'] = datetime.now()

    def evaluate_thoughts(self, thoughts: List[str], context: str, depth: int) -> List[Dict[str, Any]]:
        """Evaluates a list of thoughts for quality and potential threats."""
        evaluated_thoughts = []
        scores = []
        for i, thought in enumerate(thoughts):
            atlas_threats = self.atlas_detector.scan_thought(thought)
            
            # Get score from LLM
            try:
                if hasattr(self.llm, 'invoke'):
                    # LangChain ChatOpenAI (synchronous)
                    score_str = self.llm.invoke(f"Rate this step: '{thought}'. 1-10. Just the number.").content
                    confidence_str = self.llm.invoke(f"Confidence in this step: '{thought}'. 0.0-1.0.").content
                    category = self.llm.invoke(f"Categorize this step: '{thought}'. Choose ONE: analysis, processing, generation, evaluation.").content.lower().strip()
                else:
                    # SimpleHuggingFaceLLM fallback (simplified synchronous version)
                    score_str = str(5 + (hash(thought) % 5))  # Simple hash-based scoring for demo
                    confidence_str = "0.7"
                    category = "analysis"
                
                score = int(re.search(r'\d+', score_str).group()) if re.search(r'\d+', score_str) else 1
                confidence = float(re.search(r'(\d\.\d+)', confidence_str).group()) if re.search(r'(\d\.\d+)', confidence_str) else 0.5
            except Exception as e:
                print(f"[WARN] Error evaluating thought: {e}")
                score = 5  # Default score
                confidence = 0.5
                category = "unknown"
            
            scores.append(score)

            decision = DecisionMetrics(
                thought=thought, score=score, confidence=confidence, timestamp=datetime.now(),
                depth=depth, branch_id=f"{depth}-{i}", category=category, atlas_threats=atlas_threats
            )
            
            current_threshold = self.threshold_manager.update_threshold(scores)
            
            if score <= current_threshold or confidence < 0.3 or atlas_threats:
                self._handle_bad_decision(decision, context)

            self.decisions_log.append(decision)
            self.session_stats['total_decisions'] += 1
            
            final_score = 1 if atlas_threats else score
            evaluated_thoughts.append({"thought": thought, "score": final_score})
            
        return evaluated_thoughts

    def _handle_bad_decision(self, decision: DecisionMetrics, context: str):
        """Handles decisions that fall below quality thresholds."""
        self.session_stats['bad_decisions'] += 1
        if decision.atlas_threats:
            self.session_stats['atlas_threats_found'] += 1
            threat_names = ", ".join([t['name'] for t in decision.atlas_threats])
            decision.reason = f"ATLAS Threat Detected: {threat_names}"
            print(f"🚨 CRITICAL ALERT: Potential dangerous task detected.\n   Thought: '{decision.thought[:100]}...'\n   Reason: {decision.reason}")
            return

        try:
            if hasattr(self.llm, 'invoke'):
                decision.reason = self.llm.invoke(f"Briefly explain why this step is weak: '{decision.thought}'").content
                recovery_prompt = f"The following step was weak: '{decision.thought}'. Reason: {decision.reason}. Suggest a better, more specific step for the goal: {context}"
                recovery = self.llm.invoke(recovery_prompt).content
            else:
                decision.reason = "Quality below threshold or low confidence"
                recovery = "Consider more specific and detailed approach"
            
            print(f"[TOOL] Recovery suggested for: '{decision.thought[:50]}...'\n   Better alternative: '{recovery}'")
            self.session_stats['recoveries_attempted'] += 1
        except Exception as e:
            decision.reason = f"Evaluation failed: {e}"
            print(f"[WARN] Could not evaluate bad decision: {e}")

    def get_session_report(self) -> Dict[str, Any]:
        """Generates a session report with statistics."""
        duration = (datetime.now() - self.session_stats['start_time']).total_seconds()
        return {
            "session_duration_seconds": round(duration),
            "total_decisions": self.session_stats['total_decisions'],
            "bad_decisions": self.session_stats['bad_decisions'],
            "atlas_threats_found": self.session_stats['atlas_threats_found'],
            "final_threshold": f"{self.threshold_manager.threshold:.2f}",
        } 
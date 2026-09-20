#!/usr/bin/env python3
"""
Base RL Adapter definition for HugOS ReST-RL / GRPO subsystem.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Dict, Any

from ..hardware_profiler import HardwareTier
from ..sandbox import SandboxResult, VerificationSandbox


@dataclass
class RLTask:
    task_id: str
    target_file: str
    test_target: str
    workspace_root: str
    instruction: str = ""
    original_code: str = ""
    target_filename: str = "solution.py"

    def __post_init__(self):
        # Resolve target_file against workspace_root if relative
        resolved_target = self.target_file
        if resolved_target and not os.path.isabs(resolved_target) and self.workspace_root:
            candidate_abs = os.path.join(self.workspace_root, resolved_target)
            if os.path.isfile(candidate_abs):
                resolved_target = candidate_abs

        if not self.original_code and resolved_target and os.path.isfile(resolved_target):
            try:
                with open(resolved_target, "r", encoding="utf-8") as f:
                    self.original_code = f.read()
            except Exception:
                pass

        if not self.target_filename:
            self.target_filename = os.path.basename(self.target_file) if self.target_file else "solution.py"


@dataclass
class RolloutResult:
    task_id: str
    best_candidate: str
    best_reward: float
    iterations_completed: int
    total_iterations: int
    is_complete: bool
    status: str  # "COMPLETED", "PAUSED", "IN_PROGRESS", "FAILED"
    sandbox_result: Optional[SandboxResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.sandbox_result:
            d["sandbox_result"] = self.sandbox_result.to_dict()
        return d


class BaseRLAdapter(ABC):
    """Abstract base class for all tier RL reasoning adapters."""

    def __init__(
        self,
        tier: HardwareTier,
        model_name: str,
        sandbox: Optional[VerificationSandbox] = None,
        config: Optional[dict] = None,
    ):
        self.tier = tier
        self.model_name = model_name
        self.sandbox = sandbox or VerificationSandbox()
        self.config = config or {}
        self._task_states: Dict[str, Any] = {}

    def get_task_state(self, task_id: str) -> Optional[Any]:
        return self._task_states.get(task_id)

    def save_task_state(self, task_id: str, state: Any) -> None:
        self._task_states[task_id] = state

    def clear_task_state(self, task_id: str) -> None:
        self._task_states.pop(task_id, None)

    @abstractmethod
    def run_rollout(
        self,
        task: RLTask,
        is_paused: Callable[[], bool],
        max_iterations: Optional[int] = None,
    ) -> RolloutResult:
        """
        Executes reasoning rollout steps. Must check `is_paused()` between each
        atomic iteration/expansion step. If paused, saves state and returns status='PAUSED'.
        """
        pass

    @abstractmethod
    def checkpoint(self) -> Dict[str, Any]:
        """Saves current search/optimization state for resumption."""
        pass

    @abstractmethod
    def restore(self, state: Dict[str, Any]) -> None:
        """Restores previous search state."""
        pass

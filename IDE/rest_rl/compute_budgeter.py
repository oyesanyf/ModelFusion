#!/usr/bin/env python3
"""
Compute Budgeter for ReST-RL / GRPO Autonomous Collaborator.

Features:
1. Cyclomatic complexity & AST depth scoring.
2. Anytime mini-batching (B=2) for responsive preemption.
3. Time/iteration-decaying exploration constant c(t) for MCTS.
4. Battery-aware compute scaling via psutil.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger("rest_rl.compute_budgeter")


@dataclass
class TaskComplexityScore:
    cyclomatic_complexity: int
    ast_depth: int
    lines_of_code: int
    estimated_difficulty: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommended_iterations: int
    recommended_timeout: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ComputeBudgeter:
    """Dynamically scales reasoning budgets, exploration rates, and batches based on task and hardware state."""

    MIN_BATCH_SIZE = 2  # Anytime mini-batch size B=2

    def __init__(
        self,
        base_iterations: int = 16,
        base_exploration_c: float = 1.414,
        min_exploration_c: float = 0.35,
    ):
        self.base_iterations = base_iterations
        self.base_exploration_c = base_exploration_c
        self.min_exploration_c = min_exploration_c

    @staticmethod
    def compute_complexity(code_str: str) -> TaskComplexityScore:
        """
        Calculates McCabe cyclomatic complexity and maximum AST tree depth.
        M = Decision points + 1.
        """
        if not code_str or not code_str.strip():
            return TaskComplexityScore(
                cyclomatic_complexity=1,
                ast_depth=1,
                lines_of_code=0,
                estimated_difficulty="LOW",
                recommended_iterations=4,
                recommended_timeout=3.0,
            )

        loc = len([line for line in code_str.splitlines() if line.strip() and not line.strip().startswith("#")])

        try:
            tree = ast.parse(code_str)
        except Exception:
            return TaskComplexityScore(
                cyclomatic_complexity=1,
                ast_depth=1,
                lines_of_code=loc,
                estimated_difficulty="LOW",
                recommended_iterations=8,
                recommended_timeout=3.0,
            )

        decision_points = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)):
                decision_points += 1
            elif isinstance(node, ast.BoolOp):
                decision_points += max(0, len(node.values) - 1)

        cyclomatic = decision_points + 1

        # Calculate AST max depth
        def _get_depth(n: ast.AST, current: int = 1) -> int:
            children = list(ast.iter_child_nodes(n))
            if not children:
                return current
            return max(_get_depth(c, current + 1) for c in children)

        max_depth = _get_depth(tree)

        # Categorize difficulty
        if cyclomatic <= 2 and max_depth <= 4:
            difficulty = "LOW"
            iterations = 8
            timeout = 3.0
        elif cyclomatic <= 5 and max_depth <= 7:
            difficulty = "MEDIUM"
            iterations = 16
            timeout = 5.0
        elif cyclomatic <= 10 and max_depth <= 10:
            difficulty = "HIGH"
            iterations = 24
            timeout = 7.0
        else:
            difficulty = "CRITICAL"
            iterations = 32
            timeout = 10.0

        return TaskComplexityScore(
            cyclomatic_complexity=cyclomatic,
            ast_depth=max_depth,
            lines_of_code=loc,
            estimated_difficulty=difficulty,
            recommended_iterations=iterations,
            recommended_timeout=timeout,
        )

    def get_exploration_c(
        self,
        current_iteration: int,
        total_iterations: int,
    ) -> float:
        """
        Computes time/iteration-decaying exploration constant c(t) for MCTS UCB1.
        Decays from base_exploration_c (e.g. 1.414) down to min_exploration_c (e.g. 0.35)
        as search progresses, shifting from exploration to exploitation.
        """
        if total_iterations <= 1 or current_iteration <= 0:
            return self.base_exploration_c

        progress = min(1.0, current_iteration / total_iterations)
        c_t = self.min_exploration_c + (self.base_exploration_c - self.min_exploration_c) * (1.0 - progress)
        return round(c_t, 4)

    @classmethod
    def get_minibatch_size(cls) -> int:
        """Returns anytime mini-batch size (B=2) for fast preemption."""
        return cls.MIN_BATCH_SIZE

    @staticmethod
    def get_battery_profile() -> Dict[str, Any]:
        """
        Evaluates battery and power status via psutil to throttle compute on mobile/unplugged laptops.
        """
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return {
                    "has_battery": False,
                    "power_plugged": True,
                    "percent": 100.0,
                    "scale_factor": 1.0,
                    "throttle_sleep_sec": 0.0,
                }

            power_plugged = battery.power_plugged is not False
            pct = battery.percent

            if not power_plugged:
                # Laptop running on battery
                if pct < 20.0:
                    scale = 0.25  # Severe battery conservation: 25% compute
                    sleep_sec = 0.1
                else:
                    scale = 0.50  # Moderate battery conservation: 50% compute
                    sleep_sec = 0.05
            else:
                scale = 1.0
                sleep_sec = 0.0

            return {
                "has_battery": True,
                "power_plugged": power_plugged,
                "percent": round(pct, 1),
                "scale_factor": scale,
                "throttle_sleep_sec": sleep_sec,
            }

        except Exception as e:
            logger.debug("Failed to query battery sensors: %s", e)
            return {
                "has_battery": False,
                "power_plugged": True,
                "percent": 100.0,
                "scale_factor": 1.0,
                "throttle_sleep_sec": 0.0,
            }

    def allocate_task_budget(self, code_str: str, override_iterations: Optional[int] = None) -> Dict[str, Any]:
        """
        Computes composite resource budget combining task complexity and host battery status.
        """
        complexity = self.compute_complexity(code_str)
        battery = self.get_battery_profile()

        base_iters = override_iterations or complexity.recommended_iterations
        scaled_iters = max(2, int(base_iters * battery["scale_factor"]))

        return {
            "allocated_iterations": scaled_iters,
            "minibatch_size": self.MIN_BATCH_SIZE,
            "timeout_sec": complexity.recommended_timeout,
            "complexity": complexity.to_dict(),
            "battery": battery,
        }

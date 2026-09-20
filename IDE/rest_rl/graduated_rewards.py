#!/usr/bin/env python3
"""
Graduated Continuous Dense Verification Signal for ReST-RL / GRPO.

Calculates continuous 4-tier dense rewards:
    R(c) = w_ast * S_ast + w_diag * S_diag + w_reg * S_reg + w_test * S_test

Where:
    - w_ast (0.15): AST syntax and security validity barrier
    - w_diag (0.25): Diagnostic count reduction relative to baseline
    - w_reg (0.25): Workspace regression test pass rate
    - w_test (0.35): Target unit test assertion pass rate
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List, Tuple

from .sandbox import VerificationSandbox, SandboxResult

logger = logging.getLogger("rest_rl.graduated_rewards")


@dataclass
class GraduatedRewardBreakdown:
    s_ast: float
    s_diag: float
    s_reg: float
    s_test: float
    total_reward: float
    is_perfect: bool
    weights: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraduatedRewardEvaluator:
    """Evaluates multi-tier continuous dense rewards for candidate code rollouts."""

    def __init__(
        self,
        sandbox: Optional[VerificationSandbox] = None,
        w_ast: float = 0.15,
        w_diag: float = 0.25,
        w_reg: float = 0.25,
        w_test: float = 0.35,
    ):
        self.sandbox = sandbox or VerificationSandbox()
        self.w_ast = w_ast
        self.w_diag = w_diag
        self.w_reg = w_reg
        self.w_test = w_test

        # Normalize weights if sum != 1.0
        w_sum = self.w_ast + self.w_diag + self.w_reg + self.w_test
        if abs(w_sum - 1.0) > 1e-4 and w_sum > 0:
            self.w_ast /= w_sum
            self.w_diag /= w_sum
            self.w_reg /= w_sum
            self.w_test /= w_sum

    def compute_ast_signal(self, code_str: str) -> Tuple[float, Optional[str]]:
        """
        Tier 1: AST Validity & Security Barrier.
        Returns (1.0, None) if code parses and passes security checks; (0.0, reason) otherwise.
        """
        is_safe, err = self.sandbox.validate_code_ast(code_str)
        return (1.0, None) if is_safe else (0.0, err)

    def compute_diagnostic_signal(
        self,
        orig_diag_count: int,
        new_diag_count: int,
    ) -> float:
        """
        Tier 2: Diagnostic Count Reduction.
        Measures compiler/linter error reduction relative to the original failing code.
        """
        if orig_diag_count > 0:
            # Fraction of diagnostics resolved
            reduction = (orig_diag_count - new_diag_count) / orig_diag_count
            return max(0.0, min(1.0, reduction))
        else:
            # Baseline had no diagnostics; penalize any newly introduced diagnostics
            return 1.0 if new_diag_count == 0 else max(0.0, 1.0 - 0.25 * new_diag_count)

    def compute_regression_signal(
        self,
        passed_regressions: int,
        total_regressions: int,
    ) -> float:
        """
        Tier 3: Workspace Regression Test Pass Rate.
        Ensures candidate does not break existing unchanged tests across the workspace.
        """
        if total_regressions <= 0:
            return 1.0
        return max(0.0, min(1.0, passed_regressions / total_regressions))

    def compute_target_test_signal(
        self,
        passed_assertions: int,
        total_assertions: int,
    ) -> float:
        """
        Tier 4: Target Unit Test Assertion Pass Rate.
        Measures progress against the failing test contract.
        """
        if total_assertions <= 0:
            return 0.0
        return max(0.0, min(1.0, passed_assertions / total_assertions))

    def evaluate(
        self,
        candidate_code: str,
        target_sandbox_result: SandboxResult,
        orig_diag_count: int = 0,
        new_diag_count: int = 0,
        passed_regressions: int = 0,
        total_regressions: int = 0,
    ) -> GraduatedRewardBreakdown:
        """
        Calculates the full 4-tier composite graduated dense reward.
        """
        # 1. AST Signal (Hard gate: if AST fails, total reward is 0.0)
        s_ast, ast_err = self.compute_ast_signal(candidate_code)
        if s_ast == 0.0:
            return GraduatedRewardBreakdown(
                s_ast=0.0,
                s_diag=0.0,
                s_reg=0.0,
                s_test=0.0,
                total_reward=0.0,
                is_perfect=False,
                weights=self.get_weights(),
                details={"error": ast_err, "stage": "AST_SECURITY_FAIL"},
            )

        # 2. Diagnostic Signal
        s_diag = self.compute_diagnostic_signal(orig_diag_count, new_diag_count)

        # 3. Regression Signal
        s_reg = self.compute_regression_signal(passed_regressions, total_regressions)

        # 4. Target Test Signal
        if target_sandbox_result.total_count > 0:
            s_test = self.compute_target_test_signal(
                target_sandbox_result.passed_count,
                target_sandbox_result.total_count,
            )
        else:
            s_test = target_sandbox_result.reward

        # Compute weighted linear combination
        total = (
            self.w_ast * s_ast
            + self.w_diag * s_diag
            + self.w_reg * s_reg
            + self.w_test * s_test
        )
        total = round(max(0.0, min(1.0, total)), 4)

        # Perfect resolution check: all signals must be 1.0
        is_perfect = (
            s_ast >= 1.0
            and s_diag >= 1.0
            and s_reg >= 1.0
            and s_test >= 1.0
            and target_sandbox_result.status == "PASSED"
        )
        if is_perfect:
            total = 1.0

        return GraduatedRewardBreakdown(
            s_ast=round(s_ast, 4),
            s_diag=round(s_diag, 4),
            s_reg=round(s_reg, 4),
            s_test=round(s_test, 4),
            total_reward=total,
            is_perfect=is_perfect,
            weights=self.get_weights(),
            details={
                "orig_diag_count": orig_diag_count,
                "new_diag_count": new_diag_count,
                "passed_regressions": passed_regressions,
                "total_regressions": total_regressions,
                "target_status": target_sandbox_result.status,
            },
        )

    def get_weights(self) -> Dict[str, float]:
        return {
            "w_ast": round(self.w_ast, 4),
            "w_diag": round(self.w_diag, 4),
            "w_reg": round(self.w_reg, 4),
            "w_test": round(self.w_test, 4),
        }

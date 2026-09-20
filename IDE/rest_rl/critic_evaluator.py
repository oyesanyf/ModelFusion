#!/usr/bin/env python3
"""
Critic Evaluator for HugOS ReST-RL / GRPO Background Subsystem.

Provides secondary candidate solution evaluation and scoring using:
1. Skywork/Skywork-Critic-Llama-3.1-8B on high-VRAM machines (>= 20,000 MB free VRAM).
2. Deterministic 4-tier graduated dense verification signal on CPU when under the
   strict 40% VRAM cap (< 20,000 MB free VRAM) to prevent OOM aborts.

CRITICAL INVARIANT: Never load independent secondary reward models concurrently
with policy models on systems with < 24 GB VRAM. When VRAM < 20,000 MB, execution
is strictly confined to CPU deterministic graduated evaluation.
"""

from __future__ import annotations

import os
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, Callable

from .hardware_profiler import HardwareProfiler
from .sandbox import VerificationSandbox, SandboxResult
from .graduated_rewards import GraduatedRewardEvaluator

logger = logging.getLogger("rest_rl.critic_evaluator")


@dataclass
class CriticResult:
    score: float
    reasoning: str
    aspect_scores: Dict[str, float] = field(default_factory=dict)
    device_used: str = "cpu"  # "cpu", "cuda", "cpu_fallback"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CriticEvaluator:
    """
    Evaluates candidate patches using LLM critic models or CPU graduated verification,
    strictly obeying the 40% VRAM cap.
    """

    DEFAULT_VRAM_THRESHOLD_MB: float = 20_000.0  # 20 GB free VRAM threshold
    DEFAULT_CRITIC_MODEL: str = "Skywork/Skywork-Critic-Llama-3.1-8B"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model_name: Optional[str] = None,
        vram_threshold_mb: float = DEFAULT_VRAM_THRESHOLD_MB,
        timeout_sec: float = 10.0,
        graduated_evaluator: Optional[GraduatedRewardEvaluator] = None,
    ):
        self.endpoint = endpoint or os.environ.get("LOCAL_OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
        self.model_name = model_name or self.DEFAULT_CRITIC_MODEL
        self.vram_threshold_mb = vram_threshold_mb
        self.timeout_sec = timeout_sec
        self.graduated_evaluator = graduated_evaluator or GraduatedRewardEvaluator()

    def check_vram_and_device(self, vram_override_mb: Optional[float] = None) -> tuple[float, str]:
        """
        Queries free VRAM and decides whether to allow GPU critic execution or enforce CPU.
        Returns (free_vram_mb, selected_device).
        """
        free_vram_mb = vram_override_mb if vram_override_mb is not None else HardwareProfiler.get_available_vram_mb()

        # Strict VRAM cap: must have >= 20,000 MB free VRAM to safely load secondary critic
        if free_vram_mb >= self.vram_threshold_mb:
            return free_vram_mb, "cuda"
        return free_vram_mb, "cpu"

    def evaluate_candidate(
        self,
        candidate_code: str,
        test_source: str,
        task_description: str = "",
        target_filename: str = "solution.py",
        test_filename: str = "test_solution.py",
        orig_diag_count: int = 0,
        new_diag_count: int = 0,
        passed_regressions: int = 0,
        total_regressions: int = 0,
        workspace_root: Optional[str] = None,
        is_paused: Optional[Callable[[], bool]] = None,
        sandbox: Optional[VerificationSandbox] = None,
        vram_override_mb: Optional[float] = None,
    ) -> CriticResult:
        """
        Scores candidate code. Enforces CPU deterministic graduated verification if free VRAM
        is below threshold (< 20,000 MB); queries Skywork Critic on GPU only when sufficient VRAM exists.
        """
        free_vram, device = self.check_vram_and_device(vram_override_mb=vram_override_mb)

        active_sandbox = sandbox or VerificationSandbox()

        # Execute candidate in sandbox to get ground truth verification results
        sandbox_res: SandboxResult = active_sandbox.execute_candidate(
            candidate_code=candidate_code,
            test_source=test_source,
            target_filename=target_filename,
            test_filename=test_filename,
            workspace_root=workspace_root,
            is_paused=is_paused,
        )

        # 1. Strict CPU execution if VRAM is below threshold
        if device == "cpu":
            return self._evaluate_graduated_cpu(
                candidate_code=candidate_code,
                sandbox_res=sandbox_res,
                orig_diag_count=orig_diag_count,
                new_diag_count=new_diag_count,
                passed_regressions=passed_regressions,
                total_regressions=total_regressions,
                free_vram=free_vram,
                device_label="cpu",
            )

        # 2. GPU execution attempt with Skywork-Critic-Llama-3.1-8B
        try:
            critic_res = self._query_skywork_critic(
                candidate_code=candidate_code,
                test_output=sandbox_res.stdout or sandbox_res.stderr,
                task_description=task_description,
                sandbox_res=sandbox_res,
            )
            return critic_res
        except Exception as e:
            logger.info("Skywork Critic GPU evaluation fallback to CPU: %s", e)
            return self._evaluate_graduated_cpu(
                candidate_code=candidate_code,
                sandbox_res=sandbox_res,
                orig_diag_count=orig_diag_count,
                new_diag_count=new_diag_count,
                passed_regressions=passed_regressions,
                total_regressions=total_regressions,
                free_vram=free_vram,
                device_label="cpu_fallback",
                fallback_reason=str(e),
            )

    def _evaluate_graduated_cpu(
        self,
        candidate_code: str,
        sandbox_res: SandboxResult,
        orig_diag_count: int,
        new_diag_count: int,
        passed_regressions: int,
        total_regressions: int,
        free_vram: float,
        device_label: str,
        fallback_reason: Optional[str] = None,
    ) -> CriticResult:
        """Evaluates candidate using deterministic 4-tier continuous dense verification."""
        breakdown = self.graduated_evaluator.evaluate(
            candidate_code=candidate_code,
            target_sandbox_result=sandbox_res,
            orig_diag_count=orig_diag_count,
            new_diag_count=new_diag_count,
            passed_regressions=passed_regressions,
            total_regressions=total_regressions,
        )

        aspect_scores = {
            "ast_validity": breakdown.s_ast,
            "diagnostic_reduction": breakdown.s_diag,
            "regression_safety": breakdown.s_reg,
            "unit_test_pass": breakdown.s_test,
        }

        if fallback_reason:
            reasoning = (
                f"GPU Critic fallback ({fallback_reason}). "
                f"Evaluated via CPU 4-tier graduated verification (AST: {breakdown.s_ast:.2f}, "
                f"Diag: {breakdown.s_diag:.2f}, Reg: {breakdown.s_reg:.2f}, Test: {breakdown.s_test:.2f}). "
                f"Status: {sandbox_res.status}."
            )
        else:
            reasoning = (
                f"Strict VRAM cap enforced ({free_vram:.0f} MB free < {self.vram_threshold_mb:.0f} MB). "
                f"Evaluated via CPU 4-tier graduated verification (AST: {breakdown.s_ast:.2f}, "
                f"Diag: {breakdown.s_diag:.2f}, Reg: {breakdown.s_reg:.2f}, Test: {breakdown.s_test:.2f}). "
                f"Status: {sandbox_res.status}."
            )

        return CriticResult(
            score=breakdown.total_reward,
            reasoning=reasoning,
            aspect_scores=aspect_scores,
            device_used=device_label,
        )

    def _query_skywork_critic(
        self,
        candidate_code: str,
        test_output: str,
        task_description: str,
        sandbox_res: SandboxResult,
    ) -> CriticResult:
        """Queries local Skywork Critic endpoint and parses scoring."""
        url = f"{self.endpoint.rstrip('/')}/api/generate"

        prompt = (
            f"You are Skywork-Critic, an expert code review evaluator.\n"
            f"Task: {task_description or 'Solve the specified programming problem.'}\n\n"
            f"Candidate Code:\n```\n{candidate_code}\n```\n\n"
            f"Test Execution Output:\n{test_output}\n\n"
            f"Evaluate the candidate code. Return JSON with fields:\n"
            f"- score: float from 0.0 to 1.0\n"
            f"- reasoning: explanation of code quality, correctness, and edge cases\n"
            f"- correctness: float 0.0 to 1.0\n"
            f"- efficiency: float 0.0 to 1.0\n"
            f"- safety: float 0.0 to 1.0\n"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 128,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw_response = data.get("response", "{}")
        parsed = json.loads(raw_response)

        raw_score = float(parsed.get("score", sandbox_res.reward))
        # Hard ground-truth gate: if sandbox tests failed 100%, cap critic score at 0.40
        if sandbox_res.status == "FAILED":
            raw_score = min(raw_score, 0.40)
        elif sandbox_res.status == "PASSED":
            raw_score = max(raw_score, 0.90)

        aspect_scores = {
            "correctness": float(parsed.get("correctness", sandbox_res.reward)),
            "efficiency": float(parsed.get("efficiency", 0.8)),
            "safety": float(parsed.get("safety", 1.0 if sandbox_res.status != "SECURITY_BLOCKED" else 0.0)),
        }

        return CriticResult(
            score=round(raw_score, 4),
            reasoning=parsed.get("reasoning", "Evaluated by Skywork Critic GPU model."),
            aspect_scores=aspect_scores,
            device_used="cuda",
        )

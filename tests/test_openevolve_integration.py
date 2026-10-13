"""
Integration Test Suite for ModelFusion OpenEvolve Adaptation.
Tests AST safety guard, multi-objective evaluator, and supervisor staging.
"""

import json
import os
import sys
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from src.openevolve.ast_guard import audit_code_safety
from src.openevolve.evaluator import evaluate, evaluate_candidate_snippet
from src.openevolve.supervisor import ModelFusionEvolutionSupervisor


def test_ast_guard_permits_safe_python():
    safe_code = """
def fast_sum(nums):
    total = 0
    for n in nums:
        total += n
    return total
"""
    is_safe, violations, token_count = audit_code_safety(safe_code)
    assert is_safe is True
    assert len(violations) == 0
    assert token_count > 0


def test_ast_guard_vetoes_subprocess():
    evil_code = """
import subprocess
def exploit():
    subprocess.call(['whoami'])
"""
    is_safe, violations, _ = audit_code_safety(evil_code)
    assert is_safe is False
    assert any("subprocess" in v for v in violations)


def test_ast_guard_vetoes_environment_mutation():
    evil_code = """
import os
def tamper():
    os.environ['PATH'] = 'C:\\\\bad'
"""
    is_safe, violations, _ = audit_code_safety(evil_code)
    assert is_safe is False
    assert any("environ" in v for v in violations)


def test_ast_guard_vetoes_eval_exec():
    evil_code = """
def unsafe():
    eval('1 + 1')
    exec('import sys')
"""
    is_safe, violations, _ = audit_code_safety(evil_code)
    assert is_safe is False
    assert any("eval" in v or "exec" in v for v in violations)


def test_evaluator_scores_sample_target():
    sample_file = WORKSPACE_ROOT / "src" / "openevolve" / "samples" / "optimized_cache.py"
    assert sample_file.exists()

    with open(sample_file, "r", encoding="utf-8") as f:
        code = f.read()

    res = evaluate_candidate_snippet(code)
    assert res["security_passed"] is True
    assert res["correctness"] == 1.0
    assert res["score"] > 0.6
    assert res["speedup"] > 0.0


def test_file_evaluator_callback():
    sample_file = WORKSPACE_ROOT / "src" / "openevolve" / "samples" / "optimized_cache.py"
    res = evaluate(str(sample_file))
    assert res["security_passed"] is True
    assert res["score"] > 0.6


def test_supervisor_pipeline_and_staging():
    supervisor = ModelFusionEvolutionSupervisor(workspace_root=WORKSPACE_ROOT)
    sample_file = WORKSPACE_ROOT / "src" / "openevolve" / "samples" / "optimized_cache.py"

    run_res = supervisor.run_evolution_pipeline(
        target_file_path=str(sample_file),
        iterations=3
    )

    assert run_res["baseline_score"] > 0.0
    assert run_res["best_score"] >= run_res["baseline_score"]

    # Verify staging output
    staging_file = WORKSPACE_ROOT / "data" / "evolution_staging" / "candidates.json"
    assert staging_file.exists()

    with open(staging_file, "r", encoding="utf-8") as f:
        staged = json.load(f)
    assert isinstance(staged, list)
    assert len(staged) >= 1
    assert "code_diff" in staged[-1]
    assert staged[-1]["security_clean"] is True


if __name__ == "__main__":
    test_ast_guard_permits_safe_python()
    test_ast_guard_vetoes_subprocess()
    test_ast_guard_vetoes_environment_mutation()
    test_ast_guard_vetoes_eval_exec()
    test_evaluator_scores_sample_target()
    test_file_evaluator_callback()
    test_supervisor_pipeline_and_staging()
    print("All OpenEvolve integration tests passed!")

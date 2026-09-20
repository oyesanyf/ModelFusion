#!/usr/bin/env python3
"""
Unit tests for CriticEvaluator in HugOS ReST-RL / GRPO subsystem.
Tests:
1. Strict 40% VRAM cap enforcement (< 20,000 MB free VRAM forces CPU execution).
2. GPU device selection when free VRAM >= 20,000 MB.
3. Ground-truth deterministic graduated scoring on CPU for passing solutions.
4. Ground-truth zero score for syntax errors and AST security violations.
5. Graceful fallback from unreachable GPU endpoint to CPU graduated verification.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.critic_evaluator import CriticEvaluator, CriticResult
from rest_rl.sandbox import VerificationSandbox


class TestCriticEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = CriticEvaluator(
            endpoint="http://127.0.0.1:59999",  # non-existent endpoint for deterministic fallback
            vram_threshold_mb=20_000.0,
            timeout_sec=1.0,
        )

    def test_vram_threshold_enforcement(self):
        # 1. Under threshold: 8,000 MB free VRAM -> CPU
        vram, device = self.evaluator.check_vram_and_device(vram_override_mb=8_000.0)
        self.assertEqual(device, "cpu")
        self.assertEqual(vram, 8_000.0)

        # 2. Exactly at threshold: 20,000 MB -> cuda
        vram, device = self.evaluator.check_vram_and_device(vram_override_mb=20_000.0)
        self.assertEqual(device, "cuda")

        # 3. High VRAM: 32,000 MB -> cuda
        vram, device = self.evaluator.check_vram_and_device(vram_override_mb=32_000.0)
        self.assertEqual(device, "cuda")

    def test_cpu_graduated_evaluation_passing(self):
        code = "def solve(x):\n    return x * 2\n"
        test = "import unittest\nfrom solution import solve\nclass Test(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(solve(2), 4)\nif __name__ == '__main__':\n    unittest.main()\n"

        result = self.evaluator.evaluate_candidate(
            candidate_code=code,
            test_source=test,
            vram_override_mb=12_000.0,  # Below 20,000 MB threshold
        )

        self.assertEqual(result.device_used, "cpu")
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.aspect_scores["ast_validity"], 1.0)
        self.assertEqual(result.aspect_scores["unit_test_pass"], 1.0)
        self.assertIn("Strict VRAM cap enforced", result.reasoning)

    def test_cpu_graduated_evaluation_syntax_error(self):
        code = "def invalid_syntax(\n"
        test = "import unittest\n"

        result = self.evaluator.evaluate_candidate(
            candidate_code=code,
            test_source=test,
            vram_override_mb=10_000.0,
        )

        self.assertEqual(result.device_used, "cpu")
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.aspect_scores["ast_validity"], 0.0)

    def test_gpu_endpoint_fallback_to_cpu(self):
        code = "def solve(x):\n    return x + 1\n"
        test = "import unittest\nfrom solution import solve\nclass Test(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(solve(1), 2)\nif __name__ == '__main__':\n    unittest.main()\n"

        # Above threshold (24,000 MB), but endpoint 59999 is offline -> must fallback to CPU
        result = self.evaluator.evaluate_candidate(
            candidate_code=code,
            test_source=test,
            vram_override_mb=24_000.0,
        )

        self.assertEqual(result.device_used, "cpu_fallback")
        self.assertEqual(result.score, 1.0)
        self.assertIn("GPU Critic fallback", result.reasoning)

    def test_gpu_mocked_success(self):
        code = "def solve(x):\n    return x + 1\n"
        test = "import unittest\nfrom solution import solve\nclass Test(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(solve(1), 2)\nif __name__ == '__main__':\n    unittest.main()\n"

        # Mock the internal _query_skywork_critic method
        mock_critic_res = CriticResult(
            score=0.95,
            reasoning="Code is clear and optimal.",
            aspect_scores={"correctness": 1.0, "efficiency": 0.9, "safety": 1.0},
            device_used="cuda",
        )

        with patch.object(self.evaluator, "_query_skywork_critic", return_value=mock_critic_res):
            result = self.evaluator.evaluate_candidate(
                candidate_code=code,
                test_source=test,
                vram_override_mb=24_000.0,
            )
            self.assertEqual(result.device_used, "cuda")
            self.assertEqual(result.score, 0.95)
            self.assertEqual(result.reasoning, "Code is clear and optimal.")


if __name__ == "__main__":
    unittest.main()

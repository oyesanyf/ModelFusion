#!/usr/bin/env python3
"""
Unit tests for Multi-Tier RL Adapters (ReST-RL, TRL, Minimal-GRPO).
Includes tests for preemption, state checkpoints, and multi-task state isolation.
"""

import sys
import unittest
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.hardware_profiler import HardwareTier
from rest_rl.adapters.base import RLTask
from rest_rl.adapters.factory import create_adapter
from rest_rl.adapters.tier1_restrl import ReSTRLAdapter
from rest_rl.adapters.tier2_trl import TRLGRPOAdapter
from rest_rl.adapters.tier3_minimal import MinimalGRPOAdapter
from rest_rl.sandbox import VerificationSandbox


class TestAdapters(unittest.TestCase):

    def setUp(self):
        self.sandbox = VerificationSandbox(default_timeout=5.0)
        self.sample_task = RLTask(
            task_id="test_task_01",
            target_file="solution.py",
            test_target="""
import unittest
from solution import get_val

class TestVal(unittest.TestCase):
    def test_val(self):
        self.assertIsNotNone(get_val())
""",
            workspace_root="",
            instruction="Fix get_val to return a non-None value",
            original_code="""
def get_val():
    pass
""",
        )

        self.sample_task_2 = RLTask(
            task_id="test_task_02",
            target_file="math_solution.py",
            test_target="""
import unittest
from math_solution import multiply

class TestMath(unittest.TestCase):
    def test_mult(self):
        self.assertEqual(multiply(3, 4), 12)
""",
            workspace_root="",
            instruction="Implement multiply(a, b)",
            original_code="""
def multiply(a: int, b: int) -> int:
    pass
""",
        )

    def test_factory_instantiation(self):
        a1 = create_adapter(HardwareTier.TIER_1, sandbox=self.sandbox)
        self.assertIsInstance(a1, ReSTRLAdapter)
        self.assertEqual(a1.tier, HardwareTier.TIER_1)

        a2 = create_adapter(HardwareTier.TIER_2, sandbox=self.sandbox)
        self.assertIsInstance(a2, TRLGRPOAdapter)
        self.assertEqual(a2.tier, HardwareTier.TIER_2)

        a3 = create_adapter(HardwareTier.TIER_3, sandbox=self.sandbox)
        self.assertIsInstance(a3, MinimalGRPOAdapter)
        self.assertEqual(a3.tier, HardwareTier.TIER_3)

    def test_tier1_restrl_rollout_and_preemption(self):
        adapter = ReSTRLAdapter(sandbox=self.sandbox, config={"mcts_iterations": 4})

        # 1. Test preemption flag
        paused_calls = 0
        def pause_after_one():
            nonlocal paused_calls
            paused_calls += 1
            return paused_calls > 1

        res_paused = adapter.run_rollout(self.sample_task, is_paused=pause_after_one)
        self.assertEqual(res_paused.status, "PAUSED")
        self.assertFalse(res_paused.is_complete)

        # 2. Test checkpoint and restore
        ckpt = adapter.checkpoint()
        self.assertIn("current_iteration", ckpt)

        # Resume with pause cleared
        adapter.restore(ckpt)
        res_resumed = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertIn(res_resumed.status, ["COMPLETED", "IN_PROGRESS"])
        self.assertTrue(res_resumed.best_reward >= 0.0)

    def test_tier2_trl_grpo_rollout_and_preemption(self):
        adapter = TRLGRPOAdapter(sandbox=self.sandbox, config={"num_generations": 3})

        # Test preemption
        res_paused = adapter.run_rollout(self.sample_task, is_paused=lambda: True)
        self.assertEqual(res_paused.status, "PAUSED")

        # Test unpaused rollout on the SAME adapter
        res = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertEqual(res.status, "COMPLETED")
        self.assertTrue(res.is_complete)
        self.assertIn("mean_reward", res.metadata)

    def test_tier3_minimal_grpo_rollout(self):
        adapter = MinimalGRPOAdapter(sandbox=self.sandbox, config={"num_samples": 2})

        # Test preemption
        res_paused = adapter.run_rollout(self.sample_task, is_paused=lambda: True)
        self.assertEqual(res_paused.status, "PAUSED")

        # Test unpaused execution on the SAME adapter
        res = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertEqual(res.status, "COMPLETED")
        self.assertTrue(res.best_reward >= 0.0)

    def test_consecutive_tasks_isolation_tier2(self):
        """Verify Task 2 does NOT inherit Task 1's step count or candidate on the same adapter instance."""
        adapter = TRLGRPOAdapter(sandbox=self.sandbox, config={"num_generations": 4})

        # Run Task 1
        res1 = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertEqual(res1.status, "COMPLETED")
        self.assertEqual(res1.task_id, "test_task_01")

        # Run Task 2 on the SAME adapter
        res2 = adapter.run_rollout(self.sample_task_2, is_paused=lambda: False)
        self.assertEqual(res2.status, "COMPLETED")
        self.assertEqual(res2.task_id, "test_task_02")
        self.assertIn("multiply", res2.best_candidate)
        self.assertNotEqual(res2.best_candidate, res1.best_candidate)
        self.assertGreater(res2.iterations_completed, 0)

    def test_consecutive_tasks_isolation_tier3(self):
        """Verify MinimalGRPO does not bleed state across consecutive tasks."""
        adapter = MinimalGRPOAdapter(sandbox=self.sandbox, config={"num_samples": 3})

        res1 = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertEqual(res1.status, "COMPLETED")

        res2 = adapter.run_rollout(self.sample_task_2, is_paused=lambda: False)
        self.assertEqual(res2.status, "COMPLETED")
        self.assertEqual(res2.task_id, "test_task_02")
        self.assertIn("multiply", res2.best_candidate)
        self.assertGreater(res2.iterations_completed, 0)

    def test_interleaved_task_preemption_and_resumption(self):
        """Verify Task A can pause, Task B run, and Task A resume with its progress intact."""
        adapter = TRLGRPOAdapter(sandbox=self.sandbox, config={"num_generations": 4})

        # Pause Task A after 1 generation
        paused_count = 0
        def pause_task_a():
            nonlocal paused_count
            paused_count += 1
            return paused_count > 1

        res_a_p = adapter.run_rollout(self.sample_task, is_paused=pause_task_a)
        self.assertEqual(res_a_p.status, "PAUSED")
        self.assertFalse(res_a_p.is_complete)
        saved_step = res_a_p.iterations_completed

        # Run Task B completely
        res_b = adapter.run_rollout(self.sample_task_2, is_paused=lambda: False)
        self.assertEqual(res_b.status, "COMPLETED")

        # Resume Task A
        res_a_resumed = adapter.run_rollout(self.sample_task, is_paused=lambda: False)
        self.assertEqual(res_a_resumed.status, "COMPLETED")
        self.assertEqual(res_a_resumed.task_id, "test_task_01")
        self.assertGreaterEqual(res_a_resumed.iterations_completed, saved_step)


if __name__ == "__main__":
    unittest.main()

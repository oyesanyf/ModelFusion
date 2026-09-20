#!/usr/bin/env python3
"""
Unit tests for Hardware Profiler & Memory Sizing Rules.
"""

import sys
import unittest
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.hardware_profiler import HardwareProfiler, HardwareTier, MemoryProfile


class TestHardwareProfiler(unittest.TestCase):

    def setUp(self):
        self.profiler = HardwareProfiler()

    def test_runtime_metrics_retrieval(self):
        avail_ram, total_ram, pct = self.profiler.get_runtime_ram()
        self.assertGreater(avail_ram, 0.0)
        self.assertGreater(total_ram, 0.0)
        self.assertLessEqual(avail_ram, total_ram)
        self.assertTrue(0.0 <= pct <= 100.0)

        free_vram, total_vram, gpu_name = self.profiler.get_runtime_vram()
        self.assertGreaterEqual(free_vram, 0.0)
        self.assertGreaterEqual(total_vram, 0.0)
        self.assertIsInstance(gpu_name, str)

    def test_tier1_classification(self):
        # 32 GB available RAM, 0 VRAM -> Tier 1
        p1 = self.profiler.classify(available_ram_gb=32.0, free_vram_mb=0.0)
        self.assertEqual(p1.tier, HardwareTier.TIER_1)
        self.assertEqual(p1.recommended_model, "Qwen/Qwen2.5-Coder-7B-Instruct")
        self.assertIn("MCTS", p1.recommended_framework)
        self.assertIsNotNone(p1.reward_model)

        # 8 GB RAM, 16 GB free VRAM (16384 MB) -> Tier 1
        p2 = self.profiler.classify(available_ram_gb=8.0, free_vram_mb=16384.0)
        self.assertEqual(p2.tier, HardwareTier.TIER_1)

    def test_tier2_classification(self):
        # 16 GB available RAM, 0 VRAM -> Tier 2
        p1 = self.profiler.classify(available_ram_gb=16.0, free_vram_mb=0.0)
        self.assertEqual(p1.tier, HardwareTier.TIER_2)
        self.assertIn("GRPO", p1.recommended_framework)
        self.assertEqual(p1.recommended_model, "Qwen/Qwen2.5-Coder-1.5B-Instruct")

        # 6 GB RAM, 6 GB free VRAM (6144 MB) -> Tier 2
        p2 = self.profiler.classify(available_ram_gb=6.0, free_vram_mb=6144.0)
        self.assertEqual(p2.tier, HardwareTier.TIER_2)

    def test_tier3_classification_and_critical_available_ram_rule(self):
        # Low available RAM (<12GB) and low VRAM (<4.5GB) -> Tier 3
        p = self.profiler.classify(available_ram_gb=6.0, free_vram_mb=1024.0)
        self.assertEqual(p.tier, HardwareTier.TIER_3)
        self.assertIn("TinyZero", p.recommended_framework)

        # CRITICAL RULE: High total physical RAM installed (e.g. 64GB) but runtime available
        # RAM is only 4GB due to heavy concurrent workloads -> MUST classify as Tier 3!
        p_constrained = self.profiler.classify(available_ram_gb=4.0, free_vram_mb=500.0)
        self.assertEqual(p_constrained.tier, HardwareTier.TIER_3)

    def test_os_throttling_and_gpu_caps(self):
        # Should execute safely without uncaught exception
        throttled = HardwareProfiler.apply_os_throttling()
        # On Windows or Linux, returns True or gracefully handles permissions
        self.assertIsInstance(throttled, bool)

        caps = HardwareProfiler.apply_gpu_memory_caps(cuda_fraction=0.4, vllm_utilization=0.3)
        self.assertIsInstance(caps, bool)


if __name__ == "__main__":
    unittest.main()

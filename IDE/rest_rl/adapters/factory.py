#!/usr/bin/env python3
"""
Adapter Factory for HugOS ReST-RL / GRPO subsystem.
Instantiates appropriate tier adapter based on runtime hardware classification.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from ..hardware_profiler import HardwareProfiler, HardwareTier
from ..sandbox import VerificationSandbox
from .base import BaseRLAdapter
from .tier1_restrl import ReSTRLAdapter
from .tier2_trl import TRLGRPOAdapter
from .tier3_minimal import MinimalGRPOAdapter

logger = logging.getLogger("rest_rl.adapters.factory")


def create_adapter(
    tier: Optional[HardwareTier] = None,
    config: Optional[Dict[str, Any]] = None,
    sandbox: Optional[VerificationSandbox] = None,
) -> BaseRLAdapter:
    """
    Creates and returns the appropriate RL reasoning adapter.
    If tier is not explicitly provided, it profiles runtime available RAM and VRAM.
    """
    config = config or {}
    sandbox = sandbox or VerificationSandbox()

    if tier is None:
        profiler = HardwareProfiler(
            tier1_min_ram_gb=config.get("resources", {}).get("tier1_min_available_ram_gb", 24.0),
            tier1_min_vram_gb=config.get("resources", {}).get("tier1_min_free_vram_gb", 14.0),
            tier2_min_ram_gb=config.get("resources", {}).get("tier2_min_available_ram_gb", 12.0),
            tier2_min_vram_gb=config.get("resources", {}).get("tier2_min_free_vram_gb", 4.5),
        )
        profile = profiler.classify()
        tier = profile.tier
        logger.info(
            "Hardware automatically classified as %s (Avail RAM: %.1f GB, Free VRAM: %.1f MB)",
            tier.name,
            profile.available_ram_gb,
            profile.free_vram_mb,
        )

    model_configs = config.get("models", {})

    if tier == HardwareTier.TIER_1:
        tier_cfg = model_configs.get("tier1", {})
        return ReSTRLAdapter(
            model_name=tier_cfg.get("name", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            reward_model=tier_cfg.get("reward_model", "Skywork/Skywork-Reward-Llama-3.1-8B-v0.2"),
            sandbox=sandbox,
            config=tier_cfg,
        )
    elif tier == HardwareTier.TIER_2:
        tier_cfg = model_configs.get("tier2", {})
        return TRLGRPOAdapter(
            model_name=tier_cfg.get("name", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
            sandbox=sandbox,
            config=tier_cfg,
        )
    else:
        tier_cfg = model_configs.get("tier3", {})
        return MinimalGRPOAdapter(
            model_name=tier_cfg.get("name", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
            sandbox=sandbox,
            config=tier_cfg,
        )

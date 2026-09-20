#!/usr/bin/env python3
"""
Hardware Profiler for HugOS ReST-RL / GRPO Background Subsystem.

Evaluates runtime available RAM and free VRAM to classify system capabilities into:
- Tier 1: High resources (Available RAM >= 24GB or Free VRAM >= 14GB) -> ReST-RL (MCTS + Skywork RM)
- Tier 2: Medium resources (Available RAM >= 12GB or Free VRAM >= 4.5GB) -> TRL / Unsloth GRPO
- Tier 3: Low resources (Available RAM < 12GB and Free VRAM < 4.5GB) -> TinyZero / Minimal-GRPO / Ollama

CRITICAL LAW: Never size or allocate models based on total installed physical RAM.
Always evaluate runtime available/free memory to prevent OOM aborts.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import logging
from dataclasses import dataclass, asdict
from enum import IntEnum
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("rest_rl.hardware_profiler")


class HardwareTier(IntEnum):
    TIER_1 = 1  # High VRAM/RAM: ReST-RL MCTS + Value/Reward Model
    TIER_2 = 2  # Medium VRAM/RAM: TRL / Unsloth Single-GPU GRPO
    TIER_3 = 3  # Low VRAM/RAM: TinyZero / Minimal-GRPO / Ollama Rejection Sampling


@dataclass
class MemoryProfile:
    available_ram_gb: float
    total_ram_gb: float
    ram_utilization_pct: float
    free_vram_mb: float
    total_vram_mb: float
    gpu_name: str
    tier: HardwareTier
    recommended_model: str
    recommended_framework: str
    reward_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = int(self.tier)
        d["tier_name"] = self.tier.name
        return d


class HardwareProfiler:
    """Evaluates host memory and GPU metrics, manages process priority, and configures resource bounds."""

    def __init__(
        self,
        tier1_min_ram_gb: float = 24.0,
        tier1_min_vram_gb: float = 14.0,
        tier2_min_ram_gb: float = 12.0,
        tier2_min_vram_gb: float = 4.5,
    ):
        self.tier1_min_ram_gb = tier1_min_ram_gb
        self.tier1_min_vram_gb = tier1_min_vram_gb
        self.tier2_min_ram_gb = tier2_min_ram_gb
        self.tier2_min_vram_gb = tier2_min_vram_gb

    @staticmethod
    def get_runtime_ram() -> Tuple[float, float, float]:
        """
        Returns (available_ram_gb, total_ram_gb, utilization_pct).
        Always queries current free/available memory.
        """
        try:
            import psutil
            vm = psutil.virtual_memory()
            available_gb = vm.available / (1024 ** 3)
            total_gb = vm.total / (1024 ** 3)
            pct = vm.percent
            return round(available_gb, 2), round(total_gb, 2), round(pct, 1)
        except ImportError:
            # Fallback if psutil is somehow missing
            return 8.0, 16.0, 50.0

    @staticmethod
    def get_runtime_vram() -> Tuple[float, float, str]:
        """
        Returns (free_vram_mb, total_vram_mb, gpu_name).
        Checks PyTorch CUDA first, then nvidia-smi CLI.
        """
        # 1. Try fast nvidia-smi CLI first (avoids multi-second torch import overhead)
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                out = subprocess.check_output(
                    [
                        nvidia_smi,
                        "--query-gpu=memory.free,memory.total,name",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=3,
                ).strip()
                lines = out.splitlines()
                if lines:
                    parts = [p.strip() for p in lines[0].split(",")]
                    if len(parts) >= 3:
                        free_mb = float(parts[0])
                        total_mb = float(parts[1])
                        gpu_name = parts[2]
                        return round(free_mb, 1), round(total_mb, 1), gpu_name
            except Exception as e:
                logger.debug("nvidia-smi probe failed: %s", e)

        # 2. Try PyTorch CUDA if nvidia-smi is not available
        try:
            import torch
            if torch.cuda.is_available():
                device_idx = torch.cuda.current_device()
                gpu_name = torch.cuda.get_device_name(device_idx)
                free_bytes, total_bytes = torch.cuda.mem_get_info(device_idx)
                free_mb = free_bytes / (1024 ** 2)
                total_mb = total_bytes / (1024 ** 2)
                return round(free_mb, 1), round(total_mb, 1), gpu_name
        except Exception as e:
            logger.debug("PyTorch CUDA check skipped/failed: %s", e)

        return 0.0, 0.0, "None / CPU Only"

    def classify(
        self,
        available_ram_gb: Optional[float] = None,
        free_vram_mb: Optional[float] = None,
    ) -> MemoryProfile:
        """
        Classifies runtime hardware profile into Tier 1, Tier 2, or Tier 3.
        """
        if available_ram_gb is None or free_vram_mb is None:
            cur_avail_ram, cur_total_ram, cur_pct = self.get_runtime_ram()
            cur_free_vram, cur_total_vram, gpu_name = self.get_runtime_vram()
            avail_ram = cur_avail_ram if available_ram_gb is None else available_ram_gb
            free_vram = cur_free_vram if free_vram_mb is None else free_vram_mb
        else:
            cur_avail_ram, cur_total_ram, cur_pct = self.get_runtime_ram()
            cur_free_vram, cur_total_vram, gpu_name = self.get_runtime_vram()
            avail_ram = available_ram_gb
            free_vram = free_vram_mb

        free_vram_gb = free_vram / 1024.0

        # Tier 1 Rule: Available RAM >= 24GB OR Free VRAM >= 14GB
        if avail_ram >= self.tier1_min_ram_gb or free_vram_gb >= self.tier1_min_vram_gb:
            return MemoryProfile(
                available_ram_gb=avail_ram,
                total_ram_gb=cur_total_ram,
                ram_utilization_pct=cur_pct,
                free_vram_mb=free_vram,
                total_vram_mb=cur_total_vram,
                gpu_name=gpu_name,
                tier=HardwareTier.TIER_1,
                recommended_model="Qwen/Qwen2.5-Coder-7B-Instruct",
                recommended_framework="ReST-RL (VM-MCTS)",
                reward_model="Skywork/Skywork-Reward-Llama-3.1-8B-v0.2",
            )

        # Tier 2 Rule: Available RAM >= 12GB OR Free VRAM >= 4.5GB
        if avail_ram >= self.tier2_min_ram_gb or free_vram_gb >= self.tier2_min_vram_gb:
            return MemoryProfile(
                available_ram_gb=avail_ram,
                total_ram_gb=cur_total_ram,
                ram_utilization_pct=cur_pct,
                free_vram_mb=free_vram,
                total_vram_mb=cur_total_vram,
                gpu_name=gpu_name,
                tier=HardwareTier.TIER_2,
                recommended_model="Qwen/Qwen2.5-Coder-1.5B-Instruct",
                recommended_framework="TRL / Unsloth (GRPO)",
                reward_model=None,
            )

        # Tier 3 Rule: Available RAM < 12GB AND Free VRAM < 4.5GB
        return MemoryProfile(
            available_ram_gb=avail_ram,
            total_ram_gb=cur_total_ram,
            ram_utilization_pct=cur_pct,
            free_vram_mb=free_vram,
            total_vram_mb=cur_total_vram,
            gpu_name=gpu_name,
            tier=HardwareTier.TIER_3,
            recommended_model="Qwen/Qwen2.5-Coder-1.5B-Instruct",
            recommended_framework="TinyZero / Minimal-GRPO / Ollama",
            reward_model=None,
        )

    @staticmethod
    def apply_os_throttling() -> bool:
        """
        Enforces low OS scheduling priority so the background daemon does not
        degrade editor responsiveness or UI thread rendering.
        - On Windows: psutil.IDLE_PRIORITY_CLASS
        - On Unix/macOS: os.nice(15)
        """
        success = False
        try:
            import psutil
            p = psutil.Process()
            if sys.platform == "win32":
                p.nice(psutil.IDLE_PRIORITY_CLASS)
                logger.info("Windows process priority set to IDLE_PRIORITY_CLASS.")
                success = True
            else:
                try:
                    os.nice(15)
                    logger.info("Unix process priority set to nice 15.")
                    success = True
                except Exception as e:
                    logger.warning("os.nice(15) failed: %s", e)
        except Exception as e:
            logger.warning("Failed to set process scheduling priority: %s", e)
        return success

    @staticmethod
    def apply_gpu_memory_caps(
        cuda_fraction: float = 0.5,
        vllm_utilization: float = 0.4,
    ) -> bool:
        """
        Configures GPU memory caps to prevent starving the host compositor or main IDE window.
        """
        os.environ["VLLM_GPU_MEMORY_UTILIZATION"] = str(vllm_utilization)
        applied = False
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.set_per_process_memory_fraction(cuda_fraction, device=0)
                logger.info("PyTorch per-process CUDA memory fraction set to %.2f.", cuda_fraction)
                applied = True
        except Exception as e:
            logger.debug("PyTorch memory fraction configuration: %s", e)
        return applied

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
    def probe_dxgi_vram() -> Optional[Tuple[float, float, str]]:
        """
        Multi-vendor DirectX DXGI video memory probe via ctypes (dxgi.dll).
        Supports NVIDIA, AMD Radeon, and Intel Arc in <15ms without external dependencies.
        Returns (free_vram_mb, total_vram_mb, gpu_name) or None if unavailable.
        """
        if sys.platform != "win32":
            return None

        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8),
                ]

            IID_IDXGIFactory1 = GUID(
                0x770AAE78,
                0xF26F,
                0x4DBA,
                (wintypes.BYTE * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87),
            )

            class LUID(ctypes.Structure):
                _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

            class DXGI_ADAPTER_DESC1(ctypes.Structure):
                _fields_ = [
                    ("Description", wintypes.WCHAR * 128),
                    ("VendorId", wintypes.UINT),
                    ("DeviceId", wintypes.UINT),
                    ("SubSysId", wintypes.UINT),
                    ("Revision", wintypes.UINT),
                    ("DedicatedVideoMemory", ctypes.c_size_t),
                    ("DedicatedSystemMemory", ctypes.c_size_t),
                    ("SharedSystemMemory", ctypes.c_size_t),
                    ("AdapterLuid", LUID),
                    ("Flags", wintypes.UINT),
                ]

            dxgi = ctypes.windll.dxgi
            pFactory = ctypes.c_void_p()
            hr = dxgi.CreateDXGIFactory1(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(pFactory))
            if hr != 0 or not pFactory:
                return None

            vtable = ctypes.cast(pFactory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            EnumAdapters1_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p)
            )
            EnumAdapters1 = EnumAdapters1_proto(vtable[12])
            Release_proto = ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p)
            GetDesc1_proto = ctypes.WINFUNCTYPE(
                ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(DXGI_ADAPTER_DESC1)
            )

            best_vram = 0.0
            best_gpu_name = ""
            best_vendor = 0

            idx = 0
            pAdapter = ctypes.c_void_p()
            while EnumAdapters1(pFactory, idx, ctypes.byref(pAdapter)) == 0:
                adapter_vtable = ctypes.cast(
                    pAdapter, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
                ).contents
                GetDesc1 = GetDesc1_proto(adapter_vtable[10])
                Release_adapter = Release_proto(adapter_vtable[2])

                desc = DXGI_ADAPTER_DESC1()
                if GetDesc1(pAdapter, ctypes.byref(desc)) == 0:
                    # Filter out software adapters (DXGI_ADAPTER_FLAG_SOFTWARE = 2)
                    if not (desc.Flags & 2):
                        vram_mb = desc.DedicatedVideoMemory / (1024 ** 2)
                        if vram_mb > best_vram:
                            best_vram = vram_mb
                            best_gpu_name = desc.Description
                            best_vendor = desc.VendorId

                Release_adapter(pAdapter)
                idx += 1

            Release_proto(vtable[2])(pFactory)

            if best_vram > 0.0 and best_gpu_name:
                vendor_map = {0x10DE: "NVIDIA", 0x1002: "AMD", 0x8086: "Intel", 0x5143: "Qualcomm"}
                vendor_prefix = vendor_map.get(best_vendor, "")
                if vendor_prefix and vendor_prefix not in best_gpu_name:
                    full_gpu_name = f"{vendor_prefix} {best_gpu_name}"
                else:
                    full_gpu_name = best_gpu_name

                # Check if nvidia-smi can give exact live free VRAM for NVIDIA GPUs
                free_mb = round(best_vram * 0.85, 1)
                if best_vendor == 0x10DE:
                    nvidia_smi = shutil.which("nvidia-smi")
                    if nvidia_smi:
                        try:
                            out = subprocess.check_output(
                                [nvidia_smi, "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                text=True,
                                timeout=1,
                            ).strip()
                            if out:
                                free_mb = float(out.splitlines()[0].strip())
                        except Exception:
                            pass

                return round(free_mb, 1), round(best_vram, 1), full_gpu_name

        except Exception as e:
            logger.debug("DXGI VRAM probe exception: %s", e)

        return None

    @staticmethod
    def get_runtime_vram() -> Tuple[float, float, str]:
        """
        Returns (free_vram_mb, total_vram_mb, gpu_name).
        Checks DXGI first (<15ms, multi-vendor: NVIDIA/AMD/Intel Arc), then nvidia-smi, then PyTorch CUDA.
        """
        # 1. Try ultra-fast multi-vendor DXGI probe (<15ms)
        dxgi_res = HardwareProfiler.probe_dxgi_vram()
        if dxgi_res:
            return dxgi_res

        # 2. Try fast nvidia-smi CLI (fallback if non-Windows or DXGI failed)
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

        # 3. Try PyTorch CUDA if nvidia-smi is not available
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

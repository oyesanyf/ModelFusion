"""
Adapters for Multi-Tier Reinforcement Learning & Self-Improving Reasoning.
Supports:
- Tier 1: ReST-RL (VM-MCTS tree search with value model)
- Tier 2: TRL / Unsloth (Single-GPU GRPO batch trainer)
- Tier 3: TinyZero / Minimal-GRPO / Ollama rejection sampling
"""

from .base import BaseRLAdapter, RLTask, RolloutResult
from .tier1_restrl import ReSTRLAdapter
from .tier2_trl import TRLGRPOAdapter
from .tier3_minimal import MinimalGRPOAdapter
from .factory import create_adapter

__all__ = [
    "BaseRLAdapter",
    "RLTask",
    "RolloutResult",
    "ReSTRLAdapter",
    "TRLGRPOAdapter",
    "MinimalGRPOAdapter",
    "create_adapter",
]

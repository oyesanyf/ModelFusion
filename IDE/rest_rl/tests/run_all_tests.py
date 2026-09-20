#!/usr/bin/env python3
"""
Unified Test Runner for HugOS ReST-RL / GRPO Subsystem.
Runs:
1. test_hardware_profiler.py
2. test_sandbox.py
3. test_adapters.py
4. test_ipc_and_state.py
"""

import sys
import unittest
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    test_dir = Path(__file__).resolve().parent
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(test_dir), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    print("=" * 80)
    print(" HUGOS ReST-RL / GRPO RECURSIVE REINFORCEMENT LEARNING TEST SUITE")
    print("=" * 80)

    result = runner.run(suite)
    print("=" * 80)
    if result.wasSuccessful():
        print(f"✅ ALL {result.testsRun} TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"❌ TEST SUITE FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        sys.exit(1)

if __name__ == "__main__":
    main()

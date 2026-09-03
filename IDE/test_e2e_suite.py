#!/usr/bin/env python3
"""
IDE E2E Test Suite Runner Proxy
==============================
Invokes the master 4-tier E2E test suite in tests/e2e/run_all_e2e.py.
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
E2E_RUNNER = os.path.join(PROJECT_ROOT, "tests", "e2e", "run_all_e2e.py")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.e2e.run_all_e2e import run_e2e_suite

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run HugOS IDE & ModelFusion E2E suite.")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run a specific test tier only")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true", help="Minimize console output")
    args = parser.parse_args()

    exit_code = run_e2e_suite(tier_filter=args.tier, json_output=args.json, verbose=not args.quiet)
    sys.exit(exit_code)

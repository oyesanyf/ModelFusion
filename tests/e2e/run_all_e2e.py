#!/usr/bin/env python3
"""
ModelFusion & HugOS IDE E2E Master Test Runner
==============================================
Runs the complete 4-tier requirement-driven E2E test suite:
- Tier 1: Feature Coverage (95 test cases across 19 features)
- Tier 2: Boundary & Corner Cases (95 test cases across 19 features)
- Tier 3: Cross-Feature Interactions (20 pairwise interaction tests)
- Tier 4: Real-World Workload Scenarios (8 end-to-end scenarios)

Total: 218 Tests (100% Deterministic, Opaque-Box, Zero-Flake)
"""

import sys
import os
import time
import unittest
import argparse
import json

# Ensure project root and script directory are in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from tests.e2e.test_tier1_features import TestTier1FeatureCoverage
    from tests.e2e.test_tier2_boundaries import TestTier2BoundaryConditions
    from tests.e2e.test_tier3_interactions import TestTier3PairwiseInteractions
    from tests.e2e.test_tier4_scenarios import TestTier4RealWorldScenarios
except ImportError:
    from test_tier1_features import TestTier1FeatureCoverage
    from test_tier2_boundaries import TestTier2BoundaryConditions
    from test_tier3_interactions import TestTier3PairwiseInteractions
    from test_tier4_scenarios import TestTier4RealWorldScenarios



def run_e2e_suite(tier_filter=None, json_output=False, verbose=True):
    start_time = time.perf_counter()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    tier_suites = {
        1: (TestTier1FeatureCoverage, "Tier 1: Feature Coverage (Happy Path, 19 Features)"),
        2: (TestTier2BoundaryConditions, "Tier 2: Boundary & Corner Cases (19 Features)"),
        3: (TestTier3PairwiseInteractions, "Tier 3: Pairwise Cross-Feature Interactions"),
        4: (TestTier4RealWorldScenarios, "Tier 4: Real-World Application Workloads")
    }
    
    active_tiers = [tier_filter] if tier_filter in tier_suites else [1, 2, 3, 4]
    
    if not json_output:
        print("=" * 80)
        print(" 🚀 MODELFUSION & HUGOS IDE COMPREHENSIVE 4-TIER E2E TEST SUITE")
        print("=" * 80)
        print(f" Master Suite Location: {SCRIPT_DIR}")
        print(f" Active Tiers: {', '.join(f'Tier {t}' for t in active_tiers)}")
        print("-" * 80)

    tier_results = {}
    total_ran = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0

    for tier_num in active_tiers:
        test_class, desc = tier_suites[tier_num]
        tier_suite = loader.loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2 if verbose and not json_output else 0)
        
        if not json_output and verbose:
            print(f"\n▶ Running {desc} ({tier_suite.countTestCases()} tests)...")
            
        t_start = time.perf_counter()
        result = runner.run(tier_suite)
        t_elapsed = time.perf_counter() - t_start
        
        ran = result.testsRun
        failed = len(result.failures)
        errors = len(result.errors)
        passed = ran - failed - errors
        
        tier_results[f"tier_{tier_num}"] = {
            "description": desc,
            "tests_run": ran,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "duration_sec": round(t_elapsed, 4)
        }
        
        total_ran += ran
        total_passed += passed
        total_failed += failed
        total_errors += errors
        
        if not json_output:
            status_icon = "✔" if (failed == 0 and errors == 0) else "✖"
            print(f"  {status_icon} Tier {tier_num} Finished: {passed}/{ran} passed in {t_elapsed:.3f}s")

    total_duration = time.perf_counter() - start_time

    summary = {
        "status": "PASS" if (total_failed == 0 and total_errors == 0) else "FAIL",
        "total_tests": total_ran,
        "passed": total_passed,
        "failed": total_failed,
        "errors": total_errors,
        "pass_rate": round(total_passed / max(1, total_ran) * 100, 2),
        "total_duration_sec": round(total_duration, 4),
        "tier_breakdown": tier_results
    }

    if json_output:
        print(json.dumps(summary, indent=2))
    else:
        print("\n" + "=" * 80)
        if total_failed == 0 and total_errors == 0:
            print(f"  🎉 ALL TESTS PASSED! ({total_passed}/{total_ran} tests in {total_duration:.3f}s - 100% GREEN)")
        else:
            print(f"  ❌ TEST SUITE FAILED: {total_failed} failures, {total_errors} errors out of {total_ran} tests.")
        print(f"  Breakdown: Tier 1 ({tier_results.get('tier_1', {}).get('passed', 0)}), "
              f"Tier 2 ({tier_results.get('tier_2', {}).get('passed', 0)}), "
              f"Tier 3 ({tier_results.get('tier_3', {}).get('passed', 0)}), "
              f"Tier 4 ({tier_results.get('tier_4', {}).get('passed', 0)})")
        print("=" * 80 + "\n")

    return 0 if (total_failed == 0 and total_errors == 0) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ModelFusion & HugOS IDE E2E test suite.")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run a specific test tier only")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true", help="Minimize console output")
    args = parser.parse_args()

    exit_code = run_e2e_suite(tier_filter=args.tier, json_output=args.json, verbose=not args.quiet)
    sys.exit(exit_code)

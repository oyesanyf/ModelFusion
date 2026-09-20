#!/usr/bin/env python3
"""
Unit and integration tests for advanced ReST-RL features:
- Graduated continuous dense rewards (GraduatedRewardEvaluator)
- Adversarial mutation verification (ASTMutator & AdversarialCertificationGate)
- Compute budgeter & cyclomatic complexity (ComputeBudgeter)
- LSP diagnostic harvesting & oracle repair loop (LSPDiagnosticHarvester, CompilerOracleRepairLoop)
- Speculative synthesis & caching (SpeculativeSynthesizer, SpeculativeCache)
- Multi-file dependency migration (DependencyMigrationManager)
- Daemon RPC dispatch for all new endpoints
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.sandbox import VerificationSandbox
from rest_rl.graduated_rewards import GraduatedRewardEvaluator, GraduatedRewardBreakdown
from rest_rl.mutation_verifier import ASTMutator, AdversarialCertificationGate, CertificationResult
from rest_rl.compute_budgeter import ComputeBudgeter, TaskComplexityScore
from rest_rl.lsp_diagnostic_repair import LSPDiagnosticHarvester, CompilerOracleRepairLoop, LSPDiagnostic
from rest_rl.speculative_synthesis import SpeculativeSynthesizer, SpeculativeCache, SpeculativeItem
from rest_rl.dependency_migration import DependencyMigrationManager, DependencyBump
from rest_rl.rest_rl_daemon import RestRLDaemon


class TestGraduatedRewards(unittest.TestCase):
    def setUp(self):
        self.sandbox = VerificationSandbox()
        self.evaluator = GraduatedRewardEvaluator(sandbox=self.sandbox)

    def test_ast_signal_valid(self):
        code = "def add(a, b):\n    return a + b\n"
        signal, err = self.evaluator.compute_ast_signal(code)
        self.assertEqual(signal, 1.0)
        self.assertIsNone(err)

    def test_ast_signal_syntax_error(self):
        code = "def bad_syntax(:\n    return 42\n"
        signal, err = self.evaluator.compute_ast_signal(code)
        self.assertEqual(signal, 0.0)
        self.assertIsNotNone(err)

    def test_ast_signal_security_violation(self):
        code = "import os\nos.system('rm -rf /')\n"
        signal, err = self.evaluator.compute_ast_signal(code)
        self.assertEqual(signal, 0.0)
        self.assertIn("Forbidden", str(err))

    def test_diagnostic_signal_reduction(self):
        # 4 errors initially, reduced to 1 -> 75% reduction
        sig = self.evaluator.compute_diagnostic_signal(orig_diag_count=4, new_diag_count=1)
        self.assertAlmostEqual(sig, 0.75)

        # Baseline zero errors, new error introduced -> penalize
        sig_penalty = self.evaluator.compute_diagnostic_signal(orig_diag_count=0, new_diag_count=2)
        self.assertAlmostEqual(sig_penalty, 0.5)

    def test_regression_signal(self):
        sig = self.evaluator.compute_regression_signal(passed_regressions=8, total_regressions=10)
        self.assertAlmostEqual(sig, 0.8)

        sig_empty = self.evaluator.compute_regression_signal(passed_regressions=0, total_regressions=0)
        self.assertEqual(sig_empty, 1.0)

    def test_full_graduated_reward_breakdown(self):
        code = "def multiply(x, y):\n    return x * y\n"
        test_code = """import unittest
from math_mod import multiply

class TestMath(unittest.TestCase):
    def test_multiply(self):
        self.assertEqual(multiply(3, 4), 12)
"""
        sb_res = self.sandbox.execute_candidate(
            candidate_code=code,
            test_source=test_code,
            target_filename="math_mod.py",
        )
        breakdown = self.evaluator.evaluate(
            candidate_code=code,
            target_sandbox_result=sb_res,
            orig_diag_count=2,
            new_diag_count=0,
            passed_regressions=5,
            total_regressions=5,
        )
        self.assertTrue(breakdown.is_perfect)
        self.assertAlmostEqual(breakdown.total_reward, 1.0, places=2)
        self.assertEqual(breakdown.s_ast, 1.0)
        self.assertEqual(breakdown.s_diag, 1.0)
        self.assertEqual(breakdown.s_reg, 1.0)
        self.assertEqual(breakdown.s_test, 1.0)


class TestMutationVerifier(unittest.TestCase):
    def setUp(self):
        self.mutator = ASTMutator()
        self.sandbox = VerificationSandbox()
        self.gate = AdversarialCertificationGate(sandbox=self.sandbox, mutator=self.mutator)

    def test_ast_mutator_generates_mutants(self):
        code = "def calculate(a, b):\n    if a == b and a > 0:\n        return a + b\n    return 0\n"
        mutants = self.mutator.generate_mutants(code, max_mutants=10)
        self.assertGreater(len(mutants), 0)
        operators = {op for op, desc, mut_code in mutants}
        # Should contain at least ROR, AOR, LOR, or RVR
        self.assertTrue(any(op in operators for op in ("ROR", "AOR", "LOR", "RVR", "SDL")))

    def test_adversarial_certification_passed(self):
        # Implementation and comprehensive test suite that catches mutations
        code = "def is_positive(x):\n    if x > 0:\n        return True\n    return False\n"
        test_code = """import unittest
from solution import is_positive

class TestPositive(unittest.TestCase):
    def test_positive(self):
        self.assertTrue(is_positive(5))
        self.assertFalse(is_positive(-3))
        self.assertFalse(is_positive(0))
"""
        result = self.gate.certify(code, test_code)
        self.assertIsInstance(result, CertificationResult)
        self.assertTrue(result.is_certified)
        self.assertGreaterEqual(result.kill_ratio, 0.5)
        self.assertEqual(result.certified_reward, 1.0)

    def test_vacuous_test_suite_rejected(self):
        code = "def compute(x):\n    return x * 2\n"
        # Test code that does not assert anything on return value
        test_code = """import unittest
from solution import compute

class TestCompute(unittest.TestCase):
    def test_call(self):
        compute(10)
"""
        result = self.gate.certify(code, test_code)
        self.assertFalse(result.is_certified)
        self.assertEqual(result.kill_ratio, 0.0)
        self.assertEqual(result.certified_reward, 0.0)


class TestComputeBudgeter(unittest.TestCase):
    def test_complexity_simple_vs_complex(self):
        simple_code = "def simple(a):\n    return a + 1\n"
        complex_code = """
def complex_fn(data):
    total = 0
    for item in data:
        if item > 10 and item % 2 == 0:
            total += item
        elif item < 0:
            while item < 0:
                item += 1
                total += 1
    return total
"""
        score_simple = ComputeBudgeter.compute_complexity(simple_code)
        score_complex = ComputeBudgeter.compute_complexity(complex_code)

        self.assertLess(score_simple.cyclomatic_complexity, score_complex.cyclomatic_complexity)
        self.assertLess(score_simple.ast_depth, score_complex.ast_depth)
        self.assertIn(score_simple.estimated_difficulty, ("LOW", "MEDIUM"))
        self.assertIn(score_complex.estimated_difficulty, ("HIGH", "CRITICAL"))

    def test_exploration_decay(self):
        budgeter = ComputeBudgeter(base_iterations=16, base_exploration_c=1.414, min_exploration_c=0.35)
        c0 = budgeter.get_exploration_c(current_iteration=0, total_iterations=16)
        c8 = budgeter.get_exploration_c(current_iteration=8, total_iterations=16)
        c16 = budgeter.get_exploration_c(current_iteration=16, total_iterations=16)

        self.assertAlmostEqual(c0, 1.414)
        self.assertLess(c8, c0)
        self.assertLess(c16, c8)
        self.assertGreaterEqual(c16, 0.35)


class TestLSPDiagnosticRepair(unittest.TestCase):
    def test_harvest_from_payload(self):
        payload = {
            "file_path": "src/main.rs",
            "diagnostics": [
                {
                    "severity": 1,
                    "range": {"start": {"line": 12, "character": 4}},
                    "source": "rustc",
                    "code": "E0308",
                    "message": "mismatched types: expected u32, found i32",
                }
            ],
        }
        diags = LSPDiagnosticHarvester.harvest_from_payload(payload)
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].line_number, 12)
        self.assertEqual(diags[0].code, "E0308")
        self.assertEqual(diags[0].severity, "Error")

    def test_build_repair_task(self):
        harvester = LSPDiagnosticHarvester()
        repair_loop = CompilerOracleRepairLoop(harvester=harvester)
        diag = LSPDiagnostic(
            file_path="foo.py",
            line_number=5,
            column=2,
            severity="Error",
            source="py_compile",
            code="SyntaxError",
            message="invalid syntax",
        )
        task = repair_loop.build_repair_task(
            task_id="fix_foo",
            file_path="foo.py",
            code_str="x = (",
            diagnostics=[diag],
        )
        self.assertEqual(task.task_id, "fix_foo")
        self.assertIn("SyntaxError", task.instruction)


class TestSpeculativeSynthesis(unittest.TestCase):
    def test_detect_unwritten_callsites(self):
        synthesizer = SpeculativeSynthesizer()
        code = """
def process(data):
    norm = normalize_data(data)
    res = compute_advanced_matrix(norm, 42)
    return res
"""
        callsites = synthesizer.detect_unwritten_callsites(code, target_file="pipeline.py")
        names = [c.func_name for c in callsites]
        self.assertIn("normalize_data", names)
        self.assertIn("compute_advanced_matrix", names)
        self.assertNotIn("process", names)  # Defined in buffer

    def test_speculative_cache(self):
        cache = SpeculativeCache(max_items=3)
        item1 = SpeculativeItem(func_name="foo", signature="def foo():", candidate_code="return 1", reward=1.0)
        item2 = SpeculativeItem(func_name="bar", signature="def bar():", candidate_code="return 2", reward=0.9)
        cache.put("mod.py", item1)
        cache.put("mod.py", item2)

        retrieved = cache.get("mod.py", "foo")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.candidate_code, "return 1")

        self.assertIsNone(cache.get("mod.py", "nonexistent"))


class TestDependencyMigration(unittest.TestCase):
    def test_detect_npm_bumps(self):
        old_package_json = '{"dependencies": {"react": "^17.0.0", "lodash": "4.17.21"}}'
        new_package_json = '{"dependencies": {"react": "^18.2.0", "lodash": "4.17.21"}}'
        bumps = DependencyMigrationManager.detect_manifest_bumps("package.json", old_package_json, new_package_json)
        self.assertEqual(len(bumps), 1)
        self.assertEqual(bumps[0].package_name, "react")
        self.assertEqual(bumps[0].old_version, "^17.0.0")
        self.assertEqual(bumps[0].new_version, "^18.2.0")

    def test_detect_cargo_bumps(self):
        old_cargo = '[dependencies]\ntokio = "1.20.0"\nserde = "1.0"\n'
        new_cargo = '[dependencies]\ntokio = "1.32.0"\nserde = "1.0"\n'
        bumps = DependencyMigrationManager.detect_manifest_bumps("Cargo.toml", old_cargo, new_cargo)
        self.assertEqual(len(bumps), 1)
        self.assertEqual(bumps[0].package_name, "tokio")
        self.assertEqual(bumps[0].old_version, "1.20.0")
        self.assertEqual(bumps[0].new_version, "1.32.0")


class TestDaemonRPCDispatch(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            self.temp_db = tf.name
        self.daemon = RestRLDaemon()
        self.daemon.db_path = self.temp_db
        self.daemon._init_sqlite()

    def tearDown(self):
        try:
            os.unlink(self.temp_db)
        except Exception:
            pass

    def test_idle_start_and_stop_with_job_termination(self):
        res_start = self.daemon._handle_method("ide/idle_start", {})
        self.assertEqual(res_start["status"], "RESUMED")
        self.assertTrue(self.daemon.is_idle)

        res_stop = self.daemon._handle_method("ide/idle_stop", {})
        self.assertEqual(res_stop["status"], "PAUSED")
        self.assertFalse(self.daemon.is_idle)

    def test_speculative_detect_rpc(self):
        code = "res = undefined_service_call(x, y)\n"
        res = self.daemon._handle_method("speculative/detect", {"code": code, "file_path": "client.py"})
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["callsites"][0]["func_name"], "undefined_service_call")

    def test_budget_complexity_rpc(self):
        code = "def foo(x):\n    if x > 0:\n        return 1\n    return 0\n"
        res = self.daemon._handle_method("budget/complexity", {"code": code})
        self.assertIn("cyclomatic_complexity", res)
        self.assertEqual(res["cyclomatic_complexity"], 2)

    def test_migration_detect_rpc(self):
        old_toml = '[dependencies]\nserde = "1.0.100"\n'
        new_toml = '[dependencies]\nserde = "1.0.150"\n'
        res = self.daemon._handle_method("migration/detect", {
            "manifest_filename": "Cargo.toml",
            "old_content": old_toml,
            "new_content": new_toml,
        })
        self.assertEqual(len(res["bumps"]), 1)
        self.assertEqual(res["bumps"][0]["package_name"], "serde")

    def test_diagnostics_report_rpc(self):
        diag_payload = {
            "task_id": "test_t1",
            "file_path": "src/lib.rs",
            "diagnostics": [
                {
                    "severity": 1,
                    "range": {"start": {"line": 10, "character": 5}},
                    "source": "rustc",
                    "code": "E0425",
                    "message": "cannot find value `z` in this scope",
                }
            ],
        }
        res = self.daemon._handle_method("diagnostics/report", diag_payload)
        self.assertEqual(res["recorded"], 1)


if __name__ == "__main__":
    unittest.main()

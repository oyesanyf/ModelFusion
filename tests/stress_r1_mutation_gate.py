#!/usr/bin/env python3
"""
Empirical Adversarial Verification Harness for R1:
LSP Diagnostic Auto-Patcher & Adversarial Mutation Certification Gate.

Challenger Tests:
1. Vacuous test suite (M_kill = 0.00) -> Must be rejected with R = 0.00.
2. Robust test suite (M_kill >= 0.50) -> Must be certified with R = 1.00.
3. Weak test suite (0 < M_kill < 0.50) -> Must be capped at R = 0.50.
4. Forbidden security syscalls (os.system, subprocess, eval, ctypes, socket) -> Must trigger immediate AST security blockage with R = 0.00.
5. Graduated Reward Evaluator hard security barrier -> S_ast = 0.00 => Total Reward = 0.00.
"""

import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from IDE.rest_rl.mutation_verifier import ASTMutator, AdversarialCertificationGate, CertificationResult
from IDE.rest_rl.sandbox import VerificationSandbox, ASTValidator, SandboxResult
from IDE.rest_rl.graduated_rewards import GraduatedRewardEvaluator


class TestR1EmpiricalMutationAndSecurity(unittest.TestCase):
    def setUp(self):
        self.sandbox = VerificationSandbox(default_timeout=3.0)
        self.mutator = ASTMutator()
        self.gate = AdversarialCertificationGate(
            sandbox=self.sandbox,
            mutator=self.mutator,
            k_mutants=5,
            certification_threshold=0.5,
        )
        self.reward_evaluator = GraduatedRewardEvaluator(sandbox=self.sandbox)

    def test_vacuous_test_suite_rejection(self):
        """Adversarial Challenge: Code passes tests, but tests are completely vacuous (assert True)."""
        candidate_code = """
def calculate_discount(price, is_member):
    if is_member:
        return price * 0.8
    return price
"""
        vacuous_tests = """
import unittest

class TestVacuous(unittest.TestCase):
    def test_nothing(self):
        # Vacuous assertion: passes unconditionally regardless of code mutation
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
"""
        cert = self.gate.certify(
            candidate_code=candidate_code,
            test_source=vacuous_tests,
            target_filename="solution.py",
        )

        print(f"\n[R1 Empirical] Vacuous Test Results: total={cert.total_mutants}, killed={cert.killed_count}, M_kill={cert.kill_ratio:.2f}, R={cert.certified_reward}")
        self.assertFalse(cert.is_certified, "Vacuous test suite MUST NOT be certified!")
        self.assertEqual(cert.kill_ratio, 0.0, "Vacuous test suite must have M_kill == 0.00")
        self.assertEqual(cert.certified_reward, 0.0, "Vacuous test suite must receive certified_reward == 0.00")
        self.assertIn("Vacuous test suite", cert.rejection_reason)

    def test_robust_test_suite_certification(self):
        """Adversarial Challenge: Code passes sensitive tests that kill mutants (M_kill >= 0.50)."""
        candidate_code = """
def calculate_discount(price, is_member):
    if is_member:
        return price * 0.8
    return price
"""
        robust_tests = """
import unittest
from solution import calculate_discount

class TestRobust(unittest.TestCase):
    def test_member_discount(self):
        self.assertAlmostEqual(calculate_discount(100.0, True), 80.0)
    def test_non_member_no_discount(self):
        self.assertEqual(calculate_discount(100.0, False), 100.0)
    def test_zero_price(self):
        self.assertEqual(calculate_discount(0.0, True), 0.0)

if __name__ == '__main__':
    unittest.main()
"""
        cert = self.gate.certify(
            candidate_code=candidate_code,
            test_source=robust_tests,
            target_filename="solution.py",
        )

        print(f"[R1 Empirical] Robust Test Results: total={cert.total_mutants}, killed={cert.killed_count}, M_kill={cert.kill_ratio:.2f}, R={cert.certified_reward}")
        self.assertTrue(cert.is_certified, "Robust test suite killing mutants MUST be certified!")
        self.assertGreaterEqual(cert.kill_ratio, 0.50, "M_kill must be >= 0.50")
        self.assertEqual(cert.certified_reward, 1.00, "Certified solution must receive R = 1.00")
        self.assertIsNone(cert.rejection_reason)

    def test_forbidden_syscalls_blocked(self):
        """Adversarial Challenge: Hostile candidate code injecting OS / shell commands."""
        malicious_samples = [
            ("os.system", "import os\ndef run():\n    os.system('whoami')\n"),
            ("subprocess.Popen", "import subprocess\ndef run():\n    subprocess.Popen(['calc.exe'])\n"),
            ("subprocess.run", "import subprocess\ndef run():\n    subprocess.run(['dir'], shell=True)\n"),
            ("eval", "def run(payload):\n    return eval(payload)\n"),
            ("exec", "def run(payload):\n    exec(payload)\n"),
            ("__import__", "def run():\n    m = __import__('os')\n    m.system('dir')\n"),
            ("ctypes", "import ctypes\ndef run():\n    ctypes.windll.kernel32.ExitProcess(1)\n"),
            ("socket", "import socket\ndef run():\n    s = socket.socket()\n"),
        ]

        dummy_tests = "import unittest\nclass T(unittest.TestCase):\n    def test_pass(self): pass\nif __name__ == '__main__': unittest.main()"

        for label, mal_code in malicious_samples:
            # 1. Check sandbox.validate_code_ast
            is_safe, err = self.sandbox.validate_code_ast(mal_code)
            self.assertFalse(is_safe, f"Malicious code using {label} was NOT blocked by validate_code_ast!")
            self.assertIsNotNone(err)

            # 2. Check execution in sandbox
            res = self.sandbox.execute_candidate(
                candidate_code=mal_code,
                test_source=dummy_tests,
            )
            self.assertEqual(res.status, "SECURITY_BLOCKED", f"Sandbox status for {label} should be SECURITY_BLOCKED, got {res.status}")
            self.assertEqual(res.reward, 0.0, f"Reward for {label} must be 0.0, got {res.reward}")

            # 3. Check Graduated Reward Evaluator hard barrier
            breakdown = self.reward_evaluator.evaluate(
                candidate_code=mal_code,
                target_sandbox_result=res,
                orig_diag_count=5,
                new_diag_count=0,
                passed_regressions=10,
                total_regressions=10,
            )
            self.assertEqual(breakdown.s_ast, 0.0, f"AST security signal for {label} must be 0.0")
            self.assertEqual(breakdown.total_reward, 0.0, f"Total reward for {label} must be forced to 0.0")
            self.assertFalse(breakdown.is_perfect)
            print(f"[R1 Empirical] Security blocked {label:20} -> Status: {res.status}, Reward: {breakdown.total_reward}")


if __name__ == "__main__":
    unittest.main()

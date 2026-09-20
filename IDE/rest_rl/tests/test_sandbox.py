#!/usr/bin/env python3
"""
Unit tests for Verification Sandbox & Discrete Reward Computation.
Includes security bypass attack probes, relative workspace paths, and subdirectory handling.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add root of rest_rl to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rest_rl.sandbox import VerificationSandbox, SandboxResult


class TestVerificationSandbox(unittest.TestCase):

    def setUp(self):
        self.sandbox = VerificationSandbox(default_timeout=5.0)

    def test_syntax_error_rejection(self):
        malformed_code = "def broken_func(\n    print('missing paren')"
        test_code = "import unittest\nclass T(unittest.TestCase):\n  def test_one(self): pass"

        res = self.sandbox.execute_candidate(malformed_code, test_code)
        self.assertEqual(res.status, "SYNTAX_ERROR")
        self.assertEqual(res.reward, 0.0)
        self.assertIn("SyntaxError", res.stderr)

    def test_ast_security_blocking(self):
        unsafe_code = """
import os
def dangerous_operation():
    os.system("echo hacked")
    return True
"""
        test_code = "import unittest\nclass T(unittest.TestCase):\n  def test_one(self): pass"

        res = self.sandbox.execute_candidate(unsafe_code, test_code)
        self.assertEqual(res.status, "SECURITY_BLOCKED")
        self.assertEqual(res.reward, 0.0)
        self.assertIn("Forbidden system call", res.stderr)

    def test_ast_security_bypasses_blocked(self):
        test_code = "import unittest\nclass T(unittest.TestCase):\n  def test_one(self): pass"

        # 1. from os import system
        code1 = "from os import system\ndef run():\n  system('echo 123')\n"
        res1 = self.sandbox.execute_candidate(code1, test_code)
        self.assertEqual(res1.status, "SECURITY_BLOCKED", "Failed to block 'from os import system'")

        # 2. from subprocess import Popen
        code2 = "from subprocess import Popen\ndef run():\n  Popen('calc')\n"
        res2 = self.sandbox.execute_candidate(code2, test_code)
        self.assertEqual(res2.status, "SECURITY_BLOCKED", "Failed to block 'from subprocess import Popen'")

        # 3. eval call
        code3 = "def run():\n  return eval('1 + 1')\n"
        res3 = self.sandbox.execute_candidate(code3, test_code)
        self.assertEqual(res3.status, "SECURITY_BLOCKED", "Failed to block 'eval'")

        # 4. exec call
        code4 = "def run():\n  exec('import sys')\n"
        res4 = self.sandbox.execute_candidate(code4, test_code)
        self.assertEqual(res4.status, "SECURITY_BLOCKED", "Failed to block 'exec'")

        # 5. __import__ call
        code5 = "def run():\n  __import__('os').system('echo 123')\n"
        res5 = self.sandbox.execute_candidate(code5, test_code)
        self.assertEqual(res5.status, "SECURITY_BLOCKED", "Failed to block '__import__'")

        # 6. import ctypes
        code6 = "import ctypes\ndef run():\n  return 0\n"
        res6 = self.sandbox.execute_candidate(code6, test_code)
        self.assertEqual(res6.status, "SECURITY_BLOCKED", "Failed to block 'import ctypes'")

    def test_passing_unit_test_full_reward(self):
        candidate_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        test_code = """
import unittest
from solution import add

class TestAdd(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_negative(self):
        self.assertEqual(add(-1, -1), -2)
"""
        res = self.sandbox.execute_candidate(candidate_code, test_code)
        self.assertEqual(res.status, "PASSED")
        self.assertEqual(res.reward, 1.0)
        self.assertEqual(res.passed_count, 2)
        self.assertEqual(res.total_count, 2)

    def test_failing_unit_test_zero_reward(self):
        candidate_code = """
def add(a: int, b: int) -> int:
    return a - b  # Buggy implementation
"""
        test_code = """
import unittest
from solution import add

class TestAdd(unittest.TestCase):
    def test_one(self):
        self.assertEqual(add(2, 3), 5)
"""
        res = self.sandbox.execute_candidate(candidate_code, test_code)
        self.assertEqual(res.status, "FAILED")
        self.assertEqual(res.reward, 0.0)
        self.assertEqual(res.passed_count, 0)
        self.assertEqual(res.total_count, 1)

    def test_partial_pass_fractional_reward(self):
        candidate_code = """
def is_even(n: int) -> bool:
    return n == 2  # Passes for 2, fails for 4
"""
        test_code = """
import unittest
from solution import is_even

class TestEven(unittest.TestCase):
    def test_two(self):
        self.assertTrue(is_even(2))

    def test_four(self):
        self.assertTrue(is_even(4))
"""
        res = self.sandbox.execute_candidate(candidate_code, test_code)
        self.assertEqual(res.status, "PARTIAL")
        self.assertAlmostEqual(res.reward, 0.5, places=2)
        self.assertEqual(res.passed_count, 1)
        self.assertEqual(res.total_count, 2)

    def test_timeout_enforcement(self):
        infinite_loop_code = """
def compute():
    while True:
        pass
"""
        test_code = """
import unittest
from solution import compute

class TestLoop(unittest.TestCase):
    def test_loop(self):
        compute()
"""
        # Strict 1.5s timeout for fast test execution
        res = self.sandbox.execute_candidate(infinite_loop_code, test_code, timeout=1.5)
        self.assertEqual(res.status, "TIMEOUT")
        self.assertEqual(res.reward, 0.0)
        self.assertIn("timed out", res.stderr.lower())

    def test_subdirectories_and_relative_workspace(self):
        with tempfile.TemporaryDirectory() as ws_root:
            test_dir = os.path.join(ws_root, "tests")
            os.makedirs(test_dir, exist_ok=True)
            test_file_path = os.path.join(test_dir, "test_math.py")
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write("""
import unittest
from src.math_helpers import multiply

class TestMath(unittest.TestCase):
    def test_mult(self):
        self.assertEqual(multiply(3, 5), 15)
""")
            candidate = "def multiply(a: int, b: int) -> int:\n    return a * b\n"

            # Execute with subfolder target_filename and workspace-relative test_source
            res = self.sandbox.execute_candidate(
                candidate_code=candidate,
                test_source="tests/test_math.py",
                target_filename="src/math_helpers.py",
                test_filename="tests/test_math.py",
                workspace_root=ws_root,
            )
            self.assertEqual(res.status, "PASSED")
            self.assertEqual(res.reward, 1.0)


if __name__ == "__main__":
    unittest.main()

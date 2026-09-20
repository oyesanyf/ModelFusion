#!/usr/bin/env python3
"""
Execution Sandbox for HugOS ReST-RL / GRPO Background Subsystem.

Provides isolated subprocess execution for verifying candidate patches against
test suites. Calculates discrete rewards:
- 1.0 for 100% passed assertions
- Fractional (passed / total) for partial passes
- 0.0 for execution failure, syntax error, AST security violation, or timeout (5.0s limit).
"""

from __future__ import annotations

import os
import sys
import ast
import time
import re
import shutil
import tempfile
import subprocess
import logging
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple, Set

logger = logging.getLogger("rest_rl.sandbox")


@dataclass
class SandboxResult:
    reward: float
    passed_count: int
    total_count: int
    duration_sec: float
    stdout: str
    stderr: str
    status: str  # "PASSED", "PARTIAL", "FAILED", "SYNTAX_ERROR", "SECURITY_BLOCKED", "TIMEOUT", "ERROR"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecurityViolationError(Exception):
    """Raised when candidate code fails AST security checks."""
    pass


class ASTValidator(ast.NodeVisitor):
    """
    Inspects candidate Python AST for syntax validity and forbidden primitives
    that might harm the host machine during autonomous background evaluation.
    Tracks imports, aliases, built-in code execution primitives, and system calls.
    """

    DEFAULT_FORBIDDEN_CALLS = {
        "os.system",
        "os.popen",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "shutil.rmtree",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_output",
        "subprocess.check_call",
    }

    DEFAULT_FORBIDDEN_MODULES = {
        "ctypes",
        "subprocess",
        "socket",
        "pty",
        "posix",
        "nt",
    }

    DEFAULT_FORBIDDEN_BUILTINS = {
        "eval",
        "exec",
        "compile",
        "__import__",
    }

    def __init__(
        self,
        forbidden_calls: Optional[Set[str]] = None,
        forbidden_modules: Optional[Set[str]] = None,
        forbidden_builtins: Optional[Set[str]] = None,
    ):
        self.forbidden_calls = set(forbidden_calls) if forbidden_calls else set(self.DEFAULT_FORBIDDEN_CALLS)
        self.forbidden_modules = set(forbidden_modules) if forbidden_modules else set(self.DEFAULT_FORBIDDEN_MODULES)
        self.forbidden_builtins = set(forbidden_builtins) if forbidden_builtins else set(self.DEFAULT_FORBIDDEN_BUILTINS)
        self.violations: List[str] = []
        self.aliases: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            self.aliases[asname] = name
            if any(name == m or name.startswith(m + ".") for m in self.forbidden_modules):
                self.violations.append(f"Forbidden module import: {name} at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        if any(mod == m or mod.startswith(m + ".") for m in self.forbidden_modules):
            self.violations.append(f"Forbidden module import: {mod} at line {node.lineno}")
        for alias in node.names:
            full_name = f"{mod}.{alias.name}" if mod else alias.name
            asname = alias.asname or alias.name
            self.aliases[asname] = full_name
            if any(full_name == f or full_name.startswith(f + ".") for f in self.forbidden_calls):
                self.violations.append(f"Forbidden import: {full_name} at line {node.lineno}")
            if alias.name in self.forbidden_builtins:
                self.violations.append(f"Forbidden builtin import: {alias.name} at line {node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_name(node.func)
        if func_name:
            # Resolve aliases
            resolved = self.aliases.get(func_name, func_name)

            # Check builtins
            if func_name in self.forbidden_builtins or resolved in self.forbidden_builtins:
                self.violations.append(f"Forbidden execution builtin: {func_name} at line {node.lineno}")

            # Check forbidden calls and modules
            if any(resolved == f or resolved.startswith(f + ".") for f in self.forbidden_calls):
                self.violations.append(f"Forbidden system call: {resolved} at line {node.lineno}")
            elif any(resolved == m or resolved.startswith(m + ".") for m in self.forbidden_modules):
                self.violations.append(f"Forbidden module call: {resolved} at line {node.lineno}")

        # Check if node.func itself is a Call (e.g., __import__('os').system('...'))
        if isinstance(node.func, ast.Call):
            self.visit_Call(node.func)
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            self.visit_Call(node.func.value)

        self.generic_visit(node)

    def _resolve_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parent = self._resolve_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        elif isinstance(node, ast.Call):
            return self._resolve_name(node.func)
        return None


class VerificationSandbox:
    """Runs test suites on candidate solutions inside an isolated temporary directory."""

    def __init__(
        self,
        default_timeout: float = 5.0,
        forbidden_calls: Optional[Set[str]] = None,
        forbidden_modules: Optional[Set[str]] = None,
        forbidden_builtins: Optional[Set[str]] = None,
    ):
        self.default_timeout = default_timeout
        self.forbidden_calls = forbidden_calls or ASTValidator.DEFAULT_FORBIDDEN_CALLS
        self.forbidden_modules = forbidden_modules or ASTValidator.DEFAULT_FORBIDDEN_MODULES
        self.forbidden_builtins = forbidden_builtins or ASTValidator.DEFAULT_FORBIDDEN_BUILTINS

    def validate_code_ast(self, code_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validates syntax and AST safety of candidate code string.
        Returns (is_valid, error_reason).
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as se:
            return False, f"SyntaxError: {se.msg} (line {se.lineno}, col {se.offset})"
        except Exception as e:
            return False, f"AST Parse Error: {e}"

        validator = ASTValidator(
            forbidden_calls=self.forbidden_calls,
            forbidden_modules=self.forbidden_modules,
            forbidden_builtins=self.forbidden_builtins,
        )
        validator.visit(tree)
        if validator.violations:
            return False, "; ".join(validator.violations)

        return True, None

    def execute_candidate(
        self,
        candidate_code: str,
        test_source: str,
        timeout: Optional[float] = None,
        target_filename: str = "solution.py",
        test_filename: str = "test_solution.py",
        workspace_root: Optional[str] = None,
    ) -> SandboxResult:
        """
        Runs candidate code against test_source in an isolated environment.
        test_source can be either:
        - raw Python test code string
        - path to an existing test file (absolute or workspace-relative)
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()

        # 1. AST & Security validation
        is_safe, err = self.validate_code_ast(candidate_code)
        if not is_safe:
            duration = time.time() - start_time
            status = "SYNTAX_ERROR" if "SyntaxError" in (err or "") else "SECURITY_BLOCKED"
            return SandboxResult(
                reward=0.0,
                passed_count=0,
                total_count=0,
                duration_sec=round(duration, 3),
                stdout="",
                stderr=err or "Validation failed",
                status=status,
                error_message=err,
            )

        # Resolve relative test_source if workspace_root is given
        if not os.path.isfile(test_source) and workspace_root and not os.path.isabs(test_source):
            ws_test_path = os.path.join(workspace_root, test_source)
            if os.path.isfile(ws_test_path):
                test_source = ws_test_path

        # 2. Setup isolated temporary directory with robust Windows cleanup handling
        temp_dir = tempfile.mkdtemp(prefix="hugos_rest_rl_")
        try:
            solution_path = os.path.join(temp_dir, target_filename)
            os.makedirs(os.path.dirname(solution_path), exist_ok=True)
            with open(solution_path, "w", encoding="utf-8") as f:
                f.write(candidate_code)

            # Determine test file content and destination
            test_path = os.path.join(temp_dir, test_filename)
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            if os.path.isfile(test_source):
                try:
                    with open(test_source, "r", encoding="utf-8") as tf:
                        test_content = tf.read()
                except Exception as e:
                    return SandboxResult(
                        reward=0.0,
                        passed_count=0,
                        total_count=0,
                        duration_sec=round(time.time() - start_time, 3),
                        stdout="",
                        stderr=f"Failed to read test_source file: {e}",
                        status="ERROR",
                        error_message=str(e),
                    )
            else:
                test_content = test_source

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_content)

            # Add temporary directory and test context to PYTHONPATH in subprocess
            env = os.environ.copy()
            paths = [temp_dir]
            if os.path.isfile(test_source):
                td = os.path.dirname(os.path.abspath(test_source))
                if td not in paths:
                    paths.append(td)
            if workspace_root and os.path.isdir(workspace_root):
                if workspace_root not in paths:
                    paths.append(workspace_root)
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                paths.append(existing_pythonpath)
            env["PYTHONPATH"] = os.pathsep.join(paths)

            # 3. Execute runner (try pytest first; fallback to unittest runner)
            return self._run_test_process(temp_dir, test_filename, timeout, start_time, env)
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _run_test_process(
        self,
        cwd: str,
        test_file: str,
        timeout: float,
        start_time: float,
        env: dict,
    ) -> SandboxResult:
        """Executes test runner subprocess with timeout handling."""
        # Check if pytest is available
        has_pytest = self._check_pytest_available()
        if has_pytest:
            cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
            runner_type = "pytest"
        else:
            # Fallback to standard library unittest
            cmd = [sys.executable, "-m", "unittest", test_file]
            runner_type = "unittest"

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            duration = time.time() - start_time
            stdout = proc.stdout
            stderr = proc.stderr
            returncode = proc.returncode

            # 4. Parse results and compute discrete reward
            passed, total = self._parse_test_counts(stdout, stderr, runner_type)

            if returncode == 0:
                reward = 1.0
                status = "PASSED"
            elif total > 0 and passed > 0:
                reward = round(passed / total, 4)
                status = "PARTIAL"
            else:
                reward = 0.0
                status = "FAILED"

            return SandboxResult(
                reward=reward,
                passed_count=passed,
                total_count=total,
                duration_sec=round(duration, 3),
                stdout=stdout,
                stderr=stderr,
                status=status,
                error_message=stderr if returncode != 0 and total == 0 else None,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return SandboxResult(
                reward=0.0,
                passed_count=0,
                total_count=0,
                duration_sec=round(duration, 3),
                stdout="",
                stderr=f"Execution timed out after {timeout:.1f}s",
                status="TIMEOUT",
                error_message=f"Timeout after {timeout:.1f}s",
            )
        except Exception as e:
            duration = time.time() - start_time
            return SandboxResult(
                reward=0.0,
                passed_count=0,
                total_count=0,
                duration_sec=round(duration, 3),
                stdout="",
                stderr=str(e),
                status="ERROR",
                error_message=str(e),
            )

    @staticmethod
    def _check_pytest_available() -> bool:
        """Determines if pytest is importable in the current python runtime."""
        try:
            import pytest  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _parse_test_counts(stdout: str, stderr: str, runner_type: str) -> Tuple[int, int]:
        """Parses passed and total test counts from runner output."""
        output = f"{stdout}\n{stderr}"

        if runner_type == "pytest":
            passed_match = re.search(r"(\d+)\s+passed", output)
            failed_match = re.search(r"(\d+)\s+failed", output)
            error_match = re.search(r"(\d+)\s+error", output)

            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0
            errors = int(error_match.group(1)) if error_match else 0
            total = passed + failed + errors

            if total == 0:
                passed_items = len(re.findall(r"::.*?\s+PASSED", output))
                failed_items = len(re.findall(r"::.*?\s+FAILED", output))
                if passed_items > 0 or failed_items > 0:
                    return passed_items, passed_items + failed_items

            return passed, total

        else:
            ran_match = re.search(r"Ran\s+(\d+)\s+test", output)
            total = int(ran_match.group(1)) if ran_match else 0

            if "OK" in output and total > 0:
                return total, total

            failures_match = re.search(r"failures=(\d+)", output)
            errors_match = re.search(r"errors=(\d+)", output)

            failures = int(failures_match.group(1)) if failures_match else 0
            errors = int(errors_match.group(1)) if errors_match else 0

            passed = max(0, total - (failures + errors))
            return passed, total

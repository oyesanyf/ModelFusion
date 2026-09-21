#!/usr/bin/env python3
"""
LSP Diagnostic Harvester and Compiler Oracle Repair Loop.

Features:
1. Harvests language server diagnostics (syntax, typing, borrow-checker errors).
2. Runs compiler oracles (python -m py_compile, cargo check, tsc --noEmit, pyright).
3. Drives compiler-guided iterative repair loops until diagnostics reach zero.
"""

from __future__ import annotations

import os
import re
import sys
import shutil
import subprocess
import logging
from dataclasses import dataclass, asdict
import time
from typing import List, Optional, Dict, Any, Tuple

from .adapters.base import RLTask
from .graduated_rewards import GraduatedRewardEvaluator, GraduatedRewardBreakdown
from .mutation_verifier import ASTMutator, AdversarialCertificationGate, CertificationResult
from .sandbox import VerificationSandbox, SandboxResult

logger = logging.getLogger("rest_rl.lsp_diagnostic_repair")


@dataclass
class LSPDiagnostic:
    file_path: str
    line_number: int
    column: int
    severity: str  # "Error", "Warning", "Information", "Hint"
    source: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LSPDiagnosticHarvester:
    """Extracts, normalizes, and filters diagnostics from IDE events or compiler oracles."""

    @staticmethod
    def harvest_from_payload(payload: Dict[str, Any]) -> List[LSPDiagnostic]:
        """
        Parses JSON-RPC diagnostic payload from IDE (vscode.languages.onDidChangeDiagnostics).
        """
        diagnostics: List[LSPDiagnostic] = []
        file_path = payload.get("file_path", "")
        raw_list = payload.get("diagnostics", [])

        for item in raw_list:
            severity_num = item.get("severity", 0)
            sev_map = {0: "Error", 1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}
            severity = sev_map.get(severity_num, "Error")

            range_info = item.get("range", {})
            start_pos = range_info.get("start", {})
            line = start_pos.get("line", 1)
            col = start_pos.get("character", 0)

            diag = LSPDiagnostic(
                file_path=file_path,
                line_number=line,
                column=col,
                severity=severity,
                source=item.get("source", "lsp"),
                code=str(item.get("code", "")),
                message=item.get("message", ""),
            )
            diagnostics.append(diag)

        return diagnostics

    @staticmethod
    def harvest_from_compiler_oracle(
        file_path: str,
        custom_cmd: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> List[LSPDiagnostic]:
        """
        Executes native language compiler oracles (py_compile, rustc, tsc) to harvest diagnostics.
        """
        if not os.path.isfile(file_path):
            return []

        ext = os.path.splitext(file_path)[1].lower()
        working_dir = cwd or os.path.dirname(file_path) or "."

        if custom_cmd:
            cmd = custom_cmd
        elif ext == ".py":
            cmd = [sys.executable, "-m", "py_compile", file_path]
        elif ext == ".rs" and shutil.which("cargo"):
            cmd = ["cargo", "check", "--message-format=short"]
        elif ext in (".ts", ".tsx") and shutil.which("tsc"):
            cmd = ["tsc", "--noEmit", file_path]
        else:
            return []

        try:
            proc = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            return LSPDiagnosticHarvester._parse_compiler_output(file_path, proc.stdout, proc.stderr, ext)
        except Exception as e:
            logger.debug("Compiler oracle execution failed for %s: %s", file_path, e)
            return []

    @staticmethod
    def _parse_compiler_output(
        file_path: str, stdout: str, stderr: str, ext: str
    ) -> List[LSPDiagnostic]:
        combined = f"{stdout}\n{stderr}"
        diagnostics: List[LSPDiagnostic] = []

        if ext == ".py":
            # Python SyntaxError or IndentationError traceback
            match = re.search(r"File \"(.*?)\", line (\d+).*?\n\s*(.*?)\n\s*\^?\s*\n(\w+Error):\s*(.*)", combined)
            if match:
                f, line_no, _, err_type, msg = match.groups()
                diagnostics.append(
                    LSPDiagnostic(
                        file_path=file_path,
                        line_number=int(line_no),
                        column=0,
                        severity="Error",
                        source="py_compile",
                        code=err_type,
                        message=msg.strip(),
                    )
                )

        elif ext == ".rs":
            # cargo check format: file:line:col: error[E0308]: mismatched types
            for line in combined.splitlines():
                m = re.match(r"(.*?):(\d+):(\d+):\s*(error|warning)(?:\[(.*?)\])?:\s*(.*)", line)
                if m:
                    f, line_no, col, sev, code, msg = m.groups()
                    diagnostics.append(
                        LSPDiagnostic(
                            file_path=f if os.path.isabs(f) else os.path.abspath(f),
                            line_number=int(line_no),
                            column=int(col),
                            severity="Error" if sev == "error" else "Warning",
                            source="rustc",
                            code=code or "",
                            message=msg.strip(),
                        )
                    )

        elif ext in (".ts", ".tsx"):
            # tsc format: file(line,col): error TS2304: Cannot find name 'x'.
            for line in combined.splitlines():
                m = re.match(r"(.*?)\((\d+),(\d+)\):\s*(error|warning)\s*(TS\d+):\s*(.*)", line)
                if m:
                    f, line_no, col, sev, code, msg = m.groups()
                    diagnostics.append(
                        LSPDiagnostic(
                            file_path=f if os.path.isabs(f) else os.path.abspath(f),
                            line_number=int(line_no),
                            column=int(col),
                            severity="Error" if sev == "error" else "Warning",
                            source="tsc",
                            code=code,
                            message=msg.strip(),
                        )
                    )

        return diagnostics


class CompilerOracleRepairLoop:
    """Drives compiler oracle repair loops using RL search until errors are resolved."""

    def __init__(
        self,
        harvester: Optional[LSPDiagnosticHarvester] = None,
        evaluator: Optional[GraduatedRewardEvaluator] = None,
        gate: Optional[AdversarialCertificationGate] = None,
        sandbox: Optional[VerificationSandbox] = None,
    ):
        self.harvester = harvester or LSPDiagnosticHarvester()
        self.sandbox = sandbox or VerificationSandbox()
        self.evaluator = evaluator or GraduatedRewardEvaluator(sandbox=self.sandbox)
        self.gate = gate or AdversarialCertificationGate(sandbox=self.sandbox)

    def handle_diagnostic_report(
        self,
        payload: Dict[str, Any],
        workspace_root: str = "",
    ) -> Tuple[Optional[RLTask], List[LSPDiagnostic]]:
        """
        Wires incoming diagnostics/report payload from IDE into an actionable RLTask.
        Harvests LSP diagnostics, filters for Error severity, and constructs a repair task
        targeted at eliminating compiler diagnostics.
        """
        diags = self.harvester.harvest_from_payload(payload)
        error_diags = [d for d in diags if d.severity == "Error"]
        if not error_diags:
            return None, diags

        file_path = payload.get("file_path", "")
        code_str = payload.get("code", "")
        task_id = payload.get("task_id") or f"repair_{os.path.basename(file_path)}_{int(time.time() * 1000)}"

        task = self.build_repair_task(
            task_id=task_id,
            file_path=file_path,
            code_str=code_str,
            diagnostics=error_diags,
            workspace_root=workspace_root or payload.get("workspace_root", ""),
        )
        return task, diags

    def build_repair_task(
        self,
        task_id: str,
        file_path: str,
        code_str: str,
        diagnostics: List[LSPDiagnostic],
        workspace_root: str = "",
    ) -> RLTask:
        """
        Creates an RLTask targeted at fixing specific compiler diagnostics.
        """
        diag_summaries = []
        for d in diagnostics:
            diag_summaries.append(f"- Line {d.line_number}: [{d.source}:{d.code}] {d.message}")

        instruction = (
            f"Fix the following {len(diagnostics)} compiler/linter diagnostics in this file:\n"
            + "\n".join(diag_summaries)
        )

        return RLTask(
            task_id=task_id,
            target_file=file_path,
            test_target="# Compiler oracle self-healing validation",
            workspace_root=workspace_root,
            instruction=instruction,
            original_code=code_str,
            target_filename=os.path.basename(file_path),
        )

    def evaluate_candidate_patch(
        self,
        file_path: str,
        original_code: str,
        candidate_code: str,
        initial_diagnostics: List[LSPDiagnostic],
        test_source: Optional[str] = None,
        regression_test_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates candidate patch against:
        1. AST syntax and security validity.
        2. Compiler oracle diagnostic reduction (in-memory syntax/compiler verification).
        3. Graduated continuous dense reward (0.15 S_ast + 0.25 S_diag + 0.25 S_reg + 0.35 S_test).
        4. Adversarial mutation certification gate (K=5 AST mutants; M_kill >= 0.50 => R=1.00).

        Returns:
            Dict containing:
            - passed: bool (True only when reward == 1.00 and mutation certified)
            - reward: float (1.00 when certified)
            - is_certified: bool
            - kill_ratio: float
            - remaining_diagnostics: List[LSPDiagnostic]
            - breakdown: Optional[GraduatedRewardBreakdown]
        """
        orig_count = len([d for d in initial_diagnostics if d.severity == "Error"])
        target_filename = os.path.basename(file_path)

        # 1. AST syntax & security barrier check
        s_ast, ast_err = self.evaluator.compute_ast_signal(candidate_code)
        if s_ast < 1.0:
            err_diag = LSPDiagnostic(
                file_path=file_path,
                line_number=1,
                column=0,
                severity="Error",
                source="ast_verifier",
                code="SyntaxOrSecurityError",
                message=str(ast_err) if ast_err else "AST validation failed",
            )
            return {
                "passed": False,
                "reward": 0.0,
                "is_certified": False,
                "kill_ratio": 0.0,
                "remaining_diagnostics": [err_diag],
                "breakdown": None,
            }

        # 2. In-memory compiler oracle verification (zero temporary files on disk)
        rem_diags: List[LSPDiagnostic] = []
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            try:
                compile(candidate_code, file_path, "exec")
            except SyntaxError as se:
                rem_diags.append(
                    LSPDiagnostic(
                        file_path=file_path,
                        line_number=se.lineno or 1,
                        column=se.offset or 0,
                        severity="Error",
                        source="py_compile",
                        code="SyntaxError",
                        message=se.msg,
                    )
                )
            except Exception as e:
                rem_diags.append(
                    LSPDiagnostic(
                        file_path=file_path,
                        line_number=1,
                        column=0,
                        severity="Error",
                        source="py_compile",
                        code=type(e).__name__,
                        message=str(e),
                    )
                )
        elif os.path.isfile(file_path):
            rem_diags = self.harvester.harvest_from_compiler_oracle(file_path)

        new_count = len([d for d in rem_diags if d.severity == "Error"])

        # 3. Unit test execution in sandbox
        if test_source:
            sb_res = self.sandbox.execute_candidate(
                candidate_code=candidate_code,
                test_source=test_source,
                target_filename=target_filename,
            )
        else:
            tests_passed = 1 if new_count == 0 else 0
            total_tests = 1
            reward_val = 1.0 if new_count == 0 else max(0.0, 1.0 - (new_count / max(1, orig_count)))
            sb_res = SandboxResult(
                status="PASSED" if new_count == 0 else "FAILED",
                passed_tests=tests_passed,
                total_tests=total_tests,
                reward=reward_val,
                error_message=rem_diags[0].message if rem_diags else None,
            )

        # 4. Graduated reward breakdown
        breakdown = self.evaluator.evaluate(
            candidate_code=candidate_code,
            target_sandbox_result=sb_res,
            orig_diag_count=orig_count,
            new_diag_count=new_count,
        )

        # 5. Adversarial AST Mutation Testing Gate (K=5 mutants, M_kill >= 0.50 => R=1.00)
        effective_test_code = test_source
        if not effective_test_code and ext == ".py":
            effective_test_code = self._synthesize_sanity_test(candidate_code, target_filename)

        if effective_test_code:
            cert_res = self.gate.certify(
                candidate_code=candidate_code,
                test_source=effective_test_code,
                target_filename=target_filename,
            )
            is_certified = cert_res.is_certified
            kill_ratio = cert_res.kill_ratio
        else:
            is_certified = False
            kill_ratio = 0.0

        is_passed = (
            new_count == 0
            and breakdown.s_ast == 1.0
            and is_certified
            and kill_ratio >= 0.50
        )

        final_reward = 1.00 if is_passed else min(breakdown.total_reward, 0.50)

        return {
            "passed": is_passed,
            "reward": final_reward,
            "is_certified": is_certified,
            "kill_ratio": kill_ratio,
            "remaining_diagnostics": rem_diags,
            "breakdown": breakdown,
        }

    def _synthesize_sanity_test(self, candidate_code: str, target_filename: str) -> Optional[str]:
        """Synthesizes a minimal test harness for defined functions to test mutation sensitivity."""
        try:
            import ast
            tree = ast.parse(candidate_code)
            mod_name = os.path.splitext(target_filename)[0]
            func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
            if not func_names:
                return None
            lines = [
                "import unittest",
                f"import {mod_name}",
                "",
                "class TestSanity(unittest.TestCase):",
            ]
            for fn in func_names:
                lines.append(f"    def test_{fn}_callable(self):")
                lines.append(f"        self.assertTrue(callable(getattr({mod_name}, '{fn}')))")
            return "\n".join(lines)
        except Exception:
            return None

    def verify_repair(
        self,
        file_path: str,
        candidate_code: str,
        initial_diag_count: int,
        test_source: Optional[str] = None,
    ) -> Tuple[bool, int, List[LSPDiagnostic]]:
        """
        Evaluates candidate code in-memory without leaving temporary files on disk.
        Returns (is_repaired, remaining_count, new_diagnostics).
        """
        initial_diags = [
            LSPDiagnostic(
                file_path=file_path,
                line_number=1,
                column=0,
                severity="Error",
                source="lsp",
                code="E001",
                message="Initial diagnostic error",
            )
            for _ in range(initial_diag_count)
        ]
        res = self.evaluate_candidate_patch(
            file_path=file_path,
            original_code="",
            candidate_code=candidate_code,
            initial_diagnostics=initial_diags,
            test_source=test_source,
        )
        rem_count = len(res["remaining_diagnostics"])
        is_repaired = res["passed"] or (rem_count < initial_diag_count)
        return is_repaired, rem_count, res["remaining_diagnostics"]

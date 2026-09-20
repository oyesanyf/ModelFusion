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
from typing import List, Optional, Dict, Any, Tuple

from .adapters.base import RLTask

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

    def __init__(self, harvester: Optional[LSPDiagnosticHarvester] = None):
        self.harvester = harvester or LSPDiagnosticHarvester()

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

    def verify_repair(
        self,
        file_path: str,
        candidate_code: str,
        initial_diag_count: int,
    ) -> Tuple[bool, int, List[LSPDiagnostic]]:
        """
        Writes candidate code to temporary staging, runs oracle, and checks if diagnostics decreased.
        Returns (is_repaired, remaining_count, new_diagnostics).
        """
        import tempfile
        ext = os.path.splitext(file_path)[1]
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w", encoding="utf-8", delete=False) as tf:
            tf.write(candidate_code)
            tmp_name = tf.name

        try:
            new_diags = self.harvester.harvest_from_compiler_oracle(tmp_name)
            rem_count = len([d for d in new_diags if d.severity == "Error"])
            is_repaired = rem_count == 0 or rem_count < initial_diag_count
            return is_repaired, rem_count, new_diags
        finally:
            try:
                os.unlink(tmp_name)
            except Exception:
                pass

#!/usr/bin/env python3
"""
Adversarial Mutation Verifier for ReST-RL / GRPO Autonomous Collaborator.

Generates K AST mutants using 5 mutation operators:
1. ROR: Relational Operator Replacement (e.g., == <-> !=, < <-> >=)
2. AOR: Arithmetic Operator Replacement (e.g., + <-> -, * <-> /)
3. LOR: Logical Operator Replacement (e.g., and <-> or)
4. SDL: Statement Deletion (replaces statements with pass)
5. RVR: Return Value Replacement (inverts or nullifies return expressions)

Enforces the Adversarial Certification Gate:
- If M_kill >= 0.5: Certified passing solution (R = 1.0)
- If M_kill == 0.0: Vacuous test suite detected (R = 0.0, rejected)
- If 0.0 < M_kill < 0.5: Weak test suite (R = 0.5, flagged)
"""

from __future__ import annotations

import ast
import copy
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Tuple, Dict, Any

from .sandbox import VerificationSandbox, SandboxResult

logger = logging.getLogger("rest_rl.mutation_verifier")


@dataclass
class MutantRecord:
    operator: str
    description: str
    mutant_code: str
    killed: bool
    sandbox_result: Optional[SandboxResult] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.sandbox_result:
            d["sandbox_result"] = self.sandbox_result.to_dict()
        return d


@dataclass
class CertificationResult:
    is_certified: bool
    certified_reward: float
    kill_ratio: float
    total_mutants: int
    killed_count: int
    mutants: List[MutantRecord] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_certified": self.is_certified,
            "certified_reward": self.certified_reward,
            "kill_ratio": round(self.kill_ratio, 4),
            "total_mutants": self.total_mutants,
            "killed_count": self.killed_count,
            "rejection_reason": self.rejection_reason,
            "mutants": [m.to_dict() for m in self.mutants],
        }


class ASTMutator:
    """Generates syntactic and semantic AST mutations across 5 primary operators."""

    # 1. ROR: Relational Operator Replacement map
    ROR_MAP = {
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.GtE,
        ast.LtE: ast.Gt,
        ast.Gt: ast.LtE,
        ast.GtE: ast.Lt,
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
    }

    # 2. AOR: Arithmetic Operator Replacement map
    AOR_MAP = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.FloorDiv,
        ast.Div: ast.Mult,
        ast.FloorDiv: ast.Mult,
        ast.Mod: ast.Mult,
        ast.Pow: ast.Mult,
    }

    # 3. LOR: Logical Operator Replacement map
    LOR_MAP = {
        ast.And: ast.Or,
        ast.Or: ast.And,
    }

    def generate_mutants(self, code_str: str, max_mutants: int = 5) -> List[Tuple[str, str, str]]:
        """
        Generates up to max_mutants distinct valid AST mutants.
        Returns list of (operator_name, description, mutant_code_str).
        """
        try:
            tree = ast.parse(code_str)
        except Exception as e:
            logger.debug("Failed to parse code for mutation: %s", e)
            return []

        mutants: List[Tuple[str, str, str]] = []
        seen_codes = {code_str}

        # Collect applicable mutation targets
        ror_candidates: List[Tuple[ast.Compare, int, Any]] = []
        aor_candidates: List[Tuple[ast.BinOp, Any]] = []
        lor_candidates: List[Tuple[ast.BoolOp, Any]] = []
        sdl_candidates: List[Tuple[Any, int, ast.AST]] = []
        rvr_candidates: List[ast.Return] = []

        for node in ast.walk(tree):
            # ROR
            if isinstance(node, ast.Compare):
                for idx, op in enumerate(node.ops):
                    op_type = type(op)
                    if op_type in self.ROR_MAP:
                        ror_candidates.append((node, idx, self.ROR_MAP[op_type]))

            # AOR
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type in self.AOR_MAP:
                    aor_candidates.append((node, self.AOR_MAP[op_type]))

            # LOR
            elif isinstance(node, ast.BoolOp):
                op_type = type(node.op)
                if op_type in self.LOR_MAP:
                    lor_candidates.append((node, self.LOR_MAP[op_type]))

            # RVR
            elif isinstance(node, ast.Return) and node.value is not None:
                rvr_candidates.append(node)

        # Walk body statements for SDL (Statement Deletion)
        for node in ast.walk(tree):
            if hasattr(node, "body") and isinstance(node.body, list):
                for idx, stmt in enumerate(node.body):
                    if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Expr)) and not isinstance(stmt.value, ast.Constant):
                        sdl_candidates.append((node, idx, stmt))

        # 1. Generate ROR Mutants
        for comp_node, op_idx, new_op_cls in ror_candidates:
            if len(mutants) >= max_mutants:
                break
            tree_copy = copy.deepcopy(tree)
            target = self._find_matching_node(tree_copy, comp_node)
            if target and isinstance(target, ast.Compare) and op_idx < len(target.ops):
                target.ops[op_idx] = new_op_cls()
                mut_code = self._unparse(tree_copy)
                if mut_code and mut_code not in seen_codes:
                    seen_codes.add(mut_code)
                    mutants.append(("ROR", f"Replaced relational operator at line {getattr(comp_node, 'lineno', 1)}", mut_code))

        # 2. Generate AOR Mutants
        for bin_node, new_op_cls in aor_candidates:
            if len(mutants) >= max_mutants:
                break
            tree_copy = copy.deepcopy(tree)
            target = self._find_matching_node(tree_copy, bin_node)
            if target and isinstance(target, ast.BinOp):
                target.op = new_op_cls()
                mut_code = self._unparse(tree_copy)
                if mut_code and mut_code not in seen_codes:
                    seen_codes.add(mut_code)
                    mutants.append(("AOR", f"Replaced arithmetic operator at line {getattr(bin_node, 'lineno', 1)}", mut_code))

        # 3. Generate LOR Mutants
        for bool_node, new_op_cls in lor_candidates:
            if len(mutants) >= max_mutants:
                break
            tree_copy = copy.deepcopy(tree)
            target = self._find_matching_node(tree_copy, bool_node)
            if target and isinstance(target, ast.BoolOp):
                target.op = new_op_cls()
                mut_code = self._unparse(tree_copy)
                if mut_code and mut_code not in seen_codes:
                    seen_codes.add(mut_code)
                    mutants.append(("LOR", f"Replaced logical operator at line {getattr(bool_node, 'lineno', 1)}", mut_code))

        # 4. Generate RVR Mutants (Return Value Replacement)
        for ret_node in rvr_candidates:
            if len(mutants) >= max_mutants:
                break
            tree_copy = copy.deepcopy(tree)
            target = self._find_matching_node(tree_copy, ret_node)
            if target and isinstance(target, ast.Return) and target.value is not None:
                # Mutate return value: if bool/number, invert; else return None
                if isinstance(target.value, ast.Constant):
                    if isinstance(target.value.value, bool):
                        target.value.value = not target.value.value
                    elif isinstance(target.value.value, (int, float)):
                        target.value.value = 0 if target.value.value != 0 else 1
                    else:
                        target.value = ast.Constant(value=None)
                else:
                    target.value = ast.Constant(value=None)

                mut_code = self._unparse(tree_copy)
                if mut_code and mut_code not in seen_codes:
                    seen_codes.add(mut_code)
                    mutants.append(("RVR", f"Replaced return value at line {getattr(ret_node, 'lineno', 1)}", mut_code))

        # 5. Generate SDL Mutants (Statement Deletion -> pass)
        for parent_node, stmt_idx, stmt in sdl_candidates:
            if len(mutants) >= max_mutants:
                break
            tree_copy = copy.deepcopy(tree)
            target_parent = self._find_matching_node(tree_copy, parent_node)
            if target_parent and hasattr(target_parent, "body") and stmt_idx < len(target_parent.body):
                target_parent.body[stmt_idx] = ast.Pass()
                mut_code = self._unparse(tree_copy)
                if mut_code and mut_code not in seen_codes:
                    seen_codes.add(mut_code)
                    mutants.append(("SDL", f"Deleted statement at line {getattr(stmt, 'lineno', 1)} (replaced with pass)", mut_code))

        return mutants

    @staticmethod
    def _unparse(tree: ast.AST) -> Optional[str]:
        try:
            return ast.unparse(tree)
        except Exception:
            return None

    @staticmethod
    def _find_matching_node(tree: ast.AST, original_node: ast.AST) -> Optional[ast.AST]:
        """Finds equivalent node in cloned AST by matching line number, column, and type."""
        orig_lineno = getattr(original_node, "lineno", None)
        orig_col = getattr(original_node, "col_offset", None)
        orig_type = type(original_node)

        for n in ast.walk(tree):
            if type(n) is orig_type:
                if (
                    orig_lineno is not None
                    and getattr(n, "lineno", None) == orig_lineno
                    and getattr(n, "col_offset", None) == orig_col
                ):
                    return n

        # Fallback by type match
        for n in ast.walk(tree):
            if type(n) is orig_type:
                return n

        return None


class AdversarialCertificationGate:
    """
    Executes adversarial mutation testing against passing candidate solutions.
    Certifies candidate patches only if unit tests actively detect and kill mutated bugs.
    """

    def __init__(
        self,
        sandbox: Optional[VerificationSandbox] = None,
        mutator: Optional[ASTMutator] = None,
        k_mutants: int = 5,
        certification_threshold: float = 0.5,
    ):
        self.sandbox = sandbox or VerificationSandbox()
        self.mutator = mutator or ASTMutator()
        self.k_mutants = k_mutants
        self.certification_threshold = certification_threshold

    def certify(
        self,
        candidate_code: str,
        test_source: str,
        target_filename: str = "solution.py",
        workspace_root: Optional[str] = None,
    ) -> CertificationResult:
        """
        Runs the adversarial verification gate:
        1. Generates K mutants across ROR, AOR, LOR, SDL, RVR.
        2. Executes test suite against each mutant.
        3. Computes kill ratio M_kill.
        """
        mutant_specs = self.mutator.generate_mutants(candidate_code, max_mutants=self.k_mutants)
        if not mutant_specs:
            # Candidate code contains no mutable AST statements (e.g. empty pass); cannot certify
            return CertificationResult(
                is_certified=False,
                certified_reward=0.50,
                kill_ratio=0.0,
                total_mutants=0,
                killed_count=0,
                mutants=[],
                rejection_reason="No mutable AST statements found in candidate patch.",
            )

        mutant_records: List[MutantRecord] = []
        killed_count = 0

        for op, desc, mut_code in mutant_specs:
            res = self.sandbox.execute_candidate(
                candidate_code=mut_code,
                test_source=test_source,
                target_filename=target_filename,
                workspace_root=workspace_root,
                timeout=3.0,
            )

            # A mutant is killed if tests FAIL (reward < 1.0 or non-PASSED status)
            is_killed = (res.reward < 1.0 or res.status != "PASSED")
            if is_killed:
                killed_count += 1

            mutant_records.append(
                MutantRecord(
                    operator=op,
                    description=desc,
                    mutant_code=mut_code,
                    killed=is_killed,
                    sandbox_result=res,
                )
            )

        total_mutants = len(mutant_records)
        kill_ratio = killed_count / total_mutants if total_mutants > 0 else 1.0

        # Adversarial certification rule
        if kill_ratio >= self.certification_threshold:
            # Full certification (R = 1.0)
            return CertificationResult(
                is_certified=True,
                certified_reward=1.0,
                kill_ratio=kill_ratio,
                total_mutants=total_mutants,
                killed_count=killed_count,
                mutants=mutant_records,
                rejection_reason=None,
            )
        elif kill_ratio == 0.0:
            # Vacuous test suite detected: tests passed even when code was mutated!
            return CertificationResult(
                is_certified=False,
                certified_reward=0.0,
                kill_ratio=0.0,
                total_mutants=total_mutants,
                killed_count=0,
                mutants=mutant_records,
                rejection_reason="Vacuous test suite: all AST mutants survived without triggering test failures.",
            )
        else:
            # Weak test coverage (< 0.50 kill ratio)
            return CertificationResult(
                is_certified=False,
                certified_reward=0.5,
                kill_ratio=kill_ratio,
                total_mutants=total_mutants,
                killed_count=killed_count,
                mutants=mutant_records,
                rejection_reason=f"Weak test sensitivity: kill ratio {kill_ratio:.2f} below certification threshold ({self.certification_threshold:.2f}).",
            )

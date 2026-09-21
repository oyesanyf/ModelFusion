#!/usr/bin/env python3
"""
Empirical Performance Benchmark Harness for R3:
Semantic Codebase Knowledge Graph (`cli.exe --graph-query`).

Verifies:
- Sub-25ms Query Performance SLA across:
  1. Single-symbol definition lookup (<25ms SLA, expected <1ms)
  2. Recursive CTE 3-hop call hierarchy traversal (<25ms SLA, expected <5ms)
  3. Reverse call hierarchy (callers) traversal (<25ms SLA, expected <5ms)
  4. FTS5 + TermVector hybrid search (<25ms SLA, expected <10ms)
  5. Composite 'all' graph query (<25ms SLA)
- Multiple iterations (N=10) to calculate min, mean, and max response times.
"""

import os
import sys
import json
import time
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLI_EXE = os.path.join(REPO_ROOT, "target", "release", "cli.exe")
DB_PATH = os.path.join(REPO_ROOT, "IDE", "db", "code_graph.db")


class TestR3EmpiricalGraphPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(CLI_EXE):
            raise RuntimeError(f"cli.exe not found at {CLI_EXE}")
        if not os.path.isfile(DB_PATH):
            print(f"[R3 Setup] DB not found at {DB_PATH}, indexing workspace first...")
            subprocess.run([CLI_EXE, "--graph-index", "--db-path", DB_PATH], check=True)

    def _execute_cli_query(self, query_str: str, query_type: str = "all") -> dict:
        cmd = [
            CLI_EXE,
            "--graph-query", query_str,
            "--query-type", query_type,
            "--db-path", DB_PATH,
        ]
        t0 = time.perf_hooks_time = time.perf_counter()
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        t_total_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(proc.returncode, 0, f"cli.exe failed with stderr:\n{proc.stderr}")
        
        # Extract JSON from output
        out = proc.stdout.strip()
        # Find JSON object start
        json_start = out.find("{\n  \"query\":")
        if json_start == -1:
            json_start = out.find("{")
        
        self.assertNotEqual(json_start, -1, f"Could not find JSON in cli output:\n{out}")
        json_str = out[json_start:]
        data = json.loads(json_str)
        data["_total_cli_process_elapsed_ms"] = t_total_ms
        return data

    def test_01_single_symbol_lookup_sla(self):
        """Benchmark single-symbol definition lookup (<25ms SLA)."""
        symbol = "CodeGraphQueryEngine"
        elapsed_runs = []
        for _ in range(10):
            res = self._execute_cli_query(symbol, query_type="symbol")
            elapsed_runs.append(res.get("elapsed_ms", 0.0))

        mean_ms = sum(elapsed_runs) / len(elapsed_runs)
        min_ms = min(elapsed_runs)
        max_ms = max(elapsed_runs)
        print(f"\n[R3 Benchmark] Single-Symbol Lookup ('{symbol}'): Mean={mean_ms:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(max_ms, 25.0, f"Single-symbol lookup max time ({max_ms:.2f}ms) exceeded 25ms SLA!")
        self.assertGreater(len(res.get("symbols", [])), 0)

    def test_02_recursive_cte_call_hierarchy_sla(self):
        """Benchmark 3-hop recursive CTE call hierarchy (<25ms SLA)."""
        symbol = "CodeGraphQueryEngine"
        elapsed_runs = []
        for _ in range(10):
            res = self._execute_cli_query(symbol, query_type="calls")
            elapsed_runs.append(res.get("elapsed_ms", 0.0))

        mean_ms = sum(elapsed_runs) / len(elapsed_runs)
        min_ms = min(elapsed_runs)
        max_ms = max(elapsed_runs)
        print(f"[R3 Benchmark] Recursive CTE Calls ('{symbol}'): Mean={mean_ms:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(max_ms, 25.0, f"Recursive CTE call hierarchy max time ({max_ms:.2f}ms) exceeded 25ms SLA!")
        self.assertIsNotNone(res.get("call_hierarchy"))

    def test_03_reverse_callers_traversal_sla(self):
        """Benchmark reverse call hierarchy (callers) (<25ms SLA)."""
        symbol = "lookup_symbol"
        elapsed_runs = []
        for _ in range(10):
            res = self._execute_cli_query(symbol, query_type="callers")
            elapsed_runs.append(res.get("elapsed_ms", 0.0))

        mean_ms = sum(elapsed_runs) / len(elapsed_runs)
        min_ms = min(elapsed_runs)
        max_ms = max(elapsed_runs)
        print(f"[R3 Benchmark] Reverse Callers Traversal ('{symbol}'): Mean={mean_ms:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(max_ms, 25.0, f"Reverse callers max time ({max_ms:.2f}ms) exceeded 25ms SLA!")
        self.assertIsNotNone(res.get("callers"))

    def test_04_fts5_hybrid_search_sla(self):
        """Benchmark FTS5 + TermVector hybrid search (<25ms SLA)."""
        query_text = "hybrid search query"
        elapsed_runs = []
        for _ in range(10):
            res = self._execute_cli_query(query_text, query_type="search")
            elapsed_runs.append(res.get("elapsed_ms", 0.0))

        mean_ms = sum(elapsed_runs) / len(elapsed_runs)
        min_ms = min(elapsed_runs)
        max_ms = max(elapsed_runs)
        print(f"[R3 Benchmark] FTS5 + TermVector Search ('{query_text}'): Mean={mean_ms:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(max_ms, 25.0, f"FTS5 search max time ({max_ms:.2f}ms) exceeded 25ms SLA!")
        self.assertGreater(len(res.get("search_results", [])), 0)

    def test_05_composite_all_query_sla(self):
        """Benchmark composite 'all' query (<25ms SLA)."""
        symbol = "CodeGraphIndexer"
        elapsed_runs = []
        for _ in range(10):
            res = self._execute_cli_query(symbol, query_type="all")
            elapsed_runs.append(res.get("elapsed_ms", 0.0))

        mean_ms = sum(elapsed_runs) / len(elapsed_runs)
        min_ms = min(elapsed_runs)
        max_ms = max(elapsed_runs)
        print(f"[R3 Benchmark] Composite Query ('{symbol}'): Mean={mean_ms:.2f}ms, Min={min_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(max_ms, 25.0, f"Composite 'all' query max time ({max_ms:.2f}ms) exceeded 25ms SLA!")


if __name__ == "__main__":
    unittest.main()

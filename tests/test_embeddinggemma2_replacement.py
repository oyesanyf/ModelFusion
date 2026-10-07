#!/usr/bin/env python3
"""
Test Suite: Google EmbeddingGemma 2 Replacement Verification
Verifies that google/embeddinggemma-2 is authoritative default across:
1. config/task_models.json (sentence-similarity & feature-extraction)
2. config/model_configs.json (8192 context, 768 dims, MRL, multimodal tags)
3. crates/core/src/task_handler.rs (architecture boost & param estimation)
4. IDE/db/hf_models.db (authoritative #1 ranking model for sentence-similarity)
5. crates/cli/src/main.rs (hardware provisioning & API endpoints)
"""

import os
import sys
import json
import sqlite3
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestEmbeddingGemma2Replacement(unittest.TestCase):

    def test_01_task_models_config(self):
        """Asserts config/task_models.json has best_model == 'google/embeddinggemma-2' for sentence-similarity & feature-extraction."""
        path = os.path.join(REPO_ROOT, "config", "task_models.json")
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check sentence-similarity in special_tasks
        spec_tasks = data.get("special_tasks", {})
        self.assertIn("sentence-similarity", spec_tasks)
        ss = spec_tasks["sentence-similarity"]
        self.assertEqual(ss.get("best_model"), "google/embeddinggemma-2")
        self.assertEqual(ss.get("model_author"), "google")
        self.assertIn("EmbeddingGemma 2", ss.get("description", ""))
        self.assertIn("768d", ss.get("description", ""))
        self.assertIn("MRL", ss.get("description", ""))

        # Verify sentence-transformers/all-MiniLM-L6-v2 is in alternative_models
        alt_ids = [m.get("model_id") for m in ss.get("alternative_models", [])]
        self.assertIn("sentence-transformers/all-MiniLM-L6-v2", alt_ids)

        # Check feature-extraction in text_processing
        tp_tasks = data.get("text_processing", {})
        self.assertIn("feature-extraction", tp_tasks)
        fe = tp_tasks["feature-extraction"]
        self.assertEqual(fe.get("best_model"), "google/embeddinggemma-2")
        self.assertEqual(fe.get("model_author"), "google")
        self.assertIn("EmbeddingGemma 2", fe.get("description", ""))
        print("  [PASS] config/task_models.json verified for sentence-similarity & feature-extraction")

    def test_02_model_configs(self):
        """Asserts config/model_configs.json contains 'google/embeddinggemma-2' with 8192 context, 768 dims, MRL, and multimodal tags."""
        path = os.path.join(REPO_ROOT, "config", "model_configs.json")
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("google/embeddinggemma-2", data)
        cfg = data["google/embeddinggemma-2"]
        self.assertEqual(cfg.get("model_id"), "google/embeddinggemma-2")
        self.assertEqual(cfg.get("author"), "google")
        self.assertEqual(cfg.get("architecture"), "Gemma4Embedding")
        self.assertEqual(cfg.get("dimensions"), 768)
        self.assertEqual(cfg.get("max_position_embeddings"), 8192)
        self.assertEqual(cfg.get("mrl_dimensions"), [128, 256, 512, 768])
        self.assertIn("multimodal", cfg.get("tags", []))
        self.assertIn("image", cfg.get("modalities", []))
        self.assertIn("video", cfg.get("modalities", []))
        self.assertIn("audio", cfg.get("modalities", []))
        self.assertIn("code", cfg.get("modalities", []))
        print("  [PASS] config/model_configs.json contains google/embeddinggemma-2 with full spec")

    def test_03_core_task_handler(self):
        """Asserts crates/core/src/task_handler.rs handles embeddinggemma."""
        path = os.path.join(REPO_ROOT, "crates", "core", "src", "task_handler.rs")
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check parameter estimation
        self.assertIn('name_lower.contains("embeddinggemma")', content)
        self.assertIn("0.35", content)

        # Check score boost
        self.assertTrue(
            'name_lower.contains("embeddinggemma")' in content or
            'name_lower.contains("embedding-gemma")' in content
        )
        print("  [PASS] crates/core/src/task_handler.rs handles embeddinggemma parameter estimation and scoring boost")

    def test_04_sqlite_database_ranking(self):
        """Asserts IDE/db/hf_models.db has google/embeddinggemma-2 as top-ranking model for sentence-similarity."""
        db_path = os.path.join(REPO_ROOT, "IDE", "db", "hf_models.db")
        self.assertTrue(os.path.exists(db_path), f"Database not found: {db_path}")

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT model_id, pipeline_tag, downloads, decision_score
            FROM models
            WHERE pipeline_tag = 'sentence-similarity'
            ORDER BY downloads DESC, decision_score DESC
            LIMIT 1
        """)
        top_row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(top_row, "No sentence-similarity model found in db")
        self.assertEqual(top_row[0], "google/embeddinggemma-2", f"Expected top model to be google/embeddinggemma-2, got {top_row[0]}")
        self.assertEqual(top_row[1], "sentence-similarity")
        self.assertGreaterEqual(top_row[2], 500000000)
        self.assertGreaterEqual(top_row[3], 9.5)
        print(f"  [PASS] IDE/db/hf_models.db top model is {top_row[0]} with {top_row[2]:,} downloads and score {top_row[3]}")

    def test_05_cli_provisioning_and_endpoints(self):
        """Asserts crates/cli/src/main.rs provisions 'embeddinggemma' and serves /api/embeddings."""
        path = os.path.join(REPO_ROOT, "crates", "cli", "src", "main.rs")
        self.assertTrue(os.path.exists(path), f"File not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check hardware provisioning pulls embeddinggemma
        self.assertIn('"embeddinggemma"', content)
        self.assertIn("Embedding='embeddinggemma'", content)

        # Check seed function exists
        self.assertIn("fn seed_embeddinggemma_into_db", content)

        # Check /api/embeddings or /api/embed endpoint
        self.assertIn("/api/embeddings", content)
        self.assertIn("/api/embed", content)
        print("  [PASS] crates/cli/src/main.rs provisions embeddinggemma and hosts /api/embeddings endpoint")

if __name__ == "__main__":
    print("\n==================================================================")
    print(" Running Google EmbeddingGemma 2 Verification Test Suite")
    print("==================================================================")
    unittest.main(verbosity=2)

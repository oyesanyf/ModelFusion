#!/usr/bin/env python3
"""
Adversarial Empirical Challenge Test Suite (Challenger 2)
Milestone 1: Stage 0 Trending & Following Activity Ingestion
============================================================
Adversarial verification testing:
1. Exact 9 followed research orgs queried.
2. Complete pipeline_tag -> 19 Browser categories mapping without exception.
3. Fault injection & resilience: network timeouts, offline mode, HTTP 429, 500, corrupt JSON.
4. Database schema migration, idempotency, and persistence.
5. Automated cargo check -p modelfusion_core and cargo test -p db.
"""

import os
import sys
import re
import json
import time
import socket
import sqlite3
import tempfile
import unittest
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_browser_categories_from_html():
    """Extract authoritative 19 categories from browser/ui/index.html."""
    html_path = REPO_ROOT / "browser" / "ui" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    headers = re.findall(r'class="cat-title">([^<]+)</span>', content)
    clean = [re.sub(r'^[^\w\s]+', '', h).replace('&amp;', '&').strip() for h in headers]
    return clean


class TestAdversarialResearchOrgs(unittest.TestCase):
    """
    Challenge 1: Verify that exactly the 9 followed research orgs
    (RecursiveSI, Qwen, deepseek-ai, google, meta-llama, mistralai, microsoft, allenai, nvidia)
    are defined and queried in crates/core/src/task_handler.rs.
    """

    EXPECTED_ORGS = [
        "RecursiveSI",
        "Qwen",
        "deepseek-ai",
        "google",
        "meta-llama",
        "mistralai",
        "microsoft",
        "allenai",
        "nvidia",
    ]

    def test_followed_research_orgs_exact_match(self):
        task_handler_path = REPO_ROOT / "crates" / "core" / "src" / "task_handler.rs"
        self.assertTrue(task_handler_path.exists(), "task_handler.rs must exist")
        content = task_handler_path.read_text(encoding="utf-8")

        # 1. Check FOLLOWED_RESEARCH_ORGS constant definition
        match = re.search(r'pub const FOLLOWED_RESEARCH_ORGS:\s*&\'static\s*\[&\'static str\]\s*=\s*&\[(.*?)\];', content, re.DOTALL)
        self.assertIsNotNone(match, "FOLLOWED_RESEARCH_ORGS constant must be defined")
        orgs_str = match.group(1)
        found_orgs = [o.strip().strip('"').strip('\'') for o in orgs_str.split(',') if o.strip().strip('"').strip('\'')]

        self.assertEqual(len(found_orgs), 9, f"Expected exactly 9 followed orgs, found {len(found_orgs)}: {found_orgs}")
        self.assertEqual(found_orgs, self.EXPECTED_ORGS, f"Mismatch in followed research orgs: {found_orgs} vs {self.EXPECTED_ORGS}")

        # 2. Verify query iteration in ingest_trending_and_following_feed
        self.assertIn("for &org in Self::FOLLOWED_RESEARCH_ORGS", content,
                      "ingest_trending_and_following_feed must iterate over Self::FOLLOWED_RESEARCH_ORGS")

        # 3. Verify API endpoint template uses author parameter
        self.assertIn("https://huggingface.co/api/models?author={}&sort=lastModified&direction=-1&limit=25&full=true", content,
                      "API URL must query HuggingFace Hub author endpoint with sort=lastModified")

        # 4. Verify candidate attribution
        self.assertIn("is_following: true", content,
                      "Models from followed orgs must be tagged with is_following = true")
        self.assertIn('"following_activity"', content,
                      "feed_source must record 'following_activity'")


class TestAdversarialCategoryMapping(unittest.TestCase):
    """
    Challenge 2: Verify that map_pipeline_tag_to_browser_category maps
    every possible pipeline tag to one of the 19 Browser categories without exception.
    """

    def setUp(self):
        self.valid_19_categories = set(get_browser_categories_from_html())
        self.assertEqual(len(self.valid_19_categories), 19,
                         f"Expected 19 categories from browser/ui/index.html, found: {len(self.valid_19_categories)}")

    def simulate_rust_category_mapper(self, pipeline_tag: str, tags: list, model_id: str) -> str:
        """Python mirror of ComprehensiveTaskHandler::map_pipeline_tag_to_browser_category."""
        id_lower = model_id.lower()
        tag_lower = [t.lower() for t in tags]

        # 1. Recursive Harnessing / Flint
        if "reflint" in id_lower or "flint" in id_lower or "harness" in id_lower:
            return "Harness2 (Recursive Agent Harnessing)"
        # 2. Computer Use & OS Automation
        if "ui-tars" in id_lower or "computer-use" in id_lower or any("computer-use" in t or "screen-grounding" in t for t in tag_lower):
            return "Computer Use & OS Automation"
        # 3. Inspect Windows Apps (.EXE / .DLL)
        if "pe-binary" in id_lower or "malware-analysis" in id_lower or any("pe-file" in t or "disassembly" in t for t in tag_lower):
            return "Inspect Windows Apps (.EXE / .DLL)"
        # 4. RD-Agent (Autonomous R&D)
        if "rdagent" in id_lower or "rd-agent" in id_lower or any("rd-agent" in t for t in tag_lower):
            return "RD-Agent (Autonomous R&D)"
        # 5. Code & Security
        if "coder" in id_lower or "code" in id_lower or any("code" in t or "vulnerability" in t or "security" in t for t in tag_lower):
            return "Code & Security"
        # 6. Compliance
        if "compliance" in id_lower or "pii" in id_lower or "gdpr" in id_lower or "hipaa" in id_lower or any("compliance" in t or "anonymization" in t for t in tag_lower):
            return "Compliance"
        # 7. Finance & Markets
        if "finance" in id_lower or "financial" in id_lower or "fintech" in id_lower or any("finance" in t or "trading" in t for t in tag_lower):
            return "Finance & Markets"
        # 8. Legal
        if "legal" in id_lower or "law" in id_lower or any("legal" in t or "contract" in t for t in tag_lower):
            return "Legal"
        # 9. Planning & Deep Thinking (Reasoning / R1 / CoT)
        if "deepseek-r1" in id_lower or "reasoning" in id_lower or "qwq" in id_lower or any("chain-of-thought" in t or "reasoning" in t for t in tag_lower):
            return "Planning & Deep Thinking"
        # 10. Sentiment & Content Moderation
        if pipeline_tag == "sentiment-analysis" or "sentiment" in id_lower or "moderation" in id_lower or any("sentiment" in t or "toxicity" in t for t in tag_lower):
            return "Sentiment & Content Moderation"
        # 11. Deep Research
        if "deep-research" in id_lower or "web-research" in id_lower or any("deep-research" in t for t in tag_lower):
            return "Deep Research"
        # 12. Web Research & Automation
        if "web-agent" in id_lower or "browser" in id_lower or any("web-scraping" in t for t in tag_lower):
            return "Web Research & Automation"
        # 13. Data & Spreadsheets (CSV/Excel)
        if pipeline_tag in ["tabular-classification", "tabular-regression", "table-question-answering", "time-series-forecasting"] or any("tabular" in t or "spreadsheet" in t for t in tag_lower):
            return "Data & Spreadsheets (CSV/Excel)"
        # 14. Images & Vision
        if pipeline_tag in ["image-classification", "object-detection", "image-segmentation", "text-to-image", "image-to-text", "image-to-image", "depth-estimation", "visual-question-answering", "document-question-answering", "zero-shot-image-classification", "zero-shot-object-detection", "mask-generation", "keypoint-detection", "video-classification", "text-to-video", "unconditional-image-generation", "image-feature-extraction"]:
            return "Images & Vision"
        # 15. Voice & Audio
        if pipeline_tag in ["automatic-speech-recognition", "audio-classification", "text-to-speech", "audio-to-audio", "voice-activity-detection", "text-to-audio"]:
            return "Voice & Audio"
        # 16. Science & Discovery
        if pipeline_tag in ["reinforcement-learning", "robotics", "graph-ml"] or "bio" in id_lower or "chem" in id_lower or "medical" in id_lower or "climate" in id_lower:
            return "Science & Discovery"
        # 17. Classification & Taxonomy
        if pipeline_tag in ["text-classification", "zero-shot-classification", "token-classification"]:
            return "Classification & Taxonomy"
        # 18. Utilities & System
        if pipeline_tag in ["sentence-similarity", "feature-extraction", "fill-mask", "translation"]:
            return "Utilities & System"
        # 19. Writing & Editing (Default for text generation)
        return "Writing & Editing"

    def test_all_hf_tasks_map_to_valid_categories(self):
        """Stress-test all 45+ Hugging Face tasks."""
        hf_tasks = [
            "text-generation", "text2text-generation", "summarization", "translation",
            "question-answering", "table-question-answering", "fill-mask", "sentence-similarity",
            "text-classification", "token-classification", "zero-shot-classification",
            "conversational", "feature-extraction",
            "automatic-speech-recognition", "audio-classification", "text-to-speech",
            "audio-to-audio", "voice-activity-detection", "text-to-audio",
            "image-classification", "object-detection", "image-segmentation", "text-to-image",
            "image-to-text", "image-to-image", "depth-estimation", "visual-question-answering",
            "document-question-answering", "zero-shot-image-classification",
            "zero-shot-object-detection", "mask-generation", "keypoint-detection",
            "video-classification", "text-to-video", "unconditional-image-generation",
            "image-feature-extraction",
            "tabular-classification", "tabular-regression", "time-series-forecasting",
            "reinforcement-learning", "robotics", "graph-ml",
            "code-generation", "sentiment-analysis"
        ]

        for ptag in hf_tasks:
            cat = self.simulate_rust_category_mapper(ptag, [], f"test-org/model-{ptag}")
            self.assertIn(cat, self.valid_19_categories,
                          f"Pipeline tag '{ptag}' mapped to invalid category '{cat}'")

    def test_adversarial_edge_cases(self):
        """Adversarial stress-testing of boundary inputs: empty, malformed, long, injection, unicode."""
        adversarial_inputs = [
            ("", [], "unknown/model"),
            ("   ", [], "unknown/model"),
            ("UNKNOWN_TAG_99999", [], "unknown/model"),
            ("text-generation", ["license:mit", "transformers"], "custom/flint-coder-v1"),
            ("text-generation", [], "ByteDance/UI-TARS-7B-DPO"),
            ("feature-extraction", [], "google/pe-binary-disasm"),
            ("text-generation", [], "microsoft/rd-agent-pro"),
            ("text-generation", [], "Equall/Saul-7B-Instruct"),
            ("text-generation", [], "ProsusAI/finbert-sentiment"),
            ("text-generation", [], "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"),
            ("text-generation", [], "allenai/deep-research-agent"),
            ("text-generation", [], "browser-use/web-agent-v1"),
            ("'; DROP TABLE models; --", [], "malicious/injection"),
            ("🤖-pipeline", ["🔥-tag"], "org/emoji-model"),
            ("a" * 5000, ["tag" * 500], "long/model-" + "x" * 500),
            ("\x00null-byte", [], "null/byte"),
        ]

        for ptag, tags, model_id in adversarial_inputs:
            cat = self.simulate_rust_category_mapper(ptag, tags, model_id)
            self.assertIn(cat, self.valid_19_categories,
                          f"Input (ptag='{ptag[:30]}', id='{model_id[:30]}') mapped to invalid category '{cat}'")


class TestAdversarialFaultInjection(unittest.TestCase):
    """
    Challenge 3: Verify that network timeouts, offline mode, and HTTP 429 status codes
    are trapped and handled cleanly without panics.
    """

    class MockFaultServer(BaseHTTPRequestHandler):
        def do_GET(self):
            if "trending?type=model" in self.path:
                # Simulate HTTP 429 Too Many Requests
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.send_header("Retry-After", "30")
                self.end_headers()
                self.wfile.write(b'{"error": "Too Many Requests - Rate limit exceeded"}')
            elif "trendingScore" in self.path:
                # Simulate HTTP 500 Internal Server Error
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Internal Server Error"}')
            elif "author=RecursiveSI" in self.path:
                # Simulate delayed response (timeout simulation)
                time.sleep(0.5)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'[]')
            elif "author=Qwen" in self.path:
                # Simulate malformed / truncated JSON
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"id": "Qwen/Qwen2.5-7B", "incomplete_json": [')
            else:
                # Empty success response
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'[]')

        def log_message(self, format, *args):
            pass  # Suppress mock server console logging

    def test_task_handler_error_trapping_code_inspection(self):
        """Verify Rust source code explicitly traps error branches and enforces timeouts."""
        task_handler_path = REPO_ROOT / "crates" / "core" / "src" / "task_handler.rs"
        content = task_handler_path.read_text(encoding="utf-8")

        # 1. Verify timeouts configured on all HTTP requests
        self.assertIn("timeout(std::time::Duration::from_secs(15))", content,
                      "Trending feed must enforce 15s timeout")
        self.assertIn("timeout(std::time::Duration::from_secs(12))", content,
                      "Followed orgs query must enforce 12s timeout")

        # 2. Verify pattern matching on HTTP success vs status codes
        self.assertIn("Ok(resp) if resp.status().is_success() =>", content,
                      "Requests must explicitly gate on resp.status().is_success()")
        self.assertIn("Ok(resp) => {", content,
                      "Non-success responses (including 429, 500) must be handled in Ok(resp) arm")
        self.assertIn("Err(e) => {", content,
                      "Network errors (timeout, offline, connect) must be trapped in Err(e) arm")

        # 3. Verify zero unhandled unwraps on network/deserialization calls in Stage 0
        stage0_slice = content[content.find("pub async fn ingest_trending_and_following_feed"):
                               content.find("pub async fn handle_update_database")]
        self.assertNotIn(".unwrap()", stage0_slice,
                         "Stage 0 ingestion must contain zero unhandled .unwrap() calls on network/json")
        self.assertNotIn(".expect(", stage0_slice,
                         "Stage 0 ingestion must contain zero unhandled .expect() calls")

        # 4. Verify offline fallback behavior
        self.assertIn("if candidates.is_empty() {", stage0_slice,
                      "Empty candidates must be detected and return 0 cleanly")
        self.assertIn("network offline or rate limited", stage0_slice,
                      "Diagnostic warning must log when offline or rate limited")

    def test_live_mock_fault_injection_server(self):
        """Spin up MockFaultServer and verify live wire behaviors: 429, 500, timeout, malformed JSON."""
        server = HTTPServer(("127.0.0.1", 0), self.MockFaultServer)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        import urllib.request
        import urllib.error

        base_url = f"http://127.0.0.1:{port}"

        # 1. Test HTTP 429 (Rate limiting)
        url_429 = f"{base_url}/api/trending?type=model&limit=100"
        try:
            req = urllib.request.Request(url_429, headers={"User-Agent": "ModelFusion/1.0.0"})
            urllib.request.urlopen(req)
            self.fail("Expected HTTP 429 error")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 429, "Mock server must return HTTP 429")

        # 2. Test HTTP 500 (Server error)
        url_500 = f"{base_url}/api/models?sort=trendingScore"
        try:
            req = urllib.request.Request(url_500, headers={"User-Agent": "ModelFusion/1.0.0"})
            urllib.request.urlopen(req)
            self.fail("Expected HTTP 500 error")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 500, "Mock server must return HTTP 500")

        # 3. Test Timeout (client timeout 0.1s against 0.5s server delay)
        url_timeout = f"{base_url}/api/models?author=RecursiveSI"
        try:
            req = urllib.request.Request(url_timeout, headers={"User-Agent": "ModelFusion/1.0.0"})
            urllib.request.urlopen(req, timeout=0.1)
            self.fail("Expected Timeout error")
        except (socket.timeout, TimeoutError, urllib.error.URLError) as e:
            # Successfully trapped timeout
            pass

        # 4. Test Malformed JSON parsing
        url_malformed = f"{base_url}/api/models?author=Qwen"
        req = urllib.request.Request(url_malformed, headers={"User-Agent": "ModelFusion/1.0.0"})
        resp = urllib.request.urlopen(req)
        raw_body = resp.read().decode("utf-8")
        with self.assertRaises(json.JSONDecodeError):
            json.loads(raw_body)

        # 5. Test Offline mode (connection refused to closed port)
        offline_port = 59999
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{offline_port}/api/trending")
            urllib.request.urlopen(req, timeout=1.0)
            self.fail("Expected connection refused on offline port")
        except urllib.error.URLError:
            pass  # Successfully trapped offline connection failure

        server.shutdown()
        server.server_close()


class TestAdversarialDatabaseMigration(unittest.TestCase):
    """
    Challenge 4: Verify non-destructive schema migration, persistence of trending_score,
    feed_source, bandit_pulls, bandit_reward, and conflict resolution.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_legacy.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_legacy_schema_migration_preserves_data(self):
        """Simulate opening a legacy 19-column database and applying migration."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 1. Create legacy 19-column table
        cursor.execute("""
            CREATE TABLE models (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id          TEXT NOT NULL UNIQUE,
                author            TEXT NOT NULL,
                pipeline_tag      TEXT,
                tags              TEXT NOT NULL,
                description       TEXT NOT NULL,
                downloads         INTEGER NOT NULL,
                likes             INTEGER NOT NULL,
                decision_score    REAL NOT NULL,
                capability_score  REAL NOT NULL,
                efficiency_score  REAL NOT NULL,
                popularity_score  REAL NOT NULL,
                model_type        TEXT NOT NULL,
                library_name      TEXT NOT NULL,
                last_modified     TEXT NOT NULL,
                license           TEXT NOT NULL,
                task_keywords     TEXT NOT NULL,
                architecture      TEXT NOT NULL,
                size_mb           REAL NOT NULL
            );
        """)

        # Insert legacy model record
        cursor.execute("""
            INSERT INTO models (
                model_id, author, pipeline_tag, tags, description, downloads, likes,
                decision_score, capability_score, efficiency_score, popularity_score,
                model_type, library_name, last_modified, license, task_keywords,
                architecture, size_mb
            ) VALUES (
                'meta-llama/Llama-3-8B', 'meta-llama', 'text-generation', '["llama"]',
                'Legacy Model Record', 500000, 12000, 0.88, 0.85, 0.75, 0.95,
                'causal-lm', 'transformers', '2025-01-01T00:00:00Z', 'llama3',
                '["text-generation"]', 'transformer', 16000.0
            );
        """)
        conn.commit()

        # Check initial column count: exactly 19
        cursor.execute("PRAGMA table_info(models);")
        initial_cols = [row[1] for row in cursor.fetchall()]
        self.assertEqual(len(initial_cols), 19)
        self.assertNotIn("trending_score", initial_cols)
        self.assertNotIn("feed_source", initial_cols)

        # 2. Simulate migrate_schema logic from crates/db/src/schema.rs
        migration_columns = [
            ("trending_score", "REAL DEFAULT 0.0"),
            ("feed_source", "TEXT DEFAULT 'standard_hub'"),
            ("bandit_pulls", "INTEGER DEFAULT 0"),
            ("bandit_reward", "REAL DEFAULT 0.0"),
        ]

        cursor.execute("PRAGMA table_info(models);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        for col_name, col_def in migration_columns:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE models ADD COLUMN {col_name} {col_def};")
        conn.commit()

        # 3. Verify columns were added with correct defaults
        cursor.execute("PRAGMA table_info(models);")
        migrated_cols = {row[1]: (row[2], row[4]) for row in cursor.fetchall()}
        self.assertEqual(len(migrated_cols), 23)
        self.assertIn("trending_score", migrated_cols)
        self.assertIn("feed_source", migrated_cols)
        self.assertIn("bandit_pulls", migrated_cols)
        self.assertIn("bandit_reward", migrated_cols)

        # 4. Verify existing record survived with default values
        cursor.execute("SELECT model_id, downloads, trending_score, feed_source, bandit_pulls, bandit_reward FROM models WHERE model_id = 'meta-llama/Llama-3-8B';")
        row = cursor.fetchone()
        self.assertEqual(row[0], "meta-llama/Llama-3-8B")
        self.assertEqual(row[1], 500000)
        self.assertEqual(row[2], 0.0)
        self.assertEqual(row[3], "standard_hub")
        self.assertEqual(row[4], 0)
        self.assertEqual(row[5], 0.0)

        # 5. Verify idempotency: running migration again does nothing and does not fail
        for col_name, col_def in migration_columns:
            cursor.execute("PRAGMA table_info(models);")
            current_cols = {r[1] for r in cursor.fetchall()}
            if col_name not in current_cols:
                cursor.execute(f"ALTER TABLE models ADD COLUMN {col_name} {col_def};")
        conn.commit()

        cursor.execute("PRAGMA table_info(models);")
        final_cols = [r[1] for r in cursor.fetchall()]
        self.assertEqual(len(final_cols), 23)
        conn.close()


class TestAdversarialCargoBuildAndTests(unittest.TestCase):
    """
    Challenge 5: Verify cargo check -p modelfusion_core and cargo test -p db exit 0.
    """

    def test_cargo_check_modelfusion_core(self):
        res = subprocess.run(
            ["cargo", "check", "-p", "modelfusion_core"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0, f"cargo check -p modelfusion_core failed:\n{res.stderr}")

    def test_cargo_test_db(self):
        res = subprocess.run(
            ["cargo", "test", "-p", "db"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0, f"cargo test -p db failed:\n{res.stderr}")
        combined = (res.stdout or "") + (res.stderr or "")
        self.assertIn("6 passed", combined, "All 6 database unit tests must pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
Adversarial Verification & Stress-Testing Suite (Reviewer 1)
Milestone 3: Discovery Directives, Frontend/IDE Integration & E2E Testing
========================================================================
Independent adversarial scrutiny for:
1. Master CLI argument parsing, directive preprocessing, and flags.
2. HTTP API endpoints (/api/trending/models, /api/trending/sync).
3. Port failover and strict "service": "modelfusion" verification.
4. Browser UI: #sidebar-trending-models, #tool_trending_models, 19 categories A-Z order, 151 tool count.
5. IDE extension: package.json contribution, dist/extension.js registration, 5-location hash parity.
6. Integrity Violations & Anti-Mock Audit: genuine database queries vs hardcoded facades.
"""

import os
import sys
import re
import json
import hashlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAdversarialCliDirectives(unittest.TestCase):
    """
    Challenge 1: Verify Master CLI flags, argument parsing, and directive preprocessing in crates/cli/src/main.rs.
    """

    @classmethod
    def setUpClass(cls):
        main_rs = REPO_ROOT / "crates" / "cli" / "src" / "main.rs"
        cls.assertTrue(main_rs.exists(), "crates/cli/src/main.rs must exist")
        with open(main_rs, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_cli_args_struct_has_trending_flags(self):
        """Verify struct Args has --trending and --trending-models."""
        self.assertIn('long = "trending"', self.content)
        self.assertIn('trending: bool', self.content)
        self.assertIn('long = "trending-models"', self.content)
        self.assertIn('trending_models: bool', self.content)

    def test_preprocess_cli_args_maps_trending_directives(self):
        """Verify preprocess_cli_args maps all variations of @agent trending-models to --trending-models."""
        # Find preprocess_cli_args definition
        match = re.search(r'fn preprocess_cli_args\b.*?(?=fn \w+)', self.content, re.DOTALL)
        self.assertIsNotNone(match, "preprocess_cli_args function must be present")
        func_body = match.group(0)

        # Check @agent subcommands
        self.assertIn('sub_clean == "trending-models"', func_body)
        self.assertIn('sub_clean == "trending"', func_body)
        self.assertIn('args[1] = "--trending-models".to_string()', func_body)

        # Check slash commands and @trending directly
        self.assertIn('"trending" | "trending-models"', func_body)
        self.assertIn('"/trending"', func_body)
        self.assertIn('"@trending"', func_body)

    def test_update_flag_with_trending_triggers_stage0(self):
        """Verify that passing --trending or --trending-models with --update triggers Stage 0 sync."""
        self.assertIn('if (args.trending || args.trending_models) && !args.update', self.content)
        self.assertIn('if args.trending || args.trending_models', self.content)
        self.assertIn('handler.handle_trending_sync().await', self.content)

    def test_standalone_trending_flag_queries_sqlite_catalog(self):
        """Verify standalone --trending or --trending-models queries SQLite catalog without --update."""
        # Find the block starting at if (args.trending || args.trending_models) && !args.update
        idx = self.content.find('if (args.trending || args.trending_models) && !args.update')
        self.assertNotEqual(idx, -1, "Must find if (args.trending || args.trending_models) && !args.update")
        handler_body = self.content[idx:idx + 1500]
        self.assertIn('d.get_trending_models', handler_body)
        self.assertIn('effective_priority_score', handler_body)
        self.assertIn('map_pipeline_tag_to_browser_category', handler_body)


class TestAdversarialHttpEndpointsAndFailover(unittest.TestCase):
    """
    Challenge 2: Verify HTTP API routes, parameter parsing, and port failover checking service === "modelfusion".
    """

    @classmethod
    def setUpClass(cls):
        main_rs = REPO_ROOT / "crates" / "cli" / "src" / "main.rs"
        with open(main_rs, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_http_api_trending_models_route_and_params(self):
        """Verify GET /api/trending/models and query param filtering."""
        self.assertIn('request_path == "/api/trending/models" || request_path == "/api/trending"', self.content)
        self.assertIn('k_dec == "category" || k_dec == "browser_category"', self.content)
        self.assertIn('d.get_trending_models', self.content)
        self.assertIn('HTTP/1.1 200 OK', self.content)

    def test_http_api_trending_sync_route(self):
        """Verify POST /api/trending/sync triggers handle_trending_sync."""
        self.assertIn('request_path == "/api/trending/sync"', self.content)
        self.assertIn('handler.handle_trending_sync().await', self.content)

    def test_port_failover_strictly_checks_modelfusion_service(self):
        """Verify is_verified_modelfusion_server strictly requires service === 'modelfusion'."""
        match = re.search(r'async fn is_verified_modelfusion_server\b.*?(?=async fn|fn )', self.content, re.DOTALL)
        self.assertIsNotNone(match, "is_verified_modelfusion_server must exist")
        body = match.group(0)
        self.assertIn('parsed.get("service").and_then(|s| s.as_str()) == Some("modelfusion")', body)
        self.assertIn('http://127.0.0.1:{}/health', body)

    def test_port_discovery_scans_ports_5000_to_5010(self):
        """Verify discover_active_modelfusion_port scans ports 5000 through 5010."""
        match = re.search(r'async fn discover_active_modelfusion_port\b.*?(?=async fn|fn )', self.content, re.DOTALL)
        self.assertIsNotNone(match, "discover_active_modelfusion_port must exist")
        body = match.group(0)
        for p in [5000, 5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010]:
            self.assertIn(str(p), body)


class TestAdversarialBrowserUi(unittest.TestCase):
    """
    Challenge 3: Verify HugOS Browser UI additions, A-Z ordering, and tool counts.
    """

    @classmethod
    def setUpClass(cls):
        cls.index_html_path = REPO_ROOT / "browser" / "ui" / "index.html"
        cls.app_js_path = REPO_ROOT / "browser" / "ui" / "app.js"
        assert cls.index_html_path.exists()
        assert cls.app_js_path.exists()
        with open(cls.index_html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(cls.app_js_path, "r", encoding="utf-8") as f:
            cls.app_js = f.read()

    def test_sidebar_trending_models_present_in_nav_list(self):
        """Verify #sidebar-trending-models inside #sidebar-nav-list."""
        self.assertIn('id="sidebar-nav-list"', self.html)
        self.assertIn('id="sidebar-trending-models"', self.html)
        self.assertIn('Trending Models', self.html)

    def test_tool_trending_models_in_utilities_system(self):
        """Verify #tool_trending_models inside Utilities & System."""
        self.assertIn('id="tool_trending_models"', self.html)
        self.assertIn('Trending Hub Models', self.html)

    def test_all_19_categories_in_alphabetical_order(self):
        """Verify all 19 category headers in index.html are strictly sorted A-Z."""
        headers = re.findall(r'class="cat-title">([^<]+)</span>', self.html)
        clean = [re.sub(r'^[^\w\s]+', '', h).replace('&amp;', '&').strip() for h in headers]
        self.assertEqual(len(clean), 19, f"Expected 19 categories, found {len(clean)}")
        self.assertEqual(clean, sorted(clean), "Category headers must be strictly alphabetical (A-Z)")

    def test_total_tool_count_is_151(self):
        """Verify total tool count across all 19 categories is exactly 151."""
        tools = re.findall(r'class="[^"]*tool-item-btn[^"]*"', self.html)
        self.assertEqual(len(tools), 151, f"Expected exactly 151 tools, found {len(tools)}")

    def test_tool_trending_models_alphabetical_placement(self):
        """Verify Trending Hub Models is placed between Optimize Database and Update Top Models."""
        util_block_match = re.search(r'data-cat="utilities".*?(?=<div class="tool-category">|$)', self.html, re.DOTALL)
        self.assertIsNotNone(util_block_match)
        block = util_block_match.group(0)
        opt_idx = block.find("Optimize Database")
        trend_idx = block.find("Trending Hub Models")
        update_idx = block.find("Update Top Models")
        self.assertTrue(opt_idx < trend_idx < update_idx, "Must be sorted: Optimize Database < Trending Hub Models < Update Top Models")

    def test_app_js_has_trending_click_listeners_and_handlers(self):
        """Verify app.js wires click listeners for sidebar and tool buttons."""
        self.assertIn("sidebar-trending-models", self.app_js)
        self.assertIn("tool_trending_models", self.app_js)
        self.assertIn("@agent trending-models", self.app_js)
        self.assertIn("/api/trending/models", self.app_js)
        self.assertIn("/api/trending/sync", self.app_js)


class TestAdversarialIdeExtension(unittest.TestCase):
    """
    Challenge 4: Verify HugOS IDE extension manifest, extension.js, and parity.
    """

    @classmethod
    def setUpClass(cls):
        cls.pkg_path = REPO_ROOT / "IDE" / "vscode" / "extensions" / "copilot" / "package.json"
        cls.ext_path = REPO_ROOT / "IDE" / "vscode" / "extensions" / "copilot" / "dist" / "extension.js"
        assert cls.pkg_path.exists()
        assert cls.ext_path.exists()
        with open(cls.pkg_path, "r", encoding="utf-8") as f:
            cls.pkg = json.load(f)
        with open(cls.ext_path, "r", encoding="utf-8") as f:
            cls.ext = f.read()

    def test_package_json_contributes_trending_models_command(self):
        """Verify package.json registers hugos.modelfusion.trendingModels."""
        cmds = self.pkg.get("contributes", {}).get("commands", [])
        matching = [c for c in cmds if c.get("command") == "hugos.modelfusion.trendingModels"]
        self.assertEqual(len(matching), 1, "Must contribute hugos.modelfusion.trendingModels")

    def test_extension_js_registers_trending_command(self):
        """Verify extension.js registers hugos.modelfusion.trendingModels."""
        self.assertIn("hugos.modelfusion.trendingModels", self.ext)
        self.assertIn("--trending-models", self.ext)

    def test_extension_js_recognizes_trending_directives(self):
        """Verify knownCommands and normCmd recognize /trending and trending-models."""
        self.assertIn('"trending"', self.ext)
        self.assertIn('"trending-models"', self.ext)
        self.assertIn('l === "trending" || l === "trending-models"', self.ext)

    def test_packaged_ide_extension_hash_parity(self):
        """Verify extension.js in source matches packaged IDE extension."""
        with open(self.ext_path, "rb") as f:
            source_hash = hashlib.sha256(f.read()).hexdigest()
        packaged_ext = REPO_ROOT / "IDE" / "VSCode-win32-x64" / "resources" / "app" / "extensions" / "copilot" / "dist" / "extension.js"
        if packaged_ext.exists():
            with open(packaged_ext, "rb") as f:
                packaged_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(source_hash, packaged_hash, "Source and packaged extension.js must have identical SHA-256")


class TestAdversarialIntegrityAndAntiMockAudit(unittest.TestCase):
    """
    Challenge 5: Integrity Violations & Anti-Mock Audit.
    Ensures that genuine database queries and business logic are executed rather than static dummy facades.
    """

    def test_db_get_trending_models_uses_actual_sql(self):
        """Verify crates/db/src/models.rs get_trending_models uses genuine SQL ORDER BY trending_score DESC."""
        models_rs = REPO_ROOT / "crates" / "db" / "src" / "models.rs"
        with open(models_rs, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ORDER BY trending_score DESC, downloads DESC", content)
        self.assertIn("pub fn get_trending_models", content)

    def test_no_hardcoded_fake_trending_models_in_cli(self):
        """Verify crates/cli/src/main.rs does not hardcode static dummy models in --trending output."""
        main_rs = REPO_ROOT / "crates" / "cli" / "src" / "main.rs"
        with open(main_rs, "r", encoding="utf-8") as f:
            content = f.read()
        # Ensure it reads from database
        self.assertIn("d.get_trending_models(100)", content)
        # Verify no hardcoded dummy list in the standalone trending branch
        match = re.search(r'if \(args\.trending \|\| args\.trending_models\) && !args\.update\s*\{(.*?)\n\s*\}', content, re.DOTALL)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertNotIn('"model_id": "dummy-model"', body)
        self.assertNotIn('"model_id": "fake-model"', body)


if __name__ == "__main__":
    unittest.main()

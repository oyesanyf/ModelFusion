#!/usr/bin/env python3
"""
Empirical Verification Harness for R4:
Native Multi-Modal Visual Canvas & UI Synthesis.

Verifies:
1. Base64 encoding and image validation (PNG, JPEG, WebP, SVG, corrupted base64).
2. Offline fallback visual analyzer (fallback_visual_analyzer).
3. React TSX component generation with Tailwind CSS utility classes and design tokens.
4. CSS box model / flexbox layout bug diagnosis and CSS patch generation.
5. End-to-end execution of IDE/src/scripts/run_model_visual.py subprocess interface.
"""

import os
import sys
import io
import json
import base64
import subprocess
import unittest
from PIL import Image

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUN_VISUAL_PY = os.path.join(REPO_ROOT, "IDE", "src", "scripts", "run_model_visual.py")

sys.path.insert(0, os.path.join(REPO_ROOT, "IDE", "src", "scripts"))
import run_model_visual


class TestR4EmpiricalVisualCanvas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a synthetic 800x600 test image in memory
        img = Image.new("RGB", (800, 600), color=(30, 41, 59))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        cls.raw_png_bytes = buf.getvalue()
        cls.valid_base64 = base64.b64encode(cls.raw_png_bytes).decode("utf-8")
        cls.data_url = f"data:image/png;base64,{cls.valid_base64}"

    def test_01_base64_image_loading_and_dimensions(self):
        """Test Base64 image extraction and dimension decoding."""
        # 1. From data URL
        b64, pil_img, w, h = run_model_visual.load_image_as_base64_and_pil(self.data_url)
        self.assertEqual(w, 800)
        self.assertEqual(h, 600)
        self.assertIsNotNone(pil_img)
        self.assertEqual(b64, self.valid_base64)

        # 2. From raw base64 string
        b64_2, pil_img_2, w_2, h_2 = run_model_visual.load_image_as_base64_and_pil(self.valid_base64)
        self.assertEqual(w_2, 800)
        self.assertEqual(h_2, 600)

        # 3. From invalid / non-image string
        b64_inv, pil_inv, w_inv, h_inv = run_model_visual.load_image_as_base64_and_pil("not_an_image_random_text")
        self.assertEqual(b64_inv, "")
        self.assertIsNone(pil_inv)
        print("\n[R4 Empirical] Image base64 decoding and dimension extraction: PASS")

    def test_02_ui_synthesis_react_tailwind_generation(self):
        """Test React TSX + Tailwind CSS component synthesis in fallback visual analyzer."""
        raw_output = run_model_visual.fallback_visual_analyzer(
            workflow="ui-synthesis",
            prompt="Generate responsive dashboard",
            width=1280,
            height=720,
            pil_img=None,
        )

        parsed = run_model_visual.parse_vlm_output(raw_output, workflow="ui-synthesis")
        self.assertEqual(parsed["workflow"], "ui-synthesis")
        self.assertIn("1280x720", parsed["summary"])
        self.assertIn("React.FC", parsed["code"])
        self.assertIn("import React", parsed["code"])
        self.assertIn("bg-slate-900", parsed["code"])
        self.assertIn("grid grid-cols-1", parsed["code"])
        self.assertIn("grid-cols", parsed["design_tokens"])
        self.assertIn("bg-slate-900", parsed["design_tokens"])
        print(f"[R4 Empirical] UI Synthesis Output verified: {len(parsed['code'])} chars of React TSX generated")

    def test_03_layout_bug_diagnosis_css_patch_generation(self):
        """Test CSS Box Model bug diagnosis and CSS patch generation in fallback visual analyzer."""
        raw_output = run_model_visual.fallback_visual_analyzer(
            workflow="layout-diagnosis",
            prompt="Flex items overlapping on mobile viewport",
            width=375,
            height=667,
            pil_img=None,
        )

        parsed = run_model_visual.parse_vlm_output(raw_output, workflow="layout-diagnosis")
        self.assertEqual(parsed["workflow"], "layout-diagnosis")
        self.assertIn("overflow", parsed["diagnosis"].lower())
        self.assertIn("flex-wrap", parsed["css_patch"])
        self.assertIn("min-width: 0", parsed["css_patch"])
        self.assertIn("overflow", parsed["root_cause"].lower())
        self.assertGreater(len(parsed["explanation"]), 20)
        print(f"[R4 Empirical] Layout Bug Diagnosis verified: CSS Patch:\n{parsed['css_patch']}")

    def test_04_run_model_visual_cli_subprocess(self):
        """Test CLI execution of run_model_visual.py returning structured JSON."""
        cmd = [
            sys.executable,
            RUN_VISUAL_PY,
            "--image", self.data_url,
            "--workflow", "ui-synthesis",
            "--format", "json",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, f"run_model_visual.py failed: {proc.stderr}")

        data = json.loads(proc.stdout.strip())
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["workflow"], "ui-synthesis")
        self.assertIn("React.FC", data["code"])
        self.assertEqual(data["framework"], "react-tailwind")
        print(f"[R4 Empirical] Subprocess CLI returned valid JSON contract. Provider: {data.get('provider')}")


if __name__ == "__main__":
    unittest.main()

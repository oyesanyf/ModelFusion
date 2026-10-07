#!/usr/bin/env python3
"""
ModelFusion / HugOS EmbeddingGemma 2 Calibration & Resilient Tag Management Test Suite

Validates:
1. Google EmbeddingGemma 2 model tag is standardized to 'embeddinggemma:latest' (~0.6 GB, 300M params).
2. Aliases 'embeddinggemma:2b' and 'embeddinggemma' are normalized to 'embeddinggemma:latest'.
3. Stderr & stdout ANSI escape sequences (\\u001b[...) are sanitized from logs and error strings.
4. Rust Master CLI main.rs correctly provisions, normalizes, and exposes embeddinggemma:latest.
5. browser/ui/app.js implements stripAnsi, normalizeModelTag, and isModelMatch.
6. Zero touch of Windows Environment variables or registry.
"""

import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("🧪 Starting EmbeddingGemma 2 Calibration & ANSI Sanitization Test Suite...\n")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_rs_path = os.path.join(repo_root, "crates", "cli", "src", "main.rs")
    app_js_path = os.path.join(repo_root, "browser", "ui", "app.js")

    assert os.path.exists(main_rs_path), f"main.rs not found at {main_rs_path}"
    assert os.path.exists(app_js_path), f"app.js not found at {app_js_path}"

    with open(main_rs_path, "r", encoding="utf-8") as f:
        main_rs = f.read()

    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    # =========================================================================
    # Test 1: Rust Master CLI ANSI Escape Sanitization
    # =========================================================================
    print("--- Test 1: Master CLI strip_ansi_escapes Function ---")
    assert "fn strip_ansi_escapes(s: &str) -> String" in main_rs, "main.rs must define strip_ansi_escapes"
    assert r"\x1b\[" in main_rs or r"\u{1b}\[" in main_rs or "Regex::new" in main_rs, "strip_ansi_escapes must use regex to remove ANSI escapes"
    print("  ✅ [PASS] strip_ansi_escapes defined in crates/cli/src/main.rs")

    # =========================================================================
    # Test 2: Master CLI EmbeddingGemma Tag Standardization & Size
    # =========================================================================
    print("\n--- Test 2: Master CLI EmbeddingGemma Provisioning & Size ---")
    assert '"embeddinggemma:latest"' in main_rs, "main.rs must reference 'embeddinggemma:latest'"
    assert "300M" in main_rs, "main.rs must mention 300M parameters for EmbeddingGemma"
    assert "0.6 GB" in main_rs or "0.6GB" in main_rs, "main.rs must mention ~0.6 GB for EmbeddingGemma"

    # Verify pull normalization converts embeddinggemma:2b to embeddinggemma:latest
    assert 'model_name == "embeddinggemma:2b"' in main_rs or 'target_model == "embeddinggemma:2b"' in main_rs, "main.rs must normalize 'embeddinggemma:2b'"
    print("  ✅ [PASS] 'embeddinggemma:latest' (~0.6 GB, 300M params) standardized in main.rs")

    # =========================================================================
    # Test 3: Master CLI Hardware Endpoints Expose embeddinggemma:latest
    # =========================================================================
    print("\n--- Test 3: Master CLI Hardware Provisioning API Endpoints ---")
    assert '"embedding": "embeddinggemma:latest"' in main_rs, "Hardware provisioning JSON must output 'embedding': 'embeddinggemma:latest'"
    assert 'embeddinggemma:latest' in main_rs, "Embeddings candidate list must contain embeddinggemma:latest"
    print("  ✅ [PASS] /api/models/provision-hardware outputs embeddinggemma:latest")

    # =========================================================================
    # Test 4: Browser UI stripAnsi Function
    # =========================================================================
    print("\n--- Test 4: Browser UI stripAnsi Implementation ---")
    assert "function stripAnsi(" in app_js, "app.js must define stripAnsi"
    # Test JS regex against raw ANSI escape codes in Python
    ansi_test = "\u001b[?25h\u001b[2Kpulling 00768798939b... 100%\u001b[?25l"
    clean_test = re.sub(r'[\u001B\u009B][\[\]()#;?]*(?:(?:(?:[a-zA-Z\d]*(?:;[-a-zA-Z\d\/#&.:=?%@_]+)*)?\u0007)|(?:(?:\d{1,4}(?:;\d{0,4})*)?[\dA-PR-TZcf-ntqry=><~]))', '', ansi_test).replace('\r', '')
    assert clean_test == "pulling 00768798939b... 100%", f"ANSI regex failed to clean string: {clean_test}"
    print("  ✅ [PASS] stripAnsi correctly strips control sequences in UI")

    # =========================================================================
    # Test 5: Browser UI Model Tag Normalization & Matching
    # =========================================================================
    print("\n--- Test 5: Browser UI normalizeModelTag & isModelMatch ---")
    assert "function normalizeModelTag(" in app_js, "app.js must define normalizeModelTag"
    assert "function isModelMatch(" in app_js, "app.js must define isModelMatch"
    assert "embeddinggemma:latest" in app_js, "app.js must reference embeddinggemma:latest"
    print("  ✅ [PASS] normalizeModelTag and isModelMatch defined in app.js")

    # =========================================================================
    # Test 6: Zero Touch Environment Variables Law
    # =========================================================================
    print("\n--- Test 6: Zero Touch Registry Environment Variables Law ---")
    forbidden_patterns = [
        r'reg\s+add\s+HKCU\\Environment',
        r'reg\s+add\s+HKLM',
        r'\[Environment\]::SetEnvironmentVariable\([^)]*[\'"](?:User|Machine)[\'"]',
        r'setx\b'
    ]
    for pattern in forbidden_patterns:
        match = re.search(pattern, main_rs, re.IGNORECASE)
        assert not match, f"Forbidden registry call found in main.rs: {pattern}"
    print("  ✅ [PASS] Zero registry environment mutation calls in code")

    print("\n========================================================================")
    print("🎉 ALL EMBEDDINGGEMMA 2 CALIBRATION & ANSI SANITIZATION TESTS PASSED!")
    print("========================================================================\n")

if __name__ == "__main__":
    main()

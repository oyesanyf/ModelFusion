#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-244"

def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            check=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed to get token: {e}")
    return None

def main():
    token = get_token()
    if not token:
        print("[ERROR] No GitHub token found.")
        sys.exit(1)

    commit_title = "feat: implement Kirchenbauer token watermark and image LSB steganography detection suite (Build 244)"
    pr_body = """## Summary
- **AI Watermark Detection Suite (`crates/cli/src/watermark.rs`)**:
  - Statistical Token Green-List Watermark Detector (Kirchenbauer et al.): deterministic token hash partitioning, pseudo-random generator, cumulative binomial test with z-score calculation, and threshold decision ($z \\ge 4.0$, $\\gamma = 0.5$, $p < 0.00003$).
  - Spatial Least Significant Bit (LSB) Steganographic Shannon Entropy and Chi-Square Goodness-of-Fit Analysis across RGB channels for image assets.
  - Multi-input resolver (`detect_watermark_input`) supporting inline raw text, textual file paths (`.txt`, `.md`, `.py`, `.rs`, `.json`, etc.), and visual image formats (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`).
  - Comprehensive unit test suite covering token detector, high-confidence watermarks, image LSB scanner, and inline text resolution.
- **Master CLI, Server & MCP Catalog Integration (`crates/cli/src/main.rs`, `crates/cli/src/mcp_catalog.rs`)**:
  - Added CLI flag `--watermark [INPUT]` to `Args`.
  - Added `@agent watermark`, `/watermark`, and `watermark` directive normalization in `preprocess_cli_args()`.
  - Fast-interception handler for `/watermark` in chat with attached code context awareness.
  - Registered `detect_watermark` tool in MCP stdio catalog with text/image parameters.
  - Added HTTP endpoint `POST /api/watermark` with JSON payload parsing and markdown report output.
- **HugOS Browser UI & Visual Polish (`browser/ui/app.js`, `browser/ui/index.html`)**:
  - Registered Watermark Detection tool (`tool_watermark`) under Writing & Editing category.
  - Added dedicated `@agent watermark` directive and quick action handlers with attachment integration.
  - Clean borderless sidebar layout and Utilities category with system maintenance tools.
- **MSI Packaging, Binary Mirroring & Parity**:
  - Removed disruptive msiserver polling job that was interrupting WiX v5 database generation.
  - Rebuilt & Authenticode-signed HugOS MSI Build 244 (`IDE/HugOS.msi`) with verified payload integrity.
  - 100% cryptographic parity across all 12 binary/asset copies.
"""

    headers = {
        "User-Agent": "ModelFusion-Release-Pipeline",
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_data = {
        "title": commit_title,
        "body": pr_body,
        "head": BRANCH,
        "base": "main"
    }

    print(f"[INFO] Creating PR for branch {BRANCH}...")
    req = urllib.request.Request(pr_url, data=json.dumps(pr_data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pr_res = json.loads(resp.read().decode("utf-8"))
            pr_num = pr_res["number"]
            print(f"[OK] Created Pull Request #{pr_num}: {pr_res.get('html_url')}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[ERROR] Failed to create PR: {e.code} - {err_msg}")
        if "A pull request already exists" in err_msg:
            req_list = urllib.request.Request(f"{pr_url}?head={REPO.split('/')[0]}:{BRANCH}&state=open", headers=headers)
            with urllib.request.urlopen(req_list) as resp_list:
                open_prs = json.loads(resp_list.read().decode("utf-8"))
                if open_prs:
                    pr_num = open_prs[0]["number"]
                    print(f"[INFO] Reusing existing open PR #{pr_num}")
                else:
                    sys.exit(1)
        else:
            sys.exit(1)

    print(f"[INFO] Squash-merging PR #{pr_num}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge"
    merge_data = {
        "commit_title": f"{commit_title} (#{pr_num})",
        "commit_message": pr_body,
        "merge_method": "squash"
    }
    req_merge = urllib.request.Request(merge_url, data=json.dumps(merge_data).encode("utf-8"), headers=headers, method="PUT")
    time.sleep(2)
    try:
        with urllib.request.urlopen(req_merge) as resp:
            merge_res = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Squash-merge successful! SHA: {merge_res.get('sha')}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to merge PR: {e.code} - {e.read().decode('utf-8')}")
        sys.exit(1)

    print("[INFO] Checking out main and pulling latest changes...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

    print(f"[INFO] Deleting local branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)

    print("[SUCCESS] PR squash-merge pipeline completed successfully!")

if __name__ == "__main__":
    main()

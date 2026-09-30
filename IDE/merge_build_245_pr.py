#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-245"

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

    commit_title = "feat: implement boost under writing, cli flag, mcp and robust watermark detection (Build 245)"
    pr_body = """## Summary
- **Writing & Reasoning Boost (`crates/cli/src/main.rs`, `crates/cli/src/mcp_catalog.rs`)**:
  - Implemented `/boost`, `@agent boost`, and CLI flag `--boost <PROMPT>` for high-compute multi-agent / multi-sample reasoning and prose refinement under Writing.
  - Registered `writing_boost` and `humanize` tools under the `"writing"` category in the MCP catalog.
  - Added MCP stdio handler for `boost` and `writing_boost` tools delegating directly to the CLI reasoning boost pipeline with optional `--ollama` routing.
  - Fixed argument preprocessor combiners in `preprocess_cli_args()` for `--boost`, `--watermark`, and `--humanize`.
- **Watermark Detection Hardening (`crates/cli/src/watermark.rs`, `crates/cli/src/main.rs`)**:
  - Fixed UTF-8 multi-byte character boundary panic in `WatermarkReport::to_markdown()` by implementing `safe_truncate()` using Unicode scalar char boundaries.
  - Fixed non-existent file path false-positive by distinguishing missing files (`.png`, `.jpg`, `.txt`, `.md`, or paths with separators) from inline text prose.
  - Added quotation trimming for single and double-quoted file paths.
  - Optimized grayscale image scanning in `ImageWatermarkScanner` to avoid 3x duplicate sampling across RGB channels.
  - Sanitized Shannon entropy calculation to prevent negative zero (`-0.0`) floating point values.
  - Expanded parameter resolution in `/api/watermark` and MCP `detect_watermark` with fallbacks for `prompt`, `image`, and `file`.
  - Added comprehensive unit tests for UTF-8 truncation, missing files, quoted paths, synthetic LSB anomalies, and grayscale scanning.
- **Packaging & Parity**:
  - Rebuilt and Authenticode-signed HugOS MSI Build 245 (`IDE/HugOS.msi`) with verified payload integrity.
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

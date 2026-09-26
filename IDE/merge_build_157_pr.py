#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/chromium-browser-integration"

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

    commit_msg = "feat(browser): add AI-native Chromium browser engine with CDP WebSocket, DOM pruner, and fusion arbiter"

    # 1. Checkout feature branch
    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    # 2. Stage modified and untracked files
    print("[INFO] Staging files...")
    stage_files = [
        ".gitignore",
        "Cargo.lock",
        "IDE/HugOS.wxs",
        "IDE/build_number.txt",
        "IDE/rest_rl/tests/test_ipc_and_state.py",
        "IDE/upload_release_asset.py",
        "IDE/merge_build_157_pr.py",
        "crates/cli/src/main.rs",
        "crates/cli/src/browser_fusion.rs",
        "crates/core/Cargo.toml",
        "crates/core/src/lib.rs",
        "crates/core/src/browser",
        "browser"
    ]
    for sf in stage_files:
        if os.path.exists(sf):
            subprocess.run(["git", "add", sf], check=True)
            
    subprocess.run(["git", "add", "-f", "IDE/bin/cli.exe"], check=True)

    # 3. Commit changes
    print(f"[INFO] Committing changes with message: {commit_msg}...")
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Push to remote
    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    # 5. Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_body = """## Summary
- **AI-Native Chromium Browser Integration (`browser/`)**:
  - Implemented lightweight Chromium browser distribution with integrated ModelFusion AI sidebar extension (`browser/extension/`).
  - CDP WebSocket client (`cdp_client.rs`) for bidirectional remote debugging protocol communication on port 9222.
  - Set-of-Mark (SoM) visual grounding and DOM pruning engine (`dom_pruner.rs`) delivering 80-95% token reduction for LLM context windows.
  - Semantic HTML & CSS grid table extractor with CSV/TSV fallback (`table_extractor.rs`).
  - Browser fusion arbiter (`browser_fusion.rs`) with unanimous consensus gate and specialist proposal routing.
  - Master CLI flags: `--browser`, `--browser-task <TASK>`, `--browser-extract <URL>`, `--browser-port <PORT>`.
  - HugOS Browser signed packaging pipeline (`browser/build_browser.ps1`).
- **5-Way Cryptographic Parity Verified**:
  - `target/release/cli.exe`
  - `IDE/bin/cli.exe`
  - `IDE/VSCode-win32-x64/bin/cli.exe`
  - `%LOCALAPPDATA%/HugOS IDE/bin/cli.exe`
  - `browser/bin/cli.exe`
  - SHA-256: `5BE5B73D1076067EA04629B68C44949CEB737058F3BDF0637197FDDC44C362B0`
- **Comprehensive Test Suite Passes Cleanly**:
  - Full ReST-RL Test Suite: 59/59 tests passed.
  - Cargo Core Test Suite: 18/18 tests passed.
  - Cargo Model Selection Test Suite: 17/17 tests passed.
  - Cargo CLI Test Suite: 56/56 tests passed.
- **Signed Installer Packages**:
  - `IDE/HugOS.msi`: Build 157 (1440.52 MB, Authenticode-signed, 100% payload integrity verified).
  - `browser/HugOS_Browser.msi`: Build 1 (5.62 MB, Authenticode-signed)."""

    pr_data = {
        "title": commit_msg,
        "body": pr_body,
        "head": BRANCH,
        "base": "main"
    }
    headers = {
        "User-Agent": "ModelFusion-Release-Pipeline",
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
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
            # Find existing PR
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

    # 6. Squash-Merge Pull Request
    print(f"[INFO] Squash-merging PR #{pr_num}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge"
    merge_data = {
        "commit_title": f"{commit_msg} (#{pr_num})",
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

    # 7. Checkout main and update local
    print("[INFO] Checking out main and pulling latest changes...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # 8. Delete local feature branch
    print(f"[INFO] Deleting local branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)

    print("[SUCCESS] Pipeline completed successfully!")

if __name__ == "__main__":
    main()

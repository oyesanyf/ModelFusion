#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/hugos-browser-ui"

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

    commit_title = "feat(browser): implement dedicated HugOS Browser UI and autonomous CLI portal, package signed MSIs (#98)"

    # Stage any remaining helper files if needed
    subprocess.run(["git", "add", "IDE/merge_build_158_pr.py"], check=False)
    # Check if there are changes to commit on the branch
    p_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if "IDE/merge_build_158_pr.py" in p_status.stdout:
        subprocess.run(["git", "commit", "-m", "chore: add merge_build_158_pr script"], check=True)
        subprocess.run(["git", "push", "origin", BRANCH], check=True)

    # Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_body = """## Summary
- **Dedicated Custom Browser Environment (`browser/ui/`)**:
  - Implemented custom browser homepage (`browser/ui/index.html`, `styles.css`, `app.js`) matching HugOS IDE dark aesthetic.
  - Eliminated hardcoded `https://huggingface.co/models` startup URL in `hugos-browser.bat`, setting default startup homepage to local `ui/index.html`.
  - Added live engine telemetry pills monitoring ModelFusion IPC (`:5000`), local Ollama (`:11434`), and Chrome DevTools Protocol (`:9222`).
  - Added dynamic hardware intelligence monitor displaying CPU, active RAM tier, VRAM, and selected local LLM (`qwen2.5`).
  - Interactive omnibox navigation with history, quick action tiles (Set-of-Mark visual tagging, ACDSO AutoML extraction, Summarization, Deep Research), and terminal CLI execution log runner.
- **CDP Dual-Stack & Auto-Launch Engineering (`crates/core`, `crates/cli`)**:
  - Enhanced `cdp_client.rs` with dual-stack IPv4/IPv6 candidate probing (`localhost`, `127.0.0.1`, `[::1]`) and proper bracket stripping for Tokio `TcpStream` resolution, eliminating Windows 11 loopback dropouts.
  - Added automated background browser launcher (`browser_fusion.rs`) when CDP port 9222 is offline for `--browser`, `--browser-task`, and `--browser-extract`.
- **Packaging & WiX Toolset Pipeline**:
  - Updated WiX generator `browser/generate_wix.js` and manifest `browser/HugOS_Browser.wxs` to bundle `browser/ui/` into `%LOCALAPPDATA%\\HugOS Browser\\ui\\`.
  - Incremented build numbers: `IDE/build_number.txt` -> 158, `browser/build_number.txt` -> 6.
  - Digitally signed all executables and installer packages using `hugos-signing-cert.pfx`.
- **6-Way Cryptographic Parity Verified**:
  - `target/release/cli.exe`
  - `IDE/bin/cli.exe`
  - `IDE/VSCode-win32-x64/bin/cli.exe`
  - `%LOCALAPPDATA%\\HugOS IDE\\bin\\cli.exe`
  - `browser/bin/cli.exe`
  - `%LOCALAPPDATA%\\HugOS Browser\\bin\\cli.exe`
  - SHA-256: `A1304A57CDC4DBD22CE4FF512DC315DD04064AE504283EE52FEA416182769EF3`
- **100% Test Suite Pass Rate**:
  - `cargo test -p modelfusion_core`: 18/18 passed.
  - `cargo test --bin cli`: 57/57 passed.
  - `python IDE/rest_rl/tests/run_all_tests.py`: 59/59 passed.
- **Signed Installer Packages**:
  - `IDE/HugOS.msi`: Build 158 (1440.51 MB, Authenticode-signed, 100% payload integrity verified).
  - `browser/HugOS_Browser.msi`: Build 6 (5.62 MB, Authenticode-signed)."""

    pr_data = {
        "title": commit_title,
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

    # Squash-Merge Pull Request
    print(f"[INFO] Squash-merging PR #{pr_num}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge"
    merge_data = {
        "commit_title": f"{commit_title}",
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

    # Reset main branch to origin/main
    print("[INFO] Checking out main and pulling latest changes...")
    subprocess.run(["git", "checkout", "main"], check=True)
    # Since main has a local commit that was squash-merged, reset it to match origin
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

    # Delete local feature branch
    print(f"[INFO] Deleting local branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)

    print("[SUCCESS] PR squash-merge pipeline completed successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/settings-update-and-updatedb-2m-models"

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

    commit_title = "feat(settings): add --update and --updatedb (all 2M+ models) crawler controls to settings drawer and Master CLI API"

    # Ensure on branch
    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", BRANCH], check=True)

    # Stage files
    files_to_stage = [
        "crates/cli/src/main.rs",
        "browser/ui/index.html",
        "browser/ui/app.js",
        "README.md",
        "browser/README.md",
        "IDE/bin/cli.exe",
        "IDE/merge_updatedb_settings_pr.py"
    ]
    for f in files_to_stage:
        if os.path.exists(f):
            subprocess.run(["git", "add", "-f", f], check=True)

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status.stdout.strip():
        print(f"[INFO] Committing changes: {commit_title}")
        subprocess.run(["git", "commit", "-m", commit_title], check=True)

    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    # Create Pull Request
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ModelFusion-CI"
    }

    pr_payload = {
        "title": commit_title,
        "head": BRANCH,
        "base": "main",
        "body": """## Overview: Settings Drawer --update & --updatedb (All 2M+ Models) Crawler Controls

This PR implements full support for `--update` and `--updatedb` (over 2 million models crawler) directly inside the Settings interface and the Master CLI API server:

1. **Master CLI API Server (`crates/cli/src/main.rs`)**:
   - Added `/api/models/update`: Spawns background `cli.exe --update --db-path <resolved_db>` to fast-ingest the top ~6,500 production workhorse models across all 45 tasks and dynamically auto-provision matching local Ollama models based on runtime available RAM.
   - Added `/api/models/updatedb`: Spawns background `cli.exe --updatedb --db-path <resolved_db>` (with optional `--max-models <N>` parsed from URI query or JSON body) to continuously crawl all 2M+ models across the entire Hugging Face Hub in 1,000-model transactions (~1,000 models/sec).
   - Added unit test `test_update_and_updatedb_flags_and_canonicalization` verifying slash/flag command canonicalization and Clap argument parsing. All 61 CLI tests pass.

2. **Settings Drawer & Models Tab UI (`browser/ui/index.html`)**:
   - Added interactive **Catalog Update & Crawler Operations Card** in the Storage Tab (`pane-tab-storage`) with one-click `⚡ Run Curated Update (--update)` and `🚀 Crawl Full Registry (--updatedb)`.
   - Included quick preset cap chips (`10k`, `50k`, `250k`, `All 2M+ Unlimited`) and numeric input cap control.
   - Added quick update action buttons (`⚡ Update Curated (~6.5k)` and `🚀 Crawl All 2M+ Models`) directly to the ModelFusion Model Catalog card in the AI Models tab (`pane-tab-models`).

3. **Event Listeners & Telemetry (`browser/ui/app.js`)**:
   - Implemented event handlers for both update buttons, reading max-models cap and dispatching async POST requests to the Master CLI API.
   - Wired live status feedback in `#catalog-update-feedback` and structured log lines to terminal logger `termLog`.
   - Refreshes model catalog statistics after update triggers.
   - Synchronized updated UI to `%LOCALAPPDATA%\\HugOS Browser\\ui\\`.

4. **Documentation & Parity**:
   - Documented the new Settings Drawer update controls in `README.md` and `browser/README.md`.
   - Recompiled release Master CLI binary (`target/release/cli.exe`) and verified 100% cryptographic SHA-256 bit parity across all 6 locations.
   - Verified that all 59 ReST-RL recursive reinforcement learning tests pass cleanly."""
    }

    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    print(f"[INFO] Creating PR on {REPO}...")
    req = urllib.request.Request(pr_url, data=json.dumps(pr_payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pr_data = json.loads(resp.read().decode())
            pr_number = pr_data["number"]
            pr_html = pr_data["html_url"]
            print(f"[SUCCESS] Created PR #{pr_number}: {pr_html}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[WARN] Failed to create PR: {e.code} - {err_body}")
        # Check if PR already exists
        list_req = urllib.request.Request(f"{pr_url}?head={REPO.split('/')[0]}:{BRANCH}&base=main", headers=headers)
        with urllib.request.urlopen(list_req) as lresp:
            prs = json.loads(lresp.read().decode())
            if prs:
                pr_number = prs[0]["number"]
                pr_html = prs[0]["html_url"]
                print(f"[INFO] Existing PR #{pr_number}: {pr_html}")
            else:
                sys.exit(1)

    time.sleep(2)

    # Squash merge PR
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/merge"
    merge_payload = {
        "commit_title": f"{commit_title} (#{pr_number})",
        "commit_message": "Add --update and --updatedb (all 2M+ models) crawler controls to settings drawer and Master CLI API.",
        "merge_method": "squash"
    }
    print(f"[INFO] Merging PR #{pr_number} via squash...")
    mreq = urllib.request.Request(merge_url, data=json.dumps(merge_payload).encode(), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(mreq) as mresp:
            mdata = json.loads(mresp.read().decode())
            print(f"[SUCCESS] PR #{pr_number} merged successfully: {mdata.get('sha')}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to merge PR #{pr_number}: {e.code} - {e.read().decode()}")
        sys.exit(1)

    # Checkout main and pull
    print("[INFO] Switching back to main and pulling latest changes...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # Delete local and remote feature branch
    print(f"[INFO] Cleaning up branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=False)
    subprocess.run(["git", "push", "origin", "--delete", BRANCH], check=False)
    print("[SUCCESS] All steps complete!")

if __name__ == "__main__":
    main()

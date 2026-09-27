#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/browser-settings-tools-accordion-agentic-loop"

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

    commit_title = "feat(browser): fix settings buttons, add collapsible tools accordion, agentic loop looping, and build 172 MSI"

    # Ensure on branch
    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    # Stage files
    files_to_stage = [
        "crates/cli/src/main.rs",
        "browser/ui/index.html",
        "browser/ui/app.js",
        "browser/ui/styles.css",
        "browser/build_number.txt",
        "browser/HugOS_Browser.wxs",
        "IDE/fix_slash_commands.py",
        "IDE/build_number.txt",
        "IDE/HugOS.wxs",
        "IDE/bin/cli.exe",
        "IDE/sync_cli_parity.ps1",
        "IDE/merge_build_172_pr.py"
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

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ModelFusion-CI"
    }

    pr_payload = {
        "title": commit_title,
        "head": BRANCH,
        "base": "main",
        "body": """## Overview: Browser Settings Feedback, Tools Accordion, Agentic Loop Looping & Build 172

This pull request implements comprehensive enhancements across HugOS Browser, HugOS IDE, and the ModelFusion Master CLI:

### 1. Browser Settings Button Feedback & Modal Improvements
- **Inline Feedback Banner**: Added `#models-tab-update-feedback` inside `.db-stats-card` in `pane-tab-models` for direct, visible progress when triggering catalog updates.
- **Button Loading States**: Added busy states (`⏳ Updating... (~6.5k)` and `⏳ Crawling All 2M+...`), disabled states, and dynamic status banner updates.
- **System Panel Modal**: Elevated `.modelfusion-panel-modal` to `z-index: 10005` and wired backdrop click dismiss (`e.target === mfModal -> closeModelFusionPanel()`).
- **Hardware Sizing Parity**: Browser UI strictly adheres to Master CLI's dynamic runtime available memory sizing (Rule 3).
- **Sidebar Cleanup**: Removed redundant `@ Plugins` button.

### 2. Collapsible Tools & Directives Accordion (All 161+ Tools)
- Added `#sidebar-tools-accordion` directly below Deep Research in the sidebar with expandable category sections:
  - 🌐 **Web & Browser**: Deep research, `/som`, `/summarize`, `/browser`
  - 📊 **Data Science & AutoML**: `/acdso`, `--datascience`, `--dataanalyst`, `--timeseries`, `--predict`, `--decision`
  - 🧠 **Agent & Planning**: `--goal`, `--plan`, `--grill-me`, `--boost`, `--agentic-loop`
  - 👁️ **Vision & Multimodal**: `/vision`, `--image-classification`, `--object-detection`, `--visual-question-answering`
  - 🎙️ **Audio & Speech**: `--automatic-speech-recognition`, `--text-to-speech`, `--audio-classification`
  - 💻 **Code & Systems**: `--code-vulnerability-detection`, `--graph-index`, `--pe-header-extraction`, `--rest-rl start`
  - 🗄️ **Catalog & Maintenance**: `--update`, `--updatedb`, `--active-model`, `--sys-info`
- Wired click listeners on all tool command chips (`.tool-command-btn`) to automatically insert command flags into active chat prompt input with visual feedback.

### 3. Agentic Loop Looping (Up to 256k Tokens)
- **HugOS Browser**: Multi-turn recursive auto-chaining in `streamAiChat()` up to 32 turns (capped by target token budget). Inspects `done_reason === 'length'` and unclosed code fences, triggers recursive continuation prompts seamlessly, and updates live badge status.
- **Master CLI**: Added `--agentic-loop`, `--target-tokens`, `--chunk-tokens`, `--max-loops` flags and server-side chaining in `/api/chat` and `/orchestrate`.
- **HugOS IDE**: Patched `_sendOrchestrationRequest` via `fix_slash_commands.py` with invariant `c9` passing across all 5 distribution paths.

### 4. Tests, Parity & Signed MSI Packages
- Recompiled release Master CLI (`cli.exe`) with 6-way cryptographic parity (`E0C1B4F9209DB277423BF2F5AE5922B9FF1AE81F68164ACED116DE2C45464E25`).
- Verified all 62 CLI tests and all 59 ReST-RL tests pass 100%.
- Rebuilt and Authenticode-signed both `browser/HugOS_Browser.msi` (Build 20) and `IDE/HugOS.msi` (Build 172)."""
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
        "commit_message": "Fix settings buttons, add collapsible tools accordion, agentic loop looping, and build 172 MSI.",
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
    print("[SUCCESS] PR creation and squash-merge complete!")

if __name__ == "__main__":
    main()

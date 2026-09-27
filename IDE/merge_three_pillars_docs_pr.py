#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "docs/three-pillars-cli-ide-browser"

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

    commit_title = "docs: prominently feature the Three Pillars (CLI, IDE, Browser) in README, expand browser architecture, and document consensus panel sizing"

    # Create and checkout branch
    print(f"[INFO] Creating/switching to branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    # Stage files
    files_to_stage = [
        "README.md",
        "browser/README.md",
        "docs/HUGOS_IDE_GUIDE.md",
        "IDE/README.md",
        "IDE/merge_three_pillars_docs_pr.py"
    ]
    for f in files_to_stage:
        if os.path.exists(f):
            subprocess.run(["git", "add", "-f", f], check=True)

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("[INFO] Working tree clean, nothing to commit.")
        sys.exit(0)

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
        "body": """## Overview: The Three Pillars of ModelFusion

This PR updates `README.md` and related technical guides to prominently showcase ModelFusion's Three Pillars right at the top:
1. **Master CLI (`cli.exe`)**: Headless & Embedded Engine with 174 capability flags, dynamic RAM sizing, 2M+ model catalog crawler (`--updatedb`), ACDSO 5-objective Pareto AutoML, and MCP server.
2. **HugOS IDE (`HugOS.exe`)**: AI-Native Development Environment built on Code-OSS, with sub-8ms ReST-RL preemption via Windows Job Objects, in-memory virtual diffs (`restrl-diff://`), and native chat.
3. **HugOS Browser (`hugos-browser.bat` / `--browser`)**: AI-Native Chromium Web Operating System with Set-of-Mark (SoM) visual grounding, 90% token-pruned DOM filter, RFC-4180 table extraction into ACDSO, 12-category settings drawer, and ChatGPT canvas/ergonomic parity.

### Technical & Architectural Additions
- **Three Pillars & Parallel Quickstarts**: Prominent comparison matrix, architecture flowchart, and direct CLI / IDE / Browser quickstart snippets at the top of `README.md`.
- **Browser Consensus Panel Sizing (`--fusion-models`)**: Documented multi-model consensus deliberation, RAM-driven auto-sizing, and arbitration gates (dominant winner, unanimous agreement, reasoning synthesis).
- **Model Catalog Transparency**: Detailed contrast between `--update` (~6,500 curated workhorses) and `--updatedb` (1.27M+ registry crawler), offline fallback invariants (6,438 models baseline), and task pruning.
- **Companion AI Web Documentation**: Synchronized across `browser/README.md`, `IDE/README.md`, and `docs/HUGOS_IDE_GUIDE.md`."""
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
        "commit_message": "Feature the Three Pillars (CLI, IDE, Browser) prominently in README, expand browser architecture, and document consensus panel sizing.",
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

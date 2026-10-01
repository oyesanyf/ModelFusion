#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-249"

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

    commit_title = "fix(browser): eliminate TDZ ReferenceError in badge sync, expand capabilities to 175+, and add CLI aliases"
    commit_body = (
        "- Resolved fatal Temporal Dead Zone (TDZ) ReferenceError in browser/ui/app.js by hoisting AGENT_COMMANDS definition before updateToolsHeaderBadge() invocation.\n"
        "- Expanded Agent Capabilities badge in index.html, app.js, and styles.css to 175+ with dynamic MCP tools synchronization and minimum threshold protection.\n"
        "- Registered visible aliases (--computer_use, --ui-tars) and short flag (-t for --to) in struct Args and preprocess_cli_args() with query/prompt content fallbacks.\n"
        "- Added SUITE 11 in scratch/test_comprehensive_verification.js validating 100% elimination of legacy 161, TDZ-free badge sync, and computer use integration.\n"
        "- Rebuilt release cli.exe and synchronized 12-way distribution parity via scripts/mirror_all.py.\n"
        "- Built, validated, and Authenticode-signed HugOS.msi (Build 249)."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    files_to_stage = [
        "Cargo.lock",
        "IDE/HugOS.wxs",
        "IDE/build_number.txt",
        "IDE/bin/cli.exe",
        "IDE/bin/cliide.exe",
        "browser/bin/cli.exe",
        "browser/bin/clibrowser.exe",
        "browser/ui/app.js",
        "browser/ui/styles.css",
        "browser/ui/index.html",
        "crates/cli/src/main.rs",
        "crates/cli/src/mcp_catalog.rs",
        "crates/core/Cargo.toml",
        "crates/core/src/browser/mod.rs",
        "crates/core/src/browser/computer_use.rs",
        "crates/core/src/lib.rs",
        "scratch/test_comprehensive_verification.js",
        "IDE/merge_build_249_pr.py",
    ]

    print("[INFO] Staging files...")
    for f in files_to_stage:
        if os.path.exists(f):
            subprocess.run(["git", "add", "-f", f], check=True)

    status_p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if not status_p.stdout.strip():
        print("[INFO] Working tree clean. Proceeding to PR check...")
    else:
        print("[INFO] Committing changes...")
        subprocess.run(["git", "commit", "-m", commit_title, "-m", commit_body], check=True)

    print(f"[INFO] Pushing {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    print("[INFO] Creating Pull Request...")
    pr_data = {
        "title": commit_title,
        "head": BRANCH,
        "base": "main",
        "body": commit_body
    }
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "ModelFusion-Release-Pipeline"
        },
        data=json.dumps(pr_data).encode("utf-8"),
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            pr_resp = json.loads(resp.read().decode())
            pr_num = pr_resp["number"]
            pr_url = pr_resp["html_url"]
            print(f"[OK] Pull Request created: #{pr_num} ({pr_url})")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[WARN] Failed to create PR: {e} - {err_body}")
        if "A pull request already exists" in err_body:
            list_req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/pulls?head={REPO.split('/')[0]}:{BRANCH}&state=open",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ModelFusion-Release-Pipeline"
                }
            )
            with urllib.request.urlopen(list_req) as l_resp:
                prs = json.loads(l_resp.read().decode())
                if prs:
                    pr_num = prs[0]["number"]
                    pr_url = prs[0]["html_url"]
                    print(f"[INFO] Reusing existing PR: #{pr_num} ({pr_url})")
                else:
                    sys.exit(1)
        else:
            sys.exit(1)

    time.sleep(2)
    print(f"[INFO] Squash-merging PR #{pr_num} into main...")
    merge_data = {
        "commit_title": f"{commit_title} (#{pr_num})",
        "commit_message": commit_body,
        "merge_method": "squash"
    }
    merge_req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "ModelFusion-Release-Pipeline"
        },
        data=json.dumps(merge_data).encode("utf-8"),
        method="PUT"
    )

    with urllib.request.urlopen(merge_req) as resp:
        merge_resp = json.loads(resp.read().decode())
        sha = merge_resp.get("sha", "UNKNOWN")
        print(f"[SUCCESS] Merged PR #{pr_num} successfully! Merge commit: {sha}")

    print("[INFO] Returning to main and pulling latest...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)
    print("[SUCCESS] Pipeline completed cleanly!")

if __name__ == "__main__":
    main()

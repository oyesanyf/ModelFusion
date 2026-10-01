#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-254"

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

    commit_title = "feat(chat): hybrid intent & structural sizing engine, page/chapter regex detection, and Build 254 MSI"
    commit_body = (
        "- Implemented fast hybrid intent detector (detectChatIntention, parseRegexIntention) in browser/ui/app.js.\n"
        "- Added regex recognition for page and chapter directives (/\\b(\\d+)\\s*(?:page|chapter|section)\\b/i) and conversational patterns.\n"
        "- Added lightweight LLM intent classifier helper with format: json, max_tokens: 64, low temp, 1.8s timeout fallback, and memory caching.\n"
        "- Wired detected intentions into dynamic context window sizing (up to 32768/65536), output token limits (up to 16384), and structural multi-paragraph page directives.\n"
        "- Added comprehensive test_hybrid_intent_engine.js and verified all 5 test suites pass.\n"
        "- Synchronized 12-way distribution parity via mirror_all.py and ensured port 5000 daemon health.\n"
        "- Built and Authenticode-signed HugOS.msi installer (Build 254)."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    files_to_stage = [
        "IDE/HugOS.wxs",
        "IDE/build_number.txt",
        "IDE/build_msi.ps1",
        "IDE/bin/cli.exe",
        "IDE/bin/cliide.exe",
        "browser/bin/cli.exe",
        "browser/bin/clibrowser.exe",
        "browser/ui/app.js",
        "tests/test_continue_and_badge.js",
        "tests/test_hybrid_intent_engine.js",
        "tests/test_natural_human_engine.js",
        "tests/test_qa_routing_and_boost.js",
        "IDE/merge_build_254_pr.py",
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

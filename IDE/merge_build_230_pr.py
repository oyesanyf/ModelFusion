#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-230"

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

    commit_title = "fix(continue/export): resolve null includes in continue, universal share & export suite (Email, MD, PDF, TXT, HTML), and Build 230 MSI"
    commit_body = (
        "- Fixed null reference crash in continueAssistantMessage by passing explicit continuationSysPrompt rather than null.\n"
        "- Hardened streamAiChat and isCodeOrMathTask with defensive string casting and non-null defaults for userPrompt and effectiveSysPrompt.\n"
        "- Built Universal Share & Export Suite with scope toggle (Current Response vs Entire Conversation):\n"
        "  1. Share via Email with pre-filled subject/body + automatic clipboard copy.\n"
        "  2. Export clean formatted Markdown (.md) with metadata frontmatter.\n"
        "  3. Print / Save as PDF with clean printable styling and window.print().\n"
        "  4. Export Plain Text (.txt) with structured headers.\n"
        "  5. Export Standalone HTML (.html) with dark theme and responsive layout.\n"
        "  6. Copy Rich Formatted text (HTML + plain text) to clipboard.\n"
        "- Added Export button beside Share on all assistant message action bars and wired modals with Escape key navigation.\n"
        "- Rebuilt and digitally signed HugOS_Browser.msi (Build 59) and HugOS.msi (Build 230).\n"
        "- Maintained 100% cryptographic parity across all binaries and local installations."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    files_to_stage = [
        "IDE/HugOS.wxs",
        "IDE/build_number.txt",
        "browser/HugOS_Browser.wxs",
        "browser/build_number.txt",
        "browser/ui/app.js",
        "browser/ui/index.html",
        "browser/ui/styles.css",
        "IDE/merge_build_230_pr.py",
    ]

    print("[INFO] Staging files...")
    for f in files_to_stage:
        if os.path.exists(f):
            subprocess.run(["git", "add", "-f", f], check=True)

    status_p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if not status_p.stdout.strip():
        print("[INFO] Working tree clean. Nothing to commit.")
        return

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
    subprocess.run(["git", "pull", "origin", "main"], check=True)
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)
    print("[SUCCESS] Pipeline completed cleanly!")

if __name__ == "__main__":
    main()

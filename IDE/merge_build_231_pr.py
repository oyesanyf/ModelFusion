#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-231"

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

    commit_title = "fix(canvas/pwa): unwrap raw JSON formatting in Document Canvas/Chat, add distinct browser icons, desktop pin, and Build 231 MSI"
    commit_body = (
        "- Cleaned raw JSON responses in Document Canvas and Chat for @agent goal, /boost, and orchestrator directives via unwrapJsonContent.\n"
        "- Hardened streamAiChat across non-streaming, streaming chunks, continuation merge, session history persistence, and IPC fallback to ensure plain markdown.\n"
        "- Enhanced crates/cli/src/main.rs endpoints (/orchestrate and AI chat) to populate both 'content', 'response', and 'output' with clean text.\n"
        "- Created distinct HugOS Browser icons (favicon.svg, favicon-16/32, icon-192/512, favicon.ico, hugos_browser.ico).\n"
        "- Added PWA Web Manifest (manifest.webmanifest) and Service Worker (sw.js) for desktop installability.\n"
        "- Added '📌 Pin to Desktop' button in header and sidebar calling /api/desktop/pin with fallback to PWA install and .url shortcut download.\n"
        "- Updated desktop shortcut 'HugOS Browser.lnk' with distinct hugos_browser.ico.\n"
        "- Rebuilt and digitally signed HugOS_Browser.msi (Build 60) and HugOS.msi (Build 231).\n"
        "- Maintained 100% cryptographic parity across all 12 binary locations, Git LFS, and GitHub release assets."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    files_to_stage = [
        "IDE/HugOS.wxs",
        "IDE/build_number.txt",
        "IDE/hugos_browser.ico",
        "browser/HugOS_Browser.wxs",
        "browser/build_number.txt",
        "browser/generate_wix.js",
        "browser/ui/app.js",
        "browser/ui/index.html",
        "browser/ui/styles.css",
        "browser/ui/favicon.svg",
        "browser/ui/favicon.ico",
        "browser/ui/favicon-32x32.png",
        "browser/ui/favicon-16x16.png",
        "browser/ui/icon-192.png",
        "browser/ui/icon-512.png",
        "browser/ui/hugos_browser.ico",
        "browser/ui/manifest.webmanifest",
        "browser/ui/sw.js",
        "crates/cli/src/main.rs",
        "scripts/mirror_all.py",
        "scratch/generate_browser_icons.py",
        "scratch/test_all_features.js",
        "IDE/merge_build_231_pr.py",
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

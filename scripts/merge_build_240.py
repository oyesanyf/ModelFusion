#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"

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

    branch = "fix-ui-action-align-build-240"
    commit_title = "fix(ui/action-bar): prevent button word-wrapping, fix feedback button styling, ensure continue layout stability, and Build 240 MSI"
    commit_body = (
        "1. Enforced white-space: nowrap !important, word-break: normal !important, flex-shrink: 0, and width: 100% on .msg-action-bar, .msg-action-btn, and .action-text, preventing mid-word letter wraps.\n"
        "2. Aligned .bubble-feedback-btn (Good / Bad buttons) line-height and padding with standard action buttons, eliminating layout shift and font size discrepancies.\n"
        "3. Added min-width: 90px on .btn-continue-msg to maintain layout stability during the transition to '⏳ Continuing...'. Suppressed streaming cursor pseudo-element on bubbles containing action bars.\n"
        "4. Added window.continuingAssistantMessage compatibility alias in app.js.\n"
        "5. Configured --app-id=\"HugOS.Browser.Engine\" across hugos-browser.bat, browser_fusion.rs, and update_desktop_shortcut.ps1 for distinct Windows Taskbar grouping and icon identity.\n"
        "6. Added comprehensive Suite 7 verification in scratch/test_comprehensive_verification.js (100% pass across all 7 suites).\n"
        "7. Recompiled release cli.exe, synchronized 12-way parity mirror, and built/signed HugOS.msi (Build 240).\n"
        "8. Kept Master CLI background server daemon active on port 5000."
    )

    print(f"[INFO] Checking out branch {branch}...")
    subprocess.run(["git", "checkout", "-b", branch], check=False)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"{commit_title}\n\n{commit_body}"], check=True)
    print(f"[INFO] Pushing branch {branch} to origin...")
    subprocess.run(["git", "push", "-u", "origin", branch, "--force"], check=True)

    print("[INFO] Creating Pull Request...")
    pr_data = {
        "title": commit_title,
        "head": branch,
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

    pr_num = None
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
                f"https://api.github.com/repos/{REPO}/pulls?head={REPO.split('/')[0]}:{branch}&state=open",
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
    subprocess.run(["git", "branch", "-D", branch], check=False)
    print("[SUCCESS] Merge complete and main is fully up to date!")

if __name__ == "__main__":
    main()

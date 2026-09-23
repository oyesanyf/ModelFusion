#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json

REPO = "oyesanyf/ModelFusion"
BRANCH = "fix/cli-boost-optimize-build-145"

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

    # 1. Checkout new branch
    print(f"[INFO] Creating and checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-b", BRANCH], check=True)

    # 2. Stage and commit
    print("[INFO] Staging all modified files...")
    subprocess.run(["git", "add", "-A"], check=True)

    commit_msg = "fix(cli): optimize attachment routing, dynamic ollama flag, package signed MSI 145 (#85)"
    print(f"[INFO] Committing: {commit_msg}...")
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 3. Push to remote
    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH], check=True)

    # 4. Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_data = {
        "title": "fix(cli): optimize attachment routing, dynamic ollama flag, package signed MSI 145",
        "body": "## Summary\n- Optimize attachment routing to resolve attached files on disk and pass `--file`\n- Auto-inject `--ollama` when local models are cached\n- Registered `/boost` and `/optimize` in fast interception\n- Increment build number to 145 and package signed MSI installer\n- 100% cryptographic parity across CLI binary and MSI package",
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
            print(f"[SUCCESS] Created PR #{pr_num}: {pr_res.get('html_url')}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[ERROR] Failed to create PR: {err_msg}")
        sys.exit(1)

    # 5. Squash-merge Pull Request
    print(f"[INFO] Squash-merging PR #{pr_num}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge"
    merge_data = {
        "commit_title": f"fix(cli): optimize attachment routing, dynamic ollama flag, package signed MSI 145 (#{pr_num})",
        "merge_method": "squash"
    }
    req_merge = urllib.request.Request(merge_url, data=json.dumps(merge_data).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req_merge) as resp:
            merge_res = json.loads(resp.read().decode("utf-8"))
            print(f"[SUCCESS] Merged PR #{pr_num}: {merge_res.get('message')}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[ERROR] Failed to merge PR: {err_msg}")
        sys.exit(1)

    # 6. Checkout main and pull
    print("[INFO] Switching back to main branch and pulling latest...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # 7. Delete remote and local feature branch
    print(f"[INFO] Cleaning up branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=False)
    subprocess.run(["git", "push", "origin", "--delete", BRANCH], check=False)

    print("[SUCCESS] PR workflow complete! Main is up to date.")

if __name__ == "__main__":
    main()

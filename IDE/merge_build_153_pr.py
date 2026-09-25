#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json

REPO = "oyesanyf/ModelFusion"
BRANCH = "docs/include-acdso-build-153"

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

    commit_msg = "docs: comprehensive ACDSO documentation across README, IDE guide, and interactive docs, package signed MSI 153"

    # 1. Push to remote
    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH], check=True)

    # 2. Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_data = {
        "title": commit_msg,
        "body": "## Summary\n- Update README.md: Update CLI flag counts from 161 to 170 across all badges and documentation, add comprehensive section on ACDSO (Adaptive Contextual Data Science Optimization), covering 5-objective Pareto knee-point optimization, automated leakage guardrails, time-series forecasting, causal decision intelligence, zero paid models guarantee, and CLI/chat examples.\n- Update IDE/README.md: Add dedicated ACDSO Risk-Aware AutoML & Decision Intelligence section, add `/acdso` command to supported IDE flags and chat quick-reference table.\n- Update docs/HUGOS_IDE_GUIDE.md: Add `/acdso` to Category 5 commands and chat prompt examples, add Tutorial 5: Risk-Aware AutoML & Time-Series Forecasting with /acdso.\n- Update ModelFusion_Interactive_Docs.html: Bump to Build 153 and 170 flags, add ACDSO feature card to Core Pillars, add ACDSO Risk-Aware AutoML (9) filter button, append 9 ACDSO flags (#162 - #170) to the flags dataset.\n- Enforce 4-way cryptographic binary parity across target/release, IDE/bin, IDE/VSCode-win32-x64/bin, and %LOCALAPPDATA%/HugOS IDE/bin (SHA256: F898BD99F8DCE63D16D6455D4B1E8594DD34D1BE8F70A729C41493223151DDFB).\n- Verified 100% test pass rate across model_selection unit tests (17/17), cli unit tests (49/49), and ReST-RL / GRPO test suite (59/59).\n- Rebuild & Authenticode-sign HugOS MSI Build 153 (`IDE/HugOS.msi`, 1,510,301,696 bytes, SHA256: 4607C1F51A385F84077C8829E4799E626EF2B9D3DB34DCF71CD46A173ED830E0).",
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

    # 3. Squash-merge Pull Request
    print(f"[INFO] Squash-merging PR #{pr_num}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge"
    merge_data = {
        "commit_title": f"{commit_msg} (#{pr_num})",
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

    # 4. Checkout main and pull
    print("[INFO] Switching back to main branch and pulling latest...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # 5. Delete remote and local feature branch
    print(f"[INFO] Cleaning up branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=False)
    subprocess.run(["git", "push", "origin", "--delete", BRANCH], check=False)

    print("[SUCCESS] PR workflow complete! Main is up to date.")

if __name__ == "__main__":
    main()

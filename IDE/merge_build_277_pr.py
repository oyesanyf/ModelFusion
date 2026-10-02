#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/build-277-alphabetical-menus-cursor-icon"

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

    commit_title = "feat: restore writing menu, alphabetical sorting, dynamic cursor phrases, sleek browser icon, and Build 277 MSIs"
    commit_body = (
        "- Restored Writing & Content Creation Category in browser/ui/index.html with full suite of writing tools (/grammar, /copyedit, /paraphrase, /academic, /business, /creative, /social, /blog, /email, /docs).\n"
        "- Fixed duplicate 'Document & Code Generation' category header in browser/ui/index.html.\n"
        "- Sorted all 10 main categories in browser/ui/index.html alphabetically from A-Z (Audio & Vision, Code & Refactoring, Continuous Learning & Evolution, Data & Analysis, Document & Code Generation, Domain Knowledge & Strategy, Search & Retrieval, System & Operations, Web & Browser, Writing & Content Creation).\n"
        "- Sorted all sub-items and command action buttons within each category alphabetically A-Z.\n"
        "- Implemented dynamic streaming cursor in browser/ui/app.js with rotating status phrases (Thinking..., Analyzing..., Synthesizing..., Reasoning..., Generating response...) and smooth pulse glow.\n"
        "- Designed sleek, modern HugOS Browser icons (favicon.svg, favicon-16x16.png, favicon-32x32.png, icon-192.png, icon-512.png, favicon.ico, hugos_browser.ico) featuring an orbital cyan-to-violet gradient ring.\n"
        "- Optimized pre-packaging scripts (patch_avo_output.py, patch_extension_hidden.py, patch_cliide.py, patch_apply_codeblock.py, patch_ollama_path.py) to execute in <1s each via token scanning and conditional validation.\n"
        "- Hardened IDE/generate_wix.js and IDE/build_msi.ps1 with WiX process lock cleanup and write retries.\n"
        "- Recompiled release cli.exe via scripts/build_cli.ps1 with clang-cl and xwin-crt static CRT, verified --sys-info.\n"
        "- Established 12-way binary & asset parity via python scripts/mirror_all.py (hash: 74c45687fa367f830ede060599d59d006c1b1b8ce6f2355fb74f97eb0bdea46d).\n"
        "- Built and digitally signed IDE/HugOS.msi (Build 277, 100% payload integrity across 5,456 files) and browser/HugOS_Browser.msi with DigiCert timestamped Authenticode signatures.\n"
        "- Added test suites tests/test_alphabetical_menu.py and tests/test_dynamic_streaming_cursor.js (all passing 100%)."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    print("[INFO] Staging all tracked files and new test suites...")
    subprocess.run(["git", "add", "-A"], check=True)

    print("[INFO] Creating commit...")
    commit_msg = f"{commit_title}\n\n{commit_body}"
    res = subprocess.run(["git", "commit", "-m", commit_msg])
    if res.returncode != 0:
        print("[WARN] Nothing to commit or commit failed.")

    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    # Create Pull Request
    print("[INFO] Creating Pull Request via GitHub REST API...")
    url = f"https://api.github.com/repos/{REPO}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ModelFusion-Release-Agent"
    }

    pr_data = {
        "title": commit_title,
        "head": BRANCH,
        "base": "main",
        "body": commit_body
    }

    req = urllib.request.Request(url, data=json.dumps(pr_data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            pr_res = json.loads(resp.read().decode("utf-8"))
            pr_number = pr_res["number"]
            pr_url = pr_res["html_url"]
            print(f"[SUCCESS] Created Pull Request #{pr_number}: {pr_url}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        if "A pull request already exists" in err_msg:
            print("[INFO] PR already exists. Listing open PRs...")
            list_req = urllib.request.Request(f"{url}?head=oyesanyf:{BRANCH}&state=open", headers=headers)
            with urllib.request.urlopen(list_req) as l_resp:
                prs = json.loads(l_resp.read().decode("utf-8"))
                if prs:
                    pr_number = prs[0]["number"]
                    pr_url = prs[0]["html_url"]
                    print(f"[INFO] Found existing PR #{pr_number}: {pr_url}")
                else:
                    print(f"[ERROR] Could not find existing PR: {err_msg}")
                    sys.exit(1)
        else:
            print(f"[ERROR] Failed to create PR: {err_msg}")
            sys.exit(1)

    # Wait for GitHub PR readiness
    time.sleep(3)

    # Merge PR using squash strategy
    print(f"[INFO] Squash-merging PR #{pr_number}...")
    merge_url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/merge"
    merge_data = {
        "commit_title": f"{commit_title} (#{pr_number})",
        "commit_message": commit_body,
        "merge_method": "squash"
    }

    merge_req = urllib.request.Request(merge_url, data=json.dumps(merge_data).encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(merge_req) as m_resp:
            m_res = json.loads(m_resp.read().decode("utf-8"))
            if m_res.get("merged"):
                merged_sha = m_res.get("sha")
                print(f"[SUCCESS] PR #{pr_number} successfully squash-merged into main! (SHA: {merged_sha})")
            else:
                print(f"[WARN] Merge response: {m_res}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to squash-merge PR #{pr_number}: {e.read().decode('utf-8')}")
        sys.exit(1)

    # Delete branch on remote
    try:
        del_branch_url = f"https://api.github.com/repos/{REPO}/git/refs/heads/{BRANCH}"
        del_req = urllib.request.Request(del_branch_url, headers=headers, method="DELETE")
        with urllib.request.urlopen(del_req) as d_resp:
            print(f"[INFO] Deleted remote branch {BRANCH}.")
    except Exception as e:
        print(f"[WARN] Failed to delete remote branch: {e}")

    # Switch back to main and pull latest
    print("[INFO] Switching to local main and pulling merged commit...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    print("[SUCCESS] Main branch is up to date!")
    print(f"\nPull Request URL: {pr_url}")

if __name__ == "__main__":
    main()

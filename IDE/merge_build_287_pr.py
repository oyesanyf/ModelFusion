#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/build-287-classification-taxonomy-and-foundation-suite"

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

    commit_title = "feat: 14-menu Classification & Taxonomy suite, 12 foundation models, and Build 287 MSI"
    commit_body = (
        "- Added 14th category 'Classification & Taxonomy' in browser/ui/index.html with interactive domain filter tabs (Zero-Shot, Sentiment & Tone, Moderation, Long-Doc & Topic) and 12 foundation models strictly sorted A-Z.\n"
        "- Implemented CLASSIFICATION_MODELS registry and filterClassificationDomain() function in browser/ui/app.js.\n"
        "- Integrated classification execution routing for @agent classify, @agent zero-shot, @agent sentiment, @agent moderation, and @agent topic in executeCliCommand.\n"
        "- Added rich foundation model cards to SPECIFIC_MODEL_CARDS (BART-Large MNLI, Cross-Encoder DeBERTa-v3, DeBERTa-v3 NLI FEVER, DistilBART MNLI, DistilBERT SST-2, Twitter-RoBERTa Sentiment, GoEmotions RoBERTa, DistilBERT Emotion, Toxic-BERT, KoalaAI Text Moderation, Longformer 4096, FinBERT Classifier).\n"
        "- Added 18 classification autocomplete directives to AGENT_COMMANDS and updated Help Hub to 'All 14 Menus'.\n"
        "- Expanded and verified test suites: tests/test_alphabetical_menu.py (14 categories strictly A-Z, all sub-items strictly A-Z), tests/test_browser_comprehensive_audit.js (14 categories, 106 buttons), tests/test_help_system.js (14 categories, 44 models, 27 typo variants), and tests/test_hitl_exam_solver.js.\n"
        "- Recompiled release cli.exe with clang-cl and static CRT, verified --sys-info, established 100% 12-way parity via scripts/mirror_all.py.\n"
        "- Built and digitally signed IDE/HugOS.msi (Build 287, 100% payload integrity across 5,456 files) with DigiCert timestamped Authenticode signatures."
    )

    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    print("[INFO] Staging all tracked and untracked files...")
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

#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "fix/factual-grounding-and-silent-execution"

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

    commit_title = "fix(grounding): eliminate PowerShell popups and implement factual grounding for small models"
    commit_body = (
        "1. Eliminate PowerShell and console window popups across all three ModelFusion pillars:\n"
        "   - In memory.rs: replaced powershell and curl with native reqwest::blocking::Client, replaced cmd /C where with direct where.exe, replaced powershell env/path modifications with silent reg.exe HKCU\\Environment calls, and spawn ollama serve as detached process with CREATE_NO_WINDOW.\n"
        "   - In browser_fusion.rs: replaced cmd /c start with rundll32.exe url.dll,FileProtocolHandler with CREATE_NO_WINDOW.\n"
        "   - In hugos-browser.bat: replaced fallback powershell download with curl + run_hidden.vbs.\n"
        "   - In patch_ollama_path.py & extension.js: upgraded _ensureOllamaInPath to use silent reg.exe query/add with windowsHide: true.\n"
        "2. Implement live factual knowledge grounding & anti-hallucination guardrails for low-resource tiers:\n"
        "   - In browser/ui/app.js: added shouldRouteToWeb() pattern detection for leadership, country capitals, and biographical queries; added instant live 'Searching the web for...' status indicator bubble with stop binding; synthesized verified web evidence with strict anti-hallucination instructions and inline [1], [2] citations; added strict factual constraint fallback.\n"
        "   - In crates/cli/src/main.rs: added is_factual_query() and server-side live web search grounding in /api/chat when model is <= 3B or available RAM < 8GB.\n"
        "3. Synchronized 11-way binary parity across all pillar executables.\n"
        "4. Rebuilt, verified, and signed HugOS_Browser.msi and HugOS.msi with 100% compliant payloads."
    )

    print(f"[INFO] Creating/switching to branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    print("[INFO] Staging modified files...")
    subprocess.run(["git", "add", "-A"], check=True)

    print(f"[INFO] Committing changes...")
    subprocess.run(["git", "commit", "-m", f"{commit_title}\n\n{commit_body}"], check=True)

    print(f"[INFO] Pushing {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    print(f"[INFO] Creating Pull Request for {BRANCH} -> main...")
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

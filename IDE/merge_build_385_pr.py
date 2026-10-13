#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/native-multi-harness-rl-engine"

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
        print("[ERROR] No GitHub token found via git credential.")
        sys.exit(1)

    commit_title = "feat(rl): integrate native multi-harness reinforcement learning engine (Build 385)"
    commit_body = (
        "- Integrated Hugging Face / Liquid AI multi-harness reinforcement learning methodology natively into ModelFusion.\n"
        "- Zero external third-party harness dependencies: executes exclusively across ModelFusion's 6 native execution harnesses:\n"
        "  1. ide-copilot (cliide.exe, chat-completions)\n"
        "  2. cli-terminal (cli.exe, messages)\n"
        "  3. browser-computer-use (clibrowser.exe, responses)\n"
        "  4. rest-rl-daemon (crates/core/src/rl, chat-completions)\n"
        "  5. rd-agent (run_rd_agent, messages)\n"
        "  6. mcp-bridge (climcp.exe, messages)\n"
        "- Implemented non-linear tool-efficiency reward formula R = correctness * (1.0 + 1.5 / (15.0 + tool_calls)).\n"
        "- Added MultiHarnessBenchmark, HarnessTrajectoryRecord, and token-faithful dialect conversion in modelfusion_core.\n"
        "- Added Master CLI arguments --multi-harness, --harness, --efficiency-reward, and server endpoints /api/harness/status, /api/harness/list, /api/harness/evaluate.\n"
        "- Added Multi-Harness RL Evolution menu button to Category 11 in browser/ui/index.html in strict A-Z order.\n"
        "- Implemented buildHitlMultiHarnessWorkspaceHtml with live benchmark execution and matrix viewing in browser/ui/app.js.\n"
        "- Passed test_no_env_variable_tampering.py, test_rd_agent_integration.js, test_all_106_tools_rigorous.js, and test_multi_harness_rl_integration.js.\n"
        "- Auto-incremented to Build 385 (IDE) and Build 134 (Browser), Authenticode signed MSIs, and submitted to WDSI."
    )

    print(f"[INFO] Branch is already pushed: {BRANCH}. Creating Pull Request...")
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
    subprocess.run(["git", "fetch", "origin", "main"], check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
    subprocess.run(["git", "branch", "-D", BRANCH], check=True)
    print("[SUCCESS] Pipeline completed cleanly!")

if __name__ == "__main__":
    main()

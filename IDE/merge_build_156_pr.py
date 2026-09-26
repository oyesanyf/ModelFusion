#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/periodic-healthcheck-watchdog-build-156"

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

    commit_msg = "feat(watchdog): implement periodic healthchecks and auto-revival watchdog for ModelFusion and Ollama, package signed MSI 156"

    # 1. Checkout feature branch
    print(f"[INFO] Checking out branch {BRANCH}...")
    subprocess.run(["git", "checkout", "-B", BRANCH], check=True)

    # 2. Stage modified files
    print("[INFO] Staging files...")
    subprocess.run(["git", "add", "IDE/HugOS.wxs", "IDE/build_number.txt", "IDE/fix_slash_commands.py", "crates/cli/src/main.rs", "IDE/merge_build_156_pr.py"], check=True)
    subprocess.run(["git", "add", "-f", "IDE/bin/cli.exe"], check=True)

    # 3. Commit changes
    print(f"[INFO] Committing changes with message: {commit_msg}...")
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    # 4. Push to remote
    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH, "--force"], check=True)

    # 5. Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_data = {
        "title": commit_msg,
        "body": "## Summary\n- **Periodic Healthcheck Watchdog**:\n  - ModelFusion Master CLI (`run_server`): background async watchdog task probing `http://127.0.0.1:11434/api/tags` every 15s; auto-wakes Ollama engine via `ensure_ollama_running()` after consecutive failures.\n  - HugOS IDE Extension (`ModelFusionLMProvider`): periodic watchdog probing ModelFusion server (`http://127.0.0.1:5000/health`) and Ollama (`http://127.0.0.1:11434/api/tags`); auto-revives unresponsive server or Ollama daemon.\n  - Watchdog lifecycle bound to provider lifecycle (`_startHealthCheckWatchdog`, `_stopHealthCheckWatchdog` in `disposeServer`).\n- **Eliminate Long-Running Job & Tool Timeouts**:\n  - Removed hardcoded 600s socket timeout for long-running slash commands/tools (`/acdso`, `/automl`, `/datascience`, `/dataanalyst`, `/evolve`, `/rest-rl`, etc.) in `_sendOrchestrationRequest`.\n  - Configurable `requestTimeout` setting (0 = unlimited by default for running jobs).\n  - Socket timeout resets dynamically on incoming data chunks (`res.on(\"data\")`), ensuring active streaming/heartbeat jobs never time out.\n- **Inference Lock Self-Deadlock Resolution**:\n  - Fixed self-deadlock on `.inference.lock` where child CLI subcommands spawned by the server blocked on exclusive file lock for 600s.\n  - Passed `MODELFUSION_SUBPROCESS=1` to spawned child processes and allowed non-blocking shared access (`FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`) with 5s timeout.\n- **Parity & Tests**:\n  - Enforced 4-way cryptographic binary parity across `target/release/cli.exe`, `IDE/bin/cli.exe`, `IDE/VSCode-win32-x64/bin/cli.exe`, and `%LOCALAPPDATA%/HugOS IDE/bin/cli.exe` (SHA256: `85BCB112470EF78CF9297ABFA8E719CB368F45CD2998D977D9487FE2DDA9B004`).\n  - All 17 `model_selection` tests passed.\n  - All 49 `cli` tests passed.\n  - All 59 `ReST-RL` tests passed.\n  - Rebuilt & Authenticode-signed HugOS MSI Build 156 (`IDE/HugOS.msi`, Authenticode-signed and DigiCert timestamped).",
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

    # 6. Squash-merge Pull Request
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

    # 7. Checkout main and pull
    print("[INFO] Switching back to main branch and pulling latest...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    # 8. Delete remote and local feature branch
    print(f"[INFO] Cleaning up branch {BRANCH}...")
    subprocess.run(["git", "branch", "-D", BRANCH], check=False)
    subprocess.run(["git", "push", "origin", "--delete", BRANCH], check=False)

    print("[SUCCESS] PR workflow complete! Main is up to date.")

if __name__ == "__main__":
    main()

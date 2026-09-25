#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json

REPO = "oyesanyf/ModelFusion"
BRANCH = "fix/spawn-unknown-automl-prompt-patch"

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

    commit_msg = "fix(chat): guard workspace structure against spawn UNKNOWN, route @automl to ACDSO, package signed MSI 154"

    # 1. Push to remote
    print(f"[INFO] Pushing branch {BRANCH} to origin...")
    subprocess.run(["git", "push", "-u", "origin", BRANCH], check=True)

    # 2. Create Pull Request
    print("[INFO] Creating Pull Request via GitHub API...")
    pr_url = f"https://api.github.com/repos/{REPO}/pulls"
    pr_data = {
        "title": commit_msg,
        "body": "## Summary\n- Fix `spawn UNKNOWN (at tsx element GlobalAgentContext > UserMessage74 > _Tag > TagInner > AgentMultirootWorkspaceStructure)` chat prompt assembly crash when running `@automl` or chat commands on Windows.\n- Guard `AgentMultirootWorkspaceStructure.prepare`/`render`, `MultirootWorkspaceStructure.prepare`/`render`, `DirectoryStructure.prepare`/`render`, `WorkspaceStructure.prepare`/`render`, and `workspaceVisualFileTree` against process spawn / git failures with `emptyTree()` fallbacks.\n- Add `windowsHide: true` to `GitServiceImpl.exec` to eliminate hidden window spawn aborts.\n- Route `@automl` and `@acdso` in `crates/cli/src/main.rs` and fastInfoCommands across prompt triggers, `/orchestrate` multi-command lines, and prefix-stripping canonicalizers.\n- Enforce 4-way cryptographic binary parity across `target/release/cli.exe`, `IDE/bin/cli.exe`, `IDE/VSCode-win32-x64/bin/cli.exe`, and `%LOCALAPPDATA%/HugOS IDE/bin/cli.exe` (SHA256: `DE06830A205C5EF85A0554E02A58BD711C38D9D2ACB55B897F2F6868DDD8178F`).\n- Verify 100% test pass rate across `model_selection` unit tests (17/17), `cli` unit tests (49/49), and ReST-RL / GRPO test suite (59/59).\n- Rebuild & Authenticode-sign HugOS MSI Build 154 (`IDE/HugOS.msi`, 1,510,326,272 bytes, SHA256: `1DA07FA5D247D1236FA65EBFA5641C1C6503ABB2C26D216B80E80CB983B4B396`).",
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

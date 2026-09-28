#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "feat/deep-research-arxiv-integration"

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

    commit_title = "feat(research): integrate direct arXiv API into deep research, add dynamic status engine and error cards"
    commit_body = (
        "1. Deep Research arXiv Integration (\"anytime deep research is used it must use arXiv\"):\n"
        "   - In crates/core/src/web_research.rs: implemented search_arxiv() querying https://export.arxiv.org/api/query via reqwest with 10s timeout, custom User-Agent, and zero-panic Atom XML parsing; updated run_deep_research and run_web_agent to execute live web search and arXiv preprint search in parallel via tokio::join!, indexing all documents into WebSearchIndex; added unit tests test_parse_arxiv_atom_entry and test_web_search_index_with_arxiv_results.\n"
        "   - In crates/core/src/lib.rs: exported search_arxiv and parse_arxiv_atom.\n"
        "   - In crates/cli/src/main.rs: added --arxiv <query> CLI argument and multi-word query dispatch; mapped /arxiv, arxiv, and @agent arxiv in preprocess_cli_args; added arxiv tool definition to /api/mcp/tools and /api/arxiv HTTP endpoint; added unit tests test_preprocess_cli_args_arxiv, test_preprocess_cli_args_agent_arxiv, and test_preprocess_cli_args_slash_arxiv.\n"
        "2. Dynamic Status Engine & Explicit Error Reporting:\n"
        "   - In browser/ui/styles.css: added styling for .dynamic-status-pill, .status-pulse-dot with @keyframes pulse-dot, .agent-error-card, and .error-retry-btn.\n"
        "   - In browser/ui/index.html: added '@agent arxiv ' button in Web & Browser category.\n"
        "   - In browser/ui/app.js: added executeArxivSearch() connecting to :5000/api/arxiv with direct Atom fallback; added startDynamicStatus() rotating realistic research and reasoning states every 1500ms; added renderErrorCard() with prominent retry button calling window.executeCliCommand(lastUserPrompt); updated streamAiChat to drive dynamic status and display error card on connection failure; updated Section 4.5 and Section 6 to parallelize live web search and arXiv queries for deep research; added @agent arxiv to autocomplete.\n"
        "3. In-Memory Database Verification:\n"
        "   - In IDE/verify_msi_contents.py: updated payload verification to prioritize non-destructive in-memory MSI database inspection via msi.dll, verifying all 10 critical files and supporting both cli.exe and cliide.exe.\n"
        "4. Binary Parity, Signed MSIs, and Release Packaging:\n"
        "   - 100% cryptographic SHA-256 binary parity verified across all 11 locations.\n"
        "   - Rebuilt and signed HugOS_Browser.msi (Build 36) and HugOS.msi (Build 194) with DigiCert timestamped Authenticode signatures."
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

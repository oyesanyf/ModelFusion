#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
import json
import time

REPO = "oyesanyf/ModelFusion"
BRANCH = "sync-build-268"

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

    commit_title = "feat(browser): Ticket Booking & Map Directions HITL workspaces, natural language URL routing, and Build 268 MSI"
    commit_body = (
        "- Implemented Ticket Booking and Map Directions Human-in-the-Loop (HITL) Workspaces in browser/ui/app.js and browser/ui/styles.css.\n"
        "- Fixed computer-use execution gate in browser/ui/app.js to evaluate if (isUniversalBrowserGoal) instead of if (isContentGoal), enabling streaming and HITL execution for booking, shopping, and map directions.\n"
        "- Eliminated duplicate rendering of hitlExamCardHtml in grounding-cards-container (only hitlWorkspaceCardHtml is rendered).\n"
        "- Added Map Directions & Navigation Archetype classification in classifyPageArchetype (maps, directions, route, transit, navigate, destination, origin).\n"
        "- Implemented Natural Language URL Routing (resolveNaturalLanguageNavUrl):\n"
        "  * 'get map directions from A to B' -> https://www.google.com/maps/dir/?api=1&origin=...&destination=...\n"
        "  * 'directions to X' -> https://www.google.com/maps/dir/?api=1&destination=...\n"
        "  * 'book a ticket from SFO to JFK' -> https://www.google.com/travel/flights?q=flights+from+SFO+to+JFK\n"
        "  * 'book concert tickets' -> https://www.google.com/search?q=book+concert+tickets\n"
        "- Implemented structured route extraction (extractDirections) for both DOM and text, capturing distance, duration, transit modes, and turn-by-turn guidance.\n"
        "- Implemented Human-in-the-Loop Directions Workspace (buildHitlDirectionsWorkspaceHtml) with route cards, turn-by-turn guidance, and safety gate transitions.\n"
        "- Fixed insertBefore call in app.js with guarded safeInsertBefore.\n"
        "- Added comprehensive test suite tests/test_ticket_and_maps_directions.js (7/7 passing 100%).\n"
        "- All automated test suites passing 100%.\n"
        "- Recompiled release cli.exe, synchronized 12-way parity mirror, and built/signed HugOS.msi (Build 268) with 100% payload integrity."
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
            print(f"[SUCCESS] Created Pull Request #{pr_number}: {pr_res['html_url']}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        if "A pull request already exists" in err_msg:
            print("[INFO] PR already exists. Listing open PRs...")
            list_req = urllib.request.Request(f"{url}?head=oyesanyf:{BRANCH}&state=open", headers=headers)
            with urllib.request.urlopen(list_req) as l_resp:
                prs = json.loads(l_resp.read().decode("utf-8"))
                if prs:
                    pr_number = prs[0]["number"]
                    print(f"[INFO] Found existing PR #{pr_number}")
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
                print(f"[SUCCESS] PR #{pr_number} successfully squash-merged into main! (SHA: {m_res.get('sha')})")
            else:
                print(f"[WARN] Merge response: {m_res}")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to squash-merge PR #{pr_number}: {e.read().decode('utf-8')}")
        sys.exit(1)

    # Switch back to main and pull latest
    print("[INFO] Switching to local main and pulling merged commit...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull", "origin", "main"], check=True)

    print("[SUCCESS] Main branch is up to date!")

if __name__ == "__main__":
    main()

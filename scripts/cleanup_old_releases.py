#!/usr/bin/env python3
"""
Clean up older GitHub releases and their attached artifacts on oyesanyf/ModelFusion,
preserving only the newest release (and the latest rolling release v1.0.0-beta).
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import re

REPO = "oyesanyf/ModelFusion"
API_URL = f"https://api.github.com/repos/{REPO}"

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
        print(f"[ERROR] Failed to obtain token from git credential manager: {e}")
    return None

def api_request(url, method="GET", data=None, token=None):
    headers = {
        "User-Agent": "ModelFusion-Release-Cleaner",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return {}
            content = resp.read()
            if not content:
                return {}
            return json.loads(content.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] {method} {url} -> {e.code}: {err_body}")
        return None
    except Exception as e:
        print(f"[ERROR] {method} {url} -> {e}")
        return None

def parse_build_number(tag):
    m = re.search(r'v1\.0\.0-beta\.(\d+)', tag)
    if m:
        return int(m.group(1))
    return -1

def main():
    token = get_token()
    if not token:
        print("[ERROR] No GitHub token found. Cannot delete releases.")
        sys.exit(1)

    print(f"[INFO] Fetching all releases for {REPO}...")
    page = 1
    all_releases = []
    while True:
        url = f"{API_URL}/releases?per_page=100&page={page}"
        releases = api_request(url, token=token)
        if not releases:
            break
        all_releases.extend(releases)
        page += 1

    print(f"[INFO] Found {len(all_releases)} total releases.")

    # Identify tags to keep
    # Determine the highest versioned beta release tag
    versioned_releases = [r for r in all_releases if parse_build_number(r.get("tag_name", "")) > 0]
    highest_versioned = None
    if versioned_releases:
        highest_versioned = max(versioned_releases, key=lambda r: parse_build_number(r.get("tag_name", "")))

    keep_tags = set()
    # Always keep the latest rolling release
    keep_tags.add("v1.0.0-beta")
    if highest_versioned:
        keep_tags.add(highest_versioned["tag_name"])

    print(f"[INFO] Preserving newest release(s): {', '.join(sorted(keep_tags))}")

    deleted_count = 0
    for r in all_releases:
        tag = r.get("tag_name", "")
        rel_id = r.get("id")
        if tag in keep_tags:
            print(f"  [KEEP] {tag} (ID: {rel_id}, Name: {r.get('name')})")
            continue

        print(f"  [DELETING] {tag} (ID: {rel_id}, Name: {r.get('name')})...")
        del_url = f"{API_URL}/releases/{rel_id}"
        res = api_request(del_url, method="DELETE", token=token)
        if res is not None:
            deleted_count += 1

    print(f"\n[SUCCESS] Cleanup complete! Deleted {deleted_count} obsolete releases. Preserved {len(keep_tags)} newest release(s).")

if __name__ == "__main__":
    main()

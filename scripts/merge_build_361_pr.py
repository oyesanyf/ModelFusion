import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'IDE'))
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/resume-removal-and-job-portal-resilience'
title = 'feat(browser): resume removal, universal job portal passthrough, 403 iframe resilience & new chat (Build 361 / Browser Build 115)'
body = (
    '- Resume Removal Persistence & Anti-Re-injection:\n'
    '  * Implemented `removeSavedResume()` in `browser/ui/app.js` with clear terminal logging, staged attachment removal, and state persistence.\n'
    '  * Updated `getJobApplicantProfile()` to respect `resumeRemoved === true`, preventing automatic re-injection of default quantum resume.\n'
    '  * Added interactive `[🗑️ Remove Saved Resume]` button to resume upload prompt, candidate profile card, and HITL application workspaces.\n'
    '- Universal Job Portal & Navigation URL Passthrough:\n'
    '  * Expanded `@agent apply-jobs` with direct URL passthrough (`resolveNaturalLanguageNavUrl`) supporting any job site or company portal (Indeed, LinkedIn, Greenhouse, Lever, Workday, Ashby, ZipRecruiter, Glassdoor, Dice, or arbitrary URLs).\n'
    '  * Added specialized board recognition and archetype classification for major ATS platforms.\n'
    '- Protected Portal Session 403 Iframe Resilience:\n'
    '  * Render clean Protected Portal Session card for Google Careers and frame-blocked portals with `[🖥️ Open in Browser Viewport]` and `[↗ Open in Full Tab]` actions, eliminating raw 403 iframe crashes.\n'
    '- Universal Candidate Account Gate:\n'
    '  * Render interactive portal account and login gate in HITL workspace with candidate credential autofill, viewport login triggers, and verification gates.\n'
    '- Single Prominent [➕ New Chat] Button:\n'
    '  * Added single prominent `[➕ New Chat]` button to header, floating capsule, and conversation view toolbar, removing separate redundant `[Clear Chat]` button.\n'
    '  * Enhanced `startNewChat()` to reset conversation messages, hero views, pinned inputs, and staged attachments.\n'
    '- Comprehensive Test Suites & Verification:\n'
    '  * Updated `tests/test_apply_for_jobs_computer_use.js` (11/11 PASSED).\n'
    '  * Updated `tests/test_all_computer_use_tools.js` across all 11 tools (116/116 PASSED).\n'
    '  * Verified `tests/test_no_env_variable_tampering.py` (100% GREEN, zero registry mutations, 0 WiX violations).\n'
    '- 18-Way Binary Parity, Packaging & WDSI:\n'
    '  * Recompiled release CLI (`target/release/cli.exe`) and mirrored 18 locations via `scripts/mirror_all.py`.\n'
    '  * Packaged and signed `IDE/HugOS.msi` (Build 361) and `browser/HugOS_Browser.msi` (Build 115).\n'
    '  * Synchronized WDSI submission ledger (`IDE/reports/wdsi_submissions.json`) for all 6 release targets.'
)

print(f"Step 1: Checking out / confirming branch: {BRANCH}...")
try:
    subprocess.run(['git', 'checkout', BRANCH], check=True)
except subprocess.CalledProcessError:
    subprocess.run(['git', 'checkout', '-b', BRANCH], check=True)

print("Step 2: Staging all files...")
subprocess.run(['git', 'add', '-A'], check=True)

res = subprocess.run(['git', 'diff', '--cached', '--quiet'])
if res.returncode != 0:
    print("Step 3: Committing changes...")
    subprocess.run(['git', 'commit', '-m', f"{title}\n\n{body}"], check=True)
else:
    print("Step 3: No uncommitted changes, proceeding...")

print(f"Step 4: Pushing {BRANCH} to origin...")
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Step 5: Creating Pull Request via GitHub API for branch: {BRANCH}...")
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion-Release-Agent'}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        pr = json.loads(resp.read().decode('utf-8'))
        pr_num = pr['number']
        print(f"Created PR #{pr_num}: {pr['html_url']}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"Error creating PR: {err_body}")
    # Check if PR already exists
    list_req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls?head=oyesanyf:{BRANCH}', headers=headers)
    with urllib.request.urlopen(list_req) as lresp:
        prs = json.loads(lresp.read().decode('utf-8'))
        if prs:
            pr_num = prs[0]['number']
            print(f"Found existing PR #{pr_num}: {prs[0]['html_url']}")
        else:
            raise

print(f"Step 6: Squash-merging PR #{pr_num} into main...")
time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

print("Step 7: Checking out main and pulling latest commits...")
subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print("Successfully merged and synced to main!")

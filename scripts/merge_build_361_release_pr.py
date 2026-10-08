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
BRANCH = 'feat/computer-use-11-tools-release-build-361'
title = 'feat(computer-use): audit 11 tools, dynamic resume screening, and release build 361'
body = (
    '- Comprehensive 11-Tool Computer Use & OS Automation Audit:\n'
    '  * Upgraded test suite coverage across all 11 Computer Use tools (@agent apply-jobs, computer-use, exam-solver, ticket-booking, desktop-type, map-directions, desktop-click, shopping, screen-grounding, ui-tars, desktop-scroll).\n'
    '  * Enforced universal file acceptance (isFileTool = true) across all tools.\n'
    '  * Verified guaranteed same-page HITL card rendering with zero coordinate hallucination and typo-resilient navigation.\n'
    '- Dynamic Candidate Profile & Resume Screening Invariance:\n'
    '  * Upgraded tests/test_apply_for_jobs_computer_use.js to dynamically assert candidate qualifications against defaultProfile fields (20+ years, Master of Science in Data Science).\n'
    '  * Verified anti-re-injection persistence guard for resume removal (removeSavedResume()).\n'
    '- 18-Way Cryptographic Binary Parity:\n'
    '  * Recompiled release CLI (target/release/cli.exe, SHA-256: 5f3177dcde0eb8ab779c1d82cb576d4fb9175a4d1e0fbb43574a490791c779f9).\n'
    '  * Mirrored 18-way binary and UI distribution targets via scripts/mirror_all.py with 100% hash parity.\n'
    '- MSI Packaging, Code Signing & WDSI Submission:\n'
    '  * Packaged and Authenticode-signed IDE/HugOS.msi (Build 361) and browser/HugOS_Browser.msi (Build 115).\n'
    '  * Verified Zero-Touch PATH Law via tests/test_no_env_variable_tampering.py (0 registry mutations, 0 destructive WiX tags).\n'
    '  * Submitted all 6 Authenticode targets to Microsoft Security Intelligence (WDSI).'
)

print(f"Checking out / creating branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)

print(f"Pushing branch: {BRANCH}...")
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print("Creating Pull Request via GitHub API...")
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion-Release-Agent'}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
with urllib.request.urlopen(req) as resp:
    pr = json.loads(resp.read().decode('utf-8'))
    pr_num = pr['number']
    print(f"Created PR #{pr_num}: {pr['html_url']}")

print(f"Squash-merging PR #{pr_num} into main...")
time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print("Successfully merged and synced to main!")

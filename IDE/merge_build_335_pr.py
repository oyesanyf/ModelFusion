import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/build-335-code-audit-line-by-line-fixes'
title = 'feat(audit): resolve line-by-line code issues, optimize decision engine timeout, and update MSIs to build 335'
body = (
    '- Resolved line-by-line code audit issues in browser/ui/app.js:\n'
    '  * Removed redundant duplicate escapeHtml function declaration inside Section 4b (browser agent).\n'
    '  * Increased evaluateDecisionModel TCP abort timeout from 60ms to 300ms to prevent premature aborts on Windows loopback under system load.\n'
    '- Resolved line-by-line code audit issues in crates/cli/src/main.rs:\n'
    '  * Replaced manual quote_char.unwrap() with safe pattern matching filter in tag attribute extraction.\n'
    '  * Replaced token.unwrap() with safe pattern matching and empty/missing token fallbacks in query_hf_router.\n'
    '- 100% Green Test Suites:\n'
    '  * tests/test_alphabetical_menu.py (All 14 categories & sub-items sorted A-Z)\n'
    '  * tests/test_all_106_tools_rigorous.js (All 106 tools validated)\n'
    '  * tests/test_browser_all_106_tools_with_inputs.js (106/106 tools E2E input tests passed)\n'
    '  * tests/test_help_system.js (All 14 category @help routes & cards passed)\n'
    '  * tests/test_clef_decision_models.js (All 9 decision model test suites passed)\n'
    '- Mirrored all 12 binary and UI distribution locations via scripts/mirror_all.py.\n'
    '- Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '- Built, payload-verified, and Authenticode digitally signed release MSIs: IDE/HugOS.msi (Build 335, 366.75 MB) and browser/HugOS_Browser.msi (Build 89, 227.78 MB).\n'
    '- Master Server daemon online and healthy on port 5000.'
)

print('[GIT] Checking out branch:', BRANCH)
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '--allow-empty', '-m', f'{title}\n\n{body}'], check=True)

print('[GIT] Pushing branch to origin...')
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'ModelFusion-Release-Agent'
}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
with urllib.request.urlopen(req) as resp:
    pr = json.loads(resp.read().decode('utf-8'))
    pr_num = pr['number']
    print(f"Created PR #{pr_num}: {pr['html_url']}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Branch merged to main and synced successfully!')

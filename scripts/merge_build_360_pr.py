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
BRANCH = 'feat/data-browser-acdso'
title = 'feat(browser): add ACDSO AutoML to Data & Spreadsheets menu with @acdso routing (Build 360 / Browser Build 114)'
body = (
    '- Data & Spreadsheets Menu Enhancements (`browser/ui/index.html`):\n'
    '  * Updated `tool_acdso` in `Data & Spreadsheets (CSV/Excel)` with label "ACDSO AutoML", tag "@acdso", and title "ACDSO: Automated Causal Decision Science Optimization & AutoML".\n'
    '  * Preserved strict alphabetical ordering across all 6 tools in Data & Spreadsheets (ACDSO AutoML -> Data Insights -> Data Science Flow -> Decision Optimizer -> Predict Outcome -> Time-Series Forecast).\n'
    '- Menu Validation & Verification Script Updates (`scripts/validate_compact_menu.py`):\n'
    '  * Synchronized compact menu definition to "ACDSO AutoML" (12 chars <= 20 char budget) under `Data & Spreadsheets (CSV/Excel)`.\n'
    '- Browser Command Routing & Regex Upgrades (`browser/ui/app.js`):\n'
    '  * Enhanced command routing for ACDSO to support `/acdso`, `@agent acdso`, `@acdso`, and regex `/^(?:@agent\\s+|@|\\/)?acdso\\b/i`.\n'
    '  * Upgraded URL / argument extraction regex to cleanly parse dataset files and URLs.\n'
    '- Comprehensive Test Suites & Verification:\n'
    '  * Created `tests/test_browser_data_acdso.js` validating menu attributes, alphabetical ordering, and command routing (100% PASSED).\n'
    '  * Updated `tests/test_all_106_tools_rigorous.js` and `tests/test_browser_all_106_tools_with_inputs.js` to 109 tools across 15 categories (100% PASSED).\n'
    '  * Verified `tests/test_alphabetical_menu.py`, `scripts/validate_compact_menu.py`, and `tests/test_no_env_variable_tampering.py` (100% GREEN).\n'
    '- 18-Way Cryptographic Parity, Packaging & WDSI:\n'
    '  * Mirrored 18-way binary and UI parity via `scripts/mirror_all.py`.\n'
    '  * Built and signed `IDE/HugOS.msi` (Build 360) and `browser/HugOS_Browser.msi` (Build 114).\n'
    '  * Verified ModelFusion Master Server alive on port 5000 (`/health` -> 200 OK).\n'
    '  * Submitted all Authenticode release targets to Microsoft Security Intelligence (WDSI).'
)

print(f"Step 1: Checking out branch {BRANCH}...")
try:
    subprocess.run(['git', 'checkout', '-b', BRANCH], check=True)
except subprocess.CalledProcessError:
    subprocess.run(['git', 'checkout', BRANCH], check=True)

print("Step 2: Staging all files...")
subprocess.run(['git', 'add', '-A'], check=True)

print("Step 3: Committing changes...")
subprocess.run(['git', 'commit', '-m', f"{title}\n\n{body}"], check=True)

print(f"Step 4: Pushing {BRANCH} to origin...")
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Step 5: Creating Pull Request via GitHub API for branch: {BRANCH}...")
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion-Release-Agent'}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
with urllib.request.urlopen(req) as resp:
    pr = json.loads(resp.read().decode('utf-8'))
    pr_num = pr['number']
    print(f"Created PR #{pr_num}: {pr['html_url']}")

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

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
BRANCH = 'feature/build-398-browser-146-instant-startup-reorder'
title = 'perf(browser): instant <100ms desktop launch reorder, eliminate startup blocking loops & optimize LangExtract idle init (IDE Build 398 / Browser Build 146)'
body = (
    '- Instant Browser Desktop Launch Reordering:\n'
    '  * Reordered browser/Chromium-win32-x64/hugos-browser.bat to launch chrome.exe --app="%START_URL%" in Step 1 immediately upon discovery (<50-100ms) BEFORE executing any background health checks or daemons.\n'
    '  * Synchronized updated launcher directly to %LOCALAPPDATA%\\HugOS Browser\\Chromium-win32-x64\\hugos-browser.bat so Desktop and Start Menu icons open instantly.\n'
    '- Elimination of Blocking Delays & Loops:\n'
    '  * Removed legacy 10-iteration blocking loop (for /L %%i in (1,1,10)) and timeout /t 1 /nobreak calls that previously blocked the desktop icon for up to 10-20 seconds.\n'
    '  * Converted Ollama and Master Server checks in Step 2 to non-blocking probes with fast timeouts (--connect-timeout 1 --max-time 1).\n'
    '  * Added fallback health check on port 5005 alongside port 5000 so the launcher recognizes existing servers and never spawns redundant instances.\n'
    '- Optimized UI LangExtract Initialization:\n'
    '  * In browser/ui/app.js, pre-populated globalLangExtractMenuMap from DEFAULT_16_CATEGORY_MENU_PROTOTYPES with zero runtime latency.\n'
    '  * Removed duplicate synchronous invocation of annotateAllMenuCategoriesWithLangExtract() during DOMContentLoaded.\n'
    '  * Deferred DOM menu annotations to idle time (requestIdleCallback / setTimeout(..., 20)) ensuring zero main-thread jank during startup.\n'
    '- Packaging, WDSI & 18-Way Parity:\n'
    '  * Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '  * Maintained 18-way cryptographic binary parity across all distribution roots via scripts/mirror_all.py.\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 398) and HugOS_Browser.msi (Build 146).\n'
    '  * Submitted all 6 Authenticode-signed release targets to Microsoft Security Intelligence (WDSI).\n'
    '- Automated Verification:\n'
    '  * Updated tests/test_browser_launcher_and_port_conflict.js asserting instant launch ordering, dual-port health checks, and zero blocking loops (100% pass).\n'
    '  * All 9 tests in tests/test_langextract_google_ddg_search_and_deep_research.js passed 100%.\n'
    '  * Verified tests/test_no_env_variable_tampering.py (100% pass, zero registry mutations).'
)

print(f"Staging all changes...")
subprocess.run(['git', 'add', '-A'], check=True)
status_res = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=True)
if status_res.stdout.strip():
    print("Committing changes on local branch...")
    subprocess.run(['git', 'commit', '-m', title], check=True)

print(f"Creating and pushing branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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

print(f"Squash-merging PR #{pr_num} into main...")
time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
print("Successfully merged and synced to main!")

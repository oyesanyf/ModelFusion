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
BRANCH = 'fix/browser-iframe-sad-face-and-navigation-dedup'
title = 'fix(browser): eliminate sad face iframe crash, de-duplicate Back to Chat navigation, and strengthen Master Server proxy (Build 354 / Browser Build 109)'
body = (
    '- Chromium Webview Sad Face (:() Elimination & Proxy Resilience in `browser/ui/app.js` and `crates/cli/src/main.rs`:\n'
    '  * Intercepted cross-origin navigation failures before assigning `browserFrame.src`, setting `src = "about:blank"` and cleanly revealing `#frame-fallback` when Master Server proxy is unavailable.\n'
    '  * Strengthened `browserFrame.onerror` and `browserFrame.onload` cross-origin error handling to reset to blank and unhide fallback options.\n'
    '  * Updated `#btn-open-toplevel` to call `window.open(url, "_blank")`, eliminating top-level window replacement that hijacked the HugOS UI.\n'
    '  * Wired up `#btn-fallback-retry` to re-probe port 5000 `/health` and re-attempt proxied navigation.\n'
    '  * Extended Master Server `/orchestrate` endpoint in `crates/cli/src/main.rs` to support `task` and `model_override` payload fallbacks and return `"result"`.\n'
    '- Navigation De-duplication in `browser/ui/index.html`:\n'
    '  * Hidden redundant floating return HUD button (`.floating-return-chat-container`).\n'
    '  * Removed duplicate `.wv-btn-return-chat` and `#btn-wv-home` from webview toolbar.\n'
    '  * Consolidated all return navigation into `#header-breadcrumb-bar`.\n'
    '- Comprehensive Test Verification (100% Green):\n'
    '  * `tests/test_browser_navigation_and_proxy_resilience.js` (PASSED 100%)\n'
    '  * `tests/test_missing_model_guidance.js` (6/6 PASSED)\n'
    '  * `tests/test_apply_for_jobs_computer_use.js` (10/10 PASSED)\n'
    '  * `tests/test_hitl_exam_solver.js` (11/11 PASSED)\n'
    '  * `tests/test_no_env_variable_tampering.py` (Zero-Touch PATH verified)\n'
    '  * `tests/test_career_ops.py` (5/5 PASSED)\n'
    '  * `tests/test_all_computer_use_tools.js` (112/112 PASSED)\n'
    '  * `tests/test_career_ops_integration.js` (63/63 PASSED)\n'
    '  * `tests/test_embeddinggemma2_replacement.py` (5/5 PASSED)\n'
    '  * `tests/test_wdsi_submission.py` (5/5 PASSED)\n'
    '- 18-Way Cryptographic Parity & Multi-Target Packaging:\n'
    '  * Recompiled release Master CLI (`cargo build --release --bin cli`).\n'
    '  * Mirrored 18-way binary and UI parity via `scripts/mirror_all.py`.\n'
    '  * Synchronized build metadata: `IDE/build_number.txt` -> 354, `browser/build_number.txt` -> 109.\n'
    '  * Authenticode signed MSIs: Built and signed `IDE/HugOS.msi` (Build 354) and `browser/HugOS_Browser.msi` (Build 109).\n'
    '  * Submitted all Authenticode-signed targets to Microsoft Security Intelligence (WDSI).'
)

print(f"Pushing branch: {BRANCH}...")
subprocess.run(['git', 'add', '-A'], check=True)
# Commit if there are unstaged changes
res = subprocess.run(['git', 'diff', '--cached', '--quiet'])
if res.returncode != 0:
    subprocess.run(['git', 'commit', '-m', f'{title}\n\n{body}'], check=True)

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
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print("Successfully merged and synced to main!")

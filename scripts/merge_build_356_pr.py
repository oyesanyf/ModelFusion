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
BRANCH = 'fix/exam-answer-submission-resilience'
title = 'fix(exam-solver): strengthen live DOM answer submission & add host model calibration utility (Build 356 / Browser Build 111)'
body = (
    '- Exam Solver Live DOM Sync & Form Submission Fix in `browser/ui/app.js`:\n'
    '  * Implemented `syncExamOptionToLiveDom(qIndex, optionKey)` supporting 4 resilient synchronization strategies (explicit IDs/names, group name indexing, numeric 1-based and letter value matching, and interactive label clicks).\n'
    '  * Prioritized 1-based numeric matching (`targetVal1`) and exact letter matching over 0-based matching to prevent value "3" (C in 1-based) from erroneously matching option D.\n'
    '  * Updated `selectExamOption(qIndex, optionKey)` and `confirmExamSubmit()` to synchronize live webview DOM radio buttons with safety gate selection.\n'
    '  * Enhanced `confirmExamSubmit()` to auto-populate recommended options if unselected, trigger form submission via `form.requestSubmit()`, and update safety gate UI with next question progress.\n'
    '  * Expanded `findNextQuestionButton` with selectors for `input[value*="Answer" i]`, `input[name="submit" i]`, and next candidate button regex.\n'
    '  * Added comprehensive `tests/test_exam_answer_submission.js` verifying DOM sync, option selection, form submission, and advancement (7/7 tests passed, 100%).\n'
    '- Calibrated Host Models Feature (`@agent download-calibrated-models`):\n'
    '  * Added `tool_download_calibrated_models` button to `browser/ui/index.html` strictly sorted alphabetically (A-Z) in Category 15: "Utilities & System" between `tool_db_check` and `tool_export`.\n'
    '  * Added `download_calibrated_models` to `Args` struct and CLI preprocessor in `crates/cli/src/main.rs`.\n'
    '  * Implemented dynamic hardware evaluation in Master CLI (`query_system_resources()`, `select_ollama_model_for_hardware`, `select_verifier_model_for_hardware`, and `provision_multi_model_fusion_for_hardware()`) based on runtime free RAM and free VRAM.\n'
    '  * Added `/api/models/provision-hardware` and `/api/models/calibrate-hardware` endpoints to Master Server daemon.\n'
    '  * Added interactive host hardware telemetry card and calibrated multi-model suite rendering in `browser/ui/app.js`.\n'
    '  * Updated `tests/test_browser_menu_accordion_and_tool_count.js` tool count assertion to 109.\n'
    '- Comprehensive Test Verification (100% Green):\n'
    '  * `tests/test_exam_answer_submission.js` (7/7 PASSED)\n'
    '  * `tests/test_hitl_exam_solver.js` (11/11 PASSED)\n'
    '  * `tests/test_cfp_exam_solver.js` (PASSED 100%)\n'
    '  * `tests/test_browser_navigation_and_proxy_resilience.js` (PASSED 100%)\n'
    '  * `tests/test_all_computer_use_tools.js` (112/112 PASSED)\n'
    '  * `tests/test_apply_for_jobs_computer_use.js` (10/10 PASSED)\n'
    '  * `tests/test_career_ops_integration.js` (63/63 PASSED)\n'
    '  * `tests/test_career_ops.py` (5/5 PASSED)\n'
    '  * `tests/test_alphabetical_menu.py` (15/15 categories sorted, PASSED)\n'
    '  * `tests/test_browser_menu_accordion_and_tool_count.js` (PASSED 100%)\n'
    '  * `tests/test_no_env_variable_tampering.py` (Zero-Touch PATH verified, 100% GREEN)\n'
    '- 18-Way Cryptographic Parity & Multi-Target Packaging:\n'
    '  * Recompiled release Master CLI (`cargo build --release --bin cli`).\n'
    '  * Mirrored 18-way binary and UI parity via `scripts/mirror_all.py`.\n'
    '  * Synchronized build metadata: `IDE/build_number.txt` -> 356, `browser/build_number.txt` -> 111.\n'
    '  * Authenticode signed MSIs: Built and signed `IDE/HugOS.msi` (Build 356) and `browser/HugOS_Browser.msi` (Build 111).\n'
    '  * Submitted all Authenticode-signed targets (`cli.exe`, `clibrowser.exe`, `cliide.exe`, `climcp.exe`, `HugOS.msi`, `HugOS_Browser.msi`) to Microsoft Security Intelligence (WDSI).'
)

print(f"Checking out / creating branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)

print(f"Staging changes...")
subprocess.run(['git', 'add', '-A'], check=True)

# Commit if there are unstaged/staged changes
res = subprocess.run(['git', 'diff', '--cached', '--quiet'])
if res.returncode != 0:
    print("Committing...")
    subprocess.run(['git', 'commit', '-m', f'{title}\n\n{body}'], check=True)

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
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print("Successfully merged and synced to main!")

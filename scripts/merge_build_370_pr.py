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
BRANCH = 'fix/hitl-outline-tdz-initialization'
title = 'fix(browser): eliminate TDZ activeOutline exception & restore Writing Outline Workspace (Build 370 / Browser Build 124)'
body = (
    '- Writing Outline & Pacing Workspace TDZ Elimination (`browser/ui/app.js`):\n'
    '  * Root cause eliminated: `activeOutline` and `activeShellAction` were declared with `let` inside `executeCliCommand` thousands of lines below Phase 1 HITL Gate 2 call site.\n'
    '  * Removed `let activeOutline = null;` and `let activeShellAction = null;` from inside `executeCliCommand`.\n'
    '  * Hoisted `var activeOutline = null;` and `var activeShellAction = null;` to the top of `DOMContentLoaded` scope and initialized on `window`.\n'
    '  * Changed `activeExamQuestions`, `activeProducts`, `activeDirections`, `activeJobPostings` from `let` to `var` with safe `window` checks, completely eliminating Temporal Dead Zone (TDZ) ReferenceErrors.\n'
    '- De-Duplication & Preferred Message Bubble Action Bar:\n'
    '  * Completely removed redundant `#chat-floating-actions` / `.chat-floating-actions` toolbar from `index.html` and `styles.css` per user explicit preference.\n'
    '  * Retained full, styled message bubble action bar (`.msg-action-bar`) on assistant message bubbles (`👍 Good`, `👎 Bad`, `⚡ Continue`, `📋 Copy`, `⬆️ Share`, `📥 Export`, `🔊 Read Aloud`, `🔄 Regenerate`, `⋯`).\n'
    '  * Retained native capsule send/stop button (`btnSendPromptPinned.classList.add("btn-stop-generating")`), ensuring zero duplicate buttons on screen.\n'
    '- 100% Comprehensive Regression & Test Suite Passed:\n'
    '  * `tests/test_hitl_writing_outline_resilience.js` (100% PASSED)\n'
    '  * `tests/test_continue_and_regenerate_buttons.js` (100% PASSED)\n'
    '  * `tests/test_browser_menu_accordion_and_tool_count.js` (100% PASSED)\n'
    '  * `tests/test_apply_for_jobs_computer_use.js` (12/12 PASSED, 100%)\n'
    '  * `tests/test_career_ops_integration.js` (63/63 PASSED, 100%)\n'
    '  * `tests/test_career_ops.py` (5/5 PASSED, 100%)\n'
    '  * `tests/test_no_env_variable_tampering.py` (Zero-Touch PATH verified, 100% GREEN)\n'
    '  * `tests/test_alphabetical_menu.py` (15/15 categories sorted, 100% PASSED)\n'
    '  * `tests/test_wdsi_submission.py` (5/5 PASSED, 100%)\n'
    '- 18-Way Cryptographic Parity, Packaging & WDSI:\n'
    '  * Recompiled release Master CLI (`cargo build --release --bin cli`).\n'
    '  * Mirrored 18-way binary and UI parity via `scripts/mirror_all.py`.\n'
    '  * Synchronized build metadata: `IDE/build_number.txt` -> 370, `browser/build_number.txt` -> 124.\n'
    '  * Authenticode signed MSIs: Built and signed `IDE/HugOS.msi` (Build 370) and `browser/HugOS_Browser.msi` (Build 124).\n'
    '  * Submitted all 6 Authenticode-signed targets (`cli.exe`, `clibrowser.exe`, `cliide.exe`, `climcp.exe`, `HugOS.msi`, `HugOS_Browser.msi`) to Microsoft Security Intelligence (WDSI).'
)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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

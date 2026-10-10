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
BRANCH = 'fix/single-submenu-and-load-page-resilience'
title = 'fix(browser): single flat submenu across all 16 categories & blank load page resilience (Build 371 / Browser Build 125)'
body = (
    '- Single Flat Submenu Across All Sidebar Categories (Uniformity Law):\n'
    '  * Eliminated all inner sub-grouping filter tabs (`domain-filter-tabs`) across all categories (`Finance & Markets`, `Science & Discovery`, and `Legal & Compliance`).\n'
    '  * Every single category menu now possesses exactly ONE uniform flat submenu matching the structure of "Data & Spreadsheets (CSV/Excel)".\n'
    '  * Split "Legal & Compliance" into two distinct sidebar categories in strict alphabetical order A-Z:\n'
    '    - "Compliance" (under \'C\', placed after \'Code & Security\' and before \'Computer Use & OS Automation\') with 4 tools: Contract Review (@cuad), Document Classifier (@legal-bert), Multi-Page Contracts (@longformer), Regulatory Search (@pile-of-law).\n'
    '    - "Legal" (under \'L\', placed after \'Inspect Windows Apps\' and before \'Planning & Deep Thinking\') with 4 tools: Case Law & Precedent (@lawma), Interactive Legal (@law-chat), Legal Counsel (@saul), Statutory Briefs (@law-llm).\n'
    '  * Exactly 16 categories in 100% strict alphabetical order (A-Z) with all 109 tool sub-items sorted alphabetically.\n'
    '- Load Page Blank Resilience & Frame Fallback Protection (`browser/ui/app.js` & `browser/ui/styles.css`):\n'
    '  * Removed duplicate synchronous iframe fallback assignment block (lines ~10674-10694) racing with `fetchWithTimeout`.\n'
    '  * Added strict guard in `browserFrame.onload`: Never hides `#frame-fallback` on `about:blank`, empty `src`, or when fallback card is currently active.\n'
    '  * Upgraded `#frame-fallback` with elevated high-contrast backdrop-filter styling and verified direct action buttons: `[↗️ Open Direct in Browser]`, `[🔄 Retry / Connect Proxy]`, `[💬 Back to Chat]`.\n'
    '- Automated Test Suite & 100% Green Verification:\n'
    '  * `tests/test_single_submenu_and_load_page.js` (NEW - 100% PASSED)\n'
    '  * `tests/test_alphabetical_menu.py` (Updated for 16 categories - 100% PASSED)\n'
    '  * `tests/test_browser_menu_accordion_and_tool_count.js` (Updated for 16 categories - 100% PASSED)\n'
    '  * `tests/test_browser_performance_responsiveness.js` (100% PASSED)\n'
    '  * `tests/test_no_env_variable_tampering.py` (Zero-Touch PATH verified - 100% GREEN)\n'
    '  * `tests/test_apply_for_jobs_computer_use.js` (12/12 PASSED - 100%)\n'
    '  * `tests/test_career_ops_integration.js` (63/63 PASSED - 100%)\n'
    '  * `tests/test_career_ops.py` (5/5 PASSED - 100%)\n'
    '  * `tests/test_wdsi_submission.py` (5/5 PASSED - 100%)\n'
    '- 18-Way Cryptographic Parity, Packaging & WDSI:\n'
    '  * Recompiled release Master CLI (`cargo build --release --bin cli`).\n'
    '  * Mirrored 18-way binary and UI parity via `scripts/mirror_all.py`.\n'
    '  * Synchronized build metadata: `IDE/build_number.txt` -> 371, `browser/build_number.txt` -> 125.\n'
    '  * Authenticode signed MSIs: Built and signed `IDE/HugOS.msi` (Build 371) and `browser/HugOS_Browser.msi` (Build 125).\n'
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

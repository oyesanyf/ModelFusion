import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'IDE'))
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] Could not acquire GitHub token via Git Credential Manager.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'fix/internet-accuracy-enrichment-and-anti-staleness'
title = 'feat(accuracy,coding): implement anti-staleness search enrichment & universal coding helper code interpreter (Build 373 / Browser Build 127)'
body = (
    '- Anti-Staleness & Real-Time Internet Search Grounding (`browser/ui/app.js` & `crates/cli/src/main.rs`):\n'
    '  * Activated `isAntiStalenessAndAccuracyQuery()` for financial valuations (tickers, market caps, stock quotes), political leadership & appointments, and temporal/macroeconomic queries (2024-2027 years, inflation).\n'
    '  * Enforced Internet Accuracy Enrichment Law with explicit temporal anchoring (2026), verified institutional data retrieval, 52-week trading ranges, and real-time quotes.\n'
    '  * Preserved local routing for internal creative and coding reasoning tasks (`routeToWeb: false`).\n'
    '- Universal Coding Helper & Computational Code Interpreter (`browser/ui/app.js`, `crates/cli/src/main.rs`, `browser/ui/index.html`):\n'
    '  * Added `@agent code-helper` and `/code-helper` directives with Multi-Model Fusion activation (Primary Coder + Verifier Specialist + Sandbox).\n'
    '  * Auto-routed explicit coding requests, complex math/computational questions (compound interest, Monte Carlo, prime generation, permutations), and data parsing (JSON/CSV).\n'
    '  * Implemented ChatGPT-style collapsible `<details class="code-interpreter-drawer">` with execution status badge, run duration, copy controls, and stdout terminal.\n'
    '  * Added `▶️ Run Code` buttons with inline execution consoles across rendered code blocks.\n'
    '  * Integrated `/api/code/run` sandbox endpoint in Master Server CLI with temporary execution isolation and strict 10s preemption timeout.\n'
    '  * Added `tool_code_helper` in sidebar menu under `Code & Security` in strict alphabetical order.\n'
    '- Packaging, Verification & WDSI:\n'
    '  * 18-way cryptographic binary parity synchronized across all targets.\n'
    '  * Built and Authenticode-signed `IDE/HugOS.msi` (Build 373) and `browser/HugOS_Browser.msi` (Build 127).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI).\n'
    '  * 100% Green on all test suites (`test_internet_accuracy_enrichment.js`, `test_coding_helper_and_code_interpreter.js`, `test_alphabetical_menu.py`, `test_no_env_variable_tampering.py`, `test_wdsi_submission.py`).'
)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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
    print(f"HTTPError {e.code}: {err_body}")
    if 'A pull request already exists' in err_body:
        list_req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls?head=oyesanyf:{BRANCH}', headers=headers)
        with urllib.request.urlopen(list_req) as lresp:
            prs = json.loads(lresp.read().decode('utf-8'))
            pr_num = prs[0]['number']
            print(f"Found existing PR #{pr_num}: {prs[0]['html_url']}")
    else:
        raise

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

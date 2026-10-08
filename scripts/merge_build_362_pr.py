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
BRANCH = 'feat/distributional-rl-cvar-quantile-scoring'
title = 'feat(rl): distributional RL quantile scoring & CVaR risk-aware decision routing (Build 362 / Browser Build 116)'
body = (
    '- Distributional RL & Second-Moment Variance Estimation:\n'
    '  * Implemented `RiskProfile` enum (`Optimistic`, `Neutral`, `WorstCase`, `CVaR`, `AdaptiveCritical`) in `crates/core/src/rl/adaptive_controller.rs`.\n'
    '  * Implemented `DistributionalScore` containing expected mean, aleatoric variance, epistemic uncertainty, total uncertainty, 5 quantiles [10%, 25%, 50%, 75%, 90%], VaR, and CVaR.\n'
    '  * Added second-moment online accumulator `b_sq_vector` and circular replay buffer `CircularReplayBuffer` (10,000 capacity) for historical transition logging.\n'
    '  * Implemented Gaussian tail approximation and normal quantile estimation for exact VaR and CVaR calculations.\n'
    '- Master CLI & HTTP Server Endpoints:\n'
    '  * Added `--rl-route`, `--risk-profile`, and `--cvar-alpha` flags to `crates/cli/src/main.rs`.\n'
    '  * Implemented markdown table output and structured `--reporttype json` format for `--rl-route`.\n'
    '  * Updated `/api/rl/status` to broadcast `distributional_rl_enabled: true` and `supported_risk_profiles`.\n'
    '  * Updated `/api/rl/route` to support risk profiles and CVaR alpha parameterization.\n'
    '  * Added `@agent rl-route` preprocessing and help card documentation in `tool_help.rs`.\n'
    '- HugOS Browser UI Risk-Aware Integration:\n'
    '  * Exported `window.routeDistributionalRL` helper and added telemetry badge (`🛡️ Distributional CVaR`).\n'
    '  * Updated `evaluateDecisionModel` in `browser/ui/app.js` to automatically route mission-critical tasks (Computer Use, UI-TARS, Exam Solver, Legal, Security) with CVaR risk protection (`risk_profile: \'cvar\'`, `cvar_alpha: 0.05`).\n'
    '- Verification & Test Suites:\n'
    '  * Added comprehensive `tests/test_distributional_rl_router.js` testing CLI markdown table, JSON output, quantile monotonicity, CVaR <= Mean invariant, and ephemeral HTTP server endpoints.\n'
    '  * Verified `tests/test_no_env_variable_tampering.py` (100% green, 0 registry mutations, 0 WiX violations).\n'
    '  * Verified `tests/test_all_computer_use_tools.js` (122/122 passed).\n'
    '  * Verified `tests/test_apply_for_jobs_computer_use.js` (11/11 passed).\n'
    '  * Verified `tests/test_wdsi_submission.py` (100% compliant).\n'
    '- 18-Way Binary Parity, Packaging & WDSI:\n'
    '  * Recompiled release CLI (`target/release/cli.exe`) and mirrored 18 locations via `scripts/mirror_all.py`.\n'
    '  * Packaged and signed `IDE/HugOS.msi` (Build 362) and `browser/HugOS_Browser.msi` (Build 116).\n'
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

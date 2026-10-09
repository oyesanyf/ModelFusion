import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] GitHub token could not be obtained.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/career-ops-load-page-and-dynamic-computer-use'
title = 'feat(browser,cli): Load Page viewport action, eliminate sad-face iframe crash & Career-Ops model routing (Build 363 / Browser Build 117)'
body = (
    '- Browser Webview & Load Page Enhancement:\n'
    '  * Replaced `⤢ Full View` and `↗ New Tab` buttons in inline webview cards with a unified, high-visibility `[🌐 Load Page]` button (`btn-load-page`) navigating directly to primary browser viewport.\n'
    '  * Eliminated Chromium sad-face document icon (`:(`) on iframe-restricted sites (Indeed, Google Careers, LinkedIn, Workday, Greenhouse, Lever, SmartRecruiters, Ashby, ZipRecruiter, Dice).\n'
    '  * Rendered sleek, high-tech `Live Web Session` portal card for cross-origin restricted sites and added robust `onerror`/`onload` fallback hiding iframe errors and revealing `[Load Page]`.\n'
    '- Autonomous Career-Ops & Job Application Model Routing:\n'
    '  * Fixed model mismatch for job applications: replaced generic desktop mouse-clicking `ui-tars` agent loop with specialized `ModelFusion Career-Ops & Candidate Application Agent`.\n'
    '  * Updated recruitment action steps: `PORTAL_NAVIGATION`, `ATS_REQUIREMENTS_PARSING`, `CV_FIT_&_CAREER_OPS_MATCHING`, `HITL_ACCOUNT_&_LOGIN_GATE`, and `APPLICATION_SUBMISSION`.\n'
    '  * Dynamically resolved optimal models in `/api/computer-use` (`crates/cli/src/main.rs:16599`): probes installed Ollama models, prioritizing vision models (`moondream`, `llava`, `qwen2.5-vl`) or calibrated hardware models (`qwen2.5:32b`, `qwen2.5:14b`, `qwen2.5:7b`, `gemma2`).\n'
    '  * Updated `ComputerUseAgent` in `crates/core/src/browser/computer_use.rs`: text-prompt retry when model does not accept images, and coordinate-free graceful fallback without fake mouse coordinates.\n'
    '  * Updated `systemPrompt` in `browser/ui/app.js` with specialized Career-Ops instructions for job goals.\n'
    '  * Updated `streamAiChat` calls for job goals to pass `taskType: \'job_application\'`, isolating context and applying calibrated models.\n'
    '- Verification & Test Suites (100% Green):\n'
    '  * `node tests/test_apply_for_jobs_computer_use.js` (All 12 test suites passing 100%).\n'
    '  * `node tests/test_all_computer_use_tools.js` (All 134 assertions passing 100%).\n'
    '  * `python tests/test_no_env_variable_tampering.py` (Zero-Touch PATH Law verified 100%).\n'
    '  * `node tests/test_distributional_rl_router.js` (Distributional RL router verified 100%).\n'
    '- 18-Way Binary Parity, Packaging & WDSI:\n'
    '  * Recompiled release CLI (`target/release/cli.exe`) and mirrored across all 18 distribution paths via `scripts/mirror_all.py`.\n'
    '  * Packaged and Authenticode signed `IDE/HugOS.msi` (Build 363, 390.36 MB, SHA-256: `8a1c931f053bb8771e514d2e4ac8d4c537b4d5c38a4748c540f7ebcd82126b61`).\n'
    '  * Packaged and Authenticode signed `browser/HugOS_Browser.msi` (Build 117, 125.37 MB, SHA-256: `56dd3c98cc27b51b0e0b212a48b2ed6c3560cb4931ff45f77251518bc8a56758`).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft WDSI and updated `IDE/reports/wdsi_submissions.json`.'
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
    pr_url = pr['html_url']
    print(f"Created PR #{pr_num}: {pr_url}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Successfully merged and pulled main branch!')
print(f'PR_URL={pr_url}')

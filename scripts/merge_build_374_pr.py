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
BRANCH = 'feature/agentic-loop-anti-loop-build-374'
title = 'feat(agentic-loop): anti-loop circuit breaker, ultra-longform scaling up to 1000 pages & task-adaptive sweet spot (Build 374)'
body = (
    '- Anti-Loop Circuit Breaker (`browser/ui/app.js`):\n'
    '  * Halts repetitive looping when turns restart from Page 1 / Chapter 1 or have high sentence repetition ratio (>40%).\n'
    '  * Reverts duplicate turn output and logs transparent warning to preserve clean manuscript.\n'
    '- Ultra-Longform Scaling up to 1,000+ Pages (`browser/ui/app.js`):\n'
    '  * Dynamically computes targetTokens = max(32768, pages * 700, words * 1.4) without artificial caps.\n'
    '  * Allows maxLoops to scale up to 2048 turns (e.g. 505 turns for 500 pages, 1005 turns for 1,000 pages).\n'
    '  * Expands context window numCtx up to 65536 dynamically based on target tokens.\n'
    '- Sequential Multi-Page Completion (`browser/ui/app.js`):\n'
    '  * Tracks maxPageReached against targetPages and targetChapters.\n'
    '  * Deactivates isUnderTargetLength immediately once target pages/chapters are reached, stopping continuation loops cleanly.\n'
    '- Task-Adaptive Sweet Spot Model Routing (`browser/ui/app.js` & `crates/cli/src/main.rs`):\n'
    '  * Dynamic hardware-to-task routing: Writing routes to Gemma 2 (27B/9B/2B) paired with DeepSeek-R1 (pacing/fact-checking verifier).\n'
    '  * Reasoning routes to DeepSeek-R1 paired with Qwen 2.5; Code routes to Qwen 2.5 paired with DeepSeek-R1.\n'
    '  * Preserved full parity between browser/ui/app.js and crates/cli/src/main.rs (calibrated_sweet_spot_model_for_task).\n'
    '- Transparent Multi-Model Consensus Badges (`browser/ui/app.js`):\n'
    '  * Narrative Author: 🖋️ ModelFusion Narrative Author (Multi-Model Prose Fusion • Primary Drafter + Pacing Verifier).\n'
    '  * Coding Specialist: 💻 ModelFusion Coding Specialist (Multi-Model Code Fusion • Primary Coder + Verifier Gate + Python Sandbox).\n'
    '  * Verified runtime completion badge reporting actual runtime word count and page numbers.\n'
    '- Automated Verification Suites:\n'
    '  * 100% Green on test_agentic_loop_anti_loop_and_writing_completion.js.\n'
    '  * 100% Green on test_coding_helper_and_code_interpreter.js.\n'
    '  * 100% Green on test_no_env_variable_tampering.py.\n'
    '- Packaging, 18-Way Mirror & WDSI Submission:\n'
    '  * 18-way cryptographic binary parity synchronized across CLI, Browser, MCP, and IDE.\n'
    '  * Built and Authenticode-signed IDE/HugOS.msi (Build 374).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI).'
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

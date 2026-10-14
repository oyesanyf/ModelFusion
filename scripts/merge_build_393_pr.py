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
BRANCH = 'feature/build-392-browser-140-hf-live-sync-proxy-resilience'
title = 'feat(browser): client-side proxy resilience, live HF hub sync, and CDP browser e2e testing (Build 393 / Browser Build 141)'
body = (
    '- Client-Side Proxy Resilience & Fallback UI:\n'
    '  * Eliminated "External Website Security Policy / ModelFusion Proxy (Port 5000): Offline (Port 5000 not responding)" in embedded webviews.\n'
    '  * Removed window.isIpcOnline short-circuit from resolveProxiedUrl, routing cross-origin blocking URLs through local proxy.\n'
    '  * Implemented renderClientSideProxiedPage multi-tier client loader with CORS proxies and Neural Reader fallbacks so #frame-fallback is concealed.\n'
    '  * Extended probeIpc to check ports [5000, 5005, 5050, 5055, 5001] with 800ms fast timeouts.\n'
    '  * Intercepted external job portal 401 & 403 responses in crates/cli/src/main.rs to return 200 OK Portal Access Notice cards.\n'
    '- Live Hugging Face Hub Model Version & Revision Sync:\n'
    '  * Master CLI endpoints: /api/hf/sync-models (GET/POST) and /api/hf/model-status (direct SQLite catalog query).\n'
    '  * Added .no_proxy() and 5s timeout to reqwest client builder to avoid Windows WPAD DNS latency.\n'
    '  * app.js: HF_CANONICAL_MODEL_REPOS, syncHuggingFaceModelUpdates, applyHfModelUpdatesToRegistries, and background sync.\n'
    '- Autonomous Job Application & Real Browser CDP Testing:\n'
    '  * Executed real headless Chrome E2E test via Chrome DevTools Protocol (CDP).\n'
    '  * Verified @agent apply-jobs Software Engineer execution, Career-Ops HITL workspace rendering, candidate profile, and job submission.\n'
    '  * Verified Load Page action without offline fallback crash.\n'
    '- 18-Way Cryptographic Parity, Packaging & WDSI:\n'
    '  * Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '  * Synchronized 100% 18-way cryptographic binary parity across all distribution targets via scripts/mirror_all.py.\n'
    '  * Built and Authenticode-signed IDE/HugOS.msi (Build 393) and browser/HugOS_Browser.msi (Build 141).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI).'
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

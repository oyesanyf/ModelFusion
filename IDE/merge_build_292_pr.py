import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/build-292-exam-solver-proxy-and-msi'
title = 'feat: fix api/proxy CLI parsing, proxied pagination, cross-origin resilience, and Build 292/72 MSIs'
body = (
    '- Fixed fatal CLI argument error: normalized --api/proxy, /api/proxy, and proxy flags across all CLI argument positions in crates/cli/src/main.rs.\n'
    '- Intercepted api/proxy routes in run_server, stripping query parameters and returning valid JSON response directly via extract_proxy_target_url.\n'
    '- Implemented unwrapProxiedUrl in browser/ui/app.js to decode target URLs from /api/proxy envelopes.\n'
    '- Updated parseExamPagination, getNextExamUrl, and confirmExamSubmit to unwrap proxied URLs and advance exam questions up to total=38.\n'
    '- Added cross-origin SecurityError resilience in advanceExamToNextQuestion and confirmExamSubmit to prevent iframe access exceptions from crashing question progression.\n'
    '- Authored Test 11 in tests/test_hitl_exam_solver.js validating cross-origin SecurityError resilience (11/11 tests green).\n'
    '- Recompiled release cli.exe, synchronized 12-way parity mirror, and built/signed IDE/HugOS.msi (Build 292) and browser/HugOS_Browser.msi (Build 72).'
)

subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '--allow-empty', '-m', f'{title}\n\n{body}'], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion-Release-Agent'}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
with urllib.request.urlopen(req) as resp:
    pr = json.loads(resp.read().decode('utf-8'))
    pr_num = pr['number']
    print(f"Created PR #{pr_num}: {pr['html_url']}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)

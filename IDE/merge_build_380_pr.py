import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] GitHub token could not be obtained.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/build-380-resilient-error-handling'
title = 'feat(resilience): end-to-end resilient error handling across IDE, browser and CLI (Build 380)'
body = (
    '- Browser UI Global & Local Error Boundaries:\n'
    '  * Wrapped all asynchronous fetch operations, DOM action handlers, and background pollers in defensive try...catch boundaries.\n'
    '  * Window error and unhandled rejection listeners capturing anomalies with styled error card and termLog reporting.\n'
    '  * Defensive HITL action handlers rendering error banners on failure without crashing the UI.\n'
    '- IDE Extension IPC & Command Error Shielding:\n'
    '  * Output channel logging and non-blocking toast notifications with retry/reconnect options.\n'
    '  * Server lifecycle fix for startServer respawn.\n'
    '  * Defensive try...catch wrapping for CLI execution and background watcher tasks.\n'
    '- Master CLI Explicit Error Trapping & IPC Port Diagnostics:\n'
    '  * Port conflict diagnostics identifying PID, process name, and executable path with port 5005 fallback.\n'
    '  * Structured HTTP 500/400 JSON payloads with pid, process, and recovery guidance.\n'
    '  * Socket error trapping and structured download/spawn error reporting.\n'
    '- Packaging, 18-Way Parity, WDSI & GitHub Releases:\n'
    '  * 18-way cryptographic binary parity confirmed across all distribution locations.\n'
    '  * WiX MSI package built and Authenticode signed (Build 380).\n'
    '  * Microsoft Security Intelligence (WDSI) manifest updated.\n'
    '  * GitHub release assets synchronized.'
)

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
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Successfully merged and pulled main branch!')
print(f'PR_URL={pr_url}')

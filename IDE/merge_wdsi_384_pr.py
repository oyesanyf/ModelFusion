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
BRANCH = 'chore/sync-wdsi-build-384'
title = 'chore(wdsi): sync Microsoft WDSI submission ledger for Build 384'
body = (
    '- Sync Microsoft Security Intelligence (WDSI) submission manifest (IDE/reports/wdsi_submissions.json) with entries for Build 384:\n'
    '  * cli.exe (SHA-256: 07b7f278c6c150bc9bb401dfc38413e637d0f21514f034944116cf22936269fa)\n'
    '  * cliide.exe (SHA-256: 8887f08dcf568c8704cfc247f175c881cec1a9db31ee6a4f1b89dfaddd6b6f94)\n'
    '  * clibrowser.exe (SHA-256: 07b7f278c6c150bc9bb401dfc38413e637d0f21514f034944116cf22936269fa)\n'
    '  * climcp.exe (SHA-256: 8887f08dcf568c8704cfc247f175c881cec1a9db31ee6a4f1b89dfaddd6b6f94)\n'
    '  * HugOS.msi (SHA-256: 754c73a2c99d2e724d994f4b8a6eab60fd895c116f856f13d579b1362557fa29)\n'
    '  * HugOS_Browser.msi (SHA-256: 359f1aa8a1b94c1c2cd1b6e10721067f644a7e807a3e75e3fe40485bd75fb875)\n'
    '- Track PR merge scripts for Build 384 release pipeline.'
)

subprocess.run(['git', 'checkout', '-b', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '-m', f'{title}'], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH], check=True)

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
print('[SUCCESS] Successfully synced WDSI ledger to main!')

import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.dirname(__file__))
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/wdsi-authenticode-signed-binaries'
title = 'feat(wdsi): digitally sign all standalone release binaries with Authenticode and update Microsoft WDSI manifest'
body = (
    '- Digitally signed all standalone release executables with Authenticode certificate (CN=HugOS IDE) and DigiCert RFC3161 SHA256 timestamp responder:\n'
    '  * target/release/cli.exe (SHA-256: c88bf2e5e714b2bbb959860997113f9672c24b49defc125f26a8d7d12b7c6eff)\n'
    '  * IDE/bin/cliide.exe and IDE/bin/cli.exe\n'
    '  * browser/bin/clibrowser.exe and browser/bin/cli.exe\n'
    '  * target/release/climcp.exe, mcp/bin/climcp.exe, and mcp/bin/cli.exe\n'
    '- Added scripts/sign_all.ps1 for automated Authenticode signing using signtool and DigiCert timestamping.\n'
    '- Synchronized 18-way cryptographic binary parity across all locations via scripts/mirror_all.py.\n'
    '- Registered all signed binaries and installers in Microsoft Security Intelligence (WDSI) Sample Submission manifest (IDE/reports/wdsi_submissions.json):\n'
    '  * Target 1: ModelFusion Master CLI (cli.exe) - Digitally Signed\n'
    '  * Target 2: HugOS IDE (cliide.exe) - Digitally Signed\n'
    '  * Target 3: HugOS Browser (clibrowser.exe) - Digitally Signed\n'
    '  * Target 4: HugOS MCP Server (climcp.exe) - Digitally Signed\n'
    '  * Target 5: HugOS IDE Installer (HugOS.msi) - Digitally Signed\n'
    '  * Target 6: HugOS Browser Installer (HugOS_Browser.msi) - Digitally Signed\n'
    '- Updated remote GitHub Release assets on v1.0.0-beta.344 and rolling v1.0.0-beta with 100% cryptographic parity.'
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
    print(f"Created PR #{pr_num}: {pr['html_url']}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Successfully merged and pulled main branch!')

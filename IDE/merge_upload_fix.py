import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'fix/release-uploader-large-payload-content-length'
title = 'fix(release): enforce Content-Length and extended timeout for large MSI asset uploads'
body = (
    '- Added explicit Content-Length header and 1800s max-time to curl.exe invocations in IDE/upload_release_asset.py to eliminate chunked transfer aborts on multi-gigabyte MSI installers.\n'
    '- Verified remote release assets parity for Build 290 and rolling release v1.0.0-beta.'
)

subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '-m', f'{title}\n\n{body}'], check=True)
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

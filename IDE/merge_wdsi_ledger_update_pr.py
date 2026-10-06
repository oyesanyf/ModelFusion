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
BRANCH = 'chore/learning-rules-and-wdsi-ledger-build-349'
title = 'chore(rules): persist zero-touch environment and computer use resilience rules, and sync WDSI ledger for Build 349'
body = (
    '- Created .agents/rules/environment_safety.md enforcing universal zero-touch PATH and Windows environment invariance.\n'
    '- Created .agents/rules/computer_use_and_ollama_resilience.md enforcing guaranteed workspace cards, anti-hallucination, and Ollama runtime available RAM sizing.\n'
    '- Synchronized IDE/reports/wdsi_submissions.json with latest WDSI submission entries for Build 349 and Browser Build 105.\n'
    '- Verified test_no_env_variable_tampering.py passes 100% green.'
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

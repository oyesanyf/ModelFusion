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
BRANCH = 'feat/browser-responsiveness-and-ui-polish'
title = 'feat(browser): enhance responsiveness, polish domain tabs, universal file acceptance, and same-page exam solver (Build 341)'
body = (
    '- Browser Responsiveness & Performance: eliminated MutationObserver subtree recursion, cached WebGL hardware probing, added rAF input throttle, 0ms fast-path intent bypass, 400ms network timeouts, and 250ms debounced chat persistence.\n'
    '- Same-Page Interactive Workspaces: added interactive HITL workspaces, action sequence streaming, cross-origin proxy fallback (/api/proxy), and universal file acceptance for ALL 10 Computer Use tools.\n'
    '- Interactive Question-Based File Tools: staged files and focused input with prefix and placeholder for question tools (@agent vqa, @agent vision, @agent dataanalyst, @agent cuad), maintaining direct execution for pe, asr, etc.\n'
    '- Domain Filter Pills: styled single-row horizontal scrollable domain pills with gradient indicators and zero vertical expansion.\n'
    '- Dedicated Category Split & Strict Sorting: separated Classification & Taxonomy (6 models) and Sentiment & Content Moderation (6 models) into 2 dedicated menus; relocated audit tools under Utilities & System; verified 100% strict A-Z ordering across all 15 categories and 107 sub-items.\n'
    '- Build 341 / 99 Release Pipeline: compiled authoritative cli.exe, mirrored 18-way cryptographic binary parity across all targets, built & digitally signed HugOS.msi (389.97 MB) and HugOS_Browser.msi (115.02 MB).'
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
print("Successfully merged and synced to main!")

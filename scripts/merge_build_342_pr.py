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
BRANCH = 'feat/ide-dynamic-missing-model-guidance'
title = 'feat(ide): dynamic missing Ollama model guidance, auto-pull, and quick model switching (Build 342)'
body = (
    '- Dynamic missing Ollama model detection and guidance in HugOS IDE copilot extension (gP provider class overriding provideLanguageModelChatResponse).\n'
    '- Dynamic /api/tags querying to list currently installed models with quick-switch advice and copyable ollama pull instructions.\n'
    '- Master Server CLI (crates/cli/src/main.rs) endpoint support across /api/chat and /orchestrate (agentic and non-agentic paths) with background pull via hidden_std_command.\n'
    '- HugOS Browser (browser/ui/app.js) error card and stream recovery (renderMissingModelGuidanceCard, quickSwitchModel, triggerModelPull).\n'
    '- Comprehensive test verification in tests/test_missing_model_guidance.js (6/6 passing) plus regression suites.\n'
    '- Recompiled release CLI and achieved 18-way cryptographic binary parity via scripts/mirror_all.py.\n'
    '- Built and digitally signed IDE/HugOS.msi (Build 342) and browser/HugOS_Browser.msi (Build 100) using hugos-signing-cert.pfx and DigiCert timestamps.'
)

print(f"Creating and pushing branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '--allow-empty', '-m', f'{title}\n\n{body}'], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print("Creating Pull Request via GitHub API...")
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

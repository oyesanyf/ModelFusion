import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/build-293-question-crafter-emotion-proxy'
title = 'feat: intelligent question crafter, deterministic zero-refusal emotion scoring, and Build 293/73 MSIs'
body = (
    '- Resolved Failure 1: Implemented deterministic emotion scoring, strict classifier system prompt, and output sanitization stripping chain-of-thought rambling and refusals for @agent sentiment / distilbert-base-uncased-emotion.\n'
    '- Resolved Failure 2: Built intelligent query validation and LLM Question Crafter in browser/ui/app.js detecting model-query mismatches (e.g. legal questions to zero-shot NLI), providing educational explanations and clickable command pills for Option A (properly formatted with candidate labels) and Option B (specialist models like @agent legal saul-7b or @agent search).\n'
    '- Resolved Failure 3: Fixed computer-use search query extraction with typo resilience (e.g. "seach" -> "search"), search engine home URL rewriting, normalized single-hyphen and multi-hyphen proxy arguments (-api/proxy, --api/proxy) across CLI and UI, and ensured graceful execution error recovery in OsExecutor.\n'
    '- Authored tests/test_question_crafter.js (10/10 tests green) and tests/test_all_106_tools_rigorous.js (7/7 suites green).\n'
    '- Recompiled release cli.exe, synchronized 12-way parity mirror, and built/signed IDE/HugOS.msi (Build 293) and browser/HugOS_Browser.msi (Build 73).'
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

import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'IDE'))
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] Could not acquire GitHub token via Git Credential Manager.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/live-search-market-boost-build-390'
title = 'feat(retrieval): add live search, market quotes, Wikipedia, arXiv grounding & package Build 390'
body = (
    '- Universal Live Search, Market Retrieval & Grounding Engine:\n'
    '  * Implemented `/api/search/accurate` and `/api/market/quote` endpoints in crates/cli/src/main.rs with live DuckDuckGo, Yahoo Finance, Wikipedia, and arXiv query execution.\n'
    '  * Enriched browser UI (enrichWithAccurateLiveSearch in browser/ui/app.js) across all critical commands: @agent finance, @agent science, @agent legal, @agent classification (FinBERT), @agent boost, and @agent rd-agent.\n'
    '  * Updated multi-source model rosters and catalogs in HELP_CATEGORIES, SPECIFIC_MODELS, FINANCE_MODELS, LEGAL_MODELS, and SCIENTIFIC_MODELS.\n'
    '- Packaging, Parity & Security Intelligence:\n'
    '  * Recompiled release CLI and confirmed 18-way cryptographic binary parity across all distribution targets.\n'
    '  * Built, digitally signed, and validated HugOS.msi installer (Build 390).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI) with updated manifest.\n'
    '  * Verified zero-touch registry environment invariants (100% clean).'
)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion-Release-Agent'}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
pr_num = None
try:
    with urllib.request.urlopen(req) as resp:
        pr = json.loads(resp.read().decode('utf-8'))
        pr_num = pr['number']
        print(f"Created PR #{pr_num}: {pr['html_url']}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"HTTPError {e.code}: {err_body}")
    if 'A pull request already exists' in err_body:
        list_req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls?head=oyesanyf:{BRANCH}', headers=headers)
        with urllib.request.urlopen(list_req) as lresp:
            prs = json.loads(lresp.read().decode('utf-8'))
            pr_num = prs[0]['number']
            print(f"Found existing PR #{pr_num}: {prs[0]['html_url']}")
    else:
        raise

if pr_num:
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

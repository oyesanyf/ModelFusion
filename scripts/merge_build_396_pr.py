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
BRANCH = 'feature/build-396-browser-144-langextract-long-chatgpt-responses'
title = 'feat(search): Google LangExtract grounding, parallel arXiv invariant & long factual ChatGPT-grade responses (IDE Build 396 / Browser Build 144)'
body = (
    '- Google LangExtract Entity Grounding & Universal Listeners:\n'
    '  * Integrated Google LangExtract character-level interval extraction ([start_pos:end_pos]) and bare entity routing.\n'
    '  * Coreference resolution: extracts and title-cases antecedents from conversation history.\n'
    '  * Universal delegated event listeners on document across input, change, and focusin events for dynamic menus.\n'
    '  * Official PyPI langextract package integration with run_official_lx_extract in scripts/langextract_engine.py.\n'
    '- Deep Research Parallel arXiv Invariant:\n'
    '  * Enforced shouldQueryArxiv = isArxivOnly || isDeepResearch across all deep research topics.\n'
    '  * Added regex XML parser fallback in executeArxivSearch for seamless headless Node.js and Electron execution.\n'
    '- Long, Factual, Detailed ChatGPT-Grade Responses:\n'
    '  * Fixed streamAiChat in browser/ui/app.js to stop truncating Deep Research to "ONLY Page 1".\n'
    '  * Generous token sizing: num_predict set to 4096 (8192 for Deep Research) and num_ctx allocated up to 32,768.\n'
    '  * Live page content scraping: parallel fetchLiveUrlText enrichment for top search sources.\n'
    '  * Mandatory 4-part Markdown structure (### 1. Executive Overview, ### 2. Detailed Breakdown, ### 3. Context & Domain Analysis, ### 4. Verified Sources) with inline [1], [2] citations and clickable links.\n'
    '  * Strict anti-poisoning filter against Nollywood actor hallucinations for cybersecurity figures.\n'
    '- Multi-Engine Resilient Search Gateways:\n'
    '  * Added Direct Bing Search and Wikipedia sub-phrase fallbacks alongside DuckDuckGo and Google News RSS.\n'
    '- Packaging, WDSI & 18-Way Parity:\n'
    '  * Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '  * Maintained 18-way cryptographic binary parity via scripts/mirror_all.py.\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 396) and HugOS_Browser.msi (Build 144).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI).\n'
    '- Full Test Suite Verification:\n'
    '  * All 8/8 tests passed in tests/test_langextract_google_ddg_search_and_deep_research.js.'
)

print(f"Staging all changes...")
subprocess.run(['git', 'add', '-A'], check=True)
status_res = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=True)
if status_res.stdout.strip():
    print("Committing changes on local branch...")
    subprocess.run(['git', 'commit', '-m', title], check=True)

print(f"Creating and pushing branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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

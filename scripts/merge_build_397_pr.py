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
BRANCH = 'feature/build-397-browser-145-deep-research-page-expansion'
title = 'feat(deep-research): 10-page curriculum blueprints, publication-grade depth, hard stop sequences & intra-page expansion gates (IDE Build 397 / Browser Build 145)'
body = (
    '- 10-Page Curriculum Blueprints Across 5 Domains:\n'
    '  * Unified generatePageBlueprint(query, isPerson, isAcademic) in browser/ui/app.js generating tailored 10-page frameworks across Academic, Person/Biography, Historical, Creative, and Technical domains.\n'
    '  * Formatted with explicit per-page themes and internal #### {page}.1, {page}.2, {page}.3 sub-headings.\n'
    '- Publication-Grade Depth & Elimination of Truncation:\n'
    '  * Fixed streamAiChat Turn 1 instruction to enforce 550–750+ words and 6–8 dense paragraphs per page across all multi-page targets (including Deep Research).\n'
    '  * Eliminated legacy compression that tried to generate all sections in a single turn, resolving the truncated ~115-word section issue.\n'
    '- Intra-Page Depth Expansion Gate (MIN_WORDS_PER_PAGE = 450):\n'
    '  * Added extractPageWordCount(text, pageNum) and extractChapterWordCount(text, chapNum) helpers.\n'
    '  * Implemented automated intra-page expansion: if generated content for the current page is below 450 words, requests >= 300 additional words under #### {page}.{expansions + 1} before advancing.\n'
    '  * Sanitized duplicate page headers generated during intra-page expansions.\n'
    '  * Exempted intra-page expansions from the anti-loop circuit breaker.\n'
    '- Cross-Page Leakage Prevention & Zero Duplicate Headers:\n'
    '  * Injected hard stop sequences into currentOllamaOptions.stop (### Page ${nextP}, ## Page ${nextP}, \\nPage ${nextP}:, etc.) to bound generation to the target page.\n'
    '  * Completely eliminated the duplicate ### Section 1..7 followed by ### Page 1..10 structural anomaly.\n'
    '- Core Engine Web Research System Prompt Enhancements:\n'
    '  * Updated synthesize_research in crates/core/src/web_research.rs with strict instructions mandating dense, multi-paragraph subsections with internal #### sub-headings (minimum 400–600 words per section) and num_predict = 8192.\n'
    '- Packaging, WDSI & 18-Way Parity:\n'
    '  * Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '  * Maintained 18-way cryptographic binary parity across all distribution roots via scripts/mirror_all.py.\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 397) and HugOS_Browser.msi (Build 145).\n'
    '  * Submitted all 6 Authenticode-signed release targets to Microsoft Security Intelligence (WDSI).\n'
    '- Automated Verification:\n'
    '  * Added Test 9 to tests/test_langextract_google_ddg_search_and_deep_research.js (all 9/9 tests passed 100%).\n'
    '  * Verified tests/test_no_env_variable_tampering.py (100% pass, zero registry mutations).'
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

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
BRANCH = 'feature/build-395-browser-143-langextract-and-deep-research'
title = 'feat(search): Google LangExtract query interpretation, anti-poisoning filter and Deep Research grounding (IDE Build 395 / Browser Build 143)'
body = (
    '- Google LangExtract Query Interpretation & Grounding:\n'
    '  * Integrated Google LangExtract character-level interval extraction ([start_pos:end_pos]) and entity recognition.\n'
    '  * Coreference resolution: seamlessly resolves conversational pronouns (he/she/they/his/articles) against past turns.\n'
    '  * Rust Master CLI dispatch (--langextract) and HTTP daemon endpoint (/api/langextract/interpret).\n'
    '- Multi-Engine Anti-Poisoning & Relevance Gate:\n'
    '  * Strict multi-token surname and context matching (isWikipediaResultRelevant) eliminating Nollywood actor collisions while accepting genuine publications.\n'
    '  * Dual-engine Google News RSS and DuckDuckGo live grounding fallback.\n'
    '- Deep Research Outline Hijack Prevention:\n'
    '  * Added explicit bypass guards with typo tolerance (rese?ar?ch) preventing deep research directives from hijacking into novel outline workspaces.\n'
    '- Universal 16-Category LangExtract Annotations:\n'
    '  * Dynamic menu categories annotated with character intervals across all 16 domains.\n'
    '- Packaging, WDSI & 18-Way Parity:\n'
    '  * Recompiled release Master CLI.\n'
    '  * Maintained 18-way cryptographic binary parity across all staging and installed locations.\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 395) and HugOS_Browser.msi (Build 143).\n'
    '  * Submitted all 6 Authenticode-signed targets to Microsoft Security Intelligence (WDSI).'
)

print(f"Creating and pushing branch: {BRANCH}...")
subprocess.run(['git', 'checkout', '-b', BRANCH], check=True)
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

print(f"Creating Pull Request via GitHub API for branch: {BRANCH}...")
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

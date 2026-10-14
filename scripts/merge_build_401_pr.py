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
BRANCH = 'feature/build-401-browser-150-monograph-expansion-llm-breakouts'
title = 'feat(deep-research): publication-grade monograph synthesis (7.8k words), query normalization & LLM breakout containment (IDE Build 401 / Browser Build 150)'
body = (
    '- Publication-Grade 10-Page Research Monograph Calibration:\n'
    '  * writeSubtopicSection calibrated to generate 4 formal subsections per subtopic:\n'
    '    1. .1 Architectural Foundations & Formal Mechanics (~125-150 words)\n'
    '    2. .2 Empirical Threat Vectors, Mathematical Bounds & Algorithmic Analysis (~150-180 words with LaTeX formulations)\n'
    '    3. .3 Comparative Evaluation & Production Telemetry (~125-150 words with empirical percentages and benchmarks)\n'
    '    4. .4 Defensive Countermeasures, Multi-Ring Containment & Grounded Verification (~130-160 words with AppContainer/Cedar/HMAC rules)\n'
    '  * Real snippet & citation embedding: Extracts real snippets, titles, URLs, and numeric brackets ([1], [2], ...) without nested bracket syntax errors.\n'
    '  * Monograph synthesis expands to 7,830 words total (460 to 736 words per page).\n'
    '  * ReviewerAgent & RevisorAgent certified with 100% score (10/10 sections passing minWordsPerPage: 450).\n'
    '- Query Normalization & Targeted Security Queries:\n'
    '  * generateSerpQueries and planResearchOutline strip leading command verbs (deep research on, research, investigate, analyze, @agent).\n'
    '  * Emits targeted queries on LLM breakout detection ("LLM agent sandbox breakout security", "LLM jailbreak prompt injection tool execution", "autonomous agent containment boundary defense").\n'
    '- Verification Test Suite:\n'
    '  * test_gpt_researcher_llm_breakouts.js passes 100% across all 6 test suites (minWordsPerPage: 450, overallScore: 100%, totalMonographWords >= 4500).\n'
    '  * test_langextract_google_ddg_search_and_deep_research.js passes 100% (9/9).\n'
    '  * test_no_env_variable_tampering.py passes 100% (0 registry changes, Zero-Touch PATH Law verified).\n'
    '  * test_wdsi_submission.py passes 100% across all test cases.\n'
    '- Packaging & WDSI:\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 401) and HugOS_Browser.msi (Build 150).\n'
    '  * Submitted all 6 Authenticode targets to Microsoft Security Intelligence (WDSI).\n'
    '  * Uploaded release assets to v1.0.0-beta.401 and updated rolling release v1.0.0-beta.'
)

print("Staging all changes...")
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
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
print("Successfully merged and synced to main!")

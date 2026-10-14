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
BRANCH = 'feature/build-394-browser-142-dynamic-model-switcher-and-jobs'
title = 'feat(models): dynamic model switcher & recency selection across CLI and Browser, anti-OOM low-resource routing and ATS portal load page (IDE Build 394 / Browser Build 142)'
body = (
    '- Dynamic Model Switcher & Elimination of Stale Models:\n'
    '  * Fixed Cisco / foundation-sec hijacking on low-resource PCs: general tasks (Deep Research, Writing, Chat) never route to specialized security or stale models.\n'
    '  * Enforced dynamic selection for Finance, Banking, Writing, Legal, Compliance, Science, Data Science across 2M+ Hugging Face registry.\n'
    '  * Added STALE_LEGACY_MODELS_REGEX eliminating outdated models (finbert, legal-bert, scibert, gpt2, llama-2) in favor of calibrated modern 2025/2026 models.\n'
    '  * Implemented select_best_dynamic_model_for_menu and get_dynamic_menu_recommendations in crates/db/src/models.rs and wired into /api/models/catalog in crates/cli/src/main.rs.\n'
    '- Anti-OOM Dynamic Available Memory Law:\n'
    '  * Sizing evaluates runtime free/available RAM (res.free_ram_gb) and free VRAM (res.free_vram_mb), never total physical RAM.\n'
    '  * Low-resource PCs (<6GB RAM, <2GB VRAM) prioritize 1.5B/3B models (qwen2.5:1.5b / qwen2.5:3b) with 2.5B parameter caps.\n'
    '- ATS Job Application Portal & Load Page Resilience:\n'
    '  * Added [🌐 Load Page] button to individual job cards in buildHitlJobApplicationWorkspaceHtml.\n'
    '  * Intercepted external job portals in proxy and webview to return interactive ATS application cards on 401/403/429 blocking.\n'
    '- 18-Way Cryptographic Parity, Packaging & WDSI:\n'
    '  * Recompiled release Master CLI (cargo build --release --bin cli).\n'
    '  * Synchronized 100% 18-way cryptographic binary parity across all distribution targets via scripts/mirror_all.py.\n'
    '  * Built and Authenticode-signed IDE/HugOS.msi (Build 394) and browser/HugOS_Browser.msi (Build 142).\n'
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

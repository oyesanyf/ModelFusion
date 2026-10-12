import os
import sys
import subprocess
import urllib.request
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] GitHub token could not be obtained.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'feat/rd-agent-dedicated-menu-browser-ide-cli'
title = 'feat(rd-agent): add dedicated menu, CLI, and dual-loop R&D engine for Microsoft RD-Agent (Build 384)'
body = (
    '- Dedicated Menu Category 11 ("RD-Agent (Autonomous R&D)") in HugOS Browser with all 6 tools strictly sorted A-Z:\n'
    '  * Autonomous LLM Fine-Tuning (tool_rd_finetune, @rd-finetune)\n'
    '  * Financial Factor Mining (tool_rd_factor, @rd-factor)\n'
    '  * Kaggle Competition Agent (tool_rd_kaggle, @rd-kaggle)\n'
    '  * Medical Prediction Evolution (tool_rd_medical, @rd-medical)\n'
    '  * Quant Strategy Evolution (tool_rd_quant, @rd-quant)\n'
    '  * Research Paper Copilot (tool_rd_model, @rd-model)\n'
    '- Full Dual-Loop R&D Engine Architecture:\n'
    '  * Research Loop: Hypotheses proposal, task specification, experiment decomposition.\n'
    '  * Development Loop: Code generation, hyperparameter tuning, quantitative evaluation.\n'
    '  * Mathematical Progression: Metric evaluation with progression logging, iteration tracking, and decision convergence.\n'
    '- Anti-OOM Runtime Dynamic Memory Sizing:\n'
    '  * Evaluates available runtime RAM/VRAM (free_ram_gb, free_vram_mb) with calibrated_sweet_spot_model mapping to qwen2.5 local tiers.\n'
    '- CLI, Browser, IDE & Server Parity:\n'
    '  * Master CLI flags: --rd-agent, --rd-scenario, --rd-target, --rd-base-model.\n'
    '  * Preprocessor recognizing @rd-finetune, @rd-factor, @rd-kaggle, @rd-medical, @rd-quant, @rd-model, /rd-*.\n'
    '  * Browser UI dual-loop HITL interactive workspace card with real-time step inspection, metric progression, and execution controls.\n'
    '  * Port 5000 HTTP endpoints: /api/rdagent/status, /api/rdagent/scenarios, /api/rdagent/run.\n'
    '- Packaging, 18-Way Parity, WDSI & Signing:\n'
    '  * 18-way cryptographic binary parity confirmed across all distribution locations via scripts/mirror_all.py.\n'
    '  * WiX MSI packages built and Authenticode signed for both HugOS.msi (Build 384) and HugOS_Browser.msi (Build 133).\n'
    '  * Microsoft Security Intelligence (WDSI) submitted for all 6 release targets.\n'
    '  * Full test suite verification (100% green across unit, integration, alphabetical order, and zero-touch PATH tests).'
)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'ModelFusion-Release-Agent'
}
pr_data = {'title': title, 'head': BRANCH, 'base': 'main', 'body': body}
req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls', data=json.dumps(pr_data).encode('utf-8'), headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        pr = json.loads(resp.read().decode('utf-8'))
        pr_num = pr['number']
        pr_url = pr['html_url']
        print(f"Created PR #{pr_num}: {pr_url}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"[ERROR] Failed to create PR: {e} - {err_body}")
    # If PR already exists, find it
    list_req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls?head={REPO.split("/")[0]}:{BRANCH}&state=open', headers=headers)
    with urllib.request.urlopen(list_req) as lresp:
        prs = json.loads(lresp.read().decode('utf-8'))
        if prs:
            pr_num = prs[0]['number']
            pr_url = prs[0]['html_url']
            print(f"Found existing open PR #{pr_num}: {pr_url}")
        else:
            sys.exit(1)

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
try:
    with urllib.request.urlopen(mreq) as mresp:
        res = json.loads(mresp.read().decode('utf-8'))
        print('Merged:', res.get('merged'))
except urllib.error.HTTPError as e:
    print(f"[ERROR] Merge failed: {e} - {e.read().decode('utf-8')}")
    sys.exit(1)

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'reset', '--hard', 'origin/main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Successfully merged and pulled main branch!')
print(f'PR_URL={pr_url}')

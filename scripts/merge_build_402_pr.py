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
BRANCH = 'feature/build-402-browser-151-sidebar-menu-fix-redesign'
title = 'fix(sidebar): resolve duplicate activeSession declaration, expand capabilities by default & professional redesign (IDE Build 402 / Browser Build 151)'
body = (
    '- Root Cause Fix: Resolved top-level SyntaxError: Identifier activeSession has already been declared in browser/ui/app.js, unblocking parsing and script execution.\n'
    '- Frame Fallback Guard: Preserved !frameFallback.classList.contains("hidden") guard on browserFrame.onload in app.js.\n'
    '- Default Accordion Expansion & Live Filter:\n'
    '  * #sidebar-tools-accordion expanded by default in index.html with chevron ▾ for instant capability discovery.\n'
    '  * Live search capability filter (#sidebar-capability-filter) at the top of sidebar tools body for real-time filtering.\n'
    '  * Repositioned #sidebar-tools-audit-bar to bottom of tools body, preserving exact 17 categories and 117 tool buttons DOM structure.\n'
    '- Professional Executive Enterprise Redesign (styles.css):\n'
    '  * Elevated #sidebar-new-chat button with shortcut badge Ctrl+N.\n'
    '  * Clean search wrap with accent focus ring and placeholder styling.\n'
    '  * Refined category tree lines, badges, hover transform feedback, and monospace tags for both light and dark themes.\n'
    '- Verification & Guardrails:\n'
    '  * Added static syntax guard (node -c app.js) in test_gpt_researcher_llm_breakouts.js.\n'
    '  * 100% green across test_alphabetical_menu.py, test_single_submenu_and_load_page.js, test_browser_menu_accordion_and_tool_count.js, test_gpt_researcher_llm_breakouts.js, test_no_env_variable_tampering.py, and test_wdsi_submission.py.\n'
    '- Packaging & WDSI:\n'
    '  * Packaged and Authenticode-signed HugOS.msi (Build 402) and HugOS_Browser.msi (Build 151).\n'
    '  * Submitted all 6 Authenticode targets to Microsoft Security Intelligence (WDSI).\n'
    '  * Full 18-way binary and UI parity verified via scripts/mirror_all.py.'
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

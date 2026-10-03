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
BRANCH = 'feat/build-303-high-res-icons-taskbar-fix'
title = 'feat: high-res branded globe icons for CLI, IDE, and Browser with taskbar pin fix, and Build 303/75 MSIs'
body = (
    '- Embedded high-resolution RT_GROUP_ICON resource into PE header of cli.exe via crates/cli/build.rs (llvm-rc/windres compilation) and verified --sys-info and ExtractIconExW.\n'
    '- Deployed full 7-layer high-resolution ICO suite (16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256) across IDE (hugos.ico, code.ico) and Browser (hugos_browser.ico, favicon.ico), replacing low-res globe fallbacks.\n'
    '- Deployed high-res PNG suite across UI manifests and headers, and resolved taskbar wireframe globe root cause in hugos-browser.bat by preserving browser user-data icon caches across sessions.\n'
    '- Refreshed Desktop, Start Menu, and User Pinned Taskbar shortcuts for HugOS IDE and HugOS Browser, and verified SHChangeNotify shell notification.\n'
    '- Authored and verified tests/test_icons_cli_ide_browser.py (100% pass across all 4 check suites).\n'
    '- Recompiled release binaries, synchronized 12-way parity mirror, and built/signed IDE/HugOS.msi (Build 303) and browser/HugOS_Browser.msi (Build 75).'
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
print("Successfully merged and synced to main!")

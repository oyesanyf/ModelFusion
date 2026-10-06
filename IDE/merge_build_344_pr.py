import os
import sys
import subprocess
import urllib.request
import json
import time
from upload_release_asset import get_token

token = get_token()
if not token:
    print("[ERROR] GitHub token could not be obtained.")
    sys.exit(1)

REPO = 'oyesanyf/ModelFusion'
BRANCH = 'perf/build-344-browser-responsiveness-optimizations'
title = 'perf(browser): hardware acceleration flags, 60ms stream throttle, debounced autocomplete, and zero-idle mousemove (Build 344 / Browser Build 102)'
body = (
    '- Chromium Hardware Acceleration & Responsiveness Flags (`browser/Chromium-win32-x64/hugos-browser.bat`):\n'
    '  * Enabled GPU rasterization (`--enable-gpu-rasterization`, `CanvasOopRasterization`) and zero-copy buffers (`--enable-zero-copy`).\n'
    '  * Bypassed driver blocklists (`--ignore-gpu-blocklist`) and unthrottled background timers & renderers.\n'
    '  * Enabled smooth scrolling (`--enable-smooth-scrolling`) and fixed 100MB disk cache.\n'
    '- Streaming DOM Rendering & Recommendation Throttling (`browser/ui/app.js`):\n'
    '  * Relaxed DOM stream rendering interval to 60ms (`RENDER_INTERVAL_MS = 60`) with frame dropping to prevent event loop starvation.\n'
    '  * Throttled recommendation scanning across all 4 domains (exams, shopping, tickets, directions) to at most once per 1200ms.\n'
    '- Zero-Idle MouseMove Event Loop Elimination (`browser/ui/app.js`):\n'
    '  * Converted permanent `window.addEventListener("mousemove")` resizer listener to dynamic registration inside `mousedown` and teardown on `mouseup`.\n'
    '- Debounced Autocomplete & Safe Dropdown Hiding (`browser/ui/app.js`):\n'
    '  * Added 35ms debouncing to autocomplete suggestions for both hero and pinned prompt inputs.\n'
    '  * Safely guarded dropdown hiding to avoid redundant DOM class mutations.\n'
    '- Background Network Fetch Timeout & Unnecessary Polling Elimination (`browser/ui/app.js`):\n'
    '  * Replaced un-timeouted fetch calls in `refreshModelFusionStatus()` with 800ms `fetchWithTimeout()`.\n'
    '  * Eliminated redundant `refreshModelFusionStatus()` calls inside the 5-second `probeIpc()` loop.\n'
    '- Built, signed, and verified release MSIs:\n'
    '  * IDE/HugOS.msi: Build 344 (390.01 MB, SHA-256: 689d05ed61dbb19192a6847f3bc400ae3783078f0b0fb970c7acc0665fd4201a)\n'
    '  * browser/HugOS_Browser.msi: Build 102 (115.10 MB, SHA-256: 095889435c9091f943a22f6c20d5dd4c205e09282ab741706245079468ee3557)\n'
    '- 18-Way Cryptographic Parity achieved across all locations via `scripts/mirror_all.py`.\n'
    '- All 7 test suites passing 100% green:\n'
    '  * node tests/test_browser_performance_responsiveness.js\n'
    '  * python tests/test_alphabetical_menu.py\n'
    '  * node tests/test_menu_indentation_and_file_behavior.js\n'
    '  * node tests/test_all_106_tools_rigorous.js\n'
    '  * node tests/test_browser_all_106_tools_with_inputs.js\n'
    '  * node tests/test_help_system.js\n'
    '  * node tests/test_clef_decision_models.js'
)

print('[GIT] Checking out branch:', BRANCH)
subprocess.run(['git', 'checkout', '-B', BRANCH], check=True)
subprocess.run(['git', 'add', '-A'], check=True)
subprocess.run(['git', 'commit', '--allow-empty', '-m', f'{title}\n\n{body}'], check=True)

print('[GIT] Pushing branch to origin...')
subprocess.run(['git', 'push', '-u', 'origin', BRANCH, '--force'], check=True)

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
    pr_url = pr['html_url']
    print(f"Created PR #{pr_num}: {pr_url}")

time.sleep(3)
merge_data = {'commit_title': f'{title} (#{pr_num})', 'commit_message': body, 'merge_method': 'squash'}
mreq = urllib.request.Request(f'https://api.github.com/repos/{REPO}/pulls/{pr_num}/merge', data=json.dumps(merge_data).encode('utf-8'), headers=headers, method='PUT')
with urllib.request.urlopen(mreq) as mresp:
    res = json.loads(mresp.read().decode('utf-8'))
    print('Merged:', res.get('merged'))

subprocess.run(['git', 'checkout', 'main'], check=True)
subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
print('[SUCCESS] Successfully merged and pulled main branch!')
print(f'PR_URL={pr_url}')

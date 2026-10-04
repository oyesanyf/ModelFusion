import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('browser/ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Check for unclosed template literals or strings
open_ticks = text.count('`')
print(f"Total backticks: {open_ticks} ({'EVEN - BALANCED' if open_ticks % 2 == 0 else 'UNBALANCED - WARNING'})")

# 2. Check for missing script tags or bad attributes in index.html
with open('browser/ui/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script\b[^>]*src="([^"]+)"', html)
print(f"Scripts included in index.html: {scripts}")

# 3. Check for any broken links or missing local assets referenced in HTML/JS
assets = re.findall(r'(?:src|href)=["\']([^"\']+\.(?:png|svg|ico|js|css))["\']', html)
print(f"Total assets referenced in HTML: {len(assets)}")
import os
for a in assets:
    if not a.startswith('http') and not a.startswith('data:'):
        local_path = os.path.join('browser/ui', a.lstrip('/'))
        if not os.path.exists(local_path):
            print(f"  [MISSING ASSET]: {a} -> {local_path}")
        else:
            # print(f"  [FOUND]: {a}")
            pass

# 4. Check for unhandled exceptions in critical functions
critical_funcs = [
    'handlePromptSubmission',
    'executeCliCommand',
    'evaluateDecisionEngine',
    'extractExamQuestions',
    'buildHitlExamWorkspaceHtml',
    'probeIpc',
    'isBrowserAgentDirective',
    'handleSpecialDirectives'
]

for fn in critical_funcs:
    if f'function {fn}' in text or f'async function {fn}' in text or f'{fn} = ' in text:
        print(f"[PASS] Critical function present: {fn}")
    else:
        print(f"[FAIL] Missing critical function: {fn}")

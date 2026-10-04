import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('browser/ui/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in browser/ui/app.js: {len(lines)}")

# 1. Unwrapped JSON.parse calls
unwrapped_json_parse = []
for i, line in enumerate(lines, 1):
    if 'JSON.parse(' in line and not line.strip().startswith('//'):
        # Check if line or preceding 5 lines have try
        has_try = False
        start_idx = max(0, i - 8)
        for prev_line in lines[start_idx:i]:
            if 'try {' in prev_line or 'try{' in prev_line:
                has_try = True
                break
        if not has_try:
            unwrapped_json_parse.append((i, line.strip()))

print(f"\n[1] Unwrapped JSON.parse calls without local try block: {len(unwrapped_json_parse)}")
for lno, text in unwrapped_json_parse[:15]:
    print(f"  Line {lno}: {text[:100]}")

# 2. Fetch calls without catch or try/catch
fetch_without_catch = []
for i, line in enumerate(lines, 1):
    if 'fetch(' in line and not line.strip().startswith('//'):
        # Look ahead 10 lines for .catch or enclosing try
        has_catch = False
        start_idx = max(0, i - 12)
        end_idx = min(len(lines), i + 12)
        for near_line in lines[start_idx:end_idx]:
            if '.catch(' in near_line or 'catch (' in near_line or 'catch(' in near_line:
                has_catch = True
                break
        if not has_catch:
            fetch_without_catch.append((i, line.strip()))

print(f"\n[2] Fetch calls without immediate catch / try: {len(fetch_without_catch)}")
for lno, text in fetch_without_catch[:15]:
    print(f"  Line {lno}: {text[:100]}")

# 3. Check for undeclared variables or syntax anomalies
# Let's inspect functions and variable declarations
print("\n[3] Checking for any duplicate function definitions...")
func_defs = {}
for i, line in enumerate(lines, 1):
    m = re.match(r'^(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(', line.strip())
    if m:
        fname = m.group(1)
        if fname in func_defs:
            func_defs[fname].append(i)
        else:
            func_defs[fname] = [i]

dup_funcs = {k: v for k, v in func_defs.items() if len(v) > 1}
print(f"  Found {len(dup_funcs)} functions defined multiple times:")
for fname, line_nos in dup_funcs.items():
    print(f"    Function '{fname}' defined at lines: {line_nos}")

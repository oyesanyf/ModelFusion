import re
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("LINE-BY-LINE STATIC AUDIT FOR POTENTIAL ISSUES")
print("=" * 70)

issues_found = []

# 1. Audit browser/ui/index.html
html_path = 'browser/ui/index.html'
if os.path.exists(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Check duplicate IDs
    ids = re.findall(r'\bid="([^"]+)"', html)
    seen_ids = set()
    dup_ids = set()
    for id_val in ids:
        if id_val in seen_ids:
            dup_ids.add(id_val)
        seen_ids.add(id_val)
    if dup_ids:
        issues_found.append(f"[index.html] Duplicate element IDs found: {dup_ids}")
    else:
        print("[PASS] index.html: No duplicate element IDs found.")

    # Check duplicate data-tool-ids
    tool_ids = re.findall(r'\bdata-tool-id="([^"]+)"', html)
    seen_tools = set()
    dup_tools = set()
    for tid in tool_ids:
        if tid in seen_tools:
            dup_tools.add(tid)
        seen_tools.add(tid)
    if dup_tools:
        issues_found.append(f"[index.html] Duplicate data-tool-id found: {dup_tools}")
    else:
        print("[PASS] index.html: All data-tool-id attributes are strictly unique.")

# 2. Audit crates/cli/src/main.rs
rust_path = 'crates/cli/src/main.rs'
if os.path.exists(rust_path):
    with open(rust_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"\n[AUDIT] crates/cli/src/main.rs ({len(lines)} lines):")
    # Scan for potential panic sites or unsafe unwraps in request handling
    in_request_handler = False
    handler_unwraps = []
    for line_no, line in enumerate(lines, 1):
        if 'tokio::spawn(async move' in line or 'loop {' in line:
            in_request_handler = True
        if in_request_handler and ('.unwrap()' in line or '.expect(' in line):
            # Check if it's inside response formatting or mutex locks
            if not line.strip().startswith('//'):
                handler_unwraps.append((line_no, line.strip()))
    
    print(f"  Total unwraps/expects in server loop: {len(handler_unwraps)}")
    for lno, text in handler_unwraps[:10]:
        print(f"    Line {lno}: {text[:80]}")

# 3. Audit browser/ui/app.js
js_path = 'browser/ui/app.js'
if os.path.exists(js_path):
    with open(js_path, 'r', encoding='utf-8') as f:
        js_lines = f.readlines()
    print(f"\n[AUDIT] browser/ui/app.js ({len(js_lines)} lines):")
    
    # Check for direct innerHTML assignments without sanitization
    raw_innerhtml = []
    for line_no, line in enumerate(js_lines, 1):
        if '.innerHTML =' in line and not line.strip().startswith('//'):
            # Check if escapeHtml or sanitize is used
            if 'escapeHtml' not in line and 'sanitize' not in line and 'badge' not in line and 'pill' not in line:
                raw_innerhtml.append((line_no, line.strip()[:90]))
    print(f"  Found {len(raw_innerhtml)} unchecked innerHTML assignments.")
    for lno, text in raw_innerhtml[:8]:
        print(f"    Line {lno}: {text}")

    # Check for document.getElementById without null guards
    missing_null_guards = []
    for line_no, line in enumerate(js_lines, 1):
        m = re.search(r'document\.getElementById\([\'"]([^\'"]+)[\'"]\)\.([a-zA-Z]+)', line)
        if m:
            elem_id, prop = m.group(1), m.group(2)
            if not line.strip().startswith('//') and not line.strip().startswith('if ('):
                missing_null_guards.append((line_no, elem_id, prop, line.strip()[:80]))
    print(f"  Found {len(missing_null_guards)} unguarded document.getElementById property accesses.")
    for lno, eid, prop, text in missing_null_guards[:10]:
        print(f"    Line {lno}: getElementById('{eid}').{prop} -> {text}")

print("=" * 70)
print(f"TOTAL CRITICAL ISSUES IDENTIFIED: {len(issues_found)}")
for iss in issues_found:
    print("  *", iss)
print("=" * 70)

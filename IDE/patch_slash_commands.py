import os
import glob
import re

# Comprehensive script to patch all copilot extension.js files across IDE codebase

def patch_file(file_path):
    print(f"Checking {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    # 1. Remove cp.execFileSync blocks for stats, sysinfo, tasks
    if "Q===\"stats\"" in content or "Q==='stats'" in content:
        sub_pattern = r'Q==="stats"\|\|Q==="performance-stats"[\s\S]*?if\(Q==="evolve"\)'
        if re.search(sub_pattern, content):
            content = re.sub(sub_pattern, 'Q==="evolve"', content)
            modified = True
            print(f"  -> Removed execFileSync blocks for stats/sysinfo/tasks")

    # 2. Update line 2207 Set to include all slash commands and use W = c
    old_set_pattern = r'if\(new Set\(\["question","summary"[\s\S]*?\.has\(Q\)\)\{let W=[^;]+;'
    new_set_code = 'if(new Set(["question","summary","sentiment","ner","stats","sysinfo","sys-info","decision-stats","novel-ai-stats","performance-stats","cache-stats","ml-analytics","model-ranking","model-recommendations","analytics-demo","update","clearcache","restore","ml-retrain","tasks","search-query","demo-hyde","add-documents","mcp","keys","api-keys","security","refactor"]).has(Q)){let W=c;'

    if re.search(old_set_pattern, content):
        content = re.sub(old_set_pattern, new_set_code, content)
        modified = True
        print(f"  -> Updated direct orchestration Set and W=c")

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  -> Successfully saved changes to {file_path}")
    else:
        print(f"  -> No changes needed for {file_path}")

base_dir = r"d:\harfile\ModelFusion\IDE"
count = 0
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file == "extension.js" and "copilot" in root and "dist" in root:
            full_path = os.path.join(root, file)
            patch_file(full_path)
            count += 1

print(f"Total extension.js files processed: {count}")

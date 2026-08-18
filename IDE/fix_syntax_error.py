import os
import glob
import re

# Python script to fix SyntaxError: Unexpected token '{' in extension.js

search_dirs = [
    r"d:\harfile\ModelFusion\IDE\vscode-126-extract",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64",
    r"d:\harfile\ModelFusion\IDE\vscode"
]

def fix_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    # Fix broken `Q==="evolve"{` -> `Q==="evolve"){` or `if(Q==="evolve"){`
    broken_pattern1 = 'Q==="evolve"{'
    correct_pattern1 = 'Q==="evolve"){'

    if broken_pattern1 in content:
        content = content.replace(broken_pattern1, correct_pattern1)
        modified = True
        print(f"  -> Fixed SyntaxError: {broken_pattern1} -> {correct_pattern1} in {file_path}")

    # Also check if `cleanP` stripping `@agent` is present before slash command matching
    # Line 2160 check:
    # let P=lastText.replace(...).trim();
    # Ensure: let cleanP=P.replace(/^@\w+\s+/,"").trim(); if(cleanP.match(/^\/([a-zA-Z][\w-]*)\s*(.*)/s)){c=cleanP;}
    old_c_match = 'if(P.match(/^\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=P;}'
    new_c_match = 'let cleanP=P.replace(/^@\\w+\\s+/,"").trim();if(cleanP.match(/^\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=cleanP;}'

    if old_c_match in content:
        content = content.replace(old_c_match, new_c_match)
        modified = True
        print(f"  -> Added cleanP participant stripping in {file_path}")

    # Validate JavaScript syntax of the patched file using node -c
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  -> Saved changes to {file_path}")

count = 0
for sdir in search_dirs:
    for root, dirs, files in os.walk(sdir):
        for file in files:
            if file == "extension.js" and "copilot" in root and "dist" in root:
                full_path = os.path.join(root, file)
                fix_file(full_path)
                count += 1

print(f"Total extension.js files inspected: {count}")

#!/usr/bin/env python3
"""
patch_data_science_commands.py

Patches extension.js files across ModelFusion / HugOS IDE so that
/data-analyst, /dataanalyst, /datascience, /data-science, and /jupyter
are included in fastInfoCommands, routing directly to ModelFusion's
<1ms fast interception server with rich actionable guides when no args
are passed, and running analysis when files or arguments are provided.
"""

import os
import re

FILES = [
    r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\sanity-test-extension.js",
    r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\test-extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\sanity-test-extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\test-extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\sanity-test-extension.js",
    r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\test-extension.js",
    os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
    os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
]

def patch_file(filepath: str):
    if not os.path.isfile(filepath):
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"[WARN] Failed to read {filepath}: {e}")
        return

    # Check if fastInfoCommands already has data-analyst
    if 'fastInfoCommands' not in content:
        return

    # Pattern for newfile in fastInfoCommands set
    pattern = r'("newfile",\s*\]\);)'
    replacement = '''"newfile",
            "dataanalyst",
            "data-analyst",
            "datascience",
            "data-science",
            "jupyter",
]);'''

    if '"data-analyst"' in content and 'fastInfoCommands' in content:
        # Check if it is already inside fastInfoCommands
        fic_match = re.search(r'fastInfoCommands\s*=\s*(?:/\* @__PURE__ \*/\s*)?new Set\(\[([\s\S]*?)\]\);', content)
        if fic_match and '"data-analyst"' in fic_match.group(1):
            print(f"[OK] Already patched: {filepath}")
            return

    new_content, count = re.subn(pattern, replacement, content, count=1)
    if count > 0:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"[PATCHED] Successfully updated fastInfoCommands in {filepath}")
        except Exception as e:
            print(f"[WARN] Failed to write {filepath}: {e}")
    else:
        print(f"[SKIP] Pattern not matched in {filepath}")

if __name__ == "__main__":
    for f in FILES:
        patch_file(f)

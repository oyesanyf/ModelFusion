#!/usr/bin/env python3
import os
import re
import subprocess

def find_node():
    candidates = [
        r"D:\tools\nodejs\node.exe",
        r"C:\Program Files\nodejs\node.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "node"

def check_node(path, node):
    try:
        res = subprocess.run([node, "--check", path], capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    except Exception as e:
        return False, str(e)

def main():
    node = find_node()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(root, "IDE", "vscode", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(root, "IDE", "VSCode-win32-x64", "resources", "app", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(root, "IDE", "VSCode-win32-x64", "7e7950df89", "resources", "app", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(root, "IDE", "vscode", ".build", "extensions", "copilot", "dist", "extension.js"),
    ]

    for path in targets:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        fixed = False
        pattern = r'("version")(\s+)("updatedb")'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1,\2\3', content)
            fixed = True

        if fixed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[REPAIRED] Fixed missing comma in: {path}")
        else:
            print(f"[NO REPAIR NEEDED] {path}")

        ok, err = check_node(path, node)
        if ok:
            print(f"[VALID] {path}")
        else:
            print(f"[INVALID] {path}\n{err}")

if __name__ == "__main__":
    main()

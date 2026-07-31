import os
import glob

# Script to fix slash command detection in ModelFusionProvider (extension.js)

base_dirs = [
    r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64"
]

OLD_PATTERNS = [
    """let lastMsg=r[r.length-1],lastText=l[l.length-1]||"";
let P=lastText.replace(/\\[Context: Selected Explorer Item\\(s\\):[\\s\\S]*?\\]/g,"").trim();
if(P.match(/^\\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=P;}""",

    """let lastMsg=r[r.length-1],lastText=l[l.length-1]||"";
let P=lastText.replace(/\\[Context: Selected Explorer Item\\(s\\):[\\s\\S]*?\\]/g,"").trim();
let cleanP=P.replace(/^@\\w+\\s+/,"").trim();
if(cleanP.match(/^\\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=cleanP;}
if(!c&&(cleanP.startsWith("/evolve")||P.includes("/evolve"))){c="/evolve";}"""
]

NEW_PATTERN = """let lastMsg=r[r.length-1],lastText=l[l.length-1]||"";
let P=lastText.replace(/\\[Context: Selected Explorer Item\\(s\\):[\\s\\S]*?\\]/g,"").trim();
let cleanP=P.replace(/^@\\w+\\s+/,"").trim();
if(cleanP.match(/^\\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=cleanP;}
if(!c&&(cleanP.startsWith("/evolve")||P.includes("/evolve"))){c="/evolve";}"""

count = 0
for base_dir in base_dirs:
    for file_path in glob.glob(os.path.join(base_dir, "**", "extension.js"), recursive=True):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Strip leading @agent prefix for slash matching if not already present
        if "let cleanP=P.replace(/^@\\w+\\s+/,\"\").trim();" not in content:
            target = """let lastMsg=r[r.length-1],lastText=l[l.length-1]||"";
let P=lastText.replace(/\\[Context: Selected Explorer Item\\(s\\):[\\s\\S]*?\\]/g,"").trim();
if(P.match(/^\\/([a-zA-Z][\\w-]*)\\s*(.*)/s)){c=P;}"""
            if target in content:
                content = content.replace(target, NEW_PATTERN)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Patched slash command detection in {file_path}")
                count += 1
            else:
                print(f"Target pattern not found in {file_path}")
        else:
            print(f"Already patched: {file_path}")

print(f"Total files updated: {count}")


import os
import glob
import sys

base_dirs = [
    r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64"
]

def patch_evolve_save_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Patch OpenEvolve output block
    # Target: read evolved code and show inline diff
    target_open_evolve = 'try{let S=Gi.readFileSync(g,"utf-8");S.trim()!==r.trim()?(await this._inlineDiff.showInlineChanges(t,r,S),u.report(new st(`\\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\n`))):u.report(new st(`Code unchanged after evolution.\n`))}'
    replacement_open_evolve = 'try{let S=Gi.readFileSync(g,"utf-8");u.report(new st(`\\n\\`\\`\\`python\\n${S}\\n\\`\\`\\`\\n\\n`));S.trim()!==r.trim()?(await this._inlineDiff.showInlineChanges(t,r,S),u.report(new st(`\\u{1F9EC} Inline diff shown in editor. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\\n`))):u.report(new st(`Code unchanged after evolution.\\n`))}'

    if target_open_evolve in content:
        content = content.replace(target_open_evolve, replacement_open_evolve)
        changed = True
        print(f"  Patched OpenEvolve code block in {file_path}")

    # 2. Patch Builtin Evolve output block
    target_builtin = 'f>0&&g!==r?l?(p.report(new st(`- **Status**: \\u2705 Code improved! Showing inline diff\\u2026\n\n`)),p.report(new st(`Use **Ctrl+Shift+Y** to Accept or **Ctrl+Shift+N** to Reject.\n`)),await this._inlineDiff.showInlineChanges(t,r,g)):(p.report(new st(`- **Status**: \\u2705 Code improved! (Auto-apply is disabled \\u2014 copy from chat output)\n\n`)),p.report(new st(`\\`\\`\\`${a}\n${g}\n\\`\\`\\`\n`)))'
    replacement_builtin = 'f>0&&g!==r?l?(p.report(new st(`- **Status**: \\u2705 Code improved! Showing inline diff\\u2026\\n\\n`)),p.report(new st(`\\`\\`\\`${a}\\n${g}\\n\\`\\`\\`\\n\\n`)),p.report(new st(`Use **Ctrl+Shift+Y** to Accept or **Ctrl+Shift+N** to Reject in editor.\\n`)),await this._inlineDiff.showInlineChanges(t,r,g)):(p.report(new st(`- **Status**: \\u2705 Code improved!\\n\\n`)),p.report(new st(`\\`\\`\\`${a}\\n${g}\\n\\`\\`\\`\\n`)))'

    if target_builtin in content:
        content = content.replace(target_builtin, replacement_builtin)
        changed = True
        print(f"  Patched Builtin Evolve code block in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

count = 0
for base_dir in base_dirs:
    for file_path in glob.glob(os.path.join(base_dir, "**", "extension.js"), recursive=True):
        print(f"Checking: {file_path}")
        if patch_evolve_save_in_file(file_path):
            count += 1

print(f"\nTotal files patched for evolve code display/save: {count}")

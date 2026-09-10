#!/usr/bin/env python3
"""
patch_evolve_save.py

Patches extension.js across all development, build, packaging, and installed HugOS IDE locations
to ensure both /evolve (OpenEvolve / Builtin) and /avo (AVO) render:
1. Markdown code block with evolved code: ```<lang>\n${bestCode}\n``` in chat.
2. Inline diff in active editor via _inlineDiff.showInlineChanges(...).
3. Accept/Reject instructions: 🧬 Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.

Supports both unminified esbuild bundles and minified (terser) production bundles.
"""

import os
import glob
import sys
import re

def get_target_files():
    discovered = []
    seen = set()

    def add_if_exists(p):
        if not p:
            return
        norm = os.path.normcase(os.path.abspath(p))
        if norm not in seen and os.path.exists(norm) and os.path.isfile(norm):
            seen.add(norm)
            discovered.append(os.path.abspath(p))

    local_app_data = os.environ.get('LOCALAPPDATA', '')
    user_profile = os.environ.get('USERPROFILE', '')

    # 1. Explicit canonical paths
    explicit_candidates = [
        # Development workspace
        r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js",
        # Packaged build directory
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        # LocalAppData installed distributions
        os.path.join(local_app_data, r"HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
        os.path.join(local_app_data, r"HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
        # Common user-profile fallbacks
        os.path.join(user_profile, r"AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
        os.path.join(user_profile, r"AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
        r"C:\Users\oyesa\AppData\Local\HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        r"C:\Users\oyesa\AppData\Local\HugOS IDE\resources\app\extensions\copilot\dist\extension.js",
    ]

    for cand in explicit_candidates:
        add_if_exists(cand)

    # 2. Scoped globbing across version hash folders (fast, non-recursive over root)
    scoped_roots = [
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64",
        os.path.join(local_app_data, "HugOS IDE") if local_app_data else None,
        os.path.join(user_profile, r"AppData\Local\HugOS IDE") if user_profile else None,
    ]
    for root in scoped_roots:
        if root and os.path.exists(root):
            pattern = os.path.join(root, "*", "resources", "app", "extensions", "copilot", "dist", "extension.js")
            for match in glob.glob(pattern):
                add_if_exists(match)

    return discovered


def patch_evolve_save_in_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # =========================================================================
    # 1. BUILTIN EVOLVE - UNMINIFIED (Current esbuild bundle)
    # =========================================================================
    # 1A. Instruction update: "Use **Ctrl+Shift+Y** to Accept or **Ctrl+Shift+N** to Reject.\n" ->
    #     "\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\n"
    # Matches any LanguageModelTextPart identifier (LanguageModelTextPart, LanguageModelTextPart2, LanguageModelTextPart3, etc.)
    pattern_unmin_builtin_instr = re.compile(
        r'(progress\.report\(new\s+\w+\(["\'])Use\s+\*\*Ctrl\+Shift\+Y\*\*\s+to\s+Accept\s+or\s+\*\*Ctrl\+Shift\+N\*\*\s+to\s+Reject\.\\n(["\']\)\);)'
    )
    if pattern_unmin_builtin_instr.search(content):
        content = pattern_unmin_builtin_instr.sub(
            r'\g<1>\\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\\n\g<2>',
            content
        )
        changed = True
        print(f"  [Builtin-Unminified] Patched Accept/Reject instruction in {file_path}")

    # 1B. Ensure code block under autoApply in unminified Builtin Evolve
    pattern_unmin_no_codeblock = re.compile(
        r'(if\s*\(\s*autoApply\s*\)\s*\{[^{}]+?Showing inline diff[^{}]+?)(progress\.report\(new\s+\w+\(["\'](?:\\u\{1F9EC\}\s*Inline diff shown\.\s*)?\*\*Ctrl\+Shift\+Y\*\*.*?\)\);[^{}]+?showInlineChanges\(\s*editor\s*,\s*originalCode\s*,\s*bestCode\s*\))',
        re.DOTALL
    )
    m = pattern_unmin_no_codeblock.search(content)
    if m:
        matched_text = m.group(0)
        if "${bestCode}" not in matched_text:
            replacement = (
                m.group(1) +
                'progress.report(new LanguageModelTextPart3(`\\`\\`\\`${fileExt}\\n${bestCode}\\n\\`\\`\\`\\n\\n`));\n            ' +
                m.group(2)
            )
            content = content.replace(matched_text, replacement)
            changed = True
            print(f"  [Builtin-Unminified] Inserted missing code block in {file_path}")

    # =========================================================================
    # 2. BUILTIN EVOLVE - MINIFIED (Legacy / Production terser)
    # =========================================================================
    target_builtin_min = 'f>0&&g!==r?l?(p.report(new st(`- **Status**: \\u2705 Code improved! Showing inline diff\\u2026\n\n`)),p.report(new st(`Use **Ctrl+Shift+Y** to Accept or **Ctrl+Shift+N** to Reject.\n`)),await this._inlineDiff.showInlineChanges(t,r,g)):(p.report(new st(`- **Status**: \\u2705 Code improved! (Auto-apply is disabled \\u2014 copy from chat output)\n\n`)),p.report(new st(`\\`\\`\\`${a}\n${g}\n\\`\\`\\`\n`)))'
    replacement_builtin_min = 'f>0&&g!==r?l?(p.report(new st(`- **Status**: \\u2705 Code improved! Showing inline diff\\u2026\\n\\n`)),p.report(new st(`\\`\\`\\`${a}\\n${g}\\n\\`\\`\\`\\n\\n`)),p.report(new st(`\\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\\n`)),await this._inlineDiff.showInlineChanges(t,r,g)):(p.report(new st(`- **Status**: \\u2705 Code improved!\\n\\n`)),p.report(new st(`\\`\\`\\`${a}\\n${g}\\n\\`\\`\\`\\n`)))'
    if target_builtin_min in content:
        content = content.replace(target_builtin_min, replacement_builtin_min)
        changed = True
        print(f"  [Builtin-Minified] Patched code block and diff instructions in {file_path}")

    # =========================================================================
    # 3. OPENEVOLVE / AVO - MINIFIED (Legacy / Production terser)
    # =========================================================================
    target_open_evolve_min = 'try{let S=Gi.readFileSync(g,"utf-8");S.trim()!==r.trim()?(await this._inlineDiff.showInlineChanges(t,r,S),u.report(new st(`\\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\n`))):u.report(new st(`Code unchanged after evolution.\n`))}'
    replacement_open_evolve_min = 'try{let S=Gi.readFileSync(g,"utf-8");u.report(new st(`\\n\\`\\`\\`python\\n${S}\\n\\`\\`\\`\\n\\n`));S.trim()!==r.trim()?(await this._inlineDiff.showInlineChanges(t,r,S),u.report(new st(`\\u{1F9EC} Inline diff shown. **Ctrl+Shift+Y** to Accept, **Ctrl+Shift+N** to Reject.\\n`))):u.report(new st(`Code unchanged after evolution.\\n`))}'
    if target_open_evolve_min in content:
        content = content.replace(target_open_evolve_min, replacement_open_evolve_min)
        changed = True
        print(f"  [OpenEvolve/AVO-Minified] Patched code block in {file_path}")

    # =========================================================================
    # 4. AVO - UNMINIFIED (Ensure code block + diff + instructions)
    # =========================================================================
    pattern_avo_no_codeblock = re.compile(
        r'(if\s*\(\s*require\(["\']fs["\']\)\.existsSync\(bestCodePath\)\s*\)\s*\{\s*const\s+bestCode\s*=\s*require\(["\']fs["\']\)\.readFileSync\(bestCodePath,\s*["\']utf-8["\']\);\s*)(if\s*\(\s*bestCode\.trim\(\)\s*!==\s*originalCode\.trim\(\)\s*\))'
    )
    if pattern_avo_no_codeblock.search(content):
        content = pattern_avo_no_codeblock.sub(
            r'\g<1>progress.report(new LanguageModelTextPart3(`\\n\\`\\`\\`${path24.extname(fileName).slice(1) || "python"}\\n${bestCode}\\n\\`\\`\\`\\n\\n`));\n                  \g<2>',
            content
        )
        changed = True
        print(f"  [AVO-Unminified] Inserted missing code block in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main(dry_run=False):
    targets = get_target_files()
    print(f"Found {len(targets)} candidate extension.js files:")
    for t in targets:
        print(f"  - {t}")

    count = 0
    for file_path in targets:
        print(f"Checking: {file_path}")
        if not dry_run:
            if patch_evolve_save_in_file(file_path):
                count += 1
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            pattern_unmin_builtin_instr = re.compile(
                r'(progress\.report\(new\s+\w+\(["\'])Use\s+\*\*Ctrl\+Shift\+Y\*\*\s+to\s+Accept\s+or\s+\*\*Ctrl\+Shift\+N\*\*\s+to\s+Reject\.\\n(["\']\)\);)'
            )
            if pattern_unmin_builtin_instr.search(content):
                print(f"  [DRY RUN] Would patch Builtin instruction in {file_path}")
                count += 1

    print(f"\nTotal files patched for evolve code display/save: {count}")
    return count

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)

#!/usr/bin/env python3
"""
patch_evolution_fusion.py

Patches extension.js across all distributions to support multi-model fusion
in /avo, /evolve, and /openevolve commands via --fusion / -f flag and settings.
"""

import os
import glob
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

    explicit_candidates = [
        r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\dist\extension.js",
        os.path.join(local_app_data, r"HugOS IDE\7e7950df89\resources\app\extensions\copilot\dist\extension.js"),
        os.path.join(local_app_data, r"HugOS IDE\resources\app\extensions\copilot\dist\extension.js"),
    ]

    for cand in explicit_candidates:
        add_if_exists(cand)

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


def patch_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Update _runAvo arg parsing for --fusion / -f and pass useFusion
    target_avo_args = 'let maxIterations = defaultIterations;\n        let remainingArgs = [];\n        for (let i9 = 0; i9 < parts2.length; i9++) {'
    replacement_avo_args = 'let maxIterations = defaultIterations;\n        let remainingArgs = [];\n        let useFusion = Boolean(evolveConfig.get("fusion", false) || vscode15.workspace.getConfiguration("hugos.modelfusion").get("fusion", false));\n        for (let i9 = 0; i9 < parts2.length; i9++) {\n          if (parts2[i9] === "--fusion" || parts2[i9] === "-f") {\n            useFusion = true;\n            continue;\n          }'
    if target_avo_args in content:
        content = content.replace(target_avo_args, replacement_avo_args)
        changed = True
        print(f"  [AVO] Patched --fusion flag parsing in {file_path}")

    target_avo_call = 'await this._runAvoEvolve(editor, originalCode, fileName, maxIterations, autoApply, customFocuses, progress, token);'
    replacement_avo_call = 'await this._runAvoEvolve(editor, originalCode, fileName, maxIterations, autoApply, customFocuses, useFusion, progress, token);'
    if target_avo_call in content:
        content = content.replace(target_avo_call, replacement_avo_call)
        changed = True
        print(f"  [AVO] Patched _runAvoEvolve call with useFusion in {file_path}")

    # 2. Update _runAvoEvolve signature and orchestration request
    target_avo_sig = 'async _runAvoEvolve(editor, originalCode, fileName, iterations, autoApply, customFocuses, progress, token) {'
    replacement_avo_sig = 'async _runAvoEvolve(editor, originalCode, fileName, iterations, autoApply, customFocuses, useFusion, progress, token) {'
    if target_avo_sig in content:
        content = content.replace(target_avo_sig, replacement_avo_sig)
        changed = True
        print(f"  [AVO] Patched _runAvoEvolve signature in {file_path}")

    # Add fusion mode progress report in _runAvoEvolve
    target_avo_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${iterations}\n`));'
    replacement_avo_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${iterations}\n`));\n        if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**: Active (Multi-model consensus enabled)\\n")); }'
    if target_avo_banner in content and 'if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**' not in content:
        content = content.replace(target_avo_banner, replacement_avo_banner)
        changed = True
        print(f"  [AVO] Added Fusion Mode progress banner in {file_path}")

    # Patch Step 1 orchestration call in _runAvoEvolve
    avo_orch_regex = re.compile(
        r'(const\s+evaluatorCode\s*=\s*await\s+this\._sendOrchestrationRequest\(\s*evaluatorPrompt,\s*10,\s*)"fastest",\s*"multi-model",\s*1,\s*false,\s*true,\s*false,\s*false,\s*true,\s*ollamaModel,\s*token\s*\);'
    )
    if avo_orch_regex.search(content):
        content = avo_orch_regex.sub(
            r'\g<1>useFusion ? "multi_objective" : "fastest", "multi-model", useFusion ? 3 : 1, false, true, false, useFusion, true, ollamaModel, token);',
            content
        )
        changed = True
        print(f"  [AVO] Patched Step 1 orchestration call to pass useFusion in {file_path}")

    # 3. Update _runOpenEvolve arg parsing for --fusion / -f
    target_oe_args = 'const customFocuses = evolveConfig.get("focuses", []);\n        const parts2 = query.trim().split(/\\s+/).slice(1);\n        let maxIterations = defaultIterations;\n        let remainingArgs = [];\n        for (let i9 = 0; i9 < parts2.length; i9++) {'
    replacement_oe_args = 'const customFocuses = evolveConfig.get("focuses", []);\n        const parts2 = query.trim().split(/\\s+/).slice(1);\n        let maxIterations = defaultIterations;\n        let remainingArgs = [];\n        let useFusion = Boolean(evolveConfig.get("fusion", false) || vscode15.workspace.getConfiguration("hugos.modelfusion").get("fusion", false));\n        for (let i9 = 0; i9 < parts2.length; i9++) {\n          if (parts2[i9] === "--fusion" || parts2[i9] === "-f") {\n            useFusion = true;\n            continue;\n          }'
    if target_oe_args in content:
        content = content.replace(target_oe_args, replacement_oe_args)
        changed = True
        print(f"  [OpenEvolve] Patched --fusion flag parsing in {file_path}")

    # Patch Step 1 orchestration call in _runOpenEvolve
    oe_orch_regex = re.compile(
        r'(const\s+evalCode\s*=\s*await\s+this\._sendOrchestrationRequest\(\s*evalPrompt,\s*10,\s*)"fastest",\s*"multi-model",\s*1,\s*false,\s*true,\s*false,\s*false,\s*true,\s*ollamaModel,\s*token\s*\);'
    )
    if oe_orch_regex.search(content):
        content = oe_orch_regex.sub(
            r'\g<1>useFusion ? "multi_objective" : "fastest", "multi-model", useFusion ? 3 : 1, false, true, false, useFusion, true, ollamaModel, token);',
            content
        )
        changed = True
        print(f"  [OpenEvolve] Patched Step 1 orchestration call to pass useFusion in {file_path}")

    # Patch configYamlContent to pass fusion flag
    target_yaml = 'timeout: 60\n\nprompt:'
    replacement_yaml = 'timeout: 60\n  fusion: ${useFusion}\n\nprompt:'
    if target_yaml in content:
        content = content.replace(target_yaml, replacement_yaml)
        changed = True
        print(f"  [OpenEvolve] Injected fusion flag into config.yaml in {file_path}")

    # Pass useFusion to _runBuiltinEvolve call from _runOpenEvolve
    content = content.replace(
        'await this._runBuiltinEvolve(editor, originalCode, fileName, fileExt, language2, maxIterations, autoApply, showProgress, customFocuses, progress, token);',
        'await this._runBuiltinEvolve(editor, originalCode, fileName, fileExt, language2, maxIterations, autoApply, showProgress, customFocuses, useFusion, progress, token);'
    )

    # Pass useFusion to _runOpenEvolveProcess call from _runOpenEvolve
    content = content.replace(
        'await this._runOpenEvolveProcess(editor, originalCode, fileName, fileExt, openEvolveDir, configPath, maxIterations, autoApply, progress, token);',
        'await this._runOpenEvolveProcess(editor, originalCode, fileName, fileExt, openEvolveDir, configPath, maxIterations, autoApply, useFusion, progress, token);'
    )

    # 4. Update _runOpenEvolveProcess signature and banner
    target_oep_sig = 'async _runOpenEvolveProcess(editor, originalCode, fileName, fileExt, openEvolveDir, configPath, maxIterations, autoApply, progress, token) {'
    replacement_oep_sig = 'async _runOpenEvolveProcess(editor, originalCode, fileName, fileExt, openEvolveDir, configPath, maxIterations, autoApply, useFusion, progress, token) {'
    if target_oep_sig in content:
        content = content.replace(target_oep_sig, replacement_oep_sig)
        changed = True
        print(f"  [OpenEvolve] Patched _runOpenEvolveProcess signature in {file_path}")

    target_oep_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${maxIterations}\n`));'
    replacement_oep_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${maxIterations}\n`));\n        if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**: Active (Multi-model consensus enabled)\\n")); }'
    if target_oep_banner in content and 'if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**' not in content:
        content = content.replace(target_oep_banner, replacement_oep_banner)
        changed = True
        print(f"  [OpenEvolve] Added Fusion Mode progress banner in _runOpenEvolveProcess in {file_path}")

    # 5. Update _runBuiltinEvolve signature, banner, and iteration call
    target_be_sig = 'async _runBuiltinEvolve(editor, originalCode, fileName, fileExt, language2, maxIterations, autoApply, showProgress, customFocuses, progress, token) {'
    replacement_be_sig = 'async _runBuiltinEvolve(editor, originalCode, fileName, fileExt, language2, maxIterations, autoApply, showProgress, customFocuses, useFusion, progress, token) {'
    if target_be_sig in content:
        content = content.replace(target_be_sig, replacement_be_sig)
        changed = True
        print(f"  [BuiltinEvolve] Patched _runBuiltinEvolve signature in {file_path}")

    target_be_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${maxIterations}  \n`));'
    replacement_be_banner = 'progress.report(new LanguageModelTextPart3(`\\u{1F504} **Iterations**: ${maxIterations}  \n`));\n        if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**: Active (Multi-model consensus enabled)\\n\\n")); }'
    if target_be_banner in content and 'if (useFusion) { progress.report(new LanguageModelTextPart3("⚡ **Fusion Mode**' not in content:
        content = content.replace(target_be_banner, replacement_be_banner)
        changed = True
        print(f"  [BuiltinEvolve] Added Fusion Mode banner in _runBuiltinEvolve in {file_path}")

    # In _runBuiltinEvolve loop:
    be_orch_regex = re.compile(
        r'(const\s+improved\s*=\s*await\s+this\._sendOrchestrationRequest\(\s*prompt,\s*10,\s*)"fastest",\s*"multi-model",\s*1,\s*false,\s*true,\s*false,\s*false,\s*true,\s*ollamaModel,\s*token\s*\);'
    )
    if be_orch_regex.search(content):
        content = be_orch_regex.sub(
            r'\g<1>useFusion ? "multi_objective" : "fastest", "multi-model", useFusion ? 3 : 1, false, true, false, useFusion, true, ollamaModel, token);',
            content
        )
        changed = True
        print(f"  [BuiltinEvolve] Patched iteration orchestration call to pass useFusion in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Successfully patched {file_path}")
    else:
        print(f"[SKIP] No changes needed in {file_path}")

def main():
    target_files = get_target_files()
    print(f"Discovered {len(target_files)} target file(s) for evolution fusion patching.")
    for tf in target_files:
        print(f"\nProcessing {tf}...")
        patch_file(tf)

if __name__ == "__main__":
    main()

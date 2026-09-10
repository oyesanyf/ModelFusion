import os

def patch_file(path, replacements):
    if not os.path.exists(path):
        print(f"[SKIP] Not found: {path}")
        return False
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for target, replacement in replacements:
        if target in content:
            content = content.replace(target, replacement, 1)
            modified = True
            print(f"  [OK] Replaced pattern in {os.path.basename(path)}")
        elif replacement in content:
            print(f"  [INFO] Already patched in {os.path.basename(path)}")
        else:
            print(f"  [WARN] Target pattern not found in {os.path.basename(path)}: {target[:50]}...")
            
    if modified:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[SUCCESS] Wrote changes to {path}")
        return True
    return False

# 1. Restore github-authentication package.json
print("--- Restoring github-authentication ---")
for base in [r'D:\harfile\ModelFusion\IDE\VSCode-win32-x64', r'C:\Users\oyesanyf\AppData\Local\HugOS IDE']:
    for root, dirs, files in os.walk(base):
        if 'github-authentication' in root and 'package.json.disabled' in files:
            disabled = os.path.join(root, 'package.json.disabled')
            enabled = os.path.join(root, 'package.json')
            if os.path.exists(enabled):
                os.remove(disabled)
                print(f"[INFO] Removed leftover .disabled: {disabled}")
            else:
                os.rename(disabled, enabled)
                print(f"[SUCCESS] Restored {enabled}")

# 2. Patch unminified workbench.desktop.main.js files
print("\n--- Patching Unminified workbench.desktop.main.js ---")
unmin_replacements = [
    (
        '    const context2 = chatEntitlementService.context?.value;\n    const requests = chatEntitlementService.requests?.value;\n    if (!context2 || !requests) {\n      return;\n    }',
        '    const context2 = chatEntitlementService.context?.value;\n    const requests = chatEntitlementService.requests?.value;\n    return; // HugOS: GitHub login is optional; do not intercept chat with SetupAgent\n    if (!context2 || !requests) {\n      return;\n    }'
    ),
    (
        '  async showDialog(options3) {\n    const disposables = new DisposableStore();',
        '  async showDialog(options3) {\n    if (!options3?.forceSignInDialog) { return 0 /* Canceled */; } // HugOS: suppress automatic sign-in modal\n    const disposables = new DisposableStore();'
    )
]

for p in [
    r'D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\out\vs\workbench\workbench.desktop.main.js',
    r'C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\out\vs\workbench\workbench.desktop.main.js',
    r'D:\harfile\ModelFusion\IDE\vscode\out-vscode\vs\workbench\workbench.desktop.main.js',
]:
    patch_file(p, unmin_replacements)

# 3. Patch minified workbench.desktop.main.js files
print("\n--- Patching Minified workbench.desktop.main.js ---")
min_replacements = [
    (
        'let g=o.context?.value,f=o.requests?.value;if(!g||!f)return;let v=new Io(',
        'let g=o.context?.value,f=o.requests?.value;return;if(!g||!f)return;let v=new Io('
    ),
    (
        'async showDialog(i){let e=new O,t=this.getButtons(i),o=e.add(new Soe(',
        'async showDialog(i){if(!i?.forceSignInDialog)return 0;let e=new O,t=this.getButtons(i),o=e.add(new Soe('
    )
]

for p in [
    r'D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js',
    r'C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\out\vs\workbench\workbench.desktop.main.js',
]:
    patch_file(p, min_replacements)

print("\n--- Patching Complete ---")

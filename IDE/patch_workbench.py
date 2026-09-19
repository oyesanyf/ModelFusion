#!/usr/bin/env python3
"""
HugOS IDE Workbench Patch Script
Applies permanent chat enablement and entitlement bypass patches to workbench.desktop.main.js
Supports both minified and unminified bundles, validates syntax with node.exe,
and cleans any legacy disabled extension states from AppData.
"""

import os
import sys
import re
import shutil
import sqlite3
import subprocess

def find_node_executable():
    """Locate node.exe on the system."""
    candidate_paths = [
        r"D:\tools\nodejs\node.exe",
        shutil.which("node"),
        shutil.which("node.exe"),
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ]
    for p in candidate_paths:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None

def clean_diag_logs(content):
    """Remove temporary diagnostic logging statements if present."""
    changed = False
    diag_patterns = [
        r'if\(r\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\)this\._logService\.error\("\[DIAG-RUNLOC-COPILOT\][^;]*\);',
        r'for\(let x of t\)if\(x\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\)a\.error\("\[DIAG-OST-COPILOT\][^;]*\);',
        r'n\[c\]\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\?a\.error\("\[DIAG-EJO-COPILOT\][^:]*\):0,',
    ]
    for pat in diag_patterns:
        if re.search(pat, content):
            content = re.sub(pat, '', content)
            changed = True
    return content, changed

def patch_workbench_content(content):
    """
    Applies the 4 core HugOS chat enablement patches:
    1. Neutralize ensureChatExtensionInitialDisabledState
    2. Force EnablementState.EnabledGlobally (3) for github.copilot-chat
    3. Suppress SetupAgent entitlement interceptor
    4. Suppress forced sign-in modal dialog
    Supports both minified and unminified files.
    """
    changed = False

    # Clean any DIAG logs first
    content, diag_cleaned = clean_diag_logs(content)
    if diag_cleaned:
        changed = True

    # --- Minified Patterns ---
    # 1. ensureChatExtensionInitialDisabledState
    t1_m_orig = "ensureChatExtensionInitialDisabledState(){"
    t1_m_repl = "ensureChatExtensionInitialDisabledState(){return;"
    if t1_m_orig in content and t1_m_repl not in content:
        content = content.replace(t1_m_orig, t1_m_repl, 1)
        changed = True

    # 2. _computeEnablementState
    t2_m_orig = "e.identifier.id.toLowerCase()===this._chatExtensionId&&this.ensureChatExtensionInitialDisabledState(),r=this._getUserEnablementState(e.identifier);"
    t2_m_repl = 'if(e.identifier.id.toLowerCase()==="github.copilot-chat"||e.identifier.id.toLowerCase()===this._chatExtensionId)return 3;r=this._getUserEnablementState(e.identifier);'
    if t2_m_orig in content and t2_m_repl not in content:
        content = content.replace(t2_m_orig, t2_m_repl, 1)
        changed = True

    # 3. Suppress setupAgent entitlement interceptor
    t3_m_orig = "let g=o.context?.value,f=o.requests?.value;if(!g||!f)return;let v=new Io("
    t3_m_repl = "let g=o.context?.value,f=o.requests?.value;return;if(!g||!f)return;let v=new Io("
    if t3_m_orig in content and t3_m_repl not in content:
        content = content.replace(t3_m_orig, t3_m_repl, 1)
        changed = True

    # 4. Suppress forced sign-in modal
    t4_m_orig = "async showDialog(i){let e=new O,t=this.getButtons(i),o=e.add(new Soe("
    t4_m_repl = "async showDialog(i){if(!i?.forceSignInDialog)return 0;let e=new O,t=this.getButtons(i),o=e.add(new Soe("
    if t4_m_orig in content and t4_m_repl not in content:
        content = content.replace(t4_m_orig, t4_m_repl, 1)
        changed = True

    # --- Unminified Patterns ---
    # 1. ensureChatExtensionInitialDisabledState
    t1_u_orig = "ensureChatExtensionInitialDisabledState() {\n"
    t1_u_repl = "ensureChatExtensionInitialDisabledState() {\n    return;\n"
    if t1_u_orig in content and t1_u_repl not in content:
        content = content.replace(t1_u_orig, t1_u_repl, 1)
        changed = True

    # 2. _computeEnablementState
    t2_u_orig = (
        "    if (extension.identifier.id.toLowerCase() === this._chatExtensionId) {\n"
        "      this.ensureChatExtensionInitialDisabledState();\n"
        "    }\n"
        "    enablementState = this._getUserEnablementState(extension.identifier);"
    )
    t2_u_repl = (
        '    if (extension.identifier.id.toLowerCase() === "github.copilot-chat" || extension.identifier.id.toLowerCase() === this._chatExtensionId) {\n'
        "      return 3 /* EnabledGlobally */;\n"
        "    }\n"
        "    enablementState = this._getUserEnablementState(extension.identifier);"
    )
    if t2_u_orig in content and t2_u_repl not in content:
        content = content.replace(t2_u_orig, t2_u_repl, 1)
        changed = True

    # 3. Suppress setupAgent entitlement interceptor
    t3_u_orig = (
        "    const context2 = chatEntitlementService.context?.value;\n"
        "    const requests = chatEntitlementService.requests?.value;\n"
        "    if (!context2 || !requests) {\n"
        "      return;\n"
        "    }"
    )
    t3_u_repl = (
        "    const context2 = chatEntitlementService.context?.value;\n"
        "    const requests = chatEntitlementService.requests?.value;\n"
        "    return; // HugOS: GitHub login is optional; do not intercept chat with SetupAgent\n"
        "    if (!context2 || !requests) {\n"
        "      return;\n"
        "    }"
    )
    if t3_u_orig in content and t3_u_repl not in content:
        content = content.replace(t3_u_orig, t3_u_repl, 1)
        changed = True

    # 4. Suppress sign-in dialog
    t4_u_orig = (
        "  async showDialog(options3) {\n"
        "    const disposables = new DisposableStore();"
    )
    t4_u_repl = (
        "  async showDialog(options3) {\n"
        "    if (!options3?.forceSignInDialog) { return 0 /* Canceled */; } // HugOS: suppress automatic sign-in modal\n"
        "    const disposables = new DisposableStore();"
    )
    if t4_u_orig in content and t4_u_repl not in content:
        content = content.replace(t4_u_orig, t4_u_repl, 1)
        changed = True

    return content, changed

def patch_workbench_file(file_path, node_path):
    """Patch a single workbench.desktop.main.js file and validate with node --check."""
    print(f"\n[CHECKING] {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Cannot read {file_path}: {e}")
        return False, False

    new_content, changed = patch_workbench_content(content)

    if not changed:
        print(f"  [INFO] Already patched and up to date.")
        return True, False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [OK] Patched {file_path}")
    except Exception as e:
        print(f"  [ERROR] Failed to write {file_path}: {e}")
        return False, False

    # Validate syntax with node --check
    if node_path:
        res = subprocess.run([node_path, "--check", file_path], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [ERROR] Node syntax check failed for {file_path}!")
            print(res.stderr)
            return False, False
        print(f"  [PASS] Node syntax validation passed.")
    else:
        print(f"  [WARN] node.exe not found; skipping syntax check.")

    return True, True

def cleanup_appdata():
    """Clean disabled extension entries in state.vscdb and remove CachedProfilesData."""
    app_data = os.environ.get("APPDATA", "")
    if not app_data:
        return

    hugos_dir = os.path.join(app_data, "HugOS")
    db_path = os.path.join(hugos_dir, "User", "globalStorage", "state.vscdb")
    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("UPDATE ItemTable SET value = '[]' WHERE key = 'extensionsIdentifiers/disabled'")
            affected = cur.rowcount
            conn.commit()
            conn.close()
            print(f"[CLEANUP] Cleared extensionsIdentifiers/disabled in {db_path} ({affected} row(s) updated).")
        except Exception as e:
            print(f"[CLEANUP ERROR] Failed to clean {db_path}: {e}")

    cached_dir = os.path.join(hugos_dir, "CachedProfilesData")
    if os.path.isdir(cached_dir):
        for root, _, files in os.walk(cached_dir):
            for file in files:
                if "cache" in file.lower():
                    fp = os.path.join(root, file)
                    try:
                        os.remove(fp)
                        print(f"[CLEANUP] Removed cache file: {fp}")
                    except Exception as e:
                        print(f"[CLEANUP WARN] Could not remove {fp}: {e}")

def main():
    print("============================================================")
    print("[HUGOS] Patching workbench.desktop.main.js (Chat Enablement)")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skip_installed = any(arg.lower() in ("--skip-installed", "--check-installed=false") for arg in sys.argv)
    pack_dir_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pack_dir = (
        os.path.abspath(pack_dir_args[0].strip().strip('\"\''))
        if pack_dir_args
        else os.path.join(script_dir, "VSCode-win32-x64")
    )
    print(f"  Target packaging directory: {pack_dir}")

    node_path = find_node_executable()
    if node_path:
        print(f"  Using Node.js at: {node_path}")
    else:
        print(f"  [WARNING] node.exe not found! Syntax checks will be skipped.")

    targets = [
        os.path.join(pack_dir, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"),
        os.path.join(script_dir, "vscode", "out-vscode", "vs", "workbench", "workbench.desktop.main.js"),
    ]

    base_dirs = [pack_dir]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        hugos_installed = os.path.join(local_app_data, "HugOS IDE")
        base_dirs.append(hugos_installed)
        targets.append(os.path.join(hugos_installed, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"))

    # Scan for versioned runtime directories ([0-9a-f]{7,40})
    for b in base_dirs:
        if b and os.path.isdir(b):
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        v_wb = os.path.join(sub, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js")
                        if v_wb not in targets:
                            targets.append(v_wb)

    seen = set()
    error_count = 0
    modified_count = 0
    for t in targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_workbench_file(t, node_path)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    # AppData state DB and profile caches cleanup
    cleanup_appdata()

    if error_count > 0:
        print(f"\n[ERROR] workbench.desktop.main.js patching failed with {error_count} error(s)!")
        sys.exit(1)

    print(f"\n[SUCCESS] workbench.desktop.main.js patching complete! ({len(seen)} validated, {modified_count} modified)")
    sys.exit(0)

if __name__ == "__main__":
    main()

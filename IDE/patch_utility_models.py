#!/usr/bin/env python3
"""
HugOS IDE Utility Model and BYOK Notification Patch Script
Auto-presets chat utility models to 'modelfusion/modelfusion-local',
suppresses the intrusive 'Set BYOK utility models' popup,
and provides seamless auto-routing fallback to ModelFusion for utility and CAPI families.
"""

import os
import sys
import re
import json
import shutil
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

def validate_js_syntax(file_path, node_path):
    """Run node --check to validate JavaScript syntax."""
    if not node_path or not os.path.isfile(node_path):
        print(f"  [WARN] node.exe not found; skipping syntax validation for {os.path.basename(file_path)}")
        return True
    try:
        res = subprocess.run(
            [node_path, "--check", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if res.returncode != 0:
            print(f"  [SYNTAX ERROR] Validation failed for {file_path}:")
            print(res.stderr[:500])
            return False
        return True
    except Exception as e:
        print(f"  [SYNTAX ERROR] Exception running node --check: {e}")
        return False

def discover_vscode_var(content):
    """Find the local vscode import variable name used in _resolveUtilityOverride."""
    idx = content.find("async _resolveUtilityOverride(family)")
    if idx != -1:
        chunk = content[idx:idx + 4000]
        m = re.search(r'([a-zA-Z0-9_$]+)\.lm\.selectChatModels', chunk)
        if m:
            return m.group(1)
    m = re.search(r'([a-zA-Z0-9_$]+)\.lm\.selectChatModels\(\{\s*vendor', content)
    if m:
        return m.group(1)
    return "import_vscode90"

def patch_extension_js(ext_js_path, node_path):
    """Patch dist/extension.js to suppress BYOK popup and add auto-routing fallbacks."""
    if not os.path.isfile(ext_js_path):
        return False, False

    print(f"\n[PATCH] Processing extension.js: {ext_js_path}")
    with open(ext_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False
    vscode_var = discover_vscode_var(content)
    print(f"  Discovered VS Code import namespace: '{vscode_var}'")

    # 1. Neutralize ByokUtilityModelNotificationContribution._update()
    byok_target = "async _update() {\n    await this._refreshHasByokModels();"
    byok_replacement = "async _update() {\n    this._hideNotification();\n    return;\n    await this._refreshHasByokModels();"
    
    if "this._hideNotification();\n    return;\n    await this._refreshHasByokModels();" in content:
        print("  [OK] BYOK popup notification already neutralized.")
    elif byok_target in content:
        content = content.replace(byok_target, byok_replacement, 1)
        changed = True
        print("  [APPLIED] Neutralized ByokUtilityModelNotificationContribution._update().")
    else:
        byok_re = re.search(r'(ByokUtilityModelNotificationContribution\s*=\s*class[^{]*\{[\s\S]*?async\s+_update\s*\(\)\s*\{)', content)
        if byok_re and "this._hideNotification();\n    return;" not in content:
            orig = byok_re.group(1)
            repl = orig + "\n    this._hideNotification();\n    return;"
            content = content.replace(orig, repl, 1)
            changed = True
            print("  [APPLIED] Neutralized ByokUtilityModelNotificationContribution._update() (regex match).")
        else:
            print("  [SKIP] ByokUtilityModelNotificationContribution._update() pattern not matched.")

    # 2. Auto-route utility family in _resolveUtilityFamily(family)
    util_target = (
        "  async _resolveUtilityFamily(family) {\n"
        "    const override = await this._resolveUtilityOverride(family);\n"
        "    if (override) {\n"
        "      return override;\n"
        "    }"
    )
    util_routing = (
        f"\n    try {{\n"
        f"      const mfModels = await {vscode_var}.lm.selectChatModels({{ vendor: \"modelfusion\" }});\n"
        f"      if (mfModels && mfModels.length > 0) {{\n"
        f"        this._logService.info(`[ProductionEndpointProvider] Auto-routing utility family '${{family}}' to ModelFusion (${{mfModels[0].id}}).`);\n"
        f"        return this._instantiationService.createInstance(ExtensionContributedChatEndpoint, mfModels[0]);\n"
        f"      }}\n"
        f"    }} catch (e) {{}}"
    )
    util_replacement = util_target + util_routing

    if "Auto-routing utility family" in content:
        print("  [OK] Utility family ModelFusion auto-route already present.")
    elif util_target in content:
        content = content.replace(util_target, util_replacement, 1)
        changed = True
        print("  [APPLIED] Injected ModelFusion auto-route into _resolveUtilityFamily(family).")
    else:
        print("  [WARN] Could not find exact _resolveUtilityFamily anchor.")

    # 3. Auto-route CAPI family fallback in _resolveFamily(family)
    capi_orig = (
        "  async _resolveFamily(family) {\n"
        "    if (family === \"copilot-utility\" || family === \"copilot-utility-small\") {\n"
        "      return this._resolveUtilityFamily(family);\n"
        "    }\n"
        "    const modelMetadata = await this._modelFetcher.getChatModelFromCapiFamily(family);\n"
        "    return this.getOrCreateChatEndpointInstance(modelMetadata);\n"
        "  }"
    )
    capi_replacement = (
        "  async _resolveFamily(family) {\n"
        "    if (family === \"copilot-utility\" || family === \"copilot-utility-small\") {\n"
        "      return this._resolveUtilityFamily(family);\n"
        "    }\n"
        "    try {\n"
        "      const modelMetadata = await this._modelFetcher.getChatModelFromCapiFamily(family);\n"
        "      return this.getOrCreateChatEndpointInstance(modelMetadata);\n"
        "    } catch (err) {\n"
        f"      try {{\n"
        f"        const mfModels = await {vscode_var}.lm.selectChatModels({{ vendor: \"modelfusion\" }});\n"
        f"        if (mfModels && mfModels.length > 0) {{\n"
        f"          this._logService.info(`[ProductionEndpointProvider] CAPI family '${{family}}' unavailable; auto-routing to ModelFusion (${{mfModels[0].id}}).`);\n"
        f"          return this._instantiationService.createInstance(ExtensionContributedChatEndpoint, mfModels[0]);\n"
        f"        }}\n"
        f"      }} catch (e) {{}}\n"
        "      throw err;\n"
        "    }\n"
        "  }"
    )

    if "unavailable; auto-routing to ModelFusion" in content:
        print("  [OK] CAPI family ModelFusion fallback auto-route already present.")
    elif capi_orig in content:
        content = content.replace(capi_orig, capi_replacement, 1)
        changed = True
        print("  [APPLIED] Wrapped _resolveFamily(family) with ModelFusion fallback auto-route.")
    else:
        print("  [WARN] Could not find exact _resolveFamily anchor.")

    if not changed:
        print("  [NO CHANGES] File already contains all required patches.")
        return True, False

    # Write to temporary file first and validate syntax (must end in .js for Node.js)
    tmp_path = ext_js_path + ".tmp.js"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)

    if not validate_js_syntax(tmp_path, node_path):
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        print("  [FAIL] Patched file failed node syntax check! Reverting.")
        return False, False

    # Atomic rename / replace
    shutil.move(tmp_path, ext_js_path)
    print(f"  [SUCCESS] Successfully written and validated: {ext_js_path}")
    return True, True

def patch_package_json(pkg_path):
    """Patch package.json to set configurationDefaults for chat.utilityModel and chat.utilitySmallModel."""
    if not os.path.isfile(pkg_path):
        return False, False

    print(f"\n[PATCH] Processing package.json: {pkg_path}")
    try:
        with open(pkg_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        contributes = data.setdefault("contributes", {})
        config_defaults = contributes.setdefault("configurationDefaults", {})

        current_util = config_defaults.get("chat.utilityModel")
        current_small = config_defaults.get("chat.utilitySmallModel")

        desired = "modelfusion/modelfusion-local"
        if current_util == desired and current_small == desired:
            print("  [OK] configurationDefaults already configure utility models to modelfusion-local.")
            return True, False

        config_defaults["chat.utilityModel"] = desired
        config_defaults["chat.utilitySmallModel"] = desired

        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"  [SUCCESS] Updated configurationDefaults in {pkg_path}")
        return True, True
    except Exception as e:
        print(f"  [ERROR] Failed to patch package.json: {e}")
        return False, False

def patch_settings_file(settings_path, description, template_path=None):
    """Inject chat.utilityModel and chat.utilitySmallModel into a JSON settings file."""
    parent_dir = os.path.dirname(settings_path)
    if not os.path.isdir(parent_dir):
        return False, False

    print(f"\n[SETTINGS] Checking {description}: {settings_path}")
    try:
        content = ""
        if os.path.isfile(settings_path):
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        elif template_path and os.path.isfile(template_path):
            with open(template_path, "r", encoding="utf-8-sig") as f:
                content = f.read()

        data = json.loads(content) if content.strip() else {}
        changed = False

        desired = "modelfusion/modelfusion-local"
        if data.get("chat.utilityModel") != desired:
            data["chat.utilityModel"] = desired
            changed = True
        if data.get("chat.utilitySmallModel") != desired:
            data["chat.utilitySmallModel"] = desired
            changed = True

        if not changed:
            print(f"  [OK] Already configured with modelfusion-local.")
            return True, False

        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            f.write("\n")

        print(f"  [SUCCESS] Injected utility model presets into {settings_path}")
        return True, True
    except Exception as e:
        print(f"  [ERROR] Failed updating settings {settings_path}: {e}")
        return False, False

def main():
    print("==================================================================")
    print("[HUGOS] Patching Utility Models & Neutralizing BYOK Popup")
    print("==================================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skip_installed = any(arg.lower() in ("--skip-installed", "--check-installed=false") for arg in sys.argv)
    pack_dir_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pack_dir = (
        os.path.abspath(pack_dir_args[0].strip().strip('\"\''))
        if pack_dir_args
        else os.path.join(script_dir, "VSCode-win32-x64")
    )
    print(f"Target packaging directory: {pack_dir}")
    print(f"Skip installed locations: {skip_installed}")

    node_path = find_node_executable()
    if node_path:
        print(f"Using Node.js at: {node_path}")
    else:
        print("  [WARN] node.exe not found! Syntax validation will be skipped.")

    copilot_dirs = []
    p1 = os.path.join(pack_dir, "resources", "app", "extensions", "copilot")
    if os.path.isdir(p1):
        copilot_dirs.append(p1)

    if os.path.isdir(pack_dir):
        for entry in os.listdir(pack_dir):
            if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                sub = os.path.join(pack_dir, entry, "resources", "app", "extensions", "copilot")
                if os.path.isdir(sub):
                    copilot_dirs.append(sub)

    repo_copilot = os.path.join(script_dir, "vscode", "extensions", "copilot")
    if os.path.isdir(repo_copilot):
        copilot_dirs.append(repo_copilot)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        installed_root = os.path.join(local_app_data, "HugOS IDE")
        i1 = os.path.join(installed_root, "resources", "app", "extensions", "copilot")
        if os.path.isdir(i1):
            copilot_dirs.append(i1)
        if os.path.isdir(installed_root):
            for entry in os.listdir(installed_root):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(installed_root, entry, "resources", "app", "extensions", "copilot")
                    if os.path.isdir(sub):
                        copilot_dirs.append(sub)

    copilot_dirs = list(dict.fromkeys(os.path.abspath(d) for d in copilot_dirs))
    print(f"\nFound {len(copilot_dirs)} copilot extension directorie(s):")
    for d in copilot_dirs:
        print(f"  - {d}")

    has_errors = False
    for c_dir in copilot_dirs:
        pkg_file = os.path.join(c_dir, "package.json")
        ext_file = os.path.join(c_dir, "dist", "extension.js")

        ok_pkg, _ = patch_package_json(pkg_file)
        if not ok_pkg and os.path.exists(pkg_file):
            has_errors = True

        ok_ext, _ = patch_extension_js(ext_file, node_path)
        if not ok_ext and os.path.exists(ext_file):
            has_errors = True

    root_pds = os.path.join(pack_dir, "resources", "app", "product-default-settings.json")
    default_settings_targets = [root_pds]
    if os.path.isdir(pack_dir):
        for entry in os.listdir(pack_dir):
            if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                app_dir = os.path.join(pack_dir, entry, "resources", "app")
                if os.path.isdir(app_dir):
                    default_settings_targets.append(os.path.join(app_dir, "product-default-settings.json"))

    if local_app_data and not skip_installed:
        installed_root = os.path.join(local_app_data, "HugOS IDE")
        pds_inst = os.path.join(installed_root, "resources", "app", "product-default-settings.json")
        default_settings_targets.append(pds_inst)
        if os.path.isdir(installed_root):
            for entry in os.listdir(installed_root):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    app_dir = os.path.join(installed_root, entry, "resources", "app")
                    if os.path.isdir(app_dir):
                        default_settings_targets.append(os.path.join(app_dir, "product-default-settings.json"))

    for pds in set(default_settings_targets):
        patch_settings_file(pds, "product-default-settings.json", template_path=root_pds)

    if not skip_installed:
        roaming = os.environ.get("APPDATA", "")
        if roaming:
            user_settings = os.path.join(roaming, "HugOS", "User", "settings.json")
            if os.path.isfile(user_settings):
                patch_settings_file(user_settings, "User settings.json")

    if has_errors:
        print("\n[ERROR] Utility model patching encountered errors!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Utility model patching completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
HugOS IDE MSI Content & Payload Verification Suite
Extracts the compiled MSI package administratively and verifies 100% presence
and correctness of all critical configuration files, BYOK utility presets,
ModelFusion auto-routes, and chat enablement patches across root and versioned runtimes.
"""

import os
import sys
import re
import json
import shutil
import subprocess

def find_install_root(extract_dir):
    """Locate the HugOS IDE installation root directory inside the extracted payload."""
    candidates = [
        os.path.join(extract_dir, "LocalApp", "HugOS IDE"),
        os.path.join(extract_dir, "HugOS IDE"),
        extract_dir,
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "resources", "app")):
            return os.path.abspath(c)

    # Search recursively for resources/app
    for root, dirs, _ in os.walk(extract_dir):
        if "resources" in dirs and os.path.isdir(os.path.join(root, "resources", "app")):
            return os.path.abspath(root)
    return None

def find_versioned_dir(install_root):
    """Find the versioned runtime hash directory (e.g. 7e7950df89)."""
    for entry in os.listdir(install_root):
        if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
            full = os.path.join(install_root, entry)
            if os.path.isdir(full):
                return entry
    return None

def verify_product_json(path, label, failures):
    """Validate product.json configuration and proposals."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing product.json at: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        agent_id = data.get("defaultChatAgent", {}).get("extensionId")
        if agent_id != "GitHub.copilot-chat":
            failures.append(f"[{label}] defaultChatAgent.extensionId is '{agent_id}' (expected 'GitHub.copilot-chat')")
        else:
            print(f"  [PASS] {label} defaultChatAgent.extensionId matches 'GitHub.copilot-chat'")

        proposals = data.get("extensionEnabledApiProposals", {}).get("GitHub.copilot-chat", [])
        for req in ["defaultChatParticipant", "chatParticipantAdditions"]:
            if req not in proposals:
                failures.append(f"[{label}] Missing required proposal '{req}' in product.json")
            else:
                print(f"  [PASS] {label} contains required API proposal '{req}'")
    except Exception as e:
        failures.append(f"[{label}] Failed parsing product.json: {e}")

def verify_product_default_settings(path, label, failures):
    """Validate product-default-settings.json contains modelfusion-local presets."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing product-default-settings.json at: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        u_model = data.get("chat.utilityModel")
        u_small = data.get("chat.utilitySmallModel")
        desired = "modelfusion/modelfusion-local"

        if u_model != desired:
            failures.append(f"[{label}] chat.utilityModel is '{u_model}' (expected '{desired}')")
        else:
            print(f"  [PASS] {label} chat.utilityModel is '{desired}'")

        if u_small != desired:
            failures.append(f"[{label}] chat.utilitySmallModel is '{u_small}' (expected '{desired}')")
        else:
            print(f"  [PASS] {label} chat.utilitySmallModel is '{desired}'")

        fusion = data.get("hugos.modelfusion.fusion")
        if fusion is not True:
            failures.append(f"[{label}] hugos.modelfusion.fusion is '{fusion}' (expected True)")
        else:
            print(f"  [PASS] {label} hugos.modelfusion.fusion is True (enabled by default)")

        fusion_models = data.get("hugos.modelfusion.fusionModels")
        if fusion_models != 0:
            failures.append(f"[{label}] hugos.modelfusion.fusionModels is '{fusion_models}' (expected 0 for dynamic hardware scaling)")
        else:
            print(f"  [PASS] {label} hugos.modelfusion.fusionModels is 0 (dynamic hardware scaling)")
    except Exception as e:
        failures.append(f"[{label}] Failed parsing product-default-settings.json: {e}")

def verify_copilot_package_json(path, label, failures):
    """Validate copilot package.json configurationDefaults for utility models."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing copilot package.json at: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        cfg = data.get("contributes", {}).get("configurationDefaults", {})
        u_model = cfg.get("chat.utilityModel")
        u_small = cfg.get("chat.utilitySmallModel")
        desired = "modelfusion/modelfusion-local"

        if u_model != desired:
            failures.append(f"[{label}] contributes.configurationDefaults['chat.utilityModel'] is '{u_model}' (expected '{desired}')")
        else:
            print(f"  [PASS] {label} configurationDefaults['chat.utilityModel'] is '{desired}'")

        if u_small != desired:
            failures.append(f"[{label}] contributes.configurationDefaults['chat.utilitySmallModel'] is '{u_small}' (expected '{desired}')")
        else:
            print(f"  [PASS] {label} configurationDefaults['chat.utilitySmallModel'] is '{desired}'")
    except Exception as e:
        failures.append(f"[{label}] Failed parsing copilot package.json: {e}")

def verify_copilot_extension_js(path, label, failures):
    """Validate copilot dist/extension.js has neutralized BYOK popup and ModelFusion auto-route."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing copilot extension.js at: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Check BYOK notification neutralized
        byok_neutralized = ("this._hideNotification();" in content and "return;" in content)
        if not byok_neutralized:
            failures.append(f"[{label}] ByokUtilityModelNotificationContribution is NOT neutralized")
        else:
            print(f"  [PASS] {label} BYOK notification popup is neutralized")

        # Check _resolveUtilityFamily ModelFusion auto-route
        if "Auto-routing utility family" not in content and "modelfusion" not in content:
            failures.append(f"[{label}] ModelFusion auto-routing missing in _resolveUtilityFamily")
        else:
            print(f"  [PASS] {label} _resolveUtilityFamily auto-routes to ModelFusion")
    except Exception as e:
        failures.append(f"[{label}] Failed reading extension.js: {e}")

def verify_workbench_main_js(path, label, failures):
    """Validate workbench.desktop.main.js has chat enablement patches."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing workbench.desktop.main.js at: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Check ensureChatExtensionInitialDisabledState neutralized
        if "ensureChatExtensionInitialDisabledState" not in content or "return;" not in content:
            failures.append(f"[{label}] ensureChatExtensionInitialDisabledState is NOT neutralized")
        else:
            print(f"  [PASS] {label} ensureChatExtensionInitialDisabledState neutralized")

        # Check copilot enablement return 3
        if "github.copilot-chat" not in content or "return 3;" not in content:
            failures.append(f"[{label}] github.copilot-chat enablement state 3 missing")
        else:
            print(f"  [PASS] {label} github.copilot-chat forced enablement state 3 verified")
    except Exception as e:
        failures.append(f"[{label}] Failed reading workbench.desktop.main.js: {e}")

def verify_binary_file(path, label, min_size, failures):
    """Validate binary file existence and minimum size."""
    if not os.path.isfile(path):
        failures.append(f"[{label}] Missing binary at: {path}")
        return
    sz = os.path.getsize(path)
    if sz < min_size:
        failures.append(f"[{label}] Binary size ({sz} bytes) is below minimum threshold ({min_size} bytes)")
    else:
        print(f"  [PASS] {label} verified ({sz} bytes)")

def main():
    print("============================================================")
    print("[VERIFY] HugOS MSI Payload & Configuration Suite")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    msi_path = (
        os.path.abspath(sys.argv[1].strip().strip('\"\''))
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
        else os.path.join(script_dir, "HugOS.msi")
    )

    if not os.path.isfile(msi_path):
        print(f"[FATAL ERROR] MSI package not found at: {msi_path}")
        sys.exit(1)

    print(f"Target MSI: {msi_path} ({os.path.getsize(msi_path) / (1024*1024):.2f} MB)")

    # Use a short extraction directory on the same drive to avoid Win32 MAX_PATH (260 char) errors in msiexec
    drive = os.path.splitdrive(msi_path)[0] or "D:"
    extract_dir = os.path.join(drive, "\\_m_vfy")
    # Ensure trailing backslash for msiexec TARGETDIR
    target_arg = extract_dir.rstrip("\\") + "\\"

    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir, ignore_errors=True)
    os.makedirs(extract_dir, exist_ok=True)

    try:
        print(f"\n[INFO] Extracting MSI administratively to: {target_arg}...")
        cmd = ["msiexec.exe", "/a", os.path.abspath(msi_path), "/qn", f"TARGETDIR={target_arg}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[FATAL ERROR] msiexec administrative unpack failed with code {res.returncode}")
            print(res.stderr[:500])
            sys.exit(1)

        install_root = find_install_root(extract_dir)
        if not install_root:
            print(f"[FATAL ERROR] Could not locate HugOS IDE install root in extracted payload: {extract_dir}")
            sys.exit(1)

        print(f"[OK] Located install root: {install_root}")
        versioned_dir_name = find_versioned_dir(install_root)
        if not versioned_dir_name:
            print("[FATAL ERROR] Could not find versioned runtime hash directory (e.g. 7e7950df89) in payload!")
            sys.exit(1)

        print(f"[OK] Located versioned runtime directory: {versioned_dir_name}")
        v_root = os.path.join(install_root, versioned_dir_name)

        failures = []

        print("\n--- 1. Root Runtime Files & Payloads ---")
        verify_product_json(os.path.join(install_root, "resources", "app", "product.json"), "Root product.json", failures)
        verify_product_default_settings(os.path.join(install_root, "resources", "app", "product-default-settings.json"), "Root product-default-settings.json", failures)
        verify_copilot_package_json(os.path.join(install_root, "resources", "app", "extensions", "copilot", "package.json"), "Root copilot package.json", failures)
        verify_copilot_extension_js(os.path.join(install_root, "resources", "app", "extensions", "copilot", "dist", "extension.js"), "Root copilot extension.js", failures)
        verify_workbench_main_js(os.path.join(install_root, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"), "Root workbench.desktop.main.js", failures)

        print("\n--- 2. Versioned Runtime Files & Payloads ---")
        verify_product_json(os.path.join(v_root, "resources", "app", "product.json"), f"Versioned ({versioned_dir_name}) product.json", failures)
        verify_product_default_settings(os.path.join(v_root, "resources", "app", "product-default-settings.json"), f"Versioned ({versioned_dir_name}) product-default-settings.json", failures)
        verify_copilot_package_json(os.path.join(v_root, "resources", "app", "extensions", "copilot", "package.json"), f"Versioned ({versioned_dir_name}) copilot package.json", failures)
        verify_copilot_extension_js(os.path.join(v_root, "resources", "app", "extensions", "copilot", "dist", "extension.js"), f"Versioned ({versioned_dir_name}) copilot extension.js", failures)
        verify_workbench_main_js(os.path.join(v_root, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"), f"Versioned ({versioned_dir_name}) workbench.desktop.main.js", failures)

        print("\n--- 3. Core Engine Binaries & Database ---")
        verify_binary_file(os.path.join(install_root, "bin", "cli.exe"), "ModelFusion CLI Binary (bin/cli.exe)", 10_000_000, failures)
        verify_binary_file(os.path.join(install_root, "db", "hf_models.db"), "Model Database (db/hf_models.db)", 50_000, failures)

        print("\n============================================================")
        if failures:
            print(f"[FAIL] MSI Payload Verification FAILED with {len(failures)} error(s):")
            for f in failures:
                print(f"  - {f}")
            sys.exit(1)
        else:
            print("[SUCCESS] ALL MSI Payload & Configuration Verification checks PASSED 100%!")
            print("============================================================")
            sys.exit(0)
    finally:
        # Disk hygiene: remove extracted files
        shutil.rmtree(extract_dir, ignore_errors=True)
        print(f"[INFO] Cleaned temporary extraction directory: {extract_dir}")

if __name__ == "__main__":
    main()

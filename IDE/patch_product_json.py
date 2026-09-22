#!/usr/bin/env python3
"""
patch_product_json.py

Aligns defaultChatAgent extension IDs and injects all required
extensionEnabledApiProposals (including defaultChatParticipant)
across all development, packaging, and installed HugOS IDE product.json files.
Ensures files are saved without UTF-8 BOM.
"""

import os
import re
import sys
import json

def get_copilot_proposals(custom_pack_dir=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if custom_pack_dir and isinstance(custom_pack_dir, str):
        cleaned_custom = os.path.abspath(custom_pack_dir.strip().strip('\"\''))
        pack_dir = cleaned_custom if os.path.isdir(cleaned_custom) else os.path.join(script_dir, "VSCode-win32-x64")
    else:
        pack_dir = os.path.join(script_dir, "VSCode-win32-x64")

    possible_paths = [
        os.path.join(script_dir, "vscode", "extensions", "copilot", "package.json"),
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "package.json"),
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot-chat", "package.json"),
        os.path.join(pack_dir, "resources", "app", "extensions", "modelfusion", "package.json"),
    ]

    if os.path.isdir(pack_dir):
        for entry in os.listdir(pack_dir):
            if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                sub = os.path.join(pack_dir, entry)
                if os.path.isdir(sub):
                    possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "copilot", "package.json"))
                    possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "copilot-chat", "package.json"))
                    possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "modelfusion", "package.json"))

    if local_app_data:
        installed_base = os.path.join(local_app_data, "HugOS IDE")
        possible_paths.append(os.path.join(installed_base, "resources", "app", "extensions", "copilot", "package.json"))
        possible_paths.append(os.path.join(installed_base, "resources", "app", "extensions", "copilot-chat", "package.json"))
        possible_paths.append(os.path.join(installed_base, "resources", "app", "extensions", "modelfusion", "package.json"))
        if os.path.isdir(installed_base):
            for entry in os.listdir(installed_base):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(installed_base, entry)
                    if os.path.isdir(sub):
                        possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "copilot", "package.json"))
                        possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "copilot-chat", "package.json"))
                        possible_paths.append(os.path.join(sub, "resources", "app", "extensions", "modelfusion", "package.json"))

    for pkg_path in possible_paths:
        if os.path.isfile(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                proposals = data.get("enabledApiProposals", [])
                if proposals:
                    return proposals
            except Exception as e:
                print(f"  [WARN] Failed to read proposals from {pkg_path}: {e}")

    # Fallback list of 63 proposals
    return [
        "agentSessionsWorkspace", "agentsWindowConfiguration", "chatDebug", "chatHooks",
        "extensionsAny", "newSymbolNamesProvider", "interactive", "codeActionAI",
        "activeComment", "commentReveal", "contribCommentThreadAdditionalMenu",
        "contribCommentsViewThreadMenus", "contribChatEditorInlineGutterMenu",
        "documentFiltersExclusive", "embeddings", "findTextInFiles", "findTextInFiles2",
        "languageModelToolSupportsModel", "findFiles2", "textSearchProvider",
        "terminalDataWriteEvent", "terminalExecuteCommandEvent", "terminalSelection",
        "terminalQuickFixProvider", "mappedEditsProvider", "aiRelatedInformation",
        "aiSettingsSearch", "chatParticipantAdditions", "defaultChatParticipant",
        "contribSourceControlInputBoxMenu", "authLearnMore", "testObserver",
        "aiTextSearchProvider", "chatParticipantPrivate", "chatProvider",
        "contribDebugCreateConfiguration", "chatReferenceDiagnostic", "textSearchProvider2",
        "chatReferenceBinaryData", "languageModelSystem", "languageModelCapabilities",
        "languageModelPricing", "inlineCompletionsAdditions", "chatStatusItem",
        "chatInputNotification", "taskProblemMatcherStatus", "contribLanguageModelToolSets",
        "textDocumentChangeReason", "resolvers", "taskExecutionTerminal",
        "dataChannels", "languageModelThinkingPart", "chatSessionsProvider",
        "devDeviceId", "contribEditorContentMenu", "chatPromptFiles",
        "mcpServerDefinitions", "tabInputMultiDiff", "workspaceTrust",
        "environmentPower", "terminalTitle", "toolInvocationApproveCombination",
        "chatSessionCustomizationProvider"
    ]

def patch_product_file(file_path, proposals):
    if not os.path.isfile(file_path):
        return True, False  # (success, changed)

    try:
        has_bom = False
        try:
            with open(file_path, "rb") as bf:
                head = bf.read(3)
                if head == b"\xef\xbb\xbf" or head[:2] in (b"\xff\xfe", b"\xfe\xff"):
                    has_bom = True
        except Exception:
            pass

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [ERROR] Cannot read {file_path}: {e}")
            return False, False

        if not isinstance(data, dict):
            print(f"  [ERROR] {file_path} does not contain a JSON object (got {type(data).__name__})")
            return False, False

        changed = has_bom  # If file has BOM, force rewrite without BOM

        # 1. Align defaultChatAgent extension IDs (must match publisher.name in copilot package.json: GitHub.copilot-chat)
        dca = data.get("defaultChatAgent") or {}
        if not isinstance(dca, dict):
            dca = {}
            changed = True
        if dca.get("extensionId") != "GitHub.copilot-chat":
            dca["extensionId"] = "GitHub.copilot-chat"
            changed = True
        if dca.get("chatExtensionId") != "GitHub.copilot-chat":
            dca["chatExtensionId"] = "GitHub.copilot-chat"
            changed = True
        if dca.get("chatExtensionOutputId") != "GitHub.copilot-chat.GitHub Copilot Chat.log":
            dca["chatExtensionOutputId"] = "GitHub.copilot-chat.GitHub Copilot Chat.log"
            changed = True
        data["defaultChatAgent"] = dca

        # 2. Inject extensionEnabledApiProposals
        proposals_map = data.get("extensionEnabledApiProposals") or {}
        if not isinstance(proposals_map, dict):
            proposals_map = {}
            changed = True
        for ext_id in ["GitHub.copilot-chat", "GitHub.copilot", "HugOS.modelfusion"]:
            raw_props = proposals_map.get(ext_id)
            if not isinstance(raw_props, (list, set, tuple)):
                current = set()
            else:
                current = set(raw_props)
            updated = sorted(list(current.union(set(proposals))))
            if updated != proposals_map.get(ext_id):
                proposals_map[ext_id] = updated
                changed = True
        data["extensionEnabledApiProposals"] = proposals_map

        # 3. Ensure trustedExtensionAuthAccess has both IDs
        auth_access = data.get("trustedExtensionAuthAccess") or {}
        if not isinstance(auth_access, dict):
            auth_access = {}
            changed = True
        for provider in ["github", "github-enterprise"]:
            raw_list = auth_access.get(provider)
            if not isinstance(raw_list, list):
                cur_list = []
            else:
                cur_list = list(raw_list)
            for needed in ["GitHub.copilot", "GitHub.copilot-chat", "HugOS.modelfusion"]:
                if needed not in cur_list:
                    cur_list.append(needed)
                    changed = True
            auth_access[provider] = cur_list
        data["trustedExtensionAuthAccess"] = auth_access

        # 4. Neutralize/strip upstream Microsoft update URLs and quality to prevent accidental overwrites
        if "updateUrl" in data:
            del data["updateUrl"]
            changed = True
        if "quality" in data:
            del data["quality"]
            changed = True

        # 5. Enforce configurationDefaults for update.mode: none and disable auto updates
        cfg_defaults = data.get("configurationDefaults") or {}
        if not isinstance(cfg_defaults, dict):
            cfg_defaults = {}
            changed = True
        if cfg_defaults.get("update.mode") != "none":
            cfg_defaults["update.mode"] = "none"
            changed = True
        if cfg_defaults.get("update.enableWindowsBackgroundUpdates") is not False:
            cfg_defaults["update.enableWindowsBackgroundUpdates"] = False
            changed = True
        if cfg_defaults.get("update.showReleaseNotes") is not False:
            cfg_defaults["update.showReleaseNotes"] = False
            changed = True
        if cfg_defaults.get("extensions.autoCheckUpdates") is not False:
            cfg_defaults["extensions.autoCheckUpdates"] = False
            changed = True
        if cfg_defaults.get("extensions.autoUpdate") is not False:
            cfg_defaults["extensions.autoUpdate"] = False
            changed = True
        data["configurationDefaults"] = cfg_defaults

        if changed:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                bom_note = " (stripped BOM)" if has_bom else ""
                print(f"  [OK] Patched {file_path}{bom_note}")
                return True, True
            except Exception as e:
                print(f"  [ERROR] Failed to write {file_path}: {e}")
                return False, False
        else:
            print(f"  [INFO] Already up to date: {file_path}")
            return True, False
    except Exception as e:
        print(f"  [ERROR] Unexpected error while patching {file_path}: {e}")
        return False, False

def main():
    print("============================================================")
    print("[HUGOS] Patching product.json (defaultChatAgent & ApiProposals)")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    pack_dir = (
        os.path.abspath(sys.argv[1].strip().strip('\"\''))
        if len(sys.argv) > 1 and sys.argv[1].strip()
        else os.path.join(script_dir, "VSCode-win32-x64")
    )

    proposals = get_copilot_proposals(custom_pack_dir=pack_dir)
    print(f"  Loaded {len(proposals)} Copilot API proposals.")
    print(f"  Target packaging directory: {pack_dir}")

    local_app_data = os.environ.get("LOCALAPPDATA", "")

    targets = [
        os.path.join(script_dir, "patches", "product.json"),
        os.path.join(script_dir, "vscode", "product.json"),
        os.path.join(pack_dir, "resources", "app", "product.json"),
    ]

    base_dirs = [pack_dir]
    if local_app_data:
        base_dirs.append(os.path.join(local_app_data, "HugOS IDE"))
        targets.append(os.path.join(local_app_data, "HugOS IDE", "resources", "app", "product.json"))

    for b in base_dirs:
        if b and os.path.isdir(b):
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        v_pj = os.path.join(sub, "resources", "app", "product.json")
                        if v_pj not in targets:
                            targets.append(v_pj)

    seen = set()
    error_count = 0
    patched_count = 0
    for t in targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_product_file(t, proposals)
            if not success:
                error_count += 1
            elif changed:
                patched_count += 1

    if error_count > 0:
        print(f"\n[ERROR] product.json patching failed with {error_count} error(s)!")
        sys.exit(1)

    print(f"\n[HUGOS] product.json alignment complete! ({len(seen)} checked, {patched_count} modified)")
    sys.exit(0)

if __name__ == "__main__":
    main()

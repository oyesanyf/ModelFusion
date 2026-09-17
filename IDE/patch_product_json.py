#!/usr/bin/env python3
"""
patch_product_json.py

Aligns defaultChatAgent extension IDs and injects all required
extensionEnabledApiProposals (including defaultChatParticipant)
across all development, packaging, and installed HugOS IDE product.json files.
"""

import os
import json
import glob

def get_copilot_proposals():
    pkg_path = r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json"
    if not os.path.isfile(pkg_path):
        pkg_path = r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\package.json"
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("enabledApiProposals", [])
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
        return False

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [ERROR] Cannot read {file_path}: {e}")
        return False

    changed = False

    # 1. Align defaultChatAgent extension IDs
    dca = data.get("defaultChatAgent", {})
    if dca.get("extensionId") != "GitHub.copilot":
        dca["extensionId"] = "GitHub.copilot"
        changed = True
    if dca.get("chatExtensionId") != "GitHub.copilot-chat":
        dca["chatExtensionId"] = "GitHub.copilot-chat"
        changed = True
    if dca.get("chatExtensionOutputId") != "GitHub.copilot-chat.GitHub Copilot Chat.log":
        dca["chatExtensionOutputId"] = "GitHub.copilot-chat.GitHub Copilot Chat.log"
        changed = True
    data["defaultChatAgent"] = dca

    # 2. Inject extensionEnabledApiProposals
    proposals_map = data.get("extensionEnabledApiProposals", {})
    for ext_id in ["GitHub.copilot-chat", "GitHub.copilot", "HugOS.modelfusion"]:
        current = set(proposals_map.get(ext_id, []))
        updated = sorted(list(current.union(set(proposals))))
        if updated != proposals_map.get(ext_id):
            proposals_map[ext_id] = updated
            changed = True
    data["extensionEnabledApiProposals"] = proposals_map

    # 3. Ensure trustedExtensionAuthAccess has both IDs
    auth_access = data.get("trustedExtensionAuthAccess", {})
    for provider in ["github", "github-enterprise"]:
        cur_list = auth_access.get(provider, [])
        for needed in ["GitHub.copilot", "GitHub.copilot-chat", "HugOS.modelfusion"]:
            if needed not in cur_list:
                cur_list.append(needed)
                changed = True
        auth_access[provider] = cur_list
    data["trustedExtensionAuthAccess"] = auth_access

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"  [OK] Patched {file_path}")
        return True
    else:
        print(f"  [INFO] Already up to date: {file_path}")
        return False

def main():
    print("============================================================")
    print("[HUGOS] Patching product.json (defaultChatAgent & ApiProposals)")
    print("============================================================")

    proposals = get_copilot_proposals()
    print(f"  Loaded {len(proposals)} Copilot API proposals.")

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    targets = [
        r"D:\harfile\ModelFusion\IDE\patches\product.json",
        r"D:\harfile\ModelFusion\IDE\vscode\product.json",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\product.json",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\product.json",
        os.path.join(local_app_data, r"HugOS IDE\resources\app\product.json"),
        os.path.join(local_app_data, r"HugOS IDE\7e7950df89\resources\app\product.json"),
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\resources\app\product.json",
        r"C:\Users\oyesanyf\AppData\Local\HugOS IDE\7e7950df89\resources\app\product.json",
    ]

    seen = set()
    for t in targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            patch_product_file(t, proposals)

    print("\n[HUGOS] product.json alignment complete!")

if __name__ == "__main__":
    main()

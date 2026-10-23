#!/usr/bin/env python3
"""
HugOS IDE Language Model Availability Guard & ExtensionHost Hardening Script
Ensures:
1. ModelFusionLMProvider in extension.js, test-extension.js, and sanity-test-extension.js
   always exposes provideLanguageModelChatInformation, getAllModels, provideLanguageModelChatResponse,
   and _sendOrchestrationRequest (with direct Ollama :11434 fallback querying /api/ps then /api/tags).
2. BYOKContrib is registered BEFORE ConversationFeature in vscodeNodeContributions so the
   'modelfusion' language model provider is registered before chat participants initialize.
3. CopilotCLI buildAutoModel has isDefault: false, and ProductionEndpointProvider.getChatEndpoint
   routes session stub vendors ('copilotcli', 'claude-code') to ModelFusion instead of no-op stubs.
4. IntentDetector.provideParticipantDetection skips participant detection for non-Copilot vendors
   and catches errors so Ask-mode requests never abort before invokeAgent.
5. ExtHostLanguageModels in extensionHostProcess.js eagerly populates _localModels on provider
   registration, prioritizes 'modelfusion' in getDefaultLanguageModel, resolves local providers
   directly in selectLanguageModels/getLanguageModelByIdentifier/_sendChatRequest, and guards
   $detectChatParticipant and getModelForRequest against session stub vendors.
"""

import os
import re
import sys
import shutil
import subprocess


def find_node_executable():
    candidates = [
        r"D:\tools\nodejs\node.exe",
        shutil.which("node"),
        shutil.which("node.exe"),
        r"C:\Program Files\nodejs\node.exe",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None


def validate_js_syntax(file_path, node_path):
    if not node_path or not os.path.isfile(node_path):
        return True
    res = subprocess.run(
        [node_path, "--check", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=45,
    )
    if res.returncode != 0:
        print(f"  [SYNTAX ERROR] {file_path}:\n{res.stderr[:500]}")
        return False
    return True


def discover_vscode_var(content):
    idx = content.find("async _resolveUtilityOverride(family)")
    if idx != -1:
        chunk = content[idx : idx + 4000]
        m = re.search(r"([a-zA-Z0-9_$]+)\.lm\.selectChatModels", chunk)
        if m:
            return m.group(1)
    m = re.search(r"([a-zA-Z0-9_$]+)\.lm\.selectChatModels\(\{\s*vendor", content)
    if m:
        return m.group(1)
    return "import_vscode90"


def patch_ext_host_process(file_path, node_path):
    if not os.path.isfile(file_path):
        return True, False

    print(f"[PATCH] Checking extensionHostProcess.js: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Eagerly populate _localModels on registerLanguageModelChatProvider
    old_reg_prov = """  registerLanguageModelChatProvider(extension, vendor, provider) {
    this._languageModelProviders.set(vendor, { extension, provider });
    this._proxy.$registerLanguageModelProvider(vendor);"""
    new_reg_prov = """  registerLanguageModelChatProvider(extension, vendor, provider) {
    this._languageModelProviders.set(vendor, { extension, provider });
    this._proxy.$registerLanguageModelProvider(vendor);
    this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None).catch(() => {});"""
    if "this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None).catch(() => {});" not in content:
        if old_reg_prov in content:
            content = content.replace(old_reg_prov, new_reg_prov, 1)
            changed = True
            print("  [APPLIED] Eagerly populate _localModels in registerLanguageModelChatProvider.")

    # 2. Replace getDefaultLanguageModel with deterministic modelfusion-first & provider-resolving implementation
    gdlm_start_marker = "  async getDefaultLanguageModel(extension, forceResolveModels) {"
    gdlm_end_marker = "  async getLanguageModelByIdentifier(extension, modelId) {"
    s_idx = content.find(gdlm_start_marker)
    e_idx = content.find(gdlm_end_marker, s_idx) if s_idx != -1 else -1
    new_gdlm = """  async getDefaultLanguageModel(extension, forceResolveModels) {
    let defaultModelId;
    let hasModelFusionLocal = false;
    for (const [, mData] of this._localModels) {
      if (mData.metadata.vendor === "modelfusion") {
        hasModelFusionLocal = true;
        break;
      }
    }
    if (!hasModelFusionLocal && this._languageModelProviders.has("modelfusion")) {
      try {
        await this.$provideLanguageModelChatInfo("modelfusion", { silent: true }, CancellationToken.None);
      } catch (_) {}
    }
    if (forceResolveModels) {
      try {
        await this.selectLanguageModels(extension, {});
      } catch (_) {}
      if (!this._languageModelProviders.has("modelfusion")) {
        for (let waitStep = 0; waitStep < 30 && !this._languageModelProviders.has("modelfusion"); waitStep++) {
          await new Promise((r) => setTimeout(r, 50));
        }
      }
      for (const [vendor] of this._languageModelProviders) {
        try {
          await this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None);
        } catch (_) {}
      }
    }
    for (const [modelIdentifier, modelData] of this._localModels) {
      if (modelData.metadata.vendor === "modelfusion" && modelData.metadata.isDefaultForLocation?.["panel" /* Chat */]) {
        defaultModelId = modelIdentifier;
        break;
      }
    }
    if (!defaultModelId) {
      for (const [modelIdentifier, modelData] of this._localModels) {
        if (modelData.metadata.vendor === "modelfusion") {
          defaultModelId = modelIdentifier;
          break;
        }
      }
    }
    if (!defaultModelId) {
      for (const [modelIdentifier, modelData] of this._localModels) {
        if (modelData.metadata.isDefaultForLocation?.["panel" /* Chat */] && modelData.metadata.vendor === COPILOT_VENDOR_ID) {
          defaultModelId = modelIdentifier;
          break;
        }
      }
    }
    if (!defaultModelId && !forceResolveModels) {
      return this.getDefaultLanguageModel(extension, true);
    }
    if (!defaultModelId) {
      for (const [modelIdentifier, modelData] of this._localModels) {
        if (modelData.metadata.isDefaultForLocation?.["panel" /* Chat */] && modelData.metadata.vendor !== "copilotcli" && modelData.metadata.vendor !== "claude-code") {
          defaultModelId = modelIdentifier;
          break;
        }
      }
    }
    if (!defaultModelId) {
      for (const [modelIdentifier, modelData] of this._localModels) {
        if (modelData.metadata.vendor !== "copilotcli" && modelData.metadata.vendor !== "claude-code") {
          defaultModelId = modelIdentifier;
          break;
        }
      }
    }
    if (!defaultModelId) {
      for (const [modelIdentifier] of this._localModels) {
        defaultModelId = modelIdentifier;
        break;
      }
    }
    return this.getLanguageModelByIdentifier(extension, defaultModelId);
  }
"""
    if s_idx != -1 and e_idx != -1:
        current_gdlm = content[s_idx:e_idx]
        if current_gdlm != new_gdlm:
            content = content[:s_idx] + new_gdlm + content[e_idx:]
            changed = True
            print("  [APPLIED] Upgraded getDefaultLanguageModel with deterministic modelfusion priority and session-stub exclusion.")

    # 3. Harden getLanguageModelByIdentifier to query provider directly if _localModels cache misses
    old_by_id = """      await this._proxy.$selectChatModels({ vendor, extension: extension.identifier });
      if (!this._localModels.has(modelId)) {"""

    new_by_id = """      try {
        await this._proxy.$selectChatModels({ vendor, extension: extension.identifier });
      } catch (_) {}
      if (!this._localModels.has(modelId) && this._languageModelProviders.has(vendor)) {
        try {
          await this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None);
        } catch (_) {}
      }
      if (!this._localModels.has(modelId)) {"""

    if old_by_id in content:
        content = content.replace(old_by_id, new_by_id, 1)
        changed = True
        print("  [APPLIED] Hardened getLanguageModelByIdentifier with direct provider fallback.")

    # 4. Harden selectLanguageModels so vscode.lm.selectChatModels resolves local providers when main thread returns []
    sel_start_marker = "  async selectLanguageModels(extension, selector) {"
    sel_end_marker = "  async _sendChatRequest(extension, languageModelId, messages, options2, token) {"
    sel_s = content.find(sel_start_marker)
    sel_e = content.find(sel_end_marker, sel_s) if sel_s != -1 else -1
    new_sel = """  async selectLanguageModels(extension, selector) {
    let models = [];
    try {
      models = await this._proxy.$selectChatModels({ ...selector, extension: extension.identifier }) ?? [];
    } catch (_) {}
    const targetVendor = selector?.vendor;
    if (models.length === 0 || (targetVendor === "modelfusion" && !models.some((id) => String(id).startsWith("modelfusion/")))) {
      if (targetVendor && this._languageModelProviders.has(targetVendor)) {
        try {
          await this.$provideLanguageModelChatInfo(targetVendor, { silent: true }, CancellationToken.None);
        } catch (_) {}
      } else if (!targetVendor) {
        for (const [v] of this._languageModelProviders) {
          try {
            await this.$provideLanguageModelChatInfo(v, { silent: true }, CancellationToken.None);
          } catch (_) {}
        }
      }
      const fallbackIds = new Set(models);
      for (const [id, mData] of this._localModels) {
        const meta = mData.metadata;
        if ((!selector?.vendor || meta.vendor === selector.vendor) && (!selector?.id || meta.id === selector.id) && (!selector?.family || meta.family === selector.family) && (!selector?.version || meta.version === selector.version)) {
          fallbackIds.add(id);
        }
      }
      models = Array.from(fallbackIds);
    }
    const modelResults = await Promise.all(models.map((identifier) => this._createLanguageModelChatApi(extension, identifier)));
    return modelResults.filter((m) => !!m);
  }
"""
    if sel_s != -1 and sel_e != -1:
        current_sel = content[sel_s:sel_e]
        if current_sel != new_sel:
            content = content[:sel_s] + new_sel + content[sel_e:]
            changed = True
            print("  [APPLIED] Hardened selectLanguageModels with in-process provider fallback.")

    # 5. Harden _sendChatRequest so if $tryStartChatRequest fails during main-thread startup race,
    #    it executes the local provider's provideLanguageModelChatResponse directly in-process
    old_try_start = """    try {
      await this._proxy.$tryStartChatRequest(from, languageModelId, requestId, new SerializableObjectWithBuffers(internalMessages), options2, token);
    } catch (error) {
      this._pendingRequest.delete(requestId);
      throw LanguageModelError.tryDeserialize(error) ?? error;
    }"""

    new_try_start = """    try {
      await this._proxy.$tryStartChatRequest(from, languageModelId, requestId, new SerializableObjectWithBuffers(internalMessages), options2, token);
    } catch (error) {
      const knownModel = this._localModels.get(languageModelId);
      const provData = knownModel ? this._languageModelProviders.get(knownModel.metadata.vendor) : void 0;
      if (knownModel && provData) {
        const directProgress = new Progress(async (fragment) => {
          if (token.isCancellationRequested) {
            return;
          }
          let part;
          if (fragment instanceof LanguageModelToolCallPart) {
            part = { type: "tool_use", name: fragment.name, parameters: fragment.input, toolCallId: fragment.callId };
          } else if (fragment instanceof LanguageModelTextPart) {
            part = { type: "text", value: fragment.value, audience: fragment.audience };
          } else if (fragment instanceof LanguageModelDataPart) {
            part = { type: "data", mimeType: fragment.mimeType, data: VSBuffer.wrap(fragment.data), audience: fragment.audience };
          } else if (fragment instanceof LanguageModelThinkingPart) {
            part = { type: "thinking", value: fragment.value, id: fragment.id, metadata: fragment.metadata };
          }
          if (part) {
            res.handleResponsePart([part]);
          }
        });
        Promise.resolve(
          provData.provider.provideLanguageModelChatResponse(
            knownModel.info,
            internalMessages.map(LanguageModelChatMessage22.to),
            { ...options2, modelOptions: options2.modelOptions ?? {}, modelConfiguration: options2.configuration, requestInitiator: from ? ExtensionIdentifier.toKey(from) : "core", toolMode: options2.toolMode ?? 1 },
            directProgress,
            token
          )
        ).then(() => {
          this._pendingRequest.delete(requestId);
          res.resolve();
        }, (err) => {
          this._pendingRequest.delete(requestId);
          res.reject(err);
        });
        return res.apiObject;
      }
      this._pendingRequest.delete(requestId);
      throw LanguageModelError.tryDeserialize(error) ?? error;
    }"""

    if "const provData = knownModel ? this._languageModelProviders.get(knownModel.metadata.vendor) : void 0;" not in content:
        if old_try_start in content:
            content = content.replace(old_try_start, new_try_start, 1)
            changed = True
            print("  [APPLIED] Hardened _sendChatRequest with in-process provider fallback.")

    # 6. Guard $detectChatParticipant and getModelForRequest in ExtHostChatAgents2
    det_start = "  async $detectChatParticipant(handle, requestDto, context, options2, token) {"
    det_end = "  async _createRequest(requestDto, context, extension) {"
    d_s = content.find(det_start)
    d_e = content.find(det_end, d_s) if d_s != -1 else -1
    new_det = """  async $detectChatParticipant(handle, requestDto, context, options2, token) {
    try {
      const detector = this._participantDetectionProviders.get(handle);
      if (!detector) {
        return void 0;
      }
      const { request, location: location2, history } = await this._createRequest(requestDto, context, detector.extension);
      const model = await this.getModelForRequest(request, detector.extension);
      const tools = await this.getToolsForRequest(detector.extension, request.userSelectedTools, model.id, token);
      const extRequest = ChatAgentRequest.to(
        request,
        location2,
        model,
        request.modelConfiguration,
        this.getDiagnosticsWhenEnabled(detector.extension),
        tools,
        detector.extension,
        this._logService
      );
      return await detector.provider.provideParticipantDetection(
        extRequest,
        { history, yieldRequested: false },
        { participants: options2.participants, location: ChatLocation2.to(options2.location) },
        token
      );
    } catch (_) {
      return void 0;
    }
  }
"""
    if d_s != -1 and d_e != -1:
        if content[d_s:d_e] != new_det:
            content = content[:d_s] + new_det + content[d_e:]
            changed = True
            print("  [APPLIED] Guarded $detectChatParticipant with try/catch.")

    gmr_start = "  async getModelForRequest(request, extension) {"
    gmr_end = "  async $setRequestTools(requestId, tools) {"
    g_s = content.find(gmr_start)
    g_e = content.find(gmr_end, g_s) if g_s != -1 else -1
    new_gmr = """  async getModelForRequest(request, extension) {
    let model;
    if (request.userSelectedModelId && !String(request.userSelectedModelId).startsWith("copilotcli/") && !String(request.userSelectedModelId).startsWith("claude-code/")) {
      model = await this._languageModels.getLanguageModelByIdentifier(extension, request.userSelectedModelId);
    }
    if (!model) {
      model = await this._languageModels.getDefaultLanguageModel(extension);
      if (!model) {
        throw new Error("Language model unavailable");
      }
    }
    return model;
  }
"""
    if g_s != -1 and g_e != -1:
        if content[g_s:g_e] != new_gmr:
            content = content[:g_s] + new_gmr + content[g_e:]
            changed = True
            print("  [APPLIED] Guarded getModelForRequest against copilotcli/claude-code session stub IDs.")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        if not validate_js_syntax(file_path, node_path):
            return False, False
        print(f"  [SUCCESS] Updated and validated {file_path}")
        return True, True
    else:
        print("  [OK] Already hardened.")
        return True, False


def patch_provider_bundle(file_path, node_path):
    if not os.path.isfile(file_path):
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False
    vscode_var = discover_vscode_var(content)

    # 1. Prevent unhandled rejection on inflight.finally(...) derived Promise in Node v20+
    old_inflight = """            inflight.finally(() => {
              this._inflightMap.delete(promptText);
            });"""
    new_inflight = """            inflight.finally(() => {
              this._inflightMap.delete(promptText);
            }).catch(() => {});"""
    if old_inflight in content:
        content = content.replace(old_inflight, new_inflight, 1)
        changed = True
        print(f"  [APPLIED] Attached .catch(() => {{}}) to inflight.finally in {file_path}")

    # 2. Move BYOKContrib before ConversationFeature in vscodeNodeContributions so ModelFusionLMProvider
    #    registers BEFORE chat participants initialize
    old_contribs_head = """    vscodeNodeContributions = [
      ...contributions_default,
      asContributionFactory(ExtensionStateCommandContribution),
      asContributionFactory(ConversationFeature),"""
    new_contribs_head = """    vscodeNodeContributions = [
      ...contributions_default,
      asContributionFactory(ExtensionStateCommandContribution),
      asContributionFactory(BYOKContrib),
      asContributionFactory(ConversationFeature),"""
    old_contribs_tail = """      sessionSync_contribution_exports,
      asContributionFactory(BYOKContrib),
      asContributionFactory(DashboardContribution)"""
    new_contribs_tail = """      sessionSync_contribution_exports,
      asContributionFactory(DashboardContribution)"""
    if old_contribs_head in content and old_contribs_tail in content:
        content = content.replace(old_contribs_tail, new_contribs_tail, 1)
        content = content.replace(old_contribs_head, new_contribs_head, 1)
        changed = True
        print(f"  [APPLIED] Moved BYOKContrib before ConversationFeature in {file_path}")

    # Also fire modelFusion._onDidChange on BYOK registration
    old_byok_reg = """        this._register(import_vscode6.lm.registerLanguageModelChatProvider(ModelFusionLMProvider.providerId, modelFusion));"""
    new_byok_reg = """        this._register(import_vscode6.lm.registerLanguageModelChatProvider(ModelFusionLMProvider.providerId, modelFusion));
        try { modelFusion._onDidChange?.fire?.(); } catch (_) {}"""
    if "try { modelFusion._onDidChange?.fire?.(); } catch (_) {}" not in content:
        for v_match in re.finditer(r"this\._register\((import_vscode\d+)\.lm\.registerLanguageModelChatProvider\(ModelFusionLMProvider\.providerId,\s*modelFusion\)\);", content):
            orig_stmt = v_match.group(0)
            repl_stmt = orig_stmt + "\n        try { modelFusion._onDidChange?.fire?.(); } catch (_) {}"
            content = content.replace(orig_stmt, repl_stmt, 1)
            changed = True
            print(f"  [APPLIED] Added _onDidChange.fire() after ModelFusionLMProvider registration in {file_path}")
            break

    # 3. Change buildAutoModel isDefault: true -> isDefault: false so copilotcli/auto never hijacks default panel chat
    old_auto_model = """    targetChatSessionType: "copilotcli",
    isDefault: true
  };
}"""
    new_auto_model = """    targetChatSessionType: "copilotcli",
    isDefault: false
  };
}"""
    if old_auto_model in content:
        content = content.replace(old_auto_model, new_auto_model, 1)
        changed = True
        print(f"  [APPLIED] Set buildAutoModel isDefault: false in {file_path}")

    # 4. Route session stub vendors ('copilotcli', 'claude-code') to ModelFusion in ProductionEndpointProvider.getChatEndpoint
    old_vendor_check = """        if (model.vendor !== "copilot") {
          return this._instantiationService.createInstance(ExtensionContributedChatEndpoint, model);
        }"""
    new_vendor_check = f"""        if (model.vendor === "copilotcli" || model.vendor === "claude-code") {{
          const mfModels = await {vscode_var}.lm.selectChatModels({{ vendor: "modelfusion" }});
          if (mfModels && mfModels.length > 0) {{
            return this._instantiationService.createInstance(ExtensionContributedChatEndpoint, mfModels[0]);
          }}
        }}
        if (model.vendor !== "copilot") {{
          return this._instantiationService.createInstance(ExtensionContributedChatEndpoint, model);
        }}"""
    if 'if (model.vendor === "copilotcli" || model.vendor === "claude-code")' not in content and old_vendor_check in content:
        content = content.replace(old_vendor_check, new_vendor_check, 1)
        changed = True
        print(f"  [APPLIED] Routed copilotcli/claude-code session stubs to ModelFusion in getChatEndpoint of {file_path}")

    # 5. Guard IntentDetector.provideParticipantDetection so non-Copilot vendors skip participant detection
    old_part_det = """      async provideParticipantDetection(chatRequest, context2, options, token) {
        if (options.location !== 1 /* Panel */ && options.location !== 4 /* Editor */ || this.configurationService.getNonExtensionConfig("chat.detectParticipant.enabled") === false) {
          return;
        }"""
    new_part_det = """      async provideParticipantDetection(chatRequest, context2, options, token) {
        if (!chatRequest?.model || chatRequest.model.vendor !== "copilot") {
          return;
        }
        if (options.location !== 1 /* Panel */ && options.location !== 4 /* Editor */ || this.configurationService.getNonExtensionConfig("chat.detectParticipant.enabled") === false) {
          return;
        }"""
    if 'if (!chatRequest?.model || chatRequest.model.vendor !== "copilot")' not in content and old_part_det in content:
        content = content.replace(old_part_det, new_part_det, 1)
        changed = True
        print(f"  [APPLIED] Guarded provideParticipantDetection for non-Copilot models in {file_path}")

    # 6. Upgrade direct Ollama :11434 fallback in _sendOrchestrationRequest to check /api/ps warm models first,
    #    then /api/tags installed models before falling back to qwen2.5:1.5b
    for http_ident in ("http", "http2"):
        old_ps_only = f"""            const psReq = {http_ident}.request({{
              hostname: "127.0.0.1",
              port: 11434,
              path: "/api/ps",
              method: "GET",
              timeout: 1500
            }}, (pRes) => {{
              let pData = "";
              pRes.on("data", (c) => {{ pData += c; }});
              pRes.on("end", () => {{
                try {{
                  const pj = JSON.parse(pData);
                  const warm = (pj.models || []).map((m) => m.name).filter((n) => n && !/embed|nomic|bge|moondream|llava/i.test(n));
                  if (warm.length > 0) {{
                    tryOllamaDirect(warm[0]);
                    return;
                  }}
                }} catch (_) {{}}
                tryOllamaDirect(model && model !== "modelfusion-local" ? model : "qwen2.5:1.5b");
              }});
            }});
            psReq.on("error", () => tryOllamaDirect("qwen2.5:1.5b"));
            psReq.on("timeout", () => {{ psReq.destroy(); tryOllamaDirect("qwen2.5:1.5b"); }});
            psReq.end();"""

        old_tags_only = f"""            const tagsReq = {http_ident}.request({{
              hostname: "127.0.0.1",
              port: 11434,
              path: "/api/tags",
              method: "GET",
              timeout: 2000
            }}, (tRes) => {{
              let tData = "";
              tRes.on("data", (c) => {{ tData += c; }});
              tRes.on("end", () => {{
                let picked = model && model !== "modelfusion-local" ? model : "";
                if (!picked) {{
                  try {{
                    const tj = JSON.parse(tData);
                    const avail = (tj.models || []).map((m) => m.name).filter(Boolean);
                    for (const pref of ["qwen2.5:32b", "qwen2.5:14b", "qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b"]) {{
                      if (avail.includes(pref)) {{ picked = pref; break; }}
                    }}
                    if (!picked && avail.length > 0) picked = avail[0];
                  }} catch (_) {{}}
                }}
                tryOllamaDirect(picked || "qwen2.5:1.5b");
              }});
            }});
            tagsReq.on("error", () => reject(e4));
            tagsReq.on("timeout", () => {{ tagsReq.destroy(); reject(e4); }});
            tagsReq.end();"""

        new_ps_then_tags = f"""            const queryTagsFallback = () => {{
              const tagsReq = {http_ident}.request({{
                hostname: "127.0.0.1",
                port: 11434,
                path: "/api/tags",
                method: "GET",
                timeout: 1500
              }}, (tRes) => {{
                let tData = "";
                tRes.on("data", (c) => {{ tData += c; }});
                tRes.on("end", () => {{
                  let picked = model && model !== "modelfusion-local" ? model : "";
                  if (!picked) {{
                    try {{
                      const tj = JSON.parse(tData);
                      const avail = (tj.models || []).map((m) => m.name).filter((n) => n && !/embed|nomic|bge|moondream|llava/i.test(n));
                      for (const pref of ["qwen2.5:32b", "qwen2.5:14b", "qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b"]) {{
                        if (avail.includes(pref)) {{ picked = pref; break; }}
                      }}
                      if (!picked && avail.length > 0) picked = avail[0];
                    }} catch (_) {{}}
                  }}
                  tryOllamaDirect(picked || "qwen2.5:1.5b");
                }});
              }});
              tagsReq.on("error", () => tryOllamaDirect("qwen2.5:1.5b"));
              tagsReq.on("timeout", () => {{ tagsReq.destroy(); tryOllamaDirect("qwen2.5:1.5b"); }});
              tagsReq.end();
            }};
            const psReq = {http_ident}.request({{
              hostname: "127.0.0.1",
              port: 11434,
              path: "/api/ps",
              method: "GET",
              timeout: 1500
            }}, (pRes) => {{
              let pData = "";
              pRes.on("data", (c) => {{ pData += c; }});
              pRes.on("end", () => {{
                try {{
                  const pj = JSON.parse(pData);
                  const warm = (pj.models || []).map((m) => m.name).filter((n) => n && !/embed|nomic|bge|moondream|llava/i.test(n));
                  if (warm.length > 0) {{
                    tryOllamaDirect(warm[0]);
                    return;
                  }}
                }} catch (_) {{}}
                queryTagsFallback();
              }});
            }});
            psReq.on("error", () => queryTagsFallback());
            psReq.on("timeout", () => {{ psReq.destroy(); queryTagsFallback(); }});
            psReq.end();"""

        if "const queryTagsFallback = () => {" not in content:
            if old_ps_only in content:
                content = content.replace(old_ps_only, new_ps_then_tags, 1)
                changed = True
                print(f"  [APPLIED] Upgraded Ollama :11434 fallback to check /api/ps then /api/tags in {file_path}")
            elif old_tags_only in content:
                content = content.replace(old_tags_only, new_ps_then_tags, 1)
                changed = True
                print(f"  [APPLIED] Upgraded Ollama :11434 fallback to check /api/ps then /api/tags in {file_path}")

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    idx_p = content.find("ModelFusionLMProvider = class extends AbstractLanguageModelChatProvider")
    idx_e = content.find("async provideTokenCount(", idx_p)
    cls_slice = content[idx_p:idx_e] if idx_p != -1 and idx_e != -1 else ""
    for req_m in ("async getAllModels(", "async provideLanguageModelChatResponse(", "_sendOrchestrationRequest("):
        if req_m not in cls_slice:
            print(f"[FATAL] Missing {req_m} in ModelFusionLMProvider of {file_path}!")
            return False
    return validate_js_syntax(file_path, node_path)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    node_path = find_node_executable()
    pack_dir = os.path.join(script_dir, "VSCode-win32-x64")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    hugos_installed = os.path.join(local_app_data, "HugOS IDE") if local_app_data else ""

    # 1. Harden and sync authoritative dist/{extension.js,test-extension.js,sanity-test-extension.js} to all runtime dirs
    src_dist = os.path.join(script_dir, "vscode", "extensions", "copilot", "dist")
    for fname in ("extension.js", "test-extension.js", "sanity-test-extension.js"):
        fpath = os.path.join(src_dist, fname)
        if not patch_provider_bundle(fpath, node_path):
            sys.exit(1)

    base_dirs = [pack_dir]
    if hugos_installed and os.path.isdir(hugos_installed):
        base_dirs.append(hugos_installed)

    runtime_roots = []
    for b in base_dirs:
        if b and os.path.isdir(b):
            runtime_roots.append(b)
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        runtime_roots.append(sub)

    for root in runtime_roots:
        dst_dist = os.path.join(root, "resources", "app", "extensions", "copilot", "dist")
        if os.path.isdir(dst_dist):
            for fname in ("extension.js", "test-extension.js", "sanity-test-extension.js"):
                src_file = os.path.join(src_dist, fname)
                dst_file = os.path.join(dst_dist, fname)
                if os.path.isfile(src_file) and os.path.abspath(src_file) != os.path.abspath(dst_file):
                    try:
                        shutil.copy2(src_file, dst_file)
                        print(f"[SYNC] Copied {fname} -> {dst_file}")
                    except Exception as e:
                        print(f"[WARN] Could not copy {fname} -> {dst_file} (may be locked): {e}")

        ext_host_js = os.path.join(root, "resources", "app", "out", "vs", "workbench", "api", "node", "extensionHostProcess.js")
        if os.path.isfile(ext_host_js):
            ok, _ = patch_ext_host_process(ext_host_js, node_path)
            if not ok:
                sys.exit(1)

    print("[SUCCESS] Language model availability guard & ExtensionHost hardening complete.")


if __name__ == "__main__":
    main()

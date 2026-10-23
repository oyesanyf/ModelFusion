#!/usr/bin/env python3
"""
HugOS IDE Language Model Availability Guard & ExtensionHost Hardening Script
Ensures:
1. ModelFusionLMProvider in extension.js, test-extension.js, and sanity-test-extension.js
   always exposes provideLanguageModelChatInformation, getAllModels, provideLanguageModelChatResponse,
   and _sendOrchestrationRequest (with direct Ollama :11434 fallback if port 5000 is starting up).
2. ExtHostLanguageModels in extensionHostProcess.js resolves local language model providers
   directly in-process if main-thread model indexing is still initializing on first chat request,
   preventing Error("Language model unavailable").
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


def patch_ext_host_process(file_path, node_path):
    if not os.path.isfile(file_path):
        return True, False

    print(f"[PATCH] Checking extensionHostProcess.js: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Harden getDefaultLanguageModel to populate _localModels from _languageModelProviders if empty
    old_get_default = """    if (forceResolveModels) {
      await this.selectLanguageModels(extension, {});
    }"""

    new_get_default = """    if (forceResolveModels) {
      try {
        await this.selectLanguageModels(extension, {});
      } catch (_) {}
      if (this._localModels.size === 0 && this._languageModelProviders.size > 0) {
        for (const [vendor] of this._languageModelProviders) {
          try {
            await this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None);
          } catch (_) {}
        }
      }
    }"""

    if "await this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None);" not in content:
        if old_get_default in content:
            content = content.replace(old_get_default, new_get_default, 1)
            changed = True
            print("  [APPLIED] Hardened getDefaultLanguageModel with direct provider fallback.")

    # Also guard isDefaultForLocation optional chaining and prioritize modelfusion vendor in getDefaultLanguageModel
    for old_loc_check_1 in (
        'if (modelData.metadata.isDefaultForLocation["panel" /* Chat */] && modelData.metadata.vendor === COPILOT_VENDOR_ID)',
        'if (modelData.metadata.isDefaultForLocation?.["panel" /* Chat */] && modelData.metadata.vendor === COPILOT_VENDOR_ID)',
    ):
        new_loc_check_1 = 'if (modelData.metadata.isDefaultForLocation?.["panel" /* Chat */] && (modelData.metadata.vendor === "modelfusion" || modelData.metadata.vendor === COPILOT_VENDOR_ID))'
        if old_loc_check_1 in content:
            content = content.replace(old_loc_check_1, new_loc_check_1, 1)
            changed = True

    old_loc_check_2 = 'if (modelData.metadata.isDefaultForLocation["panel" /* Chat */])'
    new_loc_check_2 = 'if (modelData.metadata.isDefaultForLocation?.["panel" /* Chat */])'
    if old_loc_check_2 in content:
        content = content.replace(old_loc_check_2, new_loc_check_2, 1)
        changed = True

    # 2. Harden getLanguageModelByIdentifier to query provider directly if _localModels cache misses
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

    # 3. Harden _sendChatRequest so if $tryStartChatRequest fails during main-thread startup race,
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

    # 2. Upgrade direct Ollama :11434 fallback in _sendOrchestrationRequest to check /api/ps warm models first
    old_ollama_tags = r"""            const tagsReq = http.request({
              hostname: "127.0.0.1",
              port: 11434,
              path: "/api/tags",
              method: "GET",
              timeout: 2000
            }, (tRes) => {
              let tData = "";
              tRes.on("data", (c) => { tData += c; });
              tRes.on("end", () => {
                let picked = model && model !== "modelfusion-local" ? model : "";
                if (!picked) {
                  try {
                    const tj = JSON.parse(tData);
                    const avail = (tj.models || []).map((m) => m.name).filter(Boolean);
                    for (const pref of ["qwen2.5:32b", "qwen2.5:14b", "qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b"]) {
                      if (avail.includes(pref)) { picked = pref; break; }
                    }
                    if (!picked && avail.length > 0) picked = avail[0];
                  } catch (_) {}
                }
                tryOllamaDirect(picked || "qwen2.5:1.5b");
              });
            });
            tagsReq.on("error", () => reject(e4));
            tagsReq.on("timeout", () => { tagsReq.destroy(); reject(e4); });
            tagsReq.end();"""

    new_ollama_tags = r"""            const psReq = http.request({
              hostname: "127.0.0.1",
              port: 11434,
              path: "/api/ps",
              method: "GET",
              timeout: 1500
            }, (pRes) => {
              let pData = "";
              pRes.on("data", (c) => { pData += c; });
              pRes.on("end", () => {
                try {
                  const pj = JSON.parse(pData);
                  const warm = (pj.models || []).map((m) => m.name).filter((n) => n && !/embed|nomic|bge|moondream|llava/i.test(n));
                  if (warm.length > 0) {
                    tryOllamaDirect(warm[0]);
                    return;
                  }
                } catch (_) {}
                tryOllamaDirect(model && model !== "modelfusion-local" ? model : "qwen2.5:1.5b");
              });
            });
            psReq.on("error", () => tryOllamaDirect("qwen2.5:1.5b"));
            psReq.on("timeout", () => { psReq.destroy(); tryOllamaDirect("qwen2.5:1.5b"); });
            psReq.end();"""

    if old_ollama_tags in content:
        content = content.replace(old_ollama_tags, new_ollama_tags, 1)
        changed = True
        print(f"  [APPLIED] Upgraded direct Ollama :11434 fallback to use warm /api/ps model in {file_path}")

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

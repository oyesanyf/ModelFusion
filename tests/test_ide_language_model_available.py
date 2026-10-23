"""
End-to-End Verification Suite for HugOS IDE Language Model Availability & General Chat Q&A.
Verifies:
1. ModelFusionLMProvider in extension.js, test-extension.js, and sanity-test-extension.js
   retains getAllModels, provideLanguageModelChatInformation, provideLanguageModelChatResponse,
   and _sendOrchestrationRequest across all IDE distributions and passes `node --check`.
2. BYOKContrib is registered before ConversationFeature in vscodeNodeContributions,
   buildAutoModel sets isDefault: false, _resolveUtilityFamily/_resolveFamily auto-route to
   ModelFusion, and provideParticipantDetection skips non-Copilot models.
3. extensionHostProcess.js in IDE/VSCode-win32-x64 contains hardened registerLanguageModelChatProvider,
   getDefaultLanguageModel, selectLanguageModels, getLanguageModelByIdentifier, _sendChatRequest,
   getModelForRequest, and $detectChatParticipant so Error("Language model unavailable") is never thrown
   even when copilotcli/auto is in _localModels or main-thread $selectChatModels returns [].
4. workbench.desktop.main.js resolves language models immediately on registerLanguageModelProvider,
   marks modelfusion vendor isDefault: true, and guards Ask-mode detectAgentOrCommand in try/catch.
5. Real end-to-end execution of ModelFusionLMProvider.provideLanguageModelChatInformation and
   ModelFusionLMProvider.provideLanguageModelChatResponse for general prompts ("WHAT IS THE CAPITAL OF NIGERIA"
   and "why") returns accurate answers from the live local model with zero "Language model unavailable" errors.
"""

import json
import os
import shutil
import subprocess
import tempfile
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDE_DIR = os.path.join(REPO_ROOT, "IDE")


def find_node():
    for candidate in (
        r"D:\tools\nodejs\node.exe",
        shutil.which("node"),
        shutil.which("node.exe"),
        r"C:\Program Files\nodejs\node.exe",
    ):
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    pytest.skip("Node.js executable not found")


def test_all_extension_bundles_have_lm_provider_methods():
    node_bin = find_node()
    bundles = [
        os.path.join(IDE_DIR, "vscode", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(IDE_DIR, "vscode", "extensions", "copilot", "dist", "test-extension.js"),
        os.path.join(IDE_DIR, "vscode", "extensions", "copilot", "dist", "sanity-test-extension.js"),
        os.path.join(IDE_DIR, "VSCode-win32-x64", "resources", "app", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(IDE_DIR, "VSCode-win32-x64", "resources", "app", "extensions", "copilot", "dist", "test-extension.js"),
        os.path.join(IDE_DIR, "VSCode-win32-x64", "resources", "app", "extensions", "copilot", "dist", "sanity-test-extension.js"),
    ]
    required_methods = [
        "async provideLanguageModelChatInformation(",
        "async getAllModels(",
        "async provideLanguageModelChatResponse(",
        "_sendOrchestrationRequest(",
        "async _runDatabaseUpdate()",
        "_spawnCliFallback(",
        "async provideTokenCount(",
    ]
    for bpath in bundles:
        assert os.path.isfile(bpath), f"Missing bundle: {bpath}"
        with open(bpath, "r", encoding="utf-8") as f:
            content = f.read()
        idx_start = content.find("ModelFusionLMProvider = class extends AbstractLanguageModelChatProvider")
        assert idx_start != -1, f"ModelFusionLMProvider class not found in {bpath}"
        idx_end = content.find("async provideTokenCount(", idx_start)
        assert idx_end != -1, f"provideTokenCount not found in {bpath}"
        class_body = content[idx_start : idx_end + 500]
        for m in required_methods:
            assert m in class_body, f"Missing method {m} in ModelFusionLMProvider of {bpath}"

        # Verify BYOKContrib is registered before ConversationFeature
        idx_byok = content.find("asContributionFactory(BYOKContrib)")
        idx_conv = content.find("asContributionFactory(ConversationFeature)")
        assert idx_byok != -1 and idx_conv != -1 and idx_byok < idx_conv, (
            f"Expected BYOKContrib before ConversationFeature in {bpath}"
        )

        # Verify buildAutoModel has isDefault: false
        assert 'targetChatSessionType: "copilotcli",\n    isDefault: false' in content, (
            f"buildAutoModel still has isDefault: true in {bpath}"
        )

        # Verify utility family & CAPI family ModelFusion auto-routes are present
        assert "Auto-routing utility family" in content, f"Missing _resolveUtilityFamily auto-route in {bpath}"
        assert "unavailable; auto-routing to ModelFusion" in content, f"Missing _resolveFamily auto-route in {bpath}"

        # Verify provideParticipantDetection skips non-Copilot models
        assert 'if (!chatRequest?.model || chatRequest.model.vendor !== "copilot")' in content, (
            f"Missing provideParticipantDetection guard in {bpath}"
        )

        # Verify /api/ps + /api/tags fallback in _sendOrchestrationRequest
        assert "const queryTagsFallback = () => {" in content, f"Missing queryTagsFallback in {bpath}"

        res = subprocess.run([node_bin, "--check", bpath], capture_output=True, text=True, timeout=45)
        assert res.returncode == 0, f"node --check failed for {bpath}: {res.stderr}"


def test_workbench_main_language_models_service_hardened():
    node_bin = find_node()
    wb_path = os.path.join(
        IDE_DIR, "VSCode-win32-x64", "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"
    )
    assert os.path.isfile(wb_path), f"Missing {wb_path}"
    with open(wb_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'isDefault: item.vendor === "modelfusion" ? true : item.isDefault ?? false' in content
    assert "this._providers.set(vendor, provider);\n    this._resolveAllLanguageModels(vendor, true);" in content
    assert 'this._resolveAllLanguageModels("modelfusion", true);' in content
    assert "try {\n              const result = await this.chatAgentService.detectAgentOrCommand(" in content

    res = subprocess.run([node_bin, "--check", wb_path], capture_output=True, text=True, timeout=45)
    assert res.returncode == 0, f"node --check failed for {wb_path}: {res.stderr}"


def test_extension_host_process_hardened_and_adversarial_races():
    """
    Tests both static hardening of extensionHostProcess.js and live Node.js execution
    of the actual getDefaultLanguageModel, selectLanguageModels, getModelForRequest,
    and $detectChatParticipant methods under adversarial startup race conditions:
      - copilotcli/auto already populated in _localModels with isDefaultForLocation.panel = true
      - main-thread $selectChatModels returning []
      - userSelectedModelId set to "copilotcli/auto"
      - $detectChatParticipant throwing inside provideParticipantDetection
    """
    node_bin = find_node()
    ext_host = os.path.join(
        IDE_DIR, "VSCode-win32-x64", "resources", "app", "out", "vs", "workbench", "api", "node", "extensionHostProcess.js"
    )
    assert os.path.isfile(ext_host), f"Missing {ext_host}"
    with open(ext_host, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None).catch(() => {});' in content
    assert 'if (modelData.metadata.vendor === "modelfusion" && modelData.metadata.isDefaultForLocation?.["panel" /* Chat */])' in content
    assert 'const provData = knownModel ? this._languageModelProviders.get(knownModel.metadata.vendor) : void 0;' in content
    assert '!String(request.userSelectedModelId).startsWith("copilotcli/")' in content

    res = subprocess.run([node_bin, "--check", ext_host], capture_output=True, text=True, timeout=45)
    assert res.returncode == 0, f"node --check failed for {ext_host}: {res.stderr}"

    # Extract actual getDefaultLanguageModel and selectLanguageModels from extensionHostProcess.js
    gdlm_s = content.find("  async getDefaultLanguageModel(extension, forceResolveModels) {")
    gdlm_e = content.find("  async _sendChatRequest(extension, languageModelId, messages, options2, token) {", gdlm_s)
    assert gdlm_s != -1 and gdlm_e != -1
    ext_host_methods_js = content[gdlm_s:gdlm_e]

    gmr_s = content.find("  async getModelForRequest(request, extension) {")
    gmr_e = content.find("  async $setRequestTools(requestId, tools) {", gmr_s)
    assert gmr_s != -1 and gmr_e != -1
    gmr_js = content[gmr_s:gmr_e]

    det_s = content.find("  async $detectChatParticipant(handle, requestDto, context, options2, token) {")
    det_e = content.find("  async _createRequest(requestDto, context, extension) {", det_s)
    assert det_s != -1 and det_e != -1
    det_js = content[det_s:det_e]

    race_test_js = f"""
const CancellationToken = {{ None: {{ isCancellationRequested: false }} }};
const COPILOT_VENDOR_ID = "copilot";
const ChatAgentRequest = {{ to: () => ({{}}) }};
const ChatLocation2 = {{ to: () => 1 }};

class HarnessExtHostLM {{
  constructor() {{
    this._localModels = new Map();
    this._languageModelProviders = new Map();
    this._logService = {{ warn: () => {{}}, trace: () => {{}}, error: () => {{}} }};
    this._proxy = {{
      // Simulate main-thread race: $selectChatModels returns []!
      $selectChatModels: async () => []
    }};
  }}
  getVendorFromModelIdentifier(modelIdentifier) {{
    const idx = modelIdentifier.indexOf("/");
    return idx === -1 ? undefined : modelIdentifier.substring(0, idx);
  }}
  _isUsingAuth() {{ return false; }}
  async $provideLanguageModelChatInfo(vendor, options, token) {{
    const data = this._languageModelProviders.get(vendor);
    if (!data) return [];
    const infos = await data.provider.provideLanguageModelChatInformation(options, token);
    for (const info of infos) {{
      const id = `${{vendor}}/${{info.id}}`;
      this._localModels.set(id, {{
        group: undefined,
        metadata: {{
          vendor,
          id: info.id,
          name: info.name,
          family: info.family,
          version: info.version,
          isDefaultForLocation: info.isDefaultForLocation || {{ panel: true }},
          maxInputTokens: 32768,
          capabilities: {{ toolCalling: true }}
        }},
        info
      }});
    }}
    return infos;
  }}
{ext_host_methods_js}
}}

class HarnessChatAgents {{
  constructor(lm) {{
    this._languageModels = lm;
    this._participantDetectionProviders = new Map();
    this._logService = {{}};
  }}
  async _createRequest(dto) {{ return {{ request: dto, location: 1, history: [] }}; }}
  async getToolsForRequest() {{ return []; }}
  getDiagnosticsWhenEnabled() {{ return []; }}
{det_js}
{gmr_js}
}}

(async () => {{
  const lm = new HarnessExtHostLM();
  const ext = {{ identifier: {{ value: "GitHub.copilot-chat" }} }};

  // Adversarial Condition 1: copilotcli/auto is ALREADY in _localModels with isDefaultForLocation.panel = true,
  // while modelfusion provider is registered in _languageModelProviders but NOT yet in _localModels!
  lm._localModels.set("copilotcli/auto", {{
    group: undefined,
    metadata: {{
      vendor: "copilotcli",
      id: "auto",
      name: "Auto",
      family: "",
      version: "",
      isDefaultForLocation: {{ panel: true }},
      maxInputTokens: 0
    }},
    info: {{ id: "auto", name: "Auto" }}
  }});
  lm._languageModelProviders.set("modelfusion", {{
    extension: ext,
    provider: {{
      provideLanguageModelChatInformation: async () => [{{
        id: "modelfusion-local",
        name: "ModelFusion (Local Engine)",
        family: "modelfusion",
        version: "1.0.0",
        isDefaultForLocation: {{ panel: true }}
      }}]
    }}
  }});

  // Test A: getDefaultLanguageModel MUST return modelfusion/modelfusion-local, NOT copilotcli/auto!
  const defaultModel = await lm.getDefaultLanguageModel(ext);
  if (!defaultModel || defaultModel.vendor !== "modelfusion" || defaultModel.id !== "modelfusion-local") {{
    throw new Error("Test A failed: getDefaultLanguageModel returned " + JSON.stringify(defaultModel));
  }}

  // Test B: selectLanguageModels({{ vendor: "modelfusion" }}) MUST return [modelfusion-local] even when $selectChatModels returns []!
  lm._localModels.delete("modelfusion/modelfusion-local");
  const selectedMf = await lm.selectLanguageModels(ext, {{ vendor: "modelfusion" }});
  if (!selectedMf || selectedMf.length !== 1 || selectedMf[0].id !== "modelfusion-local") {{
    throw new Error("Test B failed: selectLanguageModels returned " + JSON.stringify(selectedMf));
  }}

  // Test C: getModelForRequest with userSelectedModelId = "copilotcli/auto" MUST ignore the session stub and return modelfusion-local!
  const agents = new HarnessChatAgents(lm);
  const reqModel = await agents.getModelForRequest({{ userSelectedModelId: "copilotcli/auto" }}, ext);
  if (!reqModel || reqModel.vendor !== "modelfusion" || reqModel.id !== "modelfusion-local") {{
    throw new Error("Test C failed: getModelForRequest returned " + JSON.stringify(reqModel));
  }}

  // Test D: $detectChatParticipant MUST catch errors and return undefined instead of crashing Ask mode!
  agents._participantDetectionProviders.set(1, {{
    extension: ext,
    provider: {{
      provideParticipantDetection: async () => {{
        throw new Error("Simulated CAPI utility model failure");
      }}
    }}
  }});
  const detResult = await agents.$detectChatParticipant(1, {{}}, {{}}, {{ participants: [], location: 1 }}, CancellationToken.None);
  if (detResult !== undefined) {{
    throw new Error("Test D failed: expected undefined from $detectChatParticipant, got " + JSON.stringify(detResult));
  }}

  console.log(JSON.stringify({{ ok: true, defaultVendor: defaultModel.vendor, defaultId: defaultModel.id }}));
}})().catch((e) => {{
  console.error(e);
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as tf:
        tf.write(race_test_js)
        temp_race_js = tf.name
    try:
        res = subprocess.run([node_bin, temp_race_js], capture_output=True, text=True, timeout=30)
        assert res.returncode == 0, f"Adversarial race test failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        payload = json.loads(res.stdout.strip().splitlines()[-1])
        assert payload["ok"] is True
        assert payload["defaultVendor"] == "modelfusion"
        assert payload["defaultId"] == "modelfusion-local"
    finally:
        if os.path.exists(temp_race_js):
            os.remove(temp_race_js)


def test_real_provider_chat_response_capital_of_nigeria_and_why():
    """
    Executes the real ModelFusionLMProvider code from IDE/vscode/extensions/copilot/dist/extension.js
    in Node.js against the live local ModelFusion / Ollama engine for:
      1. provideLanguageModelChatInformation({ silent: true }) and provideLanguageModelChatInformation(undefined)
      2. provideLanguageModelChatResponse("WHAT IS THE CAPITAL OF NIGERIA")
      3. provideLanguageModelChatResponse("why")
    """
    node_bin = find_node()
    ext_js = os.path.join(IDE_DIR, "vscode", "extensions", "copilot", "dist", "extension.js")
    with open(ext_js, "r", encoding="utf-8") as f:
        content = f.read()

    idx_start = content.find("ModelFusionLMProvider = class extends AbstractLanguageModelChatProvider")
    idx_close = content.find("ModelFusionLMProvider = __decorateClass([", idx_start)
    assert idx_start != -1 and idx_close != -1, "Could not locate ModelFusionLMProvider class boundaries"
    provider_class_code = content[idx_start:idx_close]

    harness_js = f"""
const child_process2 = require("child_process");
const fs3 = require("fs");
const path3 = require("path");
const http = require("http");
const os = require("os");

class LanguageModelTextPart3 {{
  constructor(value) {{ this.value = value; }}
}}
const st = LanguageModelTextPart3;

const vscode15 = {{
  window: {{
    createOutputChannel: () => ({{ appendLine: () => {{}}, show: () => {{}} }}),
    showInformationMessage: async () => undefined,
    showWarningMessage: async () => undefined,
    showErrorMessage: async () => undefined,
    activeTextEditor: undefined,
  }},
  workspace: {{
    getConfiguration: () => ({{
      get: (k, defVal) => defVal,
      update: async () => {{}},
    }}),
    onDidChangeTextDocument: () => ({{ dispose: () => {{}} }}),
    onDidChangeConfiguration: () => ({{ dispose: () => {{}} }}),
    workspaceFolders: [{{ uri: {{ fsPath: {json.dumps(REPO_ROOT)} }} }}],
  }},
  commands: {{
    registerCommand: () => ({{ dispose: () => {{}} }}),
    executeCommand: async () => {{}},
  }},
  Uri: {{ file: (p) => ({{ fsPath: p }}) }},
  CancellationTokenSource: class {{ constructor() {{ this.token = {{ isCancellationRequested: false, onCancellationRequested: () => ({{ dispose: () => {{}} }}) }}; }} }},
}};

class AbstractLanguageModelChatProvider {{
  constructor(id, name, knownModels, byokStorageService, logService) {{
    this._id = id;
    this._name = name;
    this._knownModels = knownModels;
    this._byokStorageService = byokStorageService;
    this._logService = logService;
  }}
  _register(d) {{ return d; }}
  async configureDefaultGroupWithApiKeyOnly() {{ return undefined; }}
  async provideLanguageModelChatInformation({{ silent, configuration }}, token) {{
    const models = await this.getAllModels(silent, undefined, configuration);
    return models.map((m) => ({{ ...m, isBYOK: true }}));
  }}
}}

class InlineDiffManager {{ registerCommands() {{}} }}
const TeamPresetManager = {{ getInstance: () => null }};
const ModelManagerPanel = {{ show: () => {{}} }};
const EvolutionStateManager = {{ getInstance: () => null }};
function notifyModelFusionError() {{}}
function getModelFusionOutputChannel() {{ return {{ appendLine: () => {{}} }}; }}

let ModelFusionLMProvider;
{provider_class_code}

// Neutralize background daemons inside short-lived test harness
ModelFusionLMProvider.prototype.startServer = function() {{}};
ModelFusionLMProvider.prototype._startWatcher = function() {{}};
ModelFusionLMProvider.prototype._startHealthCheckWatchdog = function() {{}};
ModelFusionLMProvider.prototype._checkOllamaInstallation = function() {{}};

(async () => {{
  const logService = {{ info: () => {{}}, warn: () => {{}}, error: () => {{}}, trace: () => {{}} }};
  const storageService = {{ getAPIKey: async () => undefined, deleteAPIKey: async () => {{}} }};
  const provider = new ModelFusionLMProvider(storageService, logService);

  // 1. Verify provideLanguageModelChatInformation with options and with undefined (edge case)
  const info1 = await provider.provideLanguageModelChatInformation({{ silent: true }}, {{}});
  const info2 = await provider.provideLanguageModelChatInformation(undefined, {{}});
  if (!Array.isArray(info1) || info1.length === 0 || info1[0].id !== "modelfusion-local") {{
    throw new Error("Invalid model info1: " + JSON.stringify(info1));
  }}
  if (!Array.isArray(info2) || info2.length === 0 || info2[0].id !== "modelfusion-local") {{
    throw new Error("Invalid model info2: " + JSON.stringify(info2));
  }}

  // 2. Ask "WHAT IS THE CAPITAL OF NIGERIA"
  const chunks1 = [];
  const progress1 = {{ report: (part) => chunks1.push(part?.value || String(part)) }};
  const token = {{ isCancellationRequested: false, onCancellationRequested: () => ({{ dispose: () => {{}} }}) }};
  await provider.provideLanguageModelChatResponse(
    info1[0],
    [{{ role: 1, content: "WHAT IS THE CAPITAL OF NIGERIA" }}],
    {{}},
    progress1,
    token
  );
  const answer1 = chunks1.join("");

  // 3. Ask follow-up "why"
  const chunks2 = [];
  const progress2 = {{ report: (part) => chunks2.push(part?.value || String(part)) }};
  await provider.provideLanguageModelChatResponse(
    info1[0],
    [
      {{ role: 1, content: "WHAT IS THE CAPITAL OF NIGERIA" }},
      {{ role: 2, content: answer1 }},
      {{ role: 1, content: "why" }}
    ],
    {{}},
    progress2,
    token
  );
  const answer2 = chunks2.join("");

  console.log(JSON.stringify({{
    modelId: info1[0].id,
    isDefaultForPanel: !!info1[0].isDefaultForLocation?.panel,
    answer1,
    answer2,
  }}));
  process.exit(0);
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as tf:
        tf.write(harness_js)
        temp_js_path = tf.name

    try:
        res = subprocess.run([node_bin, temp_js_path], capture_output=True, text=True, timeout=90)
        assert res.returncode == 0, f"Harness failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
        out_lines = [l.strip() for l in res.stdout.splitlines() if l.strip().startswith("{")]
        assert out_lines, f"No JSON output from harness: {res.stdout}"
        payload = json.loads(out_lines[-1])
        assert payload["modelId"] == "modelfusion-local"
        assert payload["isDefaultForPanel"] is True
        assert "Language model unavailable" not in payload["answer1"]
        assert "abuja" in payload["answer1"].lower(), f"Expected Abuja in answer1, got: {payload['answer1']}"
        assert "Language model unavailable" not in payload["answer2"]
        assert len(payload["answer2"].strip()) > 20, f"Expected substantive explanation for 'why', got: {payload['answer2']}"
    finally:
        if os.path.exists(temp_js_path):
            os.remove(temp_js_path)

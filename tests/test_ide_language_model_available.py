"""
End-to-End Verification Suite for HugOS IDE Language Model Availability & General Chat Q&A.
Verifies:
1. ModelFusionLMProvider in extension.js, test-extension.js, and sanity-test-extension.js
   retains getAllModels, provideLanguageModelChatInformation, provideLanguageModelChatResponse,
   and _sendOrchestrationRequest across all IDE distributions and passes `node --check`.
2. extensionHostProcess.js in IDE/VSCode-win32-x64 contains hardened getDefaultLanguageModel,
   getLanguageModelByIdentifier, and _sendChatRequest fallbacks so Error("Language model unavailable")
   is never thrown.
3. Real end-to-end execution of ModelFusionLMProvider.provideLanguageModelChatInformation and
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

        res = subprocess.run([node_bin, "--check", bpath], capture_output=True, text=True, timeout=45)
        assert res.returncode == 0, f"node --check failed for {bpath}: {res.stderr}"


def test_extension_host_process_hardened():
    node_bin = find_node()
    ext_host = os.path.join(
        IDE_DIR, "VSCode-win32-x64", "resources", "app", "out", "vs", "workbench", "api", "node", "extensionHostProcess.js"
    )
    assert os.path.isfile(ext_host), f"Missing {ext_host}"
    with open(ext_host, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'await this.$provideLanguageModelChatInfo(vendor, { silent: true }, CancellationToken.None);' in content
    assert 'modelData.metadata.vendor === "modelfusion"' in content
    assert 'const provData = knownModel ? this._languageModelProviders.get(knownModel.metadata.vendor) : void 0;' in content

    res = subprocess.run([node_bin, "--check", ext_host], capture_output=True, text=True, timeout=45)
    assert res.returncode == 0, f"node --check failed for {ext_host}: {res.stderr}"


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

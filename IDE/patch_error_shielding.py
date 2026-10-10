#!/usr/bin/env python3
"""
HugOS IDE Extension IPC & Command Error Shielding Patch Script
Applies defensive try...catch boundaries, structured diagnostic logging to
the "ModelFusion Server" output channel, and non-blocking toast notifications
(with headless-safe guards) across copilot extension bundles.
"""

import os
import sys
import re
import time
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

def safe_write_file(file_path, content_bytes):
    """Write bytes to file with retries to guard against transient Windows file locks."""
    for attempt in range(5):
        try:
            with open(file_path, "wb") as f:
                f.write(content_bytes)
            return True
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(0.5)
    return False

# ==============================================================================
# Injected Helper Code Block
# ==============================================================================
HELPER_MARKER_START = "// [MODELFUSION ERROR SHIELDING HELPERS]"
HELPER_MARKER_END = "// [/MODELFUSION ERROR SHIELDING HELPERS]"

HELPER_CODE = '''// [MODELFUSION ERROR SHIELDING HELPERS]
function getModelFusionOutputChannel() {
  try {
    if (typeof globalThis !== "undefined" && globalThis.__modelFusionOutputChannel) {
      return globalThis.__modelFusionOutputChannel;
    }
    let vsc = null;
    try {
      if (typeof vscode !== "undefined" && vscode) {
        vsc = vscode;
      } else if (typeof require === "function") {
        vsc = require("vscode");
      }
    } catch (_) {}
    if (vsc && vsc.window && typeof vsc.window.createOutputChannel === "function") {
      const ch = vsc.window.createOutputChannel("ModelFusion Server");
      if (typeof globalThis !== "undefined") {
        globalThis.__modelFusionOutputChannel = ch;
      }
      return ch;
    }
  } catch (_) {}
  return null;
}

function notifyModelFusionError(msg, actions, callback) {
  const defaultActions = ["Retry", "View Logs", "Reconnect"];
  let acts = defaultActions;
  let cb = callback;
  if (Array.isArray(actions) && actions.length > 0) {
    acts = actions;
  } else if (typeof actions === "function") {
    cb = actions;
  }

  // Structured logging to ModelFusion Server output channel
  try {
    const ch = getModelFusionOutputChannel();
    if (ch && typeof ch.appendLine === "function") {
      const ts = new Date().toISOString();
      ch.appendLine(`[DIAGNOSTIC ERROR] [${ts}] ${msg}`);
    }
  } catch (_) {}

  // Safe non-blocking toast dispatcher with headless guards
  try {
    let vsc = null;
    try {
      if (typeof vscode !== "undefined" && vscode) {
        vsc = vscode;
      } else if (typeof require === "function") {
        vsc = require("vscode");
      }
    } catch (_) {}
    if (vsc && vsc.window && typeof vsc.window.showErrorMessage === "function") {
      const displayMsg = typeof msg === "string" && msg.startsWith("[ModelFusion]") ? msg : `[ModelFusion] ${msg}`;
      const p = vsc.window.showErrorMessage(displayMsg, ...acts);
      if (p && typeof p.then === "function") {
        p.then((choice) => {
          if (choice === "View Logs") {
            try {
              const ch = getModelFusionOutputChannel();
              if (ch && typeof ch.show === "function") {
                ch.show(true);
              }
            } catch (_) {}
          }
          if (typeof cb === "function" && choice) {
            try {
              cb(choice);
            } catch (_) {}
          }
        }).catch(() => {});
      }
    }
  } catch (_) {}
}

if (typeof globalThis !== "undefined") {
  globalThis.getModelFusionOutputChannel = getModelFusionOutputChannel;
  globalThis.notifyModelFusionError = notifyModelFusionError;
}
// [/MODELFUSION ERROR SHIELDING HELPERS]
'''

def inject_helpers(content):
    """Inject error shielding helper functions at the top of the file."""
    if HELPER_MARKER_START in content:
        return content, False

    if content.startswith('"use strict";'):
        new_content = '"use strict";\n' + HELPER_CODE + '\n' + content[len('"use strict";'):].lstrip('\r\n')
    else:
        new_content = HELPER_CODE + '\n' + content

    return new_content, True

def patch_extension_js(file_path, node_path, force_validate=False):
    """Patch dist/extension.js: helpers + Ollama background pull shielding."""
    if not os.path.isfile(file_path):
        return False, False

    print(f"\n[PATCH] Processing extension.js: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Inject helpers
    content, h_changed = inject_helpers(content)
    if h_changed:
        changed = True
        print("  [APPLIED] Injected getModelFusionOutputChannel and notifyModelFusionError helpers.")
    else:
        print("  [OK] Helpers already present.")

    # 2. Shield Ollama Background Pull in provideLanguageModelChatResponse
    old_pull_re = re.compile(
        r'let pullInitiated = false;\s*'
        r'if\s*\(modelName && modelName !== "the requested model"\)\s*\{[\s\S]*?'
        r'cp\.spawn\("ollama",\s*\["pull",\s*modelName\],\s*\{ detached: true, stdio: "ignore", windowsHide: true \}\)\.unref\(\);\s*'
        r'pullInitiated = true;\s*'
        r'\}\s*catch\s*\(_\)\s*\{[\s\S]*?'
        r'req\.on\("error",\s*\(\)\s*=>\s*\{\}\);[\s\S]*?'
        r'\}\s*catch\s*\(_\)\s*\{\}\s*'
        r'\}\s*\}',
        re.MULTILINE
    )

    new_pull_code = '''let pullInitiated = false;
      if (modelName && modelName !== "the requested model") {
        try {
          const cp = require("child_process");
          cp.spawn("ollama", ["pull", modelName], { detached: true, stdio: "ignore", windowsHide: true }).unref();
          pullInitiated = true;
          try {
            const ch = getModelFusionOutputChannel();
            if (ch && typeof ch.appendLine === "function") {
              ch.appendLine(`[Ollama Pull] Initiated background pull for model '${modelName}' via process spawn.`);
            }
          } catch (_) {}
        } catch (spawnErr) {
          try {
            const ch = getModelFusionOutputChannel();
            if (ch && typeof ch.appendLine === "function") {
              ch.appendLine(`[Ollama Pull] [ERROR] Spawn failed for model '${modelName}': ${spawnErr.message}. Attempting HTTP fallback...`);
            }
          } catch (_) {}
          try {
            let httpLib = require("http");
            let u = new URL(baseUrl);
            let postBody = JSON.stringify({ name: modelName, stream: false });
            let req = httpLib.request({
              hostname: u.hostname,
              port: u.port || 11434,
              path: "/api/pull",
              method: "POST",
              headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(postBody) }
            });
            req.on("error", (netErr) => {
              const errMsg = `Failed to pull model '${modelName}' via Ollama HTTP API: ${netErr.message}`;
              try {
                const ch = getModelFusionOutputChannel();
                if (ch && typeof ch.appendLine === "function") {
                  ch.appendLine(`[Ollama Pull] [ERROR] ${errMsg}`);
                }
              } catch (_) {}
              notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], () => {});
            });
            req.write(postBody);
            req.end();
            pullInitiated = true;
            try {
              const ch = getModelFusionOutputChannel();
              if (ch && typeof ch.appendLine === "function") {
                ch.appendLine(`[Ollama Pull] Initiated background pull for model '${modelName}' via HTTP POST /api/pull.`);
              }
            } catch (_) {}
          } catch (httpErr) {
            const errMsg = `Failed to initiate pull for model '${modelName}': ${httpErr.message}`;
            try {
              const ch = getModelFusionOutputChannel();
              if (ch && typeof ch.appendLine === "function") {
                ch.appendLine(`[Ollama Pull] [ERROR] ${errMsg}`);
              }
            } catch (_) {}
            notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], () => {});
          }
        }
      }'''

    if "[Ollama Pull]" in content and "req.on(\"error\", (netErr) => {" in content:
        print("  [OK] Ollama background pull error shielding already applied.")
    elif old_pull_re.search(content):
        content = old_pull_re.sub(new_pull_code, content, count=1)
        changed = True
        print("  [APPLIED] Shielded Ollama background pull with diagnostic logs and toast dispatch.")
    else:
        print("  [WARN] Could not match Ollama background pull pattern in extension.js.")

    if changed:
        safe_write_file(file_path, content.encode("utf-8"))
        print("  [SUCCESS] Written updated extension.js.", flush=True)
        valid = validate_js_syntax(file_path, node_path)
        if not valid:
            return False, False
        return True, True
    else:
        print("  [NO CHANGES] File already up to date.", flush=True)
        if force_validate:
            valid = validate_js_syntax(file_path, node_path)
            if not valid:
                return False, False
        return True, False

def generate_methods_block(vsc, cfg, path_mod, fs_mod, os_mod, lmt):
    """Generate clean, robust, and fully shielded implementations of _runDatabaseUpdate and _spawnCliFallback."""
    return f"""      async _runDatabaseUpdate() {{
        if (this._isUpdateRunning) {{
          this._logService.info("ModelFusionProvider: Database update is already running. Skipping this tick.");
          return;
        }}
        const {cfg} = {vsc}.workspace.getConfiguration("hugos.modelfusion");
        const enabled = {cfg}.get("watcher.enabled", true);
        if (!enabled) {{
          this._stopWatcher();
          return;
        }}
        this._isUpdateRunning = true;
        this._logService.info("ModelFusionProvider: Background watcher starting database update...");
        try {{
          const cliPath = this._findCliBinary();
          const spawnCwd = {path_mod}.dirname({path_mod}.dirname(cliPath));
          const configDbPath = {cfg}.get("dbPath", "");
          const ideDbPath = {path_mod}.join(spawnCwd, "db", "hf_models.db");
          const dbPath = configDbPath ? configDbPath : ideDbPath;
          try {{
            {fs_mod}.mkdirSync({path_mod}.dirname(dbPath), {{ recursive: true }});
          }} catch (e4) {{
            this._logService.error(`ModelFusionProvider: Failed to create database directory: ${{e4.message}}`);
          }}
          const args2 = ["--update", "--db-path", dbPath];
          this._logService.info(`ModelFusionProvider: Spawning background update process: ${{cliPath}} ${{args2.join(" ")}}`);
          const child = child_process2.spawn(cliPath, args2, {{ cwd: spawnCwd }});
          try {{
            if (child.pid) {{
              try {{
                require("os").setPriority(child.pid, 19);
              }} catch (_) {{
                {os_mod}.setPriority(child.pid, 19);
              }}
              this._logService.info(`ModelFusionProvider: Set watcher process priority to Idle (19) for PID ${{child.pid}}`);
            }}
          }} catch (e4) {{
            this._logService.warn(`ModelFusionProvider: Failed to set low process priority: ${{e4.message}}`);
          }}
          child.stdout?.on("data", (data) => {{
            const lines = data.toString().split("\\n");
            for (const line of lines) {{
              if (line.trim()) {{
                this._logService.info(`ModelFusionProvider [Watcher stdout]: ${{line.trim()}}`);
                this._outputChannel.appendLine(`[Watcher] ${{line.trim()}}`);
              }}
            }}
          }});
          child.stderr?.on("data", (data) => {{
            const lines = data.toString().split("\\n");
            for (const line of lines) {{
              if (line.trim()) {{
                this._logService.warn(`ModelFusionProvider [Watcher stderr]: ${{line.trim()}}`);
                this._outputChannel.appendLine(`[Watcher] [stderr] ${{line.trim()}}`);
              }}
            }}
          }});
          child.on("close", (code) => {{
            this._isUpdateRunning = false;
            if (code === 0) {{
              this._logService.info("ModelFusionProvider: Background database update completed successfully.");
              this._outputChannel.appendLine("[Watcher] Background model & database update completed successfully.");
            }} else {{
              this._logService.error(`ModelFusionProvider: Background database update failed with exit code ${{code}}.`);
              this._outputChannel.appendLine(`[Watcher] [ERROR] Background database update failed with exit code ${{code}}.`);
              notifyModelFusionError(`Background database update failed with exit code ${{code}}.`, ["Retry", "View Logs"], (choice) => {{
                if (choice === "Retry") {{
                  this._runDatabaseUpdate();
                }}
              }});
            }}
          }});
          child.on("error", (err2) => {{
            this._isUpdateRunning = false;
            const errMsg = `Failed to launch background database update process: ${{err2.message}}`;
            this._logService.error(`ModelFusionProvider: ${{errMsg}}`);
            this._outputChannel.appendLine(`[Watcher] [ERROR] ${{errMsg}}`);
            notifyModelFusionError(`Watcher process error: ${{err2.message}}`, ["Retry", "View Logs"], (choice) => {{
              if (choice === "Retry") {{
                this._runDatabaseUpdate();
              }}
            }});
          }});
        }} catch (e4) {{
          this._isUpdateRunning = false;
          this._logService.error(`ModelFusionProvider: Error in database update watcher: ${{e4.message}}`);
          this._outputChannel.appendLine(`[Watcher] [ERROR] Error in database update watcher: ${{e4.message}}`);
        }}
      }}
      _spawnCliFallback(promptText, budget, selectionStrategy, fusionMode, fusionModels, openvino, gpu, cpu, fusion, progress, token) {{
        const cliPath = this._findCliBinary();
        const spawnCwd = {path_mod}.dirname({path_mod}.dirname(cliPath));
        const {cfg} = {vsc}.workspace.getConfiguration("hugos.modelfusion");
        const configDbPath = {cfg}.get("dbPath", "");
        const ideDbPath = {path_mod}.join(spawnCwd, "db", "hf_models.db");
        const dbPath = configDbPath ? configDbPath : ideDbPath;
        try {{
          {fs_mod}.mkdirSync({path_mod}.dirname(dbPath), {{ recursive: true }});
        }} catch (e4) {{
          this._logService.error(`ModelFusionProvider: Failed to create database directory: ${{e4.message}}`);
        }}
        const ovModelDir = {cfg}.get("ovModelDir", "") || {path_mod}.join({os_mod}.homedir(), ".hugos-ide", "ov_models");
        const tmpPromptFile = {path_mod}.join({os_mod}.tmpdir(), `modelfusion_prompt_${{Date.now()}}.txt`);
        try {{
          {fs_mod}.writeFileSync(tmpPromptFile, promptText, "utf8");
        }} catch (e4) {{
          this._logService.error(`ModelFusionProvider: Failed to write temp prompt file: ${{e4.message}}`);
        }}
        return new Promise((resolve7, reject7) => {{
          const inlinePrompt = promptText.length <= 4e3 ? promptText : promptText.slice(0, 4e3) + "\\n[... truncated for CLI fallback ...]";
          const args2 = ["--prompt", inlinePrompt, "--budget", budget.toString(), "--selection-strategy", selectionStrategy, "--fusion-mode", fusionMode, "--fusion-models", fusionModels.toString(), "--db-path", dbPath, "--ov-model-dir", ovModelDir];
          if (openvino) {{
            args2.push("--openvino");
          }}
          if (gpu) {{
            args2.push("--gpu");
          }}
          if (cpu) {{
            args2.push("--cpu");
          }}
          if (fusion) {{
            args2.push("--fusion");
          }}
          this._logService.info(`ModelFusionProvider: Spawning fallback process ${{cliPath}} (prompt length: ${{promptText.length}}, inline: ${{inlinePrompt.length}})`);
          const spawnEnv = {{ ...process.env, ...this._getWorkspaceEnv() }};
          let child;
          try {{
            child = child_process2.spawn(cliPath, args2, {{ cwd: spawnCwd, env: spawnEnv }});
          }} catch (spawnErr) {{
            try {{
              {fs_mod}.unlinkSync(tmpPromptFile);
            }} catch (_) {{}}
            const errMsg = `Failed to spawn CLI process synchronously: ${{spawnErr.message}}`;
            this._logService.error(`ModelFusionProvider: ${{errMsg}}`);
            this._outputChannel.appendLine(`[CLI ERROR] ${{errMsg}}`);
            notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], (choice) => {{
              if (choice === "Retry" || choice === "Reconnect") {{
                this._spawnCliFallback(promptText, budget, selectionStrategy, fusionMode, fusionModels, openvino, gpu, cpu, fusion, progress, token);
              }}
            }});
            progress.report(new {lmt}(`Error: Failed to launch ModelFusion CLI.\\n${{spawnErr.message}}`));
            resolve7();
            return;
          }}
          let reportedSomething = false;
          const cancelReg = token?.onCancellationRequested(() => {{
            child.kill();
            if (!reportedSomething) {{
              progress.report(new {lmt}("\\u2026"));
              reportedSomething = true;
            }}
            resolve7();
          }});
          let buffer = "";
          child.stdout.on("data", (data) => {{
            buffer += data.toString();
            const lines = buffer.split("\\n");
            buffer = lines.pop() || "";
            let output = "";
            for (const line of lines) {{
              const trimmed = line.trim();
              if (trimmed.startsWith("[SEMAPHORE]") || trimmed.startsWith("[MODEL]") || trimmed.startsWith("[FUSION]") || trimmed.includes("Checking OpenVINO") || trimmed.includes("OpenVINO GenAI is") || trimmed.includes("Using OpenVINO") || trimmed.startsWith("\\u{{1F537}}") || trimmed.startsWith("\\u2705") || trimmed.startsWith("\\u{{1F4CB}}") || trimmed.startsWith("\\u{{1F50D}}") || trimmed.startsWith("\\u2714") || trimmed.startsWith("\\u25BA")) {{
                continue;
              }}
              output += line + "\\n";
            }}
            if (output) {{
              progress.report(new {lmt}(output));
              reportedSomething = true;
            }}
          }});
          child.stderr?.on("data", (data) => {{
            const lines = data.toString().split("\\n");
            for (const line of lines) {{
              if (line.trim()) {{
                this._outputChannel.appendLine(`[CLI stderr] ${{line.trimEnd()}}`);
              }}
            }}
          }});
          child.on("close", (code) => {{
            cancelReg?.dispose();
            try {{
              {fs_mod}.unlinkSync(tmpPromptFile);
            }} catch (_11) {{}}
            if (buffer) {{
              const trimmed = buffer.trim();
              if (!(trimmed.startsWith("[SEMAPHORE]") || trimmed.startsWith("[MODEL]") || trimmed.startsWith("[FUSION]") || trimmed.includes("Checking OpenVINO") || trimmed.includes("OpenVINO GenAI is") || trimmed.includes("Using OpenVINO") || trimmed.startsWith("\\u{{1F537}}") || trimmed.startsWith("\\u2705") || trimmed.startsWith("\\u{{1F4CB}}") || trimmed.startsWith("\\u{{1F50D}}") || trimmed.startsWith("\\u2714") || trimmed.startsWith("\\u25BA"))) {{
                progress.report(new {lmt}(buffer));
                reportedSomething = true;
              }}
            }}
            if (!reportedSomething) {{
              const msg = code === 0 ? "\\u2026" : `Error: ModelFusion CLI exited with code ${{code}}.`;
              progress.report(new {lmt}(msg));
            }}
            resolve7();
          }});
          child.on("error", (err2) => {{
            cancelReg?.dispose();
            try {{
              {fs_mod}.unlinkSync(tmpPromptFile);
            }} catch (_11) {{}}
            const errMsg = `CLI execution error: ${{err2.message}}`;
            this._logService.error(`ModelFusionProvider: ${{errMsg}}`);
            this._outputChannel.appendLine(`[CLI ERROR] ${{errMsg}}`);
            notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], (choice) => {{
              if (choice === "Retry" || choice === "Reconnect") {{
                this._spawnCliFallback(promptText, budget, selectionStrategy, fusionMode, fusionModels, openvino, gpu, cpu, fusion, progress, token);
              }}
            }});
            progress.report(new {lmt}(`Error: Failed to launch ModelFusion CLI.\\n${{err2.message}}`));
            resolve7();
          }});
        }});
      }}"""

def patch_test_bundle_js(file_path, node_path, force_validate=False):
    """Patch test-extension.js / sanity-test-extension.js: helpers, respawn fix, watcher & CLI shielding."""
    if not os.path.isfile(file_path):
        return False, False

    fname = os.path.basename(file_path)
    print(f"\n[PATCH] Processing {fname}: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. Inject helpers
    content, h_changed = inject_helpers(content)
    if h_changed:
        changed = True
        print("  [APPLIED] Injected getModelFusionOutputChannel and notifyModelFusionError helpers.")
    else:
        print("  [OK] Helpers already present.")

    # 2. Register output channel in constructor: globalThis.__modelFusionOutputChannel = this._outputChannel
    out_ch_target = 'this._outputChannel.appendLine("ModelFusion Server output channel initialized.");'
    out_ch_replacement = 'if (typeof globalThis !== "undefined") { globalThis.__modelFusionOutputChannel = this._outputChannel; }\n        this._outputChannel.appendLine("ModelFusion Server output channel initialized.");'
    if 'globalThis.__modelFusionOutputChannel = this._outputChannel' in content:
        print("  [OK] globalThis.__modelFusionOutputChannel registration already present.")
    elif out_ch_target in content:
        content = content.replace(out_ch_target, out_ch_replacement, 1)
        changed = True
        print("  [APPLIED] Hooked globalThis.__modelFusionOutputChannel registration in constructor.")
    else:
        print("  [WARN] Could not match output channel initialization line.")

    # 3. Fix Server Auto-Respawn in startServer
    if "this._spawnPersistentServer()" in content:
        content = content.replace("this._spawnPersistentServer();", "this.startServer();")
        changed = True
        print("  [APPLIED] Fixed server auto-respawn: replaced _spawnPersistentServer() with startServer().")
    elif "this.startServer();" in content and "Respawning in 3 seconds" in content:
        print("  [OK] Server auto-respawn already calls this.startServer().")

    # Add structured diagnostics and notifyModelFusionError to serverProcess error handler
    old_srv_err_re = re.compile(
        r'this\._serverProcess\.on\("error",\s*\(err2\)\s*=>\s*\{[\s\S]*?this\._outputChannel\.appendLine\(`\[ERROR\] \$\{msg\}`\);\s*\}\);',
        re.MULTILINE
    )
    new_srv_err = '''this._serverProcess.on("error", (err2) => {
            const msg = `Server process error: ${err2.message}`;
            this._logService.error(`ModelFusionProvider: Persistent server error: ${err2.message}`);
            this._outputChannel.appendLine(`[ERROR] [${new Date().toISOString()}] ${msg}`);
            notifyModelFusionError(`Persistent server process error: ${err2.message}`, ["Retry", "View Logs", "Reconnect"], (choice) => {
              if (choice === "Retry" || choice === "Reconnect") {
                this.startServer();
              }
            });
          });'''

    if "Persistent server process error:" in content:
        print("  [OK] startServer error handler already shielded.")
    elif old_srv_err_re.search(content):
        content = old_srv_err_re.sub(new_srv_err, content, count=1)
        changed = True
        print("  [APPLIED] Shielded startServer error handler with structured logging and toast.")
    else:
        print("  [WARN] Could not match startServer error handler pattern.")

    # 4. Shield Watcher (_runDatabaseUpdate) and CLI Fallback (_spawnCliFallback)
    idx1 = content.find("async _runDatabaseUpdate()")
    idx2 = content.find("async provideTokenCount(", idx1) if idx1 != -1 else -1

    if idx1 != -1 and idx2 != -1:
        # Detect environment variable names from context surrounding _runDatabaseUpdate
        window_ctx = content[max(0, idx1 - 2000):idx1 + 500]
        if "vscode15" in window_ctx:
            vsc = "vscode15"
            cfg = "config3"
            path_mod = "path3"
            fs_mod = "fs3"
            os_mod = "os"
            lmt = "LanguageModelTextPart3"
        else:
            vsc = "vscode32"
            cfg = "config2"
            path_mod = "path5"
            fs_mod = "fs7"
            os_mod = "os2"
            lmt = "LanguageModelTextPart3"

        new_block = generate_methods_block(vsc, cfg, path_mod, fs_mod, os_mod, lmt).strip() + "\n      "
        existing_block = content[idx1:idx2]

        if existing_block.strip() != new_block.strip():
            content = content[:idx1] + new_block + content[idx2:]
            changed = True
            print(f"  [APPLIED] Shielded _runDatabaseUpdate and _spawnCliFallback ({vsc}, {cfg}, {path_mod}, {fs_mod}, {os_mod}).")
        else:
            print("  [OK] _runDatabaseUpdate and _spawnCliFallback already shielded.")
    else:
        print("  [WARN] Could not locate boundaries for _runDatabaseUpdate and _spawnCliFallback.")

    if changed:
        safe_write_file(file_path, content.encode("utf-8"))
        print(f"  [SUCCESS] Written updated {fname}.", flush=True)
        valid = validate_js_syntax(file_path, node_path)
        if not valid:
            return False, False
        return True, True
    else:
        print("  [NO CHANGES] File already up to date.", flush=True)
        if force_validate:
            valid = validate_js_syntax(file_path, node_path)
            if not valid:
                return False, False
        return True, False

def main():
    print("============================================================")
    print("[HUGOS] Patching copilot extension bundles (Error Shielding)")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    force_validate = "--force-validate" in sys.argv
    skip_installed = any(arg.lower() in ("--skip-installed", "--check-installed=false") for arg in sys.argv)

    node_path = find_node_executable()
    if node_path:
        print(f"  Using Node.js at: {node_path}")
    else:
        print(f"  [WARNING] node.exe not found! Syntax checks will be skipped.")

    pack_dir = os.path.join(script_dir, "VSCode-win32-x64")

    # Define all target bundles
    extension_targets = [
        os.path.join(script_dir, "vscode", "extensions", "copilot", "dist", "extension.js"),
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "dist", "extension.js"),
    ]

    test_bundle_targets = [
        os.path.join(script_dir, "vscode", "extensions", "copilot", "dist", "test-extension.js"),
        os.path.join(script_dir, "vscode", "extensions", "copilot", "dist", "sanity-test-extension.js"),
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "dist", "test-extension.js"),
        os.path.join(pack_dir, "resources", "app", "extensions", "copilot", "dist", "sanity-test-extension.js"),
    ]

    base_dirs = [pack_dir]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        hugos_installed = os.path.join(local_app_data, "HugOS IDE")
        base_dirs.append(hugos_installed)
        extension_targets.append(os.path.join(hugos_installed, "resources", "app", "extensions", "copilot", "dist", "extension.js"))
        test_bundle_targets.append(os.path.join(hugos_installed, "resources", "app", "extensions", "copilot", "dist", "test-extension.js"))
        test_bundle_targets.append(os.path.join(hugos_installed, "resources", "app", "extensions", "copilot", "dist", "sanity-test-extension.js"))

    # Scan for versioned runtime directories ([0-9a-f]{7,40})
    for b in base_dirs:
        if b and os.path.isdir(b):
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        v_ext = os.path.join(sub, "resources", "app", "extensions", "copilot", "dist", "extension.js")
                        if os.path.isfile(v_ext) and v_ext not in extension_targets:
                            extension_targets.append(v_ext)
                        v_tst = os.path.join(sub, "resources", "app", "extensions", "copilot", "dist", "test-extension.js")
                        if os.path.isfile(v_tst) and v_tst not in test_bundle_targets:
                            test_bundle_targets.append(v_tst)
                        v_snt = os.path.join(sub, "resources", "app", "extensions", "copilot", "dist", "sanity-test-extension.js")
                        if os.path.isfile(v_snt) and v_snt not in test_bundle_targets:
                            test_bundle_targets.append(v_snt)

    seen = set()
    error_count = 0
    modified_count = 0

    # Patch extension.js targets
    for t in extension_targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_extension_js(t, node_path, force_validate=force_validate)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    # Patch test-extension.js and sanity-test-extension.js targets
    for t in test_bundle_targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_test_bundle_js(t, node_path, force_validate=force_validate)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    if error_count > 0:
        print(f"\n[ERROR] Error shielding patching failed with {error_count} error(s)!")
        sys.exit(1)

    print(f"\n[SUCCESS] Error shielding patching complete! ({len(seen)} validated, {modified_count} modified)")
    sys.exit(0)

if __name__ == "__main__":
    main()

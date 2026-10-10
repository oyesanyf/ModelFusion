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

    # Add structured diagnostics and notifyModelFusionError to serverProcess error and exit
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

    # 4. Shield Background Watcher (_runDatabaseUpdate)
    # 4a: Watcher stdout forwarding
    old_watcher_stdout = '''              if (line.trim()) {
                this._logService.info(`ModelFusionProvider [Watcher stdout]: ${line.trim()}`);
              }'''
    new_watcher_stdout = '''              if (line.trim()) {
                this._logService.info(`ModelFusionProvider [Watcher stdout]: ${line.trim()}`);
                this._outputChannel.appendLine(`[Watcher] ${line.trim()}`);
              }'''
    if "this._outputChannel.appendLine(`[Watcher] ${line.trim()}`);" in content:
        print("  [OK] Watcher stdout forwarding already present.")
    elif old_watcher_stdout in content:
        content = content.replace(old_watcher_stdout, new_watcher_stdout, 1)
        changed = True
        print("  [APPLIED] Added [Watcher] prefix output channel forwarding for watcher stdout.")

    # 4b: Watcher stderr forwarding
    old_watcher_stderr = '''              if (line.trim()) {
                this._logService.warn(`ModelFusionProvider [Watcher stderr]: ${line.trim()}`);
              }'''
    new_watcher_stderr = '''              if (line.trim()) {
                this._logService.warn(`ModelFusionProvider [Watcher stderr]: ${line.trim()}`);
                this._outputChannel.appendLine(`[Watcher] [stderr] ${line.trim()}`);
              }'''
    if "this._outputChannel.appendLine(`[Watcher] [stderr] ${line.trim()}`);" in content:
        print("  [OK] Watcher stderr forwarding already present.")
    elif old_watcher_stderr in content:
        content = content.replace(old_watcher_stderr, new_watcher_stderr, 1)
        changed = True
        print("  [APPLIED] Added [Watcher] [stderr] forwarding for watcher stderr.")

    # 4c: Watcher close non-zero error reporting
    old_watcher_close_re = re.compile(
        r'child\.on\("close",\s*\(code\)\s*=>\s*\{[\s\S]*?if\s*\(code === 0\)\s*\{[\s\S]*?\}\s*else\s*\{[\s\S]*?\}\s*\}\);',
        re.MULTILINE
    )
    new_watcher_close = '''child.on("close", (code) => {
            this._isUpdateRunning = false;
            if (code === 0) {
              this._logService.info("ModelFusionProvider: Background database update completed successfully.");
              this._outputChannel.appendLine("[Watcher] Background model & database update completed successfully.");
            } else {
              this._logService.error(`ModelFusionProvider: Background database update failed with exit code ${code}.`);
              this._outputChannel.appendLine(`[Watcher] [ERROR] Background database update failed with exit code ${code}.`);
              notifyModelFusionError(`Background database update failed with exit code ${code}.`, ["Retry", "View Logs"], (choice) => {
                if (choice === "Retry") {
                  this._runDatabaseUpdate();
                }
              });
            }
          });'''
    if "[Watcher] [ERROR] Background database update failed with exit code" in content:
        print("  [OK] Watcher close handler already shielded.")
    elif old_watcher_close_re.search(content):
        content = old_watcher_close_re.sub(new_watcher_close, content, count=1)
        changed = True
        print("  [APPLIED] Shielded watcher close handler with [Watcher] [ERROR] and toast.")
    else:
        print("  [WARN] Could not match watcher close handler pattern.")

    # 4d: Watcher child error handler
    old_watcher_err_re = re.compile(
        r'child\.on\("error",\s*\(err2\)\s*=>\s*\{[\s\S]*?this\._isUpdateRunning = false;\s*this\._logService\.error\(`ModelFusionProvider: Failed to launch background database update process: \$\{err2\.message\}`\);\s*\}\);',
        re.MULTILINE
    )
    new_watcher_err = '''child.on("error", (err2) => {
            this._isUpdateRunning = false;
            const errMsg = `Failed to launch background database update process: ${err2.message}`;
            this._logService.error(`ModelFusionProvider: ${errMsg}`);
            this._outputChannel.appendLine(`[Watcher] [ERROR] ${errMsg}`);
            notifyModelFusionError(`Watcher process error: ${err2.message}`, ["Retry", "View Logs"], (choice) => {
              if (choice === "Retry") {
                this._runDatabaseUpdate();
              }
            });
          });'''
    if "[Watcher] [ERROR] Failed to launch background database update process:" in content:
        print("  [OK] Watcher child error handler already shielded.")
    elif old_watcher_err_re.search(content):
        content = old_watcher_err_re.sub(new_watcher_err, content, count=1)
        changed = True
        print("  [APPLIED] Shielded watcher child error handler with [Watcher] [ERROR] and toast.")
    else:
        print("  [WARN] Could not match watcher child error handler pattern.")

    # 5. Shield CLI Execution (_spawnCliFallback)
    # 5a: Synchronous try...catch around child_process2.spawn
    old_spawn_call = 'const child = child_process2.spawn(cliPath, args2, { cwd: spawnCwd, env: spawnEnv });'
    new_spawn_call = '''let child;
          try {
            child = child_process2.spawn(cliPath, args2, { cwd: spawnCwd, env: spawnEnv });
          } catch (spawnErr) {
            try {
              if (typeof fs7 !== "undefined") { fs7.unlinkSync(tmpPromptFile); }
              else if (typeof fs3 !== "undefined") { fs3.unlinkSync(tmpPromptFile); }
              else { require("fs").unlinkSync(tmpPromptFile); }
            } catch (_) {}
            const errMsg = `Failed to spawn CLI process synchronously: ${spawnErr.message}`;
            this._logService.error(`ModelFusionProvider: ${errMsg}`);
            this._outputChannel.appendLine(`[CLI ERROR] ${errMsg}`);
            notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], (choice) => {
              if (choice === "Retry" || choice === "Reconnect") {
                this._spawnCliFallback(promptText, budget, selectionStrategy, fusionMode, fusionModels, openvino, gpu, cpu, fusion, progress, token);
              }
            });
            progress.report(new LanguageModelTextPart3(`Error: Failed to launch ModelFusion CLI.\\n${spawnErr.message}`));
            resolve7();
            return;
          }'''
    if "Failed to spawn CLI process synchronously:" in content:
        print("  [OK] Synchronous spawn error shielding already present in _spawnCliFallback.")
    elif old_spawn_call in content:
        content = content.replace(old_spawn_call, new_spawn_call, 1)
        changed = True
        print("  [APPLIED] Enclosed child_process.spawn in synchronous try...catch boundary.")
    else:
        print("  [WARN] Could not match child_process2.spawn line in _spawnCliFallback.")

    # 5b: Pipe child.stderr to output channel as [CLI stderr]
    old_cli_stderr = '''          child.stderr.on("data", (_data) => {
          });'''
    new_cli_stderr = '''          child.stderr?.on("data", (data) => {
            const lines = data.toString().split("\\n");
            for (const line of lines) {
              if (line.trim()) {
                this._outputChannel.appendLine(`[CLI stderr] ${line.trimEnd()}`);
              }
            }
          });'''
    if "this._outputChannel.appendLine(`[CLI stderr]" in content:
        print("  [OK] CLI stderr forwarding already present.")
    elif old_cli_stderr in content:
        content = content.replace(old_cli_stderr, new_cli_stderr, 1)
        changed = True
        print("  [APPLIED] Forwarded CLI stderr to output channel with [CLI stderr] prefix.")
    else:
        print("  [WARN] Could not match empty child.stderr.on('data') block.")

    # 5c: child.on("error") in _spawnCliFallback (matches newline in template string cleanly)
    old_cli_err_re = re.compile(
        r'child\.on\("error",\s*\(err2\)\s*=>\s*\{[\s\S]*?Error: Failed to launch ModelFusion CLI[\s\S]*?resolve7\(\);\s*\}\);',
        re.MULTILINE
    )
    new_cli_err = '''child.on("error", (err2) => {
            cancelReg?.dispose();
            try {
              if (typeof fs7 !== "undefined") { fs7.unlinkSync(tmpPromptFile); }
              else if (typeof fs3 !== "undefined") { fs3.unlinkSync(tmpPromptFile); }
              else { require("fs").unlinkSync(tmpPromptFile); }
            } catch (_11) {}
            const errMsg = `CLI execution error: ${err2.message}`;
            this._logService.error(`ModelFusionProvider: ${errMsg}`);
            this._outputChannel.appendLine(`[CLI ERROR] ${errMsg}`);
            notifyModelFusionError(errMsg, ["Retry", "View Logs", "Reconnect"], (choice) => {
              if (choice === "Retry" || choice === "Reconnect") {
                this._spawnCliFallback(promptText, budget, selectionStrategy, fusionMode, fusionModels, openvino, gpu, cpu, fusion, progress, token);
              }
            });
            progress.report(new LanguageModelTextPart3(`Error: Failed to launch ModelFusion CLI.\\n${err2.message}`));
            resolve7();
          });'''
    if "CLI execution error:" in content:
        print("  [OK] _spawnCliFallback child.on('error') already shielded.")
    elif old_cli_err_re.search(content):
        content = old_cli_err_re.sub(new_cli_err, content, count=1)
        changed = True
        print("  [APPLIED] Shielded _spawnCliFallback child error handler with [CLI ERROR] and toast.")
    else:
        print("  [WARN] Could not match _spawnCliFallback child.on('error') block.")

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

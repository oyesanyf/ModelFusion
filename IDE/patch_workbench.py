#!/usr/bin/env python3
"""
HugOS IDE Workbench Patch Script
Applies permanent chat enablement and entitlement bypass patches to workbench.desktop.main.js
Supports both minified and unminified bundles, validates syntax with node.exe,
and cleans any legacy disabled extension states from AppData.
"""

import os
import sys
import re
import json
import shutil
import sqlite3
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

def clean_diag_logs(content):
    """Remove temporary diagnostic logging statements if present."""
    changed = False
    diag_patterns = [
        r'if\(r\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\)this\._logService\.error\("\[DIAG-RUNLOC-COPILOT\][^;]*\);',
        r'for\(let x of t\)if\(x\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\)a\.error\("\[DIAG-OST-COPILOT\][^;]*\);',
        r'n\[c\]\.identifier\.value\.toLowerCase\(\)\.includes\("copilot"\)\?a\.error\("\[DIAG-EJO-COPILOT\][^:]*\):0,',
    ]
    for pat in diag_patterns:
        if re.search(pat, content):
            content = re.sub(pat, '', content)
            changed = True
    return content, changed

def patch_workbench_content(content):
    """
    Applies the 4 core HugOS chat enablement patches:
    1. Neutralize ensureChatExtensionInitialDisabledState
    2. Force EnablementState.EnabledGlobally (3) for github.copilot-chat
    3. Suppress SetupAgent entitlement interceptor
    4. Suppress forced sign-in modal dialog
    Supports both minified and unminified files.
    """
    changed = False

    # Clean any DIAG logs first
    content, diag_cleaned = clean_diag_logs(content)
    if diag_cleaned:
        changed = True

    # --- Minified Patterns ---
    # 1. ensureChatExtensionInitialDisabledState
    t1_m_orig = "ensureChatExtensionInitialDisabledState(){"
    t1_m_repl = "ensureChatExtensionInitialDisabledState(){return;"
    if t1_m_orig in content and t1_m_repl not in content:
        content = content.replace(t1_m_orig, t1_m_repl, 1)
        changed = True

    # 2. _computeEnablementState
    t2_m_orig = "e.identifier.id.toLowerCase()===this._chatExtensionId&&this.ensureChatExtensionInitialDisabledState(),r=this._getUserEnablementState(e.identifier);"
    t2_m_repl = 'if(e.identifier.id.toLowerCase()==="github.copilot-chat"||e.identifier.id.toLowerCase()===this._chatExtensionId)return 3;r=this._getUserEnablementState(e.identifier);'
    if t2_m_orig in content and t2_m_repl not in content:
        content = content.replace(t2_m_orig, t2_m_repl, 1)
        changed = True

    # 3. Suppress setupAgent entitlement interceptor
    t3_m_orig = "let g=o.context?.value,f=o.requests?.value;if(!g||!f)return;let v=new Io("
    t3_m_repl = "let g=o.context?.value,f=o.requests?.value;return;if(!g||!f)return;let v=new Io("
    if t3_m_orig in content and t3_m_repl not in content:
        content = content.replace(t3_m_orig, t3_m_repl, 1)
        changed = True

    # 4. Suppress forced sign-in modal
    t4_m_orig = "async showDialog(i){let e=new O,t=this.getButtons(i),o=e.add(new Soe("
    t4_m_repl = "async showDialog(i){if(!i?.forceSignInDialog)return 0;let e=new O,t=this.getButtons(i),o=e.add(new Soe("
    if t4_m_orig in content and t4_m_repl not in content:
        content = content.replace(t4_m_orig, t4_m_repl, 1)
        changed = True

    # --- Unminified Patterns ---
    # 1. ensureChatExtensionInitialDisabledState
    t1_u_orig = "ensureChatExtensionInitialDisabledState() {\n"
    t1_u_repl = "ensureChatExtensionInitialDisabledState() {\n    return;\n"
    if t1_u_orig in content and t1_u_repl not in content:
        content = content.replace(t1_u_orig, t1_u_repl, 1)
        changed = True

    # 2. _computeEnablementState
    t2_u_orig = (
        "    if (extension.identifier.id.toLowerCase() === this._chatExtensionId) {\n"
        "      this.ensureChatExtensionInitialDisabledState();\n"
        "    }\n"
        "    enablementState = this._getUserEnablementState(extension.identifier);"
    )
    t2_u_repl = (
        '    if (extension.identifier.id.toLowerCase() === "github.copilot-chat" || extension.identifier.id.toLowerCase() === this._chatExtensionId) {\n'
        "      return 3 /* EnabledGlobally */;\n"
        "    }\n"
        "    enablementState = this._getUserEnablementState(extension.identifier);"
    )
    if t2_u_orig in content and t2_u_repl not in content:
        content = content.replace(t2_u_orig, t2_u_repl, 1)
        changed = True

    # 3. Suppress setupAgent entitlement interceptor
    t3_u_orig = (
        "    const context2 = chatEntitlementService.context?.value;\n"
        "    const requests = chatEntitlementService.requests?.value;\n"
        "    if (!context2 || !requests) {\n"
        "      return;\n"
        "    }"
    )
    t3_u_repl = (
        "    const context2 = chatEntitlementService.context?.value;\n"
        "    const requests = chatEntitlementService.requests?.value;\n"
        "    return; // HugOS: GitHub login is optional; do not intercept chat with SetupAgent\n"
        "    if (!context2 || !requests) {\n"
        "      return;\n"
        "    }"
    )
    if t3_u_orig in content and t3_u_repl not in content:
        content = content.replace(t3_u_orig, t3_u_repl, 1)
        changed = True

    # 4. Suppress sign-in dialog
    t4_u_orig = (
        "  async showDialog(options3) {\n"
        "    const disposables = new DisposableStore();"
    )
    t4_u_repl = (
        "  async showDialog(options3) {\n"
        "    if (!options3?.forceSignInDialog) { return 0 /* Canceled */; } // HugOS: suppress automatic sign-in modal\n"
        "    const disposables = new DisposableStore();"
    )
    if t4_u_orig in content and t4_u_repl not in content:
        content = content.replace(t4_u_orig, t4_u_repl, 1)
        changed = True

    # 5. Neutralize update.mode schema default to "none"
    t5_u_orig = '"update.mode": {\n      type: "string",\n      enum: ["none", "manual", "start", "default"],\n      default: "default",'
    t5_u_repl = '"update.mode": {\n      type: "string",\n      enum: ["none", "manual", "start", "default"],\n      default: "none",'
    if t5_u_orig in content and t5_u_repl not in content:
        content = content.replace(t5_u_orig, t5_u_repl, 1)
        changed = True

    # 6. Route CheckForUpdateAction to HugOS official GitHub releases channel
    t6_u_orig = '''var CheckForUpdateAction = class extends Action2 {
  constructor() {
    super({
      id: "update.checkForUpdate",
      title: localize2(18561, "Check for Updates..."),
      category: { value: product_default.nameShort, original: product_default.nameShort },
      f1: true,
      precondition: CONTEXT_UPDATE_STATE.isEqualTo("idle" /* Idle */)
    });
  }
  async run(accessor) {
    const updateService = accessor.get(IUpdateService);
    return updateService.checkForUpdates(true);
  }
};'''
    t6_u_repl = '''var CheckForUpdateAction = class extends Action2 {
  constructor() {
    super({
      id: "update.checkForUpdate",
      title: localize2(18561, "Check for Updates..."),
      category: { value: product_default.nameShort, original: product_default.nameShort },
      f1: true,
      precondition: ContextKeyExpr.true()
    });
  }
  async run(accessor) {
    const notificationService = accessor.get(INotificationService);
    const openerService = accessor.get(IOpenerService);
    const commandService = accessor.get(ICommandService);
    try {
      if (typeof fetch === "function") {
        fetch("https://api.github.com/repos/oyesanyf/ModelFusion/releases/latest", { headers: { "User-Agent": "HugOS-IDE" } })
          .then((r) => r.json())
          .then((data) => {
            const tag = data.tag_name || "latest";
            notificationService.prompt(
              Severity2.Info,
              `HugOS IDE Update: Latest official release is ${tag}. Releases: https://github.com/oyesanyf/ModelFusion/releases`,
              [
                { label: "View Release Notes", run: () => openerService.open(URI.parse(data.html_url || "https://github.com/oyesanyf/ModelFusion/releases")) },
                { label: "Download HugOS.msi", run: () => openerService.open(URI.parse(`https://github.com/oyesanyf/ModelFusion/releases/download/${tag}/HugOS.msi`)) },
                { label: "Update Models & Catalog", run: () => commandService.executeCommand("workbench.action.chat.open", { query: "@agent update" }) }
              ]
            );
          }).catch(() => {
            notificationService.prompt(
              Severity2.Info,
              "HugOS IDE: Official release channel is https://github.com/oyesanyf/ModelFusion/releases",
              [
                { label: "Open Releases", run: () => openerService.open(URI.parse("https://github.com/oyesanyf/ModelFusion/releases")) },
                { label: "Update Models & Catalog", run: () => commandService.executeCommand("workbench.action.chat.open", { query: "@agent update" }) }
              ]
            );
          });
        return;
      }
    } catch (_e) {}
    notificationService.prompt(
      Severity2.Info,
      "HugOS IDE: Official release channel is https://github.com/oyesanyf/ModelFusion/releases",
      [
        { label: "Open Releases", run: () => openerService.open(URI.parse("https://github.com/oyesanyf/ModelFusion/releases")) },
        { label: "Update Models & Catalog", run: () => commandService.executeCommand("workbench.action.chat.open", { query: "@agent update" }) }
      ]
    );
  }
};'''
    if t6_u_orig in content and t6_u_repl not in content:
        content = content.replace(t6_u_orig, t6_u_repl, 1)
        changed = True

    # 7. Route menubar getUpdateAction to always show "Check for Updates..." and execute update.checkForUpdate
    t7_u_orig = '''  getUpdateAction() {
    const state = this.updateService.state;
    switch (state.type) {
      case "idle" /* Idle */:
        return toAction({
          id: "update.check",
          label: localize(5448, null),
          enabled: true,
          run: () => this.updateService.checkForUpdates(true)
        });
      case "checking for updates" /* CheckingForUpdates */:
        return toAction({ id: "update.checking", label: localize(5449, null), enabled: false, run: () => {
        } });
      case "available for download" /* AvailableForDownload */:
        return toAction({
          id: "update.downloadNow",
          label: localize(5450, null),
          enabled: true,
          run: () => this.updateService.downloadUpdate(true)
        });
      case "downloading" /* Downloading */:
      case "overwriting" /* Overwriting */:
        return toAction({ id: "update.downloading", label: localize(5451, null), enabled: false, run: () => {
        } });
      case "downloaded" /* Downloaded */:
        return isMacintosh ? null : toAction({
          id: "update.install",
          label: localize(5455, null),
          enabled: true,
          run: () => this.updateService.applyUpdate()
        });
      case "updating" /* Updating */:
        return toAction({ id: "update.updating", label: localize(5454, null), enabled: false, run: () => {
        } });
      case "ready" /* Ready */:
        return toAction({
          id: "update.restart",
          label: localize(5457, null),
          enabled: true,
          run: () => this.updateService.quitAndInstall()
        });
      default:
        return null;
    }
  }'''
    t7_u_repl = '''  getUpdateAction() {
    return toAction({
      id: "update.check",
      label: localize(5448, null),
      enabled: true,
      run: () => this.commandService.executeCommand("update.checkForUpdate")
    });
  }'''
    if t7_u_orig in content and t7_u_repl not in content:
        content = content.replace(t7_u_orig, t7_u_repl, 1)
        changed = True

    # 8. Route CommandsRegistry update.check
    t8_u_orig = 'CommandsRegistry.registerCommand("update.check", () => this.updateService.checkForUpdates(true));'
    t8_u_repl = 'CommandsRegistry.registerCommand("update.check", () => this.commandService.executeCommand("update.checkForUpdate"));'
    if t8_u_orig in content and t8_u_repl not in content:
        content = content.replace(t8_u_orig, t8_u_repl, 1)
        changed = True

    return content, changed

def patch_workbench_file(file_path, node_path):
    """Patch a single workbench.desktop.main.js file and validate with node --check."""
    print(f"\n[CHECKING] {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Cannot read {file_path}: {e}")
        return False, False

    new_content, changed = patch_workbench_content(content)

    if not changed:
        print(f"  [INFO] Already patched and up to date.")
        return True, False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [OK] Patched {file_path}")
    except Exception as e:
        print(f"  [ERROR] Failed to write {file_path}: {e}")
        return False, False

    # Validate syntax with node --check
    if node_path:
        res = subprocess.run([node_path, "--check", file_path], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [ERROR] Node syntax check failed for {file_path}!")
            print(res.stderr)
            return False, False
        print(f"  [PASS] Node syntax validation passed.")
    else:
        print(f"  [WARN] node.exe not found; skipping syntax check.")

    return True, True

def patch_main_js_content(content):
    """
    Neutralizes Electron main process UpdateService so it never contacts Microsoft servers
    or attempts background updates. Connects manual update checks to HugOS official channel.
    """
    changed = False

    # 1. Menubar getUpdateMenuItems - always show "Check for Updates..." and NEVER "Restart to Update" or "Downloading Update..."
    menubar_orig_pat = r'getUpdateMenuItems\(\)\s*\{\s*const state = this\.updateService\.state;\s*switch\s*\(state\.type\)\s*\{[\s\S]*?default:\s*return\s*\[\];\s*\}\s*\}'
    menubar_repl = (
        'getUpdateMenuItems() {\n'
        '        const state = this.updateService.state;\n'
        '        if (state.type === "checking for updates" /* CheckingForUpdates */) {\n'
        '          return [new MenuItem3({ label: localize(2655, null), enabled: false })];\n'
        '        }\n'
        '        return [new MenuItem3({\n'
        '          label: this.mnemonicLabel(localize(2654, null)),\n'
        '          click: () => setTimeout(() => {\n'
        '            this.reportMenuActionTelemetry("CheckForUpdate");\n'
        '            this.updateService.checkForUpdates(true);\n'
        '          }, 0)\n'
        '        })];\n'
        '      }'
    )
    if re.search(menubar_orig_pat, content):
        content = re.sub(menubar_orig_pat, menubar_repl, content)
        changed = True

    # 2. Disable periodic background timer in AbstractUpdateService
    sched_orig_pat = r'scheduleCheckForUpdates\(delay = 60 \* 60 \* 1e3\)\s*\{\s*return timeout\(delay\)[\s\S]*?return this\.scheduleCheckForUpdates\(60 \* 60 \* 1e3\);\s*\}\);\s*\}'
    sched_repl = 'scheduleCheckForUpdates(delay = 60 * 60 * 1e3) {\n        return Promise.resolve();\n      }'
    if re.search(sched_orig_pat, content):
        content = re.sub(sched_orig_pat, sched_repl, content)
        changed = True

    # 3. Neutralize buildUpdateFeedUrl across all update services (Win32, Darwin, Linux)
    buf_pat = r'buildUpdateFeedUrl\(quality, commit, options\)\s*\{[\s\S]*?return createUpdateURL\([^;]+;\s*\}'
    buf_repl = 'buildUpdateFeedUrl(quality, commit, options) {\n        return void 0;\n      }'
    if re.search(buf_pat, content):
        content = re.sub(buf_pat, buf_repl, content)
        changed = True

    # 4. Neutralize DarwinUpdateService.doCheckForUpdates
    d_check_pat = r'doCheckForUpdates\(explicit, pendingCommit\)\s*\{\s*this\.logService\.info\("update#doCheckForUpdates - Microsoft updates permanently disabled in HugOS IDE"\);\s*this\.setState\(State\.Idle\(getUpdateType\(\)\)\);\s*return;\s*if \(!this\.quality\) \{'
    d_orig_pat = r'doCheckForUpdates\(explicit, pendingCommit\)\s*\{\s*if \(!this\.quality\) \{[\s\S]*?updateService\.darwin\.checkForUpdates[\s\S]*?electron\d*\.autoUpdater\.checkForUpdates\(\);\s*\}'
    if re.search(d_check_pat, content):
        content = re.sub(d_check_pat, 'doCheckForUpdates(explicit, pendingCommit) {\n        this.logService.info("update#doCheckForUpdates - Upstream Darwin updates disabled in HugOS IDE");\n        this.setState(State.Idle(getUpdateType()));\n        return;\n      }\n      _unused_d() { if (!this.quality) {', content)
        changed = True
    elif re.search(d_orig_pat, content):
        content = re.sub(d_orig_pat, 'doCheckForUpdates(explicit, pendingCommit) {\n        this.logService.info("update#doCheckForUpdates - Upstream Darwin updates disabled in HugOS IDE");\n        this.setState(State.Idle(getUpdateType()));\n        return;\n      }', content)
        changed = True

    # 5. Neutralize LinuxUpdateService.doCheckForUpdates
    l_orig_pat = r'doCheckForUpdates\(explicit, _pendingCommit\)\s*\{\s*if \(!this\.quality\) \{[\s\S]*?updateService\.linux\.checkForUpdates[\s\S]*?this\.setState\(State\.Idle\(1 /\* Archive \*/, err\.message \|\| err\);\s*\}\);\s*\}'
    if re.search(l_orig_pat, content):
        content = re.sub(l_orig_pat, 'doCheckForUpdates(explicit, _pendingCommit) {\n        this.logService.info("update#doCheckForUpdates - Upstream Linux updates disabled in HugOS IDE");\n        this.setState(State.Idle(1 /* Archive */));\n        return;\n      }', content)
        changed = True

    # 6. Wire HugOS official release channel into Win32UpdateService.doCheckForUpdates
    win32_target_start = 'doCheckForUpdates(explicit, pendingCommit) {\n        if (!this.quality) {\n          return;\n        }\n        const internalOrg = this.getInternalOrg();\n        const background = !explicit && !internalOrg;\n        const url = this.buildUpdateFeedUrl(this.quality, pendingCommit ?? this.productService.commit, { background, internalOrg });\n        if (this.state.type !== "overwriting"'
    win32_check_repl = (
        'doCheckForUpdates(explicit, pendingCommit) {\n'
        '        if (!explicit) {\n'
        '          this.setState(State.Idle(getUpdateType()));\n'
        '          return;\n'
        '        }\n'
        '        this.logService.info("update#doCheckForUpdates - Querying HugOS official release channel...");\n'
        '        this.setState(State.CheckingForUpdates(true));\n'
        '        try {\n'
        '          const https = require("https");\n'
        '          const req = https.get("https://api.github.com/repos/oyesanyf/ModelFusion/releases/latest", {\n'
        '            headers: {\n'
        '              "User-Agent": "HugOS-IDE",\n'
        '              "Accept": "application/vnd.github.v3+json"\n'
        '            },\n'
        '            timeout: 10000\n'
        '          }, (res) => {\n'
        '            let data = "";\n'
        '            res.on("data", (chunk) => { data += chunk; });\n'
        '            res.on("end", () => {\n'
        '              this.setState(State.Idle(getUpdateType()));\n'
        '              let releaseTag = "v1.0.0-beta";\n'
        '              let htmlUrl = "https://github.com/oyesanyf/ModelFusion/releases";\n'
        '              try {\n'
        '                const parsed = JSON.parse(data);\n'
        '                if (parsed && parsed.tag_name) {\n'
        '                  releaseTag = parsed.tag_name;\n'
        '                  htmlUrl = parsed.html_url || htmlUrl;\n'
        '                }\n'
        '              } catch (e) {}\n'
        '              const { shell, dialog } = require("electron");\n'
        '              if (dialog && typeof dialog.showMessageBox === "function") {\n'
        '                dialog.showMessageBox({\n'
        '                  type: "info",\n'
        '                  title: "HugOS IDE Update",\n'
        '                  message: `HugOS IDE Official Release Channel\\n\\nLatest Release: ${releaseTag}\\n\\nOfficial signed releases and MSI packages are available at:\\n${htmlUrl}`,\n'
        '                  buttons: ["Open Download Page", "OK"],\n'
        '                  defaultId: 0,\n'
        '                  cancelId: 1\n'
        '                }).then((btnResult) => {\n'
        '                  if (btnResult && btnResult.response === 0) {\n'
        '                    if (shell && typeof shell.openExternal === "function") {\n'
        '                      shell.openExternal(htmlUrl);\n'
        '                    } else {\n'
        '                      this.nativeHostMainService.openExternal(void 0, htmlUrl);\n'
        '                    }\n'
        '                  }\n'
        '                }).catch(() => {\n'
        '                  this.nativeHostMainService.openExternal(void 0, htmlUrl);\n'
        '                });\n'
        '              } else {\n'
        '                this.nativeHostMainService.openExternal(void 0, htmlUrl);\n'
        '              }\n'
        '            });\n'
        '          });\n'
        '          req.on("error", (err) => {\n'
        '            this.logService.warn("update#doCheckForUpdates - GitHub request error, opening releases page:", err);\n'
        '            this.setState(State.Idle(getUpdateType()));\n'
        '            const releasesUrl = "https://github.com/oyesanyf/ModelFusion/releases";\n'
        '            const { shell } = require("electron");\n'
        '            if (shell && typeof shell.openExternal === "function") {\n'
        '              shell.openExternal(releasesUrl);\n'
        '            } else {\n'
        '              this.nativeHostMainService.openExternal(void 0, releasesUrl);\n'
        '            }\n'
        '          });\n'
        '          req.on("timeout", () => {\n'
        '            req.destroy();\n'
        '            this.setState(State.Idle(getUpdateType()));\n'
        '            const releasesUrl = "https://github.com/oyesanyf/ModelFusion/releases";\n'
        '            const { shell } = require("electron");\n'
        '            if (shell && typeof shell.openExternal === "function") {\n'
        '              shell.openExternal(releasesUrl);\n'
        '            } else {\n'
        '              this.nativeHostMainService.openExternal(void 0, releasesUrl);\n'
        '            }\n'
        '          });\n'
        '        } catch (e) {\n'
        '          this.logService.error("update#doCheckForUpdates error:", e);\n'
        '          this.setState(State.Idle(getUpdateType()));\n'
        '          this.nativeHostMainService.openExternal(void 0, "https://github.com/oyesanyf/ModelFusion/releases");\n'
        '        }\n'
        '      }\n      '
    )
    if win32_target_start in content:
        w_start = content.find(win32_target_start)
        w_end = content.find('async doDownloadUpdate', w_start)
        if w_start != -1 and w_end != -1:
            content = content[:w_start] + win32_check_repl + content[w_end:]
            changed = True

    # 7. Neutralize doDownloadUpdate in Win32UpdateService
    dl_pat = r'async\s+doDownloadUpdate\s*\(state\)\s*\{[\s\S]*?this\.setState\(State\.Idle\(getUpdateType\(\)\)\);\s*\}'
    dl_repl = (
        'async doDownloadUpdate(state) {\n'
        '        this.logService.info("update#doDownloadUpdate - Upstream download neutralized in HugOS IDE");\n'
        '        this.nativeHostMainService.openExternal(void 0, "https://github.com/oyesanyf/ModelFusion/releases");\n'
        '        this.setState(State.Idle(getUpdateType()));\n'
        '        return;\n'
        '      }'
    )
    if re.search(dl_pat, content):
        content = re.sub(dl_pat, dl_repl, content)
        changed = True

    # 8. Neutralize doApplyUpdate in Win32UpdateService
    apply_pat = r'async\s+doApplyUpdate\s*\(\)\s*\{[\s\S]*?cancelTimeout\.dispose\(\);[\s\S]*?cts\.dispose\(\);\s*\}\);\s*\}'
    apply_repl = (
        'async doApplyUpdate() {\n'
        '        this.logService.info("update#doApplyUpdate - Upstream update apply neutralized in HugOS IDE");\n'
        '        this.setState(State.Idle(getUpdateType()));\n'
        '        return Promise.resolve(void 0);\n'
        '      }'
    )
    if re.search(apply_pat, content):
        content = re.sub(apply_pat, apply_repl, content)
        changed = True

    # 9. Neutralize doQuitAndInstall in Win32UpdateService
    quit_pat = r'doQuitAndInstall\s*\(\)\s*\{[\s\S]*?env:\s*\{\s*\.\.\.process\.env,\s*__COMPAT_LAYER:\s*"RunAsInvoker"\s*\}\s*\}\);\s*\}\s*\}'
    quit_repl = (
        'doQuitAndInstall() {\n'
        '        this.logService.info("update#doQuitAndInstall - Upstream restart to update neutralized in HugOS IDE");\n'
        '        this.nativeHostMainService.openExternal(void 0, "https://github.com/oyesanyf/ModelFusion/releases");\n'
        '        this.setState(State.Idle(getUpdateType()));\n'
        '        return;\n'
        '      }'
    )
    if re.search(quit_pat, content):
        content = re.sub(quit_pat, quit_repl, content)
        changed = True

    return content, changed

def patch_main_file(file_path, node_path):
    """Patch a single main.js file and validate with node --check."""
    print(f"\n[CHECKING MAIN] {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Cannot read {file_path}: {e}")
        return False, False

    new_content, changed = patch_main_js_content(content)

    if not changed:
        print(f"  [INFO] main.js already patched and up to date.")
        return True, False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [OK] Patched {file_path}")
    except Exception as e:
        print(f"  [ERROR] Failed to write {file_path}: {e}")
        return False, False

    if node_path:
        res = subprocess.run([node_path, "--check", file_path], capture_output=True, text=True)
        if res.returncode != 0 and ("Cannot use import" in res.stderr or "Unexpected token 'export'" in res.stderr):
            with open(file_path, "rb") as mf:
                res = subprocess.run([node_path, "--input-type=module", "--check"], stdin=mf, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [ERROR] Node syntax check failed for {file_path}!")
            print(res.stderr)
            return False, False
        print(f"  [PASS] Node syntax validation passed.")
    return True, True

def cleanup_appdata():
    """Clean disabled extension entries in state.vscdb, remove CachedProfilesData, and clean update temp files."""
    app_data = os.environ.get("APPDATA", "")
    if not app_data:
        return

    hugos_dir = os.path.join(app_data, "HugOS")
    db_path = os.path.join(hugos_dir, "User", "globalStorage", "state.vscdb")
    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("UPDATE ItemTable SET value = '[]' WHERE key = 'extensionsIdentifiers/disabled'")
            affected = cur.rowcount
            conn.commit()
            conn.close()
            print(f"[CLEANUP] Cleared extensionsIdentifiers/disabled in {db_path} ({affected} row(s) updated).")
        except Exception as e:
            print(f"[CLEANUP ERROR] Failed to clean {db_path}: {e}")

    # Enforce update.mode: none in User settings.json and Machine settings.json
    user_settings_path = os.path.join(hugos_dir, "User", "settings.json")
    if os.path.isfile(user_settings_path):
        try:
            with open(user_settings_path, "r", encoding="utf-8") as f:
                us = json.load(f)
            updated_us = False
            if us.get("update.mode") != "none":
                us["update.mode"] = "none"
                updated_us = True
            if us.get("update.enableWindowsBackgroundUpdates") is not False:
                us["update.enableWindowsBackgroundUpdates"] = False
                updated_us = True
            if us.get("update.showReleaseNotes") is not False:
                us["update.showReleaseNotes"] = False
                updated_us = True
            if updated_us:
                with open(user_settings_path, "w", encoding="utf-8") as f:
                    json.dump(us, f, indent=4)
                print(f"[ENFORCE] Set 'update.mode': 'none' in User settings: {user_settings_path}")
        except Exception as e:
            print(f"[ENFORCE WARN] Failed to update {user_settings_path}: {e}")

    machine_dir = os.path.join(hugos_dir, "Machine")
    os.makedirs(machine_dir, exist_ok=True)
    machine_settings_path = os.path.join(machine_dir, "settings.json")
    try:
        ms = {}
        if os.path.isfile(machine_settings_path) and os.path.getsize(machine_settings_path) > 0:
            with open(machine_settings_path, "r", encoding="utf-8") as f:
                ms = json.load(f)
        updated_ms = False
        if ms.get("update.mode") != "none":
            ms["update.mode"] = "none"
            updated_ms = True
        if ms.get("update.enableWindowsBackgroundUpdates") is not False:
            ms["update.enableWindowsBackgroundUpdates"] = False
            updated_ms = True
        if ms.get("update.showReleaseNotes") is not False:
            ms["update.showReleaseNotes"] = False
            updated_ms = True
        if updated_ms:
            with open(machine_settings_path, "w", encoding="utf-8") as f:
                json.dump(ms, f, indent=4)
            print(f"[ENFORCE] Enforced 'update.mode': 'none' in Machine settings: {machine_settings_path}")
    except Exception as e:
        print(f"[ENFORCE WARN] Failed to write Machine settings {machine_settings_path}: {e}")

    cached_dir = os.path.join(hugos_dir, "CachedProfilesData")
    if os.path.isdir(cached_dir):
        for root, _, files in os.walk(cached_dir):
            for file in files:
                if "cache" in file.lower():
                    fp = os.path.join(root, file)
                    try:
                        os.remove(fp)
                        print(f"[CLEANUP] Removed cache file: {fp}")
                    except Exception as e:
                        print(f"[CLEANUP WARN] Could not remove {fp}: {e}")

    # Clean temporary update caches and flag files in %TEMP%
    temp_dir = os.environ.get("TEMP", "")
    if temp_dir and os.path.isdir(temp_dir):
        for entry in os.listdir(temp_dir):
            if entry.startswith("vscode-") or entry.startswith("CodeSetup") or entry.endswith(".flag") or entry == "update-progress":
                p = os.path.join(temp_dir, entry)
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                    print(f"[CLEANUP] Removed temporary update cache: {p}")
                except Exception:
                    pass

def main():
    print("============================================================")
    print("[HUGOS] Patching workbench & main.js (Chat & Update Routing)")
    print("============================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    skip_installed = any(arg.lower() in ("--skip-installed", "--check-installed=false") for arg in sys.argv)
    pack_dir_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pack_dir = (
        os.path.abspath(pack_dir_args[0].strip().strip('\"\''))
        if pack_dir_args
        else os.path.join(script_dir, "VSCode-win32-x64")
    )
    print(f"  Target packaging directory: {pack_dir}")

    node_path = find_node_executable()
    if node_path:
        print(f"  Using Node.js at: {node_path}")
    else:
        print(f"  [WARNING] node.exe not found! Syntax checks will be skipped.")

    targets = [
        os.path.join(pack_dir, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"),
        os.path.join(script_dir, "vscode", "out-vscode", "vs", "workbench", "workbench.desktop.main.js"),
    ]

    main_targets = [
        os.path.join(pack_dir, "resources", "app", "out", "main.js"),
    ]

    base_dirs = [pack_dir]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data and not skip_installed:
        hugos_installed = os.path.join(local_app_data, "HugOS IDE")
        base_dirs.append(hugos_installed)
        targets.append(os.path.join(hugos_installed, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js"))
        main_targets.append(os.path.join(hugos_installed, "resources", "app", "out", "main.js"))

    # Scan for versioned runtime directories ([0-9a-f]{7,40})
    for b in base_dirs:
        if b and os.path.isdir(b):
            for entry in os.listdir(b):
                if re.match(r"^[0-9a-f]{7,40}$", entry, re.IGNORECASE):
                    sub = os.path.join(b, entry)
                    if os.path.isdir(sub):
                        v_wb = os.path.join(sub, "resources", "app", "out", "vs", "workbench", "workbench.desktop.main.js")
                        if v_wb not in targets:
                            targets.append(v_wb)
                        v_main = os.path.join(sub, "resources", "app", "out", "main.js")
                        if v_main not in main_targets:
                            main_targets.append(v_main)

    seen = set()
    error_count = 0
    modified_count = 0
    for t in targets:
        if t and t not in seen and os.path.isfile(t):
            seen.add(t)
            success, changed = patch_workbench_file(t, node_path)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    seen_main = set()
    for mt in main_targets:
        if mt and mt not in seen_main and os.path.isfile(mt):
            seen_main.add(mt)
            success, changed = patch_main_file(mt, node_path)
            if not success:
                error_count += 1
            elif changed:
                modified_count += 1

    # AppData state DB and profile caches cleanup & update.mode enforcement
    cleanup_appdata()

    if error_count > 0:
        print(f"\n[ERROR] workbench/main.js patching failed with {error_count} error(s)!")
        sys.exit(1)

    print(f"\n[SUCCESS] workbench/main.js patching complete! ({len(seen)} workbench, {len(seen_main)} main validated, {modified_count} modified)")
    sys.exit(0)

if __name__ == "__main__":
    main()

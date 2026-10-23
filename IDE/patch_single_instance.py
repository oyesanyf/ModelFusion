import os, sys, shutil

def patch_main_js(file_path):
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}, does not exist.")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 0. Exclude globalThis.__hugosSplashWin from getAllWindowsExcludingOffscreen()
    old_offscreen = '''function getAllWindowsExcludingOffscreen() {
  return electron3.BrowserWindow.getAllWindows().filter((win) => !win.webContents.isOffscreen());
}'''
    new_offscreen = '''function getAllWindowsExcludingOffscreen() {
  return electron3.BrowserWindow.getAllWindows().filter((win) => win !== globalThis.__hugosSplashWin && !win.webContents.isOffscreen());
}'''
    if old_offscreen in content:
        content = content.replace(old_offscreen, new_offscreen, 1)
        changed = True

    # 1. Single-instance IPC claim & zombie socket fallback + splash hold before focus handoff
    target = '''          let client;
          try {
            client = await connect(environmentMainService.mainIPCHandle, "main");
          } catch (error2) {
            if (!retry2 || isWindows2 || error2.code !== "ECONNREFUSED") {
              if (error2.code === "EPERM") {
                this.showStartupWarningDialog(
                  localize(165, null, productService.nameShort),
                  localize(166, null),
                  productService
                );
              }
              throw error2;
            }
            try {
              unlinkSync2(environmentMainService.mainIPCHandle);
            } catch (error3) {
              logService.warn("Could not delete obsolete instance handle", error3);
              throw error3;
            }
            return this.claimInstance(logService, environmentMainService, lifecycleMainService, instantiationService, productService, false);
          }
          if (environmentMainService.extensionTestsLocationURI && !environmentMainService.debugExtensionHost.break) {
            const msg = `Running extension tests from the command line is currently only supported if no other instance of ${productService.nameShort} is running.`;
            logService.error(msg);
            client.dispose();
            throw new Error(msg);
          }
          let startupWarningDialogHandle = void 0;
          if (!environmentMainService.args.wait && !environmentMainService.args.status) {
            startupWarningDialogHandle = setTimeout(() => {
              this.showStartupWarningDialog(
                localize(167, null, productService.nameShort),
                localize(168, null),
                productService
              );
            }, 1e4);
          }
          const otherInstanceLaunchMainService = ProxyChannel.toService(client.getChannel("launch"), { disableMarshalling: true });
          const otherInstanceDiagnosticsMainService = ProxyChannel.toService(client.getChannel("diagnostics"), { disableMarshalling: true });
          if (environmentMainService.args.status) {
            return instantiationService.invokeFunction(async () => {
              const diagnosticsService = new DiagnosticsService(NullTelemetryService, productService);
              const mainDiagnostics = await otherInstanceDiagnosticsMainService.getMainDiagnostics();
              const remoteDiagnostics = await otherInstanceDiagnosticsMainService.getRemoteDiagnostics({ includeProcesses: true, includeWorkspaceMetadata: true });
              const diagnostics = await diagnosticsService.getDiagnostics(mainDiagnostics, remoteDiagnostics);
              console.log(diagnostics);
              throw new ExpectedError();
            });
          }
          if (isWindows2) {
            await this.windowsAllowSetForegroundWindow(otherInstanceLaunchMainService, logService);
          }
          logService.trace("Sending env to running instance...");
          await otherInstanceLaunchMainService.start(environmentMainService.args, process.env);
          client.dispose();
          if (startupWarningDialogHandle) {
            clearTimeout(startupWarningDialogHandle);
          }
          throw new ExpectedError("Sent env to running instance. Terminating...");'''

    prev_replacement = '''          if (isWindows2) {
            await this.windowsAllowSetForegroundWindow(otherInstanceLaunchMainService, logService);
          }
          logService.trace("Sending env to running instance...");
          try {
            await otherInstanceLaunchMainService.start(environmentMainService.args, process.env);
          } catch (startErr) {
            logService.warn("Failed to send env to running instance:", startErr);
            client.dispose();
            if (startupWarningDialogHandle) {
              clearTimeout(startupWarningDialogHandle);
            }
            if (retry2) {
              if (isWindows2) {
                environmentMainService.mainIPCHandle = `${environmentMainService.mainIPCHandle}-${process.pid}`;
              }
              return this.claimInstance(logService, environmentMainService, lifecycleMainService, instantiationService, productService, false);
            }
            throw startErr;
          }
          client.dispose();
          if (startupWarningDialogHandle) {
            clearTimeout(startupWarningDialogHandle);
          }
          try { if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) { globalThis.__hugosSplashWin.destroy(); globalThis.__hugosSplashWin = null; } } catch (_) {}
          throw new ExpectedError("Sent env to running instance. Terminating...");'''

    new_handoff_tail = '''          if (isWindows2) {
            await this.windowsAllowSetForegroundWindow(otherInstanceLaunchMainService, logService);
          }
          try {
            const elapsed = Date.now() - (globalThis.__hugosSplashStart || Date.now());
            if (elapsed < 900) {
              await new Promise((r) => setTimeout(r, 900 - elapsed));
            }
            if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) {
              globalThis.__hugosSplashWin.destroy();
              globalThis.__hugosSplashWin = null;
            }
          } catch (_) {}
          logService.trace("Sending env to running instance...");
          try {
            await otherInstanceLaunchMainService.start(environmentMainService.args, process.env);
          } catch (startErr) {
            logService.warn("Failed to send env to running instance:", startErr);
            client.dispose();
            if (startupWarningDialogHandle) {
              clearTimeout(startupWarningDialogHandle);
            }
            if (retry2) {
              if (isWindows2) {
                environmentMainService.mainIPCHandle = `${environmentMainService.mainIPCHandle}-${process.pid}`;
              }
              return this.claimInstance(logService, environmentMainService, lifecycleMainService, instantiationService, productService, false);
            }
            throw startErr;
          }
          client.dispose();
          if (startupWarningDialogHandle) {
            clearTimeout(startupWarningDialogHandle);
          }
          throw new ExpectedError("Sent env to running instance. Terminating...");'''

    replacement = '''          let client;
          try {
            client = await connect(environmentMainService.mainIPCHandle, "main");
          } catch (error2) {
            let isAlive = false;
            try {
              if (fs.existsSync(environmentMainService.mainLockfile)) {
                const lockPid = parseInt(fs.readFileSync(environmentMainService.mainLockfile, "utf8"), 10);
                if (!isNaN(lockPid) && lockPid !== process.pid) {
                  try { process.kill(lockPid, 0); isAlive = true; } catch (e) { if (e.code === "ESRCH") { try { fs.unlinkSync(environmentMainService.mainLockfile); } catch (_) {} } }
                }
              }
            } catch (_) {}

            if (retry2) {
              logService.warn("Could not connect to existing handle, falling back to unique socket handle", error2);
              try { unlinkSync2(environmentMainService.mainIPCHandle); } catch (_) {}
              if (isWindows2) {
                environmentMainService.mainIPCHandle = `${environmentMainService.mainIPCHandle}-${process.pid}`;
              }
              return this.claimInstance(logService, environmentMainService, lifecycleMainService, instantiationService, productService, false);
            }
            if (isAlive && error2.code === "EPERM") {
              this.showStartupWarningDialog(
                localize(165, null, productService.nameShort),
                localize(166, null),
                productService
              );
            }
            throw error2;
          }
          if (environmentMainService.extensionTestsLocationURI && !environmentMainService.debugExtensionHost.break) {
            const msg = `Running extension tests from the command line is currently only supported if no other instance of ${productService.nameShort} is running.`;
            logService.error(msg);
            client.dispose();
            throw new Error(msg);
          }
          let startupWarningDialogHandle = void 0;
          if (!environmentMainService.args.wait && !environmentMainService.args.status) {
            startupWarningDialogHandle = setTimeout(() => {
              let otherAlive = false;
              try {
                if (fs.existsSync(environmentMainService.mainLockfile)) {
                  const lockPid = parseInt(fs.readFileSync(environmentMainService.mainLockfile, "utf8"), 10);
                  if (!isNaN(lockPid) && lockPid !== process.pid) {
                    try { process.kill(lockPid, 0); otherAlive = true; } catch (_) {}
                  }
                }
              } catch (_) {}
              if (otherAlive) {
                this.showStartupWarningDialog(
                  localize(167, null, productService.nameShort),
                  localize(168, null),
                  productService
                );
              }
            }, 3e4);
          }
          const otherInstanceLaunchMainService = ProxyChannel.toService(client.getChannel("launch"), { disableMarshalling: true });
          const otherInstanceDiagnosticsMainService = ProxyChannel.toService(client.getChannel("diagnostics"), { disableMarshalling: true });
          if (environmentMainService.args.status) {
            return instantiationService.invokeFunction(async () => {
              const diagnosticsService = new DiagnosticsService(NullTelemetryService, productService);
              const mainDiagnostics = await otherInstanceDiagnosticsMainService.getMainDiagnostics();
              const remoteDiagnostics = await otherInstanceDiagnosticsMainService.getRemoteDiagnostics({ includeProcesses: true, includeWorkspaceMetadata: true });
              const diagnostics = await diagnosticsService.getDiagnostics(mainDiagnostics, remoteDiagnostics);
              console.log(diagnostics);
              throw new ExpectedError();
            });
          }
''' + new_handoff_tail

    if target in content:
        content = content.replace(target, replacement, 1)
        changed = True
    elif prev_replacement in content:
        content = content.replace(prev_replacement, new_handoff_tail, 1)
        changed = True

    # 2. Remove premature requestSingleInstanceLock() exit in CodeMain.main()
    bad_lock_block = '''    CodeMain = class {
      main() {
        if (!app14.requestSingleInstanceLock()) {
          app14.quit();
          return;
        }
        try {'''
    clean_lock_block = '''    CodeMain = class {
      main() {
        try {'''
    if bad_lock_block in content:
        content = content.replace(bad_lock_block, clean_lock_block, 1)
        changed = True

    # 3. Ensure BaseWindow2.applyState keeps splash visible for at least 1100ms while workbench renders, then promotes main window to z-order #1
    old_apply_state_orig = '''        if (state.mode === 0 /* Maximized */ || state.mode === 3 /* Fullscreen */) {
          this._win?.maximize();
          if (state.mode === 3 /* Fullscreen */) {
            this.setFullScreen(true, true);
          }
          this._win?.show();
        }
      }'''
    old_apply_state_prev = '''        if (state.mode === 0 /* Maximized */ || state.mode === 3 /* Fullscreen */) {
          this._win?.maximize();
          if (state.mode === 3 /* Fullscreen */) {
            this.setFullScreen(true, true);
          }
          this._win?.show();
        } else {
          this._win?.show();
        }
        try { this._win?.focus(); } catch (_) {}
        try { if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) { globalThis.__hugosSplashWin.destroy(); globalThis.__hugosSplashWin = null; } } catch (_) {}
      }'''
    new_apply_state = '''        if (state.mode === 0 /* Maximized */ || state.mode === 3 /* Fullscreen */) {
          this._win?.maximize();
          if (state.mode === 3 /* Fullscreen */) {
            this.setFullScreen(true, true);
          }
          this._win?.show();
        } else {
          this._win?.show();
        }
        const winRef = this._win;
        const finishSplashAndFocus = () => {
          try {
            if (winRef && !winRef.isDestroyed()) {
              if (winRef.isMinimized()) winRef.restore();
              winRef.show();
              winRef.setAlwaysOnTop(true, "screen-saver");
              winRef.focus();
              winRef.moveTop();
            }
          } catch (_) {}
          try {
            if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) {
              globalThis.__hugosSplashWin.destroy();
              globalThis.__hugosSplashWin = null;
            }
          } catch (_) {}
          setTimeout(() => {
            try {
              if (winRef && !winRef.isDestroyed()) {
                winRef.setAlwaysOnTop(false);
                winRef.focus();
              }
            } catch (_) {}
          }, 300);
        };
        const splashElapsed = Date.now() - (globalThis.__hugosSplashStart || Date.now());
        const waitMs = Math.max(950, 1350 - splashElapsed);
        setTimeout(finishSplashAndFocus, waitMs);
      }'''
    if old_apply_state_orig in content:
        content = content.replace(old_apply_state_orig, new_apply_state, 1)
        changed = True
    elif old_apply_state_prev in content:
        content = content.replace(old_apply_state_prev, new_apply_state, 1)
        changed = True

    # 3b. Ensure BaseWindow2.doFocusWindow promotes window to z-order #1 via setAlwaysOnTop(true) -> setAlwaysOnTop(false)
    old_do_focus = '''      doFocusWindow() {
        const win = this.win;
        if (!win) {
          return;
        }
        if (win.isMinimized()) {
          win.restore();
        }
        win.focus();
        win.webContents.focus();
      }'''
    new_do_focus = '''      doFocusWindow() {
        const win = this.win;
        if (!win) {
          return;
        }
        if (win.isMinimized()) {
          win.restore();
        }
        try {
          win.show();
          win.setAlwaysOnTop(true, "screen-saver");
          win.focus();
          win.moveTop();
          setTimeout(() => {
            try {
              if (!win.isDestroyed()) {
                win.setAlwaysOnTop(false);
                win.focus();
              }
            } catch (_) {}
          }, 250);
        } catch (_) {
          win.focus();
        }
        win.webContents.focus();
      }'''
    if old_do_focus in content:
        content = content.replace(old_do_focus, new_do_focus, 1)
        changed = True

    # 4. Add instant native Electron splash window in onReady() with __hugosSplashStart and screen-saver z-order
    old_on_ready_orig = '''async function onReady() {
  mark("code/mainAppReady");
  try {
    const [, nlsConfig] = await Promise.all([
      mkdirpIgnoreError(codeCachePath),
      resolveNlsConfiguration()
    ]);
    await startup(codeCachePath, nlsConfig);
  } catch (error) {
    console.error(error);
  }
}'''
    old_on_ready_prev = '''async function onReady() {
  mark("code/mainAppReady");
  try {
    if (!args["status"] && !args["version"] && !args["help"] && !args["locate-shell-integration-path"]) {
      const splash = new electron9.BrowserWindow({
        width: 440,
        height: 250,
        frame: false,
        resizable: false,
        movable: true,
        center: true,
        alwaysOnTop: true,
        show: true,
        backgroundColor: "#0d1117",
        title: "Starting HugOS IDE...",
        webPreferences: { nodeIntegration: false, contextIsolation: true }
      });
      const splashHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box;margin:0;padding:0;user-select:none}body{background:radial-gradient(circle at 50% 25%,#261019 0%,#0d1117 75%);color:#f0f6fc;font-family:"Segoe UI",system-ui,sans-serif;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid rgba(255,75,114,0.35);border-radius:10px;overflow:hidden}.ring{width:54px;height:54px;border-radius:50%;border:3px solid rgba(255,75,114,0.2);border-top-color:#ff4b72;border-right-color:#ff8a00;animation:spin 0.85s linear infinite;margin-bottom:18px;box-shadow:0 0 24px rgba(255,75,114,0.35)}@keyframes spin{to{transform:rotate(360deg)}}h1{font-size:20px;font-weight:700;letter-spacing:0.6px;background:linear-gradient(90deg,#fff,#ffb3c1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}p{font-size:12.5px;color:#8b949e;margin-bottom:20px}.bar{width:280px;height:4px;background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;position:relative}.fill{width:45%;height:100%;background:linear-gradient(90deg,#ff4b72,#ff8a00);border-radius:4px;position:absolute;animation:slide 1.1s ease-in-out infinite}@keyframes slide{0%{left:-45%}100%{left:100%}}</style></head><body><div class="ring"></div><h1>HugOS IDE</h1><p>Initializing ModelFusion AI Operating System...</p><div class="bar"><div class="fill"></div></div></body></html>`;
      splash.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(splashHtml)).catch(() => {});
      splash.show();
      splash.focus();
      globalThis.__hugosSplashWin = splash;
      setTimeout(() => {
        try { if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) { globalThis.__hugosSplashWin.destroy(); globalThis.__hugosSplashWin = null; } } catch (_) {}
      }, 6500);
    }
  } catch (_) {}
  try {
    const [, nlsConfig] = await Promise.all([
      mkdirpIgnoreError(codeCachePath),
      resolveNlsConfiguration()
    ]);
    await startup(codeCachePath, nlsConfig);
  } catch (error) {
    console.error(error);
  }
}'''
    new_on_ready = '''async function onReady() {
  mark("code/mainAppReady");
  try {
    if (!args["status"] && !args["version"] && !args["help"] && !args["locate-shell-integration-path"]) {
      globalThis.__hugosSplashStart = Date.now();
      const splash = new electron9.BrowserWindow({
        width: 440,
        height: 250,
        frame: false,
        resizable: false,
        movable: true,
        center: true,
        alwaysOnTop: true,
        show: true,
        backgroundColor: "#0d1117",
        title: "Starting HugOS IDE...",
        webPreferences: { nodeIntegration: false, contextIsolation: true }
      });
      const splashHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box;margin:0;padding:0;user-select:none}body{background:radial-gradient(circle at 50% 25%,#261019 0%,#0d1117 75%);color:#f0f6fc;font-family:"Segoe UI",system-ui,sans-serif;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid rgba(255,75,114,0.35);border-radius:10px;overflow:hidden}.ring{width:54px;height:54px;border-radius:50%;border:3px solid rgba(255,75,114,0.2);border-top-color:#ff4b72;border-right-color:#ff8a00;animation:spin 0.85s linear infinite;margin-bottom:18px;box-shadow:0 0 24px rgba(255,75,114,0.35)}@keyframes spin{to{transform:rotate(360deg)}}h1{font-size:20px;font-weight:700;letter-spacing:0.6px;background:linear-gradient(90deg,#fff,#ffb3c1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px}p{font-size:12.5px;color:#8b949e;margin-bottom:20px}.bar{width:280px;height:4px;background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;position:relative}.fill{width:45%;height:100%;background:linear-gradient(90deg,#ff4b72,#ff8a00);border-radius:4px;position:absolute;animation:slide 1.1s ease-in-out infinite}@keyframes slide{0%{left:-45%}100%{left:100%}}</style></head><body><div class="ring"></div><h1>HugOS IDE</h1><p>Initializing ModelFusion AI Operating System...</p><div class="bar"><div class="fill"></div></div></body></html>`;
      splash.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(splashHtml)).catch(() => {});
      try { splash.setAlwaysOnTop(true, "screen-saver"); } catch (_) {}
      splash.show();
      splash.focus();
      try { splash.moveTop(); } catch (_) {}
      globalThis.__hugosSplashWin = splash;
      setTimeout(() => {
        try { if (globalThis.__hugosSplashWin && !globalThis.__hugosSplashWin.isDestroyed()) { globalThis.__hugosSplashWin.destroy(); globalThis.__hugosSplashWin = null; } } catch (_) {}
      }, 6500);
    }
  } catch (_) {}
  try {
    const [, nlsConfig] = await Promise.all([
      mkdirpIgnoreError(codeCachePath),
      resolveNlsConfiguration()
    ]);
    await startup(codeCachePath, nlsConfig);
  } catch (error) {
    console.error(error);
  }
}'''
    if old_on_ready_orig in content:
        content = content.replace(old_on_ready_orig, new_on_ready, 1)
        changed = True
    elif old_on_ready_prev in content:
        content = content.replace(old_on_ready_prev, new_on_ready, 1)
        changed = True

    # 5. Ensure clicking HugOS IDE when already running restores and focuses existing window instead of opening duplicate empty windows
    old_open_without_args = '''              default:
                openNewWindow = !isMacintosh;'''
    new_open_without_args = '''              default:
                openNewWindow = false;'''
    if old_open_without_args in content:
        content = content.replace(old_open_without_args, new_open_without_args, 1)
        changed = True

    old_open_existing_orig = '''      openExistingWindow(window, openConfig) {
        window.focus();'''
    old_open_existing_prev = '''      openExistingWindow(window, openConfig) {
        try {
          if (window.win?.isMinimized()) { window.win.restore(); }
          window.win?.show();
        } catch (_) {}
        window.focus();'''
    new_open_existing = '''      openExistingWindow(window, openConfig) {
        try {
          if (window.win && !window.win.isDestroyed()) {
            if (window.win.isMinimized()) { window.win.restore(); }
            window.win.show();
            window.win.setAlwaysOnTop(true, "screen-saver");
            window.win.focus();
            window.win.moveTop();
            setTimeout(() => {
              try {
                if (window.win && !window.win.isDestroyed()) {
                  window.win.setAlwaysOnTop(false);
                  window.win.focus();
                }
              } catch (_) {}
            }, 250);
          }
        } catch (_) {}
        window.focus();'''
    if old_open_existing_orig in content:
        content = content.replace(old_open_existing_orig, new_open_existing, 1)
        changed = True
    elif old_open_existing_prev in content:
        content = content.replace(old_open_existing_prev, new_open_existing, 1)
        changed = True

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Patched single-instance & instant splash logic in {file_path}")
        return True
    elif "falling back to unique socket handle" in content and "globalThis.__hugosSplashStart" in content:
        print(f"[ALREADY PATCHED] {file_path}")
        return True
    else:
        print(f"[WARN] Target not found in {file_path}")
        return False

def sync_native_stubs():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stubs_dir = os.path.join(repo_root, "IDE", "patches", "native_stubs")
    if not os.path.isdir(stubs_dir):
        return
    stub_map = {
        "@vscode_policy-watcher_index.js": os.path.join("resources", "app", "node_modules", "@vscode", "policy-watcher", "index.js"),
        "@vscode_spdlog_index.js": os.path.join("resources", "app", "node_modules", "@vscode", "spdlog", "index.js"),
        "@vscode_windows-mutex_index.js": os.path.join("resources", "app", "node_modules", "@vscode", "windows-mutex", "index.js"),
        "windows-foreground-love_index.js": os.path.join("resources", "app", "node_modules", "windows-foreground-love", "index.js"),
    }
    base_roots = [
        os.path.join(repo_root, "IDE", "VSCode-win32-x64"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "7e7950df89"),
        os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE"),
        os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\7e7950df89"),
    ]
    for base in base_roots:
        if not os.path.isdir(base):
            continue
        for stub_name, rel_dst in stub_map.items():
            src = os.path.join(stubs_dir, stub_name)
            dst = os.path.join(base, rel_dst)
            if os.path.isfile(src) and os.path.isdir(os.path.dirname(dst)):
                try:
                    shutil.copyfile(src, dst)
                except Exception as e:
                    print(f"[WARN] Could not copy stub {stub_name} to {dst}: {e}")

if __name__ == "__main__":
    sync_native_stubs()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "resources", "app", "out", "main.js"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "7e7950df89", "resources", "app", "out", "main.js"),
        os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\resources\app\out\main.js"),
        os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\7e7950df89\resources\app\out\main.js"),
    ]
    for t in targets:
        patch_main_js(t)

import os, sys

def patch_main_js(file_path):
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}, does not exist.")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

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
          if (isWindows2) {
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
          throw new ExpectedError("Sent env to running instance. Terminating...");'''

    if target in content:
        content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] Patched single-instance logic in {file_path}")
        return True
    elif "falling back to unique socket handle" in content:
        print(f"[ALREADY PATCHED] {file_path}")
        return True
    else:
        print(f"[WARN] Target not found in {file_path}")
        return False

if __name__ == "__main__":
    targets = [
        "IDE/VSCode-win32-x64/resources/app/out/main.js",
        "IDE/VSCode-win32-x64/7e7950df89/resources/app/out/main.js"
    ]
    for t in targets:
        patch_main_js(t)

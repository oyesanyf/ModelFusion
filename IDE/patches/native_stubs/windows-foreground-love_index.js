// HugOS stub: windows-foreground-love native addon (.node) is not shipped with this build.
// Foreground activation is handled directly via Electron setAlwaysOnTop + Win32 SetWindowPos.
exports.allowSetForegroundWindow = function (_pid) {
  return true;
};

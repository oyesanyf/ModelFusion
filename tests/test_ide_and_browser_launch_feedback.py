import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestIdeAndBrowserLaunchFeedback(unittest.TestCase):
    def test_policy_watcher_stub_fires_callback(self):
        """Ensure @vscode/policy-watcher stub fires _callback({}) so CodeMain.initServices() never deadlocks."""
        stub_paths = [
            os.path.join(REPO_ROOT, "IDE", "patches", "native_stubs", "@vscode_policy-watcher_index.js"),
            os.path.join(REPO_ROOT, "IDE", "VSCode-win32-x64", "resources", "app", "node_modules", "@vscode", "policy-watcher", "index.js"),
        ]
        local_ide = os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\resources\app\node_modules\@vscode\policy-watcher\index.js")
        if os.path.exists(local_ide):
            stub_paths.append(local_ide)

        for path in stub_paths:
            self.assertTrue(os.path.exists(path), f"Missing policy-watcher stub at {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("_callback({})", content, f"policy-watcher stub at {path} must invoke _callback({{}})")
            self.assertIn("queueMicrotask", content, f"policy-watcher stub at {path} must invoke _callback asynchronously")

    def test_ide_main_js_has_splash_and_no_premature_lock_quit(self):
        """Verify main.js has instant splash feedback, unconditional window show/focus, and no premature lock quit."""
        main_paths = [
            os.path.join(REPO_ROOT, "IDE", "VSCode-win32-x64", "resources", "app", "out", "main.js"),
        ]
        local_main = os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\resources\app\out\main.js")
        if os.path.exists(local_main):
            main_paths.append(local_main)

        for path in main_paths:
            self.assertTrue(os.path.exists(path), f"Missing main.js at {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("globalThis.__hugosSplashWin", content, f"Missing instant splash window in {path}")
            self.assertIn("globalThis.__hugosSplashStart", content, f"Missing splash timer in {path}")
            self.assertIn("Starting HugOS IDE...", content, f"Missing splash title in {path}")
            self.assertIn('setAlwaysOnTop(true, "screen-saver")', content, f"Missing foreground promotion in {path}")
            self.assertNotIn(
                "if (!app14.requestSingleInstanceLock()) {\n          app14.quit();\n          return;\n        }",
                content,
                f"Premature requestSingleInstanceLock quit still present in {path}",
            )

    def test_browser_vbs_direct_launch_and_hta_splash(self):
        """Verify hugos-browser.vbs launches hugos-splash.hta and chrome.exe directly without cmd.exe and focuses window."""
        vbs_path = os.path.join(REPO_ROOT, "browser", "Chromium-win32-x64", "hugos-browser.vbs")
        hta_path = os.path.join(REPO_ROOT, "browser", "Chromium-win32-x64", "hugos-splash.hta")
        wix_gen_path = os.path.join(REPO_ROOT, "browser", "generate_wix.js")

        self.assertTrue(os.path.exists(vbs_path), "Missing hugos-browser.vbs")
        self.assertTrue(os.path.exists(hta_path), "Missing hugos-splash.hta")

        with open(vbs_path, "r", encoding="utf-8") as f:
            vbs_content = f.read()
        self.assertIn("hugos-splash.hta", vbs_content)
        self.assertIn("chrome.exe", vbs_content)
        self.assertIn("--check-browser-window", vbs_content)
        self.assertIn("--focus-browser", vbs_content)
        self.assertNotIn("cmd.exe /c", vbs_content)

        with open(wix_gen_path, "r", encoding="utf-8") as f:
            wix_content = f.read()
        self.assertIn("[SystemFolder]wscript.exe", wix_content)
        self.assertIn("hugos-browser.vbs", wix_content)


def get_default_desktop_windows():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    wins = []

    def cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if title and title not in ("Program Manager", "Settings", "Windows Input Experience", "MSCTFIME UI", "Default IME"):
                    wins.append((hwnd, title))
        return True

    user32.EnumDesktopWindows(hdesk, WNDENUMPROC(cb), 0)
    user32.CloseDesktop(hdesk)
    return wins


def wmi_launch(cmd_line):
    import subprocess
    ps = f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine='{cmd_line}'}} | Out-Null"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def run_live_desktop_verification():
    import subprocess
    import time

    print("=== Live Desktop Verification (WinSta0\\Default) ===")
    # 0. Clean slate for Browser and IDE
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         'Get-Process -Name "HugOS","mshta" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; '
         'Get-CimInstance Win32_Process -Filter "Name=\'chrome.exe\'" | Where-Object { $_.CommandLine -like "*HugOS Browser*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }'],
        check=False
    )
    # Close any stale llama-server.exe window if still lingering from earlier session
    import ctypes
    for hwnd, title in get_default_desktop_windows():
        if "llama-server.exe" in title.lower():
            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
    time.sleep(1.0)

    vbs_path = os.path.expandvars(r"%LOCALAPPDATA%\HugOS Browser\Chromium-win32-x64\hugos-browser.vbs")
    ide_exe = os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE\HugOS.exe")

    # 1. Cold start HugOS Browser
    print("\n[1/4] Testing Cold Start of HugOS Browser...")
    wmi_launch(f'wscript.exe //B //Nologo "{vbs_path}"')
    saw_browser_splash_top = False
    t0 = time.time()
    while time.time() - t0 < 4.5:
        wins = get_default_desktop_windows()
        top_title = wins[0][1] if wins else ""
        if "Starting HugOS Browser" in top_title:
            saw_browser_splash_top = True
        time.sleep(0.08)
    wins = get_default_desktop_windows()
    top3 = [w[1] for w in wins[:3]]
    browser_wins = [w for w in wins if "HugOS Browser | ModelFusion" in w[1]]
    console_wins = [w for w in wins if "llama-server" in w[1].lower() or "cmd.exe" in w[1].lower()]
    print(f"  -> saw_splash_at_z1={saw_browser_splash_top}, top3={top3}, browser_count={len(browser_wins)}, console_wins={console_wins}")
    assert saw_browser_splash_top, "Browser splash never appeared at z-order #1"
    assert wins and "HugOS Browser | ModelFusion" in wins[0][1], f"HugOS Browser not at z-order #1: {top3}"
    assert len(browser_wins) == 1, f"Expected 1 HugOS Browser window, found {len(browser_wins)}"
    assert len(console_wins) == 0, f"Unexpected console windows: {console_wins}"

    # 2. Warm start HugOS Browser (deduplication & foreground restoration)
    print("\n[2/4] Testing Warm Start of HugOS Browser...")
    wmi_launch(f'wscript.exe //B //Nologo "{vbs_path}"')
    saw_warm_browser_splash = False
    t0 = time.time()
    while time.time() - t0 < 2.5:
        wins = get_default_desktop_windows()
        if wins and "Starting HugOS Browser" in wins[0][1]:
            saw_warm_browser_splash = True
        time.sleep(0.08)
    wins = get_default_desktop_windows()
    top3 = [w[1] for w in wins[:3]]
    browser_wins = [w for w in wins if "HugOS Browser | ModelFusion" in w[1]]
    print(f"  -> saw_warm_splash_at_z1={saw_warm_browser_splash}, top3={top3}, browser_count={len(browser_wins)}")
    assert wins and "HugOS Browser | ModelFusion" in wins[0][1], f"HugOS Browser not at z-order #1 after warm launch: {top3}"
    assert len(browser_wins) == 1, f"Duplicate HugOS Browser windows opened: {len(browser_wins)}"

    # 3. Cold start HugOS IDE
    print("\n[3/4] Testing Cold Start of HugOS IDE...")
    wmi_launch(f'"{ide_exe}"')
    saw_ide_splash_top = False
    splash_first_seen = None
    splash_last_seen = None
    t0 = time.time()
    while time.time() - t0 < 5.5:
        wins = get_default_desktop_windows()
        if wins and "Starting HugOS IDE" in wins[0][1]:
            saw_ide_splash_top = True
            now = time.time()
            if splash_first_seen is None:
                splash_first_seen = now
            splash_last_seen = now
        time.sleep(0.08)
    wins = get_default_desktop_windows()
    top3 = [w[1] for w in wins[:3]]
    ide_wins = [w for w in wins if "HugOS IDE" in w[1] and "Starting" not in w[1]]
    console_wins = [w for w in wins if "llama-server" in w[1].lower() or "cmd.exe" in w[1].lower()]
    splash_dur = (splash_last_seen - splash_first_seen) if (splash_first_seen and splash_last_seen) else 0.0
    print(f"  -> saw_splash_at_z1={saw_ide_splash_top}, splash_duration={splash_dur:.2f}s, top3={top3}, ide_count={len(ide_wins)}, console_wins={console_wins}")
    assert saw_ide_splash_top, "IDE splash never appeared at z-order #1"
    assert wins and "HugOS IDE" in wins[0][1] and "Starting" not in wins[0][1], f"HugOS IDE not at z-order #1: {top3}"
    assert len(ide_wins) == 1, f"Expected 1 HugOS IDE window, found {len(ide_wins)}"
    assert len(console_wins) == 0, f"Unexpected console windows: {console_wins}"

    # 4. Warm start HugOS IDE (while HugOS Browser is brought to front first)
    print("\n[4/4] Testing Warm Start of HugOS IDE (from behind HugOS Browser)...")
    subprocess.run([os.path.join(REPO_ROOT, "target", "release", "cli.exe"), "--focus-browser"], check=False)
    time.sleep(0.4)
    wmi_launch(f'"{ide_exe}"')
    saw_warm_ide_splash = False
    t0 = time.time()
    while time.time() - t0 < 3.5:
        wins = get_default_desktop_windows()
        if wins and "Starting HugOS IDE" in wins[0][1]:
            saw_warm_ide_splash = True
        time.sleep(0.08)
    wins = get_default_desktop_windows()
    top3 = [w[1] for w in wins[:3]]
    ide_wins = [w for w in wins if "HugOS IDE" in w[1] and "Starting" not in w[1]]
    print(f"  -> saw_warm_splash_at_z1={saw_warm_ide_splash}, top3={top3}, ide_count={len(ide_wins)}")
    assert saw_warm_ide_splash, "Warm IDE splash never appeared at z-order #1"
    assert wins and "HugOS IDE" in wins[0][1] and "Starting" not in wins[0][1], f"HugOS IDE not promoted to z-order #1 on warm start: {top3}"
    assert len(ide_wins) == 1, f"Duplicate HugOS IDE windows opened: {len(ide_wins)}"
    print("\nALL 4 LIVE DESKTOP VERIFICATION SCENARIOS PASSED 100%!")


if __name__ == "__main__":
    import sys
    if "--live-desktop" in sys.argv:
        sys.argv.remove("--live-desktop")
        run_live_desktop_verification()
    unittest.main()



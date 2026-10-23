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


if __name__ == "__main__":
    unittest.main()


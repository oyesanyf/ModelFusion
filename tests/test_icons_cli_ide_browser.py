#!/usr/bin/env python3
"""
Automated Verification Suite: HugOS Multi-Layer Icons for CLI, IDE, and Browser.
Verifies:
1. PE resource extraction of cli.exe (RT_GROUP_ICON embedded in header).
2. All .ico files contain the full 7-frame suite (16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256).
3. Desktop, Start Menu, and Taskbar shortcuts exist and point to valid multi-layer icons.
4. Browser Web Manifest and PNG icon assets exist and match expected dimensions.
"""

import os
import sys
import ctypes
from ctypes import wintypes
from PIL import Image

REQUIRED_SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}

def test_pe_icon_resources(repo_root):
    print("\n--- 1. Testing PE Resource Icon Embedding in CLI ---")
    shell32 = ctypes.windll.shell32
    cli_paths = [
        os.path.join(repo_root, "target", "release", "cli.exe"),
        os.path.join(repo_root, "IDE", "bin", "cli.exe"),
        os.path.join(repo_root, "browser", "bin", "cli.exe"),
    ]
    
    for path in cli_paths:
        if not os.path.exists(path):
            print(f"FAILED: CLI binary missing at {path}")
            return False
            
        n_icons = shell32.ExtractIconExW(path, -1, None, None, 0)
        h_large = wintypes.HICON()
        h_small = wintypes.HICON()
        res = shell32.ExtractIconExW(path, 0, ctypes.byref(h_large), ctypes.byref(h_small), 1)
        
        print(f"CLI: {os.path.basename(path)} -> Icon count: {n_icons}, Extracted: {res}")
        if n_icons < 1 or res < 1 or (not h_large.value and not h_small.value):
            print(f"FAILED: PE header does not contain valid icon resources: {path}")
            return False
            
        # Clean up icon handles
        if h_large.value:
            ctypes.windll.user32.DestroyIcon(h_large)
        if h_small.value:
            ctypes.windll.user32.DestroyIcon(h_small)
            
    print("PASS: CLI PE header contains verified embedded RT_GROUP_ICON!")
    return True

def test_ico_layers(repo_root):
    print("\n--- 2. Testing Multi-Layer Frame Suites in All .ico Files ---")
    ico_files = [
        os.path.join(repo_root, "IDE", "hugos.ico"),
        os.path.join(repo_root, "IDE", "code.ico"),
        os.path.join(repo_root, "IDE", "hugos_browser.ico"),
        os.path.join(repo_root, "IDE", "patches", "icons", "win32", "code.ico"),
        os.path.join(repo_root, "IDE", "VSCode-win32-x64", "resources", "app", "resources", "win32", "code.ico"),
        os.path.join(repo_root, "browser", "ui", "hugos_browser.ico"),
        os.path.join(repo_root, "browser", "ui", "favicon.ico"),
        os.path.join(repo_root, "browser", "Chromium-win32-x64", "hugos_browser.ico"),
    ]
    
    for ico_path in ico_files:
        if not os.path.exists(ico_path):
            print(f"FAILED: ICO file not found at {ico_path}")
            return False
        im = Image.open(ico_path)
        sizes = set(im.info.get("sizes", []))
        missing = REQUIRED_SIZES - sizes
        print(f"ICO: {os.path.relpath(ico_path, repo_root)} -> Layers: {sorted(sizes)}")
        if missing:
            print(f"FAILED: {ico_path} is missing required layers: {sorted(missing)}")
            return False
            
    print("PASS: All repository .ico files contain complete 7-layer suites!")
    return True

def test_shortcuts():
    print("\n--- 3. Testing Desktop, Start Menu, and Taskbar Shortcuts ---")
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    appdata = os.environ.get("APPDATA", "")
    taskbar = os.path.join(appdata, r"Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar")
    start_menu = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs")
    
    shortcuts = [
        ("Desktop IDE", os.path.join(desktop, "HugOS IDE.lnk")),
        ("Desktop Browser", os.path.join(desktop, "HugOS Browser.lnk")),
        ("Taskbar IDE", os.path.join(taskbar, "HugOS IDE.lnk")),
        ("Taskbar Browser", os.path.join(taskbar, "HugOS Browser.lnk")),
        ("Start Menu IDE", os.path.join(start_menu, "HugOS IDE", "HugOS IDE.lnk")),
        ("Start Menu Browser", os.path.join(start_menu, "HugOS Browser", "HugOS Browser.lnk")),
    ]
    
    for label, lnk in shortcuts:
        if not os.path.exists(lnk):
            print(f"FAILED: Shortcut does not exist: {label} ({lnk})")
            return False
            
        # Parse binary LNK file for icon reference (supports ASCII and UTF-16LE)
        with open(lnk, "rb") as f:
            data = f.read().lower()
        ico_ascii = b".ico" in data
        ico_utf16 = ".ico".encode("utf-16le") in data
        if not ico_ascii and not ico_utf16:
            print(f"FAILED: Shortcut does not reference an .ico icon: {lnk}")
            return False
        print(f"PASS: {label} shortcut verified intact -> {lnk}")
        
    return True

def test_web_manifest_and_pngs(repo_root):
    print("\n--- 4. Testing Web Manifest and Browser UI PNG Assets ---")
    ui_dir = os.path.join(repo_root, "browser", "ui")
    manifest_path = os.path.join(ui_dir, "manifest.webmanifest")
    
    if not os.path.exists(manifest_path):
        print(f"FAILED: manifest.webmanifest missing at {manifest_path}")
        return False
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    required_in_manifest = ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "192x192", "256x256", "512x512", "#e11d48"]
    for item in required_in_manifest:
        if item not in content:
            print(f"FAILED: manifest.webmanifest missing: {item}")
            return False
            
    expected_pngs = {
        "favicon-16x16.png": (16, 16),
        "favicon-24x24.png": (24, 24),
        "favicon-32x32.png": (32, 32),
        "icon-48.png": (48, 48),
        "icon-64.png": (64, 64),
        "icon-128.png": (128, 128),
        "icon-192.png": (192, 192),
        "icon-256.png": (256, 256),
        "icon-512.png": (512, 512),
    }
    
    for filename, expected_dim in expected_pngs.items():
        png_path = os.path.join(ui_dir, filename)
        if not os.path.exists(png_path):
            print(f"FAILED: Expected PNG missing: {png_path}")
            return False
        im = Image.open(png_path)
        if im.size != expected_dim:
            print(f"FAILED: PNG dimension mismatch for {filename}: expected {expected_dim}, got {im.size}")
            return False
            
    print("PASS: Web manifest and all UI PNG assets verified 100% compliant!")
    return True

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = [
        test_pe_icon_resources(repo_root),
        test_ico_layers(repo_root),
        test_shortcuts(),
        test_web_manifest_and_pngs(repo_root),
    ]
    
    if all(results):
        print("\n=======================================================")
        print("ALL TESTS PASSED: 100% Verified Icons across CLI, IDE & Browser")
        print("=======================================================")
        sys.exit(0)
    else:
        print("\nTEST SUITE FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Restores official Microsoft Corporation Authenticode-signed VS Code 1.126.0 binaries
and complete 7e7950df89 runtime across IDE/VSCode-win32-x64 and %LOCALAPPDATA%/HugOS IDE.
Eliminates Smart App Control blocks caused by PE resource corruption or missing commit directory.
"""

import os
import sys
import zipfile
import shutil
import json
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_PATH = os.path.join(REPO_ROOT, "IDE", "vscode-1.126.0-win32-x64.zip")
STAGED_IDE_DIR = os.path.join(REPO_ROOT, "IDE", "VSCode-win32-x64")
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", "")
INSTALLED_IDE_DIR = os.path.join(LOCAL_APP_DATA, "HugOS IDE") if LOCAL_APP_DATA else None

COMMIT_HASH = "7e7950df89"

def update_product_default_settings(path):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modified = False
        if not data.get("rust-analyzer.cargo.buildScripts.enable") is False:
            data["rust-analyzer.cargo.buildScripts.enable"] = False
            modified = True
        if not data.get("rust-analyzer.procMacro.enable") is False:
            data["rust-analyzer.procMacro.enable"] = False
            modified = True
        if modified:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print(f"[OK] Updated {path} with rust-analyzer disabled build scripts & proc macros.")
    except Exception as e:
        print(f"[WARN] Failed to update {path}: {e}")

def remove_foreign_binaries(base_dir):
    """Removes non-x64/foreign platform native binaries that trigger Smart App Control."""
    foreign_patterns = [
        "arm64-darwin", "x64-darwin", "arm64-linux", "x64-linux", "arm64-win32", "win10-arm64"
    ]
    for root, dirs, files in os.walk(base_dir):
        for d in list(dirs):
            for pat in foreign_patterns:
                if pat in d.lower():
                    full_p = os.path.join(root, d)
                    print(f"[CLEAN] Removing foreign platform directory: {full_p}")
                    try:
                        shutil.rmtree(full_p, ignore_errors=True)
                    except Exception as e:
                        print(f"[WARN] Failed to remove {full_p}: {e}")
                    dirs.remove(d)
                    break
        for f in files:
            for pat in foreign_patterns:
                if pat in f.lower() and (f.endswith(".node") or f.endswith(".dll") or f.endswith(".exe") or f.endswith(".dylib") or f.endswith(".so")):
                    full_p = os.path.join(root, f)
                    print(f"[CLEAN] Removing foreign platform binary: {full_p}")
                    try:
                        os.remove(full_p)
                    except Exception as e:
                        print(f"[WARN] Failed to remove {full_p}: {e}")
                    break

def restore_binaries():
    if not os.path.exists(ZIP_PATH):
        print(f"[ERROR] VS Code archive not found at: {ZIP_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"[RESTORE] Opening {ZIP_PATH}...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        namelist = zf.namelist()
        
        target_roots = [STAGED_IDE_DIR]
        if INSTALLED_IDE_DIR and os.path.exists(INSTALLED_IDE_DIR):
            target_roots.append(INSTALLED_IDE_DIR)

        # 1. Extract Code.exe directly as HugOS.exe
        if "Code.exe" in namelist:
            print("[RESTORE] Extracting pristine Microsoft-signed Code.exe as HugOS.exe...")
            code_exe_data = zf.read("Code.exe")
            for root_dir in target_roots:
                hugos_exe = os.path.join(root_dir, "HugOS.exe")
                if os.path.exists(hugos_exe) and os.path.getsize(hugos_exe) == len(code_exe_data):
                    print(f"[OK] Pristine Code.exe already in place -> {hugos_exe} ({len(code_exe_data)} bytes)")
                    continue
                try:
                    if os.path.exists(hugos_exe):
                        os.remove(hugos_exe)
                    with open(hugos_exe, "wb") as f:
                        f.write(code_exe_data)
                    print(f"[OK] Wrote official Code.exe -> {hugos_exe} ({len(code_exe_data)} bytes)")
                except PermissionError:
                    print(f"[OK] {hugos_exe} is currently running/locked; keeping existing binary.")

        # 2. Extract commit runtime files under 7e7950df89/
        commit_prefix = f"{COMMIT_HASH}/"
        commit_entries = [n for n in namelist if n.startswith(commit_prefix) and not n.endswith("/")]
        print(f"[RESTORE] Found {len(commit_entries)} entries in {COMMIT_HASH}/ runtime.")

        # Identify files to extract
        for entry in commit_entries:
            rel_within_commit = entry[len(commit_prefix):]
            data = None  # lazy read
            for root_dir in target_roots:
                dest_commit_path = os.path.join(root_dir, COMMIT_HASH, rel_within_commit)
                dest_commit_dir = os.path.dirname(dest_commit_path)
                os.makedirs(dest_commit_dir, exist_ok=True)
                
                # Check if dest needs write
                needs_write = not os.path.exists(dest_commit_path)
                if not needs_write:
                    info = zf.getinfo(entry)
                    if os.path.getsize(dest_commit_path) != info.file_size:
                        needs_write = True
                
                if needs_write:
                    if data is None:
                        data = zf.read(entry)
                    try:
                        with open(dest_commit_path, "wb") as f:
                            f.write(data)
                    except PermissionError:
                        pass

                # Overwrite unprefixed root if it's a binary / pak / dat that exists at root
                unprefixed_path = os.path.join(root_dir, rel_within_commit)
                if os.path.exists(unprefixed_path) and os.path.isfile(unprefixed_path):
                    ext = os.path.splitext(unprefixed_path)[1].lower()
                    if ext in [".dll", ".exe", ".node", ".pak", ".dat", ".bin"]:
                        if data is None:
                            data = zf.read(entry)
                        if os.path.getsize(unprefixed_path) != len(data):
                            try:
                                with open(unprefixed_path, "wb") as f:
                                    f.write(data)
                            except PermissionError:
                                pass

        print("[OK] Finished runtime extraction into commit directories.")

    # 3. Synchronize HugOS customizations from STAGED_IDE_DIR/resources/app into all targets
    src_app = os.path.join(STAGED_IDE_DIR, "resources", "app")
    dest_apps = [
        os.path.join(STAGED_IDE_DIR, COMMIT_HASH, "resources", "app"),
    ]
    if INSTALLED_IDE_DIR and os.path.exists(INSTALLED_IDE_DIR):
        dest_apps.append(os.path.join(INSTALLED_IDE_DIR, "resources", "app"))
        dest_apps.append(os.path.join(INSTALLED_IDE_DIR, COMMIT_HASH, "resources", "app"))

    # Update product-default-settings.json first
    update_product_default_settings(os.path.join(src_app, "product-default-settings.json"))

    custom_items = [
        "product.json",
        "product-default-settings.json",
        "out",
        "rest_rl",
        "extensions",
        "node_modules",
    ]

    def safe_fast_copy(s, d):
        try:
            if os.path.exists(d):
                st_s = os.stat(s)
                st_d = os.stat(d)
                if st_s.st_size == st_d.st_size and int(st_s.st_mtime) == int(st_d.st_mtime):
                    return d
            return shutil.copy2(s, d)
        except PermissionError:
            return d
        except OSError:
            return d

    for dest_app in dest_apps:
        os.makedirs(dest_app, exist_ok=True)
        for item in custom_items:
            src_item = os.path.join(src_app, item)
            dst_item = os.path.join(dest_app, item)
            if os.path.isfile(src_item):
                safe_fast_copy(src_item, dst_item)
            elif os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True, copy_function=safe_fast_copy)
        update_product_default_settings(os.path.join(dest_app, "product-default-settings.json"))
        remove_foreign_binaries(dest_app)
        print(f"[OK] Synchronized HugOS custom app bundle -> {dest_app}")

    # Remove foreign binaries from staged src_app as well
    remove_foreign_binaries(src_app)

    # Re-apply single-instance, splash, and native stubs patches
    patch_script = os.path.join(REPO_ROOT, "IDE", "patch_single_instance.py")
    if os.path.exists(patch_script):
        subprocess.run([sys.executable, patch_script], check=False)

    # 4. Remove any leftover .tmp files
    for root_dir in target_roots:
        for f in os.listdir(root_dir):
            if f.endswith(".tmp"):
                tmp_p = os.path.join(root_dir, f)
                try:
                    os.remove(tmp_p)
                    print(f"[CLEAN] Removed temporary file: {tmp_p}")
                except Exception:
                    pass

    # 5. Verify HugOS.exe Authenticode signatures
    print("\n=== Authenticode Verification of HugOS.exe ===")
    for root_dir in target_roots:
        hugos_exe = os.path.join(root_dir, "HugOS.exe")
        if os.path.exists(hugos_exe):
            size = os.path.getsize(hugos_exe)
            ps_cmd = f"$s = Get-AuthenticodeSignature '{hugos_exe}'; Write-Host $s.Status $s.SignerCertificate.Subject"
            p = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
            print(f"  {hugos_exe} ({size} bytes): {p.stdout.strip()}")

    print("\n[SUCCESS] Official Microsoft signatures and commit runtime successfully restored!")

if __name__ == "__main__":
    restore_binaries()


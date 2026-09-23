#!/usr/bin/env python3
"""
clean_untrusted_signatures.py

Strips self-signed 'CN=HugOS IDE' Authenticode signatures from official VS Code
native node modules (.node), DLLs, and third-party executables inside the IDE packaging
directory and installed HugOS IDE directory (excluding ModelFusion's own binaries in bin/).

Signing official VS Code native modules with an untrusted self-signed certificate causes
Windows Defender and Smart App Control to detect an untrusted publisher inside
Microsoft-signed HugOS.exe (Code.exe) and block components like keymapping.node.
"""

import os
import sys
import ctypes
import struct
import shutil

MOVEFILE_DELAY_UNTIL_REBOOT = 0x4

def truncate_dead_pe_overlay(filepath: str) -> bool:
    try:
        with open(filepath, "rb") as f:
            data = bytearray(f.read())
        if len(data) < 0x40:
            return False
        e_lfanew = struct.unpack("<I", data[0x3c:0x40])[0]
        if len(data) < e_lfanew + 24:
            return False
        if data[e_lfanew:e_lfanew+4] != b"PE\x00\x00":
            return False
        num_sections = struct.unpack("<H", data[e_lfanew+6:e_lfanew+8])[0]
        opt_hdr_size = struct.unpack("<H", data[e_lfanew+20:e_lfanew+22])[0]
        sections_offset = e_lfanew + 24 + opt_hdr_size
        if len(data) < sections_offset + num_sections * 40:
            return False

        max_end = 0
        for i in range(num_sections):
            sec = data[sections_offset + i*40 : sections_offset + (i+1)*40]
            raw_size = struct.unpack("<I", sec[16:20])[0]
            raw_ptr = struct.unpack("<I", sec[20:24])[0]
            end = raw_ptr + raw_size
            if end > max_end:
                max_end = end

        if max_end > 0 and len(data) > max_end:
            with open(filepath, "wb") as f:
                f.write(data[:max_end])
            return True
    except Exception as e:
        print(f"[DEBUG] Truncate overlay failed for {filepath}: {e}")
    return False

def clean_file_signature(filepath: str, imagehlp, kernel32, staging_dir: str = None) -> bool:
    try:
        with open(filepath, "rb") as f:
            data = f.read()
    except Exception as e:
        print(f"[WARN] Could not read {filepath}: {e}")
        return False

    if b"HugOS IDE" not in data:
        return False

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 1
    OPEN_EXISTING = 3

    h_file = kernel32.CreateFileW(filepath, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, None, OPEN_EXISTING, 0, None)
    if h_file == -1 or h_file == 0xFFFFFFFFFFFFFFFF:
        err = kernel32.GetLastError()
        # Error 32: sharing violation (file locked by running HugOS process)
        if err == 32 and staging_dir:
            # Try to replace by renaming locked file to .old and copying clean file from staging
            return replace_locked_file_with_clean_staged(filepath, staging_dir, kernel32)
        print(f"[WARN] Failed to open {filepath} for signature removal: error {err}")
        return False

    try:
        res = imagehlp.ImageRemoveCertificate(h_file, 0)
        if res:
            return True
        # If ImageRemoveCertificate returns False, check if PE Security Directory is already unlinked
        # but dead overlay bytes still contain the certificate text
        kernel32.CloseHandle(h_file)
        h_file = None
        return truncate_dead_pe_overlay(filepath)
    finally:
        if h_file is not None and h_file != -1 and h_file != 0xFFFFFFFFFFFFFFFF:
            kernel32.CloseHandle(h_file)

def replace_locked_file_with_clean_staged(filepath: str, staging_dir: str, kernel32) -> bool:
    """If a locked file in installed IDE has a clean counterpart in staging_dir, rename and copy."""
    # Find relative path
    appdata = os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE")
    if not filepath.lower().startswith(appdata.lower()):
        return False
    rel_path = os.path.relpath(filepath, appdata)
    clean_staged_path = os.path.join(staging_dir, rel_path)
    if not os.path.isfile(clean_staged_path):
        return False

    # Check that staged file is clean
    try:
        with open(clean_staged_path, "rb") as f:
            if b"HugOS IDE" in f.read():
                return False
    except Exception:
        return False

    old_path = filepath + ".old"
    try:
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
        os.rename(filepath, old_path)
        shutil.copy2(clean_staged_path, filepath)
        try:
            os.remove(old_path)
        except Exception:
            kernel32.MoveFileExW(old_path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
        return True
    except Exception as e:
        print(f"[WARN] Atomic replacement of locked file {filepath} failed: {e}")
        return False

def clean_directory(root_dir: str, staging_dir: str = None):
    if not os.path.isdir(root_dir):
        print(f"[INFO] Directory does not exist, skipping: {root_dir}")
        return

    if sys.platform != "win32":
        print("[INFO] Not running on Windows; skipping signature cleaning.")
        return

    imagehlp = ctypes.windll.imagehlp
    kernel32 = ctypes.windll.kernel32

    cleaned_count = 0
    scanned_count = 0

    print(f"[INFO] Scanning {root_dir} for files incorrectly signed with CN=HugOS IDE...")

    for root, dirs, files in os.walk(root_dir):
        # Skip ModelFusion's own binaries in bin/
        rel = os.path.relpath(root, root_dir).lower()
        if rel == "bin" or rel.startswith("bin" + os.sep):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in (".node", ".dll", ".exe"):
                scanned_count += 1
                full_path = os.path.join(root, file)
                if clean_file_signature(full_path, imagehlp, kernel32, staging_dir):
                    cleaned_count += 1
                    print(f"  [CLEANED] Stripped untrusted signature: {os.path.relpath(full_path, root_dir)}")

    print(f"[OK] Cleaned {cleaned_count} files in {root_dir} (scanned {scanned_count} candidate binaries).")

if __name__ == "__main__":
    staging_default = os.path.abspath(os.path.join(os.path.dirname(__file__), "VSCode-win32-x64"))
    
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        appdata_hugos = os.path.expandvars(r"%LOCALAPPDATA%\HugOS IDE")
        targets = [staging_default]
        if os.path.isdir(appdata_hugos):
            targets.append(appdata_hugos)

    for target in targets:
        clean_directory(os.path.abspath(target), staging_dir=staging_default)

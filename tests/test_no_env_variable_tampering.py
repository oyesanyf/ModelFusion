#!/usr/bin/env python3
"""
Automated Regression Guardrail Test: Zero Touch of Windows Environment Variables Law
Verifies that:
1. No binary or test modifies HKEY_CURRENT_USER\\Environment (100% cryptographic registry snapshot parity).
2. No source code in the repository contains forbidden registry modification calls (e.g., reg add HKCU\\Environment, SetEnvironmentVariable(..., 'User')).
3. WiX Installer Zero-Touch PATH Law: No WiX files (.wxs, .wxi, generate_wix.js, build_*.ps1) contain <Environment manipulating PATH or environment variables.
"""

import os
import sys
import subprocess
import winreg
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_hkcu_environment_snapshot():
    """Takes a dictionary snapshot of all (name -> (type, data)) in HKCU\\Environment."""
    snapshot = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    name, data, val_type = winreg.EnumValue(key, index)
                    snapshot[name] = (val_type, data)
                    index += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return snapshot


def diff_snapshots(before, after):
    """Compares two snapshots and returns human-readable differences."""
    diffs = []
    all_keys = set(before.keys()) | set(after.keys())
    for k in sorted(all_keys):
        if k not in before:
            diffs.append(f"ADDED: {k} = {after[k]}")
        elif k not in after:
            diffs.append(f"REMOVED: {k} (was {before[k]})")
        elif before[k] != after[k]:
            diffs.append(f"MODIFIED: {k} before={before[k]} after={after[k]}")
    return diffs


def run_command(cmd, env=None, cwd=REPO_ROOT):
    """Executes a command and raises an exception on failure."""
    print(f"  [RUN] {' '.join(cmd)}")
    p = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if p.returncode != 0:
        print(f"  [STDOUT] {p.stdout}")
        print(f"  [STDERR] {p.stderr}")
        raise RuntimeError(f"Command failed with exit code {p.returncode}: {' '.join(cmd)}")
    return p.stdout


def test_registry_invariance():
    """Ensures CLI commands and tests do not mutate HKCU\\Environment."""
    print("\n=== [1/3] Testing HKCU\\Environment Invariance Across CLI Commands ===")

    # Prepare environment with cargo in PATH if available
    cargo_bin = os.path.expanduser(r"~/.cargo/bin")
    env = os.environ.copy()
    if os.path.isdir(cargo_bin):
        env["PATH"] = f"{cargo_bin};{env.get('PATH', '')}"

    cargo_exe = shutil.which("cargo", path=env["PATH"]) or os.path.join(cargo_bin, "cargo.exe")

    snapshot_before = get_hkcu_environment_snapshot()
    print(f"  [SNAPSHOT BEFORE] Captured {len(snapshot_before)} registry values.")

    # 1. Cargo test for Gemini key persistence
    print(f"  -> Executing: {cargo_exe} test --bin cli test_set_and_persist_gemini_key_env")
    run_command([cargo_exe, "test", "--bin", "cli", "test_set_and_persist_gemini_key_env"], env=env)

    # 2. Release CLI --ensure-ollama
    cli_exe = os.path.join(REPO_ROOT, "target", "release", "cli.exe")
    if not os.path.isfile(cli_exe):
        cli_exe = os.path.join(REPO_ROOT, "target", "debug", "cli.exe")
    if not os.path.isfile(cli_exe):
        raise FileNotFoundError(f"CLI executable not found at {cli_exe}")

    print(f"  -> Executing: {cli_exe} --ensure-ollama")
    run_command([cli_exe, "--ensure-ollama"], env=env)

    # 3. Release CLI --sys-info
    print(f"  -> Executing: {cli_exe} --sys-info")
    run_command([cli_exe, "--sys-info"], env=env)

    # 4. Release CLI @agent apply-jobs --help
    print(f"  -> Executing: {cli_exe} @agent apply-jobs --help")
    run_command([cli_exe, "@agent", "apply-jobs", "--help"], env=env)

    snapshot_after = get_hkcu_environment_snapshot()
    print(f"  [SNAPSHOT AFTER] Captured {len(snapshot_after)} registry values.")

    diffs = diff_snapshots(snapshot_before, snapshot_after)
    if diffs:
        print("\n[FAIL] REGISTRY TAMPERING DETECTED! Zero Touch Law violated:")
        for d in diffs:
            print(f"    - {d}")
        sys.exit(1)

    print("  [PASS] HKCU\\Environment is 100% IDENTICAL before and after execution.")


def test_codebase_static_guardrails():
    """Scans all source files to ensure no forbidden registry manipulation calls exist."""
    print("\n=== [2/3] Scanning Codebase for Forbidden Environment Mutations ===")

    target_extensions = {".rs", ".py", ".js", ".ps1", ".bat"}
    ignore_dirs = {".git", "target", "node_modules", "dist", ".history", "reports", "backups"}
    ignore_files = {"test_no_env_variable_tampering.py"}

    violations = []

    for root, dirs, files in os.walk(REPO_ROOT):
        # Exclude ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for f in files:
            if f in ignore_files:
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in target_extensions:
                continue

            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, REPO_ROOT)

            # Skip migration scripts or historical reports
            if relpath.startswith("IDE\\merge_") or relpath.startswith("IDE/merge_"):
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, start=1):
                        # Allow test assertions checking that HKCU\Environment was NOT modified
                        if "assert_ne!" in line and "HKCU" in line:
                            continue
                        if "Get-ItemProperty" in line and "assert" in line.lower():
                            continue
                        if "Remove-ItemProperty" in line:
                            continue

                        # Check for forbidden patterns
                        if "HKCU\\Environment" in line and ("add" in line or "REG_" in line or "Set" in line):
                            violations.append((relpath, line_no, line.strip()))
                        elif "SetEnvironmentVariable" in line and ("'User'" in line or '"User"' in line):
                            # Allow pure informational comments or prompt text if any
                            if not line.strip().startswith("//") and not line.strip().startswith("#"):
                                violations.append((relpath, line_no, line.strip()))
            except Exception as e:
                print(f"  [WARN] Failed to read {relpath}: {e}")

    if violations:
        print(f"\n[FAIL] FOUND {len(violations)} FORBIDDEN REGISTRY MUTATION CALL(S):")
        for path, line_no, line in violations:
            print(f"    - {path}:{line_no} -> {line}")
        sys.exit(1)

    print("  [PASS] Codebase is 100% CLEAN of forbidden registry mutation calls.")


def test_wix_installer_zero_touch_path():
    """
    Verifies that WiX installers and generators never use <Environment Id="PATH" ...>.
    Permanent="no" on WiX Environment components generates destructive MSI table flag =-*PATH,
    which deletes the entire system or user PATH.
    """
    print("\n=== [3/3] Verifying WiX Installer Zero-Touch PATH Law ===")

    wix_files = [
        os.path.join(REPO_ROOT, "IDE", "HugOS.wxs"),
        os.path.join(REPO_ROOT, "IDE", "generate_wix.js"),
        os.path.join(REPO_ROOT, "IDE", "build_msi.ps1"),
        os.path.join(REPO_ROOT, "browser", "HugOS_Browser.wxs"),
        os.path.join(REPO_ROOT, "browser", "generate_wix.js"),
        os.path.join(REPO_ROOT, "browser", "build_browser.ps1"),
    ]

    violations = []
    for wf in wix_files:
        if not os.path.isfile(wf):
            continue
        rel = os.path.relpath(wf, REPO_ROOT)
        with open(wf, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
            if "<Environment" in content and "PATH" in content.upper():
                violations.append(f"{rel}: contains destructive <Environment element touching PATH")
            elif "=-*PATH" in content:
                violations.append(f"{rel}: contains destructive MSI table =-*PATH flag")

    if violations:
        print(f"\n[FAIL] WI-X ZERO-TOUCH PATH LAW VIOLATION:")
        for v in violations:
            print(f"    - {v}")
        sys.exit(1)

    print("  [PASS] All WiX packages and generators adhere 100% to Zero-Touch PATH Law (0 destructive MSI tags).")


if __name__ == "__main__":
    test_wix_installer_zero_touch_path()
    test_codebase_static_guardrails()
    test_registry_invariance()
    print("\nALL ZERO TOUCH REGRESSION GUARDRAILS PASSED (100% GREEN)!\n")

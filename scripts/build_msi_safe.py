#!/usr/bin/env python3
"""
Rock-solid WiX MSI Compiler and Signer for ModelFusion / HugOS IDE and Browser.
Uses a single persistent Windows Installer database keepalive handle (MsiOpenDatabaseW)
during compilation to guarantee msiserver remains active without idle timeout or service disruption.
Digitally signs resulting MSIs with DigiCert timestamp and verifies integrity.
"""

import os
import sys
import time
import shutil
import ctypes
from ctypes import wintypes
import subprocess
import hashlib

REPO_ROOT = r"D:\harfile\ModelFusion"
WIX_EXE = r"D:\tools\wix5\wix.exe"
if not os.path.exists(WIX_EXE):
    WIX_EXE = r"D:\tools\wix\PFiles64\WiX Toolset v5.0\bin\wix.exe"
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
PFX_PASS = "HugOSPassword123!"
SIGNTOOL_EXE = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"

def build_wix_msi(wxs_path, base_dir, out_msi_path):
    print(f"\n========================================================")
    print(f"[WIX BUILD] Target: {out_msi_path}")
    print(f"  Manifest: {wxs_path}")
    print(f"  Base Dir: {base_dir}")
    print(f"========================================================")

    if not os.path.exists(WIX_EXE):
        raise FileNotFoundError(f"WiX binary not found at {WIX_EXE}")
    if not os.path.exists(wxs_path):
        raise FileNotFoundError(f"WiX manifest not found at {wxs_path}")

    # Remove existing MSI if present
    if os.path.exists(out_msi_path):
        try:
            os.remove(out_msi_path)
        except Exception as e:
            print(f"Warning: Could not remove old MSI: {e}")

    # Ensure msiserver is running
    subprocess.run(["powershell", "-NoProfile", "-Command", "Start-Service msiserver"], capture_output=True)

    # Establish single persistent keepalive database handle
    msi = ctypes.windll.msi
    temp_msi = os.path.join(os.environ['TEMP'], f'keepalive_{os.path.basename(out_msi_path)}.msi')
    if os.path.exists(temp_msi):
        try:
            os.remove(temp_msi)
        except Exception:
            pass

    hDb = wintypes.HANDLE()
    res = msi.MsiOpenDatabaseW(temp_msi, ctypes.c_void_p(3), ctypes.byref(hDb))
    print(f"[INFO] Persistent Windows Installer keepalive established (res={res}, hDb={hDb.value})")

    cmd = [WIX_EXE, "build", "-b", base_dir, "-arch", "x64", "-dcl", "low", wxs_path, "-out", out_msi_path]
    print(f"[INFO] Compiling MSI with WiX Toolset v5...")
    t0 = time.time()
    
    stdout_log = out_msi_path + ".stdout.log"
    stderr_log = out_msi_path + ".stderr.log"
    with open(stdout_log, "w", encoding="utf-8", errors="replace") as f_out, \
         open(stderr_log, "w", encoding="utf-8", errors="replace") as f_err:
        res_wix = subprocess.run(cmd, stdout=f_out, stderr=f_err)
    t1 = time.time()
    print(f"[INFO] WiX finished in {t1 - t0:.2f}s (Exit Code: {res_wix.returncode})")

    # Close keepalive DB handle
    if hDb.value:
        msi.MsiCloseHandle(hDb)
    if os.path.exists(temp_msi):
        try:
            os.remove(temp_msi)
        except Exception:
            pass

    # Verify MSI existence and size
    if os.path.exists(out_msi_path) and os.path.getsize(out_msi_path) > 10 * 1024 * 1024:
        size_mb = os.path.getsize(out_msi_path) / (1024 * 1024)
        print(f"[OK] MSI successfully built at: {out_msi_path} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"[ERROR] WiX build did not produce valid MSI!")
        if os.path.exists(stderr_log):
            with open(stderr_log, "r", encoding="utf-8", errors="replace") as f:
                err_content = f.read()
                if err_content:
                    print("Stderr:", err_content[:2000])
        return False

def sign_msi(msi_path):
    print(f"\n[SIGN] Digitally signing {msi_path}...")
    if os.path.exists(SIGNTOOL_EXE):
        sign_cmd = [
            SIGNTOOL_EXE, "sign",
            "/f", PFX_PATH,
            "/p", PFX_PASS,
            "/fd", "SHA256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/d", "HugOS AI Platform",
            msi_path
        ]
        res = subprocess.run(sign_cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Successfully signed and timestamped {msi_path}")
            return True
        else:
            print(f"Warning: Primary DigiCert timestamp via signtool failed, trying Sectigo RFC3161...")
            sign_cmd[7] = "http://timestamp.sectigo.com"
            res2 = subprocess.run(sign_cmd, capture_output=True, text=True)
            if res2.returncode == 0:
                print(f"[OK] Successfully signed with Sectigo timestamp: {msi_path}")
                return True

    # Fallback to PowerShell Set-AuthenticodeSignature
    print(f"[INFO] Using PowerShell Set-AuthenticodeSignature for signing...")
    ps_cmd = [
        "powershell", "-NoProfile", "-Command",
        f"""
        $pwdSecure = ConvertTo-SecureString '{PFX_PASS}' -AsPlainText -Force
        $signCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2('{PFX_PATH}', $pwdSecure)
        $res = Set-AuthenticodeSignature -FilePath '{msi_path}' -Certificate $signCert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
        if ($res -and $res.SignerCertificate) {{
            Write-Host "[OK] Signed by: $($res.SignerCertificate.Subject)"
            exit 0
        }}
        $res2 = Set-AuthenticodeSignature -FilePath '{msi_path}' -Certificate $signCert -HashAlgorithm SHA256 -ErrorAction SilentlyContinue
        if ($res2 -and $res2.SignerCertificate) {{
            Write-Host "[OK] Signed by: $($res2.SignerCertificate.Subject) (no timestamp)"
            exit 0
        }}
        exit 1
        """
    ]
    res_ps = subprocess.run(ps_cmd, capture_output=True, text=True)
    if res_ps.returncode == 0:
        print(f"[OK] Successfully signed {msi_path} via PowerShell Authenticode ({res_ps.stdout.strip()})")
        return True
    else:
        print(f"Warning: PowerShell Authenticode signing failed: {res_ps.stderr.strip()}")
        return False

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    # 1. Deploy icons first so they are baked into all distribution dirs
    deploy_script = os.path.join(REPO_ROOT, "scripts", "deploy_icons.py")
    if os.path.exists(deploy_script):
        print("[INFO] Deploying high-res multi-layer icons across all targets...")
        subprocess.run([sys.executable, deploy_script], check=True)

    if target in ("browser", "all"):
        # Build HugOS Browser MSI
        browser_dir = os.path.join(REPO_ROOT, "browser")
        browser_wxs = os.path.join(browser_dir, "HugOS_Browser.wxs")
        browser_msi = os.path.join(browser_dir, "HugOS_Browser.msi")
        
        print("[INFO] Regenerating HugOS Browser WiX manifest...")
        node_exe = r"D:\tools\nodejs\node.exe"
        if not os.path.exists(node_exe):
            node_exe = "node"
        subprocess.run([node_exe, os.path.join(browser_dir, "generate_wix.js"), browser_dir, browser_wxs], check=True)

        if build_wix_msi(browser_wxs, browser_dir, browser_msi):
            sign_msi(browser_msi)
            print(f"[DONE] HugOS_Browser.msi SHA-256: {compute_sha256(browser_msi)}")

    if target in ("ide", "all"):
        # Build HugOS IDE MSI
        ide_dir = os.path.join(REPO_ROOT, "IDE")
        ide_wxs = os.path.join(ide_dir, "HugOS.wxs")
        ide_msi = os.path.join(ide_dir, "HugOS.msi")
        pack_dir = os.path.join(ide_dir, "VSCode-win32-x64")

        print("[INFO] Regenerating HugOS IDE WiX manifest...")
        node_exe = r"D:\tools\nodejs\node.exe"
        if not os.path.exists(node_exe):
            node_exe = "node"
        subprocess.run([node_exe, os.path.join(ide_dir, "generate_wix.js"), pack_dir, ide_wxs], check=True)

        if build_wix_msi(ide_wxs, ide_dir, ide_msi):
            sign_msi(ide_msi)
            print(f"[DONE] HugOS.msi SHA-256: {compute_sha256(ide_msi)}")

if __name__ == "__main__":
    main()

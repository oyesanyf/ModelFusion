#!/usr/bin/env python3
"""
Ensures the HugOS Code Signing Certificate is imported into the Windows
CurrentUser Root and TrustedPublisher stores so that Windows Installer and
Windows Defender / UAC recognize the certificate chain as fully VALID and TRUSTED.
"""

import os
import sys
import subprocess

REPO_ROOT = r"D:\harfile\ModelFusion"
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
PFX_PASS = "HugOSPassword123!"

def ensure_cert_trusted():
    if not os.path.exists(PFX_PATH):
        print(f"[ERROR] PFX file not found at: {PFX_PATH}")
        return False

    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    $pfxPath = '{PFX_PATH}'
    $password = '{PFX_PASS}'
    $securePwd = ConvertTo-SecureString $password -AsPlainText -Force
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $securePwd, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
    $thumb = $cert.Thumbprint
    Write-Host "[INFO] Processing Certificate: $($cert.Subject) (Thumbprint: $thumb)"

    # 1. Add to CurrentUser Root
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::Root, [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
    $rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $existingRoot = $rootStore.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint, $thumb, $false)
    if ($existingRoot.Count -eq 0) {{
        $rootStore.Add($cert)
        Write-Host "[OK] Added certificate to Cert:\\CurrentUser\\Root"
    }} else {{
        Write-Host "[OK] Certificate already present in Cert:\\CurrentUser\\Root"
    }}
    $rootStore.Close()

    # 2. Add to CurrentUser TrustedPublisher
    $pubStore = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::TrustedPublisher, [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
    $pubStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $existingPub = $pubStore.Certificates.Find([System.Security.Cryptography.X509Certificates.X509FindType]::FindByThumbprint, $thumb, $false)
    if ($existingPub.Count -eq 0) {{
        $pubStore.Add($cert)
        Write-Host "[OK] Added certificate to Cert:\\CurrentUser\\TrustedPublisher"
    }} else {{
        Write-Host "[OK] Certificate already present in Cert:\\CurrentUser\\TrustedPublisher"
    }}
    $pubStore.Close()

    # 3. Best-effort LocalMachine stores (if running with elevated privileges)
    try {{
        $lmRoot = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::Root, [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
        $lmRoot.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $lmRoot.Add($cert)
        $lmRoot.Close()
        Write-Host "[OK] Added certificate to Cert:\\LocalMachine\\Root"
    }} catch {{
        Write-Host "[INFO] LocalMachine\\Root (requires Administrator, skipped or already set)"
    }}

    try {{
        $lmPub = New-Object System.Security.Cryptography.X509Certificates.X509Store([System.Security.Cryptography.X509Certificates.StoreName]::TrustedPublisher, [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine)
        $lmPub.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
        $lmPub.Add($cert)
        $lmPub.Close()
        Write-Host "[OK] Added certificate to Cert:\\LocalMachine\\TrustedPublisher"
    }} catch {{
        Write-Host "[INFO] LocalMachine\\TrustedPublisher (requires Administrator, skipped or already set)"
    }}
    """

    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"[ERROR] Failed to ensure certificate trust: {res.stderr}")
        return False
    return True

if __name__ == "__main__":
    success = ensure_cert_trusted()
    sys.exit(0 if success else 1)

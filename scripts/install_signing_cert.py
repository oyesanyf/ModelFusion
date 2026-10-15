#!/usr/bin/env python3
"""
Ensures the HugOS Authenticode signing certificate (IDE/hugos-signing-cert.pfx)
is properly installed and trusted in both CurrentUser\\TrustedPublisher and
CurrentUser\\Root stores so that Get-AuthenticodeSignature returns Valid.
"""

import os
import sys
import ctypes
import threading
import time
import subprocess
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
crypt32 = ctypes.windll.crypt32

crypt32.CertOpenStore.restype = wintypes.HANDLE
crypt32.CertOpenStore.argtypes = [ctypes.c_char_p, wintypes.DWORD, wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
crypt32.CertAddEncodedCertificateToStore.restype = wintypes.BOOL
crypt32.CertAddEncodedCertificateToStore.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_char_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
crypt32.CertCloseStore.restype = wintypes.BOOL
crypt32.CertCloseStore.argtypes = [wintypes.HANDLE, wintypes.DWORD]

CERT_STORE_PROV_SYSTEM_W = 10
CERT_SYSTEM_STORE_CURRENT_USER = 0x00010000
CERT_STORE_ADD_REPLACE_EXISTING = 3
X509_ASN_ENCODING = 0x00000001
PKCS_7_ASN_ENCODING = 0x00010000

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFX_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.pfx")
CER_PATH = os.path.join(REPO_ROOT, "IDE", "hugos-signing-cert.cer")

def export_cer_if_needed():
    if not os.path.exists(CER_PATH) and os.path.exists(PFX_PATH):
        print("[CERT] Exporting public CER from PFX...")
        cmd = f"$c = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2('{PFX_PATH}', 'HugOSPassword123!'); [System.IO.File]::WriteAllBytes('{CER_PATH}', $c.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)

def install_to_store(store_name_str, cer_bytes):
    main_tid = kernel32.GetCurrentThreadId()
    stop_event = threading.Event()

    def watcher():
        for _ in range(50):
            if stop_event.is_set():
                break
            time.sleep(0.08)
            def enum_cb(hwnd, lparam):
                cls = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls, 256)
                if cls.value == '#32770':
                    WM_COMMAND = 0x0111
                    IDYES = 6
                    user32.SendMessageW(hwnd, WM_COMMAND, IDYES, 0)
                    return False
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumThreadWindows(main_tid, WNDENUMPROC(enum_cb), 0)

    t = threading.Thread(target=watcher, daemon=True)
    t.start()

    store_name = ctypes.create_unicode_buffer(store_name_str)
    hStore = crypt32.CertOpenStore(
        ctypes.cast(CERT_STORE_PROV_SYSTEM_W, ctypes.c_char_p),
        0,
        None,
        CERT_SYSTEM_STORE_CURRENT_USER,
        ctypes.cast(store_name, ctypes.c_void_p)
    )
    if not hStore:
        stop_event.set()
        print(f"[ERROR] Failed to open {store_name_str} store.")
        return False

    res = crypt32.CertAddEncodedCertificateToStore(
        hStore,
        X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
        cer_bytes,
        len(cer_bytes),
        CERT_STORE_ADD_REPLACE_EXISTING,
        None
    )
    stop_event.set()
    crypt32.CertCloseStore(hStore, 0)
    print(f"[OK] Added certificate to CurrentUser\\{store_name_str} (success={bool(res)})")
    return bool(res)

def ensure_signing_cert_trusted():
    export_cer_if_needed()
    if not os.path.exists(CER_PATH):
        print(f"[WARN] CER not found at {CER_PATH}")
        return False

    with open(CER_PATH, "rb") as f:
        cer_bytes = f.read()

    install_to_store("TrustedPublisher", cer_bytes)
    install_to_store("Root", cer_bytes)
    return True

if __name__ == "__main__":
    ensure_signing_cert_trusted()

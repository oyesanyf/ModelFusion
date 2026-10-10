import os
import hashlib
import sys

localappdata = os.environ.get("LOCALAPPDATA", r"C:\Users\oyesanyf\AppData\Local")

LOCATIONS = [
    (1, os.path.abspath(r"target\release\cli.exe"), "Authoritative master CLI build target"),
    (2, os.path.abspath(r"browser\bin\clibrowser.exe"), "Authoritative dedicated binary for HugOS Browser"),
    (3, os.path.abspath(r"target\release\clibrowser.exe"), "Browser release staging binary"),
    (4, os.path.join(localappdata, r"HugOS Browser\bin\clibrowser.exe"), "Locally installed production browser binary"),
    (5, os.path.abspath(r"browser\dist\win-unpacked\resources\bin\clibrowser.exe"), "Unpacked browser distribution binary"),
    (6, os.path.abspath(r"browser\bin\cli.exe"), "Browser staging fallback binary"),
    (7, os.path.join(localappdata, r"HugOS Browser\bin\cli.exe"), "Browser installed fallback binary"),
    (8, os.path.abspath(r"IDE\bin\cliide.exe"), "Authoritative dedicated binary for HugOS IDE"),
    (9, os.path.abspath(r"IDE\VSCode-win32-x64\bin\cliide.exe"), "Packaged IDE distribution binary"),
    (10, os.path.join(localappdata, r"HugOS IDE\bin\cliide.exe"), "Locally installed production IDE binary"),
    (11, os.path.abspath(r"IDE\bin\cli.exe"), "IDE packaging staging fallback binary"),
    (12, os.path.join(localappdata, r"HugOS IDE\bin\cli.exe"), "IDE installed fallback binary"),
    (13, os.path.abspath(r"target\release\climcp.exe"), "Authoritative dedicated binary for HugOS MCP Server"),
    (14, os.path.abspath(r"mcp\bin\climcp.exe"), "MCP staging dedicated binary"),
    (15, os.path.abspath(r"mcp\bin\cli.exe"), "MCP staging fallback binary"),
    (16, os.path.join(localappdata, r"HugOS MCP\bin\climcp.exe"), "Locally installed production MCP binary"),
    (17, os.path.join(localappdata, r"HugOS MCP\bin\cli.exe"), "MCP installed fallback binary"),
    (18, os.path.join(localappdata, r"Programs\ModelFusion\cli.exe"), "Root application distribution binary"),
]

def get_sha256(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    master_path = LOCATIONS[0][1]
    master_hash = get_sha256(master_path)
    if not master_hash:
        print(f"ERROR: Master binary missing at {master_path}")
        sys.exit(1)

    print(f"==================================================================")
    print(f"Authoritative Master Hash: {master_hash}")
    print(f"==================================================================")

    all_matched = True
    for idx, path, desc in LOCATIONS:
        h = get_sha256(path)
        matched = (h == master_hash)
        if not matched:
            all_matched = False
        status = "MATCH" if matched else "FAIL "
        short_hash = h[:12] if h else "MISSING     "
        print(f"[{idx:2d}/18] [{status}] {short_hash} | {desc} -> {path}")

    print(f"==================================================================")
    if all_matched:
        print("SUCCESS: 100% Cryptographic Parity Confirmed Across All 18 Locations!")
        sys.exit(0)
    else:
        print("FAILURE: Parity mismatch detected!")
        sys.exit(1)

if __name__ == "__main__":
    main()

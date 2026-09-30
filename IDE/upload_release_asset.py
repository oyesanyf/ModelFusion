#!/usr/bin/env python3
"""
Uploads HugOS.msi and cli.exe to GitHub Releases:
1. Versioned tag: v1.0.0-beta.{build_number}
2. Rolling release tag: v1.0.0-beta (clobbers existing assets)
Uses the GitHub REST API with the token stored in Git Credential Manager.
"""
import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import hashlib

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

REPO = "oyesanyf/ModelFusion"
API_URL = f"https://api.github.com/repos/{REPO}"
UPLOADS_URL = f"https://uploads.github.com/repos/{REPO}"

def get_token():
    # Try environment variable
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    # Try git credential helper
    try:
        p = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            check=True
        )
        for line in p.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed to obtain token from git credential manager: {e}")
    return None

def api_request(url, method="GET", data=None, headers=None, token=None):
    req_headers = {
        "User-Agent": "ModelFusion-Release-Pipeline",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    if headers:
        req_headers.update(headers)
    
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        elif isinstance(data, bytes):
            body = data
        else:
            body = str(data).encode("utf-8")
            
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            if content:
                return json.loads(content.decode("utf-8"))
            return None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[HTTP {e.code}] {url}: {err_body}")
        raise

def get_or_create_release(tag_name, release_name, token, make_latest=False):
    desc = (
        f"# 🚀 ModelFusion & HugOS Suite ({tag_name})\n\n"
        f"Official Release for the Three Pillars: **Master CLI**, **HugOS IDE**, and **HugOS Browser**.\n\n"
        "### 📦 Release Artifacts:\n"
        "1. **`cli.exe`** (ModelFusion Master CLI - 100% Self-Contained Static CRT)\n"
        "2. **`HugOS_Browser.msi`** (HugOS Browser - Digitally Signed Installer)\n"
        "3. **`HugOS.msi`** (HugOS IDE - Digitally Signed Installer)\n"
    )
    try:
        rel = api_request(f"{API_URL}/releases/tags/{tag_name}", token=token)
        print(f"[INFO] Found existing release for tag: {tag_name} (ID: {rel['id']})")
        # Update metadata to ensure title, body, and latest flags are refreshed
        patch_data = {
            "name": release_name,
            "body": desc,
            "prerelease": False,
        }
        if make_latest:
            patch_data["make_latest"] = "true"
        rel = api_request(f"{API_URL}/releases/{rel['id']}", method="PATCH", data=patch_data, token=token)
        return rel
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[INFO] Release for tag {tag_name} not found. Creating it...")
            data = {
                "tag_name": tag_name,
                "name": release_name,
                "body": desc,
                "draft": False,
                "prerelease": False
            }
            if make_latest:
                data["make_latest"] = "true"
            return api_request(f"{API_URL}/releases", method="POST", data=data, token=token)
        raise

def delete_existing_asset(release_id, asset_name, token):
    rel = api_request(f"{API_URL}/releases/{release_id}", token=token)
    for asset in rel.get("assets", []):
        if asset["name"] == asset_name:
            print(f"[INFO] Deleting existing asset {asset_name} (ID: {asset['id']}) from release {release_id}...")
            api_request(f"{API_URL}/releases/assets/{asset['id']}", method="DELETE", token=token)
            print(f"[OK] Deleted old asset: {asset_name}")
            import time
            time.sleep(2)

def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024 * 4)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def upload_asset(release_id, file_path, asset_name, token, force=False):
    file_size = os.path.getsize(file_path)
    file_sha256 = compute_sha256(file_path)
    size_mb = round(file_size / (1024 * 1024), 2)
    if not force:
        rel = api_request(f"{API_URL}/releases/{release_id}", token=token)
        for asset in rel.get("assets", []):
            if asset["name"] == asset_name:
                if asset.get("size") == file_size:
                    print(f"[OK] Asset {asset_name} already exists on release {release_id} with matching size ({file_size} bytes). Skipping.")
                    return asset
                else:
                    print(f"[INFO] Asset {asset_name} exists but size differs ({asset.get('size')} != {file_size}). Replacing...")
                    break

    delete_existing_asset(release_id, asset_name, token)
    print(f"[INFO] Uploading {asset_name} ({size_mb} MB, SHA256: {file_sha256}) to release {release_id}...")

    upload_url = f"{UPLOADS_URL}/releases/{release_id}/assets?name={asset_name}"

    for attempt in range(1, 4):
        cmd = [
            "curl.exe",
            "-sS",
            "-X", "POST",
            "-H", f"Authorization: Bearer {token}",
            "-H", "User-Agent: ModelFusion-Release-Pipeline",
            "-H", "Content-Type: application/octet-stream",
            "--data-binary", f"@{file_path}",
            upload_url
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            try:
                res = json.loads(p.stdout)
                uploaded_size = res.get("size")
                if uploaded_size == file_size:
                    print(f"[OK] Uploaded {asset_name} ({uploaded_size} bytes): {res.get('browser_download_url')}")
                    return res
                elif "already_exists" in p.stdout:
                    print(f"[WARN] Asset {asset_name} already exists on remote. Re-deleting and retrying...")
                    delete_existing_asset(release_id, asset_name, token)
                    import time
                    time.sleep(3)
                else:
                    print(f"[WARN] Size mismatch (attempt {attempt}): {uploaded_size} != {file_size}. Response: {p.stdout[:200]}")
            except Exception as parse_err:
                print(f"[WARN] curl response parsing failed: {parse_err}. Response: {p.stdout[:200]}")
        else:
            print(f"[WARN] curl failed with code {p.returncode}: {p.stderr[:200]}")
        import time
        time.sleep(2)
    raise RuntimeError(f"[ERROR] Failed to upload {asset_name} after 3 attempts.")

def main():
    token = get_token()
    if not token:
        print("[ERROR] No GitHub token found. Please ensure Git Credential Manager has github.com credentials or set GH_TOKEN.")
        sys.exit(1)
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_num_path = os.path.join(script_dir, "build_number.txt")
    if not os.path.isfile(build_num_path):
        print(f"[ERROR] build_number.txt not found at {build_num_path}")
        sys.exit(1)
        
    with open(build_num_path, "r", encoding="utf-8") as f:
        build_number = f.read().strip()
        
    msi_path = os.path.join(script_dir, "HugOS.msi")
    cli_path = os.path.join(os.path.dirname(script_dir), "target", "release", "cli.exe")
    browser_msi_path = os.path.join(os.path.dirname(script_dir), "browser", "HugOS_Browser.msi")
    if not os.path.isfile(msi_path):
        fallback_msi = os.path.join(script_dir, "HugOS-Setup-x64.msi")
        if os.path.isfile(fallback_msi):
            msi_path = fallback_msi
        else:
            print(f"[ERROR] MSI not found at: {msi_path} or {fallback_msi}")
            sys.exit(1)
    if not os.path.isfile(cli_path):
        print(f"[ERROR] CLI not found at: {cli_path}")
        sys.exit(1)
    if not os.path.isfile(browser_msi_path):
        print(f"[ERROR] Browser MSI not found at: {browser_msi_path}")
        sys.exit(1)

    artifacts = [
        (cli_path, "cli.exe"),
        (msi_path, "HugOS.msi"),
        (browser_msi_path, "HugOS_Browser.msi"),
    ]

    print("==========================================")
    print(f"Local Release Artifacts (Build {build_number}):")
    for fpath, fname in artifacts:
        print(f"  {fname}: {fpath} ({os.path.getsize(fpath)} bytes, SHA256: {compute_sha256(fpath)})")
    print("==========================================")
        
    targets = [
        (f"v1.0.0-beta.{build_number}", f"ModelFusion & HugOS Suite v1.0.0-beta.{build_number} (Build {build_number} - CLI, IDE, Browser)", True),
        ("v1.0.0-beta", f"ModelFusion & HugOS Suite v1.0.0-beta (Latest Rolling Release - Build {build_number})", False)
    ]

    if "--check" in sys.argv or "--verify-only" in sys.argv:
        print("\n[INFO] Running in check/verify mode — inspecting remote assets...")
        all_match = True
        for tag_name, release_name, _ in targets:
            print(f"\nVerifying remote assets for {tag_name}...")
            try:
                rel = api_request(f"{API_URL}/releases/tags/{tag_name}", token=token)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"  [FAIL] Release tag {tag_name} does not exist on remote!")
                    all_match = False
                    continue
                raise
            assets_by_name = {a["name"]: a for a in rel.get("assets", [])}
            for local_f, name in artifacts:
                local_sz = os.path.getsize(local_f)
                if name not in assets_by_name:
                    print(f"  [FAIL] {name} NOT FOUND on {tag_name}")
                    all_match = False
                else:
                    remote_sz = assets_by_name[name]["size"]
                    if remote_sz == local_sz:
                        print(f"  [PASS] {name} on {tag_name}: size {remote_sz} matches local")
                    else:
                        print(f"  [FAIL] {name} on {tag_name}: remote size {remote_sz} != local {local_sz}")
                        all_match = False
        if all_match:
            print("\n[SUCCESS] All remote release assets match local artifacts perfectly!")
            sys.exit(0)
        else:
            print("\n[ERROR] Remote release assets do not match local artifacts.")
            sys.exit(1)
    
    force = "--force" in sys.argv
    for tag_name, release_name, make_latest in targets:
        print(f"\n==========================================")
        print(f"Target Release: {tag_name} - {release_name}")
        print(f"==========================================")
        rel = get_or_create_release(tag_name, release_name, token, make_latest=make_latest)
        rel_id = rel["id"]
        for local_f, name in artifacts:
            upload_asset(rel_id, local_f, name, token, force=force)
        
    print("\n[SUCCESS] All release assets uploaded and verified successfully on GitHub Releases!")

if __name__ == "__main__":
    main()

import urllib.request
import json
import os
import subprocess

def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
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
    return None

token = get_token()
repo = "oyesanyf/ModelFusion"
tag = "v1.0.0-beta"

# Get release ID for v1.0.0-beta
req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ModelFusion"
    }
)
with urllib.request.urlopen(req) as resp:
    rel = json.loads(resp.read().decode())
    rel_id = rel["id"]
    print(f"Found release {tag} ID: {rel_id}")

# Delete existing HugOS_Browser.msi if present
for asset in rel.get("assets", []):
    if asset["name"] == "HugOS_Browser.msi":
        aid = asset["id"]
        del_req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/assets/{aid}",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "ModelFusion"},
            method="DELETE"
        )
        urllib.request.urlopen(del_req)
        print("Deleted old HugOS_Browser.msi")

# Upload browser/HugOS_Browser.msi
file_path = r"d:\harfile\ModelFusion\browser\HugOS_Browser.msi"
file_size = os.path.getsize(file_path)
print(f"Uploading HugOS_Browser.msi ({file_size} bytes)...")
upload_url = f"https://uploads.github.com/repos/{repo}/releases/{rel_id}/assets?name=HugOS_Browser.msi"
req_headers = {
    "User-Agent": "ModelFusion",
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/octet-stream",
    "Content-Length": str(file_size)
}
with open(file_path, "rb") as f:
    up_req = urllib.request.Request(upload_url, data=f, headers=req_headers, method="POST")
    with urllib.request.urlopen(up_req) as resp:
        res = json.loads(resp.read().decode())
        print(f"Uploaded successfully: {res.get('browser_download_url')}")

import urllib.request
import json
import os

import subprocess

def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
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
        print(f"Failed to obtain token: {e}")
    return None

token = get_token()


headers = {'User-Agent': 'ModelFusion-Release-Agent', 'Accept': 'application/vnd.github.v3+json'}
if token:
    headers['Authorization'] = f'token {token}'

# Test delete one old release: ID 356233690 (v1.0.0-beta.52)
url = 'https://api.github.com/repos/oyesanyf/ModelFusion/releases/356233690'
req = urllib.request.Request(url, headers=headers, method='DELETE')
try:
    with urllib.request.urlopen(req) as resp:
        print("Delete status code:", resp.status)
except Exception as e:
    print("Delete error:", e)

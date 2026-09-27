import urllib.request
import json
import subprocess

def get_token():
    p = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n', capture_output=True, text=True, check=True)
    for line in p.stdout.splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1].strip()
    return None

token = get_token()
repo = 'oyesanyf/ModelFusion'

for tag in ['v1.0.0-beta.180', 'v1.0.0-beta']:
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/releases/tags/{tag}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'ModelFusion'}
    )
    with urllib.request.urlopen(req) as resp:
        rel = json.loads(resp.read().decode())
        name = rel.get('name')
        print(f"\n=== Release: {tag} ({name}) ===")
        for a in rel.get('assets', []):
            aname = a['name']
            asize = a['size']
            url = a['browser_download_url']
            print(f"  {aname}: {asize} bytes | {url}")

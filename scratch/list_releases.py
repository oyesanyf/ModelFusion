import urllib.request
import json
import os

token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
if not token:
    # check git credential or token in file
    for p in [r'C:\Users\oyesanyf\.git-credentials', r'IDE\gh_token.txt']:
        if os.path.exists(p):
            with open(p, 'r') as f:
                content = f.read()
                if 'ghp_' in content:
                    for part in content.split():
                        if 'ghp_' in part:
                            token = part.split('@')[-1].split(':')[-1]
                            break

headers = {'User-Agent': 'ModelFusion-Release-Agent', 'Accept': 'application/vnd.github.v3+json'}
if token:
    headers['Authorization'] = f'token {token}'

page = 1
all_releases = []
while True:
    url = f'https://api.github.com/repos/oyesanyf/ModelFusion/releases?per_page=100&page={page}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if not data:
                break
            all_releases.extend(data)
            page += 1
    except Exception as e:
        print("Error fetching releases:", e)
        break

print(f"Total releases found: {len(all_releases)}")
for r in all_releases:
    print(f"ID: {r['id']} | Tag: {r['tag_name']} | Name: {r.get('name')} | Draft: {r.get('draft')} | Prerelease: {r.get('prerelease')}")

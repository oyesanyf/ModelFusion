import subprocess, os, json, urllib.request, urllib.error

p = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n', capture_output=True, text=True, check=True)
token = None
for line in p.stdout.splitlines():
    if line.startswith('password='):
        token = line.split('=', 1)[1].strip()
        break

if not token:
    print('No token found')
    exit(1)

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'ModelFusion-Pipeline'
}

# 1. Create PR
url = 'https://api.github.com/repos/oyesanyf/ModelFusion/pulls'
data = json.dumps({
    'title': 'feat(image/sources): multimodal image routing, 200 sources slider, and Build 223 MSI',
    'body': 'Adds multimodal image synthesis directive routing, prevents image queries from routing to web search, expands verified sources slider up to 200, optimizes default context window sizing, and packages Build 223 signed MSI.',
    'head': 'sync-build-223',
    'base': 'main'
}).encode('utf-8')

pr_number = None
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        pr_number = res['number']
        print(f"PR #{pr_number} created successfully: {res['html_url']}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"HTTP error {e.code}: {err_body}")
    req_list = urllib.request.Request(url + '?head=oyesanyf:sync-build-223', headers=headers)
    with urllib.request.urlopen(req_list) as resp_list:
        res_list = json.loads(resp_list.read().decode('utf-8'))
        if res_list:
            pr_number = res_list[0]['number']
            print(f"Found existing PR #{pr_number}")
        else:
            exit(1)

# 2. Merge PR (Squash merge)
merge_url = f'https://api.github.com/repos/oyesanyf/ModelFusion/pulls/{pr_number}/merge'
merge_data = json.dumps({
    'commit_title': 'feat(image/sources): multimodal image routing, 200 sources slider, and Build 223 MSI (#223)',
    'merge_method': 'squash'
}).encode('utf-8')

merge_req = urllib.request.Request(merge_url, data=merge_data, headers=headers, method='PUT')
try:
    with urllib.request.urlopen(merge_req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f"PR #{pr_number} merged successfully: {res.get('message', 'merged')}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8')
    print(f"Merge error {e.code}: {err_body}")

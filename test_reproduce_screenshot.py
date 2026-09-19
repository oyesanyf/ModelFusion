import subprocess
import urllib.request
import json
import time
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CLI_PATH = r"D:\harfile\ModelFusion\target\release\cli.exe"
DB_PATH = r"D:\harfile\ModelFusion\IDE\db\hf_models.db"
SERVER_URL = "http://127.0.0.1:5007/orchestrate"
CHAT_URL = "http://127.0.0.1:5007/v1/chat/completions"

proc = subprocess.Popen(
    [CLI_PATH, "--server", "--port", "5007", "--db-path", DB_PATH],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8"
)

# wait for ready
for _ in range(30):
    time.sleep(0.3)
    try:
        req = urllib.request.Request(
            SERVER_URL,
            data=json.dumps({"prompt": "User: /stats"}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            if r.status == 200:
                break
    except Exception:
        pass

def send_req(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode('utf-8', errors='ignore').strip()
            return raw
    except Exception as e:
        return f"ERROR: {e}"

# Test 1: Compacted conversation in /orchestrate with /active-models
p1 = {
    "prompt": "System: You are HugOS AI.\n[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\nUser: /active-models"
}
res1 = send_req(SERVER_URL, p1)
print("TEST 1 (/orchestrate /active-models):")
print(res1[:300])
print()

# Test 2: Compacted conversation in /orchestrate with @agent --active-model
p2 = {
    "prompt": "System: You are HugOS AI.\n[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\nUser: @agent --active-model"
}
res2 = send_req(SERVER_URL, p2)
print("TEST 2 (/orchestrate @agent --active-model):")
print(res2[:300])
print()

# Test 3: OpenAI chat/completions with messages containing compacted conversation and /active-models
p3 = {
    "model": "qwen2.5:7b",
    "messages": [
        {"role": "user", "content": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>"},
        {"role": "user", "content": "/active-models"}
    ]
}
res3 = send_req(CHAT_URL, p3)
print("TEST 3 (/v1/chat/completions /active-models):")
print(res3[:300])
print()

# Test 4: OpenAI chat/completions with @agent --active-model
p4 = {
    "model": "qwen2.5:7b",
    "messages": [
        {"role": "user", "content": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>"},
        {"role": "user", "content": "@agent --active-model"}
    ]
}
res4 = send_req(CHAT_URL, p4)
print("TEST 4 (/v1/chat/completions @agent --active-model):")
print(res4[:300])
print()

# Test 5: Compacted conversation with the exact VS Code preamble
p5 = {
    "prompt": "System: You are HugOS AI.\nThe following is a compressed version of the preceding history in the current conversation:\n<user>some old message</user>\n<assistant>some old response</assistant>\nUser: /active-models"
}
res5 = send_req(SERVER_URL, p5)
print("TEST 5 (VS Code preamble + /active-models):")
print(res5[:300])
print()

# Test 6: Compacted conversation with the exact VS Code preamble in chat completions
p6 = {
    "model": "qwen2.5:7b",
    "messages": [
        {"role": "user", "content": "The following is a compressed version of the preceding history in the current conversation:\n<user>some old message</user>\n<assistant>some old response</assistant>"},
        {"role": "user", "content": "@agent --active-model"}
    ]
}
res6 = send_req(CHAT_URL, p6)
print("TEST 6 (VS Code preamble in chat completions + @agent --active-model):")
print(res6[:300])
print()

# Test 7: Single user message in chat completions containing compaction AND command without User: prefix
p7 = {
    "model": "qwen2.5:7b",
    "messages": [
        {"role": "user", "content": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n/active-models"}
    ]
}
res7 = send_req(CHAT_URL, p7)
print("TEST 7 (Single message with compaction and /active-models):")
print(res7[:300])
print()

# Test 8: Single user message in chat completions containing compaction AND @agent --active-model without User: prefix
p8 = {
    "model": "qwen2.5:7b",
    "messages": [
        {"role": "user", "content": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n@agent --active-model"}
    ]
}
res8 = send_req(CHAT_URL, p8)
print("TEST 8 (Single message with compaction and @agent --active-model):")
print(res8[:300])
print()

# Test 9: /orchestrate with single user query: "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n/active-models"
p9 = {
    "prompt": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n/active-models"
}
res9 = send_req(SERVER_URL, p9)
print("TEST 9 (/orchestrate prompt with compaction and /active-models, NO 'User:' marker):")
print(res9[:300])
print()

# Test 10: /orchestrate with single user query: "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n@agent --active-model"
p10 = {
    "prompt": "[Compacted conversation]\n<user>some old message</user>\n<assistant>some old response</assistant>\n\n@agent --active-model"
}
res10 = send_req(SERVER_URL, p10)
print("TEST 10 (/orchestrate prompt with compaction and @agent --active-model, NO 'User:' marker):")
print(res10[:300])
print()

proc.terminate()

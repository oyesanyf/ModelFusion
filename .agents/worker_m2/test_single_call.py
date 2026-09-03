import subprocess
import json
import sys
import time
import os

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

env = os.environ.copy()
env["MODELFUSION_TIMEOUT"] = "5"
env["MODELFUSION_ROUTER_TIMEOUT"] = "2"
env["MODELFUSION_HF_ROUTER_TIMEOUT"] = "2"
env["MODELFUSION_USE_OLLAMA"] = "true"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    env=env
)

def send_recv(req):
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except:
                continue

# Init
res = send_recv({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
print("Init:", res)

# Test data_science
t0 = time.time()
res = send_recv({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
    "name": "data_science",
    "arguments": {"mode": "analyst", "prompt": "Quick summary"}
}})
print(f"data_science ({time.time()-t0:.2f}s):", res)

# Test text_classification
t0 = time.time()
res = send_recv({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
    "name": "text_classification",
    "arguments": {"text": "ModelFusion test classification"}
}})
print(f"text_classification ({time.time()-t0:.2f}s):", res)

p.terminate()

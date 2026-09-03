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
env["LOCAL_OLLAMA_ENDPOINT"] = "http://127.0.0.1:11434"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
    env=env
)

def send(req):
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

print("Initializing...", flush=True)
res = send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
print("Init response:", res, flush=True)

print("Calling orchestrate...", flush=True)
t0 = time.time()
res = send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
    "name": "orchestrate",
    "arguments": {
        "prompt": "Hello ModelFusion",
        "budget": 1.0
    }
}})
print(f"Orchestrate returned in {time.time()-t0:.2f}s: {res}", flush=True)

p.terminate()

import subprocess
import urllib.request
import json
import time
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"
OV_DIR = r"C:\Users\oyesa\.hugos-ide\ov_models"
SERVER_URL = "http://127.0.0.1:5005/orchestrate"

print("=" * 75)
print(" 🚀 STARTING INTEGRATED MODELFUSION SERVER & MCP TEST SUITE")
print("=" * 75)

# 1. Spawn test server on dedicated port 5005
server_cmd = [CLI_PATH, "--server", "--port", "5005", "--db-path", DB_PATH, "--ov-model-dir", OV_DIR]
print(f"Spawning test server: {' '.join(server_cmd)}")

proc = subprocess.Popen(
    server_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8"
)

# Wait for server to become responsive
ready = False
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
                ready = True
                break
    except Exception:
        pass

if not ready:
    print("❌ Failed to start test server on port 5005.")
    proc.terminate()
    sys.exit(1)

print("✅ Server initialized and listening on port 5005.\n")

def test_endpoint(prompt_text, expect_keyword=None):
    payload = {
        "prompt": prompt_text,
        "backend": "ollama",
        "device": "gpu",
        "budget": 7,
        "strategy": "multi_objective",
        "fusion": False
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(SERVER_URL, data=data, headers={'Content-Type': 'application/json'})
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = (time.time() - t0) * 1000
            raw = resp.read().decode('utf-8', errors='ignore').strip()
            try:
                obj = json.loads(raw)
                content = obj.get("content", raw)
            except Exception:
                content = raw
            
            passed = True
            if expect_keyword and expect_keyword.lower() not in content.lower():
                passed = False
            
            status = "✅ PASS" if passed else "❌ FAIL"
            preview = content.replace('\n', ' ')[:85]
            print(f"  {status} [{elapsed:6.1f}ms] {prompt_text[:35]:<35} -> {preview}...")
            return passed
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        print(f"  ❌ ERROR [{elapsed:6.1f}ms] {prompt_text[:35]:<35} -> {e}")
        return False

# Comprehensive test matrix:
# 1. @agent /cmd
# 2. @agent cmd (slash-less)
# 3. /cmd
# 4. cmd (bare word)
# 5. Full VS Code XML wrapping with <userRequest>
# 6. False positive protection with system XML
test_cases = [
    # Stats variations
    ("User: @agent stats", "CPU"),
    ("User: @agent /stats", "CPU"),
    ("User: /stats", "CPU"),
    ("User: stats", "CPU"),
    
    # Sysinfo variations
    ("User: @agent sysinfo", "Logical Cores"),
    ("User: @agent /sysinfo", "Logical Cores"),
    ("User: /sysinfo", "Logical Cores"),
    
    # MCP & Keys variations
    ("User: @agent /mcp", "MCP"),
    ("User: /mcp", "MCP"),
    ("User: @agent /keys", "API Key"),
    ("User: /keys", "API Key"),
    
    # Tasks & Stats
    ("User: @agent /tasks", "Tasks"),
    ("User: /cache-stats", "Cache"),
    ("User: /performance-stats", "Performance"),
    ("User: /decision-stats", "Decision"),
    
    # Complex VS Code XML Wrapped Prompt
    ("<context >\n<editorContext>\nFile: import math.py\n</editorContext>\n<userRequest>\nstats\n</userRequest>", "CPU"),
    ("<context >\n<editorContext>\nFile: import math.py\n</editorContext>\n<userRequest>\n@agent /evolve\n</userRequest>", "OpenEvolve"),
    
    # Unknown command fallback
    ("User: @agent /invalidcmd", "Unknown"),
]

passed = 0
for prompt, kw in test_cases:
    if test_endpoint(prompt, kw):
        passed += 1

proc.terminate()
print("\n" + "=" * 75)
print(f" FINAL RESULTS: {passed}/{len(test_cases)} Tests Passed Successfully ({passed/len(test_cases)*100:.1f}%)")
print("=" * 75)

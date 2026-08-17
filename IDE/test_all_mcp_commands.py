import subprocess
import json
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8"
)

req_id = 0
def call_mcp(method, params=None):
    global req_id
    req_id += 1
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    p.stdin.write(json.dumps(msg) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            return {}
        line_s = line.strip()
        if line_s.startswith("{"):
            try:
                return json.loads(line_s)
            except Exception:
                continue

print("=" * 70)
print(" MODELFUSION MCP PROTOCOL & COMMAND VERIFICATION SUITE")
print("=" * 70)

# 1. Initialize
init_resp = call_mcp("initialize")
server_info = init_resp.get("result", {}).get("serverInfo", {})
print(f"✅ [MCP Initialize] Server: {server_info.get('name')}, Version: {server_info.get('version')}")

# 2. List tools
tools_resp = call_mcp("tools/list")
tools = tools_resp.get("result", {}).get("tools", [])
tool_names = [t["name"] for t in tools]
print(f"✅ [MCP Tools List] Total Registered Tools: {len(tools)}")
print(f"   Tools Sample: {', '.join(tool_names[:8])}...")

# 3. Test individual commands / tool calls
tests = [
    ("get_database_stats (stats / @agent stats)", "get_database_stats", {}),
    ("get_system_info (sysinfo / @agent sysinfo)", "get_system_info", {}),
    ("get_decision_stats (/decision-stats)", "get_decision_stats", {}),
    ("get_performance_stats (/performance-stats)", "get_performance_stats", {}),
    ("get_cache_stats (/cache-stats)", "get_cache_stats", {}),
    ("get_novel_ai_stats (/novel-ai-stats)", "get_novel_ai_stats", {}),
    ("list_tasks (/tasks)", "list_tasks", {"category": "all"}),
]

print("\n" + "─" * 70)
print(" RUNNING MCP TOOL CALL TESTS")
print("─" * 70)

passed = 0
for desc, tool_name, args in tests:
    t0 = time.time()
    resp = call_mcp("tools/call", {"name": tool_name, "arguments": args})
    elapsed_ms = (time.time() - t0) * 1000
    
    if "result" in resp and "content" in resp["result"]:
        text = resp["result"]["content"][0].get("text", "")
        preview = text.replace('\n', ' ')[:90]
        print(f"  ✅ [{elapsed_ms:6.1f}ms] {desc}")
        print(f"      Result: {preview}...")
        passed += 1
    elif "error" in resp:
        print(f"  ❌ [{elapsed_ms:6.1f}ms] {desc} -> ERROR: {resp['error']}")
    else:
        print(f"  ❌ [{elapsed_ms:6.1f}ms] {desc} -> UNEXPECTED: {resp}")

p.terminate()

print("\n" + "=" * 70)
print(f" RESULTS: {passed}/{len(tests)} MCP Tool Commands Verified Successfully")
print("=" * 70)

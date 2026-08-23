import subprocess
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

p = subprocess.Popen(
    [r"d:\harfile\ModelFusion\target\release\cli.exe", "--mcp", "--db-path", r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8"
)

def call(req):
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            raise Exception("EOF")
        line_s = line.strip()
        print(f"DEBUG RECV: {line_s}", file=sys.stderr)
        if line_s.startswith("{"):
            try:
                return json.loads(line_s)
            except Exception as e:
                print(f"DEBUG EXCEPTION: {e}", file=sys.stderr)
                continue

print("1. Init:", call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})["result"]["serverInfo"])

tools_list = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
print(f"2. Tools Count: {len(tools_list['result']['tools'])}")

db_stats = call({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_database_stats", "arguments": {}}})
print("3. DB Stats result preview:", db_stats["result"]["content"][0]["text"][:120])

sys_info = call({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_system_info", "arguments": {}}})
print("4. Sys Info result preview:", sys_info["result"]["content"][0]["text"][:120])

p.terminate()
print("ALL 4 MCP TESTS PASSED!")

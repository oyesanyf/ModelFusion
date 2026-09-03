import subprocess
import json
import sys

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8"
)

def send_and_print(req):
    sys.stderr.write(f"\n>>> SENDING: {json.dumps(req)}\n")
    sys.stderr.flush()
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            sys.stderr.write("<<< EOF REACHED\n")
            break
        sys.stderr.write(f"<<< LINE: {line}")
        sys.stderr.flush()
        if line.strip().startswith("{"):
            try:
                parsed = json.loads(line.strip())
                if "id" in parsed and parsed["id"] == req.get("id"):
                    return parsed
            except Exception as e:
                sys.stderr.write(f"JSON ERROR: {e}\n")

send_and_print({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
send_and_print({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_system_info", "arguments": {}}})
send_and_print({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_database_stats", "arguments": {}}})

p.terminate()

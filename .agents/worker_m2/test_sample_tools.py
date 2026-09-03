import os
import sys
import time

ide_dir = os.path.abspath(r"D:\harfile\ModelFusion\IDE")
if ide_dir not in sys.path:
    sys.path.insert(0, ide_dir)

from test_mcp_full_harness import ModelFusionMcpClient, find_default_cli_path, find_default_db_path

cli = find_default_cli_path()
db = find_default_db_path()
print(f"Testing with CLI: {cli}")
print(f"Testing with DB: {db}")

client = ModelFusionMcpClient(cli, db, timeout=30.0)
client.start()

try:
    # 1. Init
    t0 = time.time()
    res = client.send_request("initialize")
    print(f"Init ({time.time()-t0:.2f}s):", res.get("result", {}).get("serverInfo"))

    # 2. List tools
    t0 = time.time()
    res = client.send_request("tools/list")
    tools = res.get("result", {}).get("tools", [])
    print(f"tools/list ({time.time()-t0:.2f}s): count={len(tools)}")

    # 3. Telemetry tools
    for name in ["get_system_info", "get_database_stats", "list_tasks", "get_novel_ai_stats", "get_performance_stats"]:
        t0 = time.time()
        res = client.send_request("tools/call", {"name": name, "arguments": {}})
        content = res.get("result", {}).get("content", [{}])[0].get("text", "")[:60]
        print(f"Tool '{name}' ({time.time()-t0:.3f}s): {content}")

    # 4. Single-task tool
    t0 = time.time()
    res = client.send_request("tools/call", {"name": "text_classification", "arguments": {"text": "Test statement"}})
    content = res.get("result", {}).get("content", [{}])[0].get("text", "")[:80]
    print(f"Tool 'text_classification' ({time.time()-t0:.3f}s): {content}")

finally:
    client.close()
    print("Closed client successfully.")

import subprocess
import json
import sys
import time
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

# Fallback DB if user directory doesn't have it
if not os.path.exists(DB_PATH):
    fallback = r"D:\harfile\ModelFusion\src\db\hf_models.db"
    if os.path.exists(fallback):
        DB_PATH = fallback
    else:
        DB_PATH = r"D:\harfile\ModelFusion\models.db"

print(f"Using CLI: {CLI_PATH}")
print(f"Using DB: {DB_PATH}")

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

# 1. Initialize
init_resp = call_mcp("initialize")
server_info = init_resp.get("result", {}).get("serverInfo", {})
print(f"Initialize: {server_info}")

# 2. List tools
tools_resp = call_mcp("tools/list")
tools = tools_resp.get("result", {}).get("tools", [])
print(f"Registered MCP Tools Count: {len(tools)}")

# Prepare sample payloads for each tool
tool_payloads = {
    "execute": {"args": ["--sys-info"]},
    "quick_answer": {"question": "What is 2+2?"},
    "orchestrate": {"prompt": "Hello ModelFusion"},
    "analyze_file": {"file": r"D:\harfile\ModelFusion\Cargo.toml", "prompt": "Check dependencies"},
    "analyze_folder": {"folder": r"D:\harfile\ModelFusion\crates\core", "prompt": "Overview"},
    "nlp_task": {"task": "sentiment-analysis", "text": "This framework is fast and reliable!"},
    "security_analysis": {"task": "spam-detection", "text": "Win a free lottery prize now!"},
    "code_task": {"task": "code-summary-generation", "text": "fn add(a: i32, b: i32) -> i32 { a + b }"},
    "domain_task": {"task": "financial-sentiment-analysis", "text": "Quarterly revenue increased by 25%."},
    "multimodal_task": {"task": "image-classification", "prompt": "Classify input image"},
    "semantic_search": {"action": "search", "query": "transformer attention mechanism"},
    "data_science": {"mode": "analyst", "prompt": "Analyze statistical distributions"},
    "pe_header_extraction": {"file": CLI_PATH, "prompt": "Inspect binary headers"},
    "model_management": {"action": "analytics"},
    "reporting": {"prompt": "Generate summary report", "output_path": r"D:\harfile\ModelFusion\.agents\explorer_2\sample_report.md", "format": "md"},
    "ml_management": {"action": "analytics"},
    "get_system_info": {},
    "get_database_stats": {},
    "list_tasks": {"category": "all"},
    "update_database": {},
    "restore_backup": {},
    "clear_cache": {},
    "get_decision_stats": {},
    "get_novel_ai_stats": {},
    "get_performance_stats": {},
    "get_cache_stats": {},
    "get_model_recommendations": {},
    "get_model_ranking": {"category": "text-generation"},
    "get_ml_analytics": {},
    "report_bandit_feedback": {"context": 0, "arm": 0, "reward": 0.9},
}

# Add default text payload for all 61 specialized single-task tools
for t in tools:
    name = t["name"]
    if name not in tool_payloads:
        tool_payloads[name] = {"text": f"Sample input text for testing {name} tool execution."}

results = []
passed = 0
failed = 0

print("\n" + "="*80)
print(f" TESTING ALL {len(tools)} MCP TOOLS")
print("="*80)

for idx, t in enumerate(tools, 1):
    name = t["name"]
    args = tool_payloads.get(name, {})
    t0 = time.time()
    resp = call_mcp("tools/call", {"name": name, "arguments": args})
    elapsed = (time.time() - t0) * 1000

    has_result = "result" in resp and "content" in resp["result"]
    has_error = "error" in resp

    if has_result:
        content = resp["result"]["content"]
        text_out = content[0].get("text", "") if len(content) > 0 else ""
        is_err_text = text_out.startswith("Error: Unknown tool") or "Failed to run" in text_out
        status = "FAIL" if is_err_text else "PASS"
    else:
        status = "FAIL"

    if status == "PASS":
        passed += 1
        preview = text_out.replace('\n', ' ')[:70]
        print(f"[{idx:2d}/{len(tools):2d}] PASS ({elapsed:5.1f}ms) {name:<32} -> {preview}")
    else:
        failed += 1
        print(f"[{idx:2d}/{len(tools):2d}] FAIL ({elapsed:5.1f}ms) {name:<32} -> Resp: {resp}")

    results.append({
        "index": idx,
        "name": name,
        "status": status,
        "elapsed_ms": elapsed,
        "response_preview": (text_out[:120] if has_result else str(resp))
    })

p.terminate()

print("\n" + "="*80)
print(f" SUMMARY: {passed}/{len(tools)} Passed, {failed}/{len(tools)} Failed")
print("="*80)

with open(r"D:\harfile\ModelFusion\.agents\explorer_2\mcp_test_results.json", "w", encoding="utf-8") as f:
    json.dump({"total": len(tools), "passed": passed, "failed": failed, "results": results}, f, indent=2)

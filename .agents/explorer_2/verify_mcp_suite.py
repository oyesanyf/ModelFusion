import subprocess
import json
import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"
DB_PATH = r"C:\Users\oyesa\.hugos-ide\db\hf_models.db"

env = os.environ.copy()
env["MODELFUSION_TIMEOUT"] = "3"
env["MODELFUSION_ROUTER_TIMEOUT"] = "3"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
    env=env
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
                data = json.loads(line_s)
                if "id" in data and data["id"] == req_id:
                    return data
            except Exception:
                continue

# 1. Initialize
init_resp = call_mcp("initialize")
server_info = init_resp.get("result", {}).get("serverInfo", {})
print(f"[INIT] Server Name: {server_info.get('name')}, Version: {server_info.get('version')}", flush=True)

# 2. Tools List
tools_resp = call_mcp("tools/list")
tools = tools_resp.get("result", {}).get("tools", [])
print(f"[TOOLS/LIST] Total Tools: {len(tools)}", flush=True)

# Test matrix spanning all tool families
test_matrix = [
    # In-process Database / Stats / Telemetry
    ("get_database_stats", {}),
    ("list_tasks", {"category": "all"}),
    ("get_decision_stats", {}),
    ("get_performance_stats", {}),
    ("get_cache_stats", {}),
    ("get_ml_analytics", {}),
    ("report_bandit_feedback", {"context": 0, "arm": 0, "reward": 0.95}),
    
    # CLI Subprocess System & Stats
    ("get_system_info", {}),
    ("get_novel_ai_stats", {}),
    ("get_model_ranking", {"category": "text-generation"}),
    
    # Specialized NLP Tools
    ("text_classification", {"text": "ModelFusion provides high-throughput local AI inferencing."}),
    ("summarization", {"text": "ModelFusion integrates multi-model routing, Ollama, OpenVINO, and ONNX into a unified framework."}),
    ("translation", {"text": "Hello world", "language": "fr"}),
    
    # Specialized Security Tools
    ("spam_detection", {"text": "Congratulations you won a lottery claim now"}),
    ("pii_detection", {"text": "Contact John Doe at john.doe@example.com or 555-123-4567"}),
    ("malware_text_detection", {"text": "powershell.exe -ExecutionPolicy Bypass -Command IEX"}),
    
    # Specialized Code & Domain Tools
    ("code_summary_generation", {"text": "fn compute_sum(a: i32, b: i32) -> i32 { a + b }"}),
    ("financial_sentiment_analysis", {"text": "Q3 revenues grew 34% year-over-year exceeding analyst forecasts."}),
    ("biomedical_ner", {"text": "Patient was administered 50mg of ibuprofen for headache relief."}),
    
    # Multimodal & PE Tools
    ("image_classification", {"text": "Analyze image tags"}),
    ("pe_header_extraction", {"file": CLI_PATH, "prompt": "Examine PE header properties"}),
    
    # Universal Executor
    ("execute", {"args": ["--sys-info"]}),
    
    # Direct Quick Answer
    ("quick_answer", {"question": "What is 2+2?", "model": "qwen2.5:0.5b"})
]

print("\n" + "="*80, flush=True)
print(f" RUNNING MCP REPRESENTATIVE VERIFICATION MATRIX ({len(test_matrix)} Tool Invocations)", flush=True)
print("="*80, flush=True)

passed = 0
for idx, (name, args) in enumerate(test_matrix, 1):
    t0 = time.time()
    resp = call_mcp("tools/call", {"name": name, "arguments": args})
    elapsed = (time.time() - t0) * 1000
    
    content = resp.get("result", {}).get("content", [])
    if content and "text" in content[0]:
        text = content[0]["text"].replace("\n", " ").strip()
        preview = text[:75] + ("..." if len(text) > 75 else "")
        print(f"[{idx:02d}/{len(test_matrix):02d}] PASS ({elapsed:6.1f}ms) {name:<28} -> {preview}", flush=True)
        passed += 1
    else:
        print(f"[{idx:02d}/{len(test_matrix):02d}] FAIL ({elapsed:6.1f}ms) {name:<28} -> {resp}", flush=True)

p.terminate()

print("\n" + "="*80, flush=True)
print(f" MATRIX RESULT: {passed}/{len(test_matrix)} Tests Passed Successfully ({passed/len(test_matrix)*100:.1f}%)", flush=True)
print("="*80, flush=True)

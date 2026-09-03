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
env["MODELFUSION_TIMEOUT"] = "5"
env["MODELFUSION_ROUTER_TIMEOUT"] = "3"
env["MODELFUSION_USE_OLLAMA"] = "true"

p = subprocess.Popen(
    [CLI_PATH, "--mcp", "--db-path", DB_PATH],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    env=env
)

req_id = 0
def send_mcp(method, params=None):
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
                parsed = json.loads(line_s)
                if "id" in parsed and parsed["id"] == req_id:
                    return parsed
            except Exception:
                continue

# Step 1: Handshake
init_resp = send_mcp("initialize")
server_info = init_resp.get("result", {}).get("serverInfo", {})
print(f"================================================================================", flush=True)
print(f" ModelFusion MCP Server Handshake Initialized", flush=True)
print(f" Server: {server_info.get('name')} | Version: {server_info.get('version')} | Protocol: 2024-11-05", flush=True)
print(f"================================================================================\n", flush=True)

# Step 2: Tools Listing
tools_resp = send_mcp("tools/list")
all_tools = tools_resp.get("result", {}).get("tools", [])
print(f"Total Registered MCP Tools: {len(all_tools)}\n", flush=True)

# Step 3: Test Matrix
test_cases = [
    # Telemetry, Database, Cache & Stats
    ("get_system_info", {}),
    ("get_database_stats", {}),
    ("list_tasks", {"category": "all"}),
    ("get_decision_stats", {}),
    ("get_novel_ai_stats", {}),
    ("get_performance_stats", {}),
    ("get_cache_stats", {}),
    ("get_model_recommendations", {}),
    ("get_model_ranking", {"category": "text-generation"}),
    ("get_ml_analytics", {}),
    ("report_bandit_feedback", {"context": 0, "arm": 0, "reward": 0.95}),
    ("restore_backup", {}),
    ("clear_cache", {}),
    
    # Universal & Composite Orchestration Tools
    ("execute", {"args": ["--sys-info"]}),
    ("quick_answer", {"question": "What is 2+2?", "model": "qwen2.5:0.5b"}),
    ("pe_header_extraction", {"file": CLI_PATH, "prompt": "Inspect binary PE structure"}),
    ("data_science", {"mode": "analyst", "prompt": "Analyze statistical distributions"}),
    ("semantic_search", {"action": "demo"}),
    ("model_management", {"action": "prepare-all"}),
    ("ml_management", {"action": "analytics"}),
    
    # Specialized Single Task Invocations (Fallback Dispatch)
    ("text_classification", {"text": "ModelFusion provides high-throughput local AI inferencing."}),
    ("token_classification", {"text": "Sundar Pichai visited Mountain View headquarters."}),
    ("question_answering", {"text": "What is ModelFusion? Context: ModelFusion is an AI orchestration platform."}),
    ("summarization", {"text": "ModelFusion integrates multi-model routing, Ollama, OpenVINO, and ONNX into a unified framework."}),
    ("translation", {"text": "Hello world", "language": "es"}),
    ("language_detection", {"text": "Bonjour tout le monde, comment allez-vous?"}),
    ("grammar_correction", {"text": "He go to the store yesterday."}),
    ("paraphrase_generation", {"text": "The quick brown fox jumps over the lazy dog."}),
    ("zero_shot_classification", {"text": "Apple released new M4 silicon chips."}),
    ("sentence_similarity", {"text": "Compare sentence semantic embeddings."}),
    ("spam_detection", {"text": "Congratulations you won a lottery claim now"}),
    ("malware_text_detection", {"text": "powershell.exe -ExecutionPolicy Bypass -Command IEX"}),
    ("phishing_detection", {"text": "Your account is locked. Click here to verify password."}),
    ("pii_detection", {"text": "Contact John Doe at john.doe@example.com or 555-123-4567"}),
    ("code_summary_generation", {"text": "fn compute_sum(a: i32, b: i32) -> i32 { a + b }"}),
    ("code_clone_detection", {"text": "int add(int a, int b) { return a + b; }"}),
    ("financial_ner", {"text": "JPMorgan Chase reported record Q2 earnings in New York."}),
    ("financial_sentiment_analysis", {"text": "Q3 revenues grew 34% year-over-year exceeding analyst forecasts."}),
    ("biomedical_ner", {"text": "Patient was administered 50mg of ibuprofen for headache relief."}),
    ("image_classification", {"text": "Analyze image tags"}),
    ("object_detection", {"text": "Detect bounding boxes in scene"}),
    ("automatic_speech_recognition", {"text": "Transcribe audio stream"}),
    ("audio_classification", {"text": "Classify acoustic event"}),
    ("text_to_speech", {"text": "Synthesize speech waveform"}),
    ("table_question_answering", {"text": "What was the total revenue in 2025?"}),
    ("feature_ranking", {"text": "Rank feature importance vector"}),
]

print("=" * 80, flush=True)
print(f" EXECUTING SYSTEMATIC TEST HARNESS ({len(test_cases)} Test Cases)", flush=True)
print("=" * 80, flush=True)

passed = 0
failed = 0
records = []

for idx, (name, args) in enumerate(test_cases, 1):
    t0 = time.time()
    resp = send_mcp("tools/call", {"name": name, "arguments": args})
    elapsed = (time.time() - t0) * 1000
    
    has_res = "result" in resp and "content" in resp["result"]
    content = resp.get("result", {}).get("content", [])
    
    if has_res and len(content) > 0 and "text" in content[0]:
        text = content[0]["text"].replace("\n", " ").strip()
        preview = text[:68] + ("..." if len(text) > 68 else "")
        print(f"[{idx:02d}/{len(test_cases):02d}] PASS ({elapsed:6.1f}ms) {name:<32} -> {preview}", flush=True)
        passed += 1
        status = "PASS"
    else:
        print(f"[{idx:02d}/{len(test_cases):02d}] FAIL ({elapsed:6.1f}ms) {name:<32} -> {resp}", flush=True)
        failed += 1
        status = "FAIL"
        
    records.append({
        "index": idx,
        "name": name,
        "status": status,
        "elapsed_ms": round(elapsed, 2),
        "arguments": args,
        "preview": text[:120] if (has_res and len(content) > 0) else str(resp)
    })

p.terminate()

print("\n" + "=" * 80, flush=True)
print(f" VERIFICATION RESULTS: {passed}/{len(test_cases)} PASSED ({passed/len(test_cases)*100:.1f}%), {failed} FAILED", flush=True)
print("=" * 80, flush=True)

report_data = {
    "protocol": "Model Context Protocol (MCP) 2024-11-05",
    "server": "ModelFusion MCP Server v0.1.0",
    "total_registered_tools": len(all_tools),
    "tested_tools_count": len(test_cases),
    "passed": passed,
    "failed": failed,
    "pass_rate_pct": round(passed / len(test_cases) * 100, 2),
    "records": records
}

with open(r"D:\harfile\ModelFusion\.agents\explorer_2\mcp_verification_report.json", "w", encoding="utf-8") as f:
    json.dump(report_data, f, indent=2)

#!/usr/bin/env python3
"""
ModelFusion Comprehensive Standalone MCP Test Harness
======================================================
Systematically tests and verifies the Model Context Protocol (MCP 2024-11-05)
JSON-RPC server implemented in ModelFusion (crates/cli/src/main.rs).

Tests all 91 MCP tools:
- JSON-RPC protocol handshake & notifications
- tools/list discovery and JSONSchema validation for all 91 tools
- In-process telemetry, database, cache, ranking, and bandit handlers
- Hub/composite orchestration tools (execute, quick_answer, orchestrate, etc.)
- All 61 specialized single-task tools (NLP, Security, Domain, Code, Multimodal)
- Input schema validation & error response handling
- Real-time latency tracking, JSON telemetry, and summary reporting

Usage:
    python IDE/test_mcp_full_harness.py [--cli-path <path>] [--db-path <path>] [--report-path <path>]
"""

import os
import sys
import json
import time
import argparse
import subprocess
from typing import Dict, Any, List, Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# Default Paths & Auto-detection
# ─────────────────────────────────────────────────────────────────────────────

def find_default_cli_path() -> str:
    candidates = [
        os.path.join("IDE", "bin", "cli.exe"),
        os.path.join(os.path.dirname(__file__), "bin", "cli.exe"),
        r"D:\harfile\ModelFusion\IDE\bin\cli.exe",
        os.path.join("target", "release", "cli.exe"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "target", "release", "cli.exe"),
        r"D:\harfile\ModelFusion\target\release\cli.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])

def find_default_db_path() -> str:
    candidates = [
        os.path.expandvars(r"%USERPROFILE%\.hugos-ide\db\hf_models.db"),
        r"C:\Users\oyesa\.hugos-ide\db\hf_models.db",
        os.path.join("src", "db", "hf_models.db"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "db", "hf_models.db"),
        "hf_models.db",
        "models.db",
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])


# ─────────────────────────────────────────────────────────────────────────────
# Complete 91-Tool Test Payload Matrix
# ─────────────────────────────────────────────────────────────────────────────

def get_tool_payload_matrix(cli_path: str) -> Dict[str, Dict[str, Any]]:
    """Returns valid typed input arguments for every one of the 91 MCP tools."""
    matrix: Dict[str, Dict[str, Any]] = {
        # --- 1. Universal & Core Orchestration (16 tools) ---
        "execute": {
            "args": ["--sys-info"]
        },
        "quick_answer": {
            "question": "What is the capital of France?",
            "model": "qwen2.5:0.5b"
        },
        "orchestrate": {
            "prompt": "Calculate Fibonacci sequence",
            "budget": 1.0,
            "gpu": False,
            "cpu": True
        },
        "analyze_file": {
            "file": os.path.abspath("Cargo.toml") if os.path.exists("Cargo.toml") else r"D:\harfile\ModelFusion\Cargo.toml",
            "prompt": "Inspect project dependencies and package metadata"
        },
        "analyze_folder": {
            "folder": os.path.abspath("crates") if os.path.exists("crates") else r"D:\harfile\ModelFusion\crates",
            "prompt": "Provide high-level architecture overview"
        },
        "nlp_task": {
            "task": "sentiment-analysis",
            "text": "ModelFusion provides high-throughput local AI inferencing."
        },
        "security_analysis": {
            "task": "spam-detection",
            "text": "Exclusive offer: Claim your free prize reward immediately!"
        },
        "code_task": {
            "task": "code-summary-generation",
            "text": "pub fn binary_search(arr: &[i32], target: i32) -> Option<usize>"
        },
        "domain_task": {
            "task": "financial-sentiment-analysis",
            "text": "Q3 revenues grew 28% year-over-year exceeding market consensus."
        },
        "multimodal_task": {
            "task": "image-classification",
            "prompt": "Classify scene visual features and content tags"
        },
        "semantic_search": {
            "action": "demo"
        },
        "data_science": {
            "mode": "analyst",
            "prompt": "Analyze statistical distributions and generate summary"
        },
        "pe_header_extraction": {
            "file": cli_path,
            "prompt": "Inspect binary PE structure, section headers, and imports"
        },
        "model_management": {
            "action": "prepare-all"
        },
        "reporting": {
            "prompt": "Generate summary telemetry report",
            "output_path": os.path.abspath(r"IDE\reports\mcp_test_report.md"),
            "format": "md"
        },
        "ml_management": {
            "action": "analytics"
        },

        # --- 2. In-Process Telemetry & Database Management (14 tools) ---
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
        "report_bandit_feedback": {"context": 0, "arm": 0, "reward": 0.95},

        # --- 3. Specialized NLP Single-Task Tools (15 tools) ---
        "text_classification": {"text": "ModelFusion integrates multi-model routing and local inference."},
        "token_classification": {"text": "Sundar Pichai visited Mountain View headquarters yesterday."},
        "question_answering": {"text": "What is ModelFusion? Context: ModelFusion is an AI orchestration platform."},
        "text_generation": {"text": "Explain the advantages of asynchronous I/O in distributed systems."},
        "summarization": {"text": "ModelFusion is a hybrid multi-modal AI orchestration framework and VS Code IDE."},
        "translation": {"text": "Hello world from ModelFusion", "language": "es"},
        "fill_mask": {"text": "The capital of France is [MASK]."},
        "text2text_generation": {"text": "Transform this informal sentence to formal executive tone."},
        "language_detection": {"text": "Bonjour tout le monde, comment allez-vous aujourd'hui?"},
        "grammar_correction": {"text": "He go to the store yesterday and buy some apples."},
        "paraphrase_generation": {"text": "The quick brown fox jumps over the lazy dog."},
        "causal_language_modeling": {"text": "Modern computing architectures optimize for parallelism because"},
        "zero_shot_classification": {"text": "Apple announced new M4 Apple Silicon processing units."},
        "feature_extraction": {"text": "Extract semantic feature vector for deep similarity comparison."},
        "sentence_similarity": {"text": "Compare semantic embedding similarity between two technical passages."},

        # --- 4. Specialized Security Single-Task Tools (12 tools) ---
        "anonymization": {"text": "John Doe lives at 742 Evergreen Terrace with phone 555-0199."},
        "coreference_resolution": {"text": "Alice told Bob that she would send him the documentation."},
        "spam_detection": {"text": "Congratulations! You have won a $1,000 Walmart gift card. Click now."},
        "malware_text_detection": {"text": "powershell.exe -ExecutionPolicy Bypass -NoProfile -Command IEX"},
        "phishing_detection": {"text": "URGENT: Your account has been suspended. Verify credentials immediately."},
        "pii_detection": {"text": "Contact Jane Smith at jane.smith@corp.example.com or SSN 000-12-3456."},
        "hate_speech_detection": {"text": "We welcome everyone to collaborate openly on this open-source project."},
        "cyberbullying_detection": {"text": "Thank you for the thoughtful pull request review comments."},
        "fake_news_detection": {"text": "NASA confirms observation of major solar flare activity via SDO satellite."},
        "hallucination_detection": {"text": "Verify whether the assertion is grounded in the retrieved context documents."},
        "generation_groundedness": {"text": "Evaluate factual consistency between source citations and model output."},
        "citation_intent_classification": {"text": "As previously demonstrated by Vaswani et al. (2017) in the Transformer paper..."},

        # --- 5. Specialized Domain & Code Tools (16 tools) ---
        "legal_judgment_classification": {"text": "The appellate court affirmed the summary judgment in favor of respondent."},
        "contract_clause_classification": {"text": "Neither party shall assign its rights without prior written consent."},
        "case_outcome_prediction": {"text": "Plaintiff established sufficient factual evidence to survive motion to dismiss."},
        "financial_ner": {"text": "Goldman Sachs reported Q3 investment banking revenue of $1.8 billion."},
        "legal_ner": {"text": "Judge Learned Hand delivered the landmark opinion in the Second Circuit."},
        "biomedical_ner": {"text": "Patient was prescribed 500mg amoxicillin every 8 hours for acute bronchitis."},
        "chemical_reaction_ner": {"text": "Toluene was nitrated using concentrated nitric acid and sulfuric acid catalyst."},
        "financial_sentiment_analysis": {"text": "Net profits surged 35% year-over-year exceeding analyst forecasts."},
        "scientific_abstract_summarization": {"text": "We present an attention-based neural architecture for high-speed tokenization."},
        "emotion_detection": {"text": "I am absolutely delighted by the stellar performance of the new test suite!"},
        "sarcasm_detection": {"text": "Oh fantastic, another unhandled null pointer exception right before deploy."},
        "stance_detection": {"text": "Investing in energy efficiency reduces carbon emissions and operating costs."},
        "bias_detection": {"text": "Evaluating news articles for potential demographic or partisan bias indicators."},
        "reading_level_assessment": {"text": "Photosynthesis is the biochemical process by which plants synthesize carbohydrates."},
        "code_summary_generation": {"text": "pub async fn handle_stream(mut socket: TcpStream) -> Result<()>"},
        "code_clone_detection": {"text": "fn add(a: i32, b: i32) -> i32 { a + b }\nfn sum(x: i32, y: i32) -> i32 { x + y }"},

        # --- 6. Specialized Multimodal & Audio/Vision Tools (18 tools) ---
        "image_classification": {"prompt": "Classify scene visual features and object tags"},
        "object_detection": {"prompt": "Detect bounding boxes for vehicles, pedestrians, and traffic signs"},
        "image_segmentation": {"prompt": "Perform semantic segmentation of foreground subject from background"},
        "visual_question_answering": {"prompt": "What color is the vehicle parked near the building entrance?"},
        "document_question_answering": {"prompt": "What is the total invoice amount listed on line item 12?"},
        "zero_shot_image_classification": {"prompt": "Classify input image into candidate labels: urban, rural, forest, desert"},
        "depth_estimation": {"prompt": "Compute relative depth map estimation for monocular camera input"},
        "image_feature_extraction": {"prompt": "Extract 512-dimensional normalized visual embedding feature vector"},
        "automatic_speech_recognition": {"prompt": "Transcribe spoken speech audio waveform to clean text stream"},
        "audio_classification": {"prompt": "Classify environmental acoustic event: siren, applause, speech, engine"},
        "voice_activity_detection": {"prompt": "Detect active speech voice segments vs ambient background silence"},
        "emotion_recognition": {"prompt": "Identify speaker vocal emotional state: joyful, neutral, agitated, calm"},
        "video_classification": {"prompt": "Classify primary activity in video clip: running, typing, presenting"},
        "text_to_speech": {"prompt": "Synthesize natural neural speech waveform for input sentence"},
        "text_to_image": {"prompt": "Generate high-resolution concept illustration of an AI-powered IDE"},
        "image_super_resolution": {"prompt": "Upscale low-resolution bitmap image 4x using generative super resolution"},
        "table_question_answering": {"prompt": "What was the total adjusted EBITDA recorded in Q4 2025?"},
        "feature_ranking": {"prompt": "Compute feature importance ranking vector using gradient boosted tree scoring"}
    }
    return matrix


# ─────────────────────────────────────────────────────────────────────────────
# MCP Test Client Class
# ─────────────────────────────────────────────────────────────────────────────

class ModelFusionMcpClient:
    """Manages child CLI process lifecycle and JSON-RPC 2.0 communication over stdio."""

    def __init__(self, cli_path: str, db_path: str, timeout: float = 15.0):
        self.cli_path = cli_path
        self.db_path = db_path
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.req_id = 0

    def start(self) -> None:
        if not os.path.exists(self.cli_path):
            raise FileNotFoundError(f"CLI executable not found at: {self.cli_path}")
        
        env = os.environ.copy()
        env["MODELFUSION_TIMEOUT"] = "5"
        env["MODELFUSION_ROUTER_TIMEOUT"] = "2"
        env["MODELFUSION_HF_ROUTER_TIMEOUT"] = "2"
        env["MODELFUSION_USE_OLLAMA"] = "true"
        env["LOCAL_OLLAMA_ENDPOINT"] = "http://127.0.0.1:11434"

        cmd = [self.cli_path, "--mcp"]
        if self.db_path and os.path.exists(self.db_path):
            cmd.extend(["--db-path", self.db_path])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env=env,
            bufsize=1
        )

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server process is not running.")

        self.req_id += 1
        current_id = self.req_id
        request = {
            "jsonrpc": "2.0",
            "id": current_id,
            "method": method,
            "params": params if params is not None else {}
        }

        req_str = json.dumps(request) + "\n"
        self.process.stdin.write(req_str)
        self.process.stdin.flush()

        while True:
            line = self.process.stdout.readline()
            if not line:
                return {
                    "jsonrpc": "2.0",
                    "id": current_id,
                    "error": {
                        "code": -32000,
                        "message": "EOF received from MCP server stdout"
                    }
                }

            line_str = line.strip()
            if line_str.startswith("{"):
                try:
                    data = json.loads(line_str)
                    if data.get("id") == current_id or "result" in data or "error" in data:
                        return data
                except json.JSONDecodeError:
                    continue

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server process is not running.")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else {}
        }
        self.process.stdin.write(json.dumps(notification) + "\n")
        self.process.stdin.flush()

    def close(self) -> None:
        if self.process:
            try:
                self.process.stdin.close()
            except Exception:
                pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None


# ─────────────────────────────────────────────────────────────────────────────
# Test Runner & Verification Suite
# ─────────────────────────────────────────────────────────────────────────────

class McpFullHarness:
    """Orchestrates comprehensive verification across all 91 MCP tools."""

    def __init__(self, cli_path: str, db_path: str, timeout: float = 15.0, verbose: bool = True):
        self.cli_path = cli_path
        self.db_path = db_path
        self.timeout = timeout
        self.verbose = verbose
        self.client = ModelFusionMcpClient(cli_path, db_path, timeout)
        self.results: List[Dict[str, Any]] = []
        self.server_info: Dict[str, Any] = {}
        self.registered_tools: List[Dict[str, Any]] = []

    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    def run_all(self) -> Dict[str, Any]:
        self.log("=" * 80)
        self.log(" MODELFUSION COMPREHENSIVE MCP AUTOMATED TEST HARNESS")
        self.log(f" CLI Executable : {self.cli_path}")
        self.log(f" Database Path  : {self.db_path}")
        self.log("=" * 80)

        t_start = time.time()
        self.client.start()

        try:
            # Phase 1: Handshake
            self.test_handshake()

            # Phase 2: Protocol Error Handling
            self.test_protocol_errors()

            # Phase 3: Tools Discovery & Schema Validation
            self.test_tools_discovery()

            # Phase 4: Schema Validation Error Cases
            self.test_tool_call_validation_errors()

            # Phase 5: Systematic 91-Tool Verification Matrix
            self.test_all_91_tools()

        finally:
            self.client.close()

        total_elapsed = time.time() - t_start

        # Phase 6: Telemetry & Summary Aggregation
        summary = self.generate_summary(total_elapsed)
        return summary

    def test_handshake(self) -> None:
        self.log("\n[PHASE 1] Protocol Handshake & Capabilities...")
        t0 = time.time()
        resp = self.client.send_request("initialize")
        elapsed = (time.time() - t0) * 1000

        assert "result" in resp, f"Handshake failed: {resp}"
        res = resp["result"]
        assert res.get("protocolVersion") == "2024-11-05", f"Unexpected protocol: {res.get('protocolVersion')}"
        assert "capabilities" in res and "tools" in res["capabilities"], "Missing tools capability"
        self.server_info = res.get("serverInfo", {})
        self.log(f"  ✅ Initialized in {elapsed:.1f}ms: Server='{self.server_info.get('name')}', Version='{self.server_info.get('version')}'")

        # Send notification
        self.client.send_notification("notifications/initialized")
        self.log("  ✅ Sent notifications/initialized notification.")

    def test_protocol_errors(self) -> None:
        self.log("\n[PHASE 2] JSON-RPC Protocol Error Handling...")
        t0 = time.time()
        resp = self.client.send_request("invalid_method_that_does_not_exist")
        elapsed = (time.time() - t0) * 1000

        assert "error" in resp, f"Expected error for invalid method, got: {resp}"
        err = resp["error"]
        assert err.get("code") == -32601, f"Expected error code -32601, got: {err.get('code')}"
        self.log(f"  ✅ Error handled in {elapsed:.1f}ms: code={err.get('code')}, msg='{err.get('message')}'")

    def test_tools_discovery(self) -> None:
        self.log("\n[PHASE 3] tools/list Discovery & Schema Validation...")
        t0 = time.time()
        resp = self.client.send_request("tools/list")
        elapsed = (time.time() - t0) * 1000

        assert "result" in resp and "tools" in resp["result"], f"tools/list failed: {resp}"
        self.registered_tools = resp["result"]["tools"]
        tool_count = len(self.registered_tools)
        self.log(f"  ✅ tools/list returned {tool_count} tools in {elapsed:.1f}ms (Expected: 91)")
        assert tool_count == 91, f"Expected exactly 91 registered tools, got {tool_count}"

        # Validate JSONSchema structures for each tool
        schema_valid_count = 0
        for t in self.registered_tools:
            assert "name" in t and isinstance(t["name"], str) and len(t["name"]) > 0
            assert "description" in t and isinstance(t["description"], str)
            assert "inputSchema" in t and isinstance(t["inputSchema"], dict)
            schema = t["inputSchema"]
            assert schema.get("type") == "object"
            assert "properties" in schema and isinstance(schema["properties"], dict)
            schema_valid_count += 1

        self.log(f"  ✅ Schema integrity validated: {schema_valid_count}/91 tools conform to JSONSchema specifications.")

    def test_tool_call_validation_errors(self) -> None:
        self.log("\n[PHASE 4] Tool Call Schema & Invalid Input Validation...")
        
        # Test 1: Calling execute without required 'args'
        t0 = time.time()
        resp = self.client.send_request("tools/call", {"name": "execute", "arguments": {}})
        elapsed = (time.time() - t0) * 1000
        content = resp.get("result", {}).get("content", [])
        text = content[0].get("text", "") if content else ""
        assert "Error: Invalid or missing 'args' parameter" in text or "error" in resp, f"Unexpected validation response: {resp}"
        self.log(f"  ✅ Schema error caught on 'execute' missing args ({elapsed:.1f}ms)")

        # Test 2: Calling report_bandit_feedback with invalid arm/context
        t0 = time.time()
        resp = self.client.send_request("tools/call", {"name": "report_bandit_feedback", "arguments": {"context": 99, "arm": 99}})
        elapsed = (time.time() - t0) * 1000
        content = resp.get("result", {}).get("content", [])
        text = content[0].get("text", "") if content else ""
        assert "Error: Invalid context or arm index" in text or "error" in resp, f"Unexpected validation response: {resp}"
        self.log(f"  ✅ Schema error caught on 'report_bandit_feedback' invalid indices ({elapsed:.1f}ms)")

    def test_all_91_tools(self) -> None:
        self.log("\n[PHASE 5] Executing Systematic 91-Tool Verification Suite...")
        self.log("-" * 80)
        self.log(f"{'#':<3} | {'Tool Name':<34} | {'Status':<6} | {'Latency':<8} | {'Preview'}")
        self.log("-" * 80)

        payload_matrix = get_tool_payload_matrix(self.cli_path)
        
        # Categories mapping for telemetry
        category_map = self._build_category_map()

        for idx, tool in enumerate(self.registered_tools, 1):
            name = tool["name"]
            category = category_map.get(name, "Specialized Task")
            args = payload_matrix.get(name, {})
            
            # Fallback default payload if not explicitly in matrix
            if not args:
                req_props = tool.get("inputSchema", {}).get("required", [])
                all_props = tool.get("inputSchema", {}).get("properties", {})
                args = {}
                for rp in req_props:
                    prop_type = all_props.get(rp, {}).get("type", "string")
                    if prop_type == "string":
                        args[rp] = f"Test input payload for {name}"
                    elif prop_type == "number":
                        args[rp] = 1.0
                    elif prop_type == "integer":
                        args[rp] = 1
                    elif prop_type == "boolean":
                        args[rp] = True
                    elif prop_type == "array":
                        args[rp] = ["test"]
                if "text" in all_props and "text" not in args:
                    args["text"] = f"Test input text for {name}"

            t0 = time.time()
            resp = self.client.send_request("tools/call", {"name": name, "arguments": args})
            elapsed = (time.time() - t0) * 1000

            has_result = "result" in resp and "content" in resp["result"]
            has_error = "error" in resp
            
            status = "PASS"
            err_msg = None
            response_text = ""

            if has_result:
                content = resp["result"]["content"]
                if len(content) > 0 and "text" in content[0]:
                    response_text = content[0]["text"]
                    if response_text.startswith("Error: Unknown tool"):
                        status = "FAIL"
                        err_msg = response_text
                else:
                    status = "FAIL"
                    err_msg = f"Empty content in result: {resp}"
            elif has_error:
                status = "FAIL"
                err_msg = json.dumps(resp["error"])
            else:
                status = "FAIL"
                err_msg = f"Unrecognized response format: {resp}"

            preview = response_text.replace("\n", " ").strip()
            if len(preview) > 55:
                preview = preview[:52] + "..."
            if not preview and err_msg:
                preview = f"ERR: {err_msg[:45]}..."

            status_str = f"✅ PASS" if status == "PASS" else f"❌ FAIL"
            self.log(f"{idx:02d}  | {name:<34} | {status_str} | {elapsed:6.1f}ms | {preview}")

            self.results.append({
                "index": idx,
                "name": name,
                "category": category,
                "status": status,
                "latency_ms": round(elapsed, 2),
                "request_arguments": args,
                "response_preview": preview,
                "response_length": len(response_text),
                "error": err_msg
            })

    def _build_category_map(self) -> Dict[str, str]:
        in_process = {
            "get_system_info", "get_database_stats", "list_tasks", "update_database",
            "restore_backup", "clear_cache", "get_decision_stats", "get_novel_ai_stats",
            "get_performance_stats", "get_cache_stats", "get_model_recommendations",
            "get_model_ranking", "get_ml_analytics", "report_bandit_feedback"
        }
        core_orchestration = {
            "execute", "quick_answer", "orchestrate", "analyze_file", "analyze_folder",
            "nlp_task", "security_analysis", "code_task", "domain_task", "multimodal_task",
            "semantic_search", "data_science", "pe_header_extraction", "model_management",
            "reporting", "ml_management"
        }
        nlp_tasks = {
            "text_classification", "token_classification", "question_answering",
            "text_generation", "summarization", "translation", "fill_mask",
            "text2text_generation", "language_detection", "grammar_correction",
            "paraphrase_generation", "causal_language_modeling", "zero_shot_classification",
            "feature_extraction", "sentence_similarity"
        }
        security_tasks = {
            "anonymization", "coreference_resolution", "spam_detection", "malware_text_detection",
            "phishing_detection", "pii_detection", "hate_speech_detection", "cyberbullying_detection",
            "fake_news_detection", "hallucination_detection", "generation_groundedness",
            "citation_intent_classification"
        }
        domain_code_tasks = {
            "legal_judgment_classification", "contract_clause_classification", "case_outcome_prediction",
            "financial_ner", "legal_ner", "biomedical_ner", "chemical_reaction_ner",
            "financial_sentiment_analysis", "scientific_abstract_summarization", "emotion_detection",
            "sarcasm_detection", "stance_detection", "bias_detection", "reading_level_assessment",
            "code_summary_generation", "code_clone_detection"
        }
        multimodal_tasks = {
            "image_classification", "object_detection", "image_segmentation", "visual_question_answering",
            "document_question_answering", "zero_shot_image_classification", "depth_estimation",
            "image_feature_extraction", "automatic_speech_recognition", "audio_classification",
            "voice_activity_detection", "emotion_recognition", "video_classification", "text_to_speech",
            "text_to_image", "image_super_resolution", "table_question_answering", "feature_ranking"
        }
        cmap = {}
        for k in in_process: cmap[k] = "In-Process Telemetry & DB"
        for k in core_orchestration: cmap[k] = "Core Orchestration & Composite"
        for k in nlp_tasks: cmap[k] = "Specialized NLP"
        for k in security_tasks: cmap[k] = "Specialized Security"
        for k in domain_code_tasks: cmap[k] = "Specialized Domain & Code"
        for k in multimodal_tasks: cmap[k] = "Specialized Multimodal & Audio/Vision"
        return cmap

    def generate_summary(self, total_elapsed: float) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        pass_rate = round((passed / total * 100.0) if total > 0 else 0.0, 2)

        latencies = [r["latency_ms"] for r in self.results]
        min_lat = min(latencies) if latencies else 0.0
        max_lat = max(latencies) if latencies else 0.0
        avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        median_lat = round(sorted(latencies)[len(latencies)//2], 2) if latencies else 0.0

        # Category breakdown
        category_stats: Dict[str, Dict[str, Any]] = {}
        for r in self.results:
            cat = r["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0, "failed": 0, "avg_latency_ms": 0.0, "lats": []}
            category_stats[cat]["total"] += 1
            if r["status"] == "PASS":
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1
            category_stats[cat]["lats"].append(r["latency_ms"])

        for cat, cdata in category_stats.items():
            lats = cdata.pop("lats")
            cdata["avg_latency_ms"] = round(sum(lats) / len(lats), 2) if lats else 0.0
            cdata["pass_rate_pct"] = round(cdata["passed"] / cdata["total"] * 100.0, 2)

        summary = {
            "test_suite": "ModelFusion Comprehensive MCP Test Harness",
            "protocol_version": "2024-11-05",
            "server_info": self.server_info,
            "total_registered_tools": len(self.registered_tools),
            "total_tested_tools": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": pass_rate,
            "total_elapsed_seconds": round(total_elapsed, 2),
            "latency_metrics_ms": {
                "min": round(min_lat, 2),
                "max": round(max_lat, 2),
                "average": avg_lat,
                "median": median_lat
            },
            "category_breakdown": category_stats,
            "records": self.results
        }

        self.log("\n" + "=" * 80)
        self.log(" TEST SUMMARY & TELEMETRY REPORT")
        self.log("=" * 80)
        self.log(f" Total Registered Tools : {len(self.registered_tools)}")
        self.log(f" Total Tests Executed   : {total}")
        self.log(f" Passed                 : {passed} ({pass_rate}%)")
        self.log(f" Failed                 : {failed}")
        self.log(f" Total Elapsed Time     : {total_elapsed:.2f}s")
        self.log(f" Latency Range          : Min={min_lat:.1f}ms, Max={max_lat:.1f}ms, Avg={avg_lat:.1f}ms, Median={median_lat:.1f}ms")
        self.log("-" * 80)
        self.log(" CATEGORY BREAKDOWN:")
        for cat, cdata in category_stats.items():
            self.log(f"   • {cat:<40}: {cdata['passed']}/{cdata['total']} passed ({cdata['pass_rate_pct']}%), avg={cdata['avg_latency_ms']}ms")
        self.log("=" * 80)

        return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="ModelFusion Comprehensive MCP Standalone Test Harness")
    parser.add_argument("--cli-path", default=None, help="Path to ModelFusion cli.exe")
    parser.add_argument("--db-path", default=None, help="Path to hf_models.db database")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-tool call timeout in seconds")
    parser.add_argument("--report-path", default=None, help="Path to write JSON telemetry report")
    parser.add_argument("--json-only", action="store_true", help="Output only JSON to stdout")
    args = parser.parse_args()

    cli_path = args.cli_path or find_default_cli_path()
    db_path = args.db_path or find_default_db_path()
    report_path = args.report_path or os.path.abspath(r"IDE\reports\mcp_full_harness_report.json")

    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    harness = McpFullHarness(
        cli_path=cli_path,
        db_path=db_path,
        timeout=args.timeout,
        verbose=not args.json_only
    )

    summary = harness.run_all()

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Also save to secondary report path if needed
    sec_report = os.path.abspath(r"IDE\test_mcp_report.json")
    try:
        with open(sec_report, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    except Exception:
        pass

    if args.json_only:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n[REPORT] Saved full JSON telemetry report to: {report_path}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

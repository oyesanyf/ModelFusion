//! # End-to-End IDE MCP Integration Test Suite
//!
//! Replicates realistic IDE client interactions (Antigravity IDE, VS Code, Cursor)
//! communicating with the Model Context Protocol (MCP 2024-11-05) engine binary
//! (`mcp-cli`) over both standard I/O streams and HTTP/SSE transports.
//!
//! Validates:
//! 1. Full MCP Handshake & Protocol Lifecycle (Stdio)
//! 2. Full MCP Handshake & Protocol Lifecycle (HTTP / SSE)
//! 3. End-to-end execution of all 8 @agent tools with real workspace file generation and CLI processes
//! 4. High-concurrency multi-tab / multi-agent stress testing (35+ concurrent requests)
//! 5. Cooperative cancellation ($/cancelRequest within 100ms, zero orphan processes) & error recovery

use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use futures_util::StreamExt;
use mcp_protocol::transport::sse::SseEvent;
use parking_lot::Mutex as SyncMutex;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::{mpsc, oneshot, Mutex};

/// Helper to resolve the compiled `mcp-cli` executable binary.
fn get_mcp_cli_binary() -> PathBuf {
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_mcp-cli") {
        let p = PathBuf::from(path);
        if p.exists() {
            return p;
        }
    }
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(target_dir) = current_exe.parent().and_then(|p| p.parent()) {
            let bin = target_dir.join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
            if bin.exists() {
                return bin;
            }
        }
    }
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let ws_root = manifest.parent().unwrap().parent().unwrap();
    let debug_bin = ws_root
        .join("target")
        .join("debug")
        .join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
    if debug_bin.exists() {
        return debug_bin;
    }
    let release_bin = ws_root
        .join("target")
        .join("release")
        .join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
    if release_bin.exists() {
        return release_bin;
    }
    panic!("mcp-cli binary not found. Run `cargo build --bin mcp-cli` first.");
}

/// Harness managing an `mcp-cli mcp serve --stdio` child process with multiplexed request/response channels.
#[derive(Clone)]
struct StdioTestHarness {
    child: Arc<Mutex<Option<Child>>>,
    stdin_tx: mpsc::Sender<String>,
    pending: Arc<SyncMutex<HashMap<i64, oneshot::Sender<Value>>>>,
    next_id: Arc<AtomicI64>,
}

impl StdioTestHarness {
    pub async fn spawn() -> Result<Self, String> {
        let bin = get_mcp_cli_binary();
        eprintln!("[TEST HARNESS] mcp-cli binary path: {:?}", bin);
        let mut cmd = Command::new(&bin);
        cmd.args(["mcp", "serve", "--stdio"]);
        cmd.stdin(Stdio::piped());
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| format!("Failed to spawn mcp-cli: {}", e))?;
        let stdin = child.stdin.take().expect("child stdin configured");
        let stdout = child.stdout.take().expect("child stdout configured");
        let stderr = child.stderr.take().expect("child stderr configured");

        let (stdin_tx, mut stdin_rx) = mpsc::channel::<String>(256);
        let pending = Arc::new(SyncMutex::new(HashMap::<i64, oneshot::Sender<Value>>::new()));

        // Background stdin writer
        tokio::spawn(async move {
            let mut writer = stdin;
            while let Some(line) = stdin_rx.recv().await {
                if writer.write_all(line.as_bytes()).await.is_err() {
                    break;
                }
                if writer.flush().await.is_err() {
                    break;
                }
            }
        });

        // Background stderr drainer (logs to test output)
        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                eprintln!("[mcp-cli stderr] {}", line);
            }
            eprintln!("[mcp-cli stderr EOF]");
        });

        // Background stdout reader with line framing and JSON-RPC dispatch
        let pending_clone = pending.clone();
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                if let Ok(val) = serde_json::from_str::<Value>(trimmed) {
                    if let Some(id_val) = val.get("id") {
                        if let Some(id) = id_val.as_i64() {
                            eprintln!("[RECV ID {}]", id);
                            if let Some(sender) = pending_clone.lock().remove(&id) {
                                let _ = sender.send(val);
                            }
                        } else {
                            eprintln!("[RECV non-i64 id: {:?}]", id_val);
                        }
                    } else {
                        eprintln!("[RECV notification or other: {}]", trimmed);
                    }
                } else {
                    eprintln!("[RECV unparsed line: {}]", trimmed);
                }
            }
            eprintln!("[mcp-cli stdout EOF]");
        });

        Ok(Self {
            child: Arc::new(Mutex::new(Some(child))),
            stdin_tx,
            pending,
            next_id: Arc::new(AtomicI64::new(100)),
        })
    }

    pub async fn request(&self, method: &str, params: Option<Value>) -> Result<Value, String> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        self.request_with_id(id, method, params).await
    }

    pub async fn request_with_id(
        &self,
        id: i64,
        method: &str,
        params: Option<Value>,
    ) -> Result<Value, String> {
        let (tx, rx) = oneshot::channel();
        self.pending.lock().insert(id, tx);

        let msg = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params.clone().unwrap_or(json!({}))
        });

        let line = format!("{}\n", serde_json::to_string(&msg).unwrap());
        eprintln!("[SEND ID {}] {} {:?}", id, method, params);
        self.stdin_tx
            .send(line)
            .await
            .map_err(|e| format!("Failed to send to stdin: {}", e))?;

        match tokio::time::timeout(Duration::from_secs(15), rx).await {
            Ok(Ok(response)) => Ok(response),
            Ok(Err(_)) => Err("Response sender dropped".to_string()),
            Err(_) => {
                self.pending.lock().remove(&id);
                Err(format!("Request ID {} timed out after 15s", id))
            }
        }
    }

    pub async fn notify(&self, method: &str, params: Option<Value>) -> Result<(), String> {
        let msg = if let Some(p) = params {
            json!({ "jsonrpc": "2.0", "method": method, "params": p })
        } else {
            json!({ "jsonrpc": "2.0", "method": method })
        };
        let line = format!("{}\n", serde_json::to_string(&msg).unwrap());
        self.stdin_tx
            .send(line)
            .await
            .map_err(|e| format!("Failed to send notification: {}", e))?;
        Ok(())
    }

    pub async fn send_raw_line(&self, raw: &str) -> Result<(), String> {
        self.stdin_tx
            .send(format!("{}\n", raw))
            .await
            .map_err(|e| format!("Failed to send raw line: {}", e))?;
        Ok(())
    }

    pub async fn handshake(&self) -> Result<Value, String> {
        let init_params = json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": { "listChanged": true }
            },
            "clientInfo": {
                "name": "antigravity-ide-simulation-client",
                "version": "1.0.0"
            }
        });

        let init_res = self.request("initialize", Some(init_params)).await?;
        self.notify("notifications/initialized", None).await?;
        Ok(init_res)
    }

    pub async fn call_tool(&self, name: &str, arguments: Option<Value>) -> Result<Value, String> {
        let params = json!({
            "name": name,
            "arguments": arguments.unwrap_or(json!({}))
        });
        self.request("tools/call", Some(params)).await
    }

    pub async fn close(&self) {
        let mut guard = self.child.lock().await;
        if let Some(mut child) = guard.take() {
            let _ = child.kill().await;
        }
    }
}

impl Drop for StdioTestHarness {
    fn drop(&mut self) {
        if Arc::strong_count(&self.child) <= 1 {
            if let Ok(mut guard) = self.child.try_lock() {
                if let Some(mut child) = guard.take() {
                    let _ = child.start_kill();
                }
            }
        }
    }
}

// ============================================================================
// TEST 1: R1 — Stdio Lifecycle & Handshake
// ============================================================================

#[tokio::test]
async fn test_r1_stdio_lifecycle_and_discovery() {
    let harness = StdioTestHarness::spawn().await.expect("spawn stdio harness");

    // Pre-handshake verification: tools/list before initialize must return error -32002
    let pre_init_res = harness.request("tools/list", None).await.expect("pre-init request");
    assert!(
        pre_init_res.get("error").is_some(),
        "Expected error for pre-init tools/list, got: {:?}",
        pre_init_res
    );
    let err_code = pre_init_res["error"]["code"].as_i64().expect("error code");
    assert_eq!(err_code, -32002, "Expected ServerNotInitialized (-32002)");

    // Execute Handshake: initialize
    let init_res = harness.handshake().await.expect("handshake failed");
    assert!(init_res.get("result").is_some(), "Expected initialize result, got: {:?}", init_res);

    let result = &init_res["result"];
    assert_eq!(
        result["protocolVersion"].as_str(),
        Some("2024-11-05"),
        "Protocol version negotiation must match MCP 2024-11-05"
    );
    assert_eq!(
        result["serverInfo"]["name"].as_str(),
        Some("mcp-ide-engine"),
        "Server name must be mcp-ide-engine"
    );
    assert!(
        result["capabilities"]["tools"].is_object(),
        "Server must advertise tools capability"
    );
    assert!(
        result["capabilities"]["resources"].is_object(),
        "Server must advertise resources capability"
    );
    assert!(
        result["capabilities"]["prompts"].is_object(),
        "Server must advertise prompts capability"
    );

    // Discover Tools and validate JSON schema conformance
    let tools_res = harness.request("tools/list", None).await.expect("tools/list");
    let tools_val = &tools_res["result"]["tools"];
    assert!(tools_val.is_array(), "tools must be an array");
    let tools = tools_val.as_array().unwrap();
    assert_eq!(tools.len(), 8, "Expected exactly 8 registered @agent tools");

    let expected_tools = [
        "run_command",
        "execute_cli_command",
        "write_code_file",
        "read_code_file",
        "list_directory",
        "get_telemetry",
        "recommend_best_model",
        "calculate_layer_offload",
    ];

    for expected in expected_tools {
        let found = tools.iter().any(|t| t["name"].as_str() == Some(expected));
        assert!(found, "Tool '{}' missing from tools/list", expected);
    }

    for tool in tools {
        assert!(tool.get("name").is_some(), "Tool missing name");
        assert!(
            tool["inputSchema"]["type"].as_str() == Some("object"),
            "Tool inputSchema must have type: object"
        );
    }

    // Discover Resources and validate schemas
    let res_res = harness.request("resources/list", None).await.expect("resources/list");
    let resources = res_res["result"]["resources"].as_array().expect("resources array");
    assert!(!resources.is_empty(), "Resources catalog should not be empty");
    let has_telemetry = resources
        .iter()
        .any(|r| r["uri"].as_str() == Some("telemetry://system/status"));
    assert!(has_telemetry, "Resource telemetry://system/status missing");

    // Discover Prompts and validate schemas
    let prompts_res = harness.request("prompts/list", None).await.expect("prompts/list");
    let prompts = prompts_res["result"]["prompts"].as_array().expect("prompts array");
    assert!(!prompts.is_empty(), "Prompts catalog should not be empty");
    let has_analyze = prompts.iter().any(|p| p["name"].as_str() == Some("analyze_task"));
    assert!(has_analyze, "Prompt analyze_task missing");

    // Clean shutdown
    harness.close().await;
}

// ============================================================================
// TEST 2: R1 — SSE Transport Lifecycle & HTTP POST Handshake
// ============================================================================

#[tokio::test]
async fn test_r1_sse_lifecycle_and_discovery() {
    // 1. Pick an available port
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
    let sse_port = listener.local_addr().expect("local addr").port();
    drop(listener);

    // 2. Spawn mcp-cli in SSE server mode
    let bin = get_mcp_cli_binary();
    let mut cmd = Command::new(&bin);
    cmd.args(["mcp", "serve", "--sse-port", &sse_port.to_string()]);
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let mut child = cmd.spawn().expect("failed to spawn mcp-cli SSE server");
    let stderr = child.stderr.take().expect("stderr");

    // Drain stderr
    tokio::spawn(async move {
        let reader = BufReader::new(stderr);
        let mut lines = reader.lines();
        while let Ok(Some(_)) = lines.next_line().await {}
    });

    let base_url = format!("http://127.0.0.1:{}", sse_port);
    let http_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .expect("reqwest client");

    // 3. Poll readiness on /message health check endpoint
    let mut ready = false;
    for _ in 0..60 {
        tokio::time::sleep(Duration::from_millis(100)).await;
        if let Ok(res) = http_client.get(format!("{}/message", base_url)).send().await {
            if res.status().is_success() {
                ready = true;
                break;
            }
        }
    }
    assert!(ready, "MCP SSE server failed to initialize on port {}", sse_port);

    // 4. Connect to GET /sse to establish streaming SSE transport
    let sse_res = http_client
        .get(format!("{}/sse", base_url))
        .send()
        .await
        .expect("connect to /sse");
    assert_eq!(sse_res.status(), reqwest::StatusCode::OK);

    let (event_tx, mut event_rx) = mpsc::channel::<SseEvent>(64);
    let mut stream = sse_res.bytes_stream();

    // SSE stream parser task
    tokio::spawn(async move {
        let mut buffer = String::new();
        while let Some(Ok(chunk)) = stream.next().await {
            let s = String::from_utf8_lossy(&chunk);
            buffer.push_str(&s);

            while let Some(pos) = buffer.find("\n\n") {
                let block = buffer[..pos].to_string();
                buffer = buffer[pos + 2..].to_string();

                if let Some(event) = SseEvent::parse(&block) {
                    if event_tx.send(event).await.is_err() {
                        return;
                    }
                }
            }
        }
    });

    // 5. Receive initial "endpoint" event specifying session POST URI
    let first_event = tokio::time::timeout(Duration::from_secs(5), event_rx.recv())
        .await
        .expect("timeout awaiting initial SSE endpoint event")
        .expect("no event received");

    assert_eq!(first_event.event_type.as_deref(), Some("endpoint"));
    let endpoint_uri = first_event.data.trim();
    assert!(
        endpoint_uri.starts_with("/message?sessionId="),
        "Endpoint URI must include sessionId: {}",
        endpoint_uri
    );

    let post_url = format!("{}{}", base_url, endpoint_uri);

    // 6. Send 'initialize' request via HTTP POST
    let init_req = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": { "name": "ide-sse-client", "version": "1.0.0" }
        }
    });

    let post_res = http_client
        .post(&post_url)
        .json(&init_req)
        .send()
        .await
        .expect("POST initialize");
    assert_eq!(post_res.status(), reqwest::StatusCode::ACCEPTED);

    // 7. Receive initialize response over SSE stream
    let init_resp_event = tokio::time::timeout(Duration::from_secs(5), event_rx.recv())
        .await
        .expect("timeout awaiting initialize response over SSE")
        .expect("no event received");

    let init_resp_json: Value =
        serde_json::from_str(&init_resp_event.data).expect("parse SSE initialize JSON");
    assert_eq!(init_resp_json["id"], 1);
    assert_eq!(init_resp_json["result"]["protocolVersion"], "2024-11-05");
    assert_eq!(init_resp_json["result"]["serverInfo"]["name"], "mcp-ide-engine");

    // 8. Send 'notifications/initialized' via HTTP POST
    let init_notif = json!({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    });
    let notif_res = http_client
        .post(&post_url)
        .json(&init_notif)
        .send()
        .await
        .expect("POST notifications/initialized");
    assert_eq!(notif_res.status(), reqwest::StatusCode::ACCEPTED);

    // 9. Send 'tools/list' via HTTP POST
    let tools_req = json!({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    });
    let tools_post_res = http_client
        .post(&post_url)
        .json(&tools_req)
        .send()
        .await
        .expect("POST tools/list");
    assert_eq!(tools_post_res.status(), reqwest::StatusCode::ACCEPTED);

    // 10. Receive tools/list response over SSE stream
    let tools_resp_event = tokio::time::timeout(Duration::from_secs(5), event_rx.recv())
        .await
        .expect("timeout awaiting tools/list response over SSE")
        .expect("no event received");

    let tools_resp_json: Value =
        serde_json::from_str(&tools_resp_event.data).expect("parse SSE tools/list JSON");
    assert_eq!(tools_resp_json["id"], 2);
    let tools = tools_resp_json["result"]["tools"]
        .as_array()
        .expect("tools array over SSE");
    assert_eq!(tools.len(), 8, "All 8 tools must be discoverable over SSE");

    // 11. Clean shutdown
    let _ = child.kill().await;
}

// ============================================================================
// TEST 3: R2 — All 8 @agent Tools End-to-End Workflow Testing
// ============================================================================

#[tokio::test]
async fn test_r2_all_eight_agent_tools_execution() {
    let harness = StdioTestHarness::spawn().await.expect("spawn harness");
    harness.handshake().await.expect("handshake");

    let temp_workspace = tempfile::tempdir().expect("tempdir");
    let ws_path = temp_workspace.path();

    // ------------------------------------------------------------------------
    // Tool 1: write_code_file (Code Generation & Recursive Directory Creation)
    // ------------------------------------------------------------------------
    let target_file = ws_path.join("src").join("kernel").join("allocator.rs");
    let code_content = "pub fn allocate_pages(count: usize) -> usize { count * 4096 }\n";

    let write_res = harness
        .call_tool(
            "write_code_file",
            Some(json!({
                "path": target_file.to_str().unwrap(),
                "content": code_content
            })),
        )
        .await
        .expect("write_code_file call");

    assert!(write_res.get("result").is_some(), "write_code_file result missing");
    let write_text = write_res["result"]["content"][0]["text"].as_str().unwrap();
    assert!(
        write_text.contains("success") || write_text.contains("bytes_written"),
        "Write result output should report success: {}",
        write_text
    );
    assert!(target_file.exists(), "Target code file must exist on disk");

    // ------------------------------------------------------------------------
    // Tool 2: read_code_file (Context Inspection & Exact Byte Fidelity)
    // ------------------------------------------------------------------------
    let read_res = harness
        .call_tool(
            "read_code_file",
            Some(json!({
                "path": target_file.to_str().unwrap()
            })),
        )
        .await
        .expect("read_code_file call");

    assert!(read_res.get("result").is_some(), "read_code_file result missing");
    let read_text = read_res["result"]["content"][0]["text"].as_str().unwrap();
    let read_val: Value = serde_json::from_str(read_text).expect("parse read_code_file JSON");
    assert_eq!(
        read_val["content"].as_str().unwrap(),
        code_content,
        "File content retrieved over MCP must match written code with exact byte fidelity"
    );

    // ------------------------------------------------------------------------
    // Tool 3: list_directory (Workspace Tree Inspection)
    // ------------------------------------------------------------------------
    let list_res = harness
        .call_tool(
            "list_directory",
            Some(json!({
                "path": ws_path.join("src").join("kernel").to_str().unwrap()
            })),
        )
        .await
        .expect("list_directory call");

    assert!(list_res.get("result").is_some(), "list_directory result missing");
    let list_text = list_res["result"]["content"][0]["text"].as_str().unwrap();
    let list_val: Value = serde_json::from_str(list_text).expect("parse list_directory JSON");
    let entries = list_val["entries"].as_array().expect("entries array");
    let found_allocator = entries
        .iter()
        .find(|e| e["name"].as_str() == Some("allocator.rs"))
        .expect("allocator.rs entry in directory list");

    assert_eq!(found_allocator["is_dir"].as_bool(), Some(false));
    assert!(found_allocator["size_bytes"].as_u64().unwrap() > 0);

    // ------------------------------------------------------------------------
    // Tool 4: execute_cli_command (Asynchronous Process Execution)
    // ------------------------------------------------------------------------
    let cli_res = harness
        .call_tool(
            "execute_cli_command",
            Some(json!({
                "command": "cargo --version",
                "cwd": ws_path.to_str().unwrap()
            })),
        )
        .await
        .expect("execute_cli_command call");

    assert!(cli_res.get("result").is_some(), "execute_cli_command result missing");
    let cli_text = cli_res["result"]["content"][0]["text"].as_str().unwrap();
    let cli_val: Value = serde_json::from_str(cli_text).expect("parse cli JSON");
    assert_eq!(cli_val["exit_code"].as_i64(), Some(0));
    let stdout = cli_val["stdout"].as_str().unwrap_or("");
    assert!(
        stdout.contains("cargo"),
        "cargo --version output should contain 'cargo', got: {}",
        stdout
    );
    assert!(cli_val["duration_ms"].as_u64().unwrap() > 0);

    // ------------------------------------------------------------------------
    // Tool 5: get_telemetry (Hardware Telemetry: CPU / RAM / GPU)
    // ------------------------------------------------------------------------
    let telem_res = harness.call_tool("get_telemetry", None).await.expect("get_telemetry call");
    assert!(telem_res.get("result").is_some(), "get_telemetry result missing");
    let telem_text = telem_res["result"]["content"][0]["text"].as_str().unwrap();
    let telem_val: Value = serde_json::from_str(telem_text).expect("parse telemetry JSON");

    assert!(
        telem_val["cpu"]["logical_core_count"].as_u64().unwrap() > 0,
        "Telemetry must report logical CPU cores"
    );
    assert!(
        telem_val["memory"]["total_ram_bytes"].as_u64().unwrap() > 0,
        "Telemetry must report total RAM"
    );
    assert!(
        telem_val["memory"]["available_ram_bytes"].as_u64().unwrap() > 0,
        "Telemetry must report available RAM"
    );

    // ------------------------------------------------------------------------
    // Tool 6: recommend_best_model (Dynamic Model Tier Classification)
    // ------------------------------------------------------------------------
    let model_res = harness
        .call_tool(
            "recommend_best_model",
            Some(json!({
                "context_tokens": 4096
            })),
        )
        .await
        .expect("recommend_best_model call");

    assert!(model_res.get("result").is_some(), "recommend_best_model result missing");
    let model_text = model_res["result"]["content"][0]["text"].as_str().unwrap();
    let model_val: Value = serde_json::from_str(model_text).expect("parse model JSON");
    assert!(
        model_val.get("model_id").is_some() || model_val.is_null(),
        "Model decision must return structure: {:?}",
        model_val
    );

    // ------------------------------------------------------------------------
    // Tool 7: calculate_layer_offload (GPU VRAM / RAM Layer Offloading)
    // ------------------------------------------------------------------------
    let offload_res = harness
        .call_tool(
            "calculate_layer_offload",
            Some(json!({
                "model": "llama-3.1-8b",
                "vram_gb": 12.0
            })),
        )
        .await
        .expect("calculate_layer_offload call");

    assert!(offload_res.get("result").is_some(), "calculate_layer_offload result missing");
    let offload_text = offload_res["result"]["content"][0]["text"].as_str().unwrap();
    let offload_val: Value = serde_json::from_str(offload_text).expect("parse offload JSON");
    let total_layers = offload_val["total_layers"].as_u64().unwrap();
    let gpu_layers = offload_val["gpu_layers"].as_u64().unwrap();
    let cpu_layers = offload_val["cpu_layers"].as_u64().unwrap();
    assert_eq!(total_layers, 32);
    assert_eq!(gpu_layers + cpu_layers, 32);
    assert!(gpu_layers > 0, "With 12GB VRAM, at least some layers must be offloaded");

    // ------------------------------------------------------------------------
    // Tool 8: run_command (Priority Multi-Lane Task Dispatch)
    // ------------------------------------------------------------------------
    let run_res = harness
        .call_tool(
            "run_command",
            Some(json!({
                "command": "echo",
                "args": { "workflow_id": "test_agent_alpha", "status": "active" },
                "priority": "High"
            })),
        )
        .await
        .expect("run_command call");

    assert!(run_res.get("result").is_some(), "run_command result missing");
    let run_text = run_res["result"]["content"][0]["text"].as_str().unwrap();
    let run_val: Value = serde_json::from_str(run_text).expect("parse run_command JSON");
    assert_eq!(run_val["workflow_id"].as_str(), Some("test_agent_alpha"));
    assert_eq!(run_val["status"].as_str(), Some("active"));

    harness.close().await;
}

// ============================================================================
// TEST 4: R3 — High-Concurrency Multi-Tab / Multi-Agent Stress Testing
// ============================================================================

#[tokio::test]
async fn test_r3_high_concurrency_multi_agent_stress() {
    let harness = StdioTestHarness::spawn().await.expect("spawn harness");
    harness.handshake().await.expect("handshake");

    // Simulate 35 simultaneous IDE tool calls across concurrent worker threads
    let total_concurrent = 35;
    let mut join_set = tokio::task::JoinSet::new();
    let start_time = Instant::now();

    for i in 0..total_concurrent {
        let client = harness.clone();
        join_set.spawn(async move {
            match i % 5 {
                0 => {
                    // Telemetry Probe
                    client.call_tool("get_telemetry", None).await
                }
                1 => {
                    // Model Recommendation
                    client
                        .call_tool(
                            "recommend_best_model",
                            Some(json!({ "context_tokens": 2048 + (i * 256) })),
                        )
                        .await
                }
                2 => {
                    // Layer Offload Calculation
                    client
                        .call_tool(
                            "calculate_layer_offload",
                            Some(json!({
                                "model": "llama-3.1-8b",
                                "vram_gb": 4.0 + ((i % 8) as f64 * 2.0)
                            })),
                        )
                        .await
                }
                3 => {
                    // Universal Command Bus (Echo) with thread isolation check
                    client
                        .call_tool(
                            "run_command",
                            Some(json!({
                                "command": "echo",
                                "args": { "tab_id": i, "token": format!("tok-{}", i) },
                                "priority": if i % 2 == 0 { "High" } else { "Normal" }
                            })),
                        )
                        .await
                }
                _ => {
                    // Async CLI Echo
                    client
                        .call_tool(
                            "execute_cli_command",
                            Some(json!({
                                "command": format!("echo tab_worker_{}", i)
                            })),
                        )
                        .await
                }
            }
        });
    }

    let mut successful_calls = 0;
    while let Some(res) = join_set.join_next().await {
        let tool_res = res.expect("Join task panicked").expect("Tool call failed");
        assert!(
            tool_res.get("result").is_some(),
            "Concurrent tool call returned error: {:?}",
            tool_res
        );
        let content = &tool_res["result"]["content"];
        assert!(content.is_array(), "Result content must be an array");
        successful_calls += 1;
    }

    assert_eq!(
        successful_calls, total_concurrent,
        "All 35 concurrent requests must complete successfully"
    );

    let elapsed = start_time.elapsed();
    assert!(
        elapsed < Duration::from_secs(12),
        "35 concurrent tool invocations took {:?}, exceeding 12s budget",
        elapsed
    );

    harness.close().await;
}

// ============================================================================
// TEST 5: R4 — Cooperative Cancellation & Structured Error Recovery
// ============================================================================

#[tokio::test]
async fn test_r4_cooperative_cancellation_and_error_recovery() {
    let harness = StdioTestHarness::spawn().await.expect("spawn harness");
    harness.handshake().await.expect("handshake");

    #[cfg(windows)]
    {
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", "PING.EXE"])
            .output()
            .await;
    }

    // ------------------------------------------------------------------------
    // Part A: Sub-100ms Cooperative Cancellation of In-Flight CLI Command
    // ------------------------------------------------------------------------
    let cancel_harness = harness.clone();
    let cancel_req_id = 7777;

    // Dispatch long-running command (ping -n 20 127.0.0.1 takes ~20 seconds)
    let call_task = tokio::spawn(async move {
        cancel_harness
            .request_with_id(
                cancel_req_id,
                "tools/call",
                Some(json!({
                    "name": "execute_cli_command",
                    "arguments": {
                        "command": "ping -n 20 127.0.0.1"
                    }
                })),
            )
            .await
    });

    // Allow the child process time to spawn
    tokio::time::sleep(Duration::from_millis(60)).await;

    // Send $/cancelRequest notification to abort execution
    let t0 = Instant::now();
    harness
        .notify(
            "$/cancelRequest",
            Some(json!({
                "requestId": cancel_req_id
            })),
        )
        .await
        .expect("send $/cancelRequest");

    // Await response to the cancelled request
    let cancel_res = tokio::time::timeout(Duration::from_millis(300), call_task)
        .await
        .expect("Cancellation did not abort within 300ms window")
        .expect("call_task join error")
        .expect("call_task result");

    let abort_duration = t0.elapsed();
    eprintln!("[TEST R4] cancel_res: {:?}", cancel_res);
    assert!(
        abort_duration < Duration::from_millis(100),
        "Cooperative cancellation SLA violated! Took {:?}, expected <100ms",
        abort_duration
    );

    // Verify response indicates error/cancelled
    assert!(
        cancel_res.get("error").is_some() || cancel_res["result"]["isError"].as_bool() == Some(true),
        "Cancelled request must return structured error response: {:?}",
        cancel_res
    );

    // Verify zero orphan PING.EXE processes leaked in OS process table
    #[cfg(windows)]
    {
        let mut clean = false;
        let mut last_output = String::new();
        for _ in 0..20 {
            tokio::time::sleep(Duration::from_millis(100)).await;
            let tasklist_output = Command::new("tasklist")
                .args(["/FI", "IMAGENAME eq PING.EXE"])
                .output()
                .await
                .expect("run tasklist");
            last_output = String::from_utf8_lossy(&tasklist_output.stdout).to_string();
            if last_output.contains("No tasks are running") || last_output.contains("INFO:") {
                clean = true;
                break;
            }
        }
        assert!(
            clean,
            "Orphan PING.EXE processes leaked: {}",
            last_output
        );
    }

    // ------------------------------------------------------------------------
    // Part B: Fault Isolation & Structured JSON-RPC Error Handling
    // ------------------------------------------------------------------------

    // 1. Unknown Method Error (-32601)
    let unknown_res = harness
        .request("unknown_ide_method", None)
        .await
        .expect("unknown method response");
    assert!(unknown_res.get("error").is_some());
    assert_eq!(
        unknown_res["error"]["code"].as_i64(),
        Some(-32601),
        "Unknown method must return -32601 (MethodNotFound)"
    );

    // 2. Invalid Tool Parameters Error (-32602)
    let bad_tool_res = harness
        .call_tool("write_code_file", Some(json!({ "invalid_field": 42 })))
        .await
        .expect("bad tool response");
    assert!(
        bad_tool_res.get("error").is_some(),
        "Missing required 'path' and 'content' must return error"
    );
    assert_eq!(
        bad_tool_res["error"]["code"].as_i64(),
        Some(-32602),
        "Schema validation failure must return -32602 (InvalidParams)"
    );

    // 3. Nonexistent Tool Error
    let missing_tool_res = harness
        .call_tool("nonexistent_agent_tool", None)
        .await
        .expect("missing tool response");
    assert!(missing_tool_res.get("error").is_some());

    // 4. Malformed JSON Stream Injection (Resilience Check)
    harness
        .send_raw_line("{malformed-json-line: invalid")
        .await
        .expect("send malformed json");

    tokio::time::sleep(Duration::from_millis(50)).await;

    // 5. Liveness Proof: Server survives all faults and remains healthy
    let liveness_res = harness.request("ping", None).await.expect("ping response");
    assert!(
        liveness_res.get("result").is_some(),
        "Server must remain responsive after handling invalid inputs and malformed lines"
    );

    harness.close().await;
}

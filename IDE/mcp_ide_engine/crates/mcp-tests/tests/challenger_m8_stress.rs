//! # Challenger M8 Stress & Adversarial Test Harness
//!
//! Empirically challenges and stress-tests:
//! 1. Exact byte fidelity across UTF-8, CRLF, empty files, large files, and deep directory trees
//! 2. Edge case CLI executions (non-zero exits, stderr streams, non-existent binaries)
//! 3. Resource & Layer offload boundaries (0GB VRAM vs 100GB VRAM, extreme context tokens)
//! 4. Process lifecycle stability under rapid sequential requests

use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use parking_lot::Mutex as SyncMutex;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::{mpsc, oneshot, Mutex};

fn get_mcp_cli_binary() -> PathBuf {
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_mcp-cli") {
        let p = PathBuf::from(path);
        if p.exists() {
            return p;
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
    panic!("mcp-cli binary not found.");
}

#[derive(Clone)]
struct ChallengerHarness {
    child: Arc<Mutex<Option<Child>>>,
    stdin_tx: mpsc::Sender<String>,
    pending: Arc<SyncMutex<HashMap<i64, oneshot::Sender<Value>>>>,
    next_id: Arc<AtomicI64>,
}

impl ChallengerHarness {
    pub async fn spawn() -> Result<Self, String> {
        let bin = get_mcp_cli_binary();
        let mut cmd = Command::new(&bin);
        cmd.args(["mcp", "serve", "--stdio"]);
        cmd.stdin(Stdio::piped());
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| format!("Spawn failed: {}", e))?;
        let stdin = child.stdin.take().unwrap();
        let stdout = child.stdout.take().unwrap();
        let stderr = child.stderr.take().unwrap();

        let (stdin_tx, mut stdin_rx) = mpsc::channel::<String>(256);
        let pending: Arc<SyncMutex<HashMap<i64, oneshot::Sender<Value>>>> =
            Arc::new(SyncMutex::new(HashMap::new()));

        tokio::spawn(async move {
            let mut writer = stdin;
            while let Some(line) = stdin_rx.recv().await {
                if writer.write_all(line.as_bytes()).await.is_err() || writer.flush().await.is_err() {
                    break;
                }
            }
        });

        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            while let Ok(Some(_)) = lines.next_line().await {}
        });

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
                    if let Some(id) = val.get("id").and_then(|i| i.as_i64()) {
                        if let Some(sender) = pending_clone.lock().remove(&id) {
                            let _ = sender.send(val);
                        }
                    }
                }
            }
        });

        let harness = Self {
            child: Arc::new(Mutex::new(Some(child))),
            stdin_tx,
            pending,
            next_id: Arc::new(AtomicI64::new(500)),
        };

        harness.handshake().await?;
        Ok(harness)
    }

    pub async fn request(&self, method: &str, params: Option<Value>) -> Result<Value, String> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let (tx, rx) = oneshot::channel();
        self.pending.lock().insert(id, tx);

        let msg = json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params.unwrap_or(json!({}))
        });

        let line = format!("{}\n", serde_json::to_string(&msg).unwrap());
        self.stdin_tx.send(line).await.map_err(|e| e.to_string())?;

        match tokio::time::timeout(Duration::from_secs(10), rx).await {
            Ok(Ok(resp)) => Ok(resp),
            Ok(Err(_)) => Err("Sender dropped".to_string()),
            Err(_) => {
                self.pending.lock().remove(&id);
                Err(format!("Request {} timed out", id))
            }
        }
    }

    pub async fn handshake(&self) -> Result<(), String> {
        let init_params = json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": { "name": "challenger-client", "version": "1.0.0" }
        });
        self.request("initialize", Some(init_params)).await?;

        let notif = json!({ "jsonrpc": "2.0", "method": "notifications/initialized" });
        self.stdin_tx
            .send(format!("{}\n", serde_json::to_string(&notif).unwrap()))
            .await
            .map_err(|e| e.to_string())?;
        Ok(())
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

impl Drop for ChallengerHarness {
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

#[tokio::test]
async fn test_adversarial_byte_fidelity_and_code_generation() {
    let harness = ChallengerHarness::spawn().await.expect("spawn harness");
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let root = temp_dir.path();

    // 1. CRLF line endings fidelity
    let crlf_file = root.join("src").join("crlf.rs");
    let crlf_content = "line1\r\nline2\r\nline3\r\n";
    let write_res = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": crlf_file.to_str().unwrap(), "content": crlf_content })),
        )
        .await
        .expect("write crlf");
    assert!(write_res.get("result").is_some());

    let read_res = harness
        .call_tool("read_code_file", Some(json!({ "path": crlf_file.to_str().unwrap() })))
        .await
        .expect("read crlf");
    let text = read_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["content"].as_str().unwrap(), crlf_content, "CRLF byte fidelity mismatch");

    // 2. Unicode, Emojis, and Special Characters fidelity
    let unicode_file = root.join("src").join("unicode.txt");
    let unicode_content = "🦀 Rust MCP Engine 🚀\n日本語: こんにちは世界\nMath: ∑_{i=0}^n x_i = ∫_0^∞ f(t)dt\nQuotes: \"hello\" \\ 'world'\n";
    let write_uni = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": unicode_file.to_str().unwrap(), "content": unicode_content })),
        )
        .await
        .expect("write unicode");
    assert!(write_uni.get("result").is_some());

    let read_uni = harness
        .call_tool("read_code_file", Some(json!({ "path": unicode_file.to_str().unwrap() })))
        .await
        .expect("read unicode");
    let text = read_uni["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["content"].as_str().unwrap(), unicode_content, "Unicode byte fidelity mismatch");

    // 3. Empty file write & read
    let empty_file = root.join("empty.txt");
    let write_empty = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": empty_file.to_str().unwrap(), "content": "" })),
        )
        .await
        .expect("write empty");
    assert!(write_empty.get("result").is_some());

    let read_empty = harness
        .call_tool("read_code_file", Some(json!({ "path": empty_file.to_str().unwrap() })))
        .await
        .expect("read empty");
    let text = read_empty["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["content"].as_str().unwrap(), "", "Empty file content mismatch");

    // 4. Overwrite existing file
    let overwrite_content = "OVERWRITTEN_CONTENT_VERSION_2";
    let write_over = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": empty_file.to_str().unwrap(), "content": overwrite_content })),
        )
        .await
        .expect("overwrite");
    assert!(write_over.get("result").is_some());

    let read_over = harness
        .call_tool("read_code_file", Some(json!({ "path": empty_file.to_str().unwrap() })))
        .await
        .expect("read overwrite");
    let text = read_over["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["content"].as_str().unwrap(), overwrite_content, "Overwrite content mismatch");

    // 5. Deep directory creation (10 levels deep)
    let deep_file = root
        .join("l1")
        .join("l2")
        .join("l3")
        .join("l4")
        .join("l5")
        .join("l6")
        .join("deep.rs");
    let deep_content = "pub fn deep() -> bool { true }\n";
    let write_deep = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": deep_file.to_str().unwrap(), "content": deep_content })),
        )
        .await
        .expect("write deep");
    assert!(write_deep.get("result").is_some());
    assert!(deep_file.exists());

    // 6. Large code file (64KB payload)
    let mut large_buf = String::with_capacity(65536);
    for i in 0..1024 {
        large_buf.push_str(&format!("pub fn func_{:04}() -> u32 {{ {} }}\n", i, i));
    }
    let large_file = root.join("src").join("large.rs");
    let write_large = harness
        .call_tool(
            "write_code_file",
            Some(json!({ "path": large_file.to_str().unwrap(), "content": &large_buf })),
        )
        .await
        .expect("write large");
    assert!(write_large.get("result").is_some());

    let read_large = harness
        .call_tool("read_code_file", Some(json!({ "path": large_file.to_str().unwrap() })))
        .await
        .expect("read large");
    let text = read_large["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["content"].as_str().unwrap().len(), large_buf.len());
    assert_eq!(val["content"].as_str().unwrap(), large_buf);

    harness.close().await;
}

#[tokio::test]
async fn test_adversarial_cli_execution_and_error_containment() {
    let harness = ChallengerHarness::spawn().await.expect("spawn harness");

    // 1. CLI with non-zero exit code: cmd /C exit 42 (Windows) or sh -c 'exit 42'
    #[cfg(windows)]
    let cmd = "cmd /C exit 42";
    #[cfg(not(windows))]
    let cmd = "sh -c 'exit 42'";

    let cli_res = harness
        .call_tool("execute_cli_command", Some(json!({ "command": cmd })))
        .await
        .expect("execute_cli_command call");

    assert!(cli_res.get("result").is_some());
    let text = cli_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["exit_code"].as_i64(), Some(42));
    assert_eq!(cli_res["result"]["isError"].as_bool(), Some(true));

    // 2. CLI with stderr output
    #[cfg(windows)]
    let err_cmd = "cmd /C \"echo ERROR_STREAM_MESSAGE 1>&2\"";
    #[cfg(not(windows))]
    let err_cmd = "sh -c 'echo ERROR_STREAM_MESSAGE >&2'";

    let stderr_res = harness
        .call_tool("execute_cli_command", Some(json!({ "command": err_cmd })))
        .await
        .expect("execute_cli_command stderr call");

    assert!(stderr_res.get("result").is_some());
    let text = stderr_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    let stderr_text = val["stderr"].as_str().unwrap();
    assert!(
        stderr_text.contains("ERROR_STREAM_MESSAGE"),
        "Expected stderr to contain message, got: {}",
        stderr_text
    );

    // 3. Execution of nonexistent command does not crash server
    let missing_cmd = harness
        .call_tool("execute_cli_command", Some(json!({ "command": "nonexistent_cli_bin_xyz_999" })))
        .await
        .expect("missing command call");
    // Should return result with non-zero exit or error, but server remains alive
    assert!(missing_cmd.get("result").is_some() || missing_cmd.get("error").is_some());

    // 4. Liveness check: server is fully responsive after error conditions
    let live = harness.call_tool("run_command", Some(json!({ "command": "echo", "args": { "live": true } }))).await.expect("ping");
    assert!(live.get("result").is_some());

    harness.close().await;
}

#[tokio::test]
async fn test_adversarial_hardware_and_offload_boundaries() {
    let harness = ChallengerHarness::spawn().await.expect("spawn harness");

    // 1. calculate_layer_offload with 0.0 GB VRAM -> Pure CPU offload
    let zero_res = harness
        .call_tool(
            "calculate_layer_offload",
            Some(json!({ "model": "llama-3.1-8b", "vram_gb": 0.0 })),
        )
        .await
        .expect("offload 0gb");
    assert!(zero_res.get("result").is_some());
    let text = zero_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["gpu_layers"].as_u64(), Some(0), "With 0GB VRAM, GPU layers must be 0");
    assert_eq!(val["cpu_layers"].as_u64(), Some(32), "With 0GB VRAM, CPU layers must be 32");

    // 2. calculate_layer_offload with 80.0 GB VRAM -> Pure GPU offload
    let max_res = harness
        .call_tool(
            "calculate_layer_offload",
            Some(json!({ "model": "llama-3.1-8b", "vram_gb": 80.0 })),
        )
        .await
        .expect("offload 80gb");
    assert!(max_res.get("result").is_some());
    let text = max_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["gpu_layers"].as_u64(), Some(32), "With 80GB VRAM, GPU layers must be 32");
    assert_eq!(val["cpu_layers"].as_u64(), Some(0), "With 80GB VRAM, CPU layers must be 0");

    // 3. calculate_layer_offload with 70B model
    let model_70b_res = harness
        .call_tool(
            "calculate_layer_offload",
            Some(json!({ "model": "llama-3.3-70b", "vram_gb": 24.0 })),
        )
        .await
        .expect("offload 70b");
    assert!(model_70b_res.get("result").is_some());
    let text = model_70b_res["result"]["content"][0]["text"].as_str().unwrap();
    let val: Value = serde_json::from_str(text).unwrap();
    assert_eq!(val["total_layers"].as_u64(), Some(80), "LLaMA 70B has 80 layers");
    let gpu = val["gpu_layers"].as_u64().unwrap();
    let cpu = val["cpu_layers"].as_u64().unwrap();
    assert_eq!(gpu + cpu, 80);

    // 4. recommend_best_model with small context vs huge context
    let small_ctx = harness
        .call_tool("recommend_best_model", Some(json!({ "context_tokens": 512 })))
        .await
        .expect("recommend small");
    assert!(small_ctx.get("result").is_some());

    let huge_ctx = harness
        .call_tool("recommend_best_model", Some(json!({ "context_tokens": 131072 })))
        .await
        .expect("recommend huge");
    assert!(huge_ctx.get("result").is_some());

    harness.close().await;
}

#[tokio::test]
async fn test_adversarial_rapid_sequential_burst() {
    let harness = ChallengerHarness::spawn().await.expect("spawn harness");

    // Rapidly execute 30 sequential tool calls over stdio pipe
    for i in 0..30 {
        let res = harness
            .call_tool("run_command", Some(json!({ "command": "echo", "args": { "seq": i } })))
            .await
            .expect("seq call");
        assert!(res.get("result").is_some());
        let text = res["result"]["content"][0]["text"].as_str().unwrap();
        let val: Value = serde_json::from_str(text).unwrap();
        assert_eq!(val["seq"].as_i64(), Some(i));
    }

    harness.close().await;
}

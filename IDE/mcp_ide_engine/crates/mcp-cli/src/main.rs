//! # MCP IDE Engine — Unified CLI Binary & Runtime Entrypoint

pub mod cli;
pub mod repl;
pub mod sse_server;

use clap::Parser;
use cli::{
    BenchArgs, Cli, Commands, McpArgs, McpPromptsAction, McpResourcesAction,
    McpSubcommands, McpToolsAction, ReplArgs, ResourceArgs, ResourceSubcommands,
    RunArgs, ServeArgs, TuiArgs,
};
use colored::Colorize;
use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskOutput, TaskPriority};
use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
use mcp_core::scheduler::MultiLaneScheduler;
use mcp_core::telemetry::EngineTelemetry;
use mcp_protocol::server::McpServer;
use mcp_protocol::types::{CallToolResult, PromptArgument, Role};
use mcp_resource::selector::{ModelSelector, ModelSpec};
use mcp_resource::telemetry::ResourceMonitor;
use mcp_tui::App;
use mcp_web::server::{AppState, run_server};
use repl::ReplEngine;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Cli::parse();

    // Initialize structured logging (to stderr so stdout remains clean JSON-RPC stream)
    let filter = match args.verbose {
        0 => "info,mcp_ide=info",
        1 => "debug,mcp_ide=debug",
        _ => "trace,mcp_ide=trace",
    };
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .with_writer(std::io::stderr)
        .init();

    // Configure and initialize Multithreaded Core Engine
    let compute_workers = args.compute_workers.unwrap_or_else(|| num_cpus::get_physical().max(2));
    let runtime = Arc::new(EngineRuntime::from_handle(tokio::runtime::Handle::current(), compute_workers)?);
    let telemetry = Arc::new(EngineTelemetry::new());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    // Register built-in commands
    register_builtin_commands(&registry)?;

    let worker_count = args.workers.unwrap_or_else(num_cpus::get);
    let dispatcher = TaskDispatcher::new(
        registry.clone(),
        scheduler.clone(),
        runtime.clone(),
        telemetry.clone(),
        worker_count,
    );

    // Initialize Resource Monitor
    let resource_monitor = Arc::new(ResourceMonitor::new(Duration::from_millis(250)));

    // Initialize MCP Server with standard tools & resources
    let mcp_server = Arc::new(setup_default_mcp_server(&dispatcher, &resource_monitor)?);

    // Route Subcommands
    match args.command {
        Some(Commands::Run(run_args)) => handle_run(run_args, &dispatcher, args.json).await?,
        Some(Commands::Mcp(mcp_args)) => handle_mcp(mcp_args, &mcp_server, args.json).await?,
        Some(Commands::Resource(res_args)) => handle_resource(res_args, &resource_monitor, args.json).await?,
        Some(Commands::Tui(tui_args)) => handle_tui(tui_args, dispatcher, resource_monitor, mcp_server).await?,
        Some(Commands::Serve(serve_args)) => handle_serve(serve_args, dispatcher, resource_monitor, mcp_server).await?,
        Some(Commands::Repl(repl_args)) => handle_repl(repl_args, dispatcher, resource_monitor, mcp_server).await?,
        Some(Commands::Bench(bench_args)) => handle_bench(bench_args, &dispatcher, args.json).await?,
        None => {
            // Default action: Launch interactive Reedline REPL
            handle_repl(ReplArgs { history_file: None }, dispatcher, resource_monitor, mcp_server).await?;
        }
    }

    Ok(())
}

static ACTIVE_CLI_PIDS: std::sync::LazyLock<parking_lot::Mutex<std::collections::HashMap<mcp_core::scheduler::TaskId, u32>>> =
    std::sync::LazyLock::new(|| parking_lot::Mutex::new(std::collections::HashMap::new()));

pub static LAST_SPAWNED_CLI_PID: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);

struct ProcessTreeKillGuard {
    task_id: mcp_core::scheduler::TaskId,
    child: tokio::process::Child,
    child_pid: Option<u32>,
    completed: bool,
}

impl Drop for ProcessTreeKillGuard {
    fn drop(&mut self) {
        if !self.completed {
            if let Some(pid) = self.child_pid {
                ACTIVE_CLI_PIDS.lock().remove(&self.task_id);
                #[cfg(windows)]
                {
                    tokio::spawn(async move {
                        let _ = tokio::process::Command::new("taskkill")
                            .args(&["/F", "/T", "/PID", &pid.to_string()])
                            .stdin(std::process::Stdio::null())
                            .stdout(std::process::Stdio::null())
                            .stderr(std::process::Stdio::null())
                            .output()
                            .await;
                    });
                }
            }
            let _ = self.child.start_kill();
        }
    }
}

async fn wait_child_output(child: &mut tokio::process::Child) -> std::io::Result<std::process::Output> {
    use tokio::io::AsyncReadExt;
    let stdout_pipe = child.stdout.take();
    let stderr_pipe = child.stderr.take();

    let mut stdout_buf = Vec::new();
    let mut stderr_buf = Vec::new();

    let (status_res, _, _) = tokio::join!(
        child.wait(),
        async {
            if let Some(mut p) = stdout_pipe {
                let _ = p.read_to_end(&mut stdout_buf).await;
            }
        },
        async {
            if let Some(mut p) = stderr_pipe {
                let _ = p.read_to_end(&mut stderr_buf).await;
            }
        },
    );

    let status = status_res?;
    Ok(std::process::Output {
        status,
        stdout: stdout_buf,
        stderr: stderr_buf,
    })
}

fn register_builtin_commands(registry: &CommandRegistry) -> anyhow::Result<()> {
    // 1. Echo Command
    registry.register_fn(
        "echo",
        "Echoes input arguments directly",
        "utility",
        TaskPriority::Normal,
        |_ctx, args| async move { Ok(TaskOutput::success(args)) },
    )?;

    // 2. Sleep / Async Delay Command
    registry.register_fn(
        "sleep",
        "Asynchronously sleeps for specified duration",
        "utility",
        TaskPriority::Normal,
        |_ctx, args| async move {
            let ms = args["duration_ms"].as_u64().unwrap_or(100);
            tokio::time::sleep(Duration::from_millis(ms)).await;
            Ok(TaskOutput::success(json!({ "slept_ms": ms })))
        },
    )?;

    // 3. Rayon Compute Hash
    registry.register_fn(
        "compute_hash",
        "Computes CPU-intensive rolling hash on Rayon compute pool",
        "compute",
        TaskPriority::Normal,
        |ctx, args| async move {
            let n = args["iterations"].as_u64().unwrap_or(50_000);
            let result = ctx
                .runtime
                .spawn_compute(move || {
                    let mut val: u64 = 0x517cc1b727220a95;
                    for i in 0..n {
                        val = val.rotate_left(5) ^ i.wrapping_mul(0x9e3779b97f4a7c15);
                    }
                    val
                })
                .await
                .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(e.to_string()))?;

            Ok(TaskOutput::success(json!({ "iterations": n, "hash": format!("{:#x}", result) })))
        },
    )?;

    // 4. Asynchronous Shell / CLI Command Execution
    registry.register_fn(
        "execute_cli",
        "Executes a system shell or CLI command non-blockingly on worker thread",
        "system",
        TaskPriority::High,
        |ctx, args| async move {
            let cmd_str = args["command"].as_str().unwrap_or("");
            let cwd = args["cwd"].as_str();
            if cmd_str.trim().is_empty() {
                return Err(mcp_core::registry::TaskError::InvalidArguments("Empty command".to_string()));
            }

            let parts: Vec<&str> = cmd_str.split_whitespace().collect();
            let is_cmd_builtin = !parts.is_empty() && matches!(
                parts[0].to_ascii_lowercase().as_str(),
                "dir" | "copy" | "move" | "del" | "type" | "cls" | "echo" | "set" | "cd" | "md" | "rd"
            );

            #[cfg(windows)]
            let mut proc = if is_cmd_builtin {
                let mut c = tokio::process::Command::new("cmd");
                c.args(&["/C", cmd_str]);
                c
            } else if !parts.is_empty() {
                let mut c = tokio::process::Command::new(parts[0]);
                c.args(&parts[1..]);
                c
            } else {
                let mut c = tokio::process::Command::new("cmd");
                c.args(&["/C", cmd_str]);
                c
            };

            #[cfg(not(windows))]
            let mut proc = tokio::process::Command::new("sh");
            #[cfg(not(windows))]
            proc.args(&["-c", cmd_str]);

            if let Some(dir) = cwd {
                proc.current_dir(dir);
            }

            // Ensure OS process is deterministically killed if aborted or dropped
            proc.kill_on_drop(true);
            proc.stdout(std::process::Stdio::piped());
            proc.stderr(std::process::Stdio::piped());

            let child = proc
                .spawn()
                .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to spawn command: {}", e)))?;
            let child_pid = child.id();
            if let Some(pid) = child_pid {
                ACTIVE_CLI_PIDS.lock().insert(ctx.task_id, pid);
                LAST_SPAWNED_CLI_PID.store(pid, std::sync::atomic::Ordering::SeqCst);
            }

            let mut guard = ProcessTreeKillGuard {
                task_id: ctx.task_id,
                child,
                child_pid,
                completed: false,
            };

            let start = std::time::Instant::now();
            tokio::select! {
                _ = ctx.cancellation_token.cancelled() => {
                    #[cfg(windows)]
                    if let Some(pid) = child_pid {
                        ACTIVE_CLI_PIDS.lock().remove(&ctx.task_id);
                        tokio::spawn(async move {
                            let _ = tokio::process::Command::new("taskkill")
                                .args(&["/F", "/T", "/PID", &pid.to_string()])
                                .stdin(std::process::Stdio::null())
                                .stdout(std::process::Stdio::null())
                                .stderr(std::process::Stdio::null())
                                .output()
                                .await;
                        });
                    }
                    let _ = guard.child.start_kill();
                    guard.completed = true;
                    Err(mcp_core::registry::TaskError::Cancelled)
                }
                output_res = wait_child_output(&mut guard.child) => {
                    guard.completed = true;
                    ACTIVE_CLI_PIDS.lock().remove(&ctx.task_id);
                    let output = output_res
                        .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to execute command: {}", e)))?;
                    let duration_ms = start.elapsed().as_millis() as u64;

                    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                    let exit_code = output.status.code().unwrap_or(-1);

                    let mut out = TaskOutput::success(json!({
                        "command": cmd_str,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": duration_ms,
                    }));
                    out.stdout = Some(stdout);
                    out.stderr = Some(stderr);
                    out.exit_code = exit_code;
                    out.is_error = !output.status.success();
                    Ok(out)
                }
            }
        },
    )?;

    // 5. Code Generation / File Write Command
    registry.register_fn(
        "write_file",
        "Writes or generates code in a file path creating directories as needed",
        "filesystem",
        TaskPriority::High,
        |_ctx, args| async move {
            let path = args["path"].as_str().unwrap_or("");
            let content = args["content"].as_str().unwrap_or("");
            if path.trim().is_empty() {
                return Err(mcp_core::registry::TaskError::InvalidArguments("Path is required".to_string()));
            }

            let file_path = std::path::Path::new(path);
            if let Some(parent) = file_path.parent() {
                if !parent.as_os_str().is_empty() {
                    tokio::fs::create_dir_all(parent).await
                        .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to create directories: {}", e)))?;
                }
            }

            tokio::fs::write(file_path, content).await
                .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to write file: {}", e)))?;

            Ok(TaskOutput::success(json!({
                "path": path,
                "bytes_written": content.len(),
                "status": "success"
            })))
        },
    )?;

    // 6. File Read Command
    registry.register_fn(
        "read_file",
        "Reads file contents from a workspace file path",
        "filesystem",
        TaskPriority::Normal,
        |_ctx, args| async move {
            let path = args["path"].as_str().unwrap_or("");
            if path.trim().is_empty() {
                return Err(mcp_core::registry::TaskError::InvalidArguments("Path is required".to_string()));
            }

            let content = tokio::fs::read_to_string(path).await
                .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to read file: {}", e)))?;

            Ok(TaskOutput::success(json!({
                "path": path,
                "content": content,
                "bytes_read": content.len()
            })))
        },
    )?;

    // 7. Directory Listing Command
    registry.register_fn(
        "list_dir",
        "Lists entries in a workspace directory",
        "filesystem",
        TaskPriority::Normal,
        |_ctx, args| async move {
            let path = args["path"].as_str().unwrap_or(".");
            let mut read_dir = tokio::fs::read_dir(path).await
                .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(format!("Failed to open directory: {}", e)))?;

            let mut entries = Vec::new();
            while let Ok(Some(entry)) = read_dir.next_entry().await {
                let file_type = entry.file_type().await.ok();
                let is_dir = file_type.map(|t| t.is_dir()).unwrap_or(false);
                let meta = entry.metadata().await.ok();
                let size = meta.map(|m| m.len()).unwrap_or(0);
                entries.push(json!({
                    "name": entry.file_name().to_string_lossy().to_string(),
                    "is_dir": is_dir,
                    "size_bytes": size,
                }));
            }

            Ok(TaskOutput::success(json!({ "path": path, "entries": entries })))
        },
    )?;

    Ok(())
}

struct AutoCancelTaskOnDrop {
    task_id: mcp_core::scheduler::TaskId,
    dispatcher: Arc<TaskDispatcher>,
    completed: bool,
}

impl Drop for AutoCancelTaskOnDrop {
    fn drop(&mut self) {
        if !self.completed {
            if let Some(pid) = ACTIVE_CLI_PIDS.lock().remove(&self.task_id) {
                #[cfg(windows)]
                {
                    tokio::spawn(async move {
                        let _ = tokio::process::Command::new("taskkill")
                            .args(&["/F", "/T", "/PID", &pid.to_string()])
                            .stdin(std::process::Stdio::null())
                            .stdout(std::process::Stdio::null())
                            .stderr(std::process::Stdio::null())
                            .output()
                            .await;
                    });
                }
            }
            let _ = self.dispatcher.cancel_task(&self.task_id);
        }
    }
}

fn setup_default_mcp_server(
    dispatcher: &Arc<TaskDispatcher>,
    resource_monitor: &Arc<ResourceMonitor>,
) -> anyhow::Result<McpServer> {
    let server = McpServer::new("mcp-ide-engine", "0.1.0")
        .with_instructions("High-performance multithreaded MCP IDE engine and tool dispatcher.");

    // Tool: Run Command
    let d_clone = dispatcher.clone();
    server.tools().register_fn(
        "run_command",
        Some("Dispatches any registered command through the multithreaded priority engine".to_string()),
        json!({
            "type": "object",
            "properties": {
                "command": { "type": "string" },
                "args": { "type": "object" },
                "priority": { "type": "string", "enum": ["Critical", "High", "Normal", "Low", "Background"] }
            },
            "required": ["command"]
        }),
        move |ctx, args| {
            let disp = d_clone.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let cmd = a["command"].as_str().unwrap_or("");
                let payload = a.get("args").cloned().unwrap_or(json!({}));
                let prio = match a.get("priority").and_then(|p| p.as_str()) {
                    Some("Critical") => Some(TaskPriority::Critical),
                    Some("High") => Some(TaskPriority::High),
                    Some("Low") => Some(TaskPriority::Low),
                    Some("Background") => Some(TaskPriority::Background),
                    _ => Some(TaskPriority::Normal),
                };

                let handle = disp.dispatch(cmd, payload, prio)
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed(cmd.to_string(), e.to_string()))?;
                let task_id = handle.id();
                let mut guard = AutoCancelTaskOnDrop {
                    task_id,
                    dispatcher: disp.clone(),
                    completed: false,
                };

                tokio::select! {
                    _ = ctx.cancellation_token.cancelled() => {
                        let _ = disp.cancel_task(&task_id);
                        Err(mcp_protocol::tools::ToolExecutionError::Cancelled)
                    }
                    output_res = handle.wait() => {
                        guard.completed = true;
                        let output = output_res
                            .map_err(|e| match e {
                                mcp_core::registry::TaskError::Cancelled => mcp_protocol::tools::ToolExecutionError::Cancelled,
                                other => mcp_protocol::tools::ToolExecutionError::ExecutionFailed(cmd.to_string(), other.to_string()),
                            })?;

                        let mut result = CallToolResult::text(serde_json::to_string(&output.data).unwrap());
                        if output.is_error || output.exit_code != 0 {
                            result.is_error = Some(true);
                        }
                        Ok(result)
                    }
                }
            }
        },
    )?;

    // Tool: Execute CLI Command
    let d_cli = dispatcher.clone();
    server.tools().register_fn(
        "execute_cli_command",
        Some("Executes any shell or CLI command non-blockingly across worker threads".to_string()),
        json!({
            "type": "object",
            "properties": {
                "command": { "type": "string", "description": "The shell command line to execute" },
                "cwd": { "type": "string", "description": "Optional working directory" }
            },
            "required": ["command"]
        }),
        move |ctx, args| {
            let disp = d_cli.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let handle = disp.dispatch("execute_cli", a, Some(TaskPriority::High))
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("execute_cli".to_string(), e.to_string()))?;
                let task_id = handle.id();
                let mut guard = AutoCancelTaskOnDrop {
                    task_id,
                    dispatcher: disp.clone(),
                    completed: false,
                };

                tokio::select! {
                    _ = ctx.cancellation_token.cancelled() => {
                        if let Some(pid) = ACTIVE_CLI_PIDS.lock().remove(&task_id) {
                            #[cfg(windows)]
                            {
                                tokio::spawn(async move {
                                    let _ = tokio::process::Command::new("taskkill")
                                        .args(&["/F", "/T", "/PID", &pid.to_string()])
                                        .stdin(std::process::Stdio::null())
                                        .stdout(std::process::Stdio::null())
                                        .stderr(std::process::Stdio::null())
                                        .output()
                                        .await;
                                });
                            }
                        }
                        let _ = disp.cancel_task(&task_id);
                        Err(mcp_protocol::tools::ToolExecutionError::Cancelled)
                    }
                    output_res = handle.wait() => {
                        guard.completed = true;
                        let output = output_res
                            .map_err(|e| match e {
                                mcp_core::registry::TaskError::Cancelled => mcp_protocol::tools::ToolExecutionError::Cancelled,
                                other => mcp_protocol::tools::ToolExecutionError::ExecutionFailed("execute_cli".to_string(), other.to_string()),
                            })?;

                        let text_content = serde_json::to_string_pretty(&output.data).unwrap();
                        let mut result = CallToolResult::text(text_content);
                        if output.is_error || output.exit_code != 0 {
                            result.is_error = Some(true);
                        }
                        Ok(result)
                    }
                }
            }
        },
    )?;

    // Tool: Write Code File (Code Generation)
    let d_write = dispatcher.clone();
    server.tools().register_fn(
        "write_code_file",
        Some("Writes or generates source code in a file path, creating parent directories if needed".to_string()),
        json!({
            "type": "object",
            "properties": {
                "path": { "type": "string", "description": "Target relative or absolute file path" },
                "content": { "type": "string", "description": "Code contents to write" }
            },
            "required": ["path", "content"]
        }),
        move |_ctx, args| {
            let disp = d_write.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let handle = disp.dispatch("write_file", a, Some(TaskPriority::High))
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("write_file".to_string(), e.to_string()))?;

                let output = handle.wait().await
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("write_file".to_string(), e.to_string()))?;

                Ok(CallToolResult::text(serde_json::to_string_pretty(&output.data).unwrap()))
            }
        },
    )?;

    // Tool: Read Code File
    let d_read = dispatcher.clone();
    server.tools().register_fn(
        "read_code_file",
        Some("Reads code and content from a workspace file path".to_string()),
        json!({
            "type": "object",
            "properties": {
                "path": { "type": "string", "description": "Source file path to read" }
            },
            "required": ["path"]
        }),
        move |_ctx, args| {
            let disp = d_read.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let handle = disp.dispatch("read_file", a, Some(TaskPriority::Normal))
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("read_file".to_string(), e.to_string()))?;

                let output = handle.wait().await
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("read_file".to_string(), e.to_string()))?;

                Ok(CallToolResult::text(serde_json::to_string_pretty(&output.data).unwrap()))
            }
        },
    )?;

    // Tool: List Directory
    let d_list = dispatcher.clone();
    server.tools().register_fn(
        "list_directory",
        Some("Lists entries and files in a workspace directory".to_string()),
        json!({
            "type": "object",
            "properties": {
                "path": { "type": "string", "description": "Directory path to list, defaults to '.'" }
            }
        }),
        move |_ctx, args| {
            let disp = d_list.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let handle = disp.dispatch("list_dir", a, Some(TaskPriority::Normal))
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("list_dir".to_string(), e.to_string()))?;

                let output = handle.wait().await
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("list_dir".to_string(), e.to_string()))?;

                Ok(CallToolResult::text(serde_json::to_string_pretty(&output.data).unwrap()))
            }
        },
    )?;

    // Tool: Get Telemetry
    let r_clone = resource_monitor.clone();
    server.tools().register_fn(
        "get_telemetry",
        Some("Returns real-time host CPU, RAM, and GPU telemetry snapshot".to_string()),
        json!({ "type": "object" }),
        move |_ctx, _args| {
            let mon = r_clone.clone();
            async move {
                let snap = mon.snapshot();
                Ok(CallToolResult::text(serde_json::to_string_pretty(&snap).unwrap()))
            }
        },
    )?;

    // Tool: Recommend Model
    let r_rec = resource_monitor.clone();
    server.tools().register_fn(
        "recommend_best_model",
        Some("Recommends the best local LLM or cloud fallback based on live available RAM and VRAM".to_string()),
        json!({
            "type": "object",
            "properties": {
                "context_tokens": { "type": "integer", "description": "Expected context length in tokens, defaults to 4096" }
            }
        }),
        move |_ctx, args| {
            let mon = r_rec.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let ctx = a["context_tokens"].as_u64().unwrap_or(4096) as usize;
                let snap = mon.snapshot();
                let catalog = ModelSelector::default_catalog();
                let decision = ModelSelector::select_best_model(&catalog, ctx, &snap);
                Ok(CallToolResult::text(serde_json::to_string_pretty(&decision).unwrap()))
            }
        },
    )?;

    // Tool: Calculate GPU Layer Offload
    let r_off = resource_monitor.clone();
    server.tools().register_fn(
        "calculate_layer_offload",
        Some("Calculates optimal GPU VRAM and CPU layer offload distribution for a model".to_string()),
        json!({
            "type": "object",
            "properties": {
                "model": { "type": "string", "description": "Model family or ID (e.g. llama-3.1-8b, llama-3.2-3b, llama-3.3-70b)" },
                "vram_gb": { "type": "number", "description": "Override available VRAM in Gigabytes" }
            }
        }),
        move |_ctx, args| {
            let mon = r_off.clone();
            async move {
                let a = args.unwrap_or(json!({}));
                let model = a["model"].as_str().unwrap_or("llama-3.1-8b");
                let snap = mon.snapshot();
                let vram_free_bytes = a["vram_gb"]
                    .as_f64()
                    .map(|g| (g * 1e9) as u64)
                    .or_else(|| snap.gpus.first().map(|g| g.free_vram_bytes))
                    .unwrap_or(8 * 1024 * 1024 * 1024);

                let spec = if model.contains("70b") {
                    ModelSpec::llama_3_3_70b()
                } else if model.contains("3b") {
                    ModelSpec::llama_3_2_3b()
                } else {
                    ModelSpec::llama_3_1_8b()
                };

                let plan = mcp_resource::selector::calculate_layer_offload(&spec, vram_free_bytes, 4096, 0.15);
                Ok(CallToolResult::text(serde_json::to_string_pretty(&plan).unwrap()))
            }
        },
    )?;

    // Resource: Hardware status
    server.resources().register_static_text(
        "telemetry://system/status",
        "System Hardware Telemetry",
        Some("Live CPU, RAM, and GPU load statistics".to_string()),
        Some("application/json".to_string()),
        "{\"status\":\"active\"}",
    );

    // Prompt: System Analysis Prompt
    server.prompts().register_template(
        "analyze_task",
        Some("Generate prompt for task performance analysis".to_string()),
        vec![
            PromptArgument {
                name: "task_id".to_string(),
                description: Some("Task execution ID".to_string()),
                required: Some(true),
            },
        ],
        vec![(Role::User, "Analyze execution metrics and resource usage for task {{task_id}}.".to_string())],
    );

    Ok(server)
}

async fn handle_run(args: RunArgs, dispatcher: &Arc<TaskDispatcher>, json_mode: bool) -> anyhow::Result<()> {
    let payload = serde_json::from_str::<serde_json::Value>(&args.args)
        .unwrap_or_else(|_| json!({ "raw": args.args }));

    let handle = dispatcher.dispatch(&args.name, payload, Some(args.priority.into()))?;

    if args.detach {
        if json_mode {
            println!("{}", json!({ "task_id": handle.id().to_string(), "status": "detached" }));
        } else {
            println!("{} Task queued in detached mode with ID: {}", "✓".green(), handle.id());
        }
        return Ok(());
    }

    let output = handle.wait().await?;

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&output.data)?);
    } else {
        println!("{} Task completed successfully:", "✓".green().bold());
        println!("{}", serde_json::to_string_pretty(&output.data)?);
    }

    Ok(())
}

async fn handle_mcp(args: McpArgs, server: &Arc<McpServer>, json_mode: bool) -> anyhow::Result<()> {
    match args.action {
        McpSubcommands::Tools(t_args) => match t_args.action {
            McpToolsAction::List => {
                let tools = server.tools().list();
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&tools)?);
                } else {
                    println!("{}", format!("Registered MCP Tools ({}):", tools.len()).bold().cyan());
                    for t in tools {
                        println!("  - {}: {}", t.name.green().bold(), t.description.as_deref().unwrap_or(""));
                    }
                }
            }
            McpToolsAction::Call { name, args } => {
                let payload = serde_json::from_str::<serde_json::Value>(&args).ok();
                let params = mcp_protocol::types::CallToolParams {
                    name,
                    arguments: payload,
                    _meta: None,
                };
                let cancel = mcp_core::cancellation::HierarchicalCancellationToken::new_root("cli_call");
                let res = server.tools().call(params, cancel, None).await.map_err(|e| anyhow::anyhow!(e))?;
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&res)?);
                } else {
                    println!("{} Tool Execution Output:", "✓".green().bold());
                    println!("{}", serde_json::to_string_pretty(&res)?);
                }
            }
        },
        McpSubcommands::Resources(r_args) => match r_args.action {
            McpResourcesAction::List => {
                let res = server.resources().list();
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&res)?);
                } else {
                    println!("{}", format!("Registered Resources ({}):", res.len()).bold().cyan());
                    for r in res {
                        println!("  - {} ({})", r.name.green(), r.uri.yellow());
                    }
                }
            }
            McpResourcesAction::Read { uri } => {
                let content = server.resources().read(&uri).await?;
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&content)?);
                } else {
                    println!("Resource Content for {}:", uri.yellow());
                    println!("{}", serde_json::to_string_pretty(&content)?);
                }
            }
        },
        McpSubcommands::Prompts(p_args) => match p_args.action {
            McpPromptsAction::List => {
                let prompts = server.prompts().list();
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&prompts)?);
                } else {
                    println!("{}", format!("Registered Prompts ({}):", prompts.len()).bold().cyan());
                    for p in prompts {
                        println!("  - {}: {}", p.name.green().bold(), p.description.as_deref().unwrap_or(""));
                    }
                }
            }
            McpPromptsAction::Get { name, args } => {
                let map_args: std::collections::HashMap<String, String> = serde_json::from_str(&args).unwrap_or_default();
                let rendered = server.prompts().render(&name, Some(map_args)).await?;
                if json_mode {
                    println!("{}", serde_json::to_string_pretty(&rendered)?);
                } else {
                    println!("{}", serde_json::to_string_pretty(&rendered)?);
                }
            }
        },
        McpSubcommands::Serve(s_args) => {
            if let Some(port) = s_args.sse_port {
                let addr = std::net::SocketAddr::from(([127, 0, 0, 1], port));
                eprintln!("{}", format!("Starting MCP Server on HTTP/SSE stream at http://{}", addr).green());
                sse_server::run_mcp_sse_server(server.clone(), addr).await?;
            } else if s_args.stdio {
                eprintln!("{}", "Starting MCP Server on standard I/O streams...".green());
                let transport = std::sync::Arc::new(mcp_protocol::transport::stdio::StdioStreamTransport::new(
                    tokio::io::stdin(),
                    tokio::io::stdout(),
                ));
                server.serve(transport).await?;
            } else {
                eprintln!("{}", "Error: either --stdio or --sse-port must be specified".red());
            }
        }
        McpSubcommands::Client(_c_args) => {
            eprintln!("{}", "Connecting to external MCP client...".green());
        }
    }
    Ok(())
}

async fn handle_resource(
    args: ResourceArgs,
    resource_monitor: &Arc<ResourceMonitor>,
    json_mode: bool,
) -> anyhow::Result<()> {
    match args.action {
        ResourceSubcommands::Status => {
            let snap = resource_monitor.snapshot();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&snap)?);
            } else {
                println!("{}", "Host Hardware Telemetry Status:".bold().cyan());
                println!("  CPU Usage:    {:.1}% (Logical Cores: {})", snap.cpu.global_cpu_usage_pct, snap.cpu.logical_core_count);
                println!("  RAM Usage:    {:.2} / {:.2} GB ({:.1}%)", snap.memory.used_ram_bytes as f64 / 1e9, snap.memory.total_ram_bytes as f64 / 1e9, (snap.memory.used_ram_bytes as f64 / snap.memory.total_ram_bytes.max(1) as f64) * 100.0);
                if let Some(gpu) = snap.gpus.first() {
                    println!("  GPU Device:   {} ({:?})", gpu.name.yellow(), gpu.detection_backend);
                    println!("  VRAM Usage:   {:.2} / {:.2} GB", gpu.used_vram_bytes as f64 / 1e9, gpu.total_vram_bytes as f64 / 1e9);
                } else {
                    println!("  GPU Device:   No dedicated accelerator (CPU Mode)");
                }
            }
        }
        ResourceSubcommands::Recommend { context } => {
            let snap = resource_monitor.snapshot();
            let catalog = ModelSelector::default_catalog();
            let decision = ModelSelector::select_best_model(&catalog, context, &snap);
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&decision)?);
            } else if let Some(d) = decision {
                println!("{}", "Model Fit Recommendation:".bold().green());
                println!("  Model ID:        {}", d.model_id.yellow().bold());
                println!("  Classified Tier: {:?}", d.tier);
                println!("  Execution Target:{:?}", d.target);
                println!("  Memory Required: {:.2} GB", d.memory_breakdown.total_required_bytes as f64 / 1e9);
                println!("  Reasoning:       {}", d.diagnostics.join("; "));
            } else {
                println!("{}", "No model fits within current system limits.".yellow());
            }
        }
        ResourceSubcommands::Offload { vram_gb, model } => {
            let snap = resource_monitor.snapshot();
            let vram_free_bytes = vram_gb
                .map(|g| (g * 1e9) as u64)
                .or_else(|| snap.gpus.first().map(|g| g.free_vram_bytes))
                .unwrap_or(8 * 1024 * 1024 * 1024);

            let spec = if model.contains("70b") {
                ModelSpec::llama_3_3_70b()
            } else if model.contains("3b") {
                ModelSpec::llama_3_2_3b()
            } else {
                ModelSpec::llama_3_1_8b()
            };

            let plan = mcp_resource::selector::calculate_layer_offload(&spec, vram_free_bytes, 4096, 0.15);

            if json_mode {
                println!("{}", serde_json::to_string_pretty(&plan)?);
            } else {
                println!("{}", "GPU Layer Offload Allocation:".bold().yellow());
                println!("  Model:         {}", spec.id.cyan());
                println!("  Total Layers:  {}", plan.total_layers);
                println!("  GPU Layers:    {} ({:.1}%)", plan.gpu_layers, (plan.gpu_layers as f64 / plan.total_layers as f64) * 100.0);
                println!("  CPU Layers:    {}", plan.cpu_layers);
                println!("  Allocated VRAM:{:.2} GB", plan.vram_allocated_bytes as f64 / 1e9);
            }
        }
    }
    Ok(())
}

async fn handle_tui(
    args: TuiArgs,
    dispatcher: Arc<TaskDispatcher>,
    resource_monitor: Arc<ResourceMonitor>,
    mcp_server: Arc<McpServer>,
) -> anyhow::Result<()> {
    let app = App::new()
        .with_dispatcher(dispatcher)
        .with_resource_monitor(resource_monitor)
        .with_mcp_server(mcp_server);

    mcp_tui::run_tui(app, Duration::from_millis(args.tick_rate_ms)).await?;
    Ok(())
}

async fn handle_serve(
    args: ServeArgs,
    dispatcher: Arc<TaskDispatcher>,
    resource_monitor: Arc<ResourceMonitor>,
    mcp_server: Arc<McpServer>,
) -> anyhow::Result<()> {
    let state = AppState::new(dispatcher, resource_monitor, mcp_server);
    run_server(state, args.addr).await?;
    Ok(())
}

async fn handle_repl(
    args: ReplArgs,
    dispatcher: Arc<TaskDispatcher>,
    resource_monitor: Arc<ResourceMonitor>,
    mcp_server: Arc<McpServer>,
) -> anyhow::Result<()> {
    let repl = ReplEngine::new(dispatcher, resource_monitor, mcp_server, args.history_file);
    repl.run().await?;
    Ok(())
}

async fn handle_bench(
    args: BenchArgs,
    dispatcher: &Arc<TaskDispatcher>,
    json_mode: bool,
) -> anyhow::Result<()> {
    let n = args.iterations;
    println!("{}", format!("Running dispatch benchmark ({} iterations)...", n).cyan());

    let start = std::time::Instant::now();
    let mut handles = Vec::with_capacity(n);

    for i in 0..n {
        let h = dispatcher.dispatch("echo", json!({ "iter": i }), Some(TaskPriority::Normal))?;
        handles.push(h);
    }

    for h in handles {
        let _ = h.wait().await?;
    }

    let elapsed = start.elapsed();
    let avg_per_task = elapsed / (n as u32);
    let tasks_per_sec = (n as f64) / elapsed.as_secs_f64();

    if json_mode {
        println!("{}", json!({
            "iterations": n,
            "total_elapsed_ms": elapsed.as_millis(),
            "avg_latency_us": avg_per_task.as_micros(),
            "throughput_tasks_sec": tasks_per_sec
        }));
    } else {
        println!("{}", "================ Benchmark Results ================".bold().green());
        println!("  Total Iterations:  {}", n);
        println!("  Total Elapsed:     {:.2?}", elapsed);
        println!("  Average Latency:   {:.2?}", avg_per_task);
        println!("  Throughput:        {:.1} tasks/sec", tasks_per_sec);
        if avg_per_task < Duration::from_millis(5) {
            println!("  Acceptance Target: {} (<5ms dispatch latency)", "PASS".green().bold());
        } else {
            println!("  Acceptance Target: {}", "FAIL".red().bold());
        }
        println!("{}", "===================================================".bold().green());
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use mcp_core::cancellation::HierarchicalCancellationToken;
    use mcp_core::runtime::EngineRuntimeConfig;
    use mcp_protocol::types::{CallToolParams, JsonRpcMessage, JsonRpcRequest};
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    static CLI_CANCEL_TEST_MUTEX: parking_lot::Mutex<()> = parking_lot::Mutex::new(());

    fn create_test_engine() -> (Arc<TaskDispatcher>, Arc<ResourceMonitor>, Arc<McpServer>) {
        let runtime = Arc::new(EngineRuntime::new(EngineRuntimeConfig::new()).unwrap());
        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());
        register_builtin_commands(&registry).unwrap();
        let dispatcher = TaskDispatcher::new(
            registry.clone(),
            scheduler.clone(),
            runtime.clone(),
            telemetry.clone(),
            4,
        );
        let resource_monitor = Arc::new(ResourceMonitor::new(Duration::from_millis(250)));
        let mcp_server = Arc::new(setup_default_mcp_server(&dispatcher, &resource_monitor).unwrap());
        (dispatcher, resource_monitor, mcp_server)
    }

    #[tokio::test]
    async fn test_cli_command_execution_success() {
        let (dispatcher, _, _) = create_test_engine();
        let cmd = "echo hello_mcp";

        let handle = dispatcher
            .dispatch("execute_cli", json!({ "command": cmd }), Some(TaskPriority::High))
            .unwrap();
        let output = handle.wait().await.unwrap();
        assert_eq!(output.exit_code, 0);
        assert!(!output.is_error);
        assert!(output.stdout.as_ref().unwrap().contains("hello_mcp"));
    }

    #[tokio::test]
    async fn test_cli_command_cancellation_latency_and_kill() {
        let _lock = CLI_CANCEL_TEST_MUTEX.lock();
        LAST_SPAWNED_CLI_PID.store(0, std::sync::atomic::Ordering::SeqCst);
        let (dispatcher, _, _) = create_test_engine();
        #[cfg(windows)]
        let cmd = "ping -n 10 127.0.0.1";
        #[cfg(not(windows))]
        let cmd = "sleep 10";

        let start = std::time::Instant::now();
        let handle = dispatcher
            .dispatch("execute_cli", json!({ "command": cmd }), Some(TaskPriority::High))
            .unwrap();

        let task_id = handle.id();
        let disp_clone = dispatcher.clone();

        // Spawn cancellation after 30ms
        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(30)).await;
            let _ = disp_clone.cancel_task(&task_id);
        });

        let wait_res = handle.wait().await;
        let elapsed = start.elapsed();

        assert!(matches!(wait_res, Err(mcp_core::registry::TaskError::Cancelled)));
        assert!(
            elapsed < Duration::from_millis(500),
            "Cancellation took too long: {:?}",
            elapsed
        );

        #[cfg(windows)]
        {
            let target_pid = LAST_SPAWNED_CLI_PID.load(std::sync::atomic::Ordering::SeqCst);
            let mut clean = false;
            let mut last_output = String::new();
            for _ in 0..10 {
                tokio::time::sleep(Duration::from_millis(50)).await;
                if target_pid > 0 {
                    let check = std::process::Command::new("tasklist")
                        .args(&["/FI", &format!("PID eq {}", target_pid)])
                        .output()
                        .expect("Failed to execute tasklist");
                    last_output = String::from_utf8_lossy(&check.stdout).to_string();
                    if last_output.contains("No tasks are running") || !last_output.contains(&target_pid.to_string()) {
                        clean = true;
                        break;
                    }
                } else {
                    clean = true;
                    break;
                }
            }
            assert!(
                clean,
                "Grandchild process with PID {} was leaked in OS process table: {}",
                target_pid,
                last_output
            );
        }
    }

    #[tokio::test]
    async fn test_execute_cli_command_mcp_tool_cancellation() {
        let _lock = CLI_CANCEL_TEST_MUTEX.lock();
        LAST_SPAWNED_CLI_PID.store(0, std::sync::atomic::Ordering::SeqCst);
        let (_, _, server) = create_test_engine();
        #[cfg(windows)]
        let cmd = "ping -n 10 127.0.0.1";
        #[cfg(not(windows))]
        let cmd = "sleep 10";

        let cancel_token = HierarchicalCancellationToken::new_root("test_tool_cancel");
        let cancel_clone = cancel_token.clone();

        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(30)).await;
            cancel_clone.cancel();
        });

        let start = std::time::Instant::now();
        let params = CallToolParams {
            name: "execute_cli_command".to_string(),
            arguments: Some(json!({ "command": cmd })),
            _meta: None,
        };

        let res = server.tools().call(params, cancel_token, None).await.unwrap();
        let elapsed = start.elapsed();

        assert_eq!(res.is_error, Some(true));
        assert!(
            elapsed < Duration::from_millis(500),
            "MCP tool cancellation took too long: {:?}",
            elapsed
        );

        #[cfg(windows)]
        {
            let target_pid = LAST_SPAWNED_CLI_PID.load(std::sync::atomic::Ordering::SeqCst);
            let mut clean = false;
            let mut last_output = String::new();
            for _ in 0..10 {
                tokio::time::sleep(Duration::from_millis(50)).await;
                if target_pid > 0 {
                    let check = std::process::Command::new("tasklist")
                        .args(&["/FI", &format!("PID eq {}", target_pid)])
                        .output()
                        .expect("Failed to execute tasklist");
                    last_output = String::from_utf8_lossy(&check.stdout).to_string();
                    if last_output.contains("No tasks are running") || !last_output.contains(&target_pid.to_string()) {
                        clean = true;
                        break;
                    }
                } else {
                    clean = true;
                    break;
                }
            }
            assert!(
                clean,
                "Grandchild process with PID {} was leaked in OS process table: {}",
                target_pid,
                last_output
            );
        }
    }

    #[tokio::test]
    async fn test_cli_sse_server_real_tcp_roundtrip() {
        let (_, _, server) = create_test_engine();
        let session_manager = Arc::new(mcp_protocol::transport::sse::SseSessionManager::new("/message"));
        let state = sse_server::SseServerState {
            server: server.clone(),
            session_manager,
        };
        let app = sse_server::create_sse_router(state);

        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();

        tokio::spawn(async move {
            axum::serve(listener, app).await.unwrap();
        });

        // 1. Test /message health check
        let mut stream = tokio::net::TcpStream::connect(addr).await.unwrap();
        stream
            .write_all(format!("GET /message HTTP/1.1\r\nHost: {}\r\n\r\n", addr).as_bytes())
            .await
            .unwrap();
        let mut buf = vec![0u8; 1024];
        let n = stream.read(&mut buf).await.unwrap();
        let health_resp = String::from_utf8_lossy(&buf[..n]);
        assert!(health_resp.contains("200 OK"));

        // 2. Connect to GET /sse
        let mut sse_stream = tokio::net::TcpStream::connect(addr).await.unwrap();
        sse_stream
            .write_all(
                format!(
                    "GET /sse HTTP/1.1\r\nHost: {}\r\nAccept: text/event-stream\r\n\r\n",
                    addr
                )
                .as_bytes(),
            )
            .await
            .unwrap();

        // Read initial SSE endpoint event
        let mut sse_buf = vec![0u8; 4096];
        let mut read_total = 0;
        let endpoint_line;
        loop {
            let n = sse_stream.read(&mut sse_buf[read_total..]).await.unwrap();
            read_total += n;
            let text = String::from_utf8_lossy(&sse_buf[..read_total]);
            if let Some(pos) = text.find("event: endpoint\ndata: ") {
                let rest = &text[pos + "event: endpoint\ndata: ".len()..];
                if let Some(end) = rest.find("\n") {
                    endpoint_line = rest[..end].trim().to_string();
                    break;
                }
            }
            if n == 0 {
                panic!("EOF before endpoint event");
            }
        }
        assert!(endpoint_line.starts_with("/message?sessionId="));

        // 3. Send MCP initialize Request via HTTP POST to endpoint
        let init_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            1,
            "initialize",
            Some(json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": { "name": "test-agent", "version": "1.0.0" }
            })),
        ));
        let body = serde_json::to_string(&init_req).unwrap();

        let mut post_stream = tokio::net::TcpStream::connect(addr).await.unwrap();
        let post_req = format!(
            "POST {} HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}",
            endpoint_line,
            addr,
            body.len(),
            body
        );
        post_stream.write_all(post_req.as_bytes()).await.unwrap();

        let mut post_buf = vec![0u8; 512];
        let n_post = post_stream.read(&mut post_buf).await.unwrap();
        let post_resp = String::from_utf8_lossy(&post_buf[..n_post]);
        assert!(post_resp.contains("202 Accepted"));

        // 4. Verify SSE response arrives on sse_stream
        loop {
            let n = sse_stream.read(&mut sse_buf[read_total..]).await.unwrap();
            read_total += n;
            let text = String::from_utf8_lossy(&sse_buf[..read_total]);
            if text.contains("mcp-ide-engine") && text.contains("2024-11-05") {
                break;
            }
            if n == 0 {
                panic!("EOF before initialize response received on SSE");
            }
        }
    }
}

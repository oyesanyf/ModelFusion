//! Interactive Reedline REPL with syntax suggestions and engine integration

use colored::Colorize;
use mcp_core::registry::{TaskDispatcher, TaskPriority};
use mcp_protocol::server::McpServer;
use mcp_resource::selector::ModelSelector;
use mcp_resource::telemetry::ResourceMonitor;
use reedline::{DefaultCompleter, FileBackedHistory, Prompt, Reedline, Signal};
use serde_json::json;
use std::path::PathBuf;
use std::sync::Arc;

/// Custom REPL Prompt
pub struct McpPrompt;

impl Prompt for McpPrompt {
    fn render_prompt_left(&self) -> std::borrow::Cow<'_, str> {
        std::borrow::Cow::Owned("⚡ mcp-ide".cyan().bold().to_string())
    }

    fn render_prompt_right(&self) -> std::borrow::Cow<'_, str> {
        let now = chrono_lite_timestamp();
        std::borrow::Cow::Owned(format!("[{}]", now).dimmed().to_string())
    }

    fn render_prompt_indicator(&self, _prompt_mode: reedline::PromptEditMode) -> std::borrow::Cow<'_, str> {
        std::borrow::Cow::Borrowed(" > ")
    }

    fn render_prompt_multiline_indicator(&self) -> std::borrow::Cow<'_, str> {
        std::borrow::Cow::Borrowed("::: ")
    }

    fn render_prompt_history_search_indicator(
        &self,
        history_search: reedline::PromptHistorySearch,
    ) -> std::borrow::Cow<'_, str> {
        let prefix = match history_search.status {
            reedline::PromptHistorySearchStatus::Passing => "(search: ",
            reedline::PromptHistorySearchStatus::Failing => "(failing search: ",
        };
        std::borrow::Cow::Owned(format!("{}{}) > ", prefix, history_search.term))
    }
}

fn chrono_lite_timestamp() -> String {
    let dur = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = dur.as_secs() % 86400;
    format!("{:02}:{:02}:{:02}", secs / 3600, (secs % 3600) / 60, secs % 60)
}

/// REPL Controller
pub struct ReplEngine {
    dispatcher: Arc<TaskDispatcher>,
    resource_monitor: Arc<ResourceMonitor>,
    mcp_server: Arc<McpServer>,
    history_path: Option<PathBuf>,
}

impl ReplEngine {
    pub fn new(
        dispatcher: Arc<TaskDispatcher>,
        resource_monitor: Arc<ResourceMonitor>,
        mcp_server: Arc<McpServer>,
        history_path: Option<PathBuf>,
    ) -> Self {
        Self {
            dispatcher,
            resource_monitor,
            mcp_server,
            history_path,
        }
    }

    /// Run the interactive REPL loop
    pub async fn run(&self) -> anyhow::Result<()> {
        println!("{}", "=========================================================".cyan());
        println!("{}", "  MCP IDE Interactive REPL Shell v0.1.0".bold().green());
        println!("{}", "  Type 'help' for command summary, 'exit' to quit.".yellow());
        println!("{}", "=========================================================".cyan());

        let commands = vec![
            "help".to_string(),
            "run".to_string(),
            "tasks".to_string(),
            "tools".to_string(),
            "call".to_string(),
            "resources".to_string(),
            "prompts".to_string(),
            "telemetry".to_string(),
            "models".to_string(),
            "offload".to_string(),
            "clear".to_string(),
            "exit".to_string(),
            "quit".to_string(),
        ];

        let completer = Box::new(DefaultCompleter::new_with_wordlen(commands, 2));

        let mut line_editor = Reedline::create().with_completer(completer);

        if let Some(ref path) = self.history_path {
            if let Ok(history) = FileBackedHistory::with_file(1000, path.clone()) {
                line_editor = line_editor.with_history(Box::new(history));
            }
        }

        let prompt = McpPrompt;

        loop {
            let sig = line_editor.read_line(&prompt);
            match sig {
                Ok(Signal::Success(buffer)) => {
                    let trimmed = buffer.trim();
                    if trimmed.is_empty() {
                        continue;
                    }

                    if trimmed == "exit" || trimmed == "quit" {
                        println!("{}", "Exiting MCP IDE REPL.".green());
                        break;
                    }

                    if trimmed == "clear" {
                        line_editor.clear_scrollback()?;
                        continue;
                    }

                    if let Err(e) = self.eval_command(trimmed).await {
                        eprintln!("{} {}", "Error:".red().bold(), e);
                    }
                }
                Ok(Signal::CtrlC) => {
                    println!("{}", "Interrupted. Type 'exit' to quit.".yellow());
                }
                Ok(Signal::CtrlD) => {
                    println!("{}", "Exiting MCP IDE REPL.".green());
                    break;
                }
                Err(err) => {
                    eprintln!("{} {}", "REPL error:".red(), err);
                    break;
                }
            }
        }

        Ok(())
    }

    /// Evaluate a single REPL command string
    pub async fn eval_command(&self, line: &str) -> anyhow::Result<()> {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() {
            return Ok(());
        }

        let cmd = parts[0];
        match cmd {
            "help" => {
                println!("{}", "Available REPL Commands:".bold().yellow());
                println!("  {}                       - Show active background tasks in scheduler", "tasks".green());
                println!("  {} <name> [json_args]          - Dispatch a registered task asynchronously", "run".green());
                println!("  {}                       - List all registered MCP tools", "tools".green());
                println!("  {} <tool_name> [json_args]     - Invoke an MCP tool", "call".green());
                println!("  {}                   - List registered MCP resources", "resources".green());
                println!("  {}                     - List registered MCP prompt templates", "prompts".green());
                println!("  {}                   - Inspect CPU, RAM, and GPU hardware metrics", "telemetry".green());
                println!("  {}                      - Recommend optimal model tier for current hardware", "models".green());
                println!("  {} [vram_gb]                 - Calculate GPU layer offloading distribution", "offload".green());
                println!("  {}                       - Clear screen buffer", "clear".green());
                println!("  {} / {}                  - Exit REPL session", "exit".green(), "quit".green());
            }

            "tasks" => {
                let tasks = self.dispatcher.list_task_records();
                if tasks.is_empty() {
                    println!("{}", "No active tasks in scheduler queue.".dimmed());
                } else {
                    println!("{:<8} {:<24} {:<12} {:<12} {:<12}", "ID", "Command", "Priority", "State", "Worker");
                    println!("{}", "--------------------------------------------------------------------".dimmed());
                    for t in tasks {
                        println!(
                            "{:<8} {:<24} {:<12} {:<12} {:<12}",
                            t.task_id,
                            t.command_name,
                            format!("{:?}", t.priority),
                            format!("{:?}", t.state),
                            "-"
                        );
                    }
                }
            }

            "run" => {
                if parts.len() < 2 {
                    println!("{} Usage: run <cmd_name> [json_args]", "Error:".red());
                    return Ok(());
                }
                let name = parts[1];
                let args_json = if parts.len() > 2 {
                    let rest = parts[2..].join(" ");
                    serde_json::from_str::<serde_json::Value>(&rest).unwrap_or(json!({}))
                } else {
                    json!({})
                };

                let handle = self.dispatcher.dispatch(name, args_json, Some(TaskPriority::Normal))?;
                println!("{} Task dispatched: ID {}", "✓".green(), handle.id());

                let output = handle.wait().await?;
                println!("{}", "Result:".bold().cyan());
                println!("{}", serde_json::to_string_pretty(&output.data)?);
            }

            "tools" => {
                let tools = self.mcp_server.tools().list();
                if tools.is_empty() {
                    println!("{}", "No MCP tools registered.".dimmed());
                } else {
                    println!("{}", format!("Registered MCP Tools ({}):", tools.len()).bold().yellow());
                    for t in tools {
                        println!("  {} - {}", t.name.green().bold(), t.description.as_deref().unwrap_or("No description"));
                    }
                }
            }

            "call" => {
                if parts.len() < 2 {
                    println!("{} Usage: call <tool_name> [json_args]", "Error:".red());
                    return Ok(());
                }
                let tool_name = parts[1];
                let args_json = if parts.len() > 2 {
                    let rest = parts[2..].join(" ");
                    serde_json::from_str::<serde_json::Value>(&rest).ok()
                } else {
                    None
                };

                let params = mcp_protocol::types::CallToolParams {
                    name: tool_name.to_string(),
                    arguments: args_json,
                    _meta: None,
                };
                let cancel = mcp_core::cancellation::HierarchicalCancellationToken::new_root("repl_call");
                let result = self.mcp_server.tools().call(params, cancel, None).await.map_err(|e| anyhow::anyhow!(e))?;
                println!("{}", "MCP Tool Output:".bold().green());
                println!("{}", serde_json::to_string_pretty(&result)?);
            }

            "resources" => {
                let res = self.mcp_server.resources().list();
                println!("{}", format!("MCP Resources ({}):", res.len()).bold().yellow());
                for r in res {
                    println!("  {} ({})", r.name.green(), r.uri.cyan());
                }
            }

            "prompts" => {
                let prompts = self.mcp_server.prompts().list();
                println!("{}", format!("MCP Prompts ({}):", prompts.len()).bold().yellow());
                for p in prompts {
                    println!("  {} - {}", p.name.green(), p.description.as_deref().unwrap_or(""));
                }
            }

            "telemetry" => {
                let snap = self.resource_monitor.snapshot();
                println!("{}", "Hardware Telemetry Snapshot:".bold().cyan());
                println!("  CPU: {:.1}% usage across {} logical cores", snap.cpu.global_cpu_usage_pct, snap.cpu.logical_core_count);
                println!(
                    "  RAM: {:.2} / {:.2} GB used ({:.1}%)",
                    snap.memory.used_ram_bytes as f64 / 1e9,
                    snap.memory.total_ram_bytes as f64 / 1e9,
                    (snap.memory.used_ram_bytes as f64 / snap.memory.total_ram_bytes.max(1) as f64) * 100.0
                );
                if let Some(gpu) = snap.gpus.first() {
                    println!(
                        "  GPU: {} ({:?}) | VRAM: {:.2} / {:.2} GB used",
                        gpu.name.yellow(),
                        gpu.detection_backend,
                        gpu.used_vram_bytes as f64 / 1e9,
                        gpu.total_vram_bytes as f64 / 1e9
                    );
                } else {
                    println!("  GPU: No dedicated accelerator found (CPU compute mode)");
                }
            }

            "models" => {
                let snap = self.resource_monitor.snapshot();
                let catalog = ModelSelector::default_catalog();
                if let Some(decision) = ModelSelector::select_best_model(&catalog, 4096, &snap) {
                    println!("{}", "Model Fit Recommendation:".bold().green());
                    println!("  Model ID:     {}", decision.model_id.yellow().bold());
                    println!("  Target Tier:  {:?}", decision.tier);
                    println!("  Target HW:    {:?}", decision.target);
                    println!("  Total Memory: {:.2} GB required", decision.memory_breakdown.total_required_bytes as f64 / 1e9);
                    println!("  Reasoning:    {}", decision.diagnostics.join("; "));
                } else {
                    println!("{}", "No suitable local model fits within available hardware constraints.".yellow());
                }
            }

            "offload" => {
                let snap = self.resource_monitor.snapshot();
                let vram_free = if parts.len() > 1 {
                    parts[1].parse::<f64>().unwrap_or(8.0) * 1e9
                } else if let Some(gpu) = snap.gpus.first() {
                    gpu.free_vram_bytes as f64
                } else {
                    8.0 * 1e9
                } as u64;

                let plan = mcp_resource::selector::calculate_layer_offload(
                    &mcp_resource::selector::ModelSpec::llama_3_1_8b(),
                    vram_free,
                    4096,
                    0.15,
                );

                println!("{}", "GPU Layer Offload Breakdown:".bold().yellow());
                println!("  Total Model Layers:  {}", plan.total_layers);
                println!("  Offload to GPU:      {} layers ({:.1}%)", plan.gpu_layers, (plan.gpu_layers as f64 / plan.total_layers as f64) * 100.0);
                println!("  CPU Residual Layers: {} layers", plan.cpu_layers);
                println!("  GPU VRAM Allocated:  {:.2} GB", plan.vram_allocated_bytes as f64 / 1e9);
            }

            other => {
                println!("{} Unknown command '{}'. Type 'help' for command list.", "Error:".red(), other);
            }
        }

        Ok(())
    }
}

//! Shared test fixtures and utilities for MCP E2E test suite

use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskOutput, TaskPriority};
use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
use mcp_core::scheduler::MultiLaneScheduler;
use mcp_core::telemetry::EngineTelemetry;
use mcp_protocol::server::McpServer;
use mcp_protocol::types::{CallToolResult, PromptArgument, Role};
use mcp_resource::telemetry::ResourceMonitor;
use mcp_web::server::AppState;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

pub struct TestHarness {
    pub runtime: Arc<EngineRuntime>,
    pub telemetry: Arc<EngineTelemetry>,
    pub scheduler: Arc<MultiLaneScheduler>,
    pub registry: Arc<CommandRegistry>,
    pub dispatcher: Arc<TaskDispatcher>,
    pub resource_monitor: Arc<ResourceMonitor>,
    pub mcp_server: Arc<McpServer>,
    pub web_state: AppState,
}

impl TestHarness {
    pub fn new(worker_threads: usize, compute_threads: usize) -> Self {
        let telemetry = Arc::new(EngineTelemetry::new());
        let config = EngineRuntimeConfig::new()
            .worker_threads(worker_threads)
            .compute_threads(compute_threads);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());

        // Register default test commands
        registry
            .register_fn(
                "echo",
                "Echoes input arguments",
                "test",
                TaskPriority::Normal,
                |_ctx, args| async move { Ok(TaskOutput::success(args)) },
            )
            .unwrap();

        registry
            .register_fn(
                "fast_calc",
                "Performs fast arithmetic",
                "test",
                TaskPriority::High,
                |_ctx, args| async move {
                    let a = args["a"].as_i64().unwrap_or(0);
                    let b = args["b"].as_i64().unwrap_or(0);
                    Ok(TaskOutput::success(json!({ "sum": a + b, "product": a * b })))
                },
            )
            .unwrap();

        registry
            .register_fn(
                "heavy_compute",
                "Executes CPU intensive Rayon loop",
                "test",
                TaskPriority::Normal,
                |ctx, args| async move {
                    let n = args["iterations"].as_u64().unwrap_or(10_000);
                    let val = ctx
                        .runtime
                        .spawn_compute(move || {
                            let mut acc: u64 = 0;
                            for i in 0..n {
                                acc = acc.wrapping_add(i.wrapping_mul(41));
                            }
                            acc
                        })
                        .await
                        .map_err(|e| mcp_core::registry::TaskError::ExecutionFailed(e.to_string()))?;
                    Ok(TaskOutput::success(json!({ "result": val })))
                },
            )
            .unwrap();

        registry
            .register_fn(
                "delay",
                "Asynchronously delays",
                "test",
                TaskPriority::Normal,
                |_ctx, args| async move {
                    let ms = args["ms"].as_u64().unwrap_or(10);
                    tokio::time::sleep(Duration::from_millis(ms)).await;
                    Ok(TaskOutput::success(json!({ "delayed_ms": ms })))
                },
            )
            .unwrap();

        let dispatcher = TaskDispatcher::new(
            registry.clone(),
            scheduler.clone(),
            runtime.clone(),
            telemetry.clone(),
            worker_threads,
        );

        let resource_monitor = Arc::new(ResourceMonitor::new(Duration::from_millis(50)));

        let server = McpServer::new("test-e2e-server", "1.0.0");
        server
            .tools()
            .register_fn(
                "tool_add",
                Some("Adds numbers".to_string()),
                json!({
                    "type": "object",
                    "properties": {
                        "x": { "type": "number" },
                        "y": { "type": "number" }
                    },
                    "required": ["x", "y"]
                }),
                |_ctx, args| async move {
                    let a = args.unwrap();
                    let x = a["x"].as_f64().unwrap_or(0.0);
                    let y = a["y"].as_f64().unwrap_or(0.0);
                    Ok(CallToolResult::text(format!("{}", x + y)))
                },
            )
            .unwrap();

        server.resources().register_static_text(
            "metrics://system/load",
            "System Load",
            None,
            Some("application/json".to_string()),
            "{\"cpu_usage\": 12.5}",
        );

        server.prompts().register_template(
            "code_review",
            Some("Code review prompt".to_string()),
            vec![PromptArgument {
                name: "file".to_string(),
                description: Some("File path".to_string()),
                required: Some(true),
            }],
            vec![(Role::User, "Please review file {{file}}.".to_string())],
        );

        let mcp_server = Arc::new(server);
        let web_state = AppState::new(dispatcher.clone(), resource_monitor.clone(), mcp_server.clone());

        Self {
            runtime,
            telemetry,
            scheduler,
            registry,
            dispatcher,
            resource_monitor,
            mcp_server,
            web_state,
        }
    }
}

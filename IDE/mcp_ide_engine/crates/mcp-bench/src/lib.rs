//! # MCP IDE Benchmarks
//!
//! Criterion microbenchmarks evaluating task dispatch latency (<5ms target),
//! Rayon compute bridge throughput, and JSON-RPC tool invocation overhead.

pub mod helpers {
    use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskOutput, TaskPriority};
    use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
    use mcp_core::scheduler::MultiLaneScheduler;
    use mcp_core::telemetry::EngineTelemetry;
    use mcp_protocol::server::McpServer;
    use mcp_protocol::types::CallToolResult;
    use serde_json::json;
    use std::sync::Arc;

    pub fn setup_benchmark_environment() -> (Arc<TaskDispatcher>, Arc<McpServer>) {
        let telemetry = Arc::new(EngineTelemetry::new());
        let config = EngineRuntimeConfig::new().worker_threads(4).compute_threads(2);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());

        registry
            .register_fn(
                "noop",
                "No-op baseline task",
                "bench",
                TaskPriority::High,
                |_ctx, args| async move { Ok(TaskOutput::success(args)) },
            )
            .unwrap();

        registry
            .register_fn(
                "compute_hash",
                "Rayon compute bridge task",
                "bench",
                TaskPriority::Normal,
                |ctx, args| async move {
                    let n = args["iterations"].as_u64().unwrap_or(1000);
                    let res = ctx
                        .runtime
                        .spawn_compute(move || {
                            let mut acc: u64 = 0;
                            for i in 0..n {
                                acc = acc.wrapping_add(i.wrapping_mul(37));
                            }
                            acc
                        })
                        .await
                        .unwrap();
                    Ok(TaskOutput::success(json!({ "result": res })))
                },
            )
            .unwrap();

        let dispatcher = TaskDispatcher::new(
            registry,
            scheduler,
            runtime,
            telemetry,
            4,
        );

        let server = McpServer::new("bench-mcp", "1.0.0");
        server
            .tools()
            .register_fn(
                "echo_tool",
                Some("Echo tool for JSON-RPC benchmark".to_string()),
                json!({
                    "type": "object",
                    "properties": { "msg": { "type": "string" } },
                    "required": ["msg"]
                }),
                |_ctx, args| async move {
                    let a = args.unwrap();
                    let m = a["msg"].as_str().unwrap_or("");
                    Ok(CallToolResult::text(m))
                },
            )
            .unwrap();

        (dispatcher, Arc::new(server))
    }
}

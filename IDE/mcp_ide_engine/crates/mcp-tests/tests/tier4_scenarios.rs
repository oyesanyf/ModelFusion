//! Tier 4: Real-World End-to-End Application Scenarios

use mcp_core::registry::TaskPriority;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;
use mcp_resource::selector::{ExecutionTarget, ModelSelector, ModelSpec, ModelTier};
use mcp_resource::sizing::calculate_layer_offload;
use mcp_tests::TestHarness;
use mcp_tui::{App, AppTab, LogLevel};
use mcp_web::server::{create_router, AppState};
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

// Scenario 1: Multi-Model Local vs Cloud Routing under Variable RAM/VRAM Pressure
#[tokio::test]
async fn test_scenario_1_multi_model_local_vs_cloud_routing() {
    let catalog = ModelSelector::default_catalog();

    // Condition A: High End Workstation (64 GB RAM, 24 GB VRAM)
    let mut snap_high = mcp_resource::telemetry::SystemSnapshot::default();
    snap_high.memory.total_ram_bytes = 64 * 1024 * 1024 * 1024;
    snap_high.memory.available_ram_bytes = 48 * 1024 * 1024 * 1024;
    snap_high.gpu.has_gpu = true;
    snap_high.gpu.gpus = vec![mcp_resource::gpu::GpuInfo {
        name: "RTX 4090".into(),
        vendor: mcp_resource::gpu::GpuVendor::Nvidia,
        backend: mcp_resource::gpu::GpuBackend::Nvml,
        vram_total_bytes: 24 * 1024 * 1024 * 1024,
        vram_free_bytes: 22 * 1024 * 1024 * 1024,
        vram_used_bytes: 2 * 1024 * 1024 * 1024,
        driver_version: Some("550.54".into()),
        compute_capability: Some((8, 9)),
    }];

    let dec_high = ModelSelector::select_best_model(&catalog, 4096, &snap_high).unwrap();
    assert_eq!(dec_high.selected_tier, ModelTier::Large);
    assert_eq!(dec_high.target, ExecutionTarget::HybridCpuGpu);

    let offload_high = calculate_layer_offload(&ModelSpec::llama_3_70b_instruct_q4(), 4096, 22 * 1024 * 1024 * 1024, 0.15);
    assert!(offload_high.gpu_layers > 0);

    // Condition B: Mid-Range Laptop (16 GB RAM, No GPU)
    let mut snap_mid = mcp_resource::telemetry::SystemSnapshot::default();
    snap_mid.memory.total_ram_bytes = 16 * 1024 * 1024 * 1024;
    snap_mid.memory.available_ram_bytes = 10 * 1024 * 1024 * 1024;
    snap_mid.gpu.has_gpu = false;

    let dec_mid = ModelSelector::select_best_model(&catalog, 4096, &snap_mid).unwrap();
    assert_eq!(dec_mid.selected_tier, ModelTier::Medium);
    assert_eq!(dec_mid.target, ExecutionTarget::LocalCpuOnly);

    // Condition C: Severely Constrained Container (512 MB RAM) -> Cloud Fallback
    let mut snap_low = mcp_resource::telemetry::SystemSnapshot::default();
    snap_low.memory.total_ram_bytes = 512 * 1024 * 1024;
    snap_low.memory.available_ram_bytes = 200 * 1024 * 1024;

    let dec_low = ModelSelector::select_best_model(&catalog, 4096, &snap_low).unwrap();
    assert_eq!(dec_low.target, ExecutionTarget::CloudApiFallback);
}

// Scenario 2: Parallel MCP Tool Orchestration Pipeline with Isolated Failures
#[tokio::test]
async fn test_scenario_2_parallel_mcp_tool_orchestration_pipeline() {
    let harness = TestHarness::new(4, 2);

    // Register 5 specialized tools in MCP server
    harness.mcp_server.tools().register_fn(
        "parser",
        None,
        json!({ "type": "object" }),
        |_c, args| async move {
            let a = args.unwrap_or(json!({}));
            let code = a["code"].as_str().unwrap_or("");
            Ok(CallToolResult::text(format!("AST tokens: {}", code.len())))
        }
    ).unwrap();

    harness.mcp_server.tools().register_fn(
        "linter",
        None,
        json!({ "type": "object" }),
        |_c, _a| async move { Ok(CallToolResult::text("0 warnings")) }
    ).unwrap();

    harness.mcp_server.tools().register_fn(
        "faulty_plugin",
        None,
        json!({ "type": "object" }),
        |_c, _a| async move { Ok(CallToolResult::error("Plugin crashed on syntax boundary")) }
    ).unwrap();

    // Connect client and execute orchestration pipeline
    let (ct, st) = ChannelTransport::pair(32);
    let srv = harness.mcp_server.clone();
    tokio::spawn(async move { srv.serve(st).await });

    let client = mcp_protocol::client::McpClient::connect(ct, "orchestrator-cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    let mut set = tokio::task::JoinSet::new();

    // Call parser 5 times in parallel
    for i in 0..5 {
        let c = client.clone();
        set.spawn(async move {
            c.call_tool("parser", Some(json!({ "code": format!("fn main() {{ /* {} */ }}", i) }))).await
        });
    }

    // Call linter 5 times in parallel
    for _ in 0..5 {
        let c = client.clone();
        set.spawn(async move {
            c.call_tool("linter", None).await
        });
    }

    // Call faulty plugin 5 times in parallel
    for _ in 0..5 {
        let c = client.clone();
        set.spawn(async move {
            c.call_tool("faulty_plugin", None).await
        });
    }

    let mut success_count = 0;
    let mut error_count = 0;

    while let Some(res) = set.join_next().await {
        let tool_res = res.unwrap().unwrap();
        if tool_res.is_error == Some(true) {
            error_count += 1;
        } else {
            success_count += 1;
        }
    }

    assert_eq!(success_count, 10);
    assert_eq!(error_count, 5);

    // Verify server remains healthy
    client.ping().await.unwrap();
    client.close().await.unwrap();
}

// Scenario 3: Interactive IDE Live Workspace Session (TUI & Web Simultaneous)
#[tokio::test]
async fn test_scenario_3_interactive_ide_workspace_session() {
    let harness = TestHarness::new(4, 2);

    // 1. Initialize Web router and app state
    let web_router = create_router(harness.web_state.clone());

    // 2. Initialize TUI app state
    let mut tui_app = App::new()
        .with_dispatcher(harness.dispatcher.clone())
        .with_resource_monitor(harness.resource_monitor.clone())
        .with_mcp_server(harness.mcp_server.clone());

    // 3. Dispatch 20 concurrent background tasks from web
    for i in 0..20 {
        let _ = harness.dispatcher.dispatch("fast_calc", json!({ "a": i, "b": i * 3 }), Some(TaskPriority::Normal)).unwrap();
    }

    // 4. Simultaneously render TUI
    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();

    for tab in AppTab::all() {
        tui_app.tab = *tab;
        terminal.draw(|f| mcp_tui::ui::draw(f, &mut tui_app)).unwrap();
    }

    // 5. Query Web API Health and Tasks
    let res = tower::ServiceExt::oneshot(
        web_router.clone(),
        axum::http::Request::builder().uri("/api/tasks").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);

    assert_eq!(harness.telemetry.snapshot().completed_tasks_total, 20);
}

// Scenario 4: High-Throughput Code Analysis Burst (Tokio + Rayon Concurrency)
#[tokio::test]
async fn test_scenario_4_high_throughput_code_analysis_burst() {
    let harness = TestHarness::new(8, 4);

    let start = std::time::Instant::now();
    let mut handles = Vec::new();

    // 20 heavy compute tasks
    for i in 0..20 {
        handles.push(harness.dispatcher.dispatch(
            "heavy_compute",
            json!({ "iterations": 10_000 }),
            Some(TaskPriority::Normal),
        ).unwrap());
    }

    // 20 fast I/O tasks
    for i in 0..20 {
        handles.push(harness.dispatcher.dispatch(
            "fast_calc",
            json!({ "a": i, "b": i + 1 }),
            Some(TaskPriority::High),
        ).unwrap());
    }

    for h in handles {
        let out = h.wait().await.unwrap();
        assert_eq!(out.exit_code, 0);
    }

    let elapsed = start.elapsed();
    assert!(elapsed < Duration::from_secs(10));
    assert_eq!(harness.telemetry.snapshot().completed_tasks_total, 40);
}

// Scenario 5: Cancellation & Graceful Teardown under Load
#[tokio::test]
async fn test_scenario_5_cancellation_and_graceful_teardown() {
    let harness = TestHarness::new(4, 2);

    let mut handles = Vec::new();
    for _ in 0..30 {
        let h = harness.dispatcher.dispatch("delay", json!({ "ms": 500 }), Some(TaskPriority::Normal)).unwrap();
        handles.push(h);
    }

    // Cancel every other task
    for (i, h) in handles.iter().enumerate() {
        if i % 2 == 0 {
            h.cancel();
        }
    }

    let mut completed = 0;
    let mut cancelled = 0;

    for h in handles {
        match h.wait().await {
            Ok(_) => completed += 1,
            Err(mcp_core::registry::TaskError::Cancelled) => cancelled += 1,
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    assert_eq!(completed + cancelled, 30);
    assert!(cancelled >= 15);
}

// Scenario 6: Resource Exhaustion & Graceful Fallback Recovery
#[tokio::test]
async fn test_scenario_6_resource_exhaustion_recovery() {
    let harness = TestHarness::new(2, 1);
    let catalog = ModelSelector::default_catalog();

    // Start under normal memory
    let mut snap = harness.resource_monitor.snapshot();
    let initial_decision = ModelSelector::select_best_model(&catalog, 4096, &snap);
    assert!(initial_decision.is_some());

    // Simulate extreme memory pressure (e.g. 99% RAM consumption)
    snap.memory.available_ram_bytes = 10 * 1024 * 1024; // 10 MB
    let pressured_decision = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_eq!(pressured_decision.target, ExecutionTarget::CloudApiFallback);

    // Simulate memory recovery
    snap.memory.available_ram_bytes = 16 * 1024 * 1024 * 1024; // 16 GB recovered
    let recovered_decision = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_ne!(recovered_decision.target, ExecutionTarget::CloudApiFallback);
}

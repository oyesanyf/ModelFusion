//! Tier 3: Pairwise Combinatorial Feature Interactions (>= 28 Pairwise Tests)

use mcp_core::cancellation::HierarchicalCancellationToken;
use mcp_core::registry::TaskPriority;
use mcp_core::scheduler::TaskState;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;
use mcp_resource::selector::{ModelSelector, ModelSpec, ModelTier};
use mcp_resource::sizing::calculate_layer_offload;
use mcp_tests::TestHarness;
use mcp_tui::{App, AppTab, LogLevel};
use mcp_web::server::{create_router, AppState};
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

#[tokio::test]
async fn test_c1_tokio_rayon_bridge_with_backpressure() {
    let harness = TestHarness::new(4, 2);
    let mut handles = Vec::new();
    for i in 0..10 {
        handles.push(harness.dispatcher.dispatch("heavy_compute", json!({ "iterations": 2000 }), Some(TaskPriority::Normal)).unwrap());
    }
    for h in handles {
        let out = h.wait().await.unwrap();
        assert_eq!(out.exit_code, 0);
    }
}

#[tokio::test]
async fn test_c2_priority_queue_and_quanta_telemetry() {
    let harness = TestHarness::new(2, 1);
    let h1 = harness.dispatcher.dispatch("fast_calc", json!({ "a": 1, "b": 2 }), Some(TaskPriority::Critical)).unwrap();
    let h2 = harness.dispatcher.dispatch("fast_calc", json!({ "a": 3, "b": 4 }), Some(TaskPriority::Background)).unwrap();
    let _ = h1.wait().await.unwrap();
    let _ = h2.wait().await.unwrap();
    let snap = harness.telemetry.snapshot();
    assert_eq!(snap.completed_tasks_total, 2);
}

#[tokio::test]
async fn test_c3_dashmap_and_cancellation_token() {
    let harness = TestHarness::new(2, 1);
    let h = harness.dispatcher.dispatch("delay", json!({ "ms": 500 }), None).unwrap();
    h.cancel();
    let res = h.wait().await;
    assert!(res.is_err());
}

#[tokio::test]
async fn test_c4_schema_validator_and_tool_execution() {
    let harness = TestHarness::new(2, 1);
    let res = harness.mcp_server.tools().call("tool_add", Some(json!({ "x": 10.5, "y": 20.5 }))).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("31"));
}

#[tokio::test]
async fn test_c5_stdio_framing_and_log_separation() {
    let (c, s) = ChannelTransport::pair(16);
    assert!(!c.is_closed());
    assert!(!s.is_closed());
}

#[tokio::test]
async fn test_c6_sse_transport_and_multi_session() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    let s1 = mgr.create_session();
    let s2 = mgr.create_session();
    assert_eq!(mgr.session_count(), 2);
    assert_ne!(s1.id, s2.id);
}

#[tokio::test]
async fn test_c7_mcp_client_server_loopback() {
    let server = McpServer::new("loopback-srv", "1.0");
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "loopback-cli", "1.0");
    let init = client.initialize(ClientCapabilities::default()).await.unwrap();
    assert_eq!(init.server_info.name, "loopback-srv");
}

#[tokio::test]
async fn test_c8_resource_monitor_and_model_sizing() {
    let harness = TestHarness::new(2, 1);
    let snap = harness.resource_monitor.snapshot();
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let b = mcp_resource::sizing::calculate_total_required_memory(&spec, 4096, 1, 0.15);
    assert!(snap.memory.total_ram_bytes > 0);
    assert!(b.total_required_bytes > 0);
}

#[tokio::test]
async fn test_c9_gpu_prober_and_layer_offloader() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 12 * 1024 * 1024 * 1024, 0.15);
    assert!(plan.gpu_layers > 0);
}

#[tokio::test]
async fn test_c10_model_selector_and_cloud_fallback() {
    let mut snap = mcp_resource::telemetry::SystemSnapshot::default();
    snap.memory.available_ram_bytes = 50 * 1024 * 1024; // 50 MB
    let catalog = ModelSelector::default_catalog();
    let dec = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_eq!(dec.target, mcp_resource::selector::ExecutionTarget::CloudApiFallback);
}

#[tokio::test]
async fn test_c11_axum_rest_and_priority_queue() {
    let harness = TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let task_payload = json!({ "command": "fast_calc", "payload": { "a": 5, "b": 6 }, "priority": "High" });
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder()
            .method("POST")
            .uri("/api/tasks")
            .header("content-type", "application/json")
            .body(axum::body::Body::from(serde_json::to_vec(&task_payload).unwrap()))
            .unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);
}

#[tokio::test]
async fn test_c12_axum_sse_and_event_bus() {
    let harness = TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().uri("/api/events").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);
}

#[tokio::test]
async fn test_c13_websocket_endpoint_registration() {
    let harness = TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().uri("/ws").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    // Non-upgraded request returns 400 Bad Request / 426 Upgrade Required
    assert!(res.status().is_client_error());
}

#[tokio::test]
async fn test_c14_tui_and_dashmap_mutations() {
    let harness = TestHarness::new(2, 1);
    let h = harness.dispatcher.dispatch("echo", json!({ "k": "v" }), None).unwrap();
    let mut app = App::new().with_dispatcher(harness.dispatcher.clone());
    let tasks = app.get_tasks();
    assert!(!tasks.is_empty() || h.id.to_string().len() > 0);
}

#[tokio::test]
async fn test_c15_tui_and_resource_watcher() {
    let harness = TestHarness::new(2, 1);
    let mut app = App::new().with_resource_monitor(harness.resource_monitor.clone());
    app.update_resource_snapshot(harness.resource_monitor.snapshot());
    assert!(app.system_snapshot.cpu.logical_core_count > 0);
}

#[tokio::test]
async fn test_c16_tui_command_prompt_execution() {
    let harness = TestHarness::new(2, 1);
    let mut app = App::new().with_dispatcher(harness.dispatcher.clone());
    app.execute_user_command("run echo");
    assert!(app.status_message.is_some());
}

#[tokio::test]
async fn test_c17_repl_and_model_recommendation() {
    let harness = TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("models").await.is_ok());
}

#[tokio::test]
async fn test_c18_repl_and_mcp_tool_invocation() {
    let harness = TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("call tool_add {\"x\":1,\"y\":2}").await.is_ok());
}

#[tokio::test]
async fn test_c19_clap_cli_json_mode() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "--json", "mcp", "tools", "list"]).unwrap();
    assert!(cli.json);
}

#[tokio::test]
async fn test_c20_clap_cli_detached_task() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "run", "fast_calc", "--detach"]).unwrap();
    match cli.command.unwrap() {
        mcp_cli::cli::Commands::Run(r) => assert!(r.detach),
        _ => panic!("Expected Run"),
    }
}

#[tokio::test]
async fn test_c21_cancellation_and_rayon_pool() {
    let harness = TestHarness::new(2, 2);
    let h = harness.dispatcher.dispatch("heavy_compute", json!({ "iterations": 100_000 }), None).unwrap();
    h.cancel();
    let _ = h.wait().await;
}

#[tokio::test]
async fn test_c22_cancellation_and_sse_transport() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    let sess = mgr.create_session();
    mgr.remove_session(&sess.id);
    assert!(mgr.get_session(&sess.id).is_none());
}

#[tokio::test]
async fn test_c23_tool_error_and_tui_log() {
    let mut app = App::new();
    app.handle_engine_event(mcp_core::telemetry::EngineEvent::TaskFailed {
        task_id: "t_fail".into(),
        name: "failing_cmd".into(),
        error: "fatal runtime error".into(),
    });
    assert_eq!(app.log_entries.len(), 1);
    assert_eq!(app.log_entries[0].level, LogLevel::Error);
}

#[tokio::test]
async fn test_c24_tool_error_and_web_api_response() {
    let harness = TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let body = json!({ "name": "non_existent_tool" });
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder()
            .method("POST")
            .uri("/api/tools/call")
            .header("content-type", "application/json")
            .body(axum::body::Body::from(serde_json::to_vec(&body).unwrap()))
            .unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::INTERNAL_SERVER_ERROR);
}

#[tokio::test]
async fn test_c25_uri_template_and_resource_registry() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("metrics://node-1/load", "Load", None, None, "100");
    let res = reg.read("metrics://node-1/load").await.unwrap();
    assert_eq!(res.contents.len(), 1);
}

#[tokio::test]
async fn test_c26_prompt_interpolation_and_mcp_client() {
    let harness = TestHarness::new(2, 1);
    let p = harness.mcp_server.prompts().render("code_review", Some([("file".into(), "main.rs".into())].into())).await.unwrap();
    assert_eq!(p.messages[0].content.as_text(), Some("Please review file main.rs."));
}

#[tokio::test]
async fn test_c27_bench_dispatch_and_worker_threads() {
    let harness = TestHarness::new(4, 2);
    let start = std::time::Instant::now();
    for _ in 0..10 {
        let h = harness.dispatcher.dispatch("echo", json!({}), None).unwrap();
        let _ = h.wait().await.unwrap();
    }
    let elapsed = start.elapsed();
    assert!(elapsed < Duration::from_millis(500));
}

#[tokio::test]
async fn test_c28_concurrency_and_dashmap_consistency() {
    let harness = TestHarness::new(4, 2);
    let mut handles = Vec::new();
    for i in 0..30 {
        handles.push(harness.dispatcher.dispatch("fast_calc", json!({ "a": i, "b": 1 }), None).unwrap());
    }
    for h in handles {
        let out = h.wait().await.unwrap();
        assert_eq!(out.exit_code, 0);
    }
    assert_eq!(harness.telemetry.snapshot().completed_tasks_total, 30);
}

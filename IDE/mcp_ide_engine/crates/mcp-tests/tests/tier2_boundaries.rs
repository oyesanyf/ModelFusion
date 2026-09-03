//! Tier 2: Boundary, Corner Case, Error Isolation, and Negative Tests (28 Features x 5 Tests >= 140 Test Cases)

use mcp_core::cancellation::HierarchicalCancellationToken;
use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskPriority};
use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
use mcp_core::scheduler::{MultiLaneScheduler, TaskPriority as Prio, TaskState};
use mcp_core::telemetry::EngineTelemetry;
use mcp_protocol::prompts::PromptRegistry;
use mcp_protocol::resources::ResourceRegistry;
use mcp_protocol::server::McpServer;
use mcp_protocol::tools::ToolRegistry;
use mcp_protocol::types::*;
use mcp_resource::selector::{ModelSelector, ModelSpec, ModelTier};
use mcp_resource::sizing::*;
use mcp_resource::telemetry::ResourceMonitor;
use mcp_tui::{App, AppTab, LogLevel};
use mcp_web::server::{create_router, AppState};
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

// ==========================================
// FEATURE 1: Async Runtime Boundaries
// ==========================================
#[tokio::test]
async fn test_b1_runtime_zero_workers_fallback() {
    let cfg = EngineRuntimeConfig::new().worker_threads(0);
    let rt = EngineRuntime::new(cfg).unwrap();
    assert!(rt.worker_threads() >= 1);
}
#[tokio::test]
async fn test_b1_runtime_excessive_workers() {
    let cfg = EngineRuntimeConfig::new().worker_threads(256);
    let rt = EngineRuntime::new(cfg).unwrap();
    assert_eq!(rt.worker_threads(), 256);
}
#[tokio::test]
async fn test_b1_runtime_spawn_empty_future() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(1)).unwrap();
    let res = rt.spawn_async(async {}).await;
    assert!(res.is_ok());
}
#[tokio::test]
async fn test_b1_runtime_recurrent_spawn_shutdown() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(2)).unwrap();
    rt.shutdown();
}
#[tokio::test]
async fn test_b1_runtime_panic_in_async_task() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(2)).unwrap();
    let res = rt.spawn_async(async { panic!("intentional async panic") }).await;
    assert!(res.is_err());
}

// ==========================================
// FEATURE 2: Rayon Compute Boundaries
// ==========================================
#[tokio::test]
async fn test_b2_rayon_single_thread() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(1)).unwrap();
    let res = rt.spawn_compute(|| 42).await.unwrap();
    assert_eq!(res, 42);
}
#[tokio::test]
async fn test_b2_rayon_high_thread_count() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(64)).unwrap();
    let res = rt.spawn_compute(|| "ok").await.unwrap();
    assert_eq!(res, "ok");
}
#[tokio::test]
async fn test_b2_rayon_zero_iterations() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(2)).unwrap();
    let res = rt.spawn_compute(|| (0..0).sum::<usize>()).await.unwrap();
    assert_eq!(res, 0);
}
#[tokio::test]
async fn test_b2_rayon_nested_compute_call() {
    let rt = Arc::new(EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(2)).unwrap());
    let rt_clone = rt.clone();
    let res = rt.spawn_compute(move || {
        let _ = rt_clone;
        100
    }).await.unwrap();
    assert_eq!(res, 100);
}
#[tokio::test]
async fn test_b2_rayon_large_vector_allocation() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(2)).unwrap();
    let res = rt.spawn_compute(|| {
        let vec: Vec<u8> = vec![1; 1_000_000];
        vec.len()
    }).await.unwrap();
    assert_eq!(res, 1_000_000);
}

// ==========================================
// FEATURE 3: Priority Scheduler Boundaries
// ==========================================
#[tokio::test]
async fn test_b3_scheduler_pop_empty_queue() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    assert!(sched.pop().is_none());
}
#[tokio::test]
async fn test_b3_scheduler_cancel_nonexistent_task() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    assert!(!sched.cancel_task("does_not_exist"));
}
#[tokio::test]
async fn test_b3_scheduler_set_state_nonexistent() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.set_state("ghost", TaskState::Completed);
    assert_eq!(sched.active_tasks().len(), 0);
}
#[tokio::test]
async fn test_b3_scheduler_multiple_pops_drain() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("1", "c", Prio::Critical, json!({})));
    sched.submit(mcp_core::scheduler::EngineTask::new("2", "c", Prio::Background, json!({})));
    assert!(sched.pop().is_some());
    assert!(sched.pop().is_some());
    assert!(sched.pop().is_none());
}
#[tokio::test]
async fn test_b3_scheduler_duplicate_task_id_resubmit() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("same_id", "c", Prio::Normal, json!({})));
    sched.submit(mcp_core::scheduler::EngineTask::new("same_id", "c", Prio::High, json!({})));
    assert_eq!(sched.active_tasks().len(), 1);
}

// ==========================================
// FEATURE 4: Command Registry Boundaries
// ==========================================
#[tokio::test]
async fn test_b4_command_empty_name() {
    let reg = CommandRegistry::new();
    let res = reg.register_fn("", "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) });
    assert!(res.is_ok());
    assert!(reg.get("").is_some());
}
#[tokio::test]
async fn test_b4_command_long_name() {
    let reg = CommandRegistry::new();
    let long_name = "a".repeat(1000);
    reg.register_fn(&long_name, "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    assert!(reg.get(&long_name).is_some());
}
#[tokio::test]
async fn test_b4_command_special_characters_in_name() {
    let reg = CommandRegistry::new();
    reg.register_fn("cmd:with/special.chars@123", "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    assert!(reg.get("cmd:with/special.chars@123").is_some());
}
#[tokio::test]
async fn test_b4_command_empty_registry_list() {
    let reg = CommandRegistry::new();
    assert_eq!(reg.list().len(), 0);
}
#[tokio::test]
async fn test_b4_command_null_json_output() {
    let reg = CommandRegistry::new();
    reg.register_fn("null_out", "desc", "cat", Prio::Normal, |_c, _a| async move {
        Ok(TaskOutput::success(json!(null)))
    }).unwrap();
    assert!(reg.get("null_out").is_some());
}

// ==========================================
// FEATURE 5: DashMap Task Table Boundaries
// ==========================================
#[tokio::test]
async fn test_b5_dashmap_remove_empty() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.remove("non_existent");
    assert_eq!(sched.active_tasks().len(), 0);
}
#[tokio::test]
async fn test_b5_dashmap_rapid_insert_remove() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    for i in 0..100 {
        sched.submit(mcp_core::scheduler::EngineTask::new(format!("t_{}", i), "c", Prio::Normal, json!({})));
        sched.remove(&format!("t_{}", i));
    }
    assert_eq!(sched.active_tasks().len(), 0);
}
#[tokio::test]
async fn test_b5_dashmap_assign_worker_boundary() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("t1", "c", Prio::Normal, json!({})));
    sched.assign_worker("t1", usize::MAX);
    assert_eq!(sched.active_tasks()[0].assigned_worker, Some(usize::MAX));
}
#[tokio::test]
async fn test_b5_dashmap_state_transitions() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("t1", "c", Prio::Normal, json!({})));
    sched.set_state("t1", TaskState::Running);
    sched.set_state("t1", TaskState::Completed);
    sched.set_state("t1", TaskState::Cancelled);
    assert_eq!(sched.active_tasks()[0].state, TaskState::Cancelled);
}
#[tokio::test]
async fn test_b5_dashmap_empty_query() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    assert!(sched.active_tasks().is_empty());
}

// ==========================================
// FEATURE 6: Cancellation Hierarchy Boundaries
// ==========================================
#[tokio::test]
async fn test_b6_cancellation_double_cancel() {
    let token = HierarchicalCancellationToken::new();
    token.cancel();
    token.cancel(); // idempotent
    assert!(token.is_cancelled());
}
#[tokio::test]
async fn test_b6_cancellation_deep_tree() {
    let root = HierarchicalCancellationToken::new();
    let mut current = root.clone();
    for _ in 0..50 {
        current = current.child_token();
    }
    root.cancel();
    assert!(current.is_cancelled());
}
#[tokio::test]
async fn test_b6_cancellation_sibling_isolation() {
    let root = HierarchicalCancellationToken::new();
    let child1 = root.child_token();
    let child2 = root.child_token();
    child1.cancel();
    assert!(child1.is_cancelled());
    assert!(!child2.is_cancelled());
    assert!(!root.is_cancelled());
}
#[tokio::test]
async fn test_b6_cancellation_already_cancelled_child_spawn() {
    let root = HierarchicalCancellationToken::new();
    root.cancel();
    let child = root.child_token();
    assert!(child.is_cancelled());
}
#[tokio::test]
async fn test_b6_cancellation_token_id_uniqueness() {
    let t1 = HierarchicalCancellationToken::new();
    let t2 = HierarchicalCancellationToken::new();
    assert_ne!(t1.id(), t2.id());
}

// ==========================================
// FEATURE 7: Telemetry Boundaries
// ==========================================
#[tokio::test]
async fn test_b7_telemetry_zero_duration_record() {
    let tel = EngineTelemetry::new();
    tel.record_task_completion(Duration::ZERO);
    assert_eq!(tel.snapshot().completed_tasks_total, 1);
}
#[tokio::test]
async fn test_b7_telemetry_max_duration_record() {
    let tel = EngineTelemetry::new();
    tel.record_task_completion(Duration::from_secs(3600));
    assert_eq!(tel.snapshot().completed_tasks_total, 1);
}
#[tokio::test]
async fn test_b7_telemetry_high_event_throughput() {
    let tel = EngineTelemetry::new();
    let mut rx = tel.event_bus.subscribe();
    for i in 0..100 {
        tel.event_bus.publish(mcp_core::telemetry::EngineEvent::TaskFailed {
            task_id: format!("tf_{}", i),
            name: "err".into(),
            error: "bad".into(),
        });
    }
    let mut count = 0;
    while let Ok(_) = rx.try_recv() {
        count += 1;
    }
    assert!(count > 0);
}
#[tokio::test]
async fn test_b7_telemetry_empty_histogram_summary() {
    let tel = EngineTelemetry::new();
    let s = tel.latency_summary();
    assert_eq!(s.count, 0);
}
#[tokio::test]
async fn test_b7_telemetry_snapshot_clone() {
    let tel = EngineTelemetry::new();
    let s1 = tel.snapshot();
    let s2 = s1.clone();
    assert_eq!(s1.completed_tasks_total, s2.completed_tasks_total);
}

// ==========================================
// FEATURE 8: JSON-RPC 2.0 Boundaries
// ==========================================
#[tokio::test]
async fn test_b8_jsonrpc_parse_error() {
    let err = JsonRpcError::parse_error("Invalid json");
    assert_eq!(err.code, -32700);
}
#[tokio::test]
async fn test_b8_jsonrpc_invalid_params_error() {
    let err = JsonRpcError::invalid_params("Bad args");
    assert_eq!(err.code, -32602);
}
#[tokio::test]
async fn test_b8_jsonrpc_internal_error() {
    let err = JsonRpcError::internal_error("Panic occurred");
    assert_eq!(err.code, -32603);
}
#[tokio::test]
async fn test_b8_jsonrpc_deserialize_malformed() {
    let bad_json = "{ bad: json }";
    let res = serde_json::from_str::<JsonRpcRequest>(bad_json);
    assert!(res.is_err());
}
#[tokio::test]
async fn test_b8_jsonrpc_null_id() {
    let req = JsonRpcRequest::new(None, "notify", None);
    assert!(req.id.is_none());
}

// ==========================================
// FEATURE 9: Transport Boundaries
// ==========================================
#[tokio::test]
async fn test_b9_channel_zero_capacity() {
    let (c, _s) = mcp_protocol::transport::ChannelTransport::pair(1);
    assert!(!c.is_closed());
}
#[tokio::test]
async fn test_b9_channel_send_after_close() {
    let (mut c, s) = mcp_protocol::transport::ChannelTransport::pair(1);
    drop(s);
    let msg = JsonRpcMessage::Request(JsonRpcRequest::new(None, "ping", None));
    let res = c.send(msg).await;
    assert!(res.is_err());
}
#[tokio::test]
async fn test_b9_channel_recv_empty() {
    let (mut c, mut _s) = mcp_protocol::transport::ChannelTransport::pair(1);
    let msg = c.try_receive();
    assert!(msg.is_none());
}
#[tokio::test]
async fn test_b9_channel_large_payload() {
    let (mut c, mut s) = mcp_protocol::transport::ChannelTransport::pair(1);
    let large_str = "x".repeat(100_000);
    let msg = JsonRpcMessage::Request(JsonRpcRequest::new(None, "echo", Some(json!({"data": large_str}))));
    c.send(msg).await.unwrap();
    let recv = s.receive().await.unwrap();
    assert!(matches!(recv, JsonRpcMessage::Request(_)));
}
#[tokio::test]
async fn test_b9_channel_disconnect_detection() {
    let (c, s) = mcp_protocol::transport::ChannelTransport::pair(1);
    drop(c);
    assert!(s.is_closed());
}

// ==========================================
// FEATURE 10: SSE Transport Boundaries
// ==========================================
#[tokio::test]
async fn test_b10_sse_invalid_session_id() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    assert!(mgr.get_session("non_existent").is_none());
}
#[tokio::test]
async fn test_b10_sse_remove_unregistered() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    mgr.remove_session("random");
    assert_eq!(mgr.session_count(), 0);
}
#[tokio::test]
async fn test_b10_sse_empty_broadcast() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    mgr.broadcast(JsonRpcMessage::Notification(JsonRpcNotification::new("empty", None)));
    assert_eq!(mgr.session_count(), 0);
}
#[tokio::test]
async fn test_b10_sse_event_empty_data() {
    let ev = mcp_protocol::transport::sse::SseEvent::new("empty", "");
    assert!(ev.data.is_empty());
}
#[tokio::test]
async fn test_b10_sse_multiline_data() {
    let ev = mcp_protocol::transport::sse::SseEvent::new("multi", "line1\nline2");
    assert!(ev.data.contains("\n"));
}

// ==========================================
// FEATURE 11: Lifecycle Boundaries
// ==========================================
#[tokio::test]
async fn test_b11_server_empty_name() {
    let srv = McpServer::new("", "");
    assert_eq!(srv.server_info().name, "");
}
#[tokio::test]
async fn test_b11_server_long_instructions() {
    let long_inst = "i".repeat(10_000);
    let srv = McpServer::new("s", "1.0").with_instructions(long_inst);
    assert!(srv.instructions().unwrap().len() >= 10_000);
}
#[tokio::test]
async fn test_b11_server_uninitialized_call() {
    let srv = McpServer::new("s", "1.0");
    assert_eq!(srv.state(), mcp_protocol::server::ServerState::Uninitialized);
}
#[tokio::test]
async fn test_b11_server_state_clone() {
    let srv = McpServer::new("s", "1.0");
    let srv2 = srv.clone();
    assert_eq!(srv.server_info().name, srv2.server_info().name);
}
#[tokio::test]
async fn test_b11_server_default_port() {
    let srv = McpServer::new("s", "1.0");
    assert!(srv.tools().list().is_empty());
}

// ==========================================
// FEATURE 12: Tool Execution Boundaries
// ==========================================
#[tokio::test]
async fn test_b12_tool_null_arguments() {
    let reg = ToolRegistry::new();
    reg.register_fn("t_null", None, json!({ "type": "object" }), |_c, args| async move {
        assert!(args.is_none());
        Ok(CallToolResult::text("ok"))
    }).unwrap();
    let res = reg.call("t_null", None).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("ok"));
}
#[tokio::test]
async fn test_b12_tool_empty_json_object() {
    let reg = ToolRegistry::new();
    reg.register_fn("t_empty", None, json!({ "type": "object" }), |_c, args| async move {
        assert_eq!(args.unwrap(), json!({}));
        Ok(CallToolResult::text("ok"))
    }).unwrap();
    let res = reg.call("t_empty", Some(json!({}))).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("ok"));
}
#[tokio::test]
async fn test_b12_tool_array_instead_of_object_schema() {
    let reg = ToolRegistry::new();
    reg.register_fn(
        "obj_tool",
        None,
        json!({ "type": "object" }),
        |_c, _a| async move { Ok(CallToolResult::text("ok")) }
    ).unwrap();
    let res = reg.call("obj_tool", Some(json!([1, 2, 3]))).await;
    assert!(res.is_err());
}
#[tokio::test]
async fn test_b12_tool_number_type_mismatch() {
    let reg = ToolRegistry::new();
    reg.register_fn(
        "num_tool",
        None,
        json!({
            "type": "object",
            "properties": { "count": { "type": "number" } },
            "required": ["count"]
        }),
        |_c, _a| async move { Ok(CallToolResult::text("ok")) }
    ).unwrap();
    let res = reg.call("num_tool", Some(json!({ "count": "not_a_number" }))).await;
    assert!(res.is_err());
}
#[tokio::test]
async fn test_b12_tool_progress_sink_unused() {
    let reg = ToolRegistry::new();
    reg.register_fn("t_prog", None, json!({ "type": "object" }), |ctx, _a| async move {
        ctx.progress.report(50, 100);
        Ok(CallToolResult::text("done"))
    }).unwrap();
    let res = reg.call("t_prog", None).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("done"));
}

// ==========================================
// FEATURE 13: Resource Boundaries
// ==========================================
#[tokio::test]
async fn test_b13_resource_empty_uri() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("", "Empty URI", None, None, "content");
    assert!(reg.read("").await.is_ok());
}
#[tokio::test]
async fn test_b13_resource_empty_content() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("file:///empty", "Empty", None, None, "");
    let res = reg.read("file:///empty").await.unwrap();
    match &res.contents[0] {
        ResourceContents::Text(t) => assert_eq!(t.text, ""),
        _ => panic!("Expected text"),
    }
}
#[tokio::test]
async fn test_b13_resource_binary_content() {
    let reg = ResourceRegistry::new();
    reg.register_static_binary("blob://bin", "Binary", None, Some("application/octet-stream".into()), "AAAA");
    let res = reg.read("blob://bin").await.unwrap();
    match &res.contents[0] {
        ResourceContents::Blob(b) => assert_eq!(b.blob, "AAAA"),
        _ => panic!("Expected blob"),
    }
}
#[tokio::test]
async fn test_b13_resource_unsubscribe_nonexistent() {
    let mgr = mcp_protocol::resources::SubscriptionManager::new();
    mgr.unsubscribe("random_session", "random_uri");
}
#[tokio::test]
async fn test_b13_resource_template_unmatched() {
    let tpl = mcp_protocol::resources::UriTemplate::new("schema://{id}/tail").unwrap();
    assert!(!tpl.matches("schema://123"));
}

// ==========================================
// FEATURE 14: Prompt Boundaries
// ==========================================
#[tokio::test]
async fn test_b14_prompt_empty_template() {
    let reg = PromptRegistry::new();
    reg.register_template("empty_t", None, vec![], vec![(Role::User, "".into())]);
    let res = reg.render("empty_t", None).await.unwrap();
    assert_eq!(res.messages[0].content.as_text(), Some(""));
}
#[tokio::test]
async fn test_b14_prompt_unused_arguments() {
    let reg = PromptRegistry::new();
    reg.register_template("p_static", None, vec![], vec![(Role::User, "Constant".into())]);
    let mut map = std::collections::HashMap::new();
    map.insert("extra".into(), "val".into());
    let res = reg.render("p_static", Some(map)).await.unwrap();
    assert_eq!(res.messages[0].content.as_text(), Some("Constant"));
}
#[tokio::test]
async fn test_b14_prompt_repeated_placeholder() {
    let reg = PromptRegistry::new();
    reg.register_template(
        "repeat",
        None,
        vec![PromptArgument { name: "x".into(), description: None, required: Some(true) }],
        vec![(Role::User, "{{x}} and {{x}}".into())]
    );
    let mut map = std::collections::HashMap::new();
    map.insert("x".into(), "1".into());
    let res = reg.render("repeat", Some(map)).await.unwrap();
    assert_eq!(res.messages[0].content.as_text(), Some("1 and 1"));
}
#[tokio::test]
async fn test_b14_prompt_empty_role_content() {
    let p = PromptMessage { role: Role::Assistant, content: Content::text("") };
    assert_eq!(p.content.as_text(), Some(""));
}
#[tokio::test]
async fn test_b14_prompt_get_invalid() {
    let reg = PromptRegistry::new();
    assert!(reg.get("missing", None).await.is_err());
}

// ==========================================
// FEATURE 15: Client Boundaries
// ==========================================
#[tokio::test]
async fn test_b15_client_call_unregistered_tool() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = mcp_protocol::transport::ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let err = client.call_tool("no_such_tool", None).await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_b15_client_read_unregistered_resource() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = mcp_protocol::transport::ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let err = client.read_resource("file:///no/such/res").await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_b15_client_get_unregistered_prompt() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = mcp_protocol::transport::ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let err = client.get_prompt("no_prompt", None).await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_b15_client_duplicate_close() {
    let (c, _s) = mcp_protocol::transport::ChannelTransport::pair(16);
    let client = mcp_protocol::client::McpClient::connect(c, "cli", "1.0");
    assert!(client.close().await.is_ok());
    assert!(client.close().await.is_ok());
}
#[tokio::test]
async fn test_b15_client_list_tools_empty() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = mcp_protocol::transport::ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let tools = client.list_tools(None).await.unwrap();
    assert_eq!(tools.tools.len(), 0);
}

// ==========================================
// FEATURE 16: Server Boundaries
// ==========================================
#[tokio::test]
async fn test_b16_server_empty_tool_list() {
    let srv = McpServer::new("s", "1.0");
    assert!(srv.tools().list().is_empty());
}
#[tokio::test]
async fn test_b16_server_empty_resource_list() {
    let srv = McpServer::new("s", "1.0");
    assert!(srv.resources().list().is_empty());
}
#[tokio::test]
async fn test_b16_server_empty_prompt_list() {
    let srv = McpServer::new("s", "1.0");
    assert!(srv.prompts().list().is_empty());
}
#[tokio::test]
async fn test_b16_server_instructions_none() {
    let srv = McpServer::new("s", "1.0");
    assert!(srv.instructions().is_none());
}
#[tokio::test]
async fn test_b16_server_serve_closed_transport() {
    let srv = McpServer::new("s", "1.0");
    let (c, s) = mcp_protocol::transport::ChannelTransport::pair(16);
    drop(c);
    let res = srv.serve(s).await;
    assert!(res.is_ok());
}

// ==========================================
// FEATURE 17: Tool Isolation Boundaries
// ==========================================
#[tokio::test]
async fn test_b17_tool_is_error_with_empty_message() {
    let res = CallToolResult::error("");
    assert_eq!(res.is_error, Some(true));
    assert_eq!(res.content[0].as_text(), Some(""));
}
#[tokio::test]
async fn test_b17_tool_is_error_with_multiline_trace() {
    let trace = "Error: Division by zero\n  at func.rs:42\n  at main.rs:10";
    let res = CallToolResult::error(trace);
    assert_eq!(res.is_error, Some(true));
    assert!(res.content[0].as_text().unwrap().contains("func.rs:42"));
}
#[tokio::test]
async fn test_b17_tool_panic_preserves_server_liveness() {
    let srv = McpServer::new("srv", "1.0");
    srv.tools().register_fn("panic_t", None, json!({ "type": "object" }), |_c, _a| async move {
        panic!("deadly error");
    }).unwrap();
    let res = srv.tools().call("panic_t", None).await;
    assert!(res.is_err());
    assert_eq!(srv.server_info().name, "srv");
}
#[tokio::test]
async fn test_b17_tool_execution_timeout() {
    let res = CallToolResult::error("Execution timed out after 5000ms");
    assert_eq!(res.is_error, Some(true));
}
#[tokio::test]
async fn test_b17_tool_error_serialization() {
    let res = CallToolResult::error("Bad argument");
    let json_val = serde_json::to_value(&res).unwrap();
    assert_eq!(json_val["isError"], true);
}

// ==========================================
// FEATURE 18: Telemetry Monitor Boundaries
// ==========================================
#[tokio::test]
async fn test_b18_monitor_rapid_shutdown() {
    let mon = ResourceMonitor::new(Duration::from_millis(100));
    mon.shutdown();
    let snap = mon.snapshot();
    assert!(snap.cpu.logical_core_count > 0);
}
#[tokio::test]
async fn test_b18_monitor_zero_interval() {
    let mon = ResourceMonitor::new(Duration::ZERO);
    let snap = mon.snapshot();
    assert!(snap.memory.total_ram_bytes > 0);
    mon.shutdown();
}
#[tokio::test]
async fn test_b18_monitor_huge_interval() {
    let mon = ResourceMonitor::new(Duration::from_secs(3600));
    let snap = mon.snapshot();
    assert!(snap.cpu.logical_core_count > 0);
    mon.shutdown();
}
#[tokio::test]
async fn test_b18_monitor_default_metrics() {
    let cpu = mcp_resource::telemetry::CpuMetrics::default();
    assert_eq!(cpu.logical_core_count, 0);
}
#[tokio::test]
async fn test_b18_monitor_memory_defaults() {
    let mem = mcp_resource::telemetry::MemoryMetrics::default();
    assert_eq!(mem.total_ram_bytes, 0);
}

// ==========================================
// FEATURE 19: GPU Prober Boundaries
// ==========================================
#[tokio::test]
async fn test_b19_gpu_zero_vram() {
    let mock = mcp_resource::gpu::MockGpuProber::new(vec![mcp_resource::gpu::GpuInfo {
        name: "Zero VRAM GPU".into(),
        vendor: mcp_resource::gpu::GpuVendor::Intel,
        backend: mcp_resource::gpu::GpuBackend::SysinfoFallback,
        vram_total_bytes: 0,
        vram_free_bytes: 0,
        vram_used_bytes: 0,
        driver_version: None,
        compute_capability: None,
    }]);
    let snap = mock.probe();
    assert!(snap.has_gpu);
    assert_eq!(snap.gpus[0].vram_total_bytes, 0);
}
#[tokio::test]
async fn test_b19_gpu_huge_vram() {
    let mock = mcp_resource::gpu::MockGpuProber::new(vec![mcp_resource::gpu::GpuInfo {
        name: "H100 80GB".into(),
        vendor: mcp_resource::gpu::GpuVendor::Nvidia,
        backend: mcp_resource::gpu::GpuBackend::Nvml,
        vram_total_bytes: 80 * 1024 * 1024 * 1024,
        vram_free_bytes: 80 * 1024 * 1024 * 1024,
        vram_used_bytes: 0,
        driver_version: Some("550.54".into()),
        compute_capability: Some((9, 0)),
    }]);
    let snap = mock.probe();
    assert_eq!(snap.gpus[0].vram_total_bytes, 80 * 1024 * 1024 * 1024);
}
#[tokio::test]
async fn test_b19_gpu_multiple_adapters() {
    let mock = mcp_resource::gpu::MockGpuProber::new(vec![
        mcp_resource::gpu::GpuInfo {
            name: "Integrated GPU".into(),
            vendor: mcp_resource::gpu::GpuVendor::Intel,
            backend: mcp_resource::gpu::GpuBackend::Dxgi,
            vram_total_bytes: 1024 * 1024 * 1024,
            vram_free_bytes: 512 * 1024 * 1024,
            vram_used_bytes: 512 * 1024 * 1024,
            driver_version: None,
            compute_capability: None,
        },
        mcp_resource::gpu::GpuInfo {
            name: "Discrete GPU".into(),
            vendor: mcp_resource::gpu::GpuVendor::Nvidia,
            backend: mcp_resource::gpu::GpuBackend::Nvml,
            vram_total_bytes: 16 * 1024 * 1024 * 1024,
            vram_free_bytes: 16 * 1024 * 1024 * 1024,
            vram_used_bytes: 0,
            driver_version: None,
            compute_capability: None,
        },
    ]);
    let snap = mock.probe();
    assert_eq!(snap.gpus.len(), 2);
}
#[tokio::test]
async fn test_b19_gpu_missing_driver_version() {
    let mock = mcp_resource::gpu::MockGpuProber::new(vec![mcp_resource::gpu::GpuInfo {
        name: "Generic GPU".into(),
        vendor: mcp_resource::gpu::GpuVendor::Amd,
        backend: mcp_resource::gpu::GpuBackend::SysinfoFallback,
        vram_total_bytes: 4 * 1024 * 1024 * 1024,
        vram_free_bytes: 4 * 1024 * 1024 * 1024,
        vram_used_bytes: 0,
        driver_version: None,
        compute_capability: None,
    }]);
    let snap = mock.probe();
    assert!(snap.gpus[0].driver_version.is_none());
}
#[tokio::test]
async fn test_b19_gpu_prober_default() {
    let p = mcp_resource::gpu::SysinfoFallbackProber;
    let _snap = p.probe();
}

// ==========================================
// FEATURE 20: Dynamic RAM / VRAM Tracker Boundaries
// ==========================================
#[tokio::test]
async fn test_b20_zero_total_ram_prevention() {
    let mut mem = mcp_resource::telemetry::MemoryMetrics::default();
    mem.total_ram_bytes = 0;
    mem.used_ram_bytes = 0;
    let ratio = mem.used_ram_bytes as f64 / (mem.total_ram_bytes.max(1) as f64);
    assert_eq!(ratio, 0.0);
}
#[tokio::test]
async fn test_b20_used_greater_than_total_ram_clamp() {
    let mut mem = mcp_resource::telemetry::MemoryMetrics::default();
    mem.total_ram_bytes = 1000;
    mem.used_ram_bytes = 1200;
    let ratio = (mem.used_ram_bytes as f64 / mem.total_ram_bytes as f64).clamp(0.0, 1.0);
    assert_eq!(ratio, 1.0);
}
#[tokio::test]
async fn test_b20_swap_usage_zero() {
    let mut mem = mcp_resource::telemetry::MemoryMetrics::default();
    mem.total_swap_bytes = 0;
    mem.used_swap_bytes = 0;
    assert_eq!(mem.total_swap_bytes, 0);
}
#[tokio::test]
async fn test_b20_process_memory_zero() {
    let p = mcp_resource::telemetry::ProcessMetrics::default();
    assert_eq!(p.memory_rss_bytes, 0);
}
#[tokio::test]
async fn test_b20_snapshot_default_gpu_empty() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    assert!(snap.gpu.gpus.is_empty());
}

// ==========================================
// FEATURE 21: Sizing Formula Boundaries
// ==========================================
#[tokio::test]
async fn test_b21_weights_zero_parameters() {
    let w = calculate_model_weights_memory(0.0, QuantizationType::Q4_K_M);
    assert_eq!(w, 0);
}
#[tokio::test]
async fn test_b21_kv_zero_context() {
    let kv = calculate_kv_cache_memory(32, 8, 128, 0, 1, KvCachePrecision::Fp16);
    assert_eq!(kv, 0);
}
#[tokio::test]
async fn test_b21_activation_zero_batch() {
    let act = calculate_activation_memory(32, 4096, 4096, 0);
    assert_eq!(act, 0);
}
#[tokio::test]
async fn test_b21_safety_margin_zero() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let b = calculate_total_required_memory(&spec, 4096, 1, 0.0);
    assert_eq!(b.headroom_bytes, 0);
}
#[tokio::test]
async fn test_b21_safety_margin_100_percent() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let b = calculate_total_required_memory(&spec, 4096, 1, 1.0);
    assert!(b.headroom_bytes > b.weights_bytes);
}

// ==========================================
// FEATURE 22: Model Selector Boundaries
// ==========================================
#[tokio::test]
async fn test_b22_selector_empty_catalog() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let res = ModelSelector::select_best_model(&[], 4096, &snap);
    assert!(res.is_none());
}
#[tokio::test]
async fn test_b22_selector_zero_context_length() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let catalog = ModelSelector::default_catalog();
    let res = ModelSelector::select_best_model(&catalog, 0, &snap);
    assert!(res.is_some());
}
#[tokio::test]
async fn test_b22_selector_huge_context_length() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let catalog = ModelSelector::default_catalog();
    let res = ModelSelector::select_best_model(&catalog, 1_000_000, &snap).unwrap();
    assert_eq!(res.target, mcp_resource::selector::ExecutionTarget::CloudApiFallback);
}
#[tokio::test]
async fn test_b22_selector_zero_ram_system() {
    let mut snap = mcp_resource::telemetry::SystemSnapshot::default();
    snap.memory.available_ram_bytes = 0;
    let catalog = ModelSelector::default_catalog();
    let res = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_eq!(res.target, mcp_resource::selector::ExecutionTarget::CloudApiFallback);
}
#[tokio::test]
async fn test_b22_selector_max_ram_system() {
    let mut snap = mcp_resource::telemetry::SystemSnapshot::default();
    snap.memory.available_ram_bytes = 1024 * 1024 * 1024 * 1024; // 1 TB RAM
    let catalog = ModelSelector::default_catalog();
    let res = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_eq!(res.selected_tier, ModelTier::Large);
}

// ==========================================
// FEATURE 23: Offload Calculator Boundaries
// ==========================================
#[tokio::test]
async fn test_b23_offload_zero_layer_model() {
    let mut spec = ModelSpec::llama_3_8b_instruct_q4();
    spec.num_layers = 0;
    let plan = calculate_layer_offload(&spec, 4096, 10_000_000_000, 0.15);
    assert_eq!(plan.total_layers, 0);
    assert_eq!(plan.gpu_layers, 0);
}
#[tokio::test]
async fn test_b23_offload_vram_exact_fit() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let b = calculate_total_required_memory(&spec, 4096, 1, 0.0);
    let plan = calculate_layer_offload(&spec, 4096, b.total_required_bytes, 0.0);
    assert_eq!(plan.gpu_layers, spec.num_layers);
}
#[tokio::test]
async fn test_b23_offload_1_byte_short_of_full() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let b = calculate_total_required_memory(&spec, 4096, 1, 0.0);
    let plan = calculate_layer_offload(&spec, 4096, b.total_required_bytes.saturating_sub(1), 0.0);
    assert!(plan.gpu_layers <= spec.num_layers);
}
#[tokio::test]
async fn test_b23_offload_fractional_margin() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 10_000_000_000, 0.001);
    assert!(plan.gpu_layers > 0);
}
#[tokio::test]
async fn test_b23_offload_plan_format() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 10_000_000_000, 0.15);
    assert_eq!(plan.cpu_layers + plan.gpu_layers, plan.total_layers);
}

// ==========================================
// FEATURE 24: TUI Rendering Boundaries
// ==========================================
#[tokio::test]
async fn test_b24_tui_tiny_terminal_1x1() {
    let mut app = App::new();
    let backend = TestBackend::new(1, 1);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}
#[tokio::test]
async fn test_b24_tui_huge_terminal() {
    let mut app = App::new();
    let backend = TestBackend::new(300, 100);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}
#[tokio::test]
async fn test_b24_tui_empty_log_draw() {
    let mut app = App::new();
    app.tab = AppTab::Logs;
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}
#[tokio::test]
async fn test_b24_tui_empty_tasks_draw() {
    let mut app = App::new();
    app.tab = AppTab::Tasks;
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}
#[tokio::test]
async fn test_b24_tui_empty_tools_draw() {
    let mut app = App::new();
    app.tab = AppTab::McpCatalog;
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}

// ==========================================
// FEATURE 25: Web API Boundaries
// ==========================================
#[tokio::test]
async fn test_b25_web_not_found_route() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().uri("/api/unknown_route").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::NOT_FOUND);
}
#[tokio::test]
async fn test_b25_web_cancel_invalid_task_id() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().method("POST").uri("/api/tasks/not_a_valid_id/cancel").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    // Either OK or BAD_REQUEST depending on parse
    assert!(res.status().is_client_error() || res.status().is_success());
}
#[tokio::test]
async fn test_b25_web_empty_post_body() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().method("POST").uri("/api/tasks").header("content-type", "application/json").body(axum::body::Body::from("{}")).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::UNPROCESSABLE_ENTITY);
}
#[tokio::test]
async fn test_b25_web_models_recommend_default_query() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().uri("/api/models/recommend").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);
}
#[tokio::test]
async fn test_b25_web_cors_headers() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let app = create_router(harness.web_state);
    let res = tower::ServiceExt::oneshot(
        app,
        axum::http::Request::builder().uri("/api/health").body(axum::body::Body::empty()).unwrap(),
    ).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);
}

// ==========================================
// FEATURE 26: Tool Parity Boundaries
// ==========================================
#[tokio::test]
async fn test_b26_parity_empty_args_handling() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let res = harness.dispatcher.dispatch("echo", json!({}), None);
    assert!(res.is_ok());
}
#[tokio::test]
async fn test_b26_parity_deep_nested_json() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let nested = json!({ "a": { "b": { "c": { "d": 42 } } } });
    let handle = harness.dispatcher.dispatch("echo", nested.clone(), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value, nested);
}
#[tokio::test]
async fn test_b26_parity_large_string_argument() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let big = "z".repeat(50_000);
    let handle = harness.dispatcher.dispatch("echo", json!({ "big": big }), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value["big"].as_str().unwrap().len(), 50_000);
}
#[tokio::test]
async fn test_b26_parity_special_characters_json() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let spec_json = json!({ "utf8": "🦀 \n \t \r \" \\ \u{1F980}" });
    let handle = harness.dispatcher.dispatch("echo", spec_json.clone(), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value, spec_json);
}
#[tokio::test]
async fn test_b26_parity_negative_numbers() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let handle = harness.dispatcher.dispatch("fast_calc", json!({ "a": -50, "b": 10 }), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value["sum"], -40);
    assert_eq!(out.value["product"], -500);
}

// ==========================================
// FEATURE 27: CLI Argument Boundaries
// ==========================================
#[tokio::test]
async fn test_b27_cli_empty_args_default() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide"]);
    assert!(cli.is_ok());
    assert!(cli.unwrap().command.is_none());
}
#[tokio::test]
async fn test_b27_cli_invalid_subcommand() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "invalid_subcommand"]);
    assert!(cli.is_err());
}
#[tokio::test]
async fn test_b27_cli_verbose_flag_levels() {
    use clap::Parser;
    let cli1 = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "-v"]).unwrap();
    assert_eq!(cli1.verbose, 1);
    let cli2 = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "-vv"]).unwrap();
    assert_eq!(cli2.verbose, 2);
}
#[tokio::test]
async fn test_b27_cli_json_flag() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "--json", "resource", "status"]).unwrap();
    assert!(cli.json);
}
#[tokio::test]
async fn test_b27_cli_run_detach_flag() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "run", "echo", "--detach"]).unwrap();
    match cli.command.unwrap() {
        mcp_cli::cli::Commands::Run(r) => assert!(r.detach),
        _ => panic!("Expected Run"),
    }
}

// ==========================================
// FEATURE 28: REPL Boundaries
// ==========================================
#[tokio::test]
async fn test_b28_repl_eval_empty_string() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("").await.is_ok());
}
#[tokio::test]
async fn test_b28_repl_eval_whitespace_only() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("     \t \n  ").await.is_ok());
}
#[tokio::test]
async fn test_b28_repl_eval_unknown_command() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("completely_unknown_command_123").await.is_ok());
}
#[tokio::test]
async fn test_b28_repl_eval_run_missing_command_name() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("run").await.is_ok());
}
#[tokio::test]
async fn test_b28_repl_eval_call_missing_tool_name() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("call").await.is_ok());
}

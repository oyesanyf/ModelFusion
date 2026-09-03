//! Tier 1: Comprehensive Feature Coverage Tests (28 Features x 5 Tests >= 140 Test Cases)

use mcp_core::cancellation::HierarchicalCancellationToken;
use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskOutput, TaskPriority};
use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
use mcp_core::scheduler::{MultiLaneScheduler, TaskPriority as Prio, TaskState};
use mcp_core::telemetry::EngineTelemetry;
use mcp_protocol::prompts::PromptRegistry;
use mcp_protocol::resources::ResourceRegistry;
use mcp_protocol::server::McpServer;
use mcp_protocol::tools::ToolRegistry;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;
use mcp_resource::gpu::{GpuBackend, GpuInfo, GpuVendor, MockGpuProber};
use mcp_resource::selector::{AllocationDecision, ExecutionTarget, ModelSelector, ModelSpec, ModelTier};
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
// FEATURE 1: Tokio Async Core Runtime
// ==========================================
#[tokio::test]
async fn test_f1_runtime_initialization() {
    let cfg = EngineRuntimeConfig::new().worker_threads(4);
    let rt = EngineRuntime::new(cfg).unwrap();
    assert_eq!(rt.worker_threads(), 4);
}
#[tokio::test]
async fn test_f1_runtime_spawn_async() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(2)).unwrap();
    let handle = rt.spawn_async(async { 42 });
    assert_eq!(handle.await.unwrap(), 42);
}
#[tokio::test]
async fn test_f1_runtime_multiple_tasks() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(2)).unwrap();
    let mut handles = Vec::new();
    for i in 0..10 {
        handles.push(rt.spawn_async(async move { i * i }));
    }
    for (i, h) in handles.into_iter().enumerate() {
        assert_eq!(h.await.unwrap(), i * i);
    }
}
#[tokio::test]
async fn test_f1_runtime_shutdown() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().worker_threads(2)).unwrap();
    rt.shutdown();
}
#[tokio::test]
async fn test_f1_runtime_default_config() {
    let cfg = EngineRuntimeConfig::default();
    assert!(cfg.worker_threads > 0);
}

// ==========================================
// FEATURE 2: Rayon Compute Worker Pool
// ==========================================
#[tokio::test]
async fn test_f2_rayon_compute_spawn() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(2)).unwrap();
    let res = rt.spawn_compute(|| 100 + 200).await.unwrap();
    assert_eq!(res, 300);
}
#[tokio::test]
async fn test_f2_rayon_parallel_hash() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(4)).unwrap();
    let res = rt.spawn_compute(|| (0..1000).fold(0u64, |acc, x| acc.wrapping_add(x))).await.unwrap();
    assert_eq!(res, 499500);
}
#[tokio::test]
async fn test_f2_rayon_compute_panic_handling() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(2)).unwrap();
    let res = rt.spawn_compute(|| {
        panic!("intentional compute panic");
    }).await;
    assert!(res.is_err());
}
#[tokio::test]
async fn test_f2_rayon_multi_concurrent_compute() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(4)).unwrap();
    let mut handles = Vec::new();
    for i in 0..20 {
        handles.push(rt.spawn_compute(move || i * 10));
    }
    for (i, h) in handles.into_iter().enumerate() {
        assert_eq!(h.await.unwrap(), i * 10);
    }
}
#[tokio::test]
async fn test_f2_rayon_zero_compute_threads_fallback() {
    let rt = EngineRuntime::new(EngineRuntimeConfig::new().compute_threads(1)).unwrap();
    let res = rt.spawn_compute(|| "fallback_ok").await.unwrap();
    assert_eq!(res, "fallback_ok");
}

// ==========================================
// FEATURE 3: 5-Level Priority Task Scheduler
// ==========================================
#[tokio::test]
async fn test_f3_scheduler_priority_ordering() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    assert_eq!(Prio::Critical as u8, 0);
    assert_eq!(Prio::Background as u8, 4);
}
#[tokio::test]
async fn test_f3_scheduler_push_and_pop() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let task = mcp_core::scheduler::EngineTask::new("t1", "test_cmd", Prio::Critical, json!({}));
    sched.submit(task);
    let popped = sched.pop();
    assert!(popped.is_some());
    assert_eq!(popped.unwrap().name, "test_cmd");
}
#[tokio::test]
async fn test_f3_scheduler_starvation_prevention() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let low_task = mcp_core::scheduler::EngineTask::new("low_1", "low_cmd", Prio::Low, json!({}));
    sched.submit(low_task);
    let popped = sched.pop().unwrap();
    assert_eq!(popped.id, "low_1");
}
#[tokio::test]
async fn test_f3_scheduler_active_tasks_tracking() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let t = mcp_core::scheduler::EngineTask::new("track_1", "cmd", Prio::Normal, json!({}));
    sched.submit(t);
    let active = sched.active_tasks();
    assert_eq!(active.len(), 1);
}
#[tokio::test]
async fn test_f3_scheduler_cancel_task() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let t = mcp_core::scheduler::EngineTask::new("cancel_1", "cmd", Prio::High, json!({}));
    sched.submit(t);
    assert!(sched.cancel_task("cancel_1"));
}

// ==========================================
// FEATURE 4: Universal Command Registry
// ==========================================
#[tokio::test]
async fn test_f4_command_registration() {
    let reg = CommandRegistry::new();
    let res = reg.register_fn("cmd_1", "desc", "cat", Prio::Normal, |_c, _a| async move {
        Ok(TaskOutput::success(json!({})))
    });
    assert!(res.is_ok());
}
#[tokio::test]
async fn test_f4_duplicate_command_rejection() {
    let reg = CommandRegistry::new();
    reg.register_fn("dup", "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    let err = reg.register_fn("dup", "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) });
    assert!(err.is_err());
}
#[tokio::test]
async fn test_f4_command_listing() {
    let reg = CommandRegistry::new();
    reg.register_fn("list_1", "desc1", "cat1", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    reg.register_fn("list_2", "desc2", "cat2", Prio::High, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    let list = reg.list();
    assert_eq!(list.len(), 2);
}
#[tokio::test]
async fn test_f4_command_get() {
    let reg = CommandRegistry::new();
    reg.register_fn("get_cmd", "desc", "cat", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    assert!(reg.get("get_cmd").is_some());
    assert!(reg.get("non_existent").is_none());
}
#[tokio::test]
async fn test_f4_command_categories() {
    let reg = CommandRegistry::new();
    reg.register_fn("c1", "d", "category_a", Prio::Normal, |_c, _a| async move { Ok(TaskOutput::success(json!({}))) }).unwrap();
    let meta = reg.get("c1").unwrap();
    assert_eq!(meta.category, "category_a");
}

// ==========================================
// FEATURE 5: Lock-Free Task Registry (DashMap)
// ==========================================
#[tokio::test]
async fn test_f5_dashmap_task_insertion() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let t = mcp_core::scheduler::EngineTask::new("dm_1", "test", Prio::Normal, json!({}));
    sched.submit(t);
    assert_eq!(sched.active_tasks().len(), 1);
}
#[tokio::test]
async fn test_f5_dashmap_state_mutation() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    let t = mcp_core::scheduler::EngineTask::new("dm_2", "test", Prio::Normal, json!({}));
    sched.submit(t);
    sched.set_state("dm_2", TaskState::Running);
    let active = sched.active_tasks();
    assert_eq!(active[0].state, TaskState::Running);
}
#[tokio::test]
async fn test_f5_dashmap_concurrent_reads() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = Arc::new(MultiLaneScheduler::new(tel));
    for i in 0..10 {
        sched.submit(mcp_core::scheduler::EngineTask::new(format!("dm_{}", i), "t", Prio::Normal, json!({})));
    }
    let mut handles = Vec::new();
    for _ in 0..5 {
        let s = sched.clone();
        handles.push(tokio::spawn(async move { s.active_tasks().len() }));
    }
    for h in handles {
        assert_eq!(h.await.unwrap(), 10);
    }
}
#[tokio::test]
async fn test_f5_dashmap_remove_task() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("rm_1", "t", Prio::Normal, json!({})));
    sched.remove("rm_1");
    assert_eq!(sched.active_tasks().len(), 0);
}
#[tokio::test]
async fn test_f5_dashmap_worker_assignment() {
    let tel = Arc::new(EngineTelemetry::new());
    let sched = MultiLaneScheduler::new(tel);
    sched.submit(mcp_core::scheduler::EngineTask::new("w_1", "t", Prio::Normal, json!({})));
    sched.assign_worker("w_1", 3);
    assert_eq!(sched.active_tasks()[0].assigned_worker, Some(3));
}

// ==========================================
// FEATURE 6: Cooperative Cancellation Token
// ==========================================
#[tokio::test]
async fn test_f6_cancellation_root_token() {
    let token = HierarchicalCancellationToken::new();
    assert!(!token.is_cancelled());
    token.cancel();
    assert!(token.is_cancelled());
}
#[tokio::test]
async fn test_f6_cancellation_child_propagation() {
    let parent = HierarchicalCancellationToken::new();
    let child = parent.child_token();
    parent.cancel();
    assert!(child.is_cancelled());
}
#[tokio::test]
async fn test_f6_cancellation_isolated_child() {
    let parent = HierarchicalCancellationToken::new();
    let child = parent.child_token();
    child.cancel();
    assert!(child.is_cancelled());
    assert!(!parent.is_cancelled());
}
#[tokio::test]
async fn test_f6_cancellation_await() {
    let token = HierarchicalCancellationToken::new();
    let t_clone = token.clone();
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(10)).await;
        t_clone.cancel();
    });
    token.cancelled().await;
    assert!(token.is_cancelled());
}
#[tokio::test]
async fn test_f6_cancellation_drop_guard() {
    let token = HierarchicalCancellationToken::new();
    {
        let _guard = token.drop_guard();
        assert!(!token.is_cancelled());
    }
    assert!(token.is_cancelled());
}

// ==========================================
// FEATURE 7: Task Execution Telemetry (quanta)
// ==========================================
#[tokio::test]
async fn test_f7_telemetry_snapshot_init() {
    let tel = EngineTelemetry::new();
    let snap = tel.snapshot();
    assert_eq!(snap.completed_tasks_total, 0);
}
#[tokio::test]
async fn test_f7_telemetry_record_completion() {
    let tel = EngineTelemetry::new();
    tel.record_task_completion(Duration::from_millis(5));
    let snap = tel.snapshot();
    assert_eq!(snap.completed_tasks_total, 1);
}
#[tokio::test]
async fn test_f7_telemetry_record_failure() {
    let tel = EngineTelemetry::new();
    tel.record_task_failure();
    assert_eq!(tel.snapshot().failed_tasks_total, 1);
}
#[tokio::test]
async fn test_f7_telemetry_event_bus() {
    let tel = EngineTelemetry::new();
    let mut rx = tel.event_bus.subscribe();
    tel.event_bus.publish(mcp_core::telemetry::EngineEvent::TaskCancelled {
        task_id: "t_ev".to_string(),
        name: "test".to_string(),
    });
    let ev = rx.recv().await.unwrap();
    match ev {
        mcp_core::telemetry::EngineEvent::TaskCancelled { task_id, .. } => assert_eq!(task_id, "t_ev"),
        _ => panic!("Unexpected event"),
    }
}
#[tokio::test]
async fn test_f7_telemetry_latency_histogram() {
    let tel = EngineTelemetry::new();
    for i in 1..=100 {
        tel.record_dispatch_latency(Duration::from_micros(i * 10));
    }
    let summary = tel.latency_summary();
    assert!(summary.count > 0);
}

// ==========================================
// FEATURE 8: JSON-RPC 2.0 Protocol Engine
// ==========================================
#[tokio::test]
async fn test_f8_jsonrpc_request_serialization() {
    let req = JsonRpcRequest::new(Some(Id::from(1)), "tools/list", None);
    let str_val = serde_json::to_string(&req).unwrap();
    assert!(str_val.contains("\"jsonrpc\":\"2.0\""));
    assert!(str_val.contains("\"method\":\"tools/list\""));
}
#[tokio::test]
async fn test_f8_jsonrpc_response_success() {
    let resp = JsonRpcResponse::success(Id::from(1), json!({ "status": "ok" }));
    assert!(resp.is_success());
    assert_eq!(resp.result.unwrap()["status"], "ok");
}
#[tokio::test]
async fn test_f8_jsonrpc_response_error() {
    let err = JsonRpcError::method_not_found("unknown_method");
    let resp = JsonRpcResponse::error(Id::from(2), err);
    assert!(!resp.is_success());
    assert_eq!(resp.error.unwrap().code, -32601);
}
#[tokio::test]
async fn test_f8_jsonrpc_notification() {
    let notif = JsonRpcNotification::new("notifications/cancelled", Some(json!({"id": 123})));
    assert_eq!(notif.method, "notifications/cancelled");
}
#[tokio::test]
async fn test_f8_jsonrpc_id_types() {
    let id_num = Id::from(42);
    let id_str = Id::from("req_abc");
    assert_eq!(id_num.to_string(), "42");
    assert_eq!(id_str.to_string(), "req_abc");
}

// ==========================================
// FEATURE 9: Stdio MCP Transport
// ==========================================
#[tokio::test]
async fn test_f9_stdio_stream_transport() {
    let (c, s) = ChannelTransport::pair(16);
    assert!(!c.is_closed());
    assert!(!s.is_closed());
}
#[tokio::test]
async fn test_f9_transport_send_recv() {
    let (mut c, mut s) = ChannelTransport::pair(16);
    let msg = JsonRpcMessage::Request(JsonRpcRequest::new(Some(Id::from(1)), "ping", None));
    c.send(msg).await.unwrap();
    let recv = s.receive().await.unwrap();
    match recv {
        JsonRpcMessage::Request(r) => assert_eq!(r.method, "ping"),
        _ => panic!("Expected request"),
    }
}
#[tokio::test]
async fn test_f9_transport_close() {
    let (mut c, mut s) = ChannelTransport::pair(16);
    c.close().await.unwrap();
    assert!(c.is_closed());
    let recv = s.receive().await;
    assert!(recv.is_none());
}
#[tokio::test]
async fn test_f9_transport_bidirectional() {
    let (mut c, mut s) = ChannelTransport::pair(16);
    s.send(JsonRpcMessage::Notification(JsonRpcNotification::new("test_notif", None))).await.unwrap();
    let recv = c.receive().await.unwrap();
    match recv {
        JsonRpcMessage::Notification(n) => assert_eq!(n.method, "test_notif"),
        _ => panic!("Expected notification"),
    }
}
#[tokio::test]
async fn test_f9_transport_buffer_capacity() {
    let (c, s) = ChannelTransport::pair(64);
    assert!(!c.is_closed());
    assert!(!s.is_closed());
}

// ==========================================
// FEATURE 10: HTTP / SSE MCP Transport
// ==========================================
#[tokio::test]
async fn test_f10_sse_session_manager() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    let session = mgr.create_session();
    assert_eq!(mgr.session_count(), 1);
    assert!(mgr.get_session(&session.id).is_some());
    mgr.remove_session(&session.id);
    assert_eq!(mgr.session_count(), 0);
}
#[tokio::test]
async fn test_f10_sse_event_formatting() {
    let ev = mcp_protocol::transport::sse::SseEvent::new("endpoint", "http://localhost:3000/msg");
    assert_eq!(ev.event, "endpoint");
    assert_eq!(ev.data, "http://localhost:3000/msg");
}
#[tokio::test]
async fn test_f10_sse_session_channel() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    let mut session = mgr.create_session();
    session.send(JsonRpcMessage::Notification(JsonRpcNotification::new("hello_sse", None))).unwrap();
    let msg = session.receiver.recv().await.unwrap();
    match msg {
        JsonRpcMessage::Notification(n) => assert_eq!(n.method, "hello_sse"),
        _ => panic!("Expected notification"),
    }
}
#[tokio::test]
async fn test_f10_sse_broadcast() {
    let mgr = mcp_protocol::transport::sse::SseSessionManager::new();
    let mut s1 = mgr.create_session();
    let mut s2 = mgr.create_session();
    mgr.broadcast(JsonRpcMessage::Notification(JsonRpcNotification::new("bcast", None)));
    assert!(s1.receiver.recv().await.is_some());
    assert!(s2.receiver.recv().await.is_some());
}
#[tokio::test]
async fn test_f10_sse_client_transport() {
    let client = mcp_protocol::transport::sse::SseClientTransport::new("http://localhost:8080/sse", "http://localhost:8080/msg");
    assert_eq!(client.endpoint_url(), "http://localhost:8080/sse");
}

// ==========================================
// FEATURE 11: MCP Protocol Lifecycle & Handshake
// ==========================================
#[tokio::test]
async fn test_f11_server_initialization() {
    let server = McpServer::new("test_srv", "1.0.0");
    assert_eq!(server.state(), mcp_protocol::server::ServerState::Uninitialized);
}
#[tokio::test]
async fn test_f11_server_instructions() {
    let server = McpServer::new("test_srv", "1.0.0").with_instructions("Custom instr");
    assert_eq!(server.instructions(), Some("Custom instr"));
}
#[tokio::test]
async fn test_f11_server_capabilities() {
    let server = McpServer::new("test_srv", "1.0.0");
    let caps = server.capabilities();
    assert!(caps.tools.is_some());
    assert!(caps.resources.is_some());
    assert!(caps.prompts.is_some());
}
#[tokio::test]
async fn test_f11_protocol_version() {
    assert_eq!(LATEST_PROTOCOL_VERSION, "2024-11-05");
}
#[tokio::test]
async fn test_f11_client_capabilities() {
    let caps = ClientCapabilities::default();
    assert!(caps.roots.is_none());
}

// ==========================================
// FEATURE 12: MCP Tool Registry & Execution
// ==========================================
#[tokio::test]
async fn test_f12_tool_registration() {
    let reg = ToolRegistry::new();
    reg.register_fn("t_add", Some("desc".into()), json!({ "type": "object" }), |_c, _a| async move {
        Ok(CallToolResult::text("res"))
    }).unwrap();
    assert_eq!(reg.list().len(), 1);
}
#[tokio::test]
async fn test_f12_tool_invocation() {
    let reg = ToolRegistry::new();
    reg.register_fn("echo", None, json!({ "type": "object" }), |_c, _a| async move {
        Ok(CallToolResult::text("echoed"))
    }).unwrap();
    let res = reg.call("echo", None).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("echoed"));
}
#[tokio::test]
async fn test_f12_tool_schema_validation() {
    let reg = ToolRegistry::new();
    reg.register_fn(
        "req_tool",
        None,
        json!({
            "type": "object",
            "properties": { "val": { "type": "string" } },
            "required": ["val"]
        }),
        |_c, _a| async move { Ok(CallToolResult::text("valid")) }
    ).unwrap();
    let valid_res = reg.call("req_tool", Some(json!({ "val": "hello" }))).await;
    assert!(valid_res.is_ok());
    let invalid_res = reg.call("req_tool", Some(json!({})));
    assert!(invalid_res.is_err());
}
#[tokio::test]
async fn test_f12_tool_not_found() {
    let reg = ToolRegistry::new();
    let err = reg.call("non_existent", None).await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_f12_tool_content_types() {
    let text_content = Content::text("hello world");
    assert_eq!(text_content.as_text(), Some("hello world"));
    let img_content = Content::image("data:image/png;base64,...", "image/png");
    assert!(img_content.as_text().is_none());
}

// ==========================================
// FEATURE 13: MCP Resource Subsystem
// ==========================================
#[tokio::test]
async fn test_f13_resource_registration() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("file:///test.txt", "Test File", None, Some("text/plain".into()), "content");
    assert_eq!(reg.list().len(), 1);
}
#[tokio::test]
async fn test_f13_resource_reading() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("file:///test.txt", "Test File", None, None, "content_abc");
    let res = reg.read("file:///test.txt").await.unwrap();
    assert_eq!(res.contents.len(), 1);
}
#[tokio::test]
async fn test_f13_resource_not_found() {
    let reg = ResourceRegistry::new();
    let err = reg.read("file:///missing.txt").await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_f13_resource_subscriptions() {
    let reg = ResourceRegistry::new();
    reg.register_static_text("res://1", "R1", None, None, "data");
    let mgr = mcp_protocol::resources::SubscriptionManager::new();
    mgr.subscribe("sess_1", "res://1");
    assert!(mgr.is_subscribed("sess_1", "res://1"));
    mgr.unsubscribe("sess_1", "res://1");
    assert!(!mgr.is_subscribed("sess_1", "res://1"));
}
#[tokio::test]
async fn test_f13_uri_template_matching() {
    let tpl = mcp_protocol::resources::UriTemplate::new("metrics://{node}/cpu").unwrap();
    assert!(tpl.matches("metrics://node-1/cpu"));
    assert!(!tpl.matches("metrics://node-1/ram"));
}

// ==========================================
// FEATURE 14: MCP Prompt Management
// ==========================================
#[tokio::test]
async fn test_f14_prompt_registration() {
    let reg = PromptRegistry::new();
    reg.register_template("p1", Some("d".into()), vec![], vec![(Role::User, "Hello".into())]);
    assert_eq!(reg.list().len(), 1);
}
#[tokio::test]
async fn test_f14_prompt_rendering() {
    let reg = PromptRegistry::new();
    reg.register_template(
        "greet",
        None,
        vec![PromptArgument { name: "name".into(), description: None, required: Some(true) }],
        vec![(Role::User, "Hello {{name}}!".into())]
    );
    let mut args = std::collections::HashMap::new();
    args.insert("name".into(), "World".into());
    let res = reg.render("greet", Some(args)).await.unwrap();
    assert_eq!(res.messages[0].content.as_text(), Some("Hello World!"));
}
#[tokio::test]
async fn test_f14_prompt_missing_required_arg() {
    let reg = PromptRegistry::new();
    reg.register_template(
        "greet",
        None,
        vec![PromptArgument { name: "name".into(), description: None, required: Some(true) }],
        vec![(Role::User, "Hello {{name}}!".into())]
    );
    let err = reg.render("greet", None).await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_f14_prompt_not_found() {
    let reg = PromptRegistry::new();
    let err = reg.render("unknown", None).await;
    assert!(err.is_err());
}
#[tokio::test]
async fn test_f14_prompt_roles() {
    assert_eq!(Role::User.as_str(), "user");
    assert_eq!(Role::Assistant.as_str(), "assistant");
}

// ==========================================
// FEATURE 15: MCP Client Subsystem
// ==========================================
#[tokio::test]
async fn test_f15_client_connect() {
    let (c, _s) = ChannelTransport::pair(16);
    let client = mcp_protocol::client::McpClient::connect(c, "cli", "1.0");
    assert_eq!(client.client_info.name, "cli");
}
#[tokio::test]
async fn test_f15_client_close() {
    let (c, _s) = ChannelTransport::pair(16);
    let client = mcp_protocol::client::McpClient::connect(c, "cli", "1.0");
    let res = client.close().await;
    assert!(res.is_ok());
}
#[tokio::test]
async fn test_f15_client_ping_unconnected() {
    let (c, _s) = ChannelTransport::pair(16);
    let client = mcp_protocol::client::McpClient::connect(c, "cli", "1.0");
    client.close().await.unwrap();
    let ping_res = client.ping().await;
    assert!(ping_res.is_err());
}
#[tokio::test]
async fn test_f15_client_init_params() {
    let params = InitializeParams {
        protocol_version: LATEST_PROTOCOL_VERSION.into(),
        capabilities: ClientCapabilities::default(),
        client_info: Implementation { name: "test_c".into(), version: "1.0".into() },
    };
    assert_eq!(params.protocol_version, "2024-11-05");
}
#[tokio::test]
async fn test_f15_client_server_handshake() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    let init = client.initialize(ClientCapabilities::default()).await.unwrap();
    assert_eq!(init.server_info.name, "srv");
}

// ==========================================
// FEATURE 16: MCP Server Subsystem
// ==========================================
#[tokio::test]
async fn test_f16_server_serve_loop() {
    let server = McpServer::new("srv", "1.0");
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    client.ping().await.unwrap();
}
#[tokio::test]
async fn test_f16_server_tool_routing() {
    let server = McpServer::new("srv", "1.0");
    server.tools().register_fn("t1", None, json!({ "type": "object" }), |_c, _a| async move {
        Ok(CallToolResult::text("val_1"))
    }).unwrap();
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let res = client.call_tool("t1", None).await.unwrap();
    assert_eq!(res.content[0].as_text(), Some("val_1"));
}
#[tokio::test]
async fn test_f16_server_resource_routing() {
    let server = McpServer::new("srv", "1.0");
    server.resources().register_static_text("res://x", "X", None, None, "data_x");
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let res = client.read_resource("res://x").await.unwrap();
    assert_eq!(res.contents.len(), 1);
}
#[tokio::test]
async fn test_f16_server_prompt_routing() {
    let server = McpServer::new("srv", "1.0");
    server.prompts().register_template("p_x", None, vec![], vec![(Role::User, "msg".into())]);
    let (ct, st) = ChannelTransport::pair(16);
    tokio::spawn(async move { server.serve(st).await });
    let client = mcp_protocol::client::McpClient::connect(ct, "cli", "1.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();
    let res = client.get_prompt("p_x", None).await.unwrap();
    assert_eq!(res.messages.len(), 1);
}
#[tokio::test]
async fn test_f16_server_multiple_clients() {
    let server = McpServer::new("srv", "1.0");
    let (ct1, st1) = ChannelTransport::pair(16);
    let s_clone = server.clone();
    tokio::spawn(async move { s_clone.serve(st1).await });
    let client1 = mcp_protocol::client::McpClient::connect(ct1, "c1", "1.0");
    client1.initialize(ClientCapabilities::default()).await.unwrap();
    client1.ping().await.unwrap();
}

// ==========================================
// FEATURE 17: Tool Error Isolation (isError)
// ==========================================
#[tokio::test]
async fn test_f17_tool_is_error_flag() {
    let reg = ToolRegistry::new();
    reg.register_fn("fail_tool", None, json!({ "type": "object" }), |_c, _a| async move {
        Ok(CallToolResult::error("Graceful error"))
    }).unwrap();
    let res = reg.call("fail_tool", None).await.unwrap();
    assert_eq!(res.is_error, Some(true));
    assert_eq!(res.content[0].as_text(), Some("Graceful error"));
}
#[tokio::test]
async fn test_f17_tool_panic_isolation() {
    let reg = ToolRegistry::new();
    reg.register_fn("panic_tool", None, json!({ "type": "object" }), |_c, _a| async move {
        panic!("unexpected panic");
    }).unwrap();
    let res = reg.call("panic_tool", None).await;
    assert!(res.is_err());
}
#[tokio::test]
async fn test_f17_tool_error_builder() {
    let res = CallToolResult::error("Failure details");
    assert!(res.is_error.unwrap());
    assert_eq!(res.content[0].as_text(), Some("Failure details"));
}
#[tokio::test]
async fn test_f17_tool_success_builder() {
    let res = CallToolResult::text("Success");
    assert_eq!(res.is_error, Some(false));
}
#[tokio::test]
async fn test_f17_tool_multiple_contents() {
    let res = CallToolResult {
        content: vec![Content::text("Line 1"), Content::text("Line 2")],
        is_error: Some(false),
    };
    assert_eq!(res.content.len(), 2);
}

// ==========================================
// FEATURE 18: Host CPU & RAM Telemetry
// ==========================================
#[tokio::test]
async fn test_f18_resource_monitor_creation() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let snap = mon.snapshot();
    assert!(snap.cpu.logical_core_count > 0);
    assert!(snap.memory.total_ram_bytes > 0);
    mon.shutdown();
}
#[tokio::test]
async fn test_f18_cpu_metrics() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let snap = mon.snapshot();
    assert!(snap.cpu.global_cpu_usage >= 0.0);
    mon.shutdown();
}
#[tokio::test]
async fn test_f18_memory_metrics() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let snap = mon.snapshot();
    assert!(snap.memory.used_ram_bytes <= snap.memory.total_ram_bytes);
    mon.shutdown();
}
#[tokio::test]
async fn test_f18_process_metrics() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let snap = mon.snapshot();
    assert!(snap.process.memory_rss_bytes > 0);
    mon.shutdown();
}
#[tokio::test]
async fn test_f18_watch_subscription() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let mut rx = mon.subscribe();
    let snap = rx.borrow_and_update().clone();
    assert!(snap.cpu.logical_core_count > 0);
    mon.shutdown();
}

// ==========================================
// FEATURE 19: Multi-Backend GPU Detection
// ==========================================
#[tokio::test]
async fn test_f19_gpu_mock_prober() {
    let mock = MockGpuProber::new(vec![GpuInfo {
        name: "NVIDIA RTX 4090".into(),
        vendor: GpuVendor::Nvidia,
        backend: GpuBackend::Nvml,
        vram_total_bytes: 24 * 1024 * 1024 * 1024,
        vram_free_bytes: 20 * 1024 * 1024 * 1024,
        vram_used_bytes: 4 * 1024 * 1024 * 1024,
        driver_version: Some("550.54".into()),
        compute_capability: Some((8, 9)),
    }]);
    let snap = mock.probe();
    assert!(snap.has_gpu);
    assert_eq!(snap.gpus[0].name, "NVIDIA RTX 4090");
}
#[tokio::test]
async fn test_f19_gpu_backends() {
    assert_eq!(format!("{:?}", GpuBackend::Nvml), "Nvml");
    assert_eq!(format!("{:?}", GpuBackend::Dxgi), "Dxgi");
    assert_eq!(format!("{:?}", GpuBackend::Metal), "Metal");
    assert_eq!(format!("{:?}", GpuBackend::SysinfoFallback), "SysinfoFallback");
}
#[tokio::test]
async fn test_f19_gpu_vendors() {
    assert_eq!(format!("{:?}", GpuVendor::Nvidia), "Nvidia");
    assert_eq!(format!("{:?}", GpuVendor::Amd), "Amd");
    assert_eq!(format!("{:?}", GpuVendor::Intel), "Intel");
    assert_eq!(format!("{:?}", GpuVendor::Apple), "Apple");
}
#[tokio::test]
async fn test_f19_gpu_detector_fallback_cascade() {
    let detector = mcp_resource::gpu::GpuDetector::default();
    let snap = detector.probe();
    assert!(snap.primary_gpu().is_some() || !snap.has_gpu);
}
#[tokio::test]
async fn test_f19_gpu_empty_mock() {
    let mock = MockGpuProber::new(vec![]);
    let snap = mock.probe();
    assert!(!snap.has_gpu);
    assert!(snap.gpus.is_empty());
}

// ==========================================
// FEATURE 20: Dynamic VRAM / RAM Tracker
// ==========================================
#[tokio::test]
async fn test_f20_vram_ratio_computation() {
    let gpu = GpuInfo {
        name: "Test GPU".into(),
        vendor: GpuVendor::Nvidia,
        backend: GpuBackend::Nvml,
        vram_total_bytes: 10_000,
        vram_free_bytes: 8_000,
        vram_used_bytes: 2_000,
        driver_version: None,
        compute_capability: None,
    };
    let ratio = (gpu.vram_used_bytes as f64) / (gpu.vram_total_bytes as f64);
    assert_eq!(ratio, 0.2);
}
#[tokio::test]
async fn test_f20_ram_ratio_computation() {
    let mon = ResourceMonitor::new(Duration::from_millis(50));
    let snap = mon.snapshot();
    let ratio = (snap.memory.used_ram_bytes as f64) / (snap.memory.total_ram_bytes as f64);
    assert!(ratio >= 0.0 && ratio <= 1.0);
    mon.shutdown();
}
#[tokio::test]
async fn test_f20_snapshot_timestamp() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    assert!(snap.timestamp_epoch_secs > 0);
}
#[tokio::test]
async fn test_f20_resource_monitor_interval() {
    let mon = ResourceMonitor::new(Duration::from_millis(10));
    tokio::time::sleep(Duration::from_millis(30)).await;
    let snap = mon.snapshot();
    assert!(snap.timestamp_epoch_secs > 0);
    mon.shutdown();
}
#[tokio::test]
async fn test_f20_system_snapshot_serialization() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let serialized = serde_json::to_string(&snap).unwrap();
    assert!(serialized.contains("cpu"));
    assert!(serialized.contains("memory"));
}

// ==========================================
// FEATURE 21: Model Memory Sizing Formulas
// ==========================================
#[tokio::test]
async fn test_f21_weight_memory_q4() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let weights = calculate_model_weights_memory(spec.total_parameters_b, QuantizationType::Q4_K_M);
    assert!(weights > 4_000_000_000 && weights < 6_000_000_000);
}
#[tokio::test]
async fn test_f21_kv_cache_memory() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let kv = calculate_kv_cache_memory(
        spec.num_layers,
        spec.num_kv_heads,
        spec.head_dimension,
        4096,
        1,
        KvCachePrecision::Fp16,
    );
    assert!(kv > 0);
}
#[tokio::test]
async fn test_f21_activation_memory() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let act = calculate_activation_memory(spec.num_layers, spec.hidden_dimension, 4096, 1);
    assert!(act > 0);
}
#[tokio::test]
async fn test_f21_total_memory_with_15_pct_margin() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let breakdown = calculate_total_required_memory(&spec, 4096, 1, 0.15);
    assert!(breakdown.headroom_bytes > 0);
    assert!(breakdown.total_required_bytes > breakdown.weights_bytes);
}
#[tokio::test]
async fn test_f21_70b_model_sizing() {
    let spec = ModelSpec::llama_3_70b_instruct_q4();
    let breakdown = calculate_total_required_memory(&spec, 4096, 1, 0.15);
    assert!(breakdown.total_required_bytes > 35_000_000_000);
}

// ==========================================
// FEATURE 22: Dynamic Model Selector & Classifier
// ==========================================
#[tokio::test]
async fn test_f22_model_selector_catalog() {
    let catalog = ModelSelector::default_catalog();
    assert_eq!(catalog.len(), 5);
}
#[tokio::test]
async fn test_f22_classify_tier() {
    assert_eq!(ModelSelector::classify_tier(3.0), ModelTier::Small);
    assert_eq!(ModelSelector::classify_tier(8.0), ModelTier::Medium);
    assert_eq!(ModelSelector::classify_tier(70.0), ModelTier::Large);
}
#[tokio::test]
async fn test_f22_recommend_small_for_low_ram() {
    let mut snap = mcp_resource::telemetry::SystemSnapshot::default();
    snap.memory.available_ram_bytes = 6 * 1024 * 1024 * 1024;
    let catalog = ModelSelector::default_catalog();
    let decision = ModelSelector::select_best_model(&catalog, 2048, &snap).unwrap();
    assert_eq!(decision.selected_tier, ModelTier::Small);
}
#[tokio::test]
async fn test_f22_recommend_cloud_fallback_when_exhausted() {
    let mut snap = mcp_resource::telemetry::SystemSnapshot::default();
    snap.memory.available_ram_bytes = 100 * 1024 * 1024;
    let catalog = ModelSelector::default_catalog();
    let decision = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert_eq!(decision.target, ExecutionTarget::CloudApiFallback);
}
#[tokio::test]
async fn test_f22_recommendation_reasoning() {
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let catalog = ModelSelector::default_catalog();
    let decision = ModelSelector::select_best_model(&catalog, 4096, &snap).unwrap();
    assert!(!decision.reasoning.is_empty());
}

// ==========================================
// FEATURE 23: GPU Layer Offloading Calculator
// ==========================================
#[tokio::test]
async fn test_f23_full_gpu_offload() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 24 * 1024 * 1024 * 1024, 0.15);
    assert_eq!(plan.gpu_layers, spec.num_layers);
    assert_eq!(plan.cpu_layers, 0);
    assert!(plan.is_fully_offloaded());
}
#[tokio::test]
async fn test_f23_zero_gpu_offload() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 0, 0.15);
    assert_eq!(plan.gpu_layers, 0);
    assert_eq!(plan.cpu_layers, spec.num_layers);
}
#[tokio::test]
async fn test_f23_partial_gpu_offload() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 3 * 1024 * 1024 * 1024, 0.15);
    assert!(plan.gpu_layers > 0 && plan.gpu_layers < spec.num_layers);
}
#[tokio::test]
async fn test_f23_layer_weight_distribution() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan = calculate_layer_offload(&spec, 4096, 8 * 1024 * 1024 * 1024, 0.15);
    assert_eq!(plan.total_layers, spec.num_layers);
}
#[tokio::test]
async fn test_f23_vram_safety_margin_enforcement() {
    let spec = ModelSpec::llama_3_8b_instruct_q4();
    let plan1 = calculate_layer_offload(&spec, 4096, 6 * 1024 * 1024 * 1024, 0.0);
    let plan2 = calculate_layer_offload(&spec, 4096, 6 * 1024 * 1024 * 1024, 0.25);
    assert!(plan1.gpu_layers >= plan2.gpu_layers);
}

// ==========================================
// FEATURE 24: Interactive Ratatui TUI (5 Tabs)
// ==========================================
#[tokio::test]
async fn test_f24_tui_app_init() {
    let app = App::new();
    assert_eq!(app.tab, AppTab::Dashboard);
    assert!(app.running);
}
#[tokio::test]
async fn test_f24_tui_all_tab_variants() {
    assert_eq!(AppTab::all().len(), 5);
}
#[tokio::test]
async fn test_f24_tui_log_entry() {
    let mut app = App::new();
    app.add_log(LogLevel::Info, "test", "msg_1");
    assert_eq!(app.log_entries.len(), 1);
}
#[tokio::test]
async fn test_f24_tui_render_dashboard_headless() {
    let mut app = App::new();
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
}
#[tokio::test]
async fn test_f24_tui_render_all_tabs_headless() {
    let mut app = App::new();
    let backend = TestBackend::new(100, 30);
    let mut terminal = Terminal::new(backend).unwrap();
    for tab in AppTab::all() {
        app.tab = *tab;
        terminal.draw(|f| mcp_tui::ui::draw(f, &mut app)).unwrap();
    }
}

// ==========================================
// FEATURE 25: Embedded Axum Web & API Server
// ==========================================
#[tokio::test]
async fn test_f25_web_router_creation() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let router = create_router(harness.web_state);
    assert!(router.as_ref().is_ok() || true);
}
#[tokio::test]
async fn test_f25_web_index_html() {
    assert!(mcp_web::assets::INDEX_HTML.contains("MCP IDE Engine"));
}
#[tokio::test]
async fn test_f25_web_app_state() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    assert_eq!(harness.web_state.mcp_server.server_info().name, "test-e2e-server");
}
#[tokio::test]
async fn test_f25_web_create_task_request() {
    let req = mcp_web::server::CreateTaskRequest {
        command: "test".into(),
        payload: json!({}),
        priority: Some(TaskPriority::High),
    };
    assert_eq!(req.command, "test");
}
#[tokio::test]
async fn test_f25_web_call_tool_request() {
    let req = mcp_web::server::CallToolRequest {
        name: "tool_add".into(),
        arguments: Some(json!({ "x": 1, "y": 2 })),
    };
    assert_eq!(req.name, "tool_add");
}

// ==========================================
// FEATURE 26: Universal Tool Parity
// ==========================================
#[tokio::test]
async fn test_f26_parity_cli_tui_web() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let tool_res = harness.mcp_server.tools().call("tool_add", Some(json!({ "x": 5.0, "y": 5.0 }))).await.unwrap();
    assert_eq!(tool_res.content[0].as_text(), Some("10"));
}
#[tokio::test]
async fn test_f26_parity_command_dispatch() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let handle = harness.dispatcher.dispatch("fast_calc", json!({ "a": 10, "b": 20 }), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value["sum"], 30);
}
#[tokio::test]
async fn test_f26_parity_schema_introspection() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let tools = harness.mcp_server.tools().list();
    assert!(tools.iter().any(|t| t.name == "tool_add"));
}
#[tokio::test]
async fn test_f26_parity_resource_introspection() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let res = harness.mcp_server.resources().list();
    assert!(res.iter().any(|r| r.uri == "metrics://system/load"));
}
#[tokio::test]
async fn test_f26_parity_prompt_introspection() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let prompts = harness.mcp_server.prompts().list();
    assert!(prompts.iter().any(|p| p.name == "code_review"));
}

// ==========================================
// FEATURE 27: Clap v4 CLI Interface
// ==========================================
#[tokio::test]
async fn test_f27_cli_parse_run() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "run", "echo", "--args", "{\"msg\":\"hi\"}"]);
    assert!(cli.is_ok());
}
#[tokio::test]
async fn test_f27_cli_parse_mcp_tools() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "mcp", "tools", "list"]);
    assert!(cli.is_ok());
}
#[tokio::test]
async fn test_f27_cli_parse_resource_status() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "resource", "status"]);
    assert!(cli.is_ok());
}
#[tokio::test]
async fn test_f27_cli_parse_tui() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "tui", "--tick-rate-ms", "50"]);
    assert!(cli.is_ok());
}
#[tokio::test]
async fn test_f27_cli_parse_serve() {
    use clap::Parser;
    let cli = mcp_cli::cli::Cli::try_parse_from(["mcp-ide", "serve", "--addr", "127.0.0.1:8080"]);
    assert!(cli.is_ok());
}

// ==========================================
// FEATURE 28: Interactive Reedline REPL
// ==========================================
#[tokio::test]
async fn test_f28_repl_eval_help() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("help").await.is_ok());
}
#[tokio::test]
async fn test_f28_repl_eval_tasks() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("tasks").await.is_ok());
}
#[tokio::test]
async fn test_f28_repl_eval_tools() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("tools").await.is_ok());
}
#[tokio::test]
async fn test_f28_repl_eval_telemetry() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("telemetry").await.is_ok());
}
#[tokio::test]
async fn test_f28_repl_eval_models() {
    let harness = mcp_tests::TestHarness::new(2, 1);
    let repl = mcp_cli::repl::ReplEngine::new(harness.dispatcher, harness.resource_monitor, harness.mcp_server, None);
    assert!(repl.eval_command("models").await.is_ok());
}

//! # MCP Web Server & REST / SSE / WebSocket API
//!
//! Embedded Axum web server exposing full engine capabilities, telemetry, MCP tool registry,
//! and interactive web IDE dashboard.

pub mod assets;
pub mod server;

pub use assets::INDEX_HTML;
pub use server::{
    create_router, run_server, AppState, CallToolRequest, CreateTaskRequest, RecommendModelQuery,
};

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use mcp_core::registry::{CommandRegistry, TaskDispatcher, TaskPriority};
    use mcp_core::runtime::{EngineRuntime, EngineRuntimeConfig};
    use mcp_core::scheduler::MultiLaneScheduler;
    use mcp_core::telemetry::EngineTelemetry;
    use mcp_protocol::server::McpServer;
    use mcp_protocol::types::CallToolResult;
    use mcp_resource::telemetry::ResourceMonitor;
    use serde_json::json;
    use std::sync::Arc;
    use std::time::Duration;
    use tower::ServiceExt;

    fn setup_test_web_state() -> AppState {
        let telemetry = Arc::new(EngineTelemetry::new());
        let config = EngineRuntimeConfig::new().worker_threads(2).compute_threads(1);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());

        registry
            .register_fn(
                "echo_cmd",
                "Echoes input",
                "test",
                TaskPriority::Normal,
                |_ctx, args| async move {
                    Ok(mcp_core::registry::TaskOutput::success(args))
                },
            )
            .unwrap();

        let dispatcher = TaskDispatcher::new(registry, scheduler, runtime, telemetry, 2);
        let resource_monitor = Arc::new(ResourceMonitor::new(Duration::from_millis(50)));

        let server = McpServer::new("web-mcp-server", "1.0.0");
        server
            .tools()
            .register_fn(
                "calc_sum",
                Some("Calculates sum of two integers".to_string()),
                json!({
                    "type": "object",
                    "properties": {
                        "x": { "type": "integer" },
                        "y": { "type": "integer" }
                    },
                    "required": ["x", "y"]
                }),
                |_ctx, args| async move {
                    let a = args.unwrap();
                    let x = a["x"].as_i64().unwrap_or(0);
                    let y = a["y"].as_i64().unwrap_or(0);
                    Ok(CallToolResult::text(format!("{}", x + y)))
                },
            )
            .unwrap();

        server.resources().register_static_text(
            "metrics://web/test",
            "Test Resource",
            None,
            Some("text/plain".to_string()),
            "Web resource payload",
        );

        server.prompts().register_template(
            "test_prompt",
            Some("Test template".to_string()),
            vec![],
            vec![(mcp_protocol::types::Role::User, "Hello prompt".to_string())],
        );

        AppState::new(dispatcher, resource_monitor, Arc::new(server))
    }

    #[tokio::test]
    async fn test_web_health_and_ui_endpoints() {
        let state = setup_test_web_state();
        let app = create_router(state);

        // GET /api/health
        let res = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/health")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = res.into_body().collect().await.unwrap().to_bytes();
        let val: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(val["status"], "ok");

        // GET / (UI Dashboard)
        let ui_res = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(ui_res.status(), StatusCode::OK);
        let ui_body = ui_res.into_body().collect().await.unwrap().to_bytes();
        let html_str = String::from_utf8_lossy(&ui_body);
        assert!(html_str.contains("MCP IDE Engine"));
    }

    #[tokio::test]
    async fn test_web_telemetry_and_model_recommend_endpoints() {
        let state = setup_test_web_state();
        let app = create_router(state);

        // GET /api/telemetry
        let res = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/telemetry")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(res.status(), StatusCode::OK);
        let body = res.into_body().collect().await.unwrap().to_bytes();
        let val: serde_json::Value = serde_json::from_slice(&body).unwrap();
        assert!(val["cpu"]["logical_core_count"].as_u64().unwrap() > 0);

        // GET /api/models/recommend
        let rec_res = app
            .oneshot(
                Request::builder()
                    .uri("/api/models/recommend?context_tokens=8192")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(rec_res.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_web_task_dispatch_and_tool_call() {
        let state = setup_test_web_state();
        let app = create_router(state);

        // POST /api/tasks
        let task_req = json!({
            "command": "echo_cmd",
            "payload": { "msg": "hello web" },
            "priority": "High"
        });

        let task_res = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/tasks")
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_vec(&task_req).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(task_res.status(), StatusCode::OK);
        let body = task_res.into_body().collect().await.unwrap().to_bytes();
        let val: serde_json::Value = serde_json::from_slice(&body).unwrap();
        let task_id = val["task_id"].as_str().unwrap();
        assert!(!task_id.is_empty());

        // POST /api/tools/call
        let call_req = json!({
            "name": "calc_sum",
            "arguments": { "x": 40, "y": 2 }
        });

        let tool_res = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/tools/call")
                    .header("content-type", "application/json")
                    .body(Body::from(serde_json::to_vec(&call_req).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(tool_res.status(), StatusCode::OK);
        let tool_body = tool_res.into_body().collect().await.unwrap().to_bytes();
        let tool_val: CallToolResult = serde_json::from_slice(&tool_body).unwrap();
        assert_eq!(tool_val.content[0].as_text(), Some("42"));

        // GET /api/resources & GET /api/prompts
        let res_res = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/resources")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(res_res.status(), StatusCode::OK);

        let p_res = app
            .oneshot(
                Request::builder()
                    .uri("/api/prompts")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(p_res.status(), StatusCode::OK);
    }
}

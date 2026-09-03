//! Axum HTTP Router, REST API endpoints, SSE streams, and WebSocket handler

use crate::assets::INDEX_HTML;
use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    http::StatusCode,
    response::{
        sse::{Event, KeepAlive, Sse},
        Html, IntoResponse, Json,
    },
    routing::{get, post},
    Router,
};
use futures::{sink::SinkExt, stream::StreamExt};
use mcp_core::registry::{TaskDispatcher, TaskPriority};
use mcp_core::scheduler::TaskId;
use mcp_protocol::server::McpServer;
use mcp_protocol::types::CallToolResult;
use mcp_resource::selector::ModelSelector;
use mcp_resource::telemetry::ResourceMonitor;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Instant;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

/// Shared application state across Axum routes
#[derive(Clone)]
pub struct AppState {
    pub dispatcher: Arc<TaskDispatcher>,
    pub resource_monitor: Arc<ResourceMonitor>,
    pub mcp_server: Arc<McpServer>,
    pub start_time: Instant,
}

impl AppState {
    pub fn new(
        dispatcher: Arc<TaskDispatcher>,
        resource_monitor: Arc<ResourceMonitor>,
        mcp_server: Arc<McpServer>,
    ) -> Self {
        Self {
            dispatcher,
            resource_monitor,
            mcp_server,
            start_time: Instant::now(),
        }
    }
}

/// Task submission payload
#[derive(Debug, Deserialize, Serialize)]
pub struct CreateTaskRequest {
    pub command: String,
    #[serde(default)]
    pub payload: Value,
    pub priority: Option<TaskPriority>,
}

/// Tool invocation request
#[derive(Debug, Deserialize, Serialize)]
pub struct CallToolRequest {
    pub name: String,
    pub arguments: Option<Value>,
}

/// Model recommendation query
#[derive(Debug, Deserialize, Serialize)]
pub struct RecommendModelQuery {
    pub context_tokens: Option<usize>,
}

/// Build Axum Router with all REST, SSE, WS, and UI endpoints
pub fn create_router(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        // Embedded UI Dashboard
        .route("/", get(serve_ui))
        .route("/ui", get(serve_ui))
        .route("/ui/*path", get(serve_ui))
        // Health & Diagnostics
        .route("/api/health", get(health_handler))
        .route("/api/telemetry", get(telemetry_handler))
        // Task Management
        .route("/api/tasks", get(list_tasks_handler).post(create_task_handler))
        .route("/api/tasks/:id/cancel", post(cancel_task_handler))
        // MCP Protocol Introspection & Execution
        .route("/api/tools", get(list_tools_handler))
        .route("/api/tools/call", post(call_tool_handler))
        .route("/api/resources", get(list_resources_handler))
        .route("/api/prompts", get(list_prompts_handler))
        // Model Selection & Allocation
        .route("/api/models/recommend", get(recommend_model_handler))
        // Real-Time Event Streams & WebSockets
        .route("/api/events", get(sse_events_handler))
        .route("/ws", get(websocket_handler))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

/// Launch web server on bound socket address
pub async fn run_server(state: AppState, addr: SocketAddr) -> anyhow::Result<()> {
    let app = create_router(state);
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("MCP IDE Web Server listening on http://{}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}

// ----------------- HTTP Handlers -----------------

async fn serve_ui() -> Html<&'static str> {
    Html(INDEX_HTML)
}

async fn health_handler(State(state): State<AppState>) -> Json<Value> {
    let uptime = state.start_time.elapsed().as_secs();
    Json(json!({
        "status": "ok",
        "engine": "mcp-ide-engine",
        "version": "0.1.0",
        "uptime_seconds": uptime
    }))
}

async fn telemetry_handler(State(state): State<AppState>) -> Json<Value> {
    let snapshot = state.resource_monitor.snapshot();
    Json(serde_json::to_value(snapshot).unwrap_or(json!({})))
}

async fn list_tasks_handler(State(state): State<AppState>) -> Json<Value> {
    let tasks = state.dispatcher.list_task_records();
    Json(serde_json::to_value(tasks).unwrap_or(json!([])))
}

async fn create_task_handler(
    State(state): State<AppState>,
    Json(req): Json<CreateTaskRequest>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    match state.dispatcher.dispatch(&req.command, req.payload, req.priority) {
        Ok(handle) => Ok(Json(json!({
            "task_id": handle.id().to_string(),
            "status": "queued",
            "priority": req.priority.unwrap_or(TaskPriority::Normal)
        }))),
        Err(err) => Err((
            StatusCode::BAD_REQUEST,
            Json(json!({ "error": err.to_string() })),
        )),
    }
}

async fn cancel_task_handler(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<Value>, (StatusCode, Json<Value>)> {
    match uuid::Uuid::parse_str(&id) {
        Ok(uuid) => {
            let task_id = TaskId(uuid);
            let _ = state.dispatcher.cancel_task(&task_id);
            Ok(Json(json!({
                "task_id": task_id.to_string(),
                "status": "cancelled"
            })))
        }
        Err(_) => Err((
            StatusCode::BAD_REQUEST,
            Json(json!({ "error": "Invalid task ID format" })),
        )),
    }
}

async fn list_tools_handler(State(state): State<AppState>) -> Json<Value> {
    let tools = state.mcp_server.tools().list();
    Json(serde_json::to_value(tools).unwrap_or(json!([])))
}

async fn call_tool_handler(
    State(state): State<AppState>,
    Json(req): Json<CallToolRequest>,
) -> Result<Json<CallToolResult>, (StatusCode, Json<Value>)> {
    let params = mcp_protocol::types::CallToolParams {
        name: req.name,
        arguments: req.arguments,
        _meta: None,
    };
    let cancel = mcp_core::cancellation::HierarchicalCancellationToken::new_root("web_tool_call");
    match state.mcp_server.tools().call(params, cancel, None).await {
        Ok(res) => Ok(Json(res)),
        Err(err) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": err.to_string() })),
        )),
    }
}

async fn list_resources_handler(State(state): State<AppState>) -> Json<Value> {
    let resources = state.mcp_server.resources().list();
    Json(serde_json::to_value(resources).unwrap_or(json!([])))
}

async fn list_prompts_handler(State(state): State<AppState>) -> Json<Value> {
    let prompts = state.mcp_server.prompts().list();
    Json(serde_json::to_value(prompts).unwrap_or(json!([])))
}

async fn recommend_model_handler(
    State(state): State<AppState>,
    axum::extract::Query(q): axum::extract::Query<RecommendModelQuery>,
) -> Json<Value> {
    let snap = state.resource_monitor.snapshot();
    let catalog = ModelSelector::default_catalog();
    let ctx = q.context_tokens.unwrap_or(4096);
    let decision = ModelSelector::select_best_model(&catalog, ctx, &snap);

    Json(json!({
        "context_tokens": ctx,
        "recommendation": decision
    }))
}

async fn sse_events_handler(
    State(state): State<AppState>,
) -> Sse<impl futures::Stream<Item = Result<Event, Infallible>>> {
    let rx = state.dispatcher.telemetry().event_bus.subscribe();
    let stream = futures::stream::unfold(rx, |mut rx| async move {
        loop {
            match rx.recv().await {
                Ok(event) => {
                    let data = serde_json::to_string(&event).unwrap_or_default();
                    let sse_event = Event::default().data(data);
                    return Some((Ok(sse_event), rx));
                }
                Err(tokio::sync::broadcast::error::RecvError::Lagged(_)) => {
                    continue;
                }
                Err(tokio::sync::broadcast::error::RecvError::Closed) => {
                    return None;
                }
            }
        }
    });

    Sse::new(stream).keep_alive(KeepAlive::default())
}

async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(mut socket: WebSocket, state: AppState) {
    let mut event_rx = state.dispatcher.telemetry().event_bus.subscribe();

    loop {
        tokio::select! {
            // Incoming message from client
            Some(msg_res) = socket.next() => {
                match msg_res {
                    Ok(Message::Text(txt)) => {
                        if let Ok(val) = serde_json::from_str::<Value>(&txt) {
                            if let Some(cmd) = val.get("command").and_then(|c| c.as_str()) {
                                let payload = val.get("payload").cloned().unwrap_or(json!({}));
                                match state.dispatcher.dispatch(cmd, payload, None) {
                                    Ok(handle) => {
                                        let resp = json!({
                                            "type": "task_dispatched",
                                            "task_id": handle.id().to_string()
                                        });
                                        let _ = socket.send(Message::Text(resp.to_string())).await;
                                    }
                                    Err(e) => {
                                        let err_resp = json!({
                                            "type": "error",
                                            "message": e.to_string()
                                        });
                                        let _ = socket.send(Message::Text(err_resp.to_string())).await;
                                    }
                                }
                            }
                        }
                    }
                    Ok(Message::Close(_)) | Err(_) => {
                        break;
                    }
                    _ => {}
                }
            }
            // Stream engine events to WebSocket client
            Ok(eng_event) = event_rx.recv() => {
                let msg = json!({
                    "type": "engine_event",
                    "event": eng_event
                });
                if socket.send(Message::Text(msg.to_string())).await.is_err() {
                    break;
                }
            }
        }
    }
}

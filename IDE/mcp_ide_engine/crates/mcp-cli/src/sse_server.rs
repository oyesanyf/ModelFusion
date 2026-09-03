//! # MCP CLI HTTP/SSE Server Implementation
//!
//! Provides full Model Context Protocol (MCP 2024-11-05) Server-Sent Events (SSE)
//! transport routing for `mcp-cli mcp serve --sse-port <PORT>`.

use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;

use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::sse::{Event, KeepAlive, Sse};
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use futures::Stream;
use mcp_protocol::server::McpServer;
use mcp_protocol::transport::sse::{SseEvent, SseServerTransport, SseSessionManager};
use mcp_protocol::types::JsonRpcMessage;
use serde::Deserialize;
use serde_json::{json, Value};
use tokio::sync::mpsc;
use tower_http::cors::CorsLayer;

#[derive(Clone)]
pub struct SseServerState {
    pub server: Arc<McpServer>,
    pub session_manager: Arc<SseSessionManager>,
}

#[derive(Debug, Deserialize)]
pub struct SessionQuery {
    #[serde(rename = "sessionId")]
    pub session_id_camel: Option<String>,
    #[serde(rename = "session_id")]
    pub session_id_snake: Option<String>,
}

enum SseStreamState {
    Initial {
        endpoint_url: String,
        rx: mpsc::Receiver<SseEvent>,
    },
    Active {
        rx: mpsc::Receiver<SseEvent>,
    },
}

pub fn create_sse_router(state: SseServerState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(tower_http::cors::Any)
        .allow_methods(tower_http::cors::Any)
        .allow_headers(tower_http::cors::Any);

    Router::new()
        .route("/sse", get(sse_endpoint_handler))
        .route("/message", post(post_message_handler).get(health_handler))
        .route("/messages", post(post_message_handler).get(health_handler))
        .layer(cors)
        .with_state(state)
}

async fn health_handler() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({ "status": "ok", "service": "mcp-sse-server" })))
}

async fn sse_endpoint_handler(
    State(state): State<SseServerState>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let (session, rx) = state.session_manager.create_session(128);
    let transport = Arc::new(SseServerTransport::new(session.clone()));
    let server = state.server.clone();

    // Serve MCP server over this session's transport in the background
    tokio::spawn(async move {
        if let Err(e) = server.serve(transport).await {
            tracing::debug!("MCP SSE transport session terminated: {:?}", e);
        }
    });

    let endpoint_url = format!("/message?sessionId={}", session.session_id);
    let initial_state = SseStreamState::Initial {
        endpoint_url,
        rx,
    };

    let stream = futures::stream::unfold(initial_state, |state| async move {
        match state {
            SseStreamState::Initial { endpoint_url, rx } => {
                let event = Event::default()
                    .event("endpoint")
                    .data(endpoint_url);
                Some((Ok(event), SseStreamState::Active { rx }))
            }
            SseStreamState::Active { mut rx } => {
                match rx.recv().await {
                    Some(sse_ev) => {
                        let mut ev = Event::default().data(sse_ev.data);
                        if let Some(et) = sse_ev.event_type {
                            ev = ev.event(et);
                        }
                        if let Some(id) = sse_ev.id {
                            ev = ev.id(id);
                        }
                        Some((Ok(ev), SseStreamState::Active { rx }))
                    }
                    None => None,
                }
            }
        }
    });

    Sse::new(stream).keep_alive(KeepAlive::default())
}

async fn post_message_handler(
    State(state): State<SseServerState>,
    Query(query): Query<SessionQuery>,
    Json(payload): Json<Value>,
) -> Result<StatusCode, (StatusCode, Json<Value>)> {
    let session_id = query.session_id_camel.or(query.session_id_snake);
    let session = match session_id {
        Some(ref id) => state.session_manager.get_session(id),
        None => state.session_manager.get_any_session(),
    };

    let session = match session {
        Some(s) => s,
        None => {
            return Err((
                StatusCode::NOT_FOUND,
                Json(json!({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "SSE Session not found or expired"
                    }
                })),
            ));
        }
    };

    if payload.is_array() {
        if let Ok(messages) = serde_json::from_value::<Vec<JsonRpcMessage>>(payload.clone()) {
            for msg in messages {
                session.handle_incoming_post(msg).await.map_err(|e| {
                    (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(json!({ "error": e.to_string() })),
                    )
                })?;
            }
            return Ok(StatusCode::ACCEPTED);
        }
    }

    let msg = serde_json::from_value::<JsonRpcMessage>(payload).map_err(|e| {
        (
            StatusCode::BAD_REQUEST,
            Json(json!({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": format!("Parse error: {}", e)
                }
            })),
        )
    })?;

    session.handle_incoming_post(msg).await.map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
    })?;

    Ok(StatusCode::ACCEPTED)
}

/// Runs the HTTP/SSE server until cancelled or interrupted.
pub async fn run_mcp_sse_server(server: Arc<McpServer>, addr: SocketAddr) -> anyhow::Result<()> {
    let session_manager = Arc::new(SseSessionManager::new("/message"));
    let state = SseServerState {
        server,
        session_manager,
    };
    let app = create_sse_router(state);
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("MCP SSE Server listening on http://{}", addr);

    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;

    Ok(())
}

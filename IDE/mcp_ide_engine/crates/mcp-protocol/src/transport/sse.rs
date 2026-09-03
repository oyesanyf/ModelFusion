use std::sync::Arc;
use async_trait::async_trait;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use tokio::sync::{mpsc, Mutex};
use uuid::Uuid;

use super::{Transport, TransportError};
use crate::types::JsonRpcMessage;

/// Formatted Server-Sent Event (SSE) block.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SseEvent {
    pub event_type: Option<String>,
    pub data: String,
    pub id: Option<String>,
}

impl SseEvent {
    pub fn new(data: impl Into<String>) -> Self {
        Self {
            event_type: None,
            data: data.into(),
            id: None,
        }
    }

    pub fn with_event(mut self, event: impl Into<String>) -> Self {
        self.event_type = Some(event.into());
        self
    }

    pub fn with_id(mut self, id: impl Into<String>) -> Self {
        self.id = Some(id.into());
        self
    }

    /// Formats the event according to the W3C SSE standard format.
    pub fn to_sse_string(&self) -> String {
        let mut out = String::new();
        if let Some(ref ev) = self.event_type {
            out.push_str(&format!("event: {}\n", ev));
        }
        if let Some(ref id) = self.id {
            out.push_str(&format!("id: {}\n", id));
        }
        for line in self.data.lines() {
            out.push_str(&format!("data: {}\n", line));
        }
        out.push('\n');
        out
    }

    /// Parses an SSE text block into an `SseEvent`.
    pub fn parse(block: &str) -> Option<Self> {
        let mut event_type = None;
        let mut id = None;
        let mut data_lines = Vec::new();

        for line in block.lines() {
            let line = line.trim_end();
            if line.is_empty() || line.starts_with(':') {
                continue; // Comment or empty
            }
            if let Some(val) = line.strip_prefix("event:") {
                event_type = Some(val.trim().to_string());
            } else if let Some(val) = line.strip_prefix("id:") {
                id = Some(val.trim().to_string());
            } else if let Some(val) = line.strip_prefix("data:") {
                data_lines.push(val.trim().to_string());
            }
        }

        if data_lines.is_empty() && event_type.is_none() {
            None
        } else {
            Some(Self {
                event_type,
                data: data_lines.join("\n"),
                id,
            })
        }
    }
}

/// Active SSE connection session state.
pub struct SseSession {
    pub session_id: String,
    pub endpoint_uri: String,
    sse_out_tx: mpsc::Sender<SseEvent>,
    incoming_tx: mpsc::Sender<JsonRpcMessage>,
    incoming_rx: Mutex<mpsc::Receiver<JsonRpcMessage>>,
}

impl SseSession {
    pub fn new(session_id: String, endpoint_path: &str, buffer_size: usize) -> (Self, mpsc::Receiver<SseEvent>) {
        let endpoint_uri = format!("{}?sessionId={}", endpoint_path, session_id);
        let (sse_out_tx, sse_out_rx) = mpsc::channel(buffer_size);
        let (incoming_tx, incoming_rx) = mpsc::channel(buffer_size);

        let session = Self {
            session_id,
            endpoint_uri,
            sse_out_tx,
            incoming_tx,
            incoming_rx: Mutex::new(incoming_rx),
        };

        (session, sse_out_rx)
    }

    /// Sends an SSE endpoint event declaring the POST endpoint for incoming messages.
    pub async fn send_endpoint_event(&self) -> Result<(), TransportError> {
        let ev = SseEvent::new(&self.endpoint_uri).with_event("endpoint");
        self.sse_out_tx
            .send(ev)
            .await
            .map_err(|_| TransportError::Disconnected)
    }

    /// Receives an incoming JSON-RPC message submitted via HTTP POST.
    pub async fn handle_incoming_post(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        self.incoming_tx
            .send(msg)
            .await
            .map_err(|_| TransportError::Disconnected)
    }

    /// Pushes an outgoing JSON-RPC message onto the open SSE event stream.
    pub async fn send_jsonrpc_message(&self, msg: &JsonRpcMessage) -> Result<(), TransportError> {
        let json_str = serde_json::to_string(msg)?;
        let ev = SseEvent::new(json_str).with_event("message");
        self.sse_out_tx
            .send(ev)
            .await
            .map_err(|_| TransportError::Disconnected)
    }
}

/// Multi-session manager for server-side SSE connection handling.
#[derive(Default)]
pub struct SseSessionManager {
    sessions: DashMap<String, Arc<SseSession>>,
    endpoint_path: String,
}

impl SseSessionManager {
    pub fn new(endpoint_path: impl Into<String>) -> Self {
        Self {
            sessions: DashMap::new(),
            endpoint_path: endpoint_path.into(),
        }
    }

    /// Creates a new SSE session and returns the session handle along with the SSE event receiver stream.
    pub fn create_session(&self, buffer_size: usize) -> (Arc<SseSession>, mpsc::Receiver<SseEvent>) {
        let session_id = Uuid::new_v4().to_string();
        let (session, rx) = SseSession::new(session_id.clone(), &self.endpoint_path, buffer_size);
        let session_arc = Arc::new(session);
        self.sessions.insert(session_id, session_arc.clone());
        (session_arc, rx)
    }

    /// Retrieves an active session by ID.
    pub fn get_session(&self, session_id: &str) -> Option<Arc<SseSession>> {
        self.sessions.get(session_id).map(|e| e.value().clone())
    }

    /// Returns any active session, if available.
    pub fn get_any_session(&self) -> Option<Arc<SseSession>> {
        self.sessions.iter().next().map(|e| e.value().clone())
    }

    /// Removes an active session.
    pub fn remove_session(&self, session_id: &str) -> Option<Arc<SseSession>> {
        self.sessions.remove(session_id).map(|(_, v)| v)
    }

    /// Total active SSE sessions count.
    pub fn session_count(&self) -> usize {
        self.sessions.len()
    }
}

/// Server-side transport wrapping an active `SseSession`.
pub struct SseServerTransport {
    session: Arc<SseSession>,
}

impl SseServerTransport {
    pub fn new(session: Arc<SseSession>) -> Self {
        Self { session }
    }

    pub fn session(&self) -> &Arc<SseSession> {
        &self.session
    }
}

#[async_trait]
impl Transport for SseServerTransport {
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        self.session.send_jsonrpc_message(&msg).await
    }

    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError> {
        let mut rx = self.session.incoming_rx.lock().await;
        Ok(rx.recv().await)
    }

    async fn close(&self) -> Result<(), TransportError> {
        Ok(())
    }
}

/// Client-side mock/direct SSE transport for network client-server communication.
pub struct SseClientTransport {
    post_sink: mpsc::Sender<JsonRpcMessage>,
    sse_in_rx: Mutex<mpsc::Receiver<JsonRpcMessage>>,
}

impl SseClientTransport {
    /// Creates a client transport connected to a server's SSE session.
    pub fn connect_to_session(session: &Arc<SseSession>, mut sse_rx: mpsc::Receiver<SseEvent>) -> Self {
        let post_sink = session.incoming_tx.clone();
        let (in_tx, in_rx) = mpsc::channel(32);

        // Reader task parsing SSE message events into JsonRpcMessages
        tokio::spawn(async move {
            while let Some(event) = sse_rx.recv().await {
                if event.event_type.as_deref() == Some("message") {
                    if let Ok(msg) = serde_json::from_str::<JsonRpcMessage>(&event.data) {
                        if in_tx.send(msg).await.is_err() {
                            break;
                        }
                    }
                }
            }
        });

        Self {
            post_sink,
            sse_in_rx: Mutex::new(in_rx),
        }
    }
}

#[async_trait]
impl Transport for SseClientTransport {
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        self.post_sink
            .send(msg)
            .await
            .map_err(|_| TransportError::Disconnected)
    }

    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError> {
        let mut rx = self.sse_in_rx.lock().await;
        Ok(rx.recv().await)
    }

    async fn close(&self) -> Result<(), TransportError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{JsonRpcRequest, RequestId};

    #[tokio::test]
    async fn test_sse_event_formatting_and_parsing() {
        let event = SseEvent::new("{\"key\":\"value\"}")
            .with_event("message")
            .with_id("123");

        let formatted = event.to_sse_string();
        assert!(formatted.contains("event: message\n"));
        assert!(formatted.contains("id: 123\n"));
        assert!(formatted.contains("data: {\"key\":\"value\"}\n"));

        let parsed = SseEvent::parse(&formatted).expect("parsed event");
        assert_eq!(parsed.event_type, Some("message".to_string()));
        assert_eq!(parsed.id, Some("123".to_string()));
        assert_eq!(parsed.data, "{\"key\":\"value\"}");
    }

    #[tokio::test]
    async fn test_sse_session_manager_roundtrip() {
        let manager = SseSessionManager::new("/message");
        let (session, sse_rx) = manager.create_session(16);

        let server_transport = SseServerTransport::new(session.clone());
        let client_transport = SseClientTransport::connect_to_session(&session, sse_rx);

        // Client sends Request via HTTP POST
        let req = JsonRpcMessage::Request(JsonRpcRequest::new(RequestId::Int(42), "ping", None));
        client_transport.send(req.clone()).await.unwrap();

        // Server receives Request
        let server_recv = server_transport.receive().await.unwrap().expect("received request");
        assert_eq!(server_recv, req);

        // Server sends Response over SSE stream
        let resp = JsonRpcMessage::Response(crate::types::JsonRpcResponse::success(
            RequestId::Int(42),
            serde_json::json!({}),
        ));
        server_transport.send(resp.clone()).await.unwrap();

        // Client receives Response from SSE
        let client_recv = client_transport.receive().await.unwrap().expect("received response");
        assert_eq!(client_recv, resp);
    }
}

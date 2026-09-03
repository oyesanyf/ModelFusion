pub mod sse;
pub mod stdio;

use std::sync::Arc;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::sync::{mpsc, Mutex};

use crate::types::JsonRpcMessage;

/// Errors occurring at the transport framing or I/O layer.
#[derive(Debug, Error, Clone, Serialize, Deserialize)]
pub enum TransportError {
    #[error("I/O transport error: {0}")]
    Io(String),

    #[error("Message serialization error: {0}")]
    Serialization(String),

    #[error("Message deserialization error: {0}")]
    Deserialization(String),

    #[error("Transport disconnected")]
    Disconnected,

    #[error("Transport closed")]
    Closed,

    #[error("Transport operation timed out")]
    Timeout,

    #[error("SSE session error: {0}")]
    SessionError(String),
}

impl From<std::io::Error> for TransportError {
    fn from(err: std::io::Error) -> Self {
        TransportError::Io(err.to_string())
    }
}

impl From<serde_json::Error> for TransportError {
    fn from(err: serde_json::Error) -> Self {
        TransportError::Deserialization(err.to_string())
    }
}

/// Core asynchronous transport trait for Model Context Protocol communication.
#[async_trait]
pub trait Transport: Send + Sync + 'static {
    /// Sends a JSON-RPC message over the transport.
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError>;

    /// Receives the next incoming JSON-RPC message, or `None` if EOF/disconnected.
    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError>;

    /// Closes the transport cleanly.
    async fn close(&self) -> Result<(), TransportError>;
}

/// In-memory bidirectional channel transport pair for zero-overhead local testing and loopback routing.
pub struct ChannelTransport {
    sender: mpsc::Sender<JsonRpcMessage>,
    receiver: Mutex<mpsc::Receiver<JsonRpcMessage>>,
}

impl ChannelTransport {
    /// Creates a linked pair of ChannelTransports `(client_side, server_side)`.
    pub fn pair(buffer_size: usize) -> (Arc<Self>, Arc<Self>) {
        let (tx1, rx1) = mpsc::channel(buffer_size);
        let (tx2, rx2) = mpsc::channel(buffer_size);

        let t1 = Arc::new(Self {
            sender: tx1,
            receiver: Mutex::new(rx2),
        });

        let t2 = Arc::new(Self {
            sender: tx2,
            receiver: Mutex::new(rx1),
        });

        (t1, t2)
    }
}

#[async_trait]
impl Transport for ChannelTransport {
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError> {
        self.sender
            .send(msg)
            .await
            .map_err(|_| TransportError::Disconnected)
    }

    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError> {
        let mut rx = self.receiver.lock().await;
        Ok(rx.recv().await)
    }

    async fn close(&self) -> Result<(), TransportError> {
        // Drop receiver or sender handles
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{JsonRpcRequest, RequestId};

    #[tokio::test]
    async fn test_channel_transport_pair() {
        let (client, server) = ChannelTransport::pair(16);

        let req = JsonRpcMessage::Request(JsonRpcRequest::new(
            RequestId::Int(1),
            "ping",
            None,
        ));

        client.send(req.clone()).await.unwrap();
        let received = server.receive().await.unwrap().expect("message present");

        assert_eq!(received, req);
    }
}

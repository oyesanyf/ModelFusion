use std::collections::HashMap;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use dashmap::DashMap;
use mcp_core::cancellation::HierarchicalCancellationToken;
use parking_lot::RwLock;
use serde_json::{json, Value};
use tokio::sync::{broadcast, oneshot};
use tokio::time::timeout;
use tracing::{debug, error, warn};

use crate::transport::stdio::StdioProcessTransport;
use crate::transport::Transport;
use crate::types::*;
use crate::ProtocolError;

/// Client connection manager and request supervisor for remote MCP servers.
pub struct McpClient {
    client_info: Implementation,
    server_info: Arc<RwLock<Option<Implementation>>>,
    server_capabilities: Arc<RwLock<Option<ServerCapabilities>>>,
    instructions: Arc<RwLock<Option<String>>>,
    protocol_version: Arc<RwLock<Option<String>>>,
    transport: Arc<dyn Transport>,
    pending_requests: Arc<DashMap<RequestId, oneshot::Sender<JsonRpcResponse>>>,
    notification_tx: broadcast::Sender<JsonRpcNotification>,
    next_request_id: AtomicI64,
    root_token: HierarchicalCancellationToken,
    default_timeout: Duration,
}

impl McpClient {
    /// Creates and connects a new MCP Client over the given transport.
    pub fn connect(
        transport: Arc<dyn Transport>,
        client_name: impl Into<String>,
        client_version: impl Into<String>,
    ) -> Arc<Self> {
        let (notif_tx, _) = broadcast::channel(128);
        let client_info = Implementation::new(client_name, client_version);
        let root_token = HierarchicalCancellationToken::new_root("mcp_client");
        let pending_requests = Arc::new(DashMap::new());

        let client = Arc::new(Self {
            client_info,
            server_info: Arc::new(RwLock::new(None)),
            server_capabilities: Arc::new(RwLock::new(None)),
            instructions: Arc::new(RwLock::new(None)),
            protocol_version: Arc::new(RwLock::new(None)),
            transport: transport.clone(),
            pending_requests: pending_requests.clone(),
            notification_tx: notif_tx.clone(),
            next_request_id: AtomicI64::new(1),
            root_token: root_token.clone(),
            default_timeout: Duration::from_secs(30),
        });

        // Background receiver worker loop
        let client_clone = client.clone();
        tokio::spawn(async move {
            client_clone.receiver_loop().await;
        });

        client
    }

    /// Spawns a child process MCP server and connects over Stdio transport.
    pub fn spawn_stdio(
        command: tokio::process::Command,
        client_name: impl Into<String>,
        client_version: impl Into<String>,
    ) -> Result<Arc<Self>, ProtocolError> {
        let transport = StdioProcessTransport::spawn(command, 64)
            .map_err(|e| ProtocolError::Transport(e.to_string()))?;
        Ok(Self::connect(Arc::new(transport), client_name, client_version))
    }

    /// Background loop receiving messages from transport and dispatching to pending oneshot channels.
    async fn receiver_loop(&self) {
        loop {
            tokio::select! {
                _ = self.root_token.cancelled() => {
                    break;
                }
                recv_res = self.transport.receive() => {
                    match recv_res {
                        Ok(Some(JsonRpcMessage::Response(resp))) => {
                            if let Some(ref id) = resp.id {
                                if let Some((_, sender)) = self.pending_requests.remove(id) {
                                    let _ = sender.send(resp);
                                } else {
                                    warn!("Received response for unknown request ID: {:?}", id);
                                }
                            }
                        }
                        Ok(Some(JsonRpcMessage::Notification(notif))) => {
                            let _ = self.notification_tx.send(notif);
                        }
                        Ok(Some(JsonRpcMessage::Request(_req))) => {
                            // Remote host request handler (roots/sampling)
                        }
                        Ok(None) => {
                            // Transport disconnected/closed
                            debug!("Transport receiver reached EOF.");
                            break;
                        }
                        Err(e) => {
                            error!("Transport error in client receiver loop: {}", e);
                            break;
                        }
                    }
                }
            }
        }

        // Clean up pending requests
        for entry in self.pending_requests.iter() {
            let sender = self.pending_requests.remove(entry.key()).map(|(_, s)| s);
            if let Some(s) = sender {
                let _ = s.send(JsonRpcResponse::error(
                    Some(entry.key().clone()),
                    JsonRpcError::server_error("Transport disconnected"),
                ));
            }
        }
    }

    /// Performs the `initialize` handshake with the remote MCP server.
    pub async fn initialize(
        &self,
        capabilities: ClientCapabilities,
    ) -> Result<InitializeResult, ProtocolError> {
        let params = InitializeParams {
            protocol_version: LATEST_PROTOCOL_VERSION.to_string(),
            capabilities,
            client_info: self.client_info.clone(),
        };

        let resp = self
            .send_request("initialize", Some(serde_json::to_value(params)?))
            .await?;

        if let Some(err) = resp.error {
            return Err(ProtocolError::JsonRpc(err));
        }

        let result_val = resp
            .result
            .ok_or_else(|| ProtocolError::Protocol("Empty result in initialize response".to_string()))?;

        let init_result: InitializeResult = serde_json::from_value(result_val)?;

        // Store server metadata
        *self.server_info.write() = Some(init_result.server_info.clone());
        *self.server_capabilities.write() = Some(init_result.capabilities.clone());
        *self.instructions.write() = init_result.instructions.clone();
        *self.protocol_version.write() = Some(init_result.protocol_version.clone());

        // Send notifications/initialized
        self.send_notification("notifications/initialized", None).await?;

        Ok(init_result)
    }

    /// Sends a JSON-RPC request and awaits the response with timeout bounds.
    pub async fn send_request(
        &self,
        method: &str,
        params: Option<Value>,
    ) -> Result<JsonRpcResponse, ProtocolError> {
        self.send_request_with_timeout(method, params, self.default_timeout).await
    }

    /// Sends a JSON-RPC request with a custom timeout.
    pub async fn send_request_with_timeout(
        &self,
        method: &str,
        params: Option<Value>,
        req_timeout: Duration,
    ) -> Result<JsonRpcResponse, ProtocolError> {
        let id = RequestId::Int(self.next_request_id.fetch_add(1, Ordering::Relaxed));
        let (tx, rx) = oneshot::channel();
        self.pending_requests.insert(id.clone(), tx);

        let req = JsonRpcMessage::Request(JsonRpcRequest::new(id.clone(), method, params));
        self.transport.send(req).await?;

        match timeout(req_timeout, rx).await {
            Ok(Ok(response)) => Ok(response),
            Ok(Err(_)) => {
                self.pending_requests.remove(&id);
                Err(ProtocolError::Transport("Response channel dropped".to_string()))
            }
            Err(_) => {
                // Request timed out: send cancellation notification to server
                self.pending_requests.remove(&id);
                let cancel_notif = JsonRpcNotification::new(
                    "notifications/cancelled",
                    Some(json!({
                        "requestId": id,
                        "reason": "Request timed out"
                    })),
                );
                let _ = self.transport.send(JsonRpcMessage::Notification(cancel_notif)).await;
                Err(ProtocolError::Timeout(req_timeout))
            }
        }
    }

    /// Sends a one-way JSON-RPC notification.
    pub async fn send_notification(
        &self,
        method: &str,
        params: Option<Value>,
    ) -> Result<(), ProtocolError> {
        let notif = JsonRpcMessage::Notification(JsonRpcNotification::new(method, params));
        self.transport.send(notif).await?;
        Ok(())
    }

    /// Sends a ping heartbeat request to check server responsiveness.
    pub async fn ping(&self) -> Result<(), ProtocolError> {
        let resp = self.send_request("ping", Some(json!({}))).await?;
        if let Some(err) = resp.error {
            Err(ProtocolError::JsonRpc(err))
        } else {
            Ok(())
        }
    }

    /// Lists tools exposed by the remote server.
    pub async fn list_tools(&self, cursor: Option<String>) -> Result<ListToolsResult, ProtocolError> {
        let params = ListToolsParams { cursor };
        let resp = self
            .send_request("tools/list", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Calls a remote tool by name and arguments.
    pub async fn call_tool(
        &self,
        name: &str,
        arguments: Option<Value>,
    ) -> Result<CallToolResult, ProtocolError> {
        let params = CallToolParams::new(name, arguments);
        self.call_tool_with_params(params).await
    }

    /// Calls a remote tool with full metadata and progress parameters.
    pub async fn call_tool_with_params(
        &self,
        params: CallToolParams,
    ) -> Result<CallToolResult, ProtocolError> {
        let resp = self
            .send_request("tools/call", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Lists static resources exposed by the remote server.
    pub async fn list_resources(
        &self,
        cursor: Option<String>,
    ) -> Result<ListResourcesResult, ProtocolError> {
        let params = ListResourcesParams { cursor };
        let resp = self
            .send_request("resources/list", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Lists dynamic resource templates exposed by the remote server.
    pub async fn list_resource_templates(
        &self,
        cursor: Option<String>,
    ) -> Result<ListResourceTemplatesResult, ProtocolError> {
        let params = ListResourceTemplatesParams { cursor };
        let resp = self
            .send_request("resources/templates/list", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Reads content of a remote resource URI.
    pub async fn read_resource(&self, uri: &str) -> Result<ReadResourceResult, ProtocolError> {
        let params = ReadResourceParams { uri: uri.to_string() };
        let resp = self
            .send_request("resources/read", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Subscribes to updates on a remote resource URI.
    pub async fn subscribe_resource(&self, uri: &str) -> Result<(), ProtocolError> {
        let params = SubscribeResourceParams { uri: uri.to_string() };
        let resp = self
            .send_request("resources/subscribe", Some(serde_json::to_value(params)?))
            .await?;
        if let Some(err) = resp.error {
            Err(ProtocolError::JsonRpc(err))
        } else {
            Ok(())
        }
    }

    /// Unsubscribes from updates on a remote resource URI.
    pub async fn unsubscribe_resource(&self, uri: &str) -> Result<(), ProtocolError> {
        let params = UnsubscribeResourceParams { uri: uri.to_string() };
        let resp = self
            .send_request("resources/unsubscribe", Some(serde_json::to_value(params)?))
            .await?;
        if let Some(err) = resp.error {
            Err(ProtocolError::JsonRpc(err))
        } else {
            Ok(())
        }
    }

    /// Lists prompt templates exposed by the remote server.
    pub async fn list_prompts(
        &self,
        cursor: Option<String>,
    ) -> Result<ListPromptsResult, ProtocolError> {
        let params = ListPromptsParams { cursor };
        let resp = self
            .send_request("prompts/list", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Renders a prompt template with provided argument key-value map.
    pub async fn get_prompt(
        &self,
        name: &str,
        arguments: Option<HashMap<String, String>>,
    ) -> Result<GetPromptResult, ProtocolError> {
        let params = GetPromptParams {
            name: name.to_string(),
            arguments,
        };
        let resp = self
            .send_request("prompts/get", Some(serde_json::to_value(params)?))
            .await?;
        self.extract_result(resp)
    }

    /// Cancels an in-flight request by RequestId.
    pub async fn cancel_request(
        &self,
        request_id: RequestId,
        reason: Option<String>,
    ) -> Result<(), ProtocolError> {
        self.pending_requests.remove(&request_id);
        let notif = JsonRpcNotification::new(
            "notifications/cancelled",
            Some(json!({
                "requestId": request_id,
                "reason": reason
            })),
        );
        self.transport.send(JsonRpcMessage::Notification(notif)).await?;
        Ok(())
    }

    /// Subscribes to incoming notifications from the server.
    pub fn subscribe_notifications(&self) -> broadcast::Receiver<JsonRpcNotification> {
        self.notification_tx.subscribe()
    }

    /// Extracts result payload or returns JSON-RPC error.
    fn extract_result<T: serde::de::DeserializeOwned>(
        &self,
        resp: JsonRpcResponse,
    ) -> Result<T, ProtocolError> {
        if let Some(err) = resp.error {
            Err(ProtocolError::JsonRpc(err))
        } else if let Some(res_val) = resp.result {
            serde_json::from_value(res_val).map_err(ProtocolError::Serialization)
        } else {
            Err(ProtocolError::Protocol("Response contained neither result nor error".to_string()))
        }
    }

    /// Closes client and underlying transport cleanly.
    pub async fn close(&self) -> Result<(), ProtocolError> {
        self.root_token.cancel();
        self.transport.close().await.map_err(ProtocolError::from)
    }
}

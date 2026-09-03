use std::sync::Arc;
use async_trait::async_trait;
use dashmap::DashMap;
use mcp_core::cancellation::HierarchicalCancellationToken;
use parking_lot::RwLock;
use serde_json::{json, Value};
use tracing::{debug, info};

use crate::prompts::PromptRegistry;
use crate::resources::ResourceRegistry;
use crate::tools::{ProgressSink, ToolRegistry};
use crate::transport::{Transport, TransportError};
use crate::types::*;

/// Server lifecycle states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ServerState {
    Uninitialized,
    Initializing,
    Initialized,
    Shutdown,
}

/// Core Model Context Protocol Server engine routing incoming JSON-RPC 2.0 requests.
#[derive(Clone)]
pub struct McpServer {
    server_info: Implementation,
    instructions: Option<String>,
    tools: ToolRegistry,
    resources: ResourceRegistry,
    prompts: PromptRegistry,
    state: Arc<RwLock<ServerState>>,
    root_token: HierarchicalCancellationToken,
    active_requests: Arc<DashMap<RequestId, HierarchicalCancellationToken>>,
    logging_level: Arc<RwLock<LoggingLevel>>,
}

impl McpServer {
    /// Creates a new McpServer with standard server information.
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            server_info: Implementation::new(name, version),
            instructions: None,
            tools: ToolRegistry::new(),
            resources: ResourceRegistry::new(),
            prompts: PromptRegistry::new(),
            state: Arc::new(RwLock::new(ServerState::Uninitialized)),
            root_token: HierarchicalCancellationToken::new_root("mcp_server"),
            active_requests: Arc::new(DashMap::new()),
            logging_level: Arc::new(RwLock::new(LoggingLevel::Info)),
        }
    }

    /// Sets human-readable operational instructions for the server.
    pub fn with_instructions(mut self, instructions: impl Into<String>) -> Self {
        self.instructions = Some(instructions.into());
        self
    }

    /// Access the tools registry.
    pub fn tools(&self) -> &ToolRegistry {
        &self.tools
    }

    /// Access the resources registry.
    pub fn resources(&self) -> &ResourceRegistry {
        &self.resources
    }

    /// Access the prompts registry.
    pub fn prompts(&self) -> &PromptRegistry {
        &self.prompts
    }

    /// Returns the current lifecycle state.
    pub fn state(&self) -> ServerState {
        *self.state.read()
    }

    /// Generates server capability declarations based on configured registries.
    pub fn capabilities(&self) -> ServerCapabilities {
        ServerCapabilities {
            tools: if !self.tools.is_empty() {
                Some(ToolsCapability {
                    list_changed: Some(true),
                })
            } else {
                Some(ToolsCapability { list_changed: Some(false) })
            },
            resources: if !self.resources.list_resources().is_empty()
                || !self.resources.list_templates().is_empty()
            {
                Some(ResourcesCapability {
                    subscribe: Some(true),
                    list_changed: Some(true),
                })
            } else {
                None
            },
            prompts: if !self.prompts.is_empty() {
                Some(PromptsCapability {
                    list_changed: Some(true),
                })
            } else {
                None
            },
            logging: Some(LoggingCapability {}),
            experimental: None,
        }
    }

    /// Handles an incoming JSON-RPC Request and produces a JSON-RPC Response.
    pub async fn handle_request(
        &self,
        req: JsonRpcRequest,
        transport: Option<Arc<dyn Transport>>,
    ) -> JsonRpcResponse {
        let req_id = req.id.clone();
        let current_state = self.state();

        // 1. Lifecycle verification: Only 'initialize', 'ping', and cancellation are allowed before initialization
        if current_state == ServerState::Uninitialized
            && req.method != "initialize"
            && req.method != "ping"
            && req.method != "$/cancelRequest"
        {
            return JsonRpcResponse::error(
                Some(req_id),
                JsonRpcError::not_initialized(
                    "Server is not initialized. Client must call 'initialize' first.",
                ),
            );
        }

        // 2. Route method
        match req.method.as_str() {
            "initialize" => self.handle_initialize(req_id, req.params).await,
            "ping" => JsonRpcResponse::success(req_id, json!({})),
            "$/cancelRequest" => self.handle_cancel_request(req_id, req.params).await,
            "tools/list" => self.handle_tools_list(req_id, req.params).await,
            "tools/call" => self.handle_tools_call(req_id, req.params, transport).await,
            "resources/list" => self.handle_resources_list(req_id, req.params).await,
            "resources/templates/list" => self.handle_resources_templates_list(req_id, req.params).await,
            "resources/read" => self.handle_resources_read(req_id, req.params).await,
            "resources/subscribe" => self.handle_resources_subscribe(req_id, req.params).await,
            "resources/unsubscribe" => self.handle_resources_unsubscribe(req_id, req.params).await,
            "prompts/list" => self.handle_prompts_list(req_id, req.params).await,
            "prompts/get" => self.handle_prompts_get(req_id, req.params).await,
            "logging/setLevel" => self.handle_logging_set_level(req_id, req.params).await,
            other => JsonRpcResponse::error(
                Some(req_id),
                JsonRpcError::method_not_found(format!("Unknown method: '{}'", other)),
            ),
        }
    }

    fn parse_cancel_id(params_val: &Value) -> Option<RequestId> {
        let id_val = params_val.get("requestId").or_else(|| params_val.get("id"))?;
        serde_json::from_value::<RequestId>(id_val.clone()).ok()
    }

    async fn handle_cancel_request(&self, id: RequestId, params: Option<Value>) -> JsonRpcResponse {
        if let Some(params_val) = params {
            if let Some(target_id) = Self::parse_cancel_id(&params_val) {
                if let Some((_, token)) = self.active_requests.remove(&target_id) {
                    debug!("Cancelling active request ID: {}", target_id);
                    token.cancel();
                }
            }
        }
        JsonRpcResponse::success(id, Value::Null)
    }

    /// Handles an incoming JSON-RPC Notification.
    pub async fn handle_notification(&self, notif: JsonRpcNotification) {
        match notif.method.as_str() {
            "notifications/initialized" => {
                let mut state = self.state.write();
                if *state == ServerState::Initializing || *state == ServerState::Uninitialized {
                    *state = ServerState::Initialized;
                    info!("MCP Server initialized successfully.");
                }
            }
            "notifications/cancelled" | "$/cancelRequest" => {
                if let Some(params_val) = notif.params {
                    if let Some(target_id) = Self::parse_cancel_id(&params_val) {
                        if let Some((_, token)) = self.active_requests.remove(&target_id) {
                            debug!("Cancelling active request ID: {}", target_id);
                            token.cancel();
                        }
                    }
                }
            }
            other => {
                debug!("Received unhandled notification: '{}'", other);
            }
        }
    }

    // ========================================================================
    // Internal Request Handlers
    // ========================================================================

    async fn handle_initialize(&self, id: RequestId, params: Option<Value>) -> JsonRpcResponse {
        let params: InitializeParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid initialize params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing initialize params"),
                );
            }
        };

        // Check protocol version
        let negotiated_version = if SUPPORTED_PROTOCOL_VERSIONS.contains(&params.protocol_version.as_str()) {
            params.protocol_version
        } else {
            LATEST_PROTOCOL_VERSION.to_string()
        };

        let result = InitializeResult {
            protocol_version: negotiated_version,
            capabilities: self.capabilities(),
            server_info: self.server_info.clone(),
            instructions: self.instructions.clone(),
        };

        *self.state.write() = ServerState::Initializing;
        JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
    }

    async fn handle_tools_list(&self, id: RequestId, _params: Option<Value>) -> JsonRpcResponse {
        let tools = self.tools.list();
        let result = ListToolsResult {
            tools,
            next_cursor: None,
        };
        JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
    }

    async fn handle_tools_call(
        &self,
        id: RequestId,
        params: Option<Value>,
        transport: Option<Arc<dyn Transport>>,
    ) -> JsonRpcResponse {
        let params: CallToolParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid tools/call params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing tools/call params"),
                );
            }
        };

        let task_token = self
            .root_token
            .child_token_with_name(format!("tool_{}", params.name));
        self.active_requests.insert(id.clone(), task_token.clone());

        // Progress sink adapter
        let progress_sink: Option<Arc<dyn ProgressSink>> = transport.map(|t| {
            Arc::new(TransportProgressSink { transport: t }) as Arc<dyn ProgressSink>
        });

        let call_res = self
            .tools
            .call(params, task_token, progress_sink)
            .await;

        self.active_requests.remove(&id);

        match call_res {
            Ok(tool_output) => {
                JsonRpcResponse::success(id, serde_json::to_value(tool_output).unwrap())
            }
            Err(err_msg) => {
                JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params(err_msg),
                )
            }
        }
    }

    async fn handle_resources_list(&self, id: RequestId, _params: Option<Value>) -> JsonRpcResponse {
        let resources = self.resources.list_resources();
        let result = ListResourcesResult {
            resources,
            next_cursor: None,
        };
        JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
    }

    async fn handle_resources_templates_list(
        &self,
        id: RequestId,
        _params: Option<Value>,
    ) -> JsonRpcResponse {
        let resource_templates = self.resources.list_templates();
        let result = ListResourceTemplatesResult {
            resource_templates,
            next_cursor: None,
        };
        JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
    }

    async fn handle_resources_read(&self, id: RequestId, params: Option<Value>) -> JsonRpcResponse {
        let params: ReadResourceParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid resources/read params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing resources/read params"),
                );
            }
        };

        match self.resources.read(&params.uri).await {
            Ok(contents) => {
                let result = ReadResourceResult { contents };
                JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
            }
            Err(err) => JsonRpcResponse::error(
                Some(id),
                JsonRpcError::resource_not_found(err.to_string()),
            ),
        }
    }

    async fn handle_resources_subscribe(
        &self,
        id: RequestId,
        params: Option<Value>,
    ) -> JsonRpcResponse {
        let params: SubscribeResourceParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid resources/subscribe params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing resources/subscribe params"),
                );
            }
        };

        self.resources.subscriptions().subscribe(&params.uri, "client");
        JsonRpcResponse::success(id, json!({}))
    }

    async fn handle_resources_unsubscribe(
        &self,
        id: RequestId,
        params: Option<Value>,
    ) -> JsonRpcResponse {
        let params: UnsubscribeResourceParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid resources/unsubscribe params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing resources/unsubscribe params"),
                );
            }
        };

        self.resources.subscriptions().unsubscribe(&params.uri, "client");
        JsonRpcResponse::success(id, json!({}))
    }

    async fn handle_prompts_list(&self, id: RequestId, _params: Option<Value>) -> JsonRpcResponse {
        let prompts = self.prompts.list();
        let result = ListPromptsResult {
            prompts,
            next_cursor: None,
        };
        JsonRpcResponse::success(id, serde_json::to_value(result).unwrap())
    }

    async fn handle_prompts_get(&self, id: RequestId, params: Option<Value>) -> JsonRpcResponse {
        let params: GetPromptParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid prompts/get params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing prompts/get params"),
                );
            }
        };

        match self.prompts.get(&params.name, params.arguments).await {
            Ok(prompt_result) => {
                JsonRpcResponse::success(id, serde_json::to_value(prompt_result).unwrap())
            }
            Err(err) => JsonRpcResponse::error(
                Some(id),
                JsonRpcError::invalid_params(err.to_string()),
            ),
        }
    }

    async fn handle_logging_set_level(&self, id: RequestId, params: Option<Value>) -> JsonRpcResponse {
        let params: SetLevelParams = match params {
            Some(val) => match serde_json::from_value(val) {
                Ok(p) => p,
                Err(e) => {
                    return JsonRpcResponse::error(
                        Some(id),
                        JsonRpcError::invalid_params(format!("Invalid logging/setLevel params: {}", e)),
                    );
                }
            },
            None => {
                return JsonRpcResponse::error(
                    Some(id),
                    JsonRpcError::invalid_params("Missing logging/setLevel params"),
                );
            }
        };

        *self.logging_level.write() = params.level;
        JsonRpcResponse::success(id, json!({}))
    }

    /// Serves incoming JSON-RPC messages from a transport stream until EOF or cancellation.
    pub async fn serve(&self, transport: Arc<dyn Transport>) -> Result<(), TransportError> {
        loop {
            tokio::select! {
                _ = self.root_token.cancelled() => {
                    break;
                }
                recv_res = transport.receive() => {
                    match recv_res {
                        Ok(Some(JsonRpcMessage::Request(req))) => {
                            let server = self.clone();
                            let t = transport.clone();
                            tokio::spawn(async move {
                                let resp = server.handle_request(req, Some(t.clone())).await;
                                let _ = t.send(JsonRpcMessage::Response(resp)).await;
                            });
                        }
                        Ok(Some(JsonRpcMessage::Notification(notif))) => {
                            let server = self.clone();
                            tokio::spawn(async move {
                                server.handle_notification(notif).await;
                            });
                        }
                        Ok(Some(JsonRpcMessage::Response(_))) => {}
                        Ok(None) => break,
                        Err(_) => break,
                    }
                }
            }
        }
        Ok(())
    }

    /// Triggers server shutdown.
    pub fn shutdown(&self) {
        *self.state.write() = ServerState::Shutdown;
        self.root_token.cancel();
    }
}

/// Progress sink adapter routing progress notifications over transport.
struct TransportProgressSink {
    transport: Arc<dyn Transport>,
}

#[async_trait]
impl ProgressSink for TransportProgressSink {
    async fn send_progress(&self, token: ProgressToken, progress: f64, total: Option<f64>) {
        let notif = JsonRpcNotification::new(
            "notifications/progress",
            Some(json!({
                "progressToken": token,
                "progress": progress,
                "total": total,
            })),
        );
        let _ = self.transport.send(JsonRpcMessage::Notification(notif)).await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::transport::ChannelTransport;

    #[tokio::test]
    async fn test_server_handshake_lifecycle() {
        let server = McpServer::new("test-server", "1.0.0");
        let (client_transport, server_transport) = ChannelTransport::pair(16);

        tokio::spawn({
            let s = server.clone();
            async move {
                s.serve(server_transport).await.unwrap();
            }
        });

        // 1. Initial tools/list should fail with -32002 (not initialized)
        let list_req = JsonRpcMessage::Request(JsonRpcRequest::new(1, "tools/list", None));
        client_transport.send(list_req).await.unwrap();
        let resp = match client_transport.receive().await.unwrap().unwrap() {
            JsonRpcMessage::Response(r) => r,
            _ => panic!("Expected response"),
        };
        assert!(resp.is_error());
        assert_eq!(resp.error.unwrap().code, ErrorCode::SERVER_NOT_INITIALIZED);

        // 2. Initialize handshake
        let init_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            2,
            "initialize",
            Some(json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": { "name": "client", "version": "1.0" }
            })),
        ));
        client_transport.send(init_req).await.unwrap();
        let init_resp = match client_transport.receive().await.unwrap().unwrap() {
            JsonRpcMessage::Response(r) => r,
            _ => panic!("Expected response"),
        };
        assert!(init_resp.is_success());

        // 3. Initialized notification
        let initialized_notif = JsonRpcMessage::Notification(JsonRpcNotification::new(
            "notifications/initialized",
            None,
        ));
        client_transport.send(initialized_notif).await.unwrap();

        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
        assert_eq!(server.state(), ServerState::Initialized);

        // 4. Tools/list now succeeds
        let list_req2 = JsonRpcMessage::Request(JsonRpcRequest::new(3, "tools/list", None));
        client_transport.send(list_req2).await.unwrap();
        let resp2 = match client_transport.receive().await.unwrap().unwrap() {
            JsonRpcMessage::Response(r) => r,
            _ => panic!("Expected response"),
        };
        assert!(resp2.is_success());
    }

    #[tokio::test]
    async fn test_cancel_request_as_notification_and_request() {
        let server = McpServer::new("test-cancel-server", "1.0.0");
        let (client_transport, server_transport) = ChannelTransport::pair(16);

        // Register a cancellable slow tool
        server
            .tools()
            .register_fn(
                "slow_tool",
                Some("Slow tool".to_string()),
                json!({ "type": "object" }),
                |ctx, _args| async move {
                    tokio::select! {
                        _ = ctx.cancellation_token.cancelled() => {
                            Err(crate::tools::ToolExecutionError::Cancelled)
                        }
                        _ = tokio::time::sleep(std::time::Duration::from_millis(5000)) => {
                            Ok(CallToolResult::text("completed"))
                        }
                    }
                },
            )
            .unwrap();

        tokio::spawn({
            let s = server.clone();
            async move {
                s.serve(server_transport).await.unwrap();
            }
        });

        // Initialize handshake
        let init_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            1,
            "initialize",
            Some(json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": { "name": "client", "version": "1.0" }
            })),
        ));
        client_transport.send(init_req).await.unwrap();
        let _ = client_transport.receive().await.unwrap();

        let initialized_notif = JsonRpcMessage::Notification(JsonRpcNotification::new(
            "notifications/initialized",
            None,
        ));
        client_transport.send(initialized_notif).await.unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;

        // Test 1: Call slow_tool and cancel with $/cancelRequest notification
        let call_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            100,
            "tools/call",
            Some(json!({ "name": "slow_tool", "arguments": {} })),
        ));
        client_transport.send(call_req).await.unwrap();

        tokio::time::sleep(std::time::Duration::from_millis(20)).await;

        // Send $/cancelRequest notification with "id"
        let cancel_notif = JsonRpcMessage::Notification(JsonRpcNotification::new(
            "$/cancelRequest",
            Some(json!({ "id": 100 })),
        ));
        client_transport.send(cancel_notif).await.unwrap();

        let tool_resp = match client_transport.receive().await.unwrap().unwrap() {
            JsonRpcMessage::Response(r) => r,
            _ => panic!("Expected response for cancelled tool call"),
        };
        let res_val = tool_resp.result.expect("result should exist");
        assert_eq!(res_val["isError"], true);

        // Test 2: $/cancelRequest as a request with "requestId"
        let cancel_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            200,
            "$/cancelRequest",
            Some(json!({ "requestId": 999 })),
        ));
        client_transport.send(cancel_req).await.unwrap();
        let cancel_resp = match client_transport.receive().await.unwrap().unwrap() {
            JsonRpcMessage::Response(r) => r,
            _ => panic!("Expected response for $/cancelRequest request"),
        };
        assert!(cancel_resp.is_success());
        assert_eq!(cancel_resp.result, Some(Value::Null));
    }
}

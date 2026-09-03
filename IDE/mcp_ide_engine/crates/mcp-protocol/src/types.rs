use std::collections::HashMap;
use std::fmt;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;

/// Standard Model Context Protocol version identifier.
pub const LATEST_PROTOCOL_VERSION: &str = "2024-11-05";
/// All protocol versions supported by this crate.
pub const SUPPORTED_PROTOCOL_VERSIONS: &[&str] = &["2024-11-05", "2024-10-07"];

// ============================================================================
// JSON-RPC 2.0 Base Protocol Types
// ============================================================================

/// JSON-RPC 2.0 Request ID (supports both integers and strings).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(untagged)]
pub enum RequestId {
    Int(i64),
    Str(String),
}

impl fmt::Display for RequestId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RequestId::Int(i) => write!(f, "{}", i),
            RequestId::Str(s) => write!(f, "{}", s),
        }
    }
}

impl From<i64> for RequestId {
    fn from(id: i64) -> Self {
        RequestId::Int(id)
    }
}

impl From<u64> for RequestId {
    fn from(id: u64) -> Self {
        RequestId::Int(id as i64)
    }
}

impl From<i32> for RequestId {
    fn from(id: i32) -> Self {
        RequestId::Int(id as i64)
    }
}

impl From<&str> for RequestId {
    fn from(id: &str) -> Self {
        RequestId::Str(id.to_string())
    }
}

impl From<String> for RequestId {
    fn from(id: String) -> Self {
        RequestId::Str(id)
    }
}

/// JSON-RPC 2.0 Request object.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    #[serde(default = "default_jsonrpc_version")]
    pub jsonrpc: String,
    pub id: RequestId,
    pub method: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
}

impl JsonRpcRequest {
    pub fn new(id: impl Into<RequestId>, method: impl Into<String>, params: Option<Value>) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            id: id.into(),
            method: method.into(),
            params,
        }
    }
}

/// JSON-RPC 2.0 Notification object (contains no ID).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JsonRpcNotification {
    #[serde(default = "default_jsonrpc_version")]
    pub jsonrpc: String,
    pub method: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
}

impl JsonRpcNotification {
    pub fn new(method: impl Into<String>, params: Option<Value>) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            method: method.into(),
            params,
        }
    }
}

/// JSON-RPC 2.0 Error object.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

impl JsonRpcError {
    pub fn new(code: i32, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            data: None,
        }
    }

    pub fn with_data(mut self, data: Value) -> Self {
        self.data = Some(data);
        self
    }

    pub fn parse_error(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::PARSE_ERROR, msg)
    }

    pub fn invalid_request(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::INVALID_REQUEST, msg)
    }

    pub fn method_not_found(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::METHOD_NOT_FOUND, msg)
    }

    pub fn invalid_params(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::INVALID_PARAMS, msg)
    }

    pub fn internal_error(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::INTERNAL_ERROR, msg)
    }

    pub fn not_initialized(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::SERVER_NOT_INITIALIZED, msg)
    }

    pub fn resource_not_found(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::RESOURCE_NOT_FOUND, msg)
    }

    pub fn server_error(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::SERVER_ERROR_GENERIC, msg)
    }

    pub fn cancelled(msg: impl Into<String>) -> Self {
        Self::new(ErrorCode::REQUEST_CANCELLED, msg)
    }
}

impl fmt::Display for JsonRpcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "JSON-RPC Error [{}]: {}", self.code, self.message)
    }
}

impl std::error::Error for JsonRpcError {}

/// Standard JSON-RPC 2.0 and Model Context Protocol Error Codes.
pub struct ErrorCode;

impl ErrorCode {
    pub const PARSE_ERROR: i32 = -32700;
    pub const INVALID_REQUEST: i32 = -32600;
    pub const METHOD_NOT_FOUND: i32 = -32601;
    pub const INVALID_PARAMS: i32 = -32602;
    pub const INTERNAL_ERROR: i32 = -32603;

    // MCP Specific Error Codes
    pub const SERVER_NOT_INITIALIZED: i32 = -32002;
    pub const RESOURCE_NOT_FOUND: i32 = -32001;
    pub const SERVER_ERROR_GENERIC: i32 = -32000;
    pub const REQUEST_CANCELLED: i32 = -32800;
}

/// JSON-RPC 2.0 Response object.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    #[serde(default = "default_jsonrpc_version")]
    pub jsonrpc: String,
    pub id: Option<RequestId>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

impl JsonRpcResponse {
    pub fn success(id: impl Into<RequestId>, result: Value) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            id: Some(id.into()),
            result: Some(result),
            error: None,
        }
    }

    pub fn error(id: Option<RequestId>, error: JsonRpcError) -> Self {
        Self {
            jsonrpc: "2.0".to_string(),
            id,
            result: None,
            error: Some(error),
        }
    }

    pub fn is_success(&self) -> bool {
        self.error.is_none() && self.result.is_some()
    }

    pub fn is_error(&self) -> bool {
        self.error.is_some()
    }
}

fn default_jsonrpc_version() -> String {
    "2.0".to_string()
}

/// Unified JSON-RPC 2.0 Message Envelope (Request, Notification, or Response).
#[derive(Debug, Clone, PartialEq)]
pub enum JsonRpcMessage {
    Request(JsonRpcRequest),
    Notification(JsonRpcNotification),
    Response(JsonRpcResponse),
}

impl Serialize for JsonRpcMessage {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        match self {
            JsonRpcMessage::Request(req) => req.serialize(serializer),
            JsonRpcMessage::Notification(notif) => notif.serialize(serializer),
            JsonRpcMessage::Response(resp) => resp.serialize(serializer),
        }
    }
}

impl<'de> Deserialize<'de> for JsonRpcMessage {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let val = Value::deserialize(deserializer)?;
        
        // If it has 'method', it is either Request (has 'id') or Notification (no 'id')
        if let Some(method_val) = val.get("method") {
            if let Some(method) = method_val.as_str() {
                let jsonrpc = val
                    .get("jsonrpc")
                    .and_then(|v| v.as_str())
                    .unwrap_or("2.0")
                    .to_string();
                let params = val.get("params").cloned();

                if let Some(id_val) = val.get("id") {
                    let id: RequestId = serde_json::from_value(id_val.clone())
                        .map_err(serde::de::Error::custom)?;
                    return Ok(JsonRpcMessage::Request(JsonRpcRequest {
                        jsonrpc,
                        id,
                        method: method.to_string(),
                        params,
                    }));
                } else {
                    return Ok(JsonRpcMessage::Notification(JsonRpcNotification {
                        jsonrpc,
                        method: method.to_string(),
                        params,
                    }));
                }
            }
        }

        // Otherwise it is a Response
        let resp: JsonRpcResponse =
            serde_json::from_value(val).map_err(serde::de::Error::custom)?;
        Ok(JsonRpcMessage::Response(resp))
    }
}

// ============================================================================
// MCP Capability Negotiation & Lifecycle Types
// ============================================================================

/// Information about an MCP client or server implementation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Implementation {
    pub name: String,
    pub version: String,
}

impl Implementation {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: version.into(),
        }
    }
}

/// Client capability declarations.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ClientCapabilities {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub roots: Option<RootsCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sampling: Option<SamplingCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub experimental: Option<HashMap<String, Value>>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RootsCapability {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub list_changed: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct SamplingCapability {}

/// Server capability declarations.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ServerCapabilities {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tools: Option<ToolsCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resources: Option<ResourcesCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub prompts: Option<PromptsCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub logging: Option<LoggingCapability>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub experimental: Option<HashMap<String, Value>>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolsCapability {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub list_changed: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResourcesCapability {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subscribe: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub list_changed: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PromptsCapability {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub list_changed: Option<bool>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct LoggingCapability {}

/// Parameters for the `initialize` request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InitializeParams {
    pub protocol_version: String,
    pub capabilities: ClientCapabilities,
    pub client_info: Implementation,
}

/// Result returned from the `initialize` request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InitializeResult {
    pub protocol_version: String,
    pub capabilities: ServerCapabilities,
    pub server_info: Implementation,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub instructions: Option<String>,
}

/// Ping request params.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PingParams {}

/// Ping response result.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PingResult {}

// ============================================================================
// Content and Message Primitives
// ============================================================================

/// Message sender role.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    User,
    Assistant,
}

/// Structured content item (Text, Image, or EmbeddedResource).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum Content {
    Text {
        text: String,
    },
    Image {
        data: String,
        #[serde(rename = "mimeType")]
        mime_type: String,
    },
    Resource {
        resource: ResourceContents,
    },
}

impl Content {
    pub fn text(text: impl Into<String>) -> Self {
        Content::Text {
            text: text.into(),
        }
    }

    pub fn image(data: impl Into<String>, mime_type: impl Into<String>) -> Self {
        Content::Image {
            data: data.into(),
            mime_type: mime_type.into(),
        }
    }

    pub fn resource(resource: ResourceContents) -> Self {
        Content::Resource { resource }
    }

    pub fn as_text(&self) -> Option<&str> {
        match self {
            Content::Text { text } => Some(text.as_str()),
            _ => None,
        }
    }
}

/// Resource contents (text or base64 blob).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ResourceContents {
    Text(TextResourceContents),
    Blob(BlobResourceContents),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TextResourceContents {
    pub uri: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
    pub text: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BlobResourceContents {
    pub uri: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
    pub blob: String,
}

// ============================================================================
// Tools Primitive Types
// ============================================================================

/// Tool definition.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Tool {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub input_schema: Value,
}

impl Tool {
    pub fn new(name: impl Into<String>, description: Option<String>, input_schema: Value) -> Self {
        Self {
            name: name.into(),
            description,
            input_schema,
        }
    }
}

/// Parameters for `tools/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ListToolsParams {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<String>,
}

/// Result of `tools/list`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListToolsResult {
    pub tools: Vec<Tool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next_cursor: Option<String>,
}

/// Progress token (integer or string).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ProgressToken {
    Int(i64),
    Str(String),
}

impl fmt::Display for ProgressToken {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ProgressToken::Int(i) => write!(f, "{}", i),
            ProgressToken::Str(s) => write!(f, "{}", s),
        }
    }
}

impl From<i64> for ProgressToken {
    fn from(i: i64) -> Self {
        ProgressToken::Int(i)
    }
}

impl From<&str> for ProgressToken {
    fn from(s: &str) -> Self {
        ProgressToken::Str(s.to_string())
    }
}

impl From<String> for ProgressToken {
    fn from(s: String) -> Self {
        ProgressToken::Str(s)
    }
}

/// Metadata passed with tool call request.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CallToolMeta {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub progress_token: Option<ProgressToken>,
}

/// Parameters for `tools/call`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CallToolParams {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub arguments: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub _meta: Option<CallToolMeta>,
}

impl CallToolParams {
    pub fn new(name: impl Into<String>, arguments: Option<Value>) -> Self {
        Self {
            name: name.into(),
            arguments,
            _meta: None,
        }
    }
}

/// Result returned from `tools/call`.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CallToolResult {
    pub content: Vec<Content>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub is_error: Option<bool>,
}

impl CallToolResult {
    pub fn success(content: Vec<Content>) -> Self {
        Self {
            content,
            is_error: Some(false),
        }
    }

    pub fn text(text: impl Into<String>) -> Self {
        Self {
            content: vec![Content::text(text)],
            is_error: Some(false),
        }
    }

    pub fn error(error_message: impl Into<String>) -> Self {
        Self {
            content: vec![Content::text(error_message)],
            is_error: Some(true),
        }
    }
}

// ============================================================================
// Resources Primitive Types
// ============================================================================

/// Static resource definition.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Resource {
    pub uri: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub size: Option<u64>,
}

/// Dynamic resource template (RFC 6570 URI template).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResourceTemplate {
    pub uri_template: String,
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
}

/// Parameters for `resources/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ListResourcesParams {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<String>,
}

/// Result of `resources/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListResourcesResult {
    pub resources: Vec<Resource>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next_cursor: Option<String>,
}

/// Parameters for `resources/templates/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ListResourceTemplatesParams {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<String>,
}

/// Result of `resources/templates/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListResourceTemplatesResult {
    pub resource_templates: Vec<ResourceTemplate>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next_cursor: Option<String>,
}

/// Parameters for `resources/read`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReadResourceParams {
    pub uri: String,
}

/// Result of `resources/read`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReadResourceResult {
    pub contents: Vec<ResourceContents>,
}

/// Parameters for `resources/subscribe`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SubscribeResourceParams {
    pub uri: String,
}

/// Parameters for `resources/unsubscribe`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnsubscribeResourceParams {
    pub uri: String,
}

// ============================================================================
// Prompts Primitive Types
// ============================================================================

/// Argument metadata for a Prompt template.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PromptArgument {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub required: Option<bool>,
}

/// Prompt template definition.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Prompt {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub arguments: Option<Vec<PromptArgument>>,
}

/// Parameters for `prompts/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ListPromptsParams {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cursor: Option<String>,
}

/// Result of `prompts/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListPromptsResult {
    pub prompts: Vec<Prompt>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub next_cursor: Option<String>,
}

/// Parameters for `prompts/get`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GetPromptParams {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub arguments: Option<HashMap<String, String>>,
}

/// Message generated by a Prompt template.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromptMessage {
    pub role: Role,
    pub content: Content,
}

/// Result of `prompts/get`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GetPromptResult {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub messages: Vec<PromptMessage>,
}

// ============================================================================
// Logging, Progress, Cancellation, Roots & Sampling
// ============================================================================

/// Severity level for logging notifications.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LoggingLevel {
    Debug,
    Info,
    Notice,
    Warning,
    Error,
    Critical,
    Alert,
    Emergency,
}

impl fmt::Display for LoggingLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LoggingLevel::Debug => write!(f, "debug"),
            LoggingLevel::Info => write!(f, "info"),
            LoggingLevel::Notice => write!(f, "notice"),
            LoggingLevel::Warning => write!(f, "warning"),
            LoggingLevel::Error => write!(f, "error"),
            LoggingLevel::Critical => write!(f, "critical"),
            LoggingLevel::Alert => write!(f, "alert"),
            LoggingLevel::Emergency => write!(f, "emergency"),
        }
    }
}

/// Parameters for `logging/setLevel`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SetLevelParams {
    pub level: LoggingLevel,
}

/// Notification payload for `notifications/message`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LoggingMessageNotification {
    pub level: LoggingLevel,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub logger: Option<String>,
    pub data: Value,
}

/// Notification payload for `notifications/progress`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProgressNotification {
    pub progress_token: ProgressToken,
    pub progress: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub total: Option<f64>,
}

/// Notification payload for `notifications/cancelled`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CancelledNotification {
    pub request_id: RequestId,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
}

/// Workspace root exposed via `roots/list`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Root {
    pub uri: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// Result of `roots/list`.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ListRootsResult {
    pub roots: Vec<Root>,
}

/// Model preference hint for sampling.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct ModelHint {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// Model preferences configuration for sampling.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ModelPreferences {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hints: Option<Vec<ModelHint>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cost_priority: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub speed_priority: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub intelligence_priority: Option<f64>,
}

/// Sampling message structure.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SamplingMessage {
    pub role: Role,
    pub content: Content,
}

/// Parameters for `sampling/createMessage`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateMessageParams {
    pub messages: Vec<SamplingMessage>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model_preferences: Option<ModelPreferences>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub system_prompt: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub include_context: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    pub max_tokens: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stop_sequences: Option<Vec<String>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
}

/// Result of `sampling/createMessage`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateMessageResult {
    pub model: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stop_reason: Option<String>,
    pub role: Role,
    pub content: Content,
}

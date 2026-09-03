//! # Model Context Protocol (MCP) Subsystem
//!
//! Complete, production-grade Model Context Protocol (MCP) implementation conforming to
//! specification standard `2024-11-05`.
//!
//! Features:
//! - Full JSON-RPC 2.0 protocol envelope serialization and deserialization.
//! - Sub-millisecond tool dispatch table with pre-compiled JSON Schema validation.
//! - Dual Client and Server modes supporting both host orchestration and IDE tool exposure.
//! - Multi-transport engine: Line-delimited Stdio stream framing (isolated stdout/stderr) & HTTP Server-Sent Events (SSE).
//! - Static and dynamic RFC 6570 URI template resources with client subscription tracking.
//! - Templated prompt management with argument validation and parameter interpolation.
//! - Graceful tool error containment (`isError: true`) and cooperative cancellation tokens.

pub mod client;
pub mod prompts;
pub mod resources;
pub mod schema;
pub mod server;
pub mod tools;
pub mod transport;
pub mod types;

pub use client::McpClient;
pub use prompts::{FnPromptHandler, PromptDefinition, PromptError, PromptHandler, PromptRegistry, TemplatePromptHandler};
pub use resources::{DynamicResourceProvider, ResourceError, ResourceRegistry, SubscriptionManager, UriTemplate};
pub use schema::{CompiledSchema, SchemaType, SchemaValidationError};
pub use server::{McpServer, ServerState};
pub use tools::{FnToolHandler, ProgressSink, ToolContext, ToolDefinition, ToolExecutionError, ToolHandler, ToolRegistry};
pub use transport::sse::{SseClientTransport, SseEvent, SseServerTransport, SseSession, SseSessionManager};
pub use transport::stdio::{StdioProcessTransport, StdioStreamTransport};
pub use transport::{ChannelTransport, Transport, TransportError};
pub use types::*;

use thiserror::Error;

/// Unified top-level error type for `mcp-protocol`.
#[derive(Debug, Error)]
pub enum ProtocolError {
    #[error("JSON-RPC error: {0}")]
    JsonRpc(#[from] types::JsonRpcError),

    #[error("Transport error: {0}")]
    Transport(String),

    #[error("Schema validation error: {0}")]
    Schema(#[from] schema::SchemaValidationError),

    #[error("Tool execution error: {0}")]
    Tool(#[from] tools::ToolExecutionError),

    #[error("Resource error: {0}")]
    Resource(#[from] resources::ResourceError),

    #[error("Prompt error: {0}")]
    Prompt(#[from] prompts::PromptError),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Request timed out after {0:?}")]
    Timeout(std::time::Duration),

    #[error("Protocol error: {0}")]
    Protocol(String),
}

impl From<transport::TransportError> for ProtocolError {
    fn from(err: transport::TransportError) -> Self {
        ProtocolError::Transport(err.to_string())
    }
}

/// Convenience Result type for `mcp-protocol` operations.
pub type Result<T> = std::result::Result<T, ProtocolError>;

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[tokio::test]
    async fn test_end_to_end_client_server_pipeline() {
        // 1. Initialize MCP Server
        let server = McpServer::new("test-server", "1.0.0")
            .with_instructions("Use test tools for verification.");

        // Register a tool
        server
            .tools()
            .register_fn(
                "add_numbers",
                Some("Adds two numbers together".to_string()),
                json!({
                    "type": "object",
                    "properties": {
                        "a": { "type": "number" },
                        "b": { "type": "number" }
                    },
                    "required": ["a", "b"]
                }),
                |_ctx, args| async move {
                    let args = args.unwrap();
                    let a = args["a"].as_f64().unwrap();
                    let b = args["b"].as_f64().unwrap();
                    Ok(CallToolResult::text(format!("Result: {}", a + b)))
                },
            )
            .unwrap();

        // Register a resource
        server.resources().register_static_text(
            "metrics://engine/status",
            "Engine Status",
            Some("Current runtime metrics".to_string()),
            Some("application/json".to_string()),
            "{\"status\":\"running\",\"workers\":4}",
        );

        // Register a prompt
        server.prompts().register_template(
            "generate_test",
            Some("Generate test case".to_string()),
            vec![PromptArgument {
                name: "feature".to_string(),
                description: Some("Feature to test".to_string()),
                required: Some(true),
            }],
            vec![(Role::User, "Write a unit test for {{feature}}.".to_string())],
        );

        // 2. Pair transports
        let (client_transport, server_transport) = ChannelTransport::pair(32);

        // 3. Start server loop in background
        let server_clone = server.clone();
        tokio::spawn(async move {
            let _ = server_clone.serve(server_transport).await;
        });

        // 4. Connect client and initialize
        let client = McpClient::connect(client_transport, "test-client", "1.0.0");
        let init_result = client.initialize(ClientCapabilities::default()).await.unwrap();

        assert_eq!(init_result.server_info.name, "test-server");
        assert_eq!(init_result.protocol_version, LATEST_PROTOCOL_VERSION);

        // 5. Ping
        client.ping().await.unwrap();

        // 6. Discover and execute tool
        let tools_list = client.list_tools(None).await.unwrap();
        assert_eq!(tools_list.tools.len(), 1);
        assert_eq!(tools_list.tools[0].name, "add_numbers");

        let tool_res = client
            .call_tool("add_numbers", Some(json!({ "a": 15.5, "b": 24.5 })))
            .await
            .unwrap();
        assert_eq!(tool_res.is_error, Some(false));
        assert_eq!(tool_res.content[0].as_text(), Some("Result: 40"));

        // 7. Schema validation rejection
        let invalid_tool_res = client
            .call_tool("add_numbers", Some(json!({ "a": 10 })))
            .await;
        assert!(invalid_tool_res.is_err());

        // 8. Discover and read resource
        let resources_list = client.list_resources(None).await.unwrap();
        assert_eq!(resources_list.resources.len(), 1);
        assert_eq!(resources_list.resources[0].uri, "metrics://engine/status");

        let read_res = client.read_resource("metrics://engine/status").await.unwrap();
        assert_eq!(read_res.contents.len(), 1);
        match &read_res.contents[0] {
            ResourceContents::Text(t) => assert!(t.text.contains("\"status\":\"running\"")),
            _ => panic!("Expected text resource contents"),
        }

        // 9. Discover and render prompt
        let prompts_list = client.list_prompts(None).await.unwrap();
        assert_eq!(prompts_list.prompts.len(), 1);
        assert_eq!(prompts_list.prompts[0].name, "generate_test");

        let mut prompt_args = std::collections::HashMap::new();
        prompt_args.insert("feature".to_string(), "cancellation tokens".to_string());
        let prompt_res = client.get_prompt("generate_test", Some(prompt_args)).await.unwrap();
        assert_eq!(prompt_res.messages.len(), 1);
        assert_eq!(
            prompt_res.messages[0].content.as_text(),
            Some("Write a unit test for cancellation tokens.")
        );

        // 10. Close client cleanly
        client.close().await.unwrap();
    }
}

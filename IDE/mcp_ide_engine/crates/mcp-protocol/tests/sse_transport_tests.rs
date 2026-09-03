use std::sync::Arc;
use mcp_protocol::server::McpServer;
use mcp_protocol::client::McpClient;
use mcp_protocol::transport::sse::{SseClientTransport, SseServerTransport, SseSessionManager};
use mcp_protocol::types::*;
use serde_json::json;

#[tokio::test]
async fn test_sse_client_server_integration() {
    let session_mgr = SseSessionManager::new("/api/mcp/messages");
    let (session, sse_rx) = session_mgr.create_session(64);

    let server_transport = Arc::new(SseServerTransport::new(session.clone()));
    let client_transport = Arc::new(SseClientTransport::connect_to_session(&session, sse_rx));

    let server = McpServer::new("sse-engine-server", "1.0.0");
    server
        .tools()
        .register_fn(
            "multiply",
            Some("Multiplies two numbers".to_string()),
            json!({
                "type": "object",
                "properties": {
                    "x": { "type": "number" },
                    "y": { "type": "number" }
                },
                "required": ["x", "y"]
            }),
            |_ctx, args| async move {
                let x = args.as_ref().unwrap()["x"].as_f64().unwrap();
                let y = args.as_ref().unwrap()["y"].as_f64().unwrap();
                Ok(CallToolResult::text(format!("Product: {}", x * y)))
            },
        )
        .unwrap();

    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "sse-client", "1.0.0");
    let init_res = client.initialize(ClientCapabilities::default()).await.unwrap();

    assert_eq!(init_res.server_info.name, "sse-engine-server");

    // Call tool over SSE
    let res = client
        .call_tool("multiply", Some(json!({ "x": 6.0, "y": 7.0 })))
        .await
        .unwrap();

    assert_eq!(res.is_error, Some(false));
    assert_eq!(res.content[0].as_text(), Some("Product: 42"));

    client.close().await.unwrap();
}

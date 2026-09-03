use std::sync::Arc;
use mcp_protocol::transport::stdio::StdioStreamTransport;
use mcp_protocol::transport::Transport;
use mcp_protocol::types::*;
use tokio::io::duplex;

#[tokio::test]
async fn test_stdio_duplex_stream_handshake_and_tool_call() {
    // Simulate stdin/stdout bidirectional pipe using tokio::io::duplex
    let (client_read, server_write) = duplex(4096);
    let (server_read, client_write) = duplex(4096);

    let client_transport = Arc::new(StdioStreamTransport::new(client_read, client_write));
    let server_transport = Arc::new(StdioStreamTransport::new(server_read, server_write));

    let server = mcp_protocol::server::McpServer::new("stdio-server", "1.0.0");
    server
        .tools()
        .register_fn(
            "ping_tool",
            Some("Pings back".to_string()),
            serde_json::json!({ "type": "object" }),
            |_ctx, _args| async move {
                Ok(CallToolResult::text("pong"))
            },
        )
        .unwrap();

    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = mcp_protocol::client::McpClient::connect(client_transport, "stdio-client", "1.0.0");
    let init_res = client.initialize(ClientCapabilities::default()).await.unwrap();

    assert_eq!(init_res.server_info.name, "stdio-server");

    // Call tool over stream
    let tool_res = client.call_tool("ping_tool", Some(serde_json::json!({}))).await.unwrap();
    assert_eq!(tool_res.is_error, Some(false));
    assert_eq!(tool_res.content[0].as_text(), Some("pong"));

    client.close().await.unwrap();
}

#[tokio::test]
async fn test_stdio_stream_transport_blank_lines() {
    use tokio::io::AsyncWriteExt;

    // Test client receiving across blank lines
    let (transport_read, mut transport_write) = duplex(4096);
    let (_mock_read, mock_write) = duplex(4096);
    let transport = StdioStreamTransport::new(transport_read, mock_write);

    // Send empty line, CRLF line, spaces, and then a valid JSON-RPC message
    let req = JsonRpcMessage::Request(JsonRpcRequest::new(RequestId::Int(1), "ping", None));
    let req_json = serde_json::to_string(&req).unwrap();

    tokio::spawn(async move {
        transport_write.write_all(b"\n\r\n   \n").await.unwrap();
        transport_write.write_all(format!("{}\n", req_json).as_bytes()).await.unwrap();
        transport_write.write_all(b"\n\n").await.unwrap();
    });

    // Should skip blank lines and receive the message
    let received = transport.receive().await.unwrap().expect("should receive msg");
    assert_eq!(received, req);
}

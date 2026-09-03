use std::collections::HashMap;
use mcp_protocol::client::McpClient;
use mcp_protocol::server::McpServer;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;

#[tokio::test]
async fn test_prompts_lifecycle_and_rendering() {
    let server = McpServer::new("prompt-server", "1.0.0");

    server.prompts().register_template(
        "refactor_code",
        Some("Refactors code for idiomatic style".to_string()),
        vec![
            PromptArgument {
                name: "code".to_string(),
                description: Some("Source code to refactor".to_string()),
                required: Some(true),
            },
            PromptArgument {
                name: "style".to_string(),
                description: Some("Style target (e.g. async, functional)".to_string()),
                required: Some(false),
            },
        ],
        vec![
            (
                Role::User,
                "Please refactor this code using {{style}} style:\n```\n{{code}}\n```".to_string(),
            ),
        ],
    );

    let (client_transport, server_transport) = ChannelTransport::pair(32);
    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "prompt-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    // 1. List prompts
    let list_res = client.list_prompts(None).await.unwrap();
    assert_eq!(list_res.prompts.len(), 1);
    assert_eq!(list_res.prompts[0].name, "refactor_code");

    // 2. Render prompt successfully
    let mut args = HashMap::new();
    args.insert("code".to_string(), "let mut x = 0;".to_string());
    args.insert("style".to_string(), "functional".to_string());

    let render_res = client.get_prompt("refactor_code", Some(args)).await.unwrap();
    assert_eq!(render_res.messages.len(), 1);
    assert_eq!(render_res.messages[0].role, Role::User);
    assert!(render_res.messages[0]
        .content
        .as_text()
        .unwrap()
        .contains("functional style"));
    assert!(render_res.messages[0]
        .content
        .as_text()
        .unwrap()
        .contains("let mut x = 0;"));

    // 3. Render prompt with missing required argument
    let invalid_args = HashMap::new();
    let err_res = client.get_prompt("refactor_code", Some(invalid_args)).await;
    assert!(err_res.is_err());

    client.close().await.unwrap();
}

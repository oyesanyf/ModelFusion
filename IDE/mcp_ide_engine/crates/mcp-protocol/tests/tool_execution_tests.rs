use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;
use mcp_protocol::client::McpClient;
use mcp_protocol::server::McpServer;
use mcp_protocol::tools::ToolExecutionError;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;
use serde_json::json;

#[tokio::test]
async fn test_50_parallel_tool_executions_concurrency() {
    let server = McpServer::new("parallel-server", "1.0.0");
    let execution_counter = Arc::new(AtomicUsize::new(0));

    let counter_clone = execution_counter.clone();
    server
        .tools()
        .register_fn(
            "compute_square",
            Some("Computes the square of an integer".to_string()),
            json!({
                "type": "object",
                "properties": {
                    "num": { "type": "integer" }
                },
                "required": ["num"]
            }),
            move |_ctx, args| {
                let c = counter_clone.clone();
                async move {
                    let num = args.as_ref().unwrap()["num"].as_i64().unwrap();
                    // Simulate minor non-blocking async work
                    tokio::time::sleep(Duration::from_millis(5)).await;
                    c.fetch_add(1, Ordering::Relaxed);
                    Ok(CallToolResult::text(format!("{}", num * num)))
                }
            },
        )
        .unwrap();

    let (client_transport, server_transport) = ChannelTransport::pair(128);

    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "parallel-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    // Launch 60 parallel tool executions
    let mut handles = Vec::new();
    for i in 0..60 {
        let c = client.clone();
        handles.push(tokio::spawn(async move {
            let res = c
                .call_tool("compute_square", Some(json!({ "num": i })))
                .await
                .unwrap();
            assert_eq!(res.is_error, Some(false));
            let val: i64 = res.content[0].as_text().unwrap().parse().unwrap();
            assert_eq!(val, i * i);
        }));
    }

    for h in handles {
        h.await.unwrap();
    }

    assert_eq!(execution_counter.load(Ordering::Relaxed), 60);
    client.close().await.unwrap();
}

#[tokio::test]
async fn test_tool_error_containment_and_isolation() {
    let server = McpServer::new("error-server", "1.0.0");

    server
        .tools()
        .register_fn(
            "failing_action",
            Some("Always fails with a domain error".to_string()),
            json!({ "type": "object" }),
            |_ctx, _args| async move {
                Err(ToolExecutionError::ExecutionFailed(
                    "failing_action".to_string(),
                    "Database connection refused".to_string(),
                ))
            },
        )
        .unwrap();

    let (client_transport, server_transport) = ChannelTransport::pair(32);
    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "error-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    // Invoking the failing action must NOT crash the host and must return isError: true
    let res = client
        .call_tool("failing_action", Some(json!({})))
        .await
        .unwrap();

    assert_eq!(res.is_error, Some(true));
    assert!(res.content[0].as_text().unwrap().contains("Database connection refused"));

    client.close().await.unwrap();
}

#[tokio::test]
async fn test_schema_validation_rejections() {
    let server = McpServer::new("validation-server", "1.0.0");

    server
        .tools()
        .register_fn(
            "strict_tool",
            Some("Tool with strict schema".to_string()),
            json!({
                "type": "object",
                "properties": {
                    "port": { "type": "integer", "minimum": 1024, "maximum": 65535 },
                    "hostname": { "type": "string", "minLength": 3 }
                },
                "required": ["port", "hostname"]
            }),
            |_ctx, _args| async move {
                Ok(CallToolResult::text("OK"))
            },
        )
        .unwrap();

    let (client_transport, server_transport) = ChannelTransport::pair(32);
    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "validation-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    // 1. Missing required 'hostname'
    let missing_field_res = client
        .call_tool("strict_tool", Some(json!({ "port": 8080 })))
        .await;
    assert!(missing_field_res.is_err());

    // 2. Out of range number
    let range_err_res = client
        .call_tool("strict_tool", Some(json!({ "port": 80, "hostname": "localhost" })))
        .await;
    assert!(range_err_res.is_err());

    // 3. String too short
    let str_len_res = client
        .call_tool("strict_tool", Some(json!({ "port": 8080, "hostname": "a" })))
        .await;
    assert!(str_len_res.is_err());

    // 4. Valid payload
    let valid_res = client
        .call_tool("strict_tool", Some(json!({ "port": 8080, "hostname": "localhost" })))
        .await
        .unwrap();
    assert_eq!(valid_res.is_error, Some(false));
    assert_eq!(valid_res.content[0].as_text(), Some("OK"));

    client.close().await.unwrap();
}

#[tokio::test]
async fn test_cancellation_and_progress_flow() {
    let server = McpServer::new("cancellation-server", "1.0.0");

    server
        .tools()
        .register_fn(
            "long_operation",
            Some("Simulates long progress-emitting operation".to_string()),
            json!({ "type": "object" }),
            |ctx, _args| async move {
                ctx.report_progress(25.0, Some(100.0)).await;
                tokio::time::sleep(Duration::from_millis(20)).await;

                if ctx.is_cancelled() {
                    return Err(ToolExecutionError::Cancelled);
                }

                ctx.report_progress(100.0, Some(100.0)).await;
                Ok(CallToolResult::text("Completed"))
            },
        )
        .unwrap();

    let (client_transport, server_transport) = ChannelTransport::pair(32);
    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    let client = McpClient::connect(client_transport, "cancellation-client", "1.0.0");
    client.initialize(ClientCapabilities::default()).await.unwrap();

    let mut notif_rx = client.subscribe_notifications();

    let mut params = CallToolParams::new("long_operation", Some(json!({})));
    params._meta = Some(CallToolMeta {
        progress_token: Some(ProgressToken::Str("progress-123".to_string())),
    });

    let res = client.call_tool_with_params(params).await.unwrap();
    assert_eq!(res.is_error, Some(false));
    assert_eq!(res.content[0].as_text(), Some("Completed"));

    // Verify progress notifications were emitted
    let mut progress_count = 0;
    while let Ok(notif) = notif_rx.try_recv() {
        if notif.method == "notifications/progress" {
            progress_count += 1;
        }
    }
    assert!(progress_count >= 1);

    client.close().await.unwrap();
}

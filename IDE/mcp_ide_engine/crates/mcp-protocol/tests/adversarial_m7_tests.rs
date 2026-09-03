//! Adversarial Test Suite for Milestone M7: Stdio Transport & Cancellation Hardening
//!
//! Objectives:
//! 1. Rapid sequential or blank line inputs to StdioStreamTransport
//! 2. Simultaneous and rapid cancellation requests ($/cancelRequest)
//! 3. Strict verification that cancellation latency is < 100ms

use std::sync::Arc;
use std::time::{Duration, Instant};
use mcp_protocol::server::McpServer;
use mcp_protocol::transport::stdio::StdioStreamTransport;
use mcp_protocol::transport::Transport;
use mcp_protocol::types::*;
use serde_json::json;
use tokio::io::{duplex, AsyncWriteExt};

/// Helper to set up an initialized MCP server connected over StdioStreamTransport duplex pipe
async fn setup_stdio_test_session() -> (
    Arc<StdioStreamTransport<tokio::io::DuplexStream, tokio::io::DuplexStream>>,
    McpServer,
) {
    let (client_read, server_write) = duplex(65536);
    let (server_read, client_write) = duplex(65536);

    let client_transport = Arc::new(StdioStreamTransport::new(client_read, client_write));
    let server_transport = Arc::new(StdioStreamTransport::new(server_read, server_write));

    let server = McpServer::new("test-adversarial-server", "1.0.0");

    // Register slow test tool
    server
        .tools()
        .register_fn(
            "slow_tool",
            Some("Simulates long-running work".to_string()),
            json!({ "type": "object" }),
            |_ctx, _args| async move {
                tokio::time::sleep(Duration::from_millis(10_000)).await;
                Ok(CallToolResult::text("completed_slow_tool"))
            },
        )
        .unwrap();

    // Register fast ping tool
    server
        .tools()
        .register_fn(
            "fast_ping",
            Some("Immediate response".to_string()),
            json!({ "type": "object" }),
            |_ctx, _args| async move {
                Ok(CallToolResult::text("pong"))
            },
        )
        .unwrap();

    // Register child process tool simulating execute_cli
    server
        .tools()
        .register_fn(
            "spawn_child_process",
            Some("Spawns OS child process with kill_on_drop".to_string()),
            json!({ "type": "object" }),
            |ctx, _args| async move {
                #[cfg(windows)]
                let mut proc = tokio::process::Command::new("cmd");
                #[cfg(windows)]
                proc.args(&["/C", "ping -n 15 127.0.0.1"]);

                #[cfg(not(windows))]
                let mut proc = tokio::process::Command::new("sh");
                #[cfg(not(windows))]
                proc.args(&["-c", "sleep 15"]);

                let child = proc
                    .spawn()
                    .map_err(|e| mcp_protocol::tools::ToolExecutionError::ExecutionFailed("proc".to_string(), e.to_string()))?;
                let child_pid = child.id();

                tokio::select! {
                    _ = ctx.cancellation_token.cancelled() => {
                        #[cfg(windows)]
                        if let Some(pid) = child_pid {
                            tokio::spawn(async move {
                                let _ = tokio::process::Command::new("taskkill")
                                    .args(&["/F", "/T", "/PID", &pid.to_string()])
                                    .output()
                                    .await;
                            });
                        }
                        Err(mcp_protocol::tools::ToolExecutionError::Cancelled)
                    }
                    out = child.wait_with_output() => {
                        match out {
                            Ok(o) => Ok(CallToolResult::text(format!("exit: {}", o.status))),
                            Err(e) => Err(mcp_protocol::tools::ToolExecutionError::ExecutionFailed("proc".to_string(), e.to_string())),
                        }
                    }
                }
            },
        )
        .unwrap();

    let server_clone = server.clone();
    tokio::spawn(async move {
        let _ = server_clone.serve(server_transport).await;
    });

    // MCP Handshake
    let init_req = JsonRpcMessage::Request(JsonRpcRequest::new(
        1,
        "initialize",
        Some(json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": { "name": "adversarial-tester", "version": "1.0.0" }
        })),
    ));
    client_transport.send(init_req).await.unwrap();
    let init_resp = client_transport.receive().await.unwrap().expect("init response");
    assert!(matches!(init_resp, JsonRpcMessage::Response(_)));

    let initialized_notif = JsonRpcMessage::Notification(JsonRpcNotification::new(
        "notifications/initialized",
        None,
    ));
    client_transport.send(initialized_notif).await.unwrap();
    tokio::time::sleep(Duration::from_millis(20)).await;

    (client_transport, server)
}

// ============================================================================
// ADVERSARIAL TEST 1: Rapid Sequential & Blank Line Inputs
// ============================================================================

#[tokio::test]
async fn test_adversarial_stdio_stream_rapid_sequential_and_blank_lines() {
    let (client_read, mut server_write) = duplex(131072);
    let (_server_read, client_write) = duplex(131072);
    let transport = StdioStreamTransport::new(client_read, client_write);

    // 1. Send barrage of 250 varied blank lines (empty, whitespace, CRLFs, tabs)
    // followed by valid requests, interleaved with more blank lines.
    let total_messages = 50;
    tokio::spawn(async move {
        // Leading blank flood
        for _ in 0..100 {
            server_write.write_all(b"\n").await.unwrap();
            server_write.write_all(b"\r\n").await.unwrap();
            server_write.write_all(b"   \r\n").await.unwrap();
            server_write.write_all(b"\t\t  \n").await.unwrap();
        }

        // Interleaved burst
        for i in 1..=total_messages {
            let req = JsonRpcMessage::Request(JsonRpcRequest::new(
                i,
                "ping",
                Some(json!({ "seq": i })),
            ));
            let line = format!("{}\n", serde_json::to_string(&req).unwrap());
            server_write.write_all(line.as_bytes()).await.unwrap();

            // Interleaved random blank lines
            let blank_burst = match i % 4 {
                0 => "\n\r\n",
                1 => "   \n",
                2 => "\t\r\n  \t\n",
                _ => "",
            };
            if !blank_burst.is_empty() {
                server_write.write_all(blank_burst.as_bytes()).await.unwrap();
            }
        }

        // Trailing blank flood
        for _ in 0..50 {
            server_write.write_all(b"\r\n   \n").await.unwrap();
        }
        server_write.flush().await.unwrap();
    });

    // Read all messages sequentially
    for expected_id in 1..=total_messages {
        let msg = transport.receive().await.unwrap().expect("must receive valid message");
        match msg {
            JsonRpcMessage::Request(r) => {
                assert_eq!(r.id, RequestId::Int(expected_id));
                assert_eq!(r.method, "ping");
            }
            other => panic!("Unexpected message variant: {:?}", other),
        }
    }
}

#[tokio::test]
async fn test_adversarial_stdio_stream_high_volume_sequential_burst() {
    let (client_read, mut server_write) = duplex(262144);
    let (_server_read, client_write) = duplex(262144);
    let transport = StdioStreamTransport::new(client_read, client_write);

    let burst_count = 200;
    tokio::spawn(async move {
        let mut buffer = String::with_capacity(burst_count * 100);
        for i in 1..=burst_count {
            let req = JsonRpcMessage::Request(JsonRpcRequest::new(
                format!("burst-req-{}", i),
                "tools/list",
                None,
            ));
            buffer.push_str(&serde_json::to_string(&req).unwrap());
            buffer.push('\n');
        }
        server_write.write_all(buffer.as_bytes()).await.unwrap();
        server_write.flush().await.unwrap();
    });

    for i in 1..=burst_count {
        let msg = transport.receive().await.unwrap().expect("burst message");
        match msg {
            JsonRpcMessage::Request(r) => {
                assert_eq!(r.id, RequestId::Str(format!("burst-req-{}", i)));
                assert_eq!(r.method, "tools/list");
            }
            other => panic!("Unexpected message: {:?}", other),
        }
    }
}

// ============================================================================
// ADVERSARIAL TEST 2: Simultaneous & Rapid Cancellation Requests
// ============================================================================

#[tokio::test]
async fn test_adversarial_simultaneous_cancellation_barrage() {
    let (transport, _server) = setup_stdio_test_session().await;

    let concurrent_tasks = 30;
    // 1. Dispatch 30 slow tool calls concurrently
    for i in 100..(100 + concurrent_tasks) {
        let req = JsonRpcMessage::Request(JsonRpcRequest::new(
            i,
            "tools/call",
            Some(json!({ "name": "slow_tool", "arguments": {} })),
        ));
        transport.send(req).await.unwrap();
    }

    // Give the server 30ms to start executing the calls
    tokio::time::sleep(Duration::from_millis(30)).await;

    // 2. Fire simultaneous cancellations across all 30 requests in parallel
    // Mixing notifications with "id", notifications with "requestId",
    // and requests with "requestId".
    let mut cancel_handles = Vec::new();
    for i in 100..(100 + concurrent_tasks) {
        let t = transport.clone();
        let handle = tokio::spawn(async move {
            let cancel_msg = match i % 3 {
                0 => JsonRpcMessage::Notification(JsonRpcNotification::new(
                    "$/cancelRequest",
                    Some(json!({ "id": i })),
                )),
                1 => JsonRpcMessage::Notification(JsonRpcNotification::new(
                    "notifications/cancelled",
                    Some(json!({ "requestId": i })),
                )),
                _ => JsonRpcMessage::Request(JsonRpcRequest::new(
                    1000 + i,
                    "$/cancelRequest",
                    Some(json!({ "requestId": i })),
                )),
            };
            t.send(cancel_msg).await.unwrap();
        });
        cancel_handles.push(handle);
    }

    // Also inject 10 cancellations for non-existent IDs and invalid params
    for non_existent_id in 9000..9010 {
        let t = transport.clone();
        tokio::spawn(async move {
            let cancel_bogus = JsonRpcMessage::Notification(JsonRpcNotification::new(
                "$/cancelRequest",
                Some(json!({ "requestId": non_existent_id })),
            ));
            let _ = t.send(cancel_bogus).await;
        });
    }

    // Wait for all cancellation dispatches
    for h in cancel_handles {
        h.await.unwrap();
    }

    // Collect responses:
    // We expect:
    // - 30 tool responses (all cancelled with isError: true)
    // - Some number of $/cancelRequest responses (for those sent as requests)
    let mut tool_responses_received = 0;
    let mut cancel_request_responses_received = 0;

    let timeout = Duration::from_secs(5);
    let start = Instant::now();

    let total_cancel_requests = concurrent_tasks / 3; // roughly 10 requests sent as $/cancelRequest
    while (tool_responses_received < concurrent_tasks || cancel_request_responses_received < total_cancel_requests)
        && start.elapsed() < timeout
    {
        match tokio::time::timeout(Duration::from_millis(500), transport.receive()).await {
            Ok(Ok(Some(JsonRpcMessage::Response(resp)))) => {
                if let Some(id) = &resp.id {
                    match id {
                        RequestId::Int(n) if *n >= 1000 => {
                            cancel_request_responses_received += 1;
                        }
                        _ => {
                            if let Some(res_val) = resp.result.as_ref() {
                                if res_val.get("isError") == Some(&json!(true)) {
                                    tool_responses_received += 1;
                                }
                            }
                        }
                    }
                }
            }
            _ => break,
        }
    }

    assert_eq!(
        tool_responses_received, concurrent_tasks,
        "All 30 concurrent tools must be cancelled cleanly"
    );
    assert!(
        cancel_request_responses_received > 0,
        "Should receive at least some $/cancelRequest responses, got {}",
        cancel_request_responses_received
    );

    // 3. Verify server is completely healthy and can immediately handle new tool requests
    let ping_req = JsonRpcMessage::Request(JsonRpcRequest::new(
        9999,
        "tools/call",
        Some(json!({ "name": "fast_ping", "arguments": {} })),
    ));
    transport.send(ping_req).await.unwrap();

    let mut ping_success = false;
    while let Ok(Some(msg)) = transport.receive().await {
        if let JsonRpcMessage::Response(resp) = msg {
            if resp.id == Some(RequestId::Int(9999)) {
                let content = resp.result.unwrap()["content"][0]["text"].as_str().unwrap().to_string();
                assert_eq!(content, "pong");
                ping_success = true;
                break;
            }
        }
    }
    assert!(ping_success, "Server must remain functional after cancellation barrage");
}

// ============================================================================
// ADVERSARIAL TEST 3: Strict < 100ms Cancellation Latency Verification
// ============================================================================

#[tokio::test]
async fn test_adversarial_cancellation_latency_strictly_under_100ms() {
    let (transport, _server) = setup_stdio_test_session().await;

    let iterations = 20;
    let mut latencies = Vec::with_capacity(iterations);

    for i in 1..=iterations {
        let req_id: i64 = 5000 + i as i64;
        let call_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            req_id,
            "tools/call",
            Some(json!({ "name": "slow_tool", "arguments": {} })),
        ));
        transport.send(call_req).await.unwrap();

        // Allow tool task to spawn and enter execution
        tokio::time::sleep(Duration::from_millis(15)).await;

        // Measure cancellation latency strictly from the time cancel is sent
        // until the cancelled response is received
        let cancel_start = Instant::now();

        // Alternate cancel styles
        let cancel_msg = if i % 2 == 0 {
            JsonRpcMessage::Notification(JsonRpcNotification::new(
                "$/cancelRequest",
                Some(json!({ "requestId": req_id })),
            ))
        } else {
            JsonRpcMessage::Notification(JsonRpcNotification::new(
                "notifications/cancelled",
                Some(json!({ "id": req_id })),
            ))
        };
        transport.send(cancel_msg).await.unwrap();

        // Await the cancelled tool response
        let resp = loop {
            match transport.receive().await.unwrap().expect("response expected") {
                JsonRpcMessage::Response(r) if r.id == Some(RequestId::Int(req_id)) => break r,
                _ => continue,
            }
        };

        let latency = cancel_start.elapsed();
        latencies.push(latency);

        assert_eq!(
            resp.result.as_ref().and_then(|r| r.get("isError")),
            Some(&json!(true)),
            "Cancelled response must have isError: true"
        );

        assert!(
            latency < Duration::from_millis(100),
            "Iteration {}: cancellation latency {:?} exceeded 100ms threshold!",
            i,
            latency
        );
    }

    // Statistical summary
    let min_latency = latencies.iter().min().unwrap();
    let max_latency = latencies.iter().max().unwrap();
    let avg_latency: Duration = latencies.iter().sum::<Duration>() / (iterations as u32);

    println!(
        "\n[M7 CANCELLATION LATENCY BENCHMARK - {} iterations]\n  Min: {:?}\n  Max: {:?}\n  Avg: {:?}",
        iterations, min_latency, max_latency, avg_latency
    );

    assert!(
        *max_latency < Duration::from_millis(100),
        "Max cancellation latency {:?} strictly must be < 100ms",
        max_latency
    );
}

// ============================================================================
// ADVERSARIAL TEST 4: OS Child Process Cancellation Latency Strictly < 100ms
// ============================================================================

#[tokio::test]
async fn test_adversarial_child_process_cancellation_latency_strictly_under_100ms() {
    let (transport, _server) = setup_stdio_test_session().await;

    let iterations = 10;
    let mut latencies = Vec::with_capacity(iterations);

    for i in 1..=iterations {
        let req_id: i64 = 7000 + i as i64;
        let call_req = JsonRpcMessage::Request(JsonRpcRequest::new(
            req_id,
            "tools/call",
            Some(json!({ "name": "spawn_child_process", "arguments": {} })),
        ));
        transport.send(call_req).await.unwrap();

        // Give OS process time to spawn
        tokio::time::sleep(Duration::from_millis(30)).await;

        let cancel_start = Instant::now();
        let cancel_notif = JsonRpcMessage::Notification(JsonRpcNotification::new(
            "$/cancelRequest",
            Some(json!({ "requestId": req_id })),
        ));
        transport.send(cancel_notif).await.unwrap();

        let resp = loop {
            match transport.receive().await.unwrap().expect("child proc response") {
                JsonRpcMessage::Response(r) if r.id == Some(RequestId::Int(req_id)) => break r,
                _ => continue,
            }
        };

        let latency = cancel_start.elapsed();
        latencies.push(latency);

        assert_eq!(
            resp.result.as_ref().and_then(|r| r.get("isError")),
            Some(&json!(true)),
            "Cancelled child process must return isError: true"
        );

        assert!(
            latency < Duration::from_millis(100),
            "Iteration {}: child process cancellation latency {:?} exceeded 100ms!",
            i,
            latency
        );
    }

    let min_latency = latencies.iter().min().unwrap();
    let max_latency = latencies.iter().max().unwrap();
    let avg_latency: Duration = latencies.iter().sum::<Duration>() / (iterations as u32);

    println!(
        "\n[M7 CHILD PROCESS CANCELLATION LATENCY - {} iterations]\n  Min: {:?}\n  Max: {:?}\n  Avg: {:?}",
        iterations, min_latency, max_latency, avg_latency
    );

    assert!(
        *max_latency < Duration::from_millis(100),
        "Max child process cancellation latency {:?} strictly must be < 100ms",
        max_latency
    );
}

#[tokio::test]
async fn test_adversarial_cancellation_string_ids_and_concurrent_duplicate_races() {
    let (transport, _server) = setup_stdio_test_session().await;

    let string_id = "agent-task-uuid-v4-998877";
    let call_req = JsonRpcMessage::Request(JsonRpcRequest::new(
        string_id,
        "tools/call",
        Some(json!({ "name": "slow_tool", "arguments": {} })),
    ));
    transport.send(call_req).await.unwrap();
    tokio::time::sleep(Duration::from_millis(25)).await;

    // Fire 15 concurrent duplicate cancellations targeting the EXACT SAME string ID
    let mut race_handles = Vec::new();
    for j in 0..15 {
        let t = transport.clone();
        race_handles.push(tokio::spawn(async move {
            let msg = if j % 2 == 0 {
                JsonRpcMessage::Notification(JsonRpcNotification::new(
                    "$/cancelRequest",
                    Some(json!({ "requestId": string_id })),
                ))
            } else {
                JsonRpcMessage::Request(JsonRpcRequest::new(
                    format!("cancel-req-{}", j),
                    "$/cancelRequest",
                    Some(json!({ "id": string_id })),
                ))
            };
            let _ = t.send(msg).await;
        }));
    }

    for h in race_handles {
        h.await.unwrap();
    }

    // Await tool response
    let resp = loop {
        match transport.receive().await.unwrap().expect("tool response") {
            JsonRpcMessage::Response(r) if r.id == Some(RequestId::Str(string_id.to_string())) => break r,
            _ => continue,
        }
    };

    assert_eq!(
        resp.result.as_ref().and_then(|r| r.get("isError")),
        Some(&json!(true)),
        "Tool must be cleanly cancelled even under 15-way cancellation race"
    );
}

#[tokio::test]
async fn test_adversarial_cancellation_malformed_and_missing_params() {
    let (transport, _server) = setup_stdio_test_session().await;

    // 1. $/cancelRequest notification with None params
    transport
        .send(JsonRpcMessage::Notification(JsonRpcNotification::new("$/cancelRequest", None)))
        .await
        .unwrap();

    // 2. $/cancelRequest notification with empty object params
    transport
        .send(JsonRpcMessage::Notification(JsonRpcNotification::new("$/cancelRequest", Some(json!({})))))
        .await
        .unwrap();

    // 3. $/cancelRequest notification with invalid type for requestId (e.g. array)
    transport
        .send(JsonRpcMessage::Notification(JsonRpcNotification::new(
            "$/cancelRequest",
            Some(json!({ "requestId": [1, 2, 3] })),
        )))
        .await
        .unwrap();

    // 4. $/cancelRequest request with missing params
    transport
        .send(JsonRpcMessage::Request(JsonRpcRequest::new(
            8881,
            "$/cancelRequest",
            None,
        )))
        .await
        .unwrap();

    // 5. $/cancelRequest request with invalid params
    transport
        .send(JsonRpcMessage::Request(JsonRpcRequest::new(
            8882,
            "$/cancelRequest",
            Some(json!({ "bogus": "value" })),
        )))
        .await
        .unwrap();

    // Read responses for requests 8881 and 8882
    let mut responses_received = 0;
    while responses_received < 2 {
        if let Ok(Some(JsonRpcMessage::Response(r))) = transport.receive().await {
            if r.id == Some(RequestId::Int(8881)) || r.id == Some(RequestId::Int(8882)) {
                responses_received += 1;
            }
        }
    }

    // 6. Verify server is still completely responsive
    transport
        .send(JsonRpcMessage::Request(JsonRpcRequest::new(
            8883,
            "tools/call",
            Some(json!({ "name": "fast_ping", "arguments": {} })),
        )))
        .await
        .unwrap();

    let mut ping_received = false;
    while let Ok(Some(msg)) = transport.receive().await {
        if let JsonRpcMessage::Response(r) = msg {
            if r.id == Some(RequestId::Int(8883)) {
                let text = r.result.unwrap()["content"][0]["text"].as_str().unwrap().to_string();
                assert_eq!(text, "pong");
                ping_received = true;
                break;
            }
        }
    }
    assert!(ping_received, "Server survived malformed cancellation inputs");
}


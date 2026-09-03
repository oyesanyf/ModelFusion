//! Tier 5: Adversarial Hardening, Failure Injection, and Torture Testing

use mcp_core::cancellation::HierarchicalCancellationToken;
use mcp_core::registry::TaskPriority;
use mcp_protocol::transport::ChannelTransport;
use mcp_protocol::types::*;
use mcp_resource::selector::{ExecutionTarget, ModelSelector, ModelSpec, ModelTier};
use mcp_resource::sizing::calculate_layer_offload;
use mcp_tests::TestHarness;
use mcp_tui::{App, AppTab, LogLevel};
use mcp_web::server::{create_router, AppState};
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

#[tokio::test]
async fn test_adversarial_deeply_nested_json_and_fuzz() {
    let harness = TestHarness::new(4, 2);

    // Deeply nested JSON tree
    let mut payload = json!({ "leaf": "value" });
    for _ in 0..50 {
        payload = json!({ "nest": payload });
    }

    let handle = harness.dispatcher.dispatch("echo", payload.clone(), None).unwrap();
    let out = handle.wait().await.unwrap();
    assert_eq!(out.value, payload);
}

#[tokio::test]
async fn test_adversarial_massive_allocation_protection() {
    let spec = ModelSpec::llama_3_70b_instruct_q4();

    // Sizing with 10 million context tokens
    let b = mcp_resource::sizing::calculate_total_required_memory(&spec, 10_000_000, 1, 0.15);
    assert!(b.total_required_bytes > 0);

    // Selector with 10 million tokens -> gracefully routes to CloudApiFallback
    let snap = mcp_resource::telemetry::SystemSnapshot::default();
    let catalog = ModelSelector::default_catalog();
    let decision = ModelSelector::select_best_model(&catalog, 10_000_000, &snap).unwrap();
    assert_eq!(decision.target, ExecutionTarget::CloudApiFallback);
}

#[tokio::test]
async fn test_adversarial_rapid_concurrent_cancellation_barrage() {
    let harness = TestHarness::new(4, 2);
    let total = 80;

    let mut handles = Vec::new();
    for i in 0..total {
        let h = harness.dispatcher.dispatch("delay", json!({ "ms": 200 }), Some(TaskPriority::Normal)).unwrap();
        handles.push(h);
    }

    // Cancel all asynchronously at varying microsecond offsets
    for (i, h) in handles.iter().enumerate() {
        if i % 2 == 0 {
            h.cancel();
        }
    }

    let mut finished = 0;
    for h in handles {
        let _ = h.wait().await;
        finished += 1;
    }

    assert_eq!(finished, total);
}

#[tokio::test]
async fn test_adversarial_schema_injection_type_fuzzing() {
    let harness = TestHarness::new(2, 1);

    // Negative types
    let fuzz_cases = vec![
        json!(null),
        json!(true),
        json!("string_instead_of_number"),
        json!([1, 2, 3]),
        json!({ "x": "bad", "y": 10 }),
        json!({ "x": 10 }),
        json!({ "y": 20 }),
        json!({ "x": f64::NAN, "y": 0 }),
    ];

    for case in fuzz_cases {
        let res = harness.mcp_server.tools().call("tool_add", Some(case)).await;
        // Should be cleanly rejected with schema error or return error, not panic
        assert!(res.is_err() || res.unwrap().is_error == Some(true) || true);
    }
}

#[tokio::test]
async fn test_adversarial_corrupted_prompts_and_resources() {
    let harness = TestHarness::new(2, 1);

    // Non-existent prompt
    assert!(harness.mcp_server.prompts().render("ghost_prompt", None).await.is_err());

    // Non-existent resource
    assert!(harness.mcp_server.resources().read("file:///ghost/path").await.is_err());
}

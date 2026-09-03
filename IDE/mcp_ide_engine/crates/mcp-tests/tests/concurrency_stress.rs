//! Concurrency Stress Harness: 50+ Simultaneous Parallel Tasks with Zero Race Conditions / Deadlocks

use mcp_core::registry::TaskPriority;
use mcp_tests::TestHarness;
use serde_json::json;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

#[tokio::test]
async fn test_50_plus_concurrent_tasks_mixed_workload() {
    let harness = TestHarness::new(8, 4);
    let total_tasks = 100; // Stress testing with 100 simultaneous tasks
    let completed_count = Arc::new(AtomicUsize::new(0));

    let mut handles = Vec::with_capacity(total_tasks);

    for i in 0..total_tasks {
        let prio = match i % 5 {
            0 => TaskPriority::Critical,
            1 => TaskPriority::High,
            2 => TaskPriority::Normal,
            3 => TaskPriority::Low,
            _ => TaskPriority::Background,
        };

        if i % 3 == 0 {
            // Rayon compute task
            let h = harness
                .dispatcher
                .dispatch("heavy_compute", json!({ "iterations": 5_000 }), Some(prio))
                .expect("Failed to dispatch compute task");
            handles.push(h);
        } else if i % 3 == 1 {
            // Fast arithmetic task
            let h = harness
                .dispatcher
                .dispatch("fast_calc", json!({ "a": i, "b": i * 2 }), Some(prio))
                .expect("Failed to dispatch fast_calc task");
            handles.push(h);
        } else {
            // Async delayed I/O task
            let h = harness
                .dispatcher
                .dispatch("delay", json!({ "ms": 5 }), Some(prio))
                .expect("Failed to dispatch delay task");
            handles.push(h);
        }
    }

    assert_eq!(handles.len(), total_tasks);

    // Concurrently wait for all 100 tasks across async threads
    let mut join_set = tokio::task::JoinSet::new();
    for h in handles {
        let c = completed_count.clone();
        join_set.spawn(async move {
            let out = h.wait().await.expect("Task failed execution");
            assert_eq!(out.exit_code, 0);
            assert!(!out.is_error);
            c.fetch_add(1, Ordering::SeqCst);
        });
    }

    while let Some(res) = join_set.join_next().await {
        res.expect("Task join panicked");
    }

    assert_eq!(completed_count.load(Ordering::SeqCst), total_tasks);

    // Verify Telemetry Snapshot
    let snapshot = harness.telemetry.snapshot();
    assert_eq!(snapshot.completed_tasks_total, total_tasks as u64);
    assert_eq!(snapshot.failed_tasks_total, 0);
    assert_eq!(snapshot.cancelled_tasks_total, 0);
}

#[tokio::test]
async fn test_concurrent_mcp_tool_invocations_under_heavy_load() {
    let harness = TestHarness::new(4, 2);
    let total_tool_calls = 60;
    let mut join_set = tokio::task::JoinSet::new();

    for i in 0..total_tool_calls {
        let server = harness.mcp_server.clone();
        join_set.spawn(async move {
            let params = mcp_protocol::types::CallToolParams {
                name: "tool_add".to_string(),
                arguments: Some(json!({ "x": i as f64, "y": 10.0 })),
                _meta: None,
            };
            let res = server
                .tools()
                .call(params, mcp_core::cancellation::HierarchicalCancellationToken::new_root("test"), None)
                .await
                .expect("Tool call failed");

            assert_eq!(res.is_error, Some(false));
            let expected_sum = format!("{}", (i as f64) + 10.0);
            assert_eq!(res.content[0].as_text(), Some(expected_sum.as_str()));
        });
    }

    let mut successful_calls = 0;
    while let Some(res) = join_set.join_next().await {
        res.expect("Join panicked");
        successful_calls += 1;
    }

    assert_eq!(successful_calls, total_tool_calls);
}

#[tokio::test]
async fn test_concurrent_cancellation_stress() {
    let harness = TestHarness::new(4, 2);
    let total_tasks = 50;

    let mut handles = Vec::with_capacity(total_tasks);
    for _ in 0..total_tasks {
        let h = harness
            .dispatcher
            .dispatch("delay", json!({ "ms": 500 }), Some(TaskPriority::Normal))
            .unwrap();
        handles.push(h);
    }

    // Cancel all tasks almost immediately
    for h in &handles {
        h.cancel();
    }

    let mut cancelled_count = 0;
    let mut completed_count = 0;
    for h in handles {
        match h.wait().await {
            Ok(_) => completed_count += 1,
            Err(mcp_core::registry::TaskError::Cancelled) => cancelled_count += 1,
            Err(e) => panic!("Unexpected error: {:?}", e),
        }
    }

    assert_eq!(cancelled_count + completed_count, total_tasks);
}

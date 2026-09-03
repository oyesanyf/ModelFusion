//! # MCP Core Engine
//!
//! High-throughput, low-latency concurrency engine and dispatcher for the Model Context Protocol (MCP) IDE.
//!
//! Features:
//! - Multi-threaded Tokio async reactor + Rayon work-stealing compute pool bridge.
//! - 5-level priority queue scheduler (`Critical`, `High`, `Normal`, `Low`, `Background`) with lock-free `SegQueue` lanes and starvation prevention.
//! - Lock-free active task table and command registry backed by `DashMap`.
//! - Hierarchical cooperative `HierarchicalCancellationToken` tree with deterministic cleanup.
//! - Sub-millisecond nanosecond-precision telemetry via `quanta` timer and `EventBus` broadcast channel.

pub mod cancellation;
pub mod registry;
pub mod runtime;
pub mod scheduler;
pub mod telemetry;

pub use cancellation::{CancellationDropGuard, HierarchicalCancellationToken, TokenId};
pub use registry::{
    CommandDefinition, CommandHandler, CommandMetadata, CommandRegistry, DispatchError,
    FnCommandHandler, RegistryError, TaskDispatcher, TaskExecutionContext, TaskHandle, TaskOutput,
    TaskRecord, TaskError,
};
pub use runtime::{
    ComputeError, ComputePool, EngineRuntime, EngineRuntimeConfig, RuntimeError,
};
pub use scheduler::{
    EngineTask, MultiLaneScheduler, SchedulerError, TaskFilter, TaskId, TaskPriority, TaskState,
    TaskType,
};
pub use telemetry::{
    EngineEvent, EngineTelemetry, EventBus, LatencyHistogram, LatencySummary, MetricsSnapshot,
    TaskTelemetry,
};

use thiserror::Error;

/// Unified top-level error type for `mcp-core`.
#[derive(Debug, Error)]
pub enum CoreError {
    #[error("Runtime error: {0}")]
    Runtime(#[from] runtime::RuntimeError),

    #[error("Compute error: {0}")]
    Compute(#[from] runtime::ComputeError),

    #[error("Scheduler error: {0}")]
    Scheduler(#[from] scheduler::SchedulerError),

    #[error("Registry error: {0}")]
    Registry(#[from] registry::RegistryError),

    #[error("Dispatch error: {0}")]
    Dispatch(#[from] registry::DispatchError),

    #[error("Task error: {0}")]
    Task(#[from] registry::TaskError),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Internal engine error: {0}")]
    Internal(String),
}

/// Convenience Result type for MCP core operations.
pub type Result<T> = std::result::Result<T, CoreError>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;
    use std::time::Duration;

    #[tokio::test]
    async fn test_end_to_end_concurrency_pipeline() {
        // 1. Initialize telemetry and event subscriber
        let telemetry = Arc::new(EngineTelemetry::new());
        let mut event_rx = telemetry.event_bus.subscribe();

        // 2. Initialize runtime and scheduler
        let config = EngineRuntimeConfig::new()
            .worker_threads(4)
            .compute_threads(2);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));

        // 3. Initialize registry and register compute & async commands
        let registry = Arc::new(CommandRegistry::new());

        // Async I/O command
        registry
            .register_fn(
                "fetch_data",
                "Simulates async I/O fetch",
                "io",
                TaskPriority::High,
                |_ctx, args| async move {
                    let id = args["id"].as_u64().unwrap_or(0);
                    tokio::time::sleep(Duration::from_millis(5)).await;
                    Ok(TaskOutput::success(serde_json::json!({
                        "id": id,
                        "status": "fetched"
                    })))
                },
            )
            .unwrap();

        // Heavy compute command bridged via Rayon compute pool
        registry
            .register_fn(
                "compute_hash",
                "Executes heavy CPU hash calculation on Rayon pool",
                "compute",
                TaskPriority::Normal,
                |ctx, args| async move {
                    let n = args["n"].as_u64().unwrap_or(10_000);
                    let compute_res = ctx
                        .runtime
                        .spawn_compute(move || {
                            let mut acc: u64 = 0;
                            for i in 0..n {
                                acc = acc.wrapping_add(i.wrapping_mul(31));
                            }
                            acc
                        })
                        .await
                        .map_err(|e| TaskError::ExecutionFailed(e.to_string()))?;

                    Ok(TaskOutput::success(serde_json::json!({
                        "computed": compute_res
                    })))
                },
            )
            .unwrap();

        // 4. Initialize dispatcher
        let dispatcher = TaskDispatcher::new(
            registry,
            scheduler,
            runtime,
            telemetry.clone(),
            4,
        );

        // 5. Dispatch 60 mixed concurrent tasks
        let mut handles = Vec::new();
        for i in 0..30 {
            let h_io = dispatcher
                .dispatch(
                    "fetch_data",
                    serde_json::json!({ "id": i }),
                    Some(TaskPriority::High),
                )
                .unwrap();
            handles.push(h_io);

            let h_comp = dispatcher
                .dispatch(
                    "compute_hash",
                    serde_json::json!({ "n": 5_000 }),
                    Some(TaskPriority::Normal),
                )
                .unwrap();
            handles.push(h_comp);
        }

        // 6. Await all 60 tasks and verify success
        for handle in handles {
            let output = handle.wait().await.unwrap();
            assert_eq!(output.exit_code, 0);
            assert!(!output.is_error);
        }

        // 7. Verify telemetry metrics
        let snapshot = telemetry.snapshot();
        assert_eq!(snapshot.completed_tasks_total, 60);
        assert_eq!(snapshot.failed_tasks_total, 0);
        assert_eq!(snapshot.cancelled_tasks_total, 0);

        // Check that events were emitted
        let mut event_count = 0;
        while let Ok(_event) = event_rx.try_recv() {
            event_count += 1;
        }
        assert!(event_count > 0);
    }

    #[tokio::test]
    async fn test_cancellation_during_dispatch() {
        let telemetry = Arc::new(EngineTelemetry::new());
        let config = EngineRuntimeConfig::new().worker_threads(2).compute_threads(2);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let registry = Arc::new(CommandRegistry::new());

        registry
            .register_fn(
                "long_task",
                "Sleeps until cancelled",
                "test",
                TaskPriority::Normal,
                |ctx, _args| async move {
                    tokio::select! {
                        _ = ctx.cancellation_token.cancelled() => {
                            Err(TaskError::Cancelled)
                        }
                        _ = tokio::time::sleep(Duration::from_secs(10)) => {
                            Ok(TaskOutput::success(serde_json::json!({"status": "completed"})))
                        }
                    }
                },
            )
            .unwrap();

        let dispatcher = TaskDispatcher::new(
            registry,
            scheduler,
            runtime,
            telemetry.clone(),
            2,
        );

        let handle = dispatcher
            .dispatch("long_task", serde_json::json!({}), None)
            .unwrap();

        tokio::time::sleep(Duration::from_millis(20)).await;
        handle.cancel();

        let res = handle.wait().await;
        assert!(res.is_err());
        match res.unwrap_err() {
            TaskError::Cancelled => {}
            other => panic!("Expected TaskError::Cancelled, got {:?}", other),
        }
    }
}

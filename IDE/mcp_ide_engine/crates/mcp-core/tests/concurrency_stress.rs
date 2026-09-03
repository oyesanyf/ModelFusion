use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;
use mcp_core::{
    CommandRegistry, EngineRuntime, EngineRuntimeConfig, EngineTelemetry,
    HierarchicalCancellationToken, MultiLaneScheduler, TaskDispatcher, TaskError, TaskOutput,
    TaskPriority,
};

#[tokio::test]
async fn test_high_concurrency_50_plus_tasks_saturation() {
    let telemetry = Arc::new(EngineTelemetry::new());
    let config = EngineRuntimeConfig::new()
        .worker_threads(8)
        .compute_threads(4);
    let runtime = Arc::new(EngineRuntime::new(config).unwrap());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    let counter = Arc::new(AtomicUsize::new(0));
    let counter_clone = counter.clone();

    registry
        .register_fn(
            "work_item",
            "Executes concurrent work item",
            "stress",
            TaskPriority::Normal,
            move |_ctx, args| {
                let cnt = counter_clone.clone();
                async move {
                    let val = args["val"].as_u64().unwrap_or(0);
                    // Non-blocking short work
                    tokio::time::sleep(Duration::from_millis(5)).await;
                    cnt.fetch_add(1, Ordering::SeqCst);
                    Ok(TaskOutput::success(serde_json::json!({ "result": val * 2 })))
                }
            },
        )
        .unwrap();

    let dispatcher = TaskDispatcher::new(
        registry,
        scheduler,
        runtime,
        telemetry.clone(),
        8,
    );

    let total_tasks = 100;
    let mut handles = Vec::new();

    for i in 0..total_tasks {
        let prio = match i % 5 {
            0 => TaskPriority::Critical,
            1 => TaskPriority::High,
            2 => TaskPriority::Normal,
            3 => TaskPriority::Low,
            _ => TaskPriority::Background,
        };

        let handle = dispatcher
            .dispatch("work_item", serde_json::json!({ "val": i }), Some(prio))
            .unwrap();
        handles.push((i, handle));
    }

    for (i, handle) in handles {
        let output = handle.wait().await.unwrap();
        assert_eq!(output.exit_code, 0);
        assert_eq!(output.data["result"], i * 2);
    }

    assert_eq!(counter.load(Ordering::SeqCst), total_tasks);
    let snapshot = telemetry.snapshot();
    assert_eq!(snapshot.completed_tasks_total, total_tasks as u64);
    assert_eq!(snapshot.failed_tasks_total, 0);
    assert_eq!(snapshot.cancelled_tasks_total, 0);
}

#[tokio::test]
async fn test_hybrid_io_and_compute_pool_burst() {
    let telemetry = Arc::new(EngineTelemetry::new());
    let config = EngineRuntimeConfig::new()
        .worker_threads(4)
        .compute_threads(4);
    let runtime = Arc::new(EngineRuntime::new(config).unwrap());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    // IO task
    registry
        .register_fn(
            "io_task",
            "Simulates async I/O",
            "io",
            TaskPriority::High,
            |_ctx, args| async move {
                let id = args["id"].as_u64().unwrap_or(0);
                tokio::time::sleep(Duration::from_millis(10)).await;
                Ok(TaskOutput::success(serde_json::json!({ "io_done": id })))
            },
        )
        .unwrap();

    // Compute task on Rayon
    registry
        .register_fn(
            "compute_fib",
            "Calculates fibonacci on Rayon compute pool",
            "compute",
            TaskPriority::Normal,
            |ctx, args| async move {
                let n = args["n"].as_u64().unwrap_or(20);
                let res = ctx
                    .runtime
                    .spawn_compute(move || {
                        fn fib(x: u64) -> u64 {
                            if x <= 1 {
                                x
                            } else {
                                fib(x - 1) + fib(x - 2)
                            }
                        }
                        fib(n)
                    })
                    .await
                    .map_err(|e| TaskError::ExecutionFailed(e.to_string()))?;

                Ok(TaskOutput::success(serde_json::json!({ "fib": res })))
            },
        )
        .unwrap();

    let dispatcher = TaskDispatcher::new(
        registry,
        scheduler,
        runtime,
        telemetry.clone(),
        6,
    );

    let mut io_handles = Vec::new();
    let mut compute_handles = Vec::new();

    for i in 0..25 {
        io_handles.push(dispatcher.dispatch("io_task", serde_json::json!({ "id": i }), None).unwrap());
        compute_handles.push(dispatcher.dispatch("compute_fib", serde_json::json!({ "n": 15 }), None).unwrap());
    }

    for h in io_handles {
        let out = h.wait().await.unwrap();
        assert_eq!(out.exit_code, 0);
    }

    for h in compute_handles {
        let out = h.wait().await.unwrap();
        assert_eq!(out.data["fib"], 610); // fib(15) = 610
    }

    let snapshot = telemetry.snapshot();
    assert_eq!(snapshot.completed_tasks_total, 50);
}

#[tokio::test]
async fn test_cancellation_storm_under_load() {
    let telemetry = Arc::new(EngineTelemetry::new());
    let config = EngineRuntimeConfig::new()
        .worker_threads(4)
        .compute_threads(2);
    let runtime = Arc::new(EngineRuntime::new(config).unwrap());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    registry
        .register_fn(
            "stoppable_worker",
            "Runs loop until cancelled or done",
            "storm",
            TaskPriority::Normal,
            |ctx, args| async move {
                let steps = args["steps"].as_u64().unwrap_or(20);
                for _ in 0..steps {
                    if ctx.cancellation_token.is_cancelled() {
                        return Err(TaskError::Cancelled);
                    }
                    tokio::time::sleep(Duration::from_millis(5)).await;
                }
                Ok(TaskOutput::success(serde_json::json!({ "completed": true })))
            },
        )
        .unwrap();

    let dispatcher = TaskDispatcher::new(
        registry,
        scheduler,
        runtime,
        telemetry.clone(),
        4,
    );

    let mut handles = Vec::new();
    for i in 0..40 {
        let h = dispatcher
            .dispatch("stoppable_worker", serde_json::json!({ "steps": 50 }), None)
            .unwrap();
        handles.push((i, h));
    }

    // Cancel every even indexed task after a brief jitter
    tokio::time::sleep(Duration::from_millis(15)).await;
    for (i, h) in &handles {
        if i % 2 == 0 {
            h.cancel();
        }
    }

    let mut cancelled_count = 0;
    let mut completed_count = 0;

    for (i, h) in handles {
        match h.wait().await {
            Ok(output) => {
                assert_eq!(output.exit_code, 0);
                completed_count += 1;
            }
            Err(TaskError::Cancelled) => {
                cancelled_count += 1;
                assert_eq!(i % 2, 0, "Only even tasks were targeted for cancellation");
            }
            Err(other) => panic!("Unexpected error: {:?}", other),
        }
    }

    assert!(cancelled_count > 0);
    assert_eq!(cancelled_count + completed_count, 40);
}

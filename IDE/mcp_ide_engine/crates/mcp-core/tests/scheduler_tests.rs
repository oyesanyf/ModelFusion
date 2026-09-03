use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;
use mcp_core::{
    CommandRegistry, EngineRuntime, EngineRuntimeConfig, EngineTelemetry,
    HierarchicalCancellationToken, MultiLaneScheduler, TaskDispatcher, TaskError, TaskOutput,
    TaskPriority, TaskType, EngineTask,
};

#[test]
fn test_hierarchical_cancellation_tree_multi_level() {
    let root = HierarchicalCancellationToken::new_root("root");
    let session = root.child_token_with_name("session-1");
    let pipeline = session.child_token_with_name("pipeline-1");
    let task_a = pipeline.child_token_with_name("task-a");
    let task_b = pipeline.child_token_with_name("task-b");
    let subtask_b1 = task_b.child_token_with_name("subtask-b1");

    assert_eq!(root.tree_depth(), 4);
    assert_eq!(root.active_descendant_count(), 5);

    // Cancel pipeline: should cancel task_a, task_b, subtask_b1
    pipeline.cancel();

    assert!(pipeline.is_cancelled());
    assert!(task_a.is_cancelled());
    assert!(task_b.is_cancelled());
    assert!(subtask_b1.is_cancelled());

    // Root and session must remain active
    assert!(!root.is_cancelled());
    assert!(!session.is_cancelled());
}

#[tokio::test]
async fn test_scheduler_starvation_prevention_age_promotion() {
    let telemetry = Arc::new(EngineTelemetry::new());
    // Configure very short aging threshold for Low priority tasks (50ms)
    let scheduler = MultiLaneScheduler::with_config(
        [16, 8, 4, 2, 1],
        [
            Duration::from_millis(500),
            Duration::from_millis(200),
            Duration::from_millis(100),
            Duration::from_millis(50),  // Low priority threshold
            Duration::from_millis(100),
        ],
        telemetry.clone(),
    );

    let token = HierarchicalCancellationToken::new_root("aging_test");
    let low_task = Arc::new(EngineTask::new(
        "background_sync",
        TaskPriority::Low,
        TaskType::Async,
        token,
        telemetry.new_task_telemetry(),
    ));

    scheduler.submit(low_task.clone()).unwrap();
    assert_eq!(low_task.get_effective_priority(), TaskPriority::Low);

    // Sleep long enough for aging threshold to trigger
    tokio::time::sleep(Duration::from_millis(80)).await;

    // Trigger promotion check
    let promoted = scheduler.promote_aged_tasks();
    assert_eq!(promoted, 1);
    assert_eq!(low_task.get_effective_priority(), TaskPriority::Normal);
}

#[tokio::test]
async fn test_dispatcher_with_error_and_failure_isolation() {
    let telemetry = Arc::new(EngineTelemetry::new());
    let config = EngineRuntimeConfig::new().worker_threads(2).compute_threads(2);
    let runtime = Arc::new(EngineRuntime::new(config).unwrap());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    registry
        .register_fn(
            "failing_cmd",
            "Always fails with an error",
            "test",
            TaskPriority::High,
            |_ctx, _args| async move {
                Err(TaskError::ExecutionFailed("Simulated DB failure".to_string()))
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
        .dispatch("failing_cmd", serde_json::json!({}), None)
        .unwrap();

    let task_id = handle.id();
    let res = handle.wait().await;

    assert!(res.is_err());
    match res.unwrap_err() {
        TaskError::ExecutionFailed(msg) => assert_eq!(msg, "Simulated DB failure"),
        other => panic!("Unexpected error: {:?}", other),
    }

    let record = dispatcher.get_task_record(&task_id).unwrap();
    assert_eq!(record.state, mcp_core::TaskState::Failed);
    assert!(record.error_message.unwrap().contains("Simulated DB failure"));

    let snapshot = telemetry.snapshot();
    assert_eq!(snapshot.failed_tasks_total, 1);
}

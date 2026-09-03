use std::future::Future;
use std::sync::Arc;
use std::time::Duration;
use async_trait::async_trait;
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::sync::oneshot;

use crate::cancellation::HierarchicalCancellationToken;
use crate::runtime::{EngineRuntime, RuntimeError};
use crate::scheduler::{EngineTask, MultiLaneScheduler, SchedulerError, TaskId, TaskState, TaskType};
pub use crate::scheduler::TaskPriority;
use crate::telemetry::{EngineEvent, EngineTelemetry};

/// Errors arising during command registration, validation, or lookup.
#[derive(Debug, Error)]
pub enum RegistryError {
    #[error("Command '{0}' is already registered in registry")]
    CommandAlreadyExists(String),

    #[error("Command '{0}' was not found in registry")]
    CommandNotFound(String),

    #[error("Invalid command schema for '{0}': {1}")]
    InvalidSchema(String, String),
}

/// Errors occurring during command or task execution.
#[derive(Debug, Clone, Error, Serialize, Deserialize)]
pub enum TaskError {
    #[error("Command execution failed: {0}")]
    ExecutionFailed(String),

    #[error("Invalid command arguments: {0}")]
    InvalidArguments(String),

    #[error("Task was cancelled")]
    Cancelled,

    #[error("Task execution timed out after {0:?}")]
    Timeout(Duration),

    #[error("Internal engine error: {0}")]
    Internal(String),
}

/// Errors arising during task dispatch.
#[derive(Debug, Error)]
pub enum DispatchError {
    #[error("Command not found: {0}")]
    CommandNotFound(String),

    #[error("Scheduler submission error: {0}")]
    SchedulerFailed(#[from] SchedulerError),

    #[error("Runtime error: {0}")]
    RuntimeError(#[from] RuntimeError),

    #[error("Task execution failed: {0}")]
    TaskError(#[from] TaskError),
}

/// Descriptive metadata for a registered command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandMetadata {
    pub name: String,
    pub description: String,
    pub category: String,
    pub default_priority: TaskPriority,
    pub parameters_schema: serde_json::Value,
    pub returns_schema: serde_json::Value,
}

/// Standardized output structure returned by all command handlers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskOutput {
    pub data: serde_json::Value,
    pub stdout: Option<String>,
    pub stderr: Option<String>,
    pub exit_code: i32,
    pub is_error: bool,
}

impl TaskOutput {
    /// Creates a successful task output containing JSON data.
    pub fn success(data: serde_json::Value) -> Self {
        Self {
            data,
            stdout: None,
            stderr: None,
            exit_code: 0,
            is_error: false,
        }
    }

    /// Creates an error task output with an error message.
    pub fn error(message: impl Into<String>) -> Self {
        let msg = message.into();
        Self {
            data: serde_json::json!({ "error": msg }),
            stdout: None,
            stderr: Some(msg),
            exit_code: 1,
            is_error: true,
        }
    }

    /// Attaches standard output logs.
    pub fn with_stdout(mut self, stdout: impl Into<String>) -> Self {
        self.stdout = Some(stdout.into());
        self
    }

    /// Attaches standard error logs.
    pub fn with_stderr(mut self, stderr: impl Into<String>) -> Self {
        self.stderr = Some(stderr.into());
        self
    }
}

/// Execution context passed into every invoked command handler.
pub struct TaskExecutionContext {
    pub task_id: TaskId,
    pub command_name: String,
    pub priority: TaskPriority,
    pub cancellation_token: HierarchicalCancellationToken,
    pub telemetry: Arc<EngineTelemetry>,
    pub runtime: Arc<EngineRuntime>,
}

/// Trait implemented by executable command handlers.
#[async_trait]
pub trait CommandHandler: Send + Sync + 'static {
    async fn execute(
        &self,
        ctx: TaskExecutionContext,
        args: serde_json::Value,
    ) -> Result<TaskOutput, TaskError>;
}

/// Helper struct for wrapping async closure functions as CommandHandlers.
pub struct FnCommandHandler<F> {
    f: F,
}

impl<F, Fut> FnCommandHandler<F>
where
    F: Fn(TaskExecutionContext, serde_json::Value) -> Fut + Send + Sync + 'static,
    Fut: Future<Output = Result<TaskOutput, TaskError>> + Send + 'static,
{
    pub fn new(f: F) -> Self {
        Self { f }
    }
}

#[async_trait]
impl<F, Fut> CommandHandler for FnCommandHandler<F>
where
    F: Fn(TaskExecutionContext, serde_json::Value) -> Fut + Send + Sync + 'static,
    Fut: Future<Output = Result<TaskOutput, TaskError>> + Send + 'static,
{
    async fn execute(
        &self,
        ctx: TaskExecutionContext,
        args: serde_json::Value,
    ) -> Result<TaskOutput, TaskError> {
        (self.f)(ctx, args).await
    }
}

/// Complete definition of a registered command including its metadata and executable handler.
#[derive(Clone)]
pub struct CommandDefinition {
    pub metadata: CommandMetadata,
    pub handler: Arc<dyn CommandHandler>,
}

impl std::fmt::Debug for CommandDefinition {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CommandDefinition")
            .field("metadata", &self.metadata)
            .finish()
    }
}

/// Lock-free centralized registry for executable engine commands and MCP tools.
#[derive(Default)]
pub struct CommandRegistry {
    commands: DashMap<String, CommandDefinition>,
}

impl CommandRegistry {
    /// Creates a new empty command registry.
    pub fn new() -> Self {
        Self {
            commands: DashMap::new(),
        }
    }

    /// Registers a full command definition.
    pub fn register(&self, cmd: CommandDefinition) -> Result<(), RegistryError> {
        let name = cmd.metadata.name.clone();
        if self.commands.contains_key(&name) {
            return Err(RegistryError::CommandAlreadyExists(name));
        }
        self.commands.insert(name, cmd);
        Ok(())
    }

    /// Registers an async function handler with basic metadata.
    pub fn register_fn<F, Fut>(
        &self,
        name: impl Into<String>,
        description: impl Into<String>,
        category: impl Into<String>,
        default_priority: TaskPriority,
        handler: F,
    ) -> Result<(), RegistryError>
    where
        F: Fn(TaskExecutionContext, serde_json::Value) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<TaskOutput, TaskError>> + Send + 'static,
    {
        let name_str = name.into();
        let metadata = CommandMetadata {
            name: name_str.clone(),
            description: description.into(),
            category: category.into(),
            default_priority,
            parameters_schema: serde_json::json!({ "type": "object" }),
            returns_schema: serde_json::json!({ "type": "object" }),
        };

        let cmd = CommandDefinition {
            metadata,
            handler: Arc::new(FnCommandHandler::new(handler)),
        };

        self.register(cmd)
    }

    /// Retrieves a registered command by name.
    pub fn get(&self, name: &str) -> Option<CommandDefinition> {
        self.commands.get(name).map(|entry| entry.value().clone())
    }

    /// Checks if a command name is registered.
    pub fn contains(&self, name: &str) -> bool {
        self.commands.contains_key(name)
    }

    /// Returns metadata for all registered commands.
    pub fn list(&self) -> Vec<CommandMetadata> {
        self.commands
            .iter()
            .map(|entry| entry.value().metadata.clone())
            .collect()
    }

    /// Unregisters a command by name.
    pub fn unregister(&self, name: &str) -> Option<CommandDefinition> {
        self.commands.remove(name).map(|(_, v)| v)
    }

    /// Total number of registered commands.
    pub fn len(&self) -> usize {
        self.commands.len()
    }

    /// Checks if registry is empty.
    pub fn is_empty(&self) -> bool {
        self.commands.is_empty()
    }
}

/// Detailed historical or active task record in the state table.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskRecord {
    pub task_id: TaskId,
    pub command_name: String,
    pub priority: TaskPriority,
    pub state: TaskState,
    pub queue_duration_us: Option<u64>,
    pub dispatch_latency_us: Option<u64>,
    pub run_duration_us: Option<u64>,
    pub total_duration_us: Option<u64>,
    pub error_message: Option<String>,
    pub output: Option<TaskOutput>,
}

/// Internal payload struct held in dispatcher state during task execution.
struct DispatchPayload {
    args: serde_json::Value,
    sender: oneshot::Sender<Result<TaskOutput, TaskError>>,
    command: CommandDefinition,
}

/// Handle returned from an asynchronous task dispatch, allowing awaiting the output or cancelling.
pub struct TaskHandle<T> {
    task_id: TaskId,
    receiver: oneshot::Receiver<Result<T, TaskError>>,
    cancellation_token: HierarchicalCancellationToken,
}

impl<T> TaskHandle<T> {
    /// Returns the task identifier.
    pub fn id(&self) -> TaskId {
        self.task_id
    }

    /// Cancels this task.
    pub fn cancel(&self) {
        self.cancellation_token.cancel();
    }

    /// Awaits the task output.
    pub async fn wait(self) -> Result<T, TaskError> {
        if self.cancellation_token.is_cancelled() {
            return Err(TaskError::Cancelled);
        }
        tokio::select! {
            _ = self.cancellation_token.cancelled() => {
                Err(TaskError::Cancelled)
            }
            res = self.receiver => {
                match res {
                    Ok(result) => result,
                    Err(_) => {
                        if self.cancellation_token.is_cancelled() {
                            Err(TaskError::Cancelled)
                        } else {
                            Err(TaskError::Internal("Task sender channel dropped".to_string()))
                        }
                    }
                }
            }
        }
    }
}

/// Core task dispatcher coordinating registry lookup, priority scheduling, runtime execution, and telemetry.
pub struct TaskDispatcher {
    registry: Arc<CommandRegistry>,
    scheduler: Arc<MultiLaneScheduler>,
    runtime: Arc<EngineRuntime>,
    telemetry: Arc<EngineTelemetry>,
    root_token: HierarchicalCancellationToken,
    task_records: Arc<DashMap<TaskId, RwLock<TaskRecord>>>,
    payload_map: Arc<DashMap<TaskId, DispatchPayload>>,
}

impl TaskDispatcher {
    /// Initializes a new TaskDispatcher and starts background worker dispatcher loops.
    pub fn new(
        registry: Arc<CommandRegistry>,
        scheduler: Arc<MultiLaneScheduler>,
        runtime: Arc<EngineRuntime>,
        telemetry: Arc<EngineTelemetry>,
        worker_count: usize,
    ) -> Arc<Self> {
        let root_token = HierarchicalCancellationToken::new_root("dispatcher_root");
        let task_records = Arc::new(DashMap::new());
        let payload_map = Arc::new(DashMap::new());

        let dispatcher = Arc::new(Self {
            registry,
            scheduler,
            runtime,
            telemetry,
            root_token,
            task_records,
            payload_map,
        });

        // Launch background worker loops
        let worker_count = worker_count.max(2);
        for worker_id in 0..worker_count {
            let d = dispatcher.clone();
            dispatcher.runtime.spawn(async move {
                d.worker_loop(worker_id).await;
            });
        }

        dispatcher
    }

    /// Asynchronously dispatches a command through the priority scheduler.
    pub fn dispatch(
        &self,
        command_name: &str,
        args: serde_json::Value,
        priority_override: Option<TaskPriority>,
    ) -> Result<TaskHandle<TaskOutput>, DispatchError> {
        let cmd = self
            .registry
            .get(command_name)
            .ok_or_else(|| DispatchError::CommandNotFound(command_name.to_string()))?;

        let priority = priority_override.unwrap_or(cmd.metadata.default_priority);
        let task_token = self
            .root_token
            .child_token_with_name(format!("task_{}", command_name));

        let task_telem = self.telemetry.new_task_telemetry();
        let engine_task = Arc::new(EngineTask::new(
            command_name,
            priority,
            TaskType::Command,
            task_token.clone(),
            task_telem,
        ));

        let (tx, rx) = oneshot::channel();
        let task_id = engine_task.id;

        // Initialize record
        let record = TaskRecord {
            task_id,
            command_name: command_name.to_string(),
            priority,
            state: TaskState::Queued,
            queue_duration_us: None,
            dispatch_latency_us: None,
            run_duration_us: None,
            total_duration_us: None,
            error_message: None,
            output: None,
        };
        self.task_records.insert(task_id, RwLock::new(record));

        // Package task context with args and sender in dispatcher map
        let payload = DispatchPayload {
            args,
            sender: tx,
            command: cmd,
        };
        self.payload_map.insert(task_id, payload);

        self.scheduler.submit(engine_task)?;
        self.telemetry.total_dispatched.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        // Publish event
        self.telemetry.event_bus.publish(EngineEvent::TaskQueued {
            task_id: task_id.0,
            name: command_name.to_string(),
            priority: priority as u8,
            timestamp_ms: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
        });

        Ok(TaskHandle {
            task_id,
            receiver: rx,
            cancellation_token: task_token,
        })
    }

    /// Synchronously executes a command directly (useful for CLI execution).
    pub async fn dispatch_sync(
        &self,
        command_name: &str,
        args: serde_json::Value,
    ) -> Result<TaskOutput, DispatchError> {
        let handle = self.dispatch(command_name, args, None)?;
        handle.wait().await.map_err(DispatchError::TaskError)
    }

    /// Worker execution loop dequeuing tasks from scheduler and executing command handlers.
    async fn worker_loop(&self, _worker_id: usize) {
        let notifier = self.scheduler.notifier();

        loop {
            if self.root_token.is_cancelled() {
                break;
            }

            // Dequeue next task
            if let Some(task) = self.scheduler.next_task() {
                let task_id = task.id;

                if let Some((_, payload)) = self.payload_map.remove(&task_id) {
                    let d = self;

                    // If task was cancelled while queued, complete immediately with Cancelled
                    if task.is_cancelled() {
                        task.set_state(TaskState::Cancelled);
                        let telem_guard = task.telemetry.read();
                        d.telemetry.record_task_cancellation(&telem_guard);
                        if let Some(rec) = d.task_records.get(&task_id) {
                            let mut r = rec.write();
                            r.state = TaskState::Cancelled;
                        }
                        d.telemetry.event_bus.publish(EngineEvent::TaskCancelled {
                            task_id: task_id.0,
                            stage: "queued".to_string(),
                        });
                        d.telemetry.active_tasks.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
                        let _ = payload.sender.send(Err(TaskError::Cancelled));
                        continue;
                    }

                    // Mark scheduled & started
                    {
                        let mut telem = task.telemetry.write();
                        telem.mark_scheduled();
                        telem.mark_started();
                    }
                    task.set_state(TaskState::Running);

                    // Update record state
                    if let Some(rec) = d.task_records.get(&task_id) {
                        let mut r = rec.write();
                        r.state = TaskState::Running;
                        if let Some(q) = task.telemetry.read().queue_duration() {
                            r.queue_duration_us = Some(q.as_micros() as u64);
                        }
                    }

                    // Build context
                    let ctx = TaskExecutionContext {
                        task_id,
                        command_name: task.name.clone(),
                        priority: task.priority,
                        cancellation_token: task.cancellation_token.clone(),
                        telemetry: d.telemetry.clone(),
                        runtime: d.runtime.clone(),
                    };

                    let token = task.cancellation_token.clone();
                    let handler = payload.command.handler.clone();
                    let args = payload.args;
                    let tx = payload.sender;

                    // Execute with cooperative cancellation
                    let exec_fut = async move {
                        tokio::select! {
                            _ = token.cancelled() => {
                                Err(TaskError::Cancelled)
                            }
                            res = handler.execute(ctx, args) => {
                                res
                            }
                        }
                    };

                    let result = exec_fut.await;
                    {
                        let mut telem = task.telemetry.write();
                        telem.mark_completed();
                    }

                    // Record metrics & update state
                    let telem_guard = task.telemetry.read();
                    match &result {
                        Ok(output) => {
                            task.set_state(TaskState::Completed);
                            d.telemetry.record_task_completion(&telem_guard);

                            if let Some(rec) = d.task_records.get(&task_id) {
                                let mut r = rec.write();
                                r.state = TaskState::Completed;
                                r.run_duration_us = telem_guard.run_duration().map(|d| d.as_micros() as u64);
                                r.total_duration_us = telem_guard.total_duration().map(|d| d.as_micros() as u64);
                                r.output = Some(output.clone());
                            }

                            d.telemetry.event_bus.publish(EngineEvent::TaskCompleted {
                                task_id: task_id.0,
                                run_duration_us: telem_guard.run_duration().map(|d| d.as_micros() as u64).unwrap_or(0),
                                total_duration_us: telem_guard.total_duration().map(|d| d.as_micros() as u64).unwrap_or(0),
                            });
                        }
                        Err(TaskError::Cancelled) => {
                            task.set_state(TaskState::Cancelled);
                            d.telemetry.record_task_cancellation(&telem_guard);

                            if let Some(rec) = d.task_records.get(&task_id) {
                                let mut r = rec.write();
                                r.state = TaskState::Cancelled;
                            }

                            d.telemetry.event_bus.publish(EngineEvent::TaskCancelled {
                                task_id: task_id.0,
                                stage: "execution".to_string(),
                            });
                        }
                        Err(err) => {
                            task.set_state(TaskState::Failed);
                            d.telemetry.record_task_failure(&telem_guard);

                            if let Some(rec) = d.task_records.get(&task_id) {
                                let mut r = rec.write();
                                r.state = TaskState::Failed;
                                r.error_message = Some(err.to_string());
                            }

                            d.telemetry.event_bus.publish(EngineEvent::TaskFailed {
                                task_id: task_id.0,
                                error: err.to_string(),
                                run_duration_us: telem_guard.run_duration().map(|d| d.as_micros() as u64).unwrap_or(0),
                            });
                        }
                    }

                    d.telemetry.active_tasks.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
                    let _ = tx.send(result);
                }
            } else {
                // Wait for new task submission or cancellation
                tokio::select! {
                    _ = notifier.notified() => {}
                    _ = self.root_token.cancelled() => {
                        break;
                    }
                }
            }
        }
    }

    /// Queries a task record by TaskId.
    pub fn get_task_record(&self, task_id: &TaskId) -> Option<TaskRecord> {
        self.task_records.get(task_id).map(|r| r.read().clone())
    }

    /// Returns a list of all task records.
    pub fn list_task_records(&self) -> Vec<TaskRecord> {
        self.task_records.iter().map(|r| r.value().read().clone()).collect()
    }

    /// Cancels a running or queued task.
    pub fn cancel_task(&self, task_id: &TaskId) -> Result<bool, SchedulerError> {
        self.scheduler.cancel(task_id)
    }

    /// Returns the command registry reference.
    pub fn registry(&self) -> &Arc<CommandRegistry> {
        &self.registry
    }

    /// Returns the telemetry reference.
    pub fn telemetry(&self) -> &Arc<EngineTelemetry> {
        &self.telemetry
    }

    /// Returns the root cancellation token for global engine shutdown.
    pub fn root_token(&self) -> &HierarchicalCancellationToken {
        &self.root_token
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::EngineRuntimeConfig;

    #[tokio::test]
    async fn test_command_registration_and_execution() {
        let registry = Arc::new(CommandRegistry::new());
        registry
            .register_fn(
                "echo",
                "Echoes input text",
                "core",
                TaskPriority::High,
                |_ctx, args| async move {
                    let msg = args.get("message").and_then(|v| v.as_str()).unwrap_or("");
                    Ok(TaskOutput::success(serde_json::json!({ "echoed": msg })))
                },
            )
            .unwrap();

        assert_eq!(registry.len(), 1);
        assert!(registry.contains("echo"));

        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let config = EngineRuntimeConfig::new().worker_threads(2).compute_threads(2);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());

        let dispatcher = TaskDispatcher::new(
            registry,
            scheduler,
            runtime,
            telemetry,
            2,
        );

        let output = dispatcher
            .dispatch_sync("echo", serde_json::json!({ "message": "hello world" }))
            .await
            .unwrap();

        assert_eq!(output.exit_code, 0);
        assert_eq!(output.data["echoed"], "hello world");
    }

    #[tokio::test]
    async fn test_concurrent_task_dispatch_load() {
        let registry = Arc::new(CommandRegistry::new());
        registry
            .register_fn(
                "add",
                "Adds numbers",
                "math",
                TaskPriority::Normal,
                |_ctx, args| async move {
                    let a = args["a"].as_i64().unwrap_or(0);
                    let b = args["b"].as_i64().unwrap_or(0);
                    Ok(TaskOutput::success(serde_json::json!({ "sum": a + b })))
                },
            )
            .unwrap();

        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
        let config = EngineRuntimeConfig::new().worker_threads(4).compute_threads(2);
        let runtime = Arc::new(EngineRuntime::new(config).unwrap());

        let dispatcher = TaskDispatcher::new(
            registry,
            scheduler,
            runtime,
            telemetry.clone(),
            4,
        );

        let mut handles = Vec::new();
        for i in 0..50 {
            let handle = dispatcher
                .dispatch(
                    "add",
                    serde_json::json!({ "a": i, "b": i * 2 }),
                    Some(TaskPriority::Normal),
                )
                .unwrap();
            handles.push((i, handle));
        }

        for (i, handle) in handles {
            let res = handle.wait().await.unwrap();
            let sum = res.data["sum"].as_i64().unwrap();
            assert_eq!(sum, i + i * 2);
        }

        assert_eq!(telemetry.completed_tasks_total.load(std::sync::atomic::Ordering::Relaxed), 50);
    }
}

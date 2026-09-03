use std::sync::atomic::{AtomicU32, AtomicU8, Ordering};
use std::sync::Arc;
use std::time::Duration;
use crossbeam_queue::SegQueue;
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::sync::Notify;
use uuid::Uuid;

use crate::cancellation::HierarchicalCancellationToken;
use crate::telemetry::{EngineTelemetry, TaskTelemetry};

/// Errors arising during task scheduling or priority queue operations.
#[derive(Debug, Error)]
pub enum SchedulerError {
    #[error("Task not found: {0}")]
    TaskNotFound(TaskId),

    #[error("Scheduler queue full")]
    QueueFull,

    #[error("Scheduler has been shut down")]
    SchedulerShutdown,

    #[error("Invalid task state transition from {from:?} to {to:?}")]
    InvalidStateTransition { from: TaskState, to: TaskState },
}

/// 5-Level priority classification for engine tasks.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum TaskPriority {
    Critical = 0,   // System emergencies, heartbeats, kill signals, watchdog alerts
    High = 1,       // Foreground interactive CLI actions, UI requests, direct MCP tool calls
    Normal = 2,     // Standard agent workflow pipelines, multi-step tasks
    Low = 3,        // Background AST re-indexing, cache warmups, batch file validations
    Background = 4, // Deep telemetry sweeps, log flushes, repository archives
}

impl TaskPriority {
    /// Array of all 5 priority levels in descending order of urgency.
    pub const ALL: [TaskPriority; 5] = [
        TaskPriority::Critical,
        TaskPriority::High,
        TaskPriority::Normal,
        TaskPriority::Low,
        TaskPriority::Background,
    ];

    /// Returns the numerical lane index (0 to 4).
    pub fn index(self) -> usize {
        self as usize
    }

    /// Converts a u8 integer to TaskPriority.
    pub fn from_u8(val: u8) -> Self {
        match val {
            0 => TaskPriority::Critical,
            1 => TaskPriority::High,
            2 => TaskPriority::Normal,
            3 => TaskPriority::Low,
            _ => TaskPriority::Background,
        }
    }

    /// Returns the promoted (higher urgency) priority level.
    pub fn promote(self) -> Self {
        match self {
            TaskPriority::Critical => TaskPriority::Critical,
            TaskPriority::High => TaskPriority::Critical,
            TaskPriority::Normal => TaskPriority::High,
            TaskPriority::Low => TaskPriority::Normal,
            TaskPriority::Background => TaskPriority::Low,
        }
    }

    /// Human-readable name of the priority level.
    pub fn name(self) -> &'static str {
        match self {
            TaskPriority::Critical => "Critical",
            TaskPriority::High => "High",
            TaskPriority::Normal => "Normal",
            TaskPriority::Low => "Low",
            TaskPriority::Background => "Background",
        }
    }
}

impl std::fmt::Display for TaskPriority {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name())
    }
}

/// Unique identifier for a task, backed by a UUID v7 (time-ordered).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TaskId(pub Uuid);

impl TaskId {
    /// Generates a new time-ordered UUID v7 task ID.
    pub fn new() -> Self {
        Self(Uuid::now_v7())
    }
}

impl Default for TaskId {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Display for TaskId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Lifecycle state machine for engine tasks.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum TaskState {
    Queued = 0,
    Scheduled = 1,
    Running = 2,
    Completed = 3,
    Failed = 4,
    Cancelled = 5,
    TimedOut = 6,
}

impl TaskState {
    pub fn from_u8(val: u8) -> Self {
        match val {
            0 => TaskState::Queued,
            1 => TaskState::Scheduled,
            2 => TaskState::Running,
            3 => TaskState::Completed,
            4 => TaskState::Failed,
            5 => TaskState::Cancelled,
            6 => TaskState::TimedOut,
            _ => TaskState::Failed,
        }
    }

    pub fn is_terminal(self) -> bool {
        matches!(
            self,
            TaskState::Completed | TaskState::Failed | TaskState::Cancelled | TaskState::TimedOut
        )
    }

    pub fn as_str(self) -> &'static str {
        match self {
            TaskState::Queued => "Queued",
            TaskState::Scheduled => "Scheduled",
            TaskState::Running => "Running",
            TaskState::Completed => "Completed",
            TaskState::Failed => "Failed",
            TaskState::Cancelled => "Cancelled",
            TaskState::TimedOut => "TimedOut",
        }
    }
}

impl std::fmt::Display for TaskState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// Nature of the task workload.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskType {
    Async,
    Compute,
    Blocking,
    Command,
}

/// Internal representation of an executable task in the engine.
pub struct EngineTask {
    pub id: TaskId,
    pub name: String,
    pub description: String,
    pub priority: TaskPriority,
    pub effective_priority: AtomicU8,
    pub state: AtomicU8,
    pub task_type: TaskType,
    pub cancellation_token: HierarchicalCancellationToken,
    pub telemetry: RwLock<TaskTelemetry>,
    pub metadata: serde_json::Value,
}

impl EngineTask {
    /// Creates a new EngineTask with the given parameters and telemetry tracker.
    pub fn new(
        name: impl Into<String>,
        priority: TaskPriority,
        task_type: TaskType,
        cancellation_token: HierarchicalCancellationToken,
        telemetry: TaskTelemetry,
    ) -> Self {
        let id = TaskId::new();
        Self {
            id,
            name: name.into(),
            description: String::new(),
            priority,
            effective_priority: AtomicU8::new(priority as u8),
            state: AtomicU8::new(TaskState::Queued as u8),
            task_type,
            cancellation_token,
            telemetry: RwLock::new(telemetry),
            metadata: serde_json::Value::Null,
        }
    }

    /// Sets the task state atomically.
    pub fn set_state(&self, new_state: TaskState) {
        self.state.store(new_state as u8, Ordering::Release);
    }

    /// Reads the current task state.
    pub fn get_state(&self) -> TaskState {
        TaskState::from_u8(self.state.load(Ordering::Acquire))
    }

    /// Returns the currently effective priority level (after potential age-boosting).
    pub fn get_effective_priority(&self) -> TaskPriority {
        TaskPriority::from_u8(self.effective_priority.load(Ordering::Acquire))
    }

    /// Boosts effective priority by one level.
    pub fn promote_priority(&self) -> TaskPriority {
        let current = self.get_effective_priority();
        let promoted = current.promote();
        self.effective_priority.store(promoted as u8, Ordering::Release);
        promoted
    }

    /// Checks if this task has been cancelled.
    pub fn is_cancelled(&self) -> bool {
        self.cancellation_token.is_cancelled()
            || self.get_state() == TaskState::Cancelled
    }
}

/// Filter criteria for querying task lists.
#[derive(Debug, Clone, Default)]
pub struct TaskFilter {
    pub state: Option<TaskState>,
    pub priority: Option<TaskPriority>,
    pub name_contains: Option<String>,
    pub limit: Option<usize>,
}

/// Multi-lane priority scheduler with lock-free SegQueue lanes, weighted round-robin, and starvation prevention.
pub struct MultiLaneScheduler {
    lanes: [SegQueue<Arc<EngineTask>>; 5],
    active_tasks: Arc<DashMap<TaskId, Arc<EngineTask>>>,
    notify: Arc<Notify>,
    weights: [u32; 5],
    consumed_in_round: [AtomicU32; 5],
    telemetry: Arc<EngineTelemetry>,
    age_thresholds: [Duration; 5],
}

impl MultiLaneScheduler {
    /// Creates a new MultiLaneScheduler with default weights [16, 8, 4, 2, 1] and aging thresholds.
    pub fn new(telemetry: Arc<EngineTelemetry>) -> Self {
        Self::with_config(
            [16, 8, 4, 2, 1],
            [
                Duration::from_millis(500),  // Critical
                Duration::from_secs(2),      // High
                Duration::from_secs(5),      // Normal
                Duration::from_secs(15),     // Low
                Duration::from_secs(30),     // Background
            ],
            telemetry,
        )
    }

    /// Creates a MultiLaneScheduler with custom weights and starvation age thresholds.
    pub fn with_config(
        weights: [u32; 5],
        age_thresholds: [Duration; 5],
        telemetry: Arc<EngineTelemetry>,
    ) -> Self {
        Self {
            lanes: [
                SegQueue::new(),
                SegQueue::new(),
                SegQueue::new(),
                SegQueue::new(),
                SegQueue::new(),
            ],
            active_tasks: Arc::new(DashMap::new()),
            notify: Arc::new(Notify::new()),
            weights,
            consumed_in_round: [
                AtomicU32::new(0),
                AtomicU32::new(0),
                AtomicU32::new(0),
                AtomicU32::new(0),
                AtomicU32::new(0),
            ],
            telemetry,
            age_thresholds,
        }
    }

    /// Submits a task to the priority scheduler.
    pub fn submit(&self, task: Arc<EngineTask>) -> Result<TaskId, SchedulerError> {
        let task_id = task.id;
        let prio = task.get_effective_priority().index();

        task.set_state(TaskState::Queued);
        self.active_tasks.insert(task_id, task.clone());
        self.lanes[prio].push(task);

        // Update telemetry gauge
        self.telemetry.queued_tasks_by_priority[prio].fetch_add(1, Ordering::Relaxed);
        self.telemetry.active_tasks.fetch_add(1, Ordering::Relaxed);

        // Notify waiting worker loops
        self.notify.notify_one();

        Ok(task_id)
    }

    /// Dequeues the next task according to weighted round-robin scheduling and starvation prevention.
    pub fn next_task(&self) -> Option<Arc<EngineTask>> {
        // Starvation prevention: promote long-waiting tasks first
        self.promote_aged_tasks();

        // 1. Try to find a lane that has tasks and has not exceeded its round quota
        for lane_idx in 0..5 {
            let quota = self.weights[lane_idx];

            while self.consumed_in_round[lane_idx].load(Ordering::Acquire) < quota {
                if let Some(task) = self.lanes[lane_idx].pop() {
                    self.telemetry.queued_tasks_by_priority[lane_idx].fetch_sub(1, Ordering::Relaxed);

                    // Check if task was cancelled while in queue
                    if task.is_cancelled() {
                        task.set_state(TaskState::Cancelled);
                        self.telemetry.record_task_cancellation(&task.telemetry.read());
                        self.telemetry.active_tasks.fetch_sub(1, Ordering::Relaxed);
                        continue;
                    }

                    self.consumed_in_round[lane_idx].fetch_add(1, Ordering::Release);
                    return Some(task);
                } else {
                    break;
                }
            }
        }

        // 2. If all lanes have exhausted their quotas for the current round, reset counters and retry
        self.reset_round_quotas();

        for lane_idx in 0..5 {
            let quota = self.weights[lane_idx];

            while self.consumed_in_round[lane_idx].load(Ordering::Acquire) < quota {
                if let Some(task) = self.lanes[lane_idx].pop() {
                    self.telemetry.queued_tasks_by_priority[lane_idx].fetch_sub(1, Ordering::Relaxed);

                    if task.is_cancelled() {
                        task.set_state(TaskState::Cancelled);
                        self.telemetry.record_task_cancellation(&task.telemetry.read());
                        self.telemetry.active_tasks.fetch_sub(1, Ordering::Relaxed);
                        continue;
                    }

                    self.consumed_in_round[lane_idx].fetch_add(1, Ordering::Release);
                    return Some(task);
                } else {
                    break;
                }
            }
        }

        None
    }

    /// Promotes aged tasks that have waited longer than their priority threshold.
    pub fn promote_aged_tasks(&self) -> usize {
        let mut promoted_count = 0;
        let clock = &self.telemetry.clock;
        let now = clock.now();

        // Check lanes 1..4 (Normal, Low, Background) for tasks waiting too long
        for lane_idx in (1..5).rev() {
            let threshold = self.age_thresholds[lane_idx];
            let mut temp_tasks = Vec::new();

            while let Some(task) = self.lanes[lane_idx].pop() {
                let wait_time = {
                    let telem = task.telemetry.read();
                    if now >= telem.created_at {
                        now.duration_since(telem.created_at)
                    } else {
                        Duration::ZERO
                    }
                };

                if wait_time >= threshold && !task.is_cancelled() {
                    // Promote to higher priority lane
                    let new_prio = task.promote_priority();
                    self.lanes[new_prio.index()].push(task);
                    self.telemetry.queued_tasks_by_priority[lane_idx].fetch_sub(1, Ordering::Relaxed);
                    self.telemetry.queued_tasks_by_priority[new_prio.index()].fetch_add(1, Ordering::Relaxed);
                    promoted_count += 1;
                } else {
                    temp_tasks.push(task);
                }
            }

            // Restore non-promoted tasks back to the lane
            for task in temp_tasks {
                self.lanes[lane_idx].push(task);
            }
        }

        promoted_count
    }

    /// Resets WRR round quotas across all 5 priority lanes.
    fn reset_round_quotas(&self) {
        for counter in &self.consumed_in_round {
            counter.store(0, Ordering::Release);
        }
    }

    /// Cancels an active or queued task by its TaskId.
    pub fn cancel(&self, task_id: &TaskId) -> Result<bool, SchedulerError> {
        if let Some(task) = self.active_tasks.get(task_id) {
            task.cancellation_token.cancel();
            task.set_state(TaskState::Cancelled);
            Ok(true)
        } else {
            Err(SchedulerError::TaskNotFound(*task_id))
        }
    }

    /// Retrieves an Arc reference to a task by ID.
    pub fn get_task(&self, task_id: &TaskId) -> Option<Arc<EngineTask>> {
        self.active_tasks.get(task_id).map(|entry| entry.value().clone())
    }

    /// Lists active tasks matching optional filter criteria.
    pub fn list_tasks(&self, filter: Option<TaskFilter>) -> Vec<Arc<EngineTask>> {
        let filter = filter.unwrap_or_default();
        let mut results = Vec::new();

        for entry in self.active_tasks.iter() {
            let task = entry.value();

            if let Some(state) = filter.state {
                if task.get_state() != state {
                    continue;
                }
            }

            if let Some(priority) = filter.priority {
                if task.priority != priority {
                    continue;
                }
            }

            if let Some(ref name_sub) = filter.name_contains {
                if !task.name.contains(name_sub) {
                    continue;
                }
            }

            results.push(task.clone());

            if let Some(limit) = filter.limit {
                if results.len() >= limit {
                    break;
                }
            }
        }

        results
    }

    /// Returns the number of tasks in each priority queue lane.
    pub fn queue_depth(&self) -> [usize; 5] {
        [
            self.lanes[0].len(),
            self.lanes[1].len(),
            self.lanes[2].len(),
            self.lanes[3].len(),
            self.lanes[4].len(),
        ]
    }

    /// Returns the total number of queued tasks across all lanes.
    pub fn total_queued(&self) -> usize {
        self.lanes.iter().map(|l| l.len()).sum()
    }

    /// Returns the total count of tracked active tasks in the registry.
    pub fn active_count(&self) -> usize {
        self.active_tasks.len()
    }

    /// Returns the notifier for waiting dispatchers.
    pub fn notifier(&self) -> Arc<Notify> {
        self.notify.clone()
    }

    /// Prunes terminal tasks (completed/failed/cancelled) exceeding the specified retention limit.
    pub fn prune_terminal_tasks(&self, max_retained: usize) -> usize {
        let mut terminal_ids = Vec::new();

        for entry in self.active_tasks.iter() {
            if entry.value().get_state().is_terminal() {
                terminal_ids.push(*entry.key());
            }
        }

        if terminal_ids.len() > max_retained {
            let to_remove = terminal_ids.len() - max_retained;
            for id in terminal_ids.iter().take(to_remove) {
                self.active_tasks.remove(id);
            }
            to_remove
        } else {
            0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cancellation::HierarchicalCancellationToken;

    fn make_task(name: &str, prio: TaskPriority, telem: &EngineTelemetry) -> Arc<EngineTask> {
        let token = HierarchicalCancellationToken::new_root(name);
        let task_telem = telem.new_task_telemetry();
        Arc::new(EngineTask::new(
            name,
            prio,
            TaskType::Async,
            token,
            task_telem,
        ))
    }

    #[test]
    fn test_priority_ordering_dequeue() {
        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = MultiLaneScheduler::new(telemetry.clone());

        let low = make_task("low", TaskPriority::Low, &telemetry);
        let high = make_task("high", TaskPriority::High, &telemetry);
        let crit = make_task("crit", TaskPriority::Critical, &telemetry);

        scheduler.submit(low).unwrap();
        scheduler.submit(high).unwrap();
        scheduler.submit(crit).unwrap();

        let t1 = scheduler.next_task().unwrap();
        let t2 = scheduler.next_task().unwrap();
        let t3 = scheduler.next_task().unwrap();

        assert_eq!(t1.name, "crit");
        assert_eq!(t2.name, "high");
        assert_eq!(t3.name, "low");
        assert!(scheduler.next_task().is_none());
    }

    #[test]
    fn test_weighted_round_robin_starvation_prevention() {
        let telemetry = Arc::new(EngineTelemetry::new());
        // Set small weights: 2 Critical, 1 Low
        let scheduler = MultiLaneScheduler::with_config(
            [2, 2, 2, 2, 1],
            [
                Duration::from_secs(10),
                Duration::from_secs(10),
                Duration::from_secs(10),
                Duration::from_secs(10),
                Duration::from_secs(10),
            ],
            telemetry.clone(),
        );

        // Submit 5 Critical and 2 Low
        for i in 0..5 {
            scheduler
                .submit(make_task(&format!("crit_{}", i), TaskPriority::Critical, &telemetry))
                .unwrap();
        }
        for i in 0..2 {
            scheduler
                .submit(make_task(&format!("low_{}", i), TaskPriority::Low, &telemetry))
                .unwrap();
        }

        // In round 1: 2 Critical tasks should be drained, then 1 Low task
        let t1 = scheduler.next_task().unwrap();
        let t2 = scheduler.next_task().unwrap();
        let t3 = scheduler.next_task().unwrap();

        assert_eq!(t1.priority, TaskPriority::Critical);
        assert_eq!(t2.priority, TaskPriority::Critical);
        assert_eq!(t3.priority, TaskPriority::Low);
    }

    #[test]
    fn test_in_queue_cancellation() {
        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = MultiLaneScheduler::new(telemetry.clone());

        let task1 = make_task("task1", TaskPriority::Normal, &telemetry);
        let task2 = make_task("task2", TaskPriority::Normal, &telemetry);

        scheduler.submit(task1.clone()).unwrap();
        scheduler.submit(task2.clone()).unwrap();

        // Cancel task1 before dequeue
        scheduler.cancel(&task1.id).unwrap();

        // next_task should skip task1 and return task2
        let picked = scheduler.next_task().unwrap();
        assert_eq!(picked.name, "task2");
        assert!(scheduler.next_task().is_none());
    }

    #[test]
    fn test_task_filtering() {
        let telemetry = Arc::new(EngineTelemetry::new());
        let scheduler = MultiLaneScheduler::new(telemetry.clone());

        let t1 = make_task("alpha_build", TaskPriority::High, &telemetry);
        let t2 = make_task("beta_test", TaskPriority::Low, &telemetry);
        let t3 = make_task("alpha_lint", TaskPriority::Normal, &telemetry);

        scheduler.submit(t1).unwrap();
        scheduler.submit(t2).unwrap();
        scheduler.submit(t3).unwrap();

        let filtered = scheduler.list_tasks(Some(TaskFilter {
            name_contains: Some("alpha".to_string()),
            ..Default::default()
        }));

        assert_eq!(filtered.len(), 2);
    }
}

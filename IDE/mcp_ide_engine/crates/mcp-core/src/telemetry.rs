use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;
use hdrhistogram::Histogram;
use parking_lot::RwLock;
use quanta::{Clock, Instant};
use serde::{Deserialize, Serialize};
use tokio::sync::broadcast;
use uuid::Uuid;

/// High-resolution task lifecycle latency measurement.
#[derive(Debug, Clone)]
pub struct TaskTelemetry {
    clock: Clock,
    pub created_at: Instant,
    pub scheduled_at: Option<Instant>,
    pub started_at: Option<Instant>,
    pub completed_at: Option<Instant>,
}

impl TaskTelemetry {
    /// Creates a new telemetry tracker with the current instant.
    pub fn new(clock: Clock) -> Self {
        let created_at = clock.now();
        Self {
            clock,
            created_at,
            scheduled_at: None,
            started_at: None,
            completed_at: None,
        }
    }

    /// Marks the instant when the task was scheduled for execution.
    pub fn mark_scheduled(&mut self) {
        self.scheduled_at = Some(self.clock.now());
    }

    /// Marks the instant when the task execution actually started on a worker thread.
    pub fn mark_started(&mut self) {
        self.started_at = Some(self.clock.now());
    }

    /// Marks the instant when the task completed, failed, or was cancelled.
    pub fn mark_completed(&mut self) {
        self.completed_at = Some(self.clock.now());
    }

    /// Time spent waiting in the scheduling queue before being picked up.
    pub fn queue_duration(&self) -> Option<Duration> {
        let end = self.scheduled_at.or(self.started_at)?;
        if end >= self.created_at {
            Some(end.duration_since(self.created_at))
        } else {
            Some(Duration::ZERO)
        }
    }

    /// Latency between schedule decision and worker execution start.
    pub fn dispatch_latency(&self) -> Option<Duration> {
        let scheduled = self.scheduled_at?;
        let started = self.started_at?;
        if started >= scheduled {
            Some(started.duration_since(scheduled))
        } else {
            Some(Duration::ZERO)
        }
    }

    /// Active execution duration on a worker thread.
    pub fn run_duration(&self) -> Option<Duration> {
        let started = self.started_at?;
        let completed = self.completed_at?;
        if completed >= started {
            Some(completed.duration_since(started))
        } else {
            Some(Duration::ZERO)
        }
    }

    /// Total turnaround time from submission to completion.
    pub fn total_duration(&self) -> Option<Duration> {
        let completed = self.completed_at?;
        if completed >= self.created_at {
            Some(completed.duration_since(self.created_at))
        } else {
            Some(Duration::ZERO)
        }
    }
}

/// Thread-safe statistical latency tracker backed by HDRHistogram.
pub struct LatencyHistogram {
    histogram: RwLock<Histogram<u64>>,
}

impl LatencyHistogram {
    /// Creates a new histogram configured for microsecond measurements (1 us to 1 hour).
    pub fn new() -> Self {
        // Range 1 to 3,600,000,000 microseconds (1 hour), 3 significant figures
        let hist = Histogram::<u64>::new_with_bounds(1, 3_600_000_000, 3)
            .unwrap_or_else(|_| Histogram::<u64>::new(3).unwrap());
        Self {
            histogram: RwLock::new(hist),
        }
    }

    /// Records a duration in microseconds.
    pub fn record(&self, duration: Duration) {
        let us = duration.as_micros().max(1) as u64;
        let mut hist = self.histogram.write();
        let _ = hist.record(us);
    }

    /// Computes summary percentiles in microseconds.
    pub fn summary(&self) -> LatencySummary {
        let hist = self.histogram.read();
        if hist.is_empty() {
            return LatencySummary::default();
        }
        LatencySummary {
            count: hist.len(),
            min_us: hist.min(),
            p50_us: hist.value_at_percentile(50.0),
            p90_us: hist.value_at_percentile(90.0),
            p95_us: hist.value_at_percentile(95.0),
            p99_us: hist.value_at_percentile(99.0),
            max_us: hist.max(),
            mean_us: hist.mean(),
        }
    }

    /// Resets the histogram data.
    pub fn reset(&self) {
        let mut hist = self.histogram.write();
        hist.reset();
    }
}

impl Default for LatencyHistogram {
    fn default() -> Self {
        Self::new()
    }
}

/// Latency percentile statistics in microseconds.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize, Default)]
pub struct LatencySummary {
    pub count: u64,
    pub min_us: u64,
    pub p50_us: u64,
    pub p90_us: u64,
    pub p95_us: u64,
    pub p99_us: u64,
    pub max_us: u64,
    pub mean_us: f64,
}

/// Real-time engine event emitted during task lifecycle and system operations.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum EngineEvent {
    TaskQueued {
        task_id: Uuid,
        name: String,
        priority: u8,
        timestamp_ms: u64,
    },
    TaskScheduled {
        task_id: Uuid,
        queue_duration_us: u64,
    },
    TaskStarted {
        task_id: Uuid,
        dispatch_latency_us: u64,
    },
    TaskCompleted {
        task_id: Uuid,
        run_duration_us: u64,
        total_duration_us: u64,
    },
    TaskFailed {
        task_id: Uuid,
        error: String,
        run_duration_us: u64,
    },
    TaskCancelled {
        task_id: Uuid,
        stage: String,
    },
    TaskTimedOut {
        task_id: Uuid,
        duration_us: u64,
    },
    SystemAlert {
        level: String,
        message: String,
    },
    Custom {
        topic: String,
        data: serde_json::Value,
    },
}

/// Broadcast event bus for real-time engine telemetry and notifications.
pub struct EventBus {
    sender: broadcast::Sender<EngineEvent>,
}

impl EventBus {
    /// Creates a new EventBus with the specified channel capacity.
    pub fn new(capacity: usize) -> Self {
        let (sender, _) = broadcast::channel(capacity.max(64));
        Self { sender }
    }

    /// Subscribes to engine events.
    pub fn subscribe(&self) -> broadcast::Receiver<EngineEvent> {
        self.sender.subscribe()
    }

    /// Publishes an event to all active subscribers. Returns subscriber count.
    pub fn publish(&self, event: EngineEvent) -> usize {
        self.sender.send(event).unwrap_or(0)
    }

    /// Returns the number of active subscribers.
    pub fn subscriber_count(&self) -> usize {
        self.sender.receiver_count()
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new(10_000)
    }
}

/// Centralized engine telemetry aggregator tracking counters, latencies, and events.
pub struct EngineTelemetry {
    pub clock: Clock,
    pub active_tasks: AtomicUsize,
    pub queued_tasks_by_priority: [AtomicUsize; 5],
    pub total_dispatched: AtomicU64,
    pub completed_tasks_total: AtomicU64,
    pub failed_tasks_total: AtomicU64,
    pub cancelled_tasks_total: AtomicU64,
    pub timed_out_tasks_total: AtomicU64,

    pub queue_latency: LatencyHistogram,
    pub dispatch_latency: LatencyHistogram,
    pub run_duration: LatencyHistogram,
    pub total_turnaround: LatencyHistogram,

    pub event_bus: Arc<EventBus>,
}

impl EngineTelemetry {
    /// Creates a new EngineTelemetry instance with default configuration.
    pub fn new() -> Self {
        Self::with_capacity(10_000)
    }

    /// Creates a new EngineTelemetry with the specified event bus capacity.
    pub fn with_capacity(event_capacity: usize) -> Self {
        let clock = Clock::new();
        Self {
            clock,
            active_tasks: AtomicUsize::new(0),
            queued_tasks_by_priority: [
                AtomicUsize::new(0),
                AtomicUsize::new(0),
                AtomicUsize::new(0),
                AtomicUsize::new(0),
                AtomicUsize::new(0),
            ],
            total_dispatched: AtomicU64::new(0),
            completed_tasks_total: AtomicU64::new(0),
            failed_tasks_total: AtomicU64::new(0),
            cancelled_tasks_total: AtomicU64::new(0),
            timed_out_tasks_total: AtomicU64::new(0),

            queue_latency: LatencyHistogram::new(),
            dispatch_latency: LatencyHistogram::new(),
            run_duration: LatencyHistogram::new(),
            total_turnaround: LatencyHistogram::new(),

            event_bus: Arc::new(EventBus::new(event_capacity)),
        }
    }

    /// Creates a new TaskTelemetry measurement block initialized with the engine clock.
    pub fn new_task_telemetry(&self) -> TaskTelemetry {
        TaskTelemetry::new(self.clock.clone())
    }

    /// Records completed task latencies and updates counters.
    pub fn record_task_completion(&self, telemetry: &TaskTelemetry) {
        self.completed_tasks_total.fetch_add(1, Ordering::Relaxed);
        if let Some(queue) = telemetry.queue_duration() {
            self.queue_latency.record(queue);
        }
        if let Some(dispatch) = telemetry.dispatch_latency() {
            self.dispatch_latency.record(dispatch);
        }
        if let Some(run) = telemetry.run_duration() {
            self.run_duration.record(run);
        }
        if let Some(total) = telemetry.total_duration() {
            self.total_turnaround.record(total);
        }
    }

    /// Records a task failure.
    pub fn record_task_failure(&self, telemetry: &TaskTelemetry) {
        self.failed_tasks_total.fetch_add(1, Ordering::Relaxed);
        if let Some(run) = telemetry.run_duration() {
            self.run_duration.record(run);
        }
        if let Some(total) = telemetry.total_duration() {
            self.total_turnaround.record(total);
        }
    }

    /// Records a task cancellation.
    pub fn record_task_cancellation(&self, _telemetry: &TaskTelemetry) {
        self.cancelled_tasks_total.fetch_add(1, Ordering::Relaxed);
    }

    /// Records a task timeout.
    pub fn record_task_timeout(&self, _telemetry: &TaskTelemetry) {
        self.timed_out_tasks_total.fetch_add(1, Ordering::Relaxed);
    }

    /// Generates an immutable snapshot of current engine metrics.
    pub fn snapshot(&self) -> MetricsSnapshot {
        let queued = [
            self.queued_tasks_by_priority[0].load(Ordering::Relaxed),
            self.queued_tasks_by_priority[1].load(Ordering::Relaxed),
            self.queued_tasks_by_priority[2].load(Ordering::Relaxed),
            self.queued_tasks_by_priority[3].load(Ordering::Relaxed),
            self.queued_tasks_by_priority[4].load(Ordering::Relaxed),
        ];

        MetricsSnapshot {
            active_tasks: self.active_tasks.load(Ordering::Relaxed),
            queued_tasks_by_priority: queued,
            total_dispatched: self.total_dispatched.load(Ordering::Relaxed),
            completed_tasks_total: self.completed_tasks_total.load(Ordering::Relaxed),
            failed_tasks_total: self.failed_tasks_total.load(Ordering::Relaxed),
            cancelled_tasks_total: self.cancelled_tasks_total.load(Ordering::Relaxed),
            timed_out_tasks_total: self.timed_out_tasks_total.load(Ordering::Relaxed),
            queue_latency_us: self.queue_latency.summary(),
            dispatch_latency_us: self.dispatch_latency.summary(),
            run_duration_us: self.run_duration.summary(),
            total_turnaround_us: self.total_turnaround.summary(),
        }
    }
}

impl Default for EngineTelemetry {
    fn default() -> Self {
        Self::new()
    }
}

/// Point-in-time snapshot of engine telemetry metrics.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MetricsSnapshot {
    pub active_tasks: usize,
    pub queued_tasks_by_priority: [usize; 5],
    pub total_dispatched: u64,
    pub completed_tasks_total: u64,
    pub failed_tasks_total: u64,
    pub cancelled_tasks_total: u64,
    pub timed_out_tasks_total: u64,
    pub queue_latency_us: LatencySummary,
    pub dispatch_latency_us: LatencySummary,
    pub run_duration_us: LatencySummary,
    pub total_turnaround_us: LatencySummary,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_task_telemetry_durations() {
        let clock = Clock::new();
        let mut telemetry = TaskTelemetry::new(clock);

        std::thread::sleep(Duration::from_millis(10));
        telemetry.mark_scheduled();

        std::thread::sleep(Duration::from_millis(10));
        telemetry.mark_started();

        std::thread::sleep(Duration::from_millis(20));
        telemetry.mark_completed();

        let queue = telemetry.queue_duration().unwrap();
        let dispatch = telemetry.dispatch_latency().unwrap();
        let run = telemetry.run_duration().unwrap();
        let total = telemetry.total_duration().unwrap();

        assert!(queue.as_millis() >= 8);
        assert!(dispatch.as_millis() >= 8);
        assert!(run.as_millis() >= 18);
        assert!(total.as_millis() >= 38);
    }

    #[test]
    fn test_latency_histogram_percentiles() {
        let histogram = LatencyHistogram::new();
        for i in 1..=100 {
            histogram.record(Duration::from_micros(i * 10));
        }

        let summary = histogram.summary();
        assert_eq!(summary.count, 100);
        assert!(summary.p50_us >= 450 && summary.p50_us <= 550);
        assert!(summary.p99_us >= 950 && summary.p99_us <= 1050);
    }

    #[tokio::test]
    async fn test_event_bus_broadcast() {
        let bus = EventBus::new(100);
        let mut rx1 = bus.subscribe();
        let mut rx2 = bus.subscribe();

        let event = EngineEvent::SystemAlert {
            level: "INFO".to_string(),
            message: "Engine started".to_string(),
        };

        let sent = bus.publish(event);
        assert_eq!(sent, 2);

        let received1 = rx1.recv().await.unwrap();
        let received2 = rx2.recv().await.unwrap();

        match (received1, received2) {
            (EngineEvent::SystemAlert { message: m1, .. }, EngineEvent::SystemAlert { message: m2, .. }) => {
                assert_eq!(m1, "Engine started");
                assert_eq!(m2, "Engine started");
            }
            _ => panic!("Unexpected event received"),
        }
    }

    #[test]
    fn test_telemetry_snapshot_serialization() {
        let telemetry = EngineTelemetry::new();
        telemetry.active_tasks.store(5, Ordering::Relaxed);
        telemetry.completed_tasks_total.store(42, Ordering::Relaxed);

        let mut task = telemetry.new_task_telemetry();
        task.mark_scheduled();
        task.mark_started();
        task.mark_completed();
        telemetry.record_task_completion(&task);

        let snapshot = telemetry.snapshot();
        assert_eq!(snapshot.active_tasks, 5);
        assert_eq!(snapshot.completed_tasks_total, 43);

        let json = serde_json::to_string_pretty(&snapshot).unwrap();
        assert!(json.contains("\"active_tasks\": 5"));
        assert!(json.contains("\"completed_tasks_total\": 43"));
    }
}

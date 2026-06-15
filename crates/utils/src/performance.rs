//! Operation timing and performance metrics tracking.

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

/// Per-operation statistics snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationStats {
    pub count: usize,
    pub success_count: usize,
    pub error_count: usize,
    pub success_rate: f64,
    pub avg_time_ms: f64,
    pub min_time_ms: f64,
    pub max_time_ms: f64,
    pub median_time_ms: f64,
    pub std_dev_ms: f64,
}

/// Overall system statistics snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverallStats {
    pub uptime_seconds: f64,
    pub total_operations: usize,
    pub total_success: usize,
    pub total_errors: usize,
    pub overall_success_rate: f64,
    pub avg_operation_time_ms: f64,
    pub operations_per_second: f64,
    pub operation_types: Vec<String>,
}

/// Tracks timing and success/failure counts per named operation.
///
/// Keeps at most 1 000 samples per operation to bound memory usage.
pub struct PerformanceMonitor {
    /// operation_name → list of durations in milliseconds
    times: HashMap<String, Vec<f64>>,
    /// operation_name → (success_count, error_count)
    counts: HashMap<String, (usize, usize)>,
    start: std::time::Instant,
}

impl PerformanceMonitor {
    const MAX_SAMPLES: usize = 1_000;

    /// Create a new, empty monitor.
    pub fn new() -> Self {
        Self {
            times: HashMap::new(),
            counts: HashMap::new(),
            start: std::time::Instant::now(),
        }
    }

    /// Record a completed operation.
    ///
    /// `duration_ms` is the wall-clock time of the operation in milliseconds.
    pub fn record(&mut self, name: &str, duration_ms: f64, success: bool) {
        let vec = self.times.entry(name.to_string()).or_default();
        vec.push(duration_ms);
        if vec.len() > Self::MAX_SAMPLES {
            vec.drain(0..vec.len() - Self::MAX_SAMPLES);
        }

        let (s, e) = self.counts.entry(name.to_string()).or_insert((0, 0));
        if success { *s += 1; } else { *e += 1; }
    }

    /// Get statistics for a specific operation. Returns `None` if no data yet.
    pub fn stats_for(&self, name: &str) -> Option<OperationStats> {
        let times = self.times.get(name)?;
        if times.is_empty() {
            return None;
        }
        let (sc, ec) = self.counts.get(name).copied().unwrap_or((0, 0));
        Some(compute_stats(times, sc, ec))
    }

    /// Get aggregate statistics across all operations.
    pub fn overall_stats(&self) -> OverallStats {
        let all: Vec<f64> = self.times.values().flatten().copied().collect();
        let total = all.len();
        let total_success: usize = self.counts.values().map(|(s, _)| s).sum();
        let total_errors: usize = self.counts.values().map(|(_, e)| e).sum();
        let uptime = self.start.elapsed().as_secs_f64();

        let avg = if all.is_empty() {
            0.0
        } else {
            all.iter().sum::<f64>() / all.len() as f64
        };

        OverallStats {
            uptime_seconds: uptime,
            total_operations: total,
            total_success,
            total_errors,
            overall_success_rate: if total > 0 { total_success as f64 / total as f64 } else { 0.0 },
            avg_operation_time_ms: avg,
            operations_per_second: if uptime > 0.0 { total as f64 / uptime } else { 0.0 },
            operation_types: self.times.keys().cloned().collect(),
        }
    }

    /// Reset all recorded metrics and restart the uptime clock.
    pub fn reset(&mut self) {
        self.times.clear();
        self.counts.clear();
        self.start = std::time::Instant::now();
    }
}

impl Default for PerformanceMonitor {
    fn default() -> Self {
        Self::new()
    }
}

// ── helpers ────────────────────────────────────────────────────────────────

fn compute_stats(times: &[f64], success: usize, errors: usize) -> OperationStats {
    let count = times.len();
    let sum: f64 = times.iter().sum();
    let avg = sum / count as f64;
    let min = times.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = times.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

    let mut sorted = times.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let median = if count % 2 == 0 {
        (sorted[count / 2 - 1] + sorted[count / 2]) / 2.0
    } else {
        sorted[count / 2]
    };

    let variance = times.iter().map(|t| (t - avg).powi(2)).sum::<f64>() / count as f64;
    let std_dev = variance.sqrt();

    OperationStats {
        count,
        success_count: success,
        error_count: errors,
        success_rate: if count > 0 { success as f64 / count as f64 } else { 0.0 },
        avg_time_ms: avg,
        min_time_ms: min,
        max_time_ms: max,
        median_time_ms: median,
        std_dev_ms: std_dev,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_and_retrieves_stats() {
        let mut pm = PerformanceMonitor::new();
        pm.record("test_op", 10.0, true);
        pm.record("test_op", 20.0, true);
        pm.record("test_op", 30.0, false);
        let stats = pm.stats_for("test_op").unwrap();
        assert_eq!(stats.count, 3);
        assert_eq!(stats.success_count, 2);
        assert_eq!(stats.error_count, 1);
        assert!((stats.avg_time_ms - 20.0).abs() < 0.001);
        assert!((stats.min_time_ms - 10.0).abs() < 0.001);
        assert!((stats.max_time_ms - 30.0).abs() < 0.001);
    }
}

//! Real-time system resource monitor and hardware telemetry engine.
//!
//! Provides non-blocking background polling of host CPU utilization,
//! core metrics, system RAM, swap pressure, process memory, and GPU/VRAM states.
//!
//! Publishes immutable, lock-free [`SystemSnapshot`] states via `tokio::sync::watch`.

use crate::gpu::{GpuDetector, GpuDetectorTrait, GpuInfo};
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use sysinfo::{
    CpuRefreshKind, MemoryRefreshKind, Pid, ProcessRefreshKind, ProcessesToUpdate, RefreshKind,
    System,
};
use tokio::sync::watch;
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

/// Host CPU telemetry metrics.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CpuMetrics {
    /// Number of physical CPU cores
    pub physical_core_count: usize,
    /// Number of logical threads
    pub logical_core_count: usize,
    /// Global aggregated CPU usage percentage (0.0 - 100.0)
    pub global_cpu_usage_pct: f32,
    /// Per-core CPU load percentages
    pub per_core_usage_pct: Vec<f32>,
    /// CPU model / brand name
    pub cpu_brand: String,
    /// CPU clock frequency in MHz
    pub frequency_mhz: u64,
}

/// Host Memory and Swap metrics.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryMetrics {
    /// Total physical RAM in bytes
    pub total_ram_bytes: u64,
    /// Currently used RAM in bytes
    pub used_ram_bytes: u64,
    /// Available RAM for allocation in bytes
    pub available_ram_bytes: u64,
    /// Free unallocated RAM in bytes
    pub free_ram_bytes: u64,
    /// Total system swap space in bytes
    pub total_swap_bytes: u64,
    /// Used system swap space in bytes
    pub used_swap_bytes: u64,
    /// Memory pressure percentage: (used_ram / total_ram) * 100.0
    pub memory_pressure_pct: f32,
}

impl MemoryMetrics {
    /// Total RAM in Gigabytes.
    pub fn total_ram_gb(&self) -> f64 {
        self.total_ram_bytes as f64 / (1024.0 * 1024.0 * 1024.0)
    }

    /// Available RAM in Gigabytes.
    pub fn available_ram_gb(&self) -> f64 {
        self.available_ram_bytes as f64 / (1024.0 * 1024.0 * 1024.0)
    }

    /// Available RAM in Megabytes.
    pub fn available_ram_mb(&self) -> u64 {
        self.available_ram_bytes / (1024 * 1024)
    }
}

/// Process-level resource metrics for the MCP IDE engine host process.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProcessMetrics {
    /// Process identifier (PID)
    pub pid: u32,
    /// Process CPU utilization percentage (0.0 - 100.0)
    pub process_cpu_usage_pct: f32,
    /// Resident memory in bytes (RSS)
    pub process_memory_bytes: u64,
    /// Virtual memory footprint in bytes
    pub process_virtual_memory_bytes: u64,
}

/// Comprehensive immutable system hardware and process snapshot.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SystemSnapshot {
    /// Capture timestamp
    pub timestamp: SystemTime,
    /// Host CPU metrics
    pub cpu: CpuMetrics,
    /// Host memory metrics
    pub memory: MemoryMetrics,
    /// Current process metrics
    pub process: ProcessMetrics,
    /// Detected GPU devices
    pub gpus: Vec<GpuInfo>,
    /// Index into `gpus` for the primary GPU (if available)
    pub primary_gpu_index: Option<usize>,
}

impl SystemSnapshot {
    /// Returns the primary GPU metrics if one is available.
    pub fn primary_gpu(&self) -> Option<&GpuInfo> {
        self.primary_gpu_index.and_then(|idx| self.gpus.get(idx))
    }

    /// Returns the total available VRAM across all discrete GPUs.
    pub fn total_free_vram_bytes(&self) -> u64 {
        self.gpus.iter().map(|g| g.free_vram_bytes).sum()
    }

    /// Returns whether any GPU with at least `min_vram_bytes` is available.
    pub fn has_gpu_with_min_vram(&self, min_vram_bytes: u64) -> bool {
        self.gpus.iter().any(|g| g.free_vram_bytes >= min_vram_bytes)
    }
}

impl Default for SystemSnapshot {
    fn default() -> Self {
        Self {
            timestamp: SystemTime::now(),
            cpu: CpuMetrics {
                logical_core_count: 1,
                physical_core_count: 1,
                global_cpu_usage_pct: 0.0,
                per_core_usage_pct: vec![],
                cpu_brand: "CPU".to_string(),
                frequency_mhz: 0,
            },
            memory: MemoryMetrics {
                total_ram_bytes: 1,
                used_ram_bytes: 0,
                free_ram_bytes: 1,
                available_ram_bytes: 1,
                total_swap_bytes: 0,
                used_swap_bytes: 0,
                memory_pressure_pct: 0.0,
            },
            process: ProcessMetrics {
                pid: 0,
                process_cpu_usage_pct: 0.0,
                process_memory_bytes: 0,
                process_virtual_memory_bytes: 0,
            },
            gpus: vec![],
            primary_gpu_index: None,
        }
    }
}

/// Dynamic asynchronous resource monitor.
///
/// Spawns a background polling tick loop that refreshes CPU, RAM, process,
/// and GPU metrics without blocking runtime execution threads.
pub struct ResourceMonitor {
    snapshot_tx: watch::Sender<SystemSnapshot>,
    snapshot_rx: watch::Receiver<SystemSnapshot>,
    cancel_token: CancellationToken,
    poll_interval: Arc<RwLock<Duration>>,
}

impl ResourceMonitor {
    /// Starts the resource monitor with standard cross-platform hardware detection.
    pub fn new(poll_interval: Duration) -> Self {
        let detector: Arc<dyn GpuDetectorTrait> = Arc::new(GpuDetector::new());
        Self::with_gpu_detector(poll_interval, detector)
    }

    /// Starts the resource monitor with a custom GPU detection strategy (e.g. for testing).
    pub fn with_gpu_detector(
        poll_interval: Duration,
        detector: Arc<dyn GpuDetectorTrait>,
    ) -> Self {
        let initial_snapshot = Self::sample_hardware_blocking(detector.as_ref());
        let (tx, rx) = watch::channel(initial_snapshot);
        let cancel_token = CancellationToken::new();
        let interval_holder = Arc::new(RwLock::new(poll_interval));

        let loop_token = cancel_token.clone();
        let loop_interval = interval_holder.clone();
        let loop_detector = detector.clone();
        let loop_tx = tx.clone();

        tokio::spawn(async move {
            info!("ResourceMonitor background polling loop started");
            let mut sys = System::new();
            let current_pid = sysinfo::get_current_pid().ok();

            // Initial warmup refresh for CPU baseline
            sys.refresh_specifics(
                RefreshKind::new()
                    .with_cpu(CpuRefreshKind::everything())
                    .with_memory(MemoryRefreshKind::everything()),
            );

            loop {
                let current_duration = *loop_interval.read();
                tokio::select! {
                    _ = loop_token.cancelled() => {
                        debug!("ResourceMonitor background polling loop received cancellation");
                        break;
                    }
                    _ = tokio::time::sleep(current_duration) => {
                        // Refresh sysinfo state
                        let detector_ref = loop_detector.clone();
                        let snapshot = tokio::task::spawn_blocking(move || {
                            let mut s = System::new();
                            s.refresh_specifics(
                                RefreshKind::new()
                                    .with_cpu(CpuRefreshKind::everything())
                                    .with_memory(MemoryRefreshKind::everything())
                            );

                            let pid = sysinfo::get_current_pid().ok();
                            if let Some(p) = pid {
                                s.refresh_processes_specifics(
                                    ProcessesToUpdate::Some(&[p]),
                                    ProcessRefreshKind::everything(),
                                );
                            }

                            Self::build_snapshot_from_system(&s, pid, &*detector_ref)
                        })
                        .await;

                        match snapshot {
                            Ok(snap) => {
                                if loop_tx.send(snap).is_err() {
                                    debug!("All ResourceMonitor subscribers dropped; exiting loop");
                                    break;
                                }
                            }
                            Err(e) => {
                                error!("Error in ResourceMonitor background sampling: {}", e);
                            }
                        }
                    }
                }
            }
            debug!("ResourceMonitor background polling loop terminated");
        });

        Self {
            snapshot_tx: tx,
            snapshot_rx: rx,
            cancel_token,
            poll_interval: interval_holder,
        }
    }

    /// Obtains the most recent immutable system resource snapshot in $O(1)$ time with zero locks.
    pub fn snapshot(&self) -> SystemSnapshot {
        self.snapshot_rx.borrow().clone()
    }

    /// Subscribes to real-time system snapshot updates.
    pub fn subscribe(&self) -> watch::Receiver<SystemSnapshot> {
        self.snapshot_rx.clone()
    }

    /// Dynamically updates the polling frequency interval.
    pub fn set_poll_interval(&self, new_interval: Duration) {
        *self.poll_interval.write() = new_interval;
    }

    /// Manually injects a snapshot (useful for unit testing synthetic loads and stress conditions).
    pub fn inject_snapshot(&self, snapshot: SystemSnapshot) {
        let _ = self.snapshot_tx.send(snapshot);
    }

    /// Gracefully stops the background telemetry tick loop.
    pub fn shutdown(&self) {
        self.cancel_token.cancel();
    }

    /// One-shot synchronous sampling of host hardware state.
    pub fn sample_hardware_blocking(detector: &dyn GpuDetectorTrait) -> SystemSnapshot {
        let mut sys = System::new();
        sys.refresh_specifics(
            RefreshKind::new()
                .with_cpu(CpuRefreshKind::everything())
                .with_memory(MemoryRefreshKind::everything()),
        );

        let pid = sysinfo::get_current_pid().ok();
        if let Some(p) = pid {
            sys.refresh_processes_specifics(
                ProcessesToUpdate::Some(&[p]),
                ProcessRefreshKind::everything(),
            );
        }

        Self::build_snapshot_from_system(&sys, pid, detector)
    }

    fn build_snapshot_from_system(
        sys: &System,
        pid: Option<Pid>,
        detector: &dyn GpuDetectorTrait,
    ) -> SystemSnapshot {
        let cpus = sys.cpus();
        let physical_cores = sys.physical_core_count().unwrap_or_else(|| cpus.len().max(1));
        let logical_cores = cpus.len().max(1);
        let global_cpu_usage = sys.global_cpu_usage();
        let per_core_usage = cpus.iter().map(|c| c.cpu_usage()).collect();
        let cpu_brand = cpus
            .first()
            .map(|c| c.brand().to_string())
            .unwrap_or_else(|| "Host CPU".to_string());
        let frequency = cpus.first().map(|c| c.frequency()).unwrap_or(0);

        let total_ram = sys.total_memory();
        let used_ram = sys.used_memory();
        let available_ram = sys.available_memory();
        let free_ram = sys.free_memory();
        let total_swap = sys.total_swap();
        let used_swap = sys.used_swap();
        let memory_pressure = if total_ram > 0 {
            (used_ram as f32 / total_ram as f32) * 100.0
        } else {
            0.0
        };

        let process_metrics = if let Some(p) = pid.and_then(|id| sys.process(id)) {
            ProcessMetrics {
                pid: pid.map(|id| id.as_u32()).unwrap_or(0),
                process_cpu_usage_pct: p.cpu_usage(),
                process_memory_bytes: p.memory(),
                process_virtual_memory_bytes: p.virtual_memory(),
            }
        } else {
            ProcessMetrics {
                pid: pid.map(|id| id.as_u32()).unwrap_or(0),
                process_cpu_usage_pct: 0.0,
                process_memory_bytes: 0,
                process_virtual_memory_bytes: 0,
            }
        };

        let gpus = detector.probe_gpus();
        let primary_gpu_index = if gpus.is_empty() { None } else { Some(0) };

        SystemSnapshot {
            timestamp: SystemTime::now(),
            cpu: CpuMetrics {
                physical_core_count: physical_cores,
                logical_core_count: logical_cores,
                global_cpu_usage_pct: global_cpu_usage,
                per_core_usage_pct: per_core_usage,
                cpu_brand,
                frequency_mhz: frequency,
            },
            memory: MemoryMetrics {
                total_ram_bytes: total_ram,
                used_ram_bytes: used_ram,
                available_ram_bytes: available_ram,
                free_ram_bytes: free_ram,
                total_swap_bytes: total_swap,
                used_swap_bytes: used_swap,
                memory_pressure_pct: memory_pressure,
            },
            process: process_metrics,
            gpus,
            primary_gpu_index,
        }
    }
}

impl Drop for ResourceMonitor {
    fn drop(&mut self) {
        self.shutdown();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_resource_monitor_live_snapshot() {
        let monitor = ResourceMonitor::new(Duration::from_millis(50));
        let snap = monitor.snapshot();

        assert!(snap.cpu.logical_core_count > 0);
        assert!(snap.memory.total_ram_bytes > 0);

        let mut rx = monitor.subscribe();
        let res = tokio::time::timeout(Duration::from_millis(500), rx.changed()).await;
        assert!(res.is_ok());

        let updated = rx.borrow().clone();
        assert!(updated.memory.total_ram_bytes > 0);
        monitor.shutdown();
    }
}

use mcp_resource::{
    CpuMetrics, MemoryMetrics, ProcessMetrics, ResourceMonitor, SystemSnapshot,
};
use std::time::{Duration, SystemTime};

#[tokio::test]
async fn test_live_telemetry_polling_and_updates() {
    let monitor = ResourceMonitor::new(Duration::from_millis(50));
    let initial_snapshot = monitor.snapshot();

    // Verify host hardware discovery
    assert!(
        initial_snapshot.cpu.logical_core_count > 0,
        "Expected at least 1 logical core"
    );
    assert!(
        initial_snapshot.cpu.physical_core_count > 0,
        "Expected at least 1 physical core"
    );
    assert!(
        initial_snapshot.memory.total_ram_bytes > 0,
        "Expected total RAM > 0"
    );
    assert!(
        initial_snapshot.memory.available_ram_bytes > 0,
        "Expected available RAM > 0"
    );

    // Subscribe to watch channel
    let mut rx = monitor.subscribe();
    assert_eq!(rx.borrow().cpu.logical_core_count, initial_snapshot.cpu.logical_core_count);

    // Wait for subsequent tick
    let changed = tokio::time::timeout(Duration::from_millis(600), rx.changed()).await;
    assert!(
        changed.is_ok(),
        "Telemetry watch channel did not emit tick within timeout"
    );

    let updated_snapshot = rx.borrow().clone();
    assert!(updated_snapshot.memory.total_ram_bytes > 0);
    assert_eq!(
        updated_snapshot.cpu.logical_core_count,
        initial_snapshot.cpu.logical_core_count
    );

    monitor.shutdown();
}

#[tokio::test]
async fn test_dynamic_polling_interval_change() {
    let monitor = ResourceMonitor::new(Duration::from_millis(100));
    monitor.set_poll_interval(Duration::from_millis(20));

    let mut rx = monitor.subscribe();
    let res = tokio::time::timeout(Duration::from_millis(300), rx.changed()).await;
    assert!(res.is_ok());

    monitor.shutdown();
}

#[tokio::test]
async fn test_synthetic_snapshot_injection() {
    let monitor = ResourceMonitor::new(Duration::from_secs(10));
    let mut rx = monitor.subscribe();

    let synthetic = SystemSnapshot {
        timestamp: SystemTime::now(),
        cpu: CpuMetrics {
            physical_core_count: 64,
            logical_core_count: 128,
            global_cpu_usage_pct: 75.5,
            per_core_usage_pct: vec![75.5; 128],
            cpu_brand: "Synthetic SuperCPU".to_string(),
            frequency_mhz: 4500,
        },
        memory: MemoryMetrics {
            total_ram_bytes: 256 * 1024 * 1024 * 1024,
            used_ram_bytes: 128 * 1024 * 1024 * 1024,
            available_ram_bytes: 128 * 1024 * 1024 * 1024,
            free_ram_bytes: 128 * 1024 * 1024 * 1024,
            total_swap_bytes: 64 * 1024 * 1024 * 1024,
            used_swap_bytes: 0,
            memory_pressure_pct: 50.0,
        },
        process: ProcessMetrics {
            pid: 9999,
            process_cpu_usage_pct: 12.0,
            process_memory_bytes: 512 * 1024 * 1024,
            process_virtual_memory_bytes: 1024 * 1024 * 1024,
        },
        gpus: Vec::new(),
        primary_gpu_index: None,
    };

    monitor.inject_snapshot(synthetic.clone());
    let current = monitor.snapshot();
    assert_eq!(current.cpu.logical_core_count, 128);
    assert_eq!(current.cpu.cpu_brand, "Synthetic SuperCPU");
    assert_eq!(current.memory.total_ram_gb(), 256.0);

    let changed = rx.has_changed();
    assert!(changed.unwrap_or(false) || rx.borrow().cpu.logical_core_count == 128);

    monitor.shutdown();
}

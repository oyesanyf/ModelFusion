use mcp_resource::{
    ExecutionTarget, GpuDetector, GpuInfo, GpuVendor, MockGpuProber, ModelSelector, ModelSpec,
    ModelTier, SystemSnapshot,
};

fn create_mock_snapshot(
    vram_bytes: u64,
    free_vram_bytes: u64,
    total_ram_bytes: u64,
    avail_ram_bytes: u64,
    memory_pressure_pct: f32,
) -> SystemSnapshot {
    let gpus = if vram_bytes > 0 {
        vec![GpuInfo::new_mock(
            0,
            "NVIDIA GeForce RTX 4090",
            GpuVendor::Nvidia,
            vram_bytes,
            free_vram_bytes,
            Some((8, 9)),
        )]
    } else {
        Vec::new()
    };

    SystemSnapshot {
        timestamp: std::time::SystemTime::now(),
        cpu: mcp_resource::CpuMetrics {
            physical_core_count: 16,
            logical_core_count: 32,
            global_cpu_usage_pct: 15.0,
            per_core_usage_pct: vec![15.0; 32],
            cpu_brand: "AMD Ryzen 9 7950X".to_string(),
            frequency_mhz: 4500,
        },
        memory: mcp_resource::MemoryMetrics {
            total_ram_bytes,
            used_ram_bytes: total_ram_bytes.saturating_sub(avail_ram_bytes),
            available_ram_bytes: avail_ram_bytes,
            free_ram_bytes: avail_ram_bytes,
            total_swap_bytes: 32 * 1024 * 1024 * 1024,
            used_swap_bytes: 0,
            memory_pressure_pct,
        },
        process: mcp_resource::ProcessMetrics {
            pid: 4321,
            process_cpu_usage_pct: 2.0,
            process_memory_bytes: 128 * 1024 * 1024,
            process_virtual_memory_bytes: 256 * 1024 * 1024,
        },
        primary_gpu_index: if gpus.is_empty() { None } else { Some(0) },
        gpus,
    }
}

#[test]
fn test_tier_classification_logic() {
    let high_end = create_mock_snapshot(24 * 1024 * 1024 * 1024, 24 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024, 20.0);
    assert_eq!(ModelSelector::select_best_tier(&high_end), ModelTier::Large);

    let mid_tier = create_mock_snapshot(8 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024, 32 * 1024 * 1024 * 1024, 32 * 1024 * 1024 * 1024, 20.0);
    assert_eq!(ModelSelector::select_best_tier(&mid_tier), ModelTier::Medium);

    let entry_tier = create_mock_snapshot(4 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024, 16 * 1024 * 1024 * 1024, 16 * 1024 * 1024 * 1024, 20.0);
    assert_eq!(ModelSelector::select_best_tier(&entry_tier), ModelTier::Small);

    let low_end = create_mock_snapshot(0, 0, 8 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024, 50.0);
    assert_eq!(ModelSelector::select_best_tier(&low_end), ModelTier::MicroNano);

    let constrained = create_mock_snapshot(0, 0, 4 * 1024 * 1024 * 1024, 1 * 1024 * 1024 * 1024, 80.0);
    assert_eq!(ModelSelector::select_best_tier(&constrained), ModelTier::Cloud);
}

#[test]
fn test_routing_under_critical_system_memory_pressure() {
    // 95% RAM pressure -> Should trigger CloudFallback immediately
    let snap = create_mock_snapshot(24 * 1024 * 1024 * 1024, 24 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024, 95.0);
    let model = ModelSpec::llama_3_1_8b();

    let decision = ModelSelector::evaluate(&model, 8192, &snap);
    match decision.target {
        ExecutionTarget::CloudFallback { reason, .. } => {
            assert!(reason.contains("Critical host RAM pressure"));
        }
        other => panic!("Expected CloudFallback under 95% memory pressure, got {:?}", other),
    }
}

#[test]
fn test_catalog_best_model_selection() {
    let catalog = ModelSelector::default_catalog();

    // 1. On high-end 24GB VRAM GPU, should choose large / highest quality model that fits
    let high_snap = create_mock_snapshot(24 * 1024 * 1024 * 1024, 24 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024, 48 * 1024 * 1024 * 1024, 20.0);
    let choice = ModelSelector::select_best_model(&catalog, 4096, &high_snap);
    assert!(choice.is_some());
    let res = choice.unwrap();
    assert!(res.tier == ModelTier::Large || res.tier == ModelTier::Medium);

    // 2. On low-end machine (0 GPU, 4GB RAM), should choose Micro/Nano
    let low_snap = create_mock_snapshot(0, 0, 8 * 1024 * 1024 * 1024, 3 * 1024 * 1024 * 1024, 40.0);
    let choice_low = ModelSelector::select_best_model(&catalog, 2048, &low_snap);
    assert!(choice_low.is_some());
    let res_low = choice_low.unwrap();
    assert!(res_low.tier == ModelTier::MicroNano || res_low.tier == ModelTier::Small);
}

#[test]
fn test_gpu_detector_mock_fallback_chain() {
    let mock_gpu = GpuInfo::new_mock(
        0,
        "Mock AMD Radeon RX 7900 XTX",
        GpuVendor::Amd,
        24 * 1024 * 1024 * 1024,
        20 * 1024 * 1024 * 1024,
        None,
    );
    let mock_prober = MockGpuProber::new(vec![mock_gpu.clone()]);
    let (detector, prober) = GpuDetector::with_mock(mock_prober);

    let gpus = detector.detect_gpus();
    assert_eq!(gpus.len(), 1);
    assert_eq!(gpus[0].name, "Mock AMD Radeon RX 7900 XTX");
    assert_eq!(gpus[0].vendor, GpuVendor::Amd);

    // Dynamically change VRAM
    prober.set_free_vram(0, 10 * 1024 * 1024 * 1024);
    let updated = detector.detect_gpus();
    assert_eq!(updated[0].free_vram_bytes, 10 * 1024 * 1024 * 1024);
}

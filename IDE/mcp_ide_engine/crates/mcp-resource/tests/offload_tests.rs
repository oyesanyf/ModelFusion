use mcp_resource::{
    calculate_layer_offload, ModelSpec, QuantizationType, DEFAULT_SAFETY_HEADROOM_MARGIN,
};

#[test]
fn test_full_gpu_offload_calculation() {
    let model = ModelSpec::llama_3_1_8b(); // 32 layers
    let available_vram = 16 * 1024 * 1024 * 1024; // 16 GB VRAM

    let plan = calculate_layer_offload(&model, available_vram, 8192, DEFAULT_SAFETY_HEADROOM_MARGIN);

    assert!(plan.is_full_gpu);
    assert!(!plan.is_hybrid);
    assert!(!plan.is_cpu_only);
    assert_eq!(plan.gpu_layers, 32);
    assert_eq!(plan.cpu_layers, 0);
    assert_eq!(plan.total_layers, 32);
    assert_eq!(plan.ram_allocated_bytes, 0);
    assert!(plan.vram_allocated_bytes > 0);
}

#[test]
fn test_hybrid_layer_offload_partition() {
    let model = ModelSpec::llama_3_1_8b(); // 32 layers, total weights ~4.89GB
    let available_vram = 4 * 1024 * 1024 * 1024; // 4 GB VRAM

    let plan = calculate_layer_offload(&model, available_vram, 4096, DEFAULT_SAFETY_HEADROOM_MARGIN);

    assert!(plan.is_hybrid, "Expected hybrid offload with 4GB VRAM");
    assert!(!plan.is_full_gpu);
    assert!(!plan.is_cpu_only);
    assert!(plan.gpu_layers > 0 && plan.gpu_layers < 32);
    assert_eq!(plan.gpu_layers + plan.cpu_layers, 32);
    assert!(plan.vram_allocated_bytes > 0);
    assert!(plan.ram_allocated_bytes > 0);
}

#[test]
fn test_zero_vram_pure_cpu_offload() {
    let model = ModelSpec::llama_3_1_8b();
    let available_vram = 0; // 0 VRAM

    let plan = calculate_layer_offload(&model, available_vram, 8192, DEFAULT_SAFETY_HEADROOM_MARGIN);

    assert!(plan.is_cpu_only);
    assert!(!plan.is_full_gpu);
    assert!(!plan.is_hybrid);
    assert_eq!(plan.gpu_layers, 0);
    assert_eq!(plan.cpu_layers, 32);
    assert_eq!(plan.vram_allocated_bytes, 0);
    assert!(plan.ram_allocated_bytes > 0);
}

#[test]
fn test_large_70b_model_layer_offloading() {
    let model = ModelSpec::llama_3_3_70b(); // 80 layers, ~42GB weights Q4
    let available_vram = 24 * 1024 * 1024 * 1024; // 24 GB VRAM (RTX 4090 / 3090)

    let plan = calculate_layer_offload(&model, available_vram, 4096, DEFAULT_SAFETY_HEADROOM_MARGIN);

    assert!(plan.is_hybrid);
    assert!(plan.gpu_layers >= 30 && plan.gpu_layers <= 50);
    assert_eq!(plan.gpu_layers + plan.cpu_layers, 80);
}

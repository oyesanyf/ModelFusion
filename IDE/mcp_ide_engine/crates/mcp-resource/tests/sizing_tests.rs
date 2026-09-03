use mcp_resource::{
    calculate_activation_memory, calculate_kv_cache_memory, calculate_model_weights_memory,
    calculate_total_required_memory, KvCachePrecision, QuantizationType,
    DEFAULT_SAFETY_HEADROOM_MARGIN, DEFAULT_TENSOR_OVERHEAD,
};

#[test]
fn test_all_quantization_scaling_factors() {
    let params = 1_000_000_000u64; // 1B params

    let fp32_weight = calculate_model_weights_memory(params, QuantizationType::FP32, 1.0);
    assert_eq!(fp32_weight, 4_000_000_000);

    let fp16_weight = calculate_model_weights_memory(params, QuantizationType::FP16, 1.0);
    assert_eq!(fp16_weight, 2_000_000_000);

    let q8_weight = calculate_model_weights_memory(params, QuantizationType::Q8_0, 1.0);
    assert_eq!(q8_weight, 1_062_500_000);

    let q4_weight = calculate_model_weights_memory(params, QuantizationType::Q4_K_M, 1.0);
    assert_eq!(q4_weight, 580_000_000);

    let q2_weight = calculate_model_weights_memory(params, QuantizationType::Q2_K, 1.0);
    assert_eq!(q2_weight, 380_000_000);
}

#[test]
fn test_tensor_overhead_application() {
    let params = 10_000_000_000u64; // 10B params
    let raw = calculate_model_weights_memory(params, QuantizationType::FP16, 1.0);
    let with_overhead =
        calculate_model_weights_memory(params, QuantizationType::FP16, DEFAULT_TENSOR_OVERHEAD);

    assert_eq!(raw, 20_000_000_000);
    assert_eq!(with_overhead, 21_000_000_000); // +5%
}

#[test]
fn test_kv_cache_gqa_vs_mha() {
    // 32 layers, 128 head_dim, 8192 context, FP16 (2.0 bytes)
    let num_layers = 32;
    let head_dim = 128;
    let context = 8192;

    // Multi-Head Attention (32 KV heads)
    let kv_mha = calculate_kv_cache_memory(
        num_layers,
        32,
        head_dim,
        context,
        KvCachePrecision::FP16,
        1,
    );
    // 2 * 32 * 32 * 128 * 8192 * 2 = 4,294,967,296 bytes = 4.0 GB
    assert_eq!(kv_mha, 4_294_967_296);

    // Grouped-Query Attention (8 KV heads)
    let kv_gqa = calculate_kv_cache_memory(
        num_layers,
        8,
        head_dim,
        context,
        KvCachePrecision::FP16,
        1,
    );
    // 2 * 32 * 8 * 128 * 8192 * 2 = 1,073,741,824 bytes = 1.0 GB
    assert_eq!(kv_gqa, 1_073_741_824);
    assert_eq!(kv_gqa * 4, kv_mha);

    // FP8 KV cache (1.0 byte per elem)
    let kv_gqa_fp8 = calculate_kv_cache_memory(
        num_layers,
        8,
        head_dim,
        context,
        KvCachePrecision::FP8,
        1,
    );
    assert_eq!(kv_gqa_fp8, 536_870_912); // 512 MB
}

#[test]
fn test_context_length_kv_scaling() {
    let num_layers = 32;
    let num_kv_heads = 8;
    let head_dim = 128;

    let kv_4k = calculate_kv_cache_memory(num_layers, num_kv_heads, head_dim, 4096, KvCachePrecision::FP16, 1);
    let kv_8k = calculate_kv_cache_memory(num_layers, num_kv_heads, head_dim, 8192, KvCachePrecision::FP16, 1);
    let kv_32k = calculate_kv_cache_memory(num_layers, num_kv_heads, head_dim, 32768, KvCachePrecision::FP16, 1);
    let kv_128k = calculate_kv_cache_memory(num_layers, num_kv_heads, head_dim, 131072, KvCachePrecision::FP16, 1);

    assert_eq!(kv_8k, kv_4k * 2);
    assert_eq!(kv_32k, kv_4k * 8);
    assert_eq!(kv_128k, kv_4k * 32);
}

#[test]
fn test_working_activation_memory() {
    let act = calculate_activation_memory(1, 8192, 4096, 32, 2.0);
    // Base minimum is 128MB
    assert!(act >= 128 * 1024 * 1024);
}

#[test]
fn test_total_model_memory_with_safety_headroom() {
    // Llama 3.1 8B Q4_K_M
    let breakdown = calculate_total_required_memory(
        8_030_000_000,
        QuantizationType::Q4_K_M,
        32,
        8,
        128,
        4096,
        8192,
        KvCachePrecision::FP16,
        1,
        DEFAULT_SAFETY_HEADROOM_MARGIN,
    );

    assert_eq!(breakdown.safety_margin, 0.15);
    let expected_headroom = ((breakdown.base_total_bytes as f64) * 0.15).ceil() as u64;
    assert_eq!(breakdown.headroom_bytes, expected_headroom);
    assert_eq!(
        breakdown.total_required_bytes,
        breakdown.base_total_bytes + breakdown.headroom_bytes
    );
    assert!(breakdown.total_required_gb() > 6.0 && breakdown.total_required_gb() < 8.5);
}

//! Mathematical model memory sizing formulas.
//!
//! Provides exact memory formulas for:
//! - Model weight memory ($M_{\text{weights}} = \text{parameters} \times \text{bytes\_per\_weight} \times \text{tensor\_overhead}$)
//! - KV Cache memory ($M_{\text{kv}} = 2 \times N_{\text{layers}} \times N_{\text{kv\_heads}} \times D_{\text{head}} \times C_{\text{context}} \times B_{\text{elem}} \times S_{\text{batch}}$)
//! - Activation memory ($M_{\text{act}} = B_{\text{batch}} \times C_{\text{context}} \times D_{\text{model}} \times \text{layers} \times \text{overhead}$)
//! - Total required memory with configurable 15% safety headroom margin ($\gamma = 0.15$).

use serde::{Deserialize, Serialize};

/// Quantization scheme and effective bytes-per-weight scaling factor ($\beta_Q$).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum QuantizationType {
    /// Full precision (32-bit float, 4.0 bytes/param)
    FP32,
    /// Half precision (16-bit float, 2.0 bytes/param)
    FP16,
    /// Brain floating point (16-bit, 2.0 bytes/param)
    BF16,
    /// 8-bit quantization (Q8_0, ~1.0625 bytes/param = 8.5 bits)
    Q8_0,
    /// 6-bit K-quantization (~0.850 bytes/param = 6.8 bits)
    Q6_K,
    /// 5-bit K-quantization Medium (~0.725 bytes/param = 5.8 bits)
    Q5_K_M,
    /// 5-bit legacy quantization (~0.6875 bytes/param = 5.5 bits)
    Q5_0,
    /// 4-bit K-quantization Medium (~0.580 bytes/param = 4.64 bits)
    Q4_K_M,
    /// 4-bit legacy quantization (~0.5625 bytes/param = 4.5 bits)
    Q4_0,
    /// 3-bit K-quantization Medium (~0.480 bytes/param = 3.84 bits)
    Q3_K_M,
    /// 2-bit K-quantization (~0.380 bytes/param = 3.04 bits)
    Q2_K,
    /// Importance-quantized 4-bit (~0.530 bytes/param)
    IQ4_XS,
    /// Importance-quantized 3-bit (~0.385 bytes/param)
    IQ3_XXS,
    /// Importance-quantized 2-bit (~0.275 bytes/param)
    IQ2_XXS,
    /// Custom quantization scheme
    Custom { bytes_per_weight: f64 },
}

impl QuantizationType {
    /// Returns the effective bytes per parameter ($\beta_Q$).
    pub fn bytes_per_weight(&self) -> f64 {
        match self {
            Self::FP32 => 4.000,
            Self::FP16 => 2.000,
            Self::BF16 => 2.000,
            Self::Q8_0 => 1.0625,
            Self::Q6_K => 0.850,
            Self::Q5_K_M => 0.725,
            Self::Q5_0 => 0.6875,
            Self::Q4_K_M => 0.580,
            Self::Q4_0 => 0.5625,
            Self::Q3_K_M => 0.480,
            Self::Q2_K => 0.380,
            Self::IQ4_XS => 0.530,
            Self::IQ3_XXS => 0.385,
            Self::IQ2_XXS => 0.275,
            Self::Custom { bytes_per_weight } => *bytes_per_weight,
        }
    }

    /// Parses a quantization string (e.g. "Q4_K_M", "fp16", "q8_0").
    pub fn from_str_lenient(s: &str) -> Self {
        let normalized = s.trim().to_uppercase().replace('-', "_");
        match normalized.as_str() {
            "FP32" | "F32" => Self::FP32,
            "FP16" | "F16" => Self::FP16,
            "BF16" | "BFLOAT16" => Self::BF16,
            "Q8_0" | "Q8" => Self::Q8_0,
            "Q6_K" | "Q6" => Self::Q6_K,
            "Q5_K_M" | "Q5_K" | "Q5" => Self::Q5_K_M,
            "Q5_0" => Self::Q5_0,
            "Q4_K_M" | "Q4_K" | "Q4" => Self::Q4_K_M,
            "Q4_0" => Self::Q4_0,
            "Q3_K_M" | "Q3_K" | "Q3" => Self::Q3_K_M,
            "Q2_K" | "Q2" => Self::Q2_K,
            "IQ4_XS" | "IQ4" => Self::IQ4_XS,
            "IQ3_XXS" | "IQ3" => Self::IQ3_XXS,
            "IQ2_XXS" | "IQ2" => Self::IQ2_XXS,
            _ => Self::Q4_K_M,
        }
    }
}

/// KV Cache precision type and bytes per element ($B_{\text{elem}}$).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum KvCachePrecision {
    /// FP16 (2.0 bytes per key/value element)
    FP16,
    /// FP8 / Q8 (1.0 byte per key/value element)
    FP8,
    /// Q4 (0.5 bytes per key/value element)
    Q4,
    /// Custom bytes per element
    Custom(f64),
}

impl KvCachePrecision {
    pub fn bytes_per_elem(&self) -> f64 {
        match self {
            Self::FP16 => 2.0,
            Self::FP8 => 1.0,
            Self::Q4 => 0.5,
            Self::Custom(b) => *b,
        }
    }
}

/// Detailed memory breakdown for an LLM execution configuration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryBreakdown {
    /// Model weights memory in bytes ($M_{\text{weights}}$)
    pub weights_bytes: u64,
    /// KV Cache memory in bytes ($M_{\text{kv}}$)
    pub kv_cache_bytes: u64,
    /// Activation memory in bytes ($M_{\text{act}}$)
    pub activation_bytes: u64,
    /// Base required memory before headroom ($M_{\text{base}} = M_{\text{weights}} + M_{\text{kv}} + M_{\text{act}}$)
    pub base_total_bytes: u64,
    /// Safety headroom buffer in bytes ($M_{\text{base}} \times \gamma$)
    pub headroom_bytes: u64,
    /// Total required memory in bytes ($M_{\text{total}} = M_{\text{base}} + \text{headroom}$)
    pub total_required_bytes: u64,
    /// Headroom margin applied ($\gamma$, default 0.15 = 15%)
    pub safety_margin: f64,
}

impl MemoryBreakdown {
    /// Weights memory in Megabytes.
    pub fn weights_mb(&self) -> f64 {
        self.weights_bytes as f64 / (1024.0 * 1024.0)
    }

    /// KV Cache memory in Megabytes.
    pub fn kv_cache_mb(&self) -> f64 {
        self.kv_cache_bytes as f64 / (1024.0 * 1024.0)
    }

    /// Activation memory in Megabytes.
    pub fn activation_mb(&self) -> f64 {
        self.activation_bytes as f64 / (1024.0 * 1024.0)
    }

    /// Total required memory in Megabytes.
    pub fn total_required_mb(&self) -> f64 {
        self.total_required_bytes as f64 / (1024.0 * 1024.0)
    }

    /// Total required memory in Gigabytes.
    pub fn total_required_gb(&self) -> f64 {
        self.total_required_bytes as f64 / (1024.0 * 1024.0 * 1024.0)
    }
}

/// Default tensor overhead factor for model metadata, tensor padding, and GGUF/Safetensors headers (1.05 = +5%).
pub const DEFAULT_TENSOR_OVERHEAD: f64 = 1.05;

/// Default safety headroom margin ($\gamma = 0.15$ = 15%).
pub const DEFAULT_SAFETY_HEADROOM_MARGIN: f64 = 0.15;

/// Calculates model weights memory in bytes:
/// $$M_{\text{weights}} = \left( \text{parameters} \times \beta_Q \times \text{overhead} \right)$$
pub fn calculate_model_weights_memory(
    parameter_count: u64,
    quantization: QuantizationType,
    tensor_overhead: f64,
) -> u64 {
    let bytes_per_param = quantization.bytes_per_weight();
    ((parameter_count as f64) * bytes_per_param * tensor_overhead).ceil() as u64
}

/// Calculates KV Cache memory in bytes:
/// $$M_{\text{kv}} = 2 \times N_{\text{layers}} \times N_{\text{kv\_heads}} \times D_{\text{head}} \times C_{\text{context}} \times B_{\text{elem}} \times S_{\text{batch}}$$
///
/// Where:
/// - Factor 2: Accounts for Keys and Values ($K + V$)
/// - $N_{\text{layers}}$: Total transformer decoder layers
/// - $N_{\text{kv\_heads}}$: Number of key-value attention heads (GQA / MHA)
/// - $D_{\text{head}}$: Dimension per head (typically hidden_dim / num_attention_heads, e.g. 128)
/// - $C_{\text{context}}$: Context length in tokens
/// - $B_{\text{elem}}$: Bytes per KV element (2.0 for FP16, 1.0 for FP8)
/// - $S_{\text{batch}}$: Batch size (default 1)
pub fn calculate_kv_cache_memory(
    num_layers: usize,
    num_kv_heads: usize,
    head_dim: usize,
    context_tokens: usize,
    kv_precision: KvCachePrecision,
    batch_size: usize,
) -> u64 {
    let bytes_per_elem = kv_precision.bytes_per_elem();
    let total_elements =
        2.0 * (num_layers as f64) * (num_kv_heads as f64) * (head_dim as f64) * (context_tokens as f64) * (batch_size as f64);
    (total_elements * bytes_per_elem).ceil() as u64
}

/// Calculates working activation memory in bytes:
/// $$M_{\text{act}} = \max\left(256\text{ MB}, B_{\text{batch}} \times C_{\text{context}} \times D_{\text{model}} \times \text{layers} \times \text{overhead}\right)$$
///
/// Or simplified working activation buffer:
/// $$M_{\text{act}} = \max\left(256\text{ MB}, B_{\text{batch}} \times C_{\text{context}} \times D_{\text{model}} \times 4 \times B_{\text{elem}}\right)$$
pub fn calculate_activation_memory(
    batch_size: usize,
    context_tokens: usize,
    hidden_dim: usize,
    num_layers: usize,
    overhead_multiplier: f64,
) -> u64 {
    // Standard activation formula: batch * context * hidden_dim * layer_factor * overhead
    let raw_act = (batch_size as f64)
        * (context_tokens as f64)
        * (hidden_dim as f64)
        * (num_layers.min(4) as f64)
        * overhead_multiplier;

    // Ensure a baseline working buffer of at least 128 MB and at most scaled by context
    let min_buffer = 128 * 1024 * 1024; // 128 MB
    (raw_act as u64).max(min_buffer)
}

/// Calculates complete memory breakdown and total required memory with safety margin:
/// $$M_{\text{total}} = (M_{\text{weights}} + M_{\text{kv}} + M_{\text{act}}) \times (1 + \gamma)$$
pub fn calculate_total_required_memory(
    parameter_count: u64,
    quantization: QuantizationType,
    num_layers: usize,
    num_kv_heads: usize,
    head_dim: usize,
    hidden_dim: usize,
    context_tokens: usize,
    kv_precision: KvCachePrecision,
    batch_size: usize,
    safety_margin: f64,
) -> MemoryBreakdown {
    let weights_bytes =
        calculate_model_weights_memory(parameter_count, quantization, DEFAULT_TENSOR_OVERHEAD);
    let kv_cache_bytes = calculate_kv_cache_memory(
        num_layers,
        num_kv_heads,
        head_dim,
        context_tokens,
        kv_precision,
        batch_size,
    );
    let activation_bytes =
        calculate_activation_memory(batch_size, context_tokens, hidden_dim, num_layers, 2.0);

    let base_total_bytes = weights_bytes + kv_cache_bytes + activation_bytes;
    let headroom_bytes = ((base_total_bytes as f64) * safety_margin).ceil() as u64;
    let total_required_bytes = base_total_bytes + headroom_bytes;

    MemoryBreakdown {
        weights_bytes,
        kv_cache_bytes,
        activation_bytes,
        base_total_bytes,
        headroom_bytes,
        total_required_bytes,
        safety_margin,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quantization_factors() {
        assert_eq!(QuantizationType::FP16.bytes_per_weight(), 2.0);
        assert_eq!(QuantizationType::Q8_0.bytes_per_weight(), 1.0625);
        assert_eq!(QuantizationType::Q4_K_M.bytes_per_weight(), 0.580);
    }

    #[test]
    fn test_llama_3_8b_memory_math() {
        // Llama 3.1 8B parameters:
        // params: 8.03B, layers: 32, kv_heads: 8, head_dim: 128, hidden_dim: 4096, context: 8192
        let params = 8_030_000_000u64;
        let layers = 32;
        let kv_heads = 8;
        let head_dim = 128;
        let hidden_dim = 4096;
        let context = 8192;

        // 1. Weights memory for Q4_K_M:
        // 8.03e9 * 0.580 * 1.05 = ~4.89 GB = ~4_890_270_000 bytes
        let weights = calculate_model_weights_memory(params, QuantizationType::Q4_K_M, 1.05);
        assert!(weights > 4_800_000_000 && weights < 5_000_000_000);

        // 2. KV cache memory for 8192 context FP16:
        // 2 * 32 * 8 * 128 * 8192 * 2 = 1,073,741,824 bytes (exact 1.0 GB)
        let kv = calculate_kv_cache_memory(
            layers,
            kv_heads,
            head_dim,
            context,
            KvCachePrecision::FP16,
            1,
        );
        assert_eq!(kv, 1_073_741_824);

        // 3. Total memory with 15% headroom
        let breakdown = calculate_total_required_memory(
            params,
            QuantizationType::Q4_K_M,
            layers,
            kv_heads,
            head_dim,
            hidden_dim,
            context,
            KvCachePrecision::FP16,
            1,
            0.15,
        );

        assert_eq!(breakdown.kv_cache_bytes, 1_073_741_824);
        assert_eq!(breakdown.safety_margin, 0.15);
        assert!(breakdown.total_required_bytes > breakdown.base_total_bytes);
        assert_eq!(
            breakdown.total_required_bytes,
            breakdown.base_total_bytes + breakdown.headroom_bytes
        );
    }
}

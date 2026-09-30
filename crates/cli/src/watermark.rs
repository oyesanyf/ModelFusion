//! Watermark Detection Suite: Kirchenbauer Token Green-List & Image LSB Spatial Entropy Scanner
//!
//! Provides statistical token watermark verification (Kirchenbauer et al.) for LLM-generated prose
//! and spatial domain least-significant-bit (LSB) entropy & chi-square goodness-of-fit scanning for imagery.

use image::{GenericImageView, Pixel};
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::path::Path;

/// Result of statistical token green-list watermark evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionResult {
    pub total_evaluated: usize,
    pub green_count: usize,
    pub green_ratio: f64,
    pub z_score: f64,
    pub is_watermarked: bool,
}

/// Kirchenbauer et al. statistical token green-list watermark detector.
#[derive(Debug, Clone)]
pub struct TokenWatermarkDetector {
    secret_key: u64,
    gamma: f64,       // Expected fraction of green tokens under null hypothesis
    z_threshold: f64, // Standard score cutoff (typically 3.0 to 4.0)
}

impl Default for TokenWatermarkDetector {
    fn default() -> Self {
        Self::new(0x5F3759DF, 0.50, 4.0)
    }
}

impl TokenWatermarkDetector {
    pub fn new(secret_key: u64, gamma: f64, z_threshold: f64) -> Self {
        Self {
            secret_key,
            gamma,
            z_threshold,
        }
    }

    /// Evaluates whether a given token belongs to the green list based on the preceding context token.
    pub fn is_green_token(&self, context_token: u32, target_token: u32) -> bool {
        let mut hasher = DefaultHasher::new();
        self.secret_key.hash(&mut hasher);
        context_token.hash(&mut hasher);
        target_token.hash(&mut hasher);

        let hash_val = hasher.finish();
        // Check if the normalized pseudo-random output falls within the gamma fraction
        let normalized = (hash_val as f64) / (u64::MAX as f64);
        normalized < self.gamma
    }

    /// Computes the z-score over an entire tokenized sequence.
    pub fn detect(&self, tokens: &[u32]) -> Option<DetectionResult> {
        if tokens.len() < 2 {
            return None;
        }

        let mut green_count = 0usize;
        let total_evaluated = tokens.len() - 1;

        for window in tokens.windows(2) {
            let context_token = window[0];
            let target_token = window[1];

            if self.is_green_token(context_token, target_token) {
                green_count += 1;
            }
        }

        let n = total_evaluated as f64;
        let observed_mean = green_count as f64;
        let expected_mean = n * self.gamma;
        let standard_deviation = (n * self.gamma * (1.0 - self.gamma)).sqrt();

        let z_score = if standard_deviation > 0.0 {
            (observed_mean - expected_mean) / standard_deviation
        } else {
            0.0
        };

        Some(DetectionResult {
            total_evaluated,
            green_count,
            green_ratio: if n > 0.0 { observed_mean / n } else { 0.0 },
            z_score,
            is_watermarked: z_score >= self.z_threshold,
        })
    }

    /// Detect watermark from raw text using BPE tokenization (tiktoken cl100k_base) or word-hash fallback.
    pub fn detect_text(&self, text: &str) -> Option<DetectionResult> {
        let tokens = tokenize_text(text);
        self.detect(&tokens)
    }
}

/// Tokenize text into a token ID stream using tiktoken cl100k_base or word hashing.
pub fn tokenize_text(text: &str) -> Vec<u32> {
    if let Ok(bpe) = tiktoken_rs::cl100k_base() {
        bpe.encode_with_special_tokens(text)
            .into_iter()
            .map(|t| t as u32)
            .collect()
    } else {
        // Fallback: word-level token hashing
        text.split_whitespace()
            .map(|w| {
                let mut hasher = DefaultHasher::new();
                w.hash(&mut hasher);
                (hasher.finish() & 0xFFFF_FFFF) as u32
            })
            .collect()
    }
}

/// Result of spatial least significant bit (LSB) steganographic entropy and anomaly detection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageLsbAnalysis {
    pub total_samples: usize,
    pub bit_entropy: f64,
    pub chi_square_stat: f64,
    pub is_anomalous: bool,
}

/// Scans image color channels for spatial domain least-significant-bit watermarks and steganographic tampering.
#[derive(Debug, Clone)]
pub struct ImageWatermarkScanner {
    // A standard threshold for binary entropy deviation from natural photographic baselines
    pub entropy_threshold: f64,
}

impl Default for ImageWatermarkScanner {
    fn default() -> Self {
        Self::new(0.9995)
    }
}

impl ImageWatermarkScanner {
    pub fn new(entropy_threshold: f64) -> Self {
        Self { entropy_threshold }
    }

    pub fn scan_path<P: AsRef<Path>>(&self, path: P) -> Result<ImageLsbAnalysis, image::ImageError> {
        let img = image::open(path)?;
        Ok(self.analyze(&img))
    }

    pub fn scan_bytes(&self, bytes: &[u8]) -> Result<ImageLsbAnalysis, image::ImageError> {
        let img = image::load_from_memory(bytes)?;
        Ok(self.analyze(&img))
    }

    pub fn analyze<I: GenericImageView>(&self, img: &I) -> ImageLsbAnalysis
    where
        <<I as GenericImageView>::Pixel as Pixel>::Subpixel: std::ops::BitAnd<Output = <<I as GenericImageView>::Pixel as Pixel>::Subpixel> + PartialEq + From<u8> + Copy,
    {
        let mut zero_bits = 0usize;
        let mut one_bits = 0usize;
        let one = 1u8.into();

        for (_x, _y, pixel) in img.pixels() {
            let channels = pixel.channels();
            // Inspect the primary R, G, B channels
            for &value in channels.iter().take(3) {
                if (value & one) == one {
                    one_bits += 1;
                } else {
                    zero_bits += 1;
                }
            }
        }

        let total_samples = zero_bits + one_bits;
        if total_samples == 0 {
            return ImageLsbAnalysis {
                total_samples: 0,
                bit_entropy: 0.0,
                chi_square_stat: 0.0,
                is_anomalous: false,
            };
        }

        let p0 = zero_bits as f64 / total_samples as f64;
        let p1 = one_bits as f64 / total_samples as f64;

        // Shannon entropy of the least significant bit plane
        let entropy = -(
            (if p0 > 0.0 { p0 * p0.log2() } else { 0.0 }) +
            (if p1 > 0.0 { p1 * p1.log2() } else { 0.0 })
        );

        // Chi-Square goodness-of-fit against theoretical uniform noise distribution
        let expected = total_samples as f64 / 2.0;
        let chi_square = ((zero_bits as f64 - expected).powi(2) + (one_bits as f64 - expected).powi(2)) / expected;

        // Dense encrypted or pseudorandom watermarks push entropy extremely close to 1.0 (>= 0.999)
        let is_anomalous = entropy >= self.entropy_threshold;

        ImageLsbAnalysis {
            total_samples,
            bit_entropy: entropy,
            chi_square_stat: chi_square,
            is_anomalous,
        }
    }
}

/// Unified watermark report for both text and imagery.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "mode")]
pub enum WatermarkReport {
    Text {
        target: String,
        result: DetectionResult,
    },
    Image {
        target: String,
        result: ImageLsbAnalysis,
    },
}

impl WatermarkReport {
    pub fn to_markdown(&self) -> String {
        match self {
            WatermarkReport::Text { target, result } => {
                let status_badge = if result.is_watermarked {
                    "🚨 **WATERMARK DETECTED** (High statistical confidence)"
                } else {
                    "✅ **NO WATERMARK DETECTED** (Consistent with natural human variation)"
                };
                let display_target = if target.len() > 60 {
                    format!("{}...", &target[..57])
                } else {
                    target.clone()
                };
                format!(
                    "### ✍️ Text Watermark Analysis (Token Green-List Detector)\n\n\
                     - **Status**: {}\n\
                     - **Input Source**: `{}`\n\
                     - **Total Tokens Evaluated**: {}\n\
                     - **Green Token Count**: {}\n\
                     - **Observed Green Ratio**: {:.2}%\n\
                     - **Cumulative Z-Score**: {:.4}\n\
                     - **Watermark Threshold**: z ≥ 4.0000 (γ = 0.50, p < 0.00003)\n\n\
                     > **Statistical Methodology**: Kirchenbauer et al. green-list token hash partition test under binomial null hypothesis.",
                    status_badge,
                    display_target,
                    result.total_evaluated,
                    result.green_count,
                    result.green_ratio * 100.0,
                    result.z_score
                )
            }
            WatermarkReport::Image { target, result } => {
                let status_badge = if result.is_anomalous {
                    "🚨 **STEGANOGRAPHIC WATERMARK / TAMPERING DETECTED**"
                } else {
                    "✅ **CLEAN / NATURAL IMAGE** (No anomalous LSB steganography detected)"
                };
                format!(
                    "### 🖼️ Image LSB Spatial Entropy & Chi-Square Analysis\n\n\
                     - **Status**: {}\n\
                     - **Target Image**: `{}`\n\
                     - **Total LSB Samples Scanned**: {}\n\
                     - **LSB Bit-Plane Shannon Entropy**: {:.6} / 1.000000\n\
                     - **Chi-Square Goodness-of-Fit**: {:.4}\n\
                     - **Anomaly Flag**: {}\n\n\
                     > **Spatial Methodology**: PoV chi-square distribution scan of RGB least significant bits. Cryptographic/synthetic watermark embeddings flatten lower-bit entropy toward 1.0.",
                    status_badge,
                    target,
                    result.total_samples,
                    result.bit_entropy,
                    result.chi_square_stat,
                    if result.is_anomalous { "ANOMALOUS (≥ 0.9995)" } else { "NORMAL (< 0.9995)" }
                )
            }
        }
    }
}

/// Detect watermark across arbitrary input: image path, text file path, or inline text.
pub fn detect_watermark_input(input: &str) -> Result<WatermarkReport, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("No input provided for watermark detection. Provide inline text, a text file path, or an image file path (.png, .jpg).".to_string());
    }

    let path = Path::new(trimmed);
    if path.is_file() {
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        if matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "webp" | "bmp" | "gif" | "tiff" | "ico") {
            let scanner = ImageWatermarkScanner::default();
            match scanner.scan_path(path) {
                Ok(res) => Ok(WatermarkReport::Image {
                    target: trimmed.to_string(),
                    result: res,
                }),
                Err(e) => Err(format!("Failed to analyze image '{}': {}", trimmed, e)),
            }
        } else {
            // Read as text file
            match std::fs::read_to_string(path) {
                Ok(content) => {
                    let detector = TokenWatermarkDetector::default();
                    match detector.detect_text(&content) {
                        Some(res) => Ok(WatermarkReport::Text {
                            target: format!("file: {}", trimmed),
                            result: res,
                        }),
                        None => Err(format!("File '{}' has insufficient tokens (< 2) for statistical watermark evaluation.", trimmed)),
                    }
                }
                Err(e) => Err(format!("Failed to read file '{}': {}", trimmed, e)),
            }
        }
    } else {
        // Treat as inline text
        let detector = TokenWatermarkDetector::default();
        match detector.detect_text(trimmed) {
            Some(res) => Ok(WatermarkReport::Text {
                target: if trimmed.len() > 40 { format!("{}...", &trimmed[..37]) } else { trimmed.to_string() },
                result: res,
            }),
            None => Err("Inline text has insufficient tokens (< 2) for statistical watermark evaluation.".to_string()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_token_watermark_detector_basic() {
        let detector = TokenWatermarkDetector::new(0x5F3759DF, 0.50, 4.0);
        let token_stream = vec![101, 2054, 2003, 1037, 3231, 2005, 1037, 4001, 102];

        let result = detector.detect(&token_stream);
        assert!(result.is_some());
        let res = result.unwrap();
        assert_eq!(res.total_evaluated, 8);
        assert!(res.green_ratio >= 0.0 && res.green_ratio <= 1.0);
        assert_eq!(res.is_watermarked, res.z_score >= 4.0);
    }

    #[test]
    fn test_token_watermark_high_confidence() {
        let detector = TokenWatermarkDetector::new(0x5F3759DF, 0.50, 3.0);
        // Synthesize a sequence of 100 tokens that are all green
        let mut tokens = vec![100u32];
        for _ in 0..100 {
            let prev = *tokens.last().unwrap();
            let mut candidate = 1u32;
            while !detector.is_green_token(prev, candidate) {
                candidate += 1;
            }
            tokens.push(candidate);
        }

        let res = detector.detect(&tokens).expect("detection should succeed");
        assert_eq!(res.total_evaluated, 100);
        assert_eq!(res.green_count, 100);
        assert_eq!(res.green_ratio, 1.0);
        // z-score for 100/100 with gamma 0.5 is (100 - 50) / sqrt(100 * 0.25) = 50 / 5 = 10.0
        assert!((res.z_score - 10.0).abs() < 0.01);
        assert!(res.is_watermarked);
    }

    #[test]
    fn test_image_lsb_scanner() {
        use image::{Rgb, RgbImage};
        let mut img = RgbImage::new(10, 10);
        for pixel in img.pixels_mut() {
            *pixel = Rgb([100, 150, 200]); // all even LSBs (LSB = 0)
        }

        let scanner = ImageWatermarkScanner::new(0.9995);
        let dyn_img = image::DynamicImage::ImageRgb8(img);
        let analysis = scanner.analyze(&dyn_img);
        assert_eq!(analysis.total_samples, 300);
        // Since all bits are 0, entropy is 0.0
        assert_eq!(analysis.bit_entropy, 0.0);
        assert!(!analysis.is_anomalous);
    }

    #[test]
    fn test_detect_watermark_input_inline_text() {
        let text = "Artificial intelligence models generate synthetic text according to statistical probability distributions.";
        let res = detect_watermark_input(text);
        assert!(res.is_ok());
        if let Ok(WatermarkReport::Text { result, .. }) = res {
            assert!(result.total_evaluated > 5);
        } else {
            panic!("Expected Text watermark report");
        }
    }
}

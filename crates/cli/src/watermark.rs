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
        let analysis = match &img {
            image::DynamicImage::ImageLuma8(gray) => self.analyze(gray),
            image::DynamicImage::ImageLuma16(gray) => self.analyze(gray),
            image::DynamicImage::ImageLumaA8(gray) => self.analyze(gray),
            image::DynamicImage::ImageLumaA16(gray) => self.analyze(gray),
            _ => self.analyze(&img),
        };
        Ok(analysis)
    }

    pub fn scan_bytes(&self, bytes: &[u8]) -> Result<ImageLsbAnalysis, image::ImageError> {
        let img = image::load_from_memory(bytes)?;
        let analysis = match &img {
            image::DynamicImage::ImageLuma8(gray) => self.analyze(gray),
            image::DynamicImage::ImageLuma16(gray) => self.analyze(gray),
            image::DynamicImage::ImageLumaA8(gray) => self.analyze(gray),
            image::DynamicImage::ImageLumaA16(gray) => self.analyze(gray),
            _ => self.analyze(&img),
        };
        Ok(analysis)
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
        let sanitized_entropy = if entropy.abs() < 1e-12 { 0.0 } else { entropy };

        // Chi-Square goodness-of-fit against theoretical uniform noise distribution
        let expected = total_samples as f64 / 2.0;
        let chi_square = if expected > 0.0 {
            ((zero_bits as f64 - expected).powi(2) + (one_bits as f64 - expected).powi(2)) / expected
        } else {
            0.0
        };

        // Dense encrypted or pseudorandom watermarks push entropy extremely close to 1.0 (>= 0.999)
        let is_anomalous = sanitized_entropy >= self.entropy_threshold;

        ImageLsbAnalysis {
            total_samples,
            bit_entropy: sanitized_entropy,
            chi_square_stat: chi_square,
            is_anomalous,
        }
    }
}

/// Safely truncates a Unicode string to a maximum character count without splitting multi-byte UTF-8 boundaries.
pub fn safe_truncate(s: &str, max_chars: usize) -> String {
    let char_count = s.chars().count();
    if char_count > max_chars {
        let prefix: String = s.chars().take(max_chars.saturating_sub(3)).collect();
        format!("{}...", prefix)
    } else {
        s.to_string()
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
                let display_target = safe_truncate(target, 60);
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

    // Strip wrapping single or double quotes
    let unquoted = if (trimmed.starts_with('"') && trimmed.ends_with('"') && trimmed.len() >= 2)
        || (trimmed.starts_with('\'') && trimmed.ends_with('\'') && trimmed.len() >= 2)
    {
        &trimmed[1..trimmed.len() - 1]
    } else {
        trimmed
    };

    let path = Path::new(unquoted);
    let resolved_path = if path.is_file() {
        Some(path.to_path_buf())
    } else {
        let p1 = Path::new("..").join(unquoted);
        if p1.is_file() {
            Some(p1)
        } else {
            let p2 = Path::new("../..").join(unquoted);
            if p2.is_file() {
                Some(p2)
            } else {
                None
            }
        }
    };

    if let Some(target_path) = resolved_path {
        let ext = target_path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        if matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "webp" | "bmp" | "gif" | "tiff" | "ico") {
            let scanner = ImageWatermarkScanner::default();
            match scanner.scan_path(&target_path) {
                Ok(res) => Ok(WatermarkReport::Image {
                    target: unquoted.to_string(),
                    result: res,
                }),
                Err(e) => Err(format!("Failed to analyze image '{}': {}", unquoted, e)),
            }
        } else {
            // Read as text file
            match std::fs::read_to_string(&target_path) {
                Ok(content) => {
                    let detector = TokenWatermarkDetector::default();
                    match detector.detect_text(&content) {
                        Some(res) => Ok(WatermarkReport::Text {
                            target: format!("file: {}", unquoted),
                            result: res,
                        }),
                        None => Err(format!("File '{}' has insufficient tokens (< 2) for statistical watermark evaluation.", unquoted)),
                    }
                }
                Err(e) => Err(format!("Failed to read file '{}': {}", unquoted, e)),
            }
        }
    } else {
        // If it looks like a file path rather than inline prose, return an explicit error
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        let is_img_ext = matches!(ext.as_str(), "png" | "jpg" | "jpeg" | "webp" | "bmp" | "gif" | "tiff" | "ico");
        let is_doc_ext = matches!(ext.as_str(), "txt" | "md" | "json" | "rs" | "py" | "js" | "ts" | "html" | "css" | "csv" | "log");
        let has_path_sep = unquoted.contains('/') || unquoted.contains('\\');

        if is_img_ext {
            return Err(format!("Image file not found: '{}'", unquoted));
        } else if is_doc_ext || (has_path_sep && !unquoted.contains(' ')) {
            return Err(format!("File not found: '{}'", unquoted));
        }

        // Treat as inline text
        let detector = TokenWatermarkDetector::default();
        match detector.detect_text(unquoted) {
            Some(res) => Ok(WatermarkReport::Text {
                target: safe_truncate(unquoted, 40),
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

    #[test]
    fn test_missing_image_file_returns_error() {
        let res = detect_watermark_input("nonexistent_render_test.png");
        assert!(res.is_err());
        assert!(res.unwrap_err().contains("Image file not found"));

        let res_jpg = detect_watermark_input("sample_photo.jpeg");
        assert!(res_jpg.is_err());
        assert!(res_jpg.unwrap_err().contains("Image file not found"));
    }

    #[test]
    fn test_quoted_image_path() {
        let temp_dir = std::env::temp_dir();
        let temp_file = temp_dir.join("test_watermark_quoted.png");
        let img = image::RgbImage::new(16, 16);
        let _ = img.save(&temp_file);

        let path_str = temp_file.to_string_lossy().to_string();
        let quoted = format!("\"{}\"", path_str);
        let res = detect_watermark_input(&quoted);
        assert!(res.is_ok(), "Quoted path must be cleanly parsed and analyzed");
        if let Ok(WatermarkReport::Image { target, result }) = res {
            assert_eq!(target, path_str);
            assert!(result.total_samples > 0);
        } else {
            panic!("Expected Image watermark report for quoted path");
        }
        let _ = std::fs::remove_file(temp_file);
    }

    #[test]
    fn test_utf8_multibyte_string_truncation() {
        // Multi-byte Unicode: Emojis and Chinese characters
        let complex_unicode = "🌟🚀🤖 这是一个非常长的测试文本用于验证水印检测系统在处理多字节UTF-8字符时绝不发生边界恐慌与崩溃 🔍✨";
        let res = detect_watermark_input(complex_unicode);
        assert!(res.is_ok());
        if let Ok(report) = res {
            let md = report.to_markdown();
            assert!(!md.is_empty());
        }
    }

    #[test]
    fn test_synthetic_anomalous_lsb_watermark() {
        use image::{Rgb, RgbImage};
        let mut img = RgbImage::new(40, 40);
        // Interleave 0 and 1 LSBs evenly so p0 = 0.5, p1 = 0.5 -> maximal entropy 1.0
        let mut toggle = false;
        for pixel in img.pixels_mut() {
            let b0 = if toggle { 1u8 } else { 0u8 };
            let b1 = if !toggle { 1u8 } else { 0u8 };
            let b2 = if toggle { 1u8 } else { 0u8 };
            *pixel = Rgb([100 | b0, 150 | b1, 200 | b2]);
            toggle = !toggle;
        }

        let scanner = ImageWatermarkScanner::new(0.9995);
        let dyn_img = image::DynamicImage::ImageRgb8(img);
        let analysis = scanner.analyze(&dyn_img);
        assert_eq!(analysis.total_samples, 40 * 40 * 3);
        assert!((analysis.bit_entropy - 1.0).abs() < 0.001);
        assert!(analysis.is_anomalous, "Interleaved pseudo-random LSB noise must trigger steganography anomaly flag");
    }

    #[test]
    fn test_grayscale_image_lsb() {
        use image::GrayImage;
        let mut img = GrayImage::new(20, 20);
        for pixel in img.pixels_mut() {
            *pixel = image::Luma([128]); // LSB 0
        }
        let scanner = ImageWatermarkScanner::new(0.9995);
        let analysis = scanner.analyze(&img);
        assert_eq!(analysis.total_samples, 400); // 1 sample per pixel, not 3x duplicated
        assert_eq!(analysis.bit_entropy, 0.0);
    }
}

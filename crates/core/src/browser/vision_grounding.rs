//! Vision-Language grounding engine for locating UI elements from screenshots.
//!
//! Integrates multimodal vision models (e.g. `qwen2.5-vl`, `llama3.2-vision`, OpenVINO VLM)
//! with browser viewport coordinates to pinpoint visual interactive targets without relying
//! solely on DOM trees or text selectors.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Normalized bounding box coordinates for a visual element.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GroundingBox {
    /// Minimum y coordinate (normalized 0.0 to 1.0 or 0 to 1000).
    pub ymin: f32,
    /// Minimum x coordinate.
    pub xmin: f32,
    /// Maximum y coordinate.
    pub ymax: f32,
    /// Maximum x coordinate.
    pub xmax: f32,
    /// Detected label or semantic target description.
    pub label: String,
    /// Detection confidence score (0.0 to 1.0).
    pub confidence: f32,
}

impl GroundingBox {
    /// Computes absolute viewport pixel coordinates `(x, y)` at the center of the bounding box.
    pub fn center_pixel(&self, viewport_width: u32, viewport_height: u32) -> (f64, f64) {
        // Normalize coordinates to 0.0 - 1.0 if they are in 0 - 1000 scale
        let (y0, x0, y1, x1) = if self.ymax > 1.0 || self.xmax > 1.0 {
            (self.ymin / 1000.0, self.xmin / 1000.0, self.ymax / 1000.0, self.xmax / 1000.0)
        } else {
            (self.ymin, self.xmin, self.ymax, self.xmax)
        };

        let center_x = ((x0 + x1) / 2.0) as f64 * (viewport_width as f64);
        let center_y = ((y0 + y1) / 2.0) as f64 * (viewport_height as f64);

        (center_x.round(), center_y.round())
    }
}

/// The result of visual element grounding.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GroundingResult {
    /// The original natural language element target query.
    pub target_query: String,
    /// The resolved visual bounding box, if located.
    pub bounding_box: Option<GroundingBox>,
    /// Calculated center pixel coordinates `(x, y)` for clicking.
    pub click_coordinates: Option<(f64, f64)>,
    /// Raw textual response returned by the VLM.
    pub raw_model_response: String,
    /// The vision model utilized for grounding.
    pub model_used: String,
}

/// Vision grounding orchestrator communicating with local Ollama or OpenVINO vision endpoints.
#[derive(Debug, Clone)]
pub struct VisionGroundingEngine {
    pub endpoint: String,
    pub model: String,
    pub timeout_secs: u64,
}

impl Default for VisionGroundingEngine {
    fn default() -> Self {
        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        Self {
            endpoint,
            model: "qwen2.5-vl".to_string(),
            timeout_secs: 20,
        }
    }
}

impl VisionGroundingEngine {
    pub fn new(endpoint: impl Into<String>, model: impl Into<String>, timeout_secs: u64) -> Self {
        Self {
            endpoint: endpoint.into(),
            model: model.into(),
            timeout_secs,
        }
    }

    /// Locates an element within a screenshot base64 image and computes click coordinates.
    pub async fn locate_element(
        &self,
        screenshot_base64: &str,
        query: &str,
        viewport_width: u32,
        viewport_height: u32,
    ) -> Result<GroundingResult, String> {
        let prompt = format!(
            "You are a precise GUI grounding assistant. Locate the following element in the provided screenshot:\n\
             Target: \"{}\"\n\n\
             Return ONLY the normalized bounding box coordinates for the element in 0-1000 scale as JSON:\n\
             {{\"ymin\": <number>, \"xmin\": <number>, \"ymax\": <number>, \"xmax\": <number>}}\n\
             If the element is not visible, return {{\"error\": \"not_found\"}}.",
            query
        );

        let clean_b64 = if let Some(idx) = screenshot_base64.find("base64,") {
            &screenshot_base64[idx + 7..]
        } else {
            screenshot_base64
        };

        let request_payload = serde_json::json!({
            "model": self.model,
            "prompt": prompt,
            "images": [clean_b64],
            "stream": false,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        });

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(self.timeout_secs))
            .build()
            .map_err(|e| format!("Failed to create HTTP client for vision grounding: {}", e))?;

        let url = format!("{}/api/generate", self.endpoint.trim_end_matches('/'));

        let resp = client
            .post(&url)
            .json(&request_payload)
            .send()
            .await
            .map_err(|e| format!("Vision model request failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Vision model endpoint returned HTTP {}", resp.status()));
        }

        let resp_json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse vision response JSON: {}", e))?;

        let raw_text = resp_json
            .get("response")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();

        let bbox = Self::parse_box_from_response(&raw_text, query);
        let click_coords = bbox.as_ref().map(|b| b.center_pixel(viewport_width, viewport_height));

        Ok(GroundingResult {
            target_query: query.to_string(),
            bounding_box: bbox,
            click_coordinates: click_coords,
            raw_model_response: raw_text,
            model_used: self.model.clone(),
        })
    }

    /// Parses normalized coordinates from JSON, array, or Qwen-VL tag formats.
    pub fn parse_box_from_response(raw: &str, query: &str) -> Option<GroundingBox> {
        // Format 1: JSON object {"ymin": ..., "xmin": ..., "ymax": ..., "xmax": ...}
        let re_json = Regex::new(r#"\{[^{}]*"ymin"\s*:\s*([0-9.]+)[^{}]*"xmin"\s*:\s*([0-9.]+)[^{}]*"ymax"\s*:\s*([0-9.]+)[^{}]*"xmax"\s*:\s*([0-9.]+)[^{}]*\}"#).unwrap();
        if let Some(cap) = re_json.captures(raw) {
            let ymin = cap[1].parse::<f32>().ok()?;
            let xmin = cap[2].parse::<f32>().ok()?;
            let ymax = cap[3].parse::<f32>().ok()?;
            let xmax = cap[4].parse::<f32>().ok()?;
            return Some(GroundingBox {
                ymin,
                xmin,
                ymax,
                xmax,
                label: query.to_string(),
                confidence: 0.95,
            });
        }

        // Format 2: Array [ymin, xmin, ymax, xmax]
        let re_arr = Regex::new(r#"\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]"#).unwrap();
        if let Some(cap) = re_arr.captures(raw) {
            let ymin = cap[1].parse::<f32>().ok()?;
            let xmin = cap[2].parse::<f32>().ok()?;
            let ymax = cap[3].parse::<f32>().ok()?;
            let xmax = cap[4].parse::<f32>().ok()?;
            return Some(GroundingBox {
                ymin,
                xmin,
                ymax,
                xmax,
                label: query.to_string(),
                confidence: 0.90,
            });
        }

        // Format 3: Qwen2.5-VL <box>(ymin,xmin),(ymax,xmax)</box>
        let re_qwen = Regex::new(r#"<box>\s*\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)\s*,\s*\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)\s*</box>"#).unwrap();
        if let Some(cap) = re_qwen.captures(raw) {
            let ymin = cap[1].parse::<f32>().ok()?;
            let xmin = cap[2].parse::<f32>().ok()?;
            let ymax = cap[3].parse::<f32>().ok()?;
            let xmax = cap[4].parse::<f32>().ok()?;
            return Some(GroundingBox {
                ymin,
                xmin,
                ymax,
                xmax,
                label: query.to_string(),
                confidence: 0.92,
            });
        }

        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_json_box() {
        let raw = r#"Here is the location: {"ymin": 150, "xmin": 300, "ymax": 250, "xmax": 500}"#;
        let bbox = VisionGroundingEngine::parse_box_from_response(raw, "Search button").unwrap();
        assert_eq!(bbox.ymin, 150.0);
        assert_eq!(bbox.xmin, 300.0);
        assert_eq!(bbox.ymax, 250.0);
        assert_eq!(bbox.xmax, 500.0);

        let (cx, cy) = bbox.center_pixel(1920, 1080);
        // Normalized center: x = (300+500)/2000 = 0.40, y = (150+250)/2000 = 0.20
        // Pixel: x = 0.40 * 1920 = 768, y = 0.20 * 1080 = 216
        assert_eq!(cx, 768.0);
        assert_eq!(cy, 216.0);
    }

    #[test]
    fn test_parse_array_box() {
        let raw = "The bounding box is [100.0, 200.0, 300.0, 400.0].";
        let bbox = VisionGroundingEngine::parse_box_from_response(raw, "Logo").unwrap();
        assert_eq!(bbox.ymin, 100.0);
        assert_eq!(bbox.xmin, 200.0);
        assert_eq!(bbox.ymax, 300.0);
        assert_eq!(bbox.xmax, 400.0);
    }
}

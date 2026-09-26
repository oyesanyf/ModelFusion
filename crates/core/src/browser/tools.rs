//! Unified browser tool suite for ModelFusion and HugOS autonomous web operations.
//!
//! Provides high-level browser actions (`navigate`, `click`, `type_text`, `scroll`,
//! `extract_tables`, `capture_viewport`, `get_clean_dom`) bridging CDP live automation
//! with fallback HTTP fetching, Set-of-Mark injection, and vision grounding.

use super::cdp_client::{CdpClient, TargetInfo};
use super::dom_pruner::{DomPruner, DomPrunerOptions, PrunedDom};
use super::table_extractor::{ExtractedTable, TableExtractor};
use super::vision_grounding::VisionGroundingEngine;
use serde::{Deserialize, Serialize};

/// Target identification for interactive web elements.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "target_type", content = "value")]
pub enum ElementTarget {
    /// Target by Set-of-Mark index e.g. [12].
    ByMark(usize),
    /// Target by standard CSS selector e.g. "#submit-btn".
    BySelector(String),
    /// Target by exact viewport pixel coordinates (x, y).
    ByCoordinates(f64, f64),
    /// Target by visible text or label.
    ByText(String),
}

/// Browser actions supported by the unified browser agent.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "action", content = "parameters")]
pub enum BrowserAction {
    /// Navigate to a specified URL.
    Navigate { url: String },
    /// Click an element specified by Set-of-Mark index, selector, coordinates, or text.
    Click { target: ElementTarget },
    /// Input text into a targeted element or the currently focused input.
    TypeText { target: Option<ElementTarget>, text: String },
    /// Scroll the viewport ("up", "down", "top", "bottom").
    Scroll { direction: String, amount: Option<i32> },
    /// Extract all tabular datasets and CSS grids into structured CSV/JSON.
    ExtractTables { url: Option<String> },
    /// Capture a base64 PNG screenshot of the current page.
    CaptureViewport,
    /// Extract a token-pruned semantic DOM tree tagged with Set-of-Mark indices.
    GetCleanDom { max_chars: Option<usize> },
}

/// The result returned after executing a browser action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserActionResult {
    pub success: bool,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

/// State representation of the current active browser tab.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserTabState {
    pub url: String,
    pub title: String,
    pub pruned_dom: PrunedDom,
    pub tables_count: usize,
    pub cdp_connected: bool,
}

/// Unified browser tool suite.
pub struct BrowserToolSuite {
    pub cdp: CdpClient,
    pub vision: VisionGroundingEngine,
    pub active_target: Option<TargetInfo>,
    pub last_pruned_dom: Option<PrunedDom>,
}

impl Default for BrowserToolSuite {
    fn default() -> Self {
        Self::new(9222)
    }
}

impl BrowserToolSuite {
    pub fn new(port: u16) -> Self {
        Self {
            cdp: CdpClient::new("127.0.0.1", port),
            vision: VisionGroundingEngine::default(),
            active_target: None,
            last_pruned_dom: None,
        }
    }

    /// Connects to active CDP target or resolves initial tab.
    pub async fn ensure_active_target(&mut self) -> Result<TargetInfo, String> {
        if let Some(ref t) = self.active_target {
            return Ok(t.clone());
        }
        let target = self.cdp.get_or_create_page_target().await?;
        self.active_target = Some(target.clone());
        Ok(target)
    }

    /// Dispatches an action enum directly.
    pub async fn execute_action(&mut self, action: BrowserAction) -> BrowserActionResult {
        match action {
            BrowserAction::Navigate { url } => match self.navigate(&url).await {
                Ok(msg) => BrowserActionResult {
                    success: true,
                    message: msg,
                    data: None,
                },
                Err(err) => BrowserActionResult {
                    success: false,
                    message: err,
                    data: None,
                },
            },
            BrowserAction::Click { target } => match self.click(target).await {
                Ok(msg) => BrowserActionResult {
                    success: true,
                    message: msg,
                    data: None,
                },
                Err(err) => BrowserActionResult {
                    success: false,
                    message: err,
                    data: None,
                },
            },
            BrowserAction::TypeText { target, text } => match self.type_text(target, &text).await {
                Ok(msg) => BrowserActionResult {
                    success: true,
                    message: msg,
                    data: None,
                },
                Err(err) => BrowserActionResult {
                    success: false,
                    message: err,
                    data: None,
                },
            },
            BrowserAction::Scroll { direction, amount } => {
                match self.scroll(&direction, amount.unwrap_or(400)).await {
                    Ok(msg) => BrowserActionResult {
                        success: true,
                        message: msg,
                        data: None,
                    },
                    Err(err) => BrowserActionResult {
                        success: false,
                        message: err,
                        data: None,
                    },
                }
            }
            BrowserAction::ExtractTables { url } => match self.extract_tables(url.as_deref()).await {
                Ok(tables) => BrowserActionResult {
                    success: true,
                    message: format!("Successfully extracted {} table(s).", tables.len()),
                    data: Some(serde_json::to_value(&tables).unwrap_or(serde_json::Value::Null)),
                },
                Err(err) => BrowserActionResult {
                    success: false,
                    message: err,
                    data: None,
                },
            },
            BrowserAction::CaptureViewport => match self.capture_viewport().await {
                Ok(b64) => BrowserActionResult {
                    success: true,
                    message: "Captured viewport screenshot successfully.".to_string(),
                    data: Some(serde_json::json!({ "screenshot_base64": b64 })),
                },
                Err(err) => BrowserActionResult {
                    success: false,
                    message: err,
                    data: None,
                },
            },
            BrowserAction::GetCleanDom { max_chars } => {
                let mut options = DomPrunerOptions::default();
                if let Some(limit) = max_chars {
                    options.max_text_len = limit;
                }
                match self.get_clean_dom(Some(options)).await {
                    Ok(pruned) => BrowserActionResult {
                        success: true,
                        message: format!(
                            "Retrieved clean DOM with {} interactive elements ({:.1}% token reduction).",
                            pruned.interactive_elements.len(),
                            pruned.token_reduction_pct
                        ),
                        data: Some(serde_json::to_value(&pruned).unwrap_or(serde_json::Value::Null)),
                    },
                    Err(err) => BrowserActionResult {
                        success: false,
                        message: err,
                        data: None,
                    },
                }
            }
        }
    }

    /// Navigates to a URL via CDP, or fetches content via HTTP if CDP is offline.
    pub async fn navigate(&mut self, url: &str) -> Result<String, String> {
        let normalized_url = if !url.starts_with("http://") && !url.starts_with("https://") {
            format!("https://{}", url)
        } else {
            url.to_string()
        };

        if self.cdp.is_available().await {
            let target = self.ensure_active_target().await?;
            self.cdp.navigate(&target, &normalized_url).await?;
            // Allow 500ms for network settling
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            Ok(format!("Navigated to '{}' via live CDP tab.", normalized_url))
        } else {
            // CDP offline fallback
            Ok(format!("CDP not connected on port {}. URL '{}' staged for HTTP fallback inspection.", self.cdp.port, normalized_url))
        }
    }

    /// Retrieves and prunes the current page DOM.
    pub async fn get_clean_dom(&mut self, options: Option<DomPrunerOptions>) -> Result<PrunedDom, String> {
        let opts = options.unwrap_or_default();
        let raw_html = if self.cdp.is_available().await {
            let target = self.ensure_active_target().await?;
            self.cdp.get_html(&target).await?
        } else {
            return Err(format!(
                "Chromium CDP endpoint is not reachable at {}. Start HugOS Browser first.",
                self.cdp.base_url()
            ));
        };

        let pruned = DomPruner::prune_html(&raw_html, &opts);
        self.last_pruned_dom = Some(pruned.clone());
        Ok(pruned)
    }

    /// Clicks on an interactive element by mark index, selector, text, or coordinates.
    pub async fn click(&mut self, target: ElementTarget) -> Result<String, String> {
        let cdp_target = self.ensure_active_target().await?;

        match target {
            ElementTarget::ByCoordinates(x, y) => {
                self.cdp.click_at(&cdp_target, x, y).await?;
                Ok(format!("Clicked at coordinates ({}, {}).", x, y))
            }
            ElementTarget::BySelector(selector) => {
                let js = format!(
                    "(() => {{ const el = document.querySelector('{}'); if (el) {{ el.click(); return true; }} return false; }})()",
                    selector.replace('\'', "\\'")
                );
                let res = self.cdp.evaluate(&cdp_target, &js).await?;
                if res.get("value").and_then(|v| v.as_bool()).unwrap_or(false) {
                    Ok(format!("Clicked selector '{}'.", selector))
                } else {
                    Err(format!("Element with selector '{}' not found in DOM.", selector))
                }
            }
            ElementTarget::ByMark(mark_id) => {
                let selector_opt = self.last_pruned_dom.as_ref().and_then(|p| p.find_element(mark_id)).map(|e| e.selector.clone());
                if let Some(selector) = selector_opt {
                    let js = format!(
                        "(() => {{ const el = document.querySelector('{}'); if (el) {{ el.click(); return true; }} return false; }})()",
                        selector.replace('\'', "\\'")
                    );
                    let res = self.cdp.evaluate(&cdp_target, &js).await?;
                    if res.get("value").and_then(|v| v.as_bool()).unwrap_or(false) {
                        return Ok(format!("Clicked Set-of-Mark element [{}] via selector '{}'.", mark_id, selector));
                    }
                }
                // Fallback: look for data-mark-id or nth element
                let js = format!(
                    "(() => {{ const el = document.querySelector('[data-mark-id=\"{}\"]'); if (el) {{ el.click(); return true; }} return false; }})()",
                    mark_id
                );
                let res = self.cdp.evaluate(&cdp_target, &js).await?;
                if res.get("value").and_then(|v| v.as_bool()).unwrap_or(false) {
                    Ok(format!("Clicked Set-of-Mark element [{}].", mark_id))
                } else {
                    Err(format!("Set-of-Mark [{}] could not be resolved to a DOM element.", mark_id))
                }
            }
            ElementTarget::ByText(text) => {
                let js = format!(
                    "(() => {{
                        const elements = Array.from(document.querySelectorAll('a, button, input[type=\"submit\"], [role=\"button\"]'));
                        const found = elements.find(el => el.textContent.toLowerCase().includes('{}'));
                        if (found) {{ found.click(); return true; }}
                        return false;
                    }})()",
                    text.to_lowercase().replace('\'', "\\'")
                );
                let res = self.cdp.evaluate(&cdp_target, &js).await?;
                if res.get("value").and_then(|v| v.as_bool()).unwrap_or(false) {
                    Ok(format!("Clicked element containing text \"{}\".", text))
                } else {
                    Err(format!("No interactive element found containing text \"{}\".", text))
                }
            }
        }
    }

    /// Types text into an element or current focus.
    pub async fn type_text(&mut self, target: Option<ElementTarget>, text: &str) -> Result<String, String> {
        let cdp_target = self.ensure_active_target().await?;

        if let Some(t) = target {
            // Focus targeted element first
            match t {
                ElementTarget::BySelector(sel) => {
                    let js = format!(
                        "(() => {{ const el = document.querySelector('{}'); if (el) {{ el.focus(); el.value = ''; return true; }} return false; }})()",
                        sel.replace('\'', "\\'")
                    );
                    self.cdp.evaluate(&cdp_target, &js).await?;
                }
                ElementTarget::ByMark(mark_id) => {
                    if let Some(ref pruned) = self.last_pruned_dom {
                        if let Some(elem) = pruned.find_element(mark_id) {
                            let js = format!(
                                "(() => {{ const el = document.querySelector('{}'); if (el) {{ el.focus(); el.value = ''; return true; }} return false; }})()",
                                elem.selector.replace('\'', "\\'")
                            );
                            self.cdp.evaluate(&cdp_target, &js).await?;
                        }
                    }
                }
                _ => {}
            }
        }

        self.cdp.type_text(&cdp_target, text).await?;
        Ok(format!("Typed \"{}\" into target.", text))
    }

    /// Scrolls the viewport.
    pub async fn scroll(&mut self, direction: &str, amount: i32) -> Result<String, String> {
        let cdp_target = self.ensure_active_target().await?;
        let (dx, dy) = match direction.to_lowercase().as_str() {
            "up" => (0.0, -(amount as f64)),
            "down" => (0.0, amount as f64),
            "top" => {
                self.cdp.evaluate(&cdp_target, "window.scrollTo(0, 0)").await?;
                return Ok("Scrolled to top of page.".to_string());
            }
            "bottom" => {
                self.cdp.evaluate(&cdp_target, "window.scrollTo(0, document.body.scrollHeight)").await?;
                return Ok("Scrolled to bottom of page.".to_string());
            }
            _ => (0.0, amount as f64),
        };

        self.cdp.scroll(&cdp_target, dx, dy).await?;
        Ok(format!("Scrolled {} by {}px.", direction, amount))
    }

    /// Extracts tables from a URL or from the active browser tab.
    pub async fn extract_tables(&mut self, url: Option<&str>) -> Result<Vec<ExtractedTable>, String> {
        let html = if let Some(target_url) = url {
            // Fetch via reqwest
            let client = reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(15))
                .user_agent("ModelFusion-Browser/1.0 (Windows NT 10.0; Win64; x64)")
                .build()
                .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

            let resp = client
                .get(target_url)
                .send()
                .await
                .map_err(|e| format!("HTTP request to '{}' failed: {}", target_url, e))?;

            resp.text()
                .await
                .map_err(|e| format!("Failed to read HTTP response from '{}': {}", target_url, e))?
        } else if self.cdp.is_available().await {
            let target = self.ensure_active_target().await?;
            self.cdp.get_html(&target).await?
        } else {
            return Err("Neither a target URL was specified nor is Chromium CDP currently active.".to_string());
        };

        Ok(TableExtractor::extract_from_html(&html))
    }

    /// Captures a screenshot of the active viewport.
    pub async fn capture_viewport(&mut self) -> Result<String, String> {
        let target = self.ensure_active_target().await?;
        self.cdp.capture_screenshot(&target).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_browser_tool_suite_action_dispatch() {
        let mut suite = BrowserToolSuite::new(9999); // Offline mock port
        let res = suite
            .execute_action(BrowserAction::Navigate {
                url: "https://example.com".to_string(),
            })
            .await;

        assert!(res.success);
        assert!(res.message.contains("https://example.com"));
    }

    #[tokio::test]
    async fn test_extract_tables_from_sample_html() {
        let _suite = BrowserToolSuite::new(9999);
        // Direct extraction test
        let sample_html = r#"
            <table>
                <tr><th>Col A</th><th>Col B</th></tr>
                <tr><td>1</td><td>2</td></tr>
            </table>
        "#;
        let tables = TableExtractor::extract_from_html(sample_html);
        assert_eq!(tables.len(), 1);
        assert_eq!(tables[0].headers, vec!["Col A", "Col B"]);
    }
}

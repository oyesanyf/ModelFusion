//! Async Chrome DevTools Protocol (CDP) client communicating over HTTP and WebSockets.
//!
//! Connects to Chromium instances launched with `--remote-debugging-port=<port>` (default 9222),
//! querying active targets, creating/closing tabs, executing DOM/JavaScript commands, capturing
//! viewports, and dispatching keyboard/mouse inputs.

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;

/// Information regarding an active Chromium target (page tab, iframe, service worker).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TargetInfo {
    pub id: String,
    pub title: String,
    #[serde(rename = "type")]
    pub target_type: String,
    pub url: String,
    #[serde(rename = "webSocketDebuggerUrl")]
    pub web_socket_debugger_url: Option<String>,
}

/// CDP response wrapper.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CdpResponse {
    pub id: u64,
    pub result: Option<serde_json::Value>,
    pub error: Option<serde_json::Value>,
}

/// Chrome DevTools Protocol client.
pub struct CdpClient {
    pub port: u16,
    pub host: String,
    req_counter: AtomicU64,
    http_client: reqwest::Client,
}

impl Default for CdpClient {
    fn default() -> Self {
        Self::new("127.0.0.1", 9222)
    }
}

impl CdpClient {
    pub fn new(host: impl Into<String>, port: u16) -> Self {
        let http_client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap_or_default();
        Self {
            host: host.into(),
            port,
            req_counter: AtomicU64::new(1),
            http_client,
        }
    }

    /// Base HTTP endpoint for the Chromium debugging instance.
    pub fn base_url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }

    /// Checks whether the Chromium remote debugging endpoint is responsive.
    pub async fn is_available(&self) -> bool {
        let url = format!("{}/json/version", self.base_url());
        match self.http_client.get(&url).send().await {
            Ok(resp) => resp.status().is_success(),
            Err(_) => false,
        }
    }

    /// Queries the browser version and metadata.
    pub async fn get_version(&self) -> Result<serde_json::Value, String> {
        let url = format!("{}/json/version", self.base_url());
        let resp = self
            .http_client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to connect to CDP at {}: {}", url, e))?;
        resp.json::<serde_json::Value>()
            .await
            .map_err(|e| format!("Failed to parse CDP version JSON: {}", e))
    }

    /// Lists all active browser targets.
    pub async fn list_targets(&self) -> Result<Vec<TargetInfo>, String> {
        let url = format!("{}/json/list", self.base_url());
        let resp = self
            .http_client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to list CDP targets at {}: {}", url, e))?;
        resp.json::<Vec<TargetInfo>>()
            .await
            .map_err(|e| format!("Failed to parse CDP targets JSON: {}", e))
    }

    /// Returns the primary active page target, or creates a new tab if none exist.
    pub async fn get_or_create_page_target(&self) -> Result<TargetInfo, String> {
        let targets = self.list_targets().await?;
        if let Some(target) = targets.into_iter().find(|t| t.target_type == "page") {
            return Ok(target);
        }
        self.create_target("about:blank").await
    }

    /// Creates a new browser tab navigating to the specified URL.
    pub async fn create_target(&self, url: &str) -> Result<TargetInfo, String> {
        let endpoint = format!("{}/json/new?{}", self.base_url(), url);
        let resp = self
            .http_client
            .put(&endpoint)
            .send()
            .await
            .map_err(|e| format!("Failed to create new CDP target at {}: {}", endpoint, e))?;
        resp.json::<TargetInfo>()
            .await
            .map_err(|e| format!("Failed to parse new target JSON: {}", e))
    }

    /// Activates (brings to front) the target tab.
    pub async fn activate_target(&self, target_id: &str) -> Result<(), String> {
        let endpoint = format!("{}/json/activate/{}", self.base_url(), target_id);
        let resp = self
            .http_client
            .get(&endpoint)
            .send()
            .await
            .map_err(|e| format!("Failed to activate target {}: {}", target_id, e))?;
        if resp.status().is_success() {
            Ok(())
        } else {
            Err(format!("Activate target returned HTTP {}", resp.status()))
        }
    }

    /// Closes the specified target tab.
    pub async fn close_target(&self, target_id: &str) -> Result<(), String> {
        let endpoint = format!("{}/json/close/{}", self.base_url(), target_id);
        let resp = self
            .http_client
            .get(&endpoint)
            .send()
            .await
            .map_err(|e| format!("Failed to close target {}: {}", target_id, e))?;
        if resp.status().is_success() {
            Ok(())
        } else {
            Err(format!("Close target returned HTTP {}", resp.status()))
        }
    }

    /// Sends a low-level CDP JSON-RPC command over WebSocket to the specified target.
    pub async fn send_command(
        &self,
        target: &TargetInfo,
        method: &str,
        params: serde_json::Value,
    ) -> Result<serde_json::Value, String> {
        let ws_url = target
            .web_socket_debugger_url
            .as_deref()
            .ok_or_else(|| format!("Target '{}' has no webSocketDebuggerUrl", target.id))?;

        let req_id = self.req_counter.fetch_add(1, Ordering::SeqCst);
        let payload = serde_json::json!({
            "id": req_id,
            "method": method,
            "params": params
        });

        let payload_str = payload.to_string();

        // Connect and dispatch over RFC 6455 WebSocket
        let response_str = tokio::time::timeout(
            Duration::from_secs(10),
            Self::execute_ws_transaction(&self.host, self.port, ws_url, req_id, &payload_str),
        )
        .await
        .map_err(|_| format!("CDP command '{}' timed out after 10s", method))??;

        let parsed: CdpResponse = serde_json::from_str(&response_str)
            .map_err(|e| format!("Failed to parse CDP response JSON: {}. Raw: {}", e, response_str))?;

        if let Some(err) = parsed.error {
            return Err(format!("CDP error for {}: {}", method, err));
        }

        Ok(parsed.result.unwrap_or(serde_json::Value::Null))
    }

    /// Internal RFC-6455 single-transaction WebSocket client.
    async fn execute_ws_transaction(
        host: &str,
        port: u16,
        ws_url: &str,
        expected_id: u64,
        payload: &str,
    ) -> Result<String, String> {
        let path = if let Some(idx) = ws_url.find(&format!("{}:{}/", host, port)) {
            &ws_url[idx + format!("{}:{}/", host, port).len() - 1..]
        } else if let Some(idx) = ws_url.find("/devtools/") {
            &ws_url[idx..]
        } else {
            "/devtools/page"
        };

        let mut stream = TcpStream::connect((host, port))
            .await
            .map_err(|e| format!("Failed to connect to CDP socket at {}:{}: {}", host, port, e))?;

        // 1. Send WebSocket Upgrade handshake
        let handshake = format!(
            "GET {} HTTP/1.1\r\n\
             Host: {}:{}\r\n\
             Upgrade: websocket\r\n\
             Connection: Upgrade\r\n\
             Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\
             Sec-WebSocket-Version: 13\r\n\r\n",
            path, host, port
        );

        stream
            .write_all(handshake.as_bytes())
            .await
            .map_err(|e| format!("Handshake write failed: {}", e))?;

        // 2. Read handshake response
        let mut buffer = [0u8; 4096];
        let mut handshake_read = 0;
        let mut header_complete = false;

        while handshake_read < buffer.len() {
            let n = stream
                .read(&mut buffer[handshake_read..])
                .await
                .map_err(|e| format!("Handshake read failed: {}", e))?;
            if n == 0 {
                return Err("CDP socket closed during handshake".to_string());
            }
            handshake_read += n;
            let resp_str = String::from_utf8_lossy(&buffer[..handshake_read]);
            if resp_str.contains("\r\n\r\n") {
                if !resp_str.starts_with("HTTP/1.1 101") {
                    return Err(format!("Invalid WebSocket handshake response: {}", resp_str));
                }
                header_complete = true;
                break;
            }
        }

        if !header_complete {
            return Err("Incomplete WebSocket handshake from CDP server".to_string());
        }

        // 3. Send masked client frame with text payload
        let payload_bytes = payload.as_bytes();
        let mut frame = Vec::new();
        frame.push(0x81); // FIN + Opcode 1 (text)

        let len = payload_bytes.len();
        if len <= 125 {
            frame.push(0x80 | (len as u8));
        } else if len <= 65535 {
            frame.push(0x80 | 126);
            frame.extend_from_slice(&(len as u16).to_be_bytes());
        } else {
            frame.push(0x80 | 127);
            frame.extend_from_slice(&(len as u64).to_be_bytes());
        }

        let mask: [u8; 4] = [0x54, 0x67, 0x89, 0xAB];
        frame.extend_from_slice(&mask);

        for (i, &b) in payload_bytes.iter().enumerate() {
            frame.push(b ^ mask[i % 4]);
        }

        stream
            .write_all(&frame)
            .await
            .map_err(|e| format!("Frame write failed: {}", e))?;

        // 4. Read incoming WebSocket frames until we get the response for expected_id
        let mut incoming = Vec::new();
        let mut read_buf = [0u8; 8192];

        loop {
            let n = stream
                .read(&mut read_buf)
                .await
                .map_err(|e| format!("Frame read failed: {}", e))?;
            if n == 0 {
                break;
            }
            incoming.extend_from_slice(&read_buf[..n]);

            // Attempt decoding frames from incoming buffer
            if let Some(decoded_text) = Self::try_decode_ws_text_frame(&mut incoming) {
                if decoded_text.contains(&format!("\"id\":{}", expected_id))
                    || decoded_text.contains(&format!("\"id\": {}", expected_id))
                {
                    return Ok(decoded_text);
                }
            }
        }

        Err("Connection ended before receiving CDP response".to_string())
    }

    /// Decodes a server-to-client RFC-6455 unmasked text frame.
    fn try_decode_ws_text_frame(buffer: &mut Vec<u8>) -> Option<String> {
        if buffer.len() < 2 {
            return None;
        }

        let _fin = (buffer[0] & 0x80) != 0;
        let opcode = buffer[0] & 0x0F;
        let masked = (buffer[1] & 0x80) != 0;
        let mut payload_len = (buffer[1] & 0x7F) as usize;
        let mut offset = 2;

        if payload_len == 126 {
            if buffer.len() < 4 {
                return None;
            }
            payload_len = u16::from_be_bytes([buffer[2], buffer[3]]) as usize;
            offset = 4;
        } else if payload_len == 127 {
            if buffer.len() < 10 {
                return None;
            }
            payload_len = u64::from_be_bytes([
                buffer[2], buffer[3], buffer[4], buffer[5], buffer[6], buffer[7], buffer[8],
                buffer[9],
            ]) as usize;
            offset = 10;
        }

        if masked {
            offset += 4;
        }

        if buffer.len() < offset + payload_len {
            return None;
        }

        let payload = buffer[offset..offset + payload_len].to_vec();
        // Drain processed frame from buffer
        buffer.drain(..offset + payload_len);

        if opcode == 1 {
            String::from_utf8(payload).ok()
        } else {
            None
        }
    }

    // High-Level Browser Control Helpers

    /// Navigates the target tab to a URL.
    pub async fn navigate(&self, target: &TargetInfo, url: &str) -> Result<String, String> {
        let res = self
            .send_command(target, "Page.navigate", serde_json::json!({ "url": url }))
            .await?;
        let frame_id = res
            .get("frameId")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        Ok(frame_id)
    }

    /// Evaluates JavaScript code on the target tab and returns the result value.
    pub async fn evaluate(&self, target: &TargetInfo, script: &str) -> Result<serde_json::Value, String> {
        let res = self
            .send_command(
                target,
                "Runtime.evaluate",
                serde_json::json!({
                    "expression": script,
                    "returnByValue": true,
                    "awaitPromise": true
                }),
            )
            .await?;

        Ok(res.get("result").cloned().unwrap_or(serde_json::Value::Null))
    }

    /// Retrieves the full outer HTML of the document.
    pub async fn get_html(&self, target: &TargetInfo) -> Result<String, String> {
        let res = self
            .evaluate(target, "document.documentElement.outerHTML")
            .await?;
        Ok(res.get("value").and_then(|v| v.as_str()).unwrap_or("").to_string())
    }

    /// Retrieves the current document title.
    pub async fn get_title(&self, target: &TargetInfo) -> Result<String, String> {
        let res = self.evaluate(target, "document.title").await?;
        Ok(res.get("value").and_then(|v| v.as_str()).unwrap_or("").to_string())
    }

    /// Captures a viewport screenshot encoded as base64 PNG.
    pub async fn capture_screenshot(&self, target: &TargetInfo) -> Result<String, String> {
        let res = self
            .send_command(
                target,
                "Page.captureScreenshot",
                serde_json::json!({ "format": "png", "quality": 90 }),
            )
            .await?;

        res.get("data")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| "Missing 'data' in Page.captureScreenshot response".to_string())
    }

    /// Dispatches mouse click event sequence (mousePressed followed by mouseReleased) at pixel coordinates.
    pub async fn click_at(&self, target: &TargetInfo, x: f64, y: f64) -> Result<(), String> {
        // Press
        self.send_command(
            target,
            "Input.dispatchMouseEvent",
            serde_json::json!({
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }),
        )
        .await?;

        // Release
        self.send_command(
            target,
            "Input.dispatchMouseEvent",
            serde_json::json!({
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1
            }),
        )
        .await?;

        Ok(())
    }

    /// Dispatches text input into the currently focused element.
    pub async fn type_text(&self, target: &TargetInfo, text: &str) -> Result<(), String> {
        self.send_command(
            target,
            "Input.insertText",
            serde_json::json!({
                "text": text
            }),
        )
        .await?;

        Ok(())
    }

    /// Dispatches mouse wheel scroll events.
    pub async fn scroll(&self, target: &TargetInfo, delta_x: f64, delta_y: f64) -> Result<(), String> {
        self.send_command(
            target,
            "Input.dispatchMouseEvent",
            serde_json::json!({
                "type": "mouseWheel",
                "x": 200.0,
                "y": 200.0,
                "deltaX": delta_x,
                "deltaY": delta_y
            }),
        )
        .await?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cdp_client_initialization() {
        let client = CdpClient::new("127.0.0.1", 9222);
        assert_eq!(client.base_url(), "http://127.0.0.1:9222");
    }

    #[test]
    fn test_decode_ws_text_frame() {
        let message = r#"{"id":1,"result":{"value":"ok"}}"#;
        let mut frame = Vec::new();
        frame.push(0x81); // FIN + text
        frame.push(message.len() as u8);
        frame.extend_from_slice(message.as_bytes());

        let decoded = CdpClient::try_decode_ws_text_frame(&mut frame);
        assert_eq!(decoded, Some(message.to_string()));
        assert!(frame.is_empty());
    }
}

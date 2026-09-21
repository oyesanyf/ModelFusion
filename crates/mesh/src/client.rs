//! Encrypted mTLS Mesh Client for Dispatching Remote Workloads

use crate::peer::MeshNodeInfo;
use crate::rpc::{
    ArbitrateTaskRequest, ArbitrateTaskResponse, NodeStatusResponse, RestRlTaskRequest,
    RestRlTaskResponse,
};
use crate::tls::MeshIdentity;
use anyhow::{anyhow, Context, Result};
use rustls::pki_types::ServerName;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::time::timeout;

#[derive(Clone)]
pub struct MeshClient {
    identity: MeshIdentity,
    timeout_duration: Duration,
}

impl MeshClient {
    pub fn new(identity: MeshIdentity) -> Self {
        Self {
            identity,
            timeout_duration: Duration::from_secs(15),
        }
    }

    pub fn with_timeout(mut self, duration: Duration) -> Self {
        self.timeout_duration = duration;
        self
    }

    /// Query node status and telemetry over mTLS.
    pub async fn query_status(&self, peer: &MeshNodeInfo) -> Result<NodeStatusResponse> {
        let fp = if peer.tls_fingerprint.is_empty() {
            None
        } else {
            Some(peer.tls_fingerprint.as_str())
        };
        let resp_bytes = self
            .send_request(&peer.ip, peer.port, "GET", "/mesh/node/status", &[], fp)
            .await?;
        let res: NodeStatusResponse = serde_json::from_slice(&resp_bytes)
            .with_context(|| "Failed to parse NodeStatusResponse from peer")?;
        Ok(res)
    }

    /// Offload multi-model candidate arbitration to remote LAN workstation.
    pub async fn offload_arbitration(
        &self,
        peer: &MeshNodeInfo,
        req: &ArbitrateTaskRequest,
    ) -> Result<ArbitrateTaskResponse> {
        let body = serde_json::to_vec(req)?;
        let fp = if peer.tls_fingerprint.is_empty() {
            None
        } else {
            Some(peer.tls_fingerprint.as_str())
        };
        let resp_bytes = self
            .send_request(&peer.ip, peer.port, "POST", "/mesh/tasks/arbitrate", &body, fp)
            .await?;
        let res: ArbitrateTaskResponse = serde_json::from_slice(&resp_bytes)
            .with_context(|| "Failed to parse ArbitrateTaskResponse from peer")?;
        Ok(res)
    }

    /// Offload ReST-RL compute sweep or candidate generation to remote LAN workstation.
    pub async fn offload_rest_rl(
        &self,
        peer: &MeshNodeInfo,
        req: &RestRlTaskRequest,
    ) -> Result<RestRlTaskResponse> {
        let body = serde_json::to_vec(req)?;
        let fp = if peer.tls_fingerprint.is_empty() {
            None
        } else {
            Some(peer.tls_fingerprint.as_str())
        };
        let resp_bytes = self
            .send_request(&peer.ip, peer.port, "POST", "/mesh/tasks/rest-rl", &body, fp)
            .await?;
        let res: RestRlTaskResponse = serde_json::from_slice(&resp_bytes)
            .with_context(|| "Failed to parse RestRlTaskResponse from peer")?;
        Ok(res)
    }

    async fn send_request(
        &self,
        ip: &str,
        port: u16,
        method: &str,
        path: &str,
        body: &[u8],
        expected_fingerprint: Option<&str>,
    ) -> Result<Vec<u8>> {
        let connector = self.identity.build_tls_connector(expected_fingerprint)?;
        let addr = format!("{}:{}", ip, port);

        let tcp_stream = timeout(Duration::from_secs(5), TcpStream::connect(&addr))
            .await
            .map_err(|_| anyhow!("Connection to peer {} timed out", addr))?
            .with_context(|| format!("Failed to connect to peer TCP at {}", addr))?;

        let server_name = ServerName::try_from("localhost".to_string())
            .map_err(|e| anyhow!("Invalid server name: {:?}", e))?;

        let mut tls_stream = timeout(Duration::from_secs(5), connector.connect(server_name, tcp_stream))
            .await
            .map_err(|_| anyhow!("TLS handshake with peer {} timed out", addr))?
            .with_context(|| format!("Failed TLS handshake with {}", addr))?;

        let req_header = format!(
            "{} {} HTTP/1.1\r\nHost: {}:{}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            method,
            path,
            ip,
            port,
            body.len()
        );

        tls_stream.write_all(req_header.as_bytes()).await?;
        if !body.is_empty() {
            tls_stream.write_all(body).await?;
        }
        tls_stream.flush().await?;

        // Read response
        let mut resp_data = Vec::new();
        let mut buf = [0u8; 4096];
        loop {
            let n = timeout(self.timeout_duration, tls_stream.read(&mut buf))
                .await
                .map_err(|_| anyhow!("Peer response timed out"))?
                .unwrap_or(0);
            if n == 0 {
                break;
            }
            resp_data.extend_from_slice(&buf[..n]);
        }

        // Parse HTTP header & body
        if let Some(pos) = find_subsequence(&resp_data, b"\r\n\r\n") {
            let header_str = std::str::from_utf8(&resp_data[..pos]).unwrap_or("");
            let status_code = header_str
                .lines()
                .next()
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<u16>().ok())
                .unwrap_or(500);

            let body_bytes = &resp_data[pos + 4..];
            if status_code == 200 {
                Ok(body_bytes.to_vec())
            } else {
                Err(anyhow!(
                    "Peer returned HTTP {}: {}",
                    status_code,
                    String::from_utf8_lossy(body_bytes)
                ))
            }
        } else {
            Err(anyhow!("Invalid HTTP response from peer"))
        }
    }
}

fn find_subsequence(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack
        .windows(needle.len())
        .position(|window| window == needle)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::server::MeshServer;

    #[tokio::test]
    async fn test_mtls_client_server_roundtrip() {
        let server_id = MeshIdentity::generate("server-node-1").unwrap();
        let client_id = MeshIdentity::generate("client-node-1").unwrap();

        let server_info = MeshNodeInfo {
            node_id: "server-node-1".to_string(),
            hostname: "workstation.local".to_string(),
            ip: "127.0.0.1".to_string(),
            port: 59955, // test port
            free_ram_gb: 32.0,
            gpu_name: "RTX 4090".to_string(),
            free_vram_mb: 24000,
            capabilities: vec!["32b".to_string()],
            tls_fingerprint: server_id.tls_fingerprint.clone(),
            active_jobs: 0,
            last_seen_epoch_secs: 0,
        };

        let server = MeshServer::new(server_id, server_info.clone(), 59955);
        server.start().await.unwrap();

        // Give server a moment to bind
        tokio::time::sleep(Duration::from_millis(100)).await;

        let client = MeshClient::new(client_id);
        let status = client.query_status(&server_info).await.unwrap();
        assert_eq!(status.node_id, "server-node-1");
        assert_eq!(status.free_vram_mb, 24000);

        // Test arbitration offload
        let arb_req = ArbitrateTaskRequest {
            task_description: "Write fibonacci".to_string(),
            candidates: vec![crate::rpc::CandidateSolutionPayload {
                id: "c1".to_string(),
                model: "qwen2.5:32b".to_string(),
                code: "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)".to_string(),
                verification_score: 1.0,
                test_output: None,
            }],
            hardware_tier: 1,
            target_model: Some("qwen2.5:32b".to_string()),
        };

        let arb_res = client.offload_arbitration(&server_info, &arb_req).await.unwrap();
        assert_eq!(arb_res.offloaded_to, "server-node-1");
        assert_eq!(arb_res.result.selected_candidate_id, "c1");

        // Test fingerprint mismatch fails connection
        let mut mismatched_server_info = server_info.clone();
        mismatched_server_info.tls_fingerprint = "0000000000000000000000000000000000000000000000000000000000000000".to_string();
        let mismatch_res = client.query_status(&mismatched_server_info).await;
        assert!(mismatch_res.is_err(), "Client must reject connection when server TLS fingerprint mismatches advertised hash");

        server.stop();
    }
}

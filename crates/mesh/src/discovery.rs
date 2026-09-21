//! mDNS / DNS-SD Peer Discovery for Distributed Local Mesh

use crate::peer::{current_epoch_secs, MeshNodeInfo, PeerRegistry};
use anyhow::{anyhow, Result};
use mdns_sd::{ServiceDaemon, ServiceEvent, ServiceInfo};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::task::JoinHandle;

pub const MESH_SERVICE_TYPE: &str = "_hugos-mesh._tcp.local.";

pub struct MeshDiscovery {
    daemon: ServiceDaemon,
    registry: PeerRegistry,
    running: Arc<AtomicBool>,
    browser_handle: Option<JoinHandle<()>>,
}

impl MeshDiscovery {
    pub fn new(registry: PeerRegistry) -> Result<Self> {
        let daemon = ServiceDaemon::new().map_err(|e| anyhow!("Failed to start mDNS daemon: {:?}", e))?;
        Ok(Self {
            daemon,
            registry,
            running: Arc::new(AtomicBool::new(false)),
            browser_handle: None,
        })
    }

    /// Register local node in the mDNS network.
    pub fn advertise_node(&self, local_info: &MeshNodeInfo) -> Result<()> {
        let instance_name = format!("hugos-{}", &local_info.node_id[..local_info.node_id.len().min(8)]);
        let host_name = format!("{}.local.", local_info.hostname.replace(' ', "-"));

        let mut properties = HashMap::new();
        properties.insert("node_id".to_string(), local_info.node_id.clone());
        properties.insert("hostname".to_string(), local_info.hostname.clone());
        properties.insert("port".to_string(), local_info.port.to_string());
        properties.insert("free_ram_gb".to_string(), format!("{:.1}", local_info.free_ram_gb));
        properties.insert("gpu_name".to_string(), local_info.gpu_name.clone());
        properties.insert("free_vram_mb".to_string(), local_info.free_vram_mb.to_string());
        properties.insert("capabilities".to_string(), local_info.capabilities.join(","));
        properties.insert("tls_fingerprint".to_string(), local_info.tls_fingerprint.clone());

        let service_info = ServiceInfo::new(
            MESH_SERVICE_TYPE,
            &instance_name,
            &host_name,
            &local_info.ip,
            local_info.port,
            properties,
        )
        .map_err(|e| anyhow!("Failed to create ServiceInfo: {:?}", e))?;

        self.daemon
            .register(service_info)
            .map_err(|e| anyhow!("Failed to register mDNS service: {:?}", e))?;

        log::info!(
            "[MESH] Registered mDNS service: {} on port {}",
            instance_name,
            local_info.port
        );
        Ok(())
    }

    /// Start browsing for remote LAN mesh peers in background.
    pub fn start_browsing(&mut self) -> Result<()> {
        let receiver = self
            .daemon
            .browse(MESH_SERVICE_TYPE)
            .map_err(|e| anyhow!("Failed to browse mDNS: {:?}", e))?;

        self.running.store(true, Ordering::SeqCst);
        let running_flag = self.running.clone();
        let registry = self.registry.clone();

        let handle = tokio::spawn(async move {
            while running_flag.load(Ordering::SeqCst) {
                match receiver.recv_async().await {
                    Ok(event) => match event {
                        ServiceEvent::ServiceResolved(info) => {
                            if let Some(peer) = parse_service_info(&info) {
                                log::info!(
                                    "[MESH] Discovered LAN peer '{}' ({}:{}) with capabilities: {:?}",
                                    peer.node_id,
                                    peer.ip,
                                    peer.port,
                                    peer.capabilities
                                );
                                registry.upsert_peer(peer);
                            }
                        }
                        ServiceEvent::ServiceRemoved(_, fullname) => {
                            log::info!("[MESH] Peer service removed: {}", fullname);
                        }
                        _ => {}
                    },
                    Err(_) => break,
                }
            }
        });

        self.browser_handle = Some(handle);
        Ok(())
    }

    /// Stop browsing and unregister.
    pub fn stop(&mut self) {
        self.running.store(false, Ordering::SeqCst);
        if let Some(handle) = self.browser_handle.take() {
            handle.abort();
        }
    }
}

fn parse_service_info(info: &ServiceInfo) -> Option<MeshNodeInfo> {
    let node_id = info.get_property_val_str("node_id")?.to_string();
    let hostname = info
        .get_property_val_str("hostname")
        .unwrap_or("unknown")
        .to_string();
    let port: u16 = info
        .get_property_val_str("port")
        .and_then(|p| p.parse().ok())
        .unwrap_or_else(|| info.get_port());
    let free_ram_gb: f64 = info
        .get_property_val_str("free_ram_gb")
        .and_then(|r| r.parse().ok())
        .unwrap_or(0.0);
    let gpu_name = info
        .get_property_val_str("gpu_name")
        .unwrap_or("None")
        .to_string();
    let free_vram_mb: u64 = info
        .get_property_val_str("free_vram_mb")
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    let capabilities = info
        .get_property_val_str("capabilities")
        .map(|c| c.split(',').map(|s| s.trim().to_string()).collect())
        .unwrap_or_default();
    let tls_fingerprint = info
        .get_property_val_str("tls_fingerprint")
        .unwrap_or("")
        .to_string();

    let ip = info
        .get_addresses()
        .iter()
        .next()
        .map(|a| a.to_string())
        .unwrap_or_else(|| "127.0.0.1".to_string());

    Some(MeshNodeInfo {
        node_id,
        hostname,
        ip,
        port,
        free_ram_gb,
        gpu_name,
        free_vram_mb,
        capabilities,
        tls_fingerprint,
        active_jobs: 0,
        last_seen_epoch_secs: current_epoch_secs(),
    })
}

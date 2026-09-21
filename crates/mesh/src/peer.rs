//! Peer Node Information and Thread-Safe Peer Registry

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MeshNodeInfo {
    pub node_id: String,
    pub hostname: String,
    pub ip: String,
    pub port: u16,
    pub free_ram_gb: f64,
    pub gpu_name: String,
    pub free_vram_mb: u64,
    pub capabilities: Vec<String>, // e.g. ["32b", "rest-rl", "vision"]
    pub tls_fingerprint: String,   // SHA-256 fingerprint of peer's mTLS certificate
    pub active_jobs: usize,
    pub last_seen_epoch_secs: u64,
}

impl MeshNodeInfo {
    pub fn has_capability(&self, cap: &str) -> bool {
        self.capabilities
            .iter()
            .any(|c| c.eq_ignore_ascii_case(cap))
    }

    pub fn can_run_32b(&self) -> bool {
        (self.free_vram_mb >= 14_000 || self.free_ram_gb >= 24.0) && self.has_capability("32b")
    }

    pub fn can_run_rest_rl(&self) -> bool {
        self.has_capability("rest-rl")
    }
}

/// Thread-safe peer registry with automatic expiration pruning.
#[derive(Debug, Clone, Default)]
pub struct PeerRegistry {
    peers: Arc<RwLock<HashMap<String, MeshNodeInfo>>>,
}

impl PeerRegistry {
    pub fn new() -> Self {
        Self {
            peers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Add or update a discovered peer in the registry.
    pub fn upsert_peer(&self, mut info: MeshNodeInfo) {
        if info.last_seen_epoch_secs == 0 {
            info.last_seen_epoch_secs = current_epoch_secs();
        }
        if let Ok(mut lock) = self.peers.write() {
            lock.insert(info.node_id.clone(), info);
        }
    }

    /// Remove a peer by node_id.
    pub fn remove_peer(&self, node_id: &str) -> Option<MeshNodeInfo> {
        if let Ok(mut lock) = self.peers.write() {
            lock.remove(node_id)
        } else {
            None
        }
    }

    /// Prune peers that haven't sent a heartbeat within `ttl_secs`.
    pub fn prune_expired(&self, ttl_secs: u64) -> usize {
        let now = current_epoch_secs();
        if let Ok(mut lock) = self.peers.write() {
            let before = lock.len();
            lock.retain(|_, peer| now.saturating_sub(peer.last_seen_epoch_secs) < ttl_secs);
            before - lock.len()
        } else {
            0
        }
    }

    /// Retrieve all currently active peers.
    pub fn all_peers(&self) -> Vec<MeshNodeInfo> {
        if let Ok(lock) = self.peers.read() {
            lock.values().cloned().collect()
        } else {
            Vec::new()
        }
    }

    /// Find the best LAN peer with the requested compute capacity and capability.
    pub fn find_offload_peer(
        &self,
        min_vram_mb: u64,
        min_ram_gb: f64,
        required_capability: &str,
    ) -> Option<MeshNodeInfo> {
        let peers = self.all_peers();
        peers
            .into_iter()
            .filter(|p| {
                p.has_capability(required_capability)
                    && (p.free_vram_mb >= min_vram_mb || p.free_ram_gb >= min_ram_gb)
            })
            .min_by_key(|p| p.active_jobs) // Pick least busy node
    }
}

pub fn current_epoch_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_peer_registry_upsert_and_find() {
        let registry = PeerRegistry::new();
        let peer = MeshNodeInfo {
            node_id: "gpu-worker-1".to_string(),
            hostname: "rig.local".to_string(),
            ip: "192.168.1.100".to_string(),
            port: 5055,
            free_ram_gb: 64.0,
            gpu_name: "NVIDIA RTX 4090".to_string(),
            free_vram_mb: 24000,
            capabilities: vec!["32b".to_string(), "rest-rl".to_string()],
            tls_fingerprint: "abc123sha".to_string(),
            active_jobs: 0,
            last_seen_epoch_secs: current_epoch_secs(),
        };

        registry.upsert_peer(peer.clone());
        let found = registry.find_offload_peer(14000, 24.0, "32b");
        assert!(found.is_some());
        assert_eq!(found.unwrap().node_id, "gpu-worker-1");
    }

    #[test]
    fn test_peer_registry_pruning() {
        let registry = PeerRegistry::new();
        let old_peer = MeshNodeInfo {
            node_id: "stale-node".to_string(),
            hostname: "old.local".to_string(),
            ip: "192.168.1.101".to_string(),
            port: 5055,
            free_ram_gb: 8.0,
            gpu_name: "None".to_string(),
            free_vram_mb: 0,
            capabilities: vec!["1.5b".to_string()],
            tls_fingerprint: "oldsha".to_string(),
            active_jobs: 0,
            last_seen_epoch_secs: current_epoch_secs() - 100,
        };

        registry.upsert_peer(old_peer);
        assert_eq!(registry.all_peers().len(), 1);
        let pruned = registry.prune_expired(30);
        assert_eq!(pruned, 1);
        assert!(registry.all_peers().is_empty());
    }
}

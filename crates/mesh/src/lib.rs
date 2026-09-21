//! Distributed Local AI Mesh Crate for ModelFusion
//!
//! Provides mDNS peer discovery (`_hugos-mesh._tcp.local.`), self-signed
//! mTLS transport via `rustls`/`rcgen`, and RPC endpoints for offloading
//! 32B model arbitration and ReST-RL sweeps across local LAN workstations.

pub mod client;
pub mod discovery;
pub mod peer;
pub mod rpc;
pub mod server;
pub mod tls;

pub use client::MeshClient;
pub use discovery::{MeshDiscovery, MESH_SERVICE_TYPE};
pub use peer::{current_epoch_secs, MeshNodeInfo, PeerRegistry};
pub use rpc::{
    ArbitrateTaskRequest, ArbitrateTaskResponse, ArbitrationResultPayload,
    CandidateSolutionPayload, NodeStatusResponse, RestRlTaskRequest, RestRlTaskResponse,
};
pub use server::{ArbitrateHandler, MeshServer, RestRlHandler};
pub use tls::MeshIdentity;

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

//! RPC Payload Definitions for Mesh Node Communication

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CandidateSolutionPayload {
    pub id: String,
    pub model: String,
    pub code: String,
    pub verification_score: f64,
    pub test_output: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArbitrationResultPayload {
    pub selected_candidate_id: String,
    pub resolved_code: String,
    pub reasoning: String,
    pub was_arbitrated: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArbitrateTaskRequest {
    pub task_description: String,
    pub candidates: Vec<CandidateSolutionPayload>,
    pub hardware_tier: u8,
    pub target_model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArbitrateTaskResponse {
    pub result: ArbitrationResultPayload,
    pub offloaded_to: String,
    pub elapsed_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RestRlTaskRequest {
    pub file_path: String,
    pub code: String,
    pub diagnostics: Vec<String>,
    pub test_target: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RestRlTaskResponse {
    pub passed: bool,
    pub reward: f64,
    pub candidate_code: Option<String>,
    pub diff: Option<String>,
    pub mutants_killed: usize,
    pub total_mutants: usize,
    pub offloaded_to: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeStatusResponse {
    pub node_id: String,
    pub hostname: String,
    pub free_ram_gb: f64,
    pub gpu_name: String,
    pub free_vram_mb: u64,
    pub capabilities: Vec<String>,
    pub active_jobs: usize,
    pub tls_fingerprint: String,
}

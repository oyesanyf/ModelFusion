//! Data types for decision monitoring.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use security::ThreatEntry;

/// Metrics captured for a single thought during chain-of-thought reasoning.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionMetrics {
    /// The thought text that was evaluated.
    pub thought: String,
    /// Quality score 1–10 (higher is better).
    pub score: i32,
    /// Confidence in the score (0.0–1.0).
    pub confidence: f64,
    /// When this decision was recorded.
    pub timestamp: DateTime<Utc>,
    /// Depth of the thought in the reasoning tree.
    pub depth: u32,
    /// Unique branch identifier (e.g. `"2-3"` for depth 2, branch 3).
    pub branch_id: String,
    /// Optional human-readable reason for the score.
    pub reason: Option<String>,
    /// Category of the thought (analysis / processing / generation / evaluation).
    pub category: Option<String>,
    /// Whether a recovery was attempted because the score was below threshold.
    pub recovery_attempted: bool,
    /// Suggestion generated when a bad decision is detected.
    pub improvement_suggestion: Option<String>,
    /// ATLAS threats detected in this thought, if any.
    pub atlas_threats: Vec<ThreatEntry>,
}

impl DecisionMetrics {
    /// Returns `true` if any ATLAS threats were detected.
    pub fn has_threats(&self) -> bool {
        !self.atlas_threats.is_empty()
    }

    /// Returns `true` if this thought passed the quality threshold.
    pub fn passed(&self, threshold: f64) -> bool {
        self.score as f64 >= threshold
    }
}

/// Aggregate statistics for a monitoring session.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionStats {
    /// Total decisions evaluated.
    pub total_decisions: usize,
    /// Average score across all decisions.
    pub avg_score: f64,
    /// Fraction of decisions that passed the threshold (0.0–1.0).
    pub pass_rate: f64,
    /// Total number of ATLAS threats detected.
    pub threat_count: usize,
    /// Breakdown of categories: category → count.
    pub category_counts: std::collections::HashMap<String, usize>,
}

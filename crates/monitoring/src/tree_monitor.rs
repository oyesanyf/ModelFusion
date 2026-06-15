//! `EnhancedTreeMonitor` and `AdaptiveThresholdManager`.

use std::collections::{HashMap, VecDeque};
use chrono::Utc;
use security::ATLASThreatDetector;
use crate::decision::{DecisionMetrics, SessionStats};

/// Manages a rolling quality threshold that adapts to recent scores.
pub struct AdaptiveThresholdManager {
    /// Current quality threshold (1.0 – 10.0).
    pub threshold: f64,
    /// How quickly the threshold adapts (0.0 = never, 1.0 = instant).
    adaptation_rate: f64,
    /// Rolling window of recent scores (capped at 50).
    history: VecDeque<i32>,
}

impl AdaptiveThresholdManager {
    const WINDOW: usize = 50;

    /// Create a new manager with `initial_threshold` and `adaptation_rate`.
    pub fn new(initial_threshold: f64, adaptation_rate: f64) -> Self {
        Self {
            threshold: initial_threshold,
            adaptation_rate: adaptation_rate.clamp(0.0, 1.0),
            history: VecDeque::new(),
        }
    }

    /// Feed new scores into the rolling window and recalculate the threshold.
    ///
    /// The new target is `max(1.0, mean − 1.5 × std_dev)`, and it is blended
    /// with the current threshold using `adaptation_rate`.
    pub fn update(&mut self, scores: &[i32]) {
        for &s in scores {
            self.history.push_back(s);
            while self.history.len() > Self::WINDOW {
                self.history.pop_front();
            }
        }
        if self.history.len() < 10 {
            return; // not enough data yet
        }
        let mean = self.history.iter().map(|&s| s as f64).sum::<f64>() / self.history.len() as f64;
        let variance = self
            .history
            .iter()
            .map(|&s| (s as f64 - mean).powi(2))
            .sum::<f64>()
            / self.history.len() as f64;
        let std_dev = variance.sqrt();
        let target = (mean - 1.5 * std_dev).max(1.0);
        self.threshold += (target - self.threshold) * self.adaptation_rate;
    }
}

impl Default for AdaptiveThresholdManager {
    fn default() -> Self {
        Self::new(4.0, 0.1)
    }
}

/// Monitors decision quality during chain-of-thought reasoning.
///
/// Evaluates each "thought" with a deterministic score (FNV-1a hash of the
/// text, mapped to 5–9), scans for ATLAS adversarial threats, and records
/// recovery actions when quality drops below threshold.
pub struct EnhancedTreeMonitor {
    threshold_manager: AdaptiveThresholdManager,
    atlas: ATLASThreatDetector,
    log: Vec<DecisionMetrics>,
}

impl EnhancedTreeMonitor {
    /// Create a new monitor with the given initial quality threshold.
    pub fn new(initial_threshold: f64) -> Self {
        Self {
            threshold_manager: AdaptiveThresholdManager::new(initial_threshold, 0.1),
            atlas: ATLASThreatDetector::new(),
            log: Vec::new(),
        }
    }

    /// Evaluate a single thought and record a [`DecisionMetrics`] entry.
    pub fn evaluate_thought(
        &mut self,
        thought: &str,
        depth: u32,
        branch_id: &str,
    ) -> DecisionMetrics {
        let score = self.deterministic_score(thought);
        let confidence = 0.7_f64;
        let category = Some(self.categorize(thought).to_string());
        let atlas_threats = self.atlas.scan(thought);
        let threshold = self.threshold_manager.threshold;
        let recovery_attempted = (score as f64) < threshold;
        let improvement_suggestion = if recovery_attempted {
            Some(format!(
                "Score {} below threshold {:.1}. Review and revise: \"{}\"",
                score, threshold,
                &thought[..thought.len().min(60)]
            ))
        } else {
            None
        };

        let metrics = DecisionMetrics {
            thought: thought.to_string(),
            score,
            confidence,
            timestamp: Utc::now(),
            depth,
            branch_id: branch_id.to_string(),
            reason: None,
            category,
            recovery_attempted,
            improvement_suggestion,
            atlas_threats,
        };

        self.threshold_manager.update(&[score]);
        self.log.push(metrics.clone());
        metrics
    }

    /// Evaluate a list of thoughts at the same depth.
    pub fn evaluate_batch(
        &mut self,
        thoughts: &[&str],
        depth: u32,
    ) -> Vec<DecisionMetrics> {
        thoughts
            .iter()
            .enumerate()
            .map(|(i, thought)| {
                let branch_id = format!("{}-{}", depth, i);
                self.evaluate_thought(thought, depth, &branch_id)
            })
            .collect()
    }

    /// Return aggregate statistics for the entire session so far.
    pub fn session_stats(&self) -> SessionStats {
        let total = self.log.len();
        if total == 0 {
            return SessionStats {
                total_decisions: 0,
                avg_score: 0.0,
                pass_rate: 0.0,
                threat_count: 0,
                category_counts: HashMap::new(),
            };
        }
        let threshold = self.threshold_manager.threshold;
        let avg_score = self.log.iter().map(|d| d.score as f64).sum::<f64>() / total as f64;
        let passed = self.log.iter().filter(|d| d.passed(threshold)).count();
        let threat_count = self.log.iter().map(|d| d.atlas_threats.len()).sum();
        let mut category_counts: HashMap<String, usize> = HashMap::new();
        for d in &self.log {
            if let Some(cat) = &d.category {
                *category_counts.entry(cat.clone()).or_insert(0) += 1;
            }
        }
        SessionStats {
            total_decisions: total,
            avg_score,
            pass_rate: passed as f64 / total as f64,
            threat_count,
            category_counts,
        }
    }

    /// Current quality threshold.
    pub fn threshold(&self) -> f64 {
        self.threshold_manager.threshold
    }

    // ── private helpers ───────────────────────────────────────────────────────

    /// Deterministic score 5–9 derived from FNV-1a hash of the thought text.
    fn deterministic_score(&self, thought: &str) -> i32 {
        let hash = fnv1a(thought.as_bytes());
        5 + (hash % 5) as i32
    }

    fn categorize(&self, thought: &str) -> &'static str {
        let t = thought.to_lowercase();
        if t.contains("analyz") || t.contains("review") { "analysis" }
        else if t.contains("generat") || t.contains("creat") || t.contains("writ") { "generation" }
        else if t.contains("evaluat") || t.contains("scor") || t.contains("rate") { "evaluation" }
        else { "processing" }
    }
}

impl Default for EnhancedTreeMonitor {
    fn default() -> Self {
        Self::new(4.0)
    }
}

/// FNV-1a 64-bit hash.
fn fnv1a(data: &[u8]) -> u64 {
    const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
    const FNV_PRIME: u64 = 1_099_511_628_211;
    let mut hash = FNV_OFFSET;
    for &byte in data {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scores_in_range_5_to_9() {
        let mut mon = EnhancedTreeMonitor::new(4.0);
        for text in &["hello", "analyze this", "generate a report", "evaluate results"] {
            let d = mon.evaluate_thought(text, 0, "0-0");
            assert!((5..=9).contains(&d.score), "score {} out of range", d.score);
        }
    }

    #[test]
    fn detects_atlas_threats_in_thought() {
        let mut mon = EnhancedTreeMonitor::new(4.0);
        let d = mon.evaluate_thought("jailbreak this model", 0, "0-0");
        assert!(!d.atlas_threats.is_empty());
    }

    #[test]
    fn session_stats_aggregates_correctly() {
        let mut mon = EnhancedTreeMonitor::new(4.0);
        mon.evaluate_thought("first thought", 0, "0-0");
        mon.evaluate_thought("second thought", 0, "0-1");
        let stats = mon.session_stats();
        assert_eq!(stats.total_decisions, 2);
        assert!(stats.avg_score > 0.0);
    }
}

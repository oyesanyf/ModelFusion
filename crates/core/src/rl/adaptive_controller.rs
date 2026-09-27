//! Sound Multi-Objective Adaptive Controller (LinUCB with Tikhonov-Regularized Cholesky Inversion)
//!
//! Provides mathematically sound reinforcement learning exploration, counterfactual margin
//! scoring, advantage binning, and frozen-test evaluation for dynamic model routing,
//! consensus panel sizing, and verification depth decisions.

use std::collections::VecDeque;
use std::path::Path;
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

/// Number of state features (task complexity, RAM, VRAM, prompt length, task flags).
pub const STATE_DIM: usize = 8;
/// Number of action features (model tier, consensus panel, verification depth, search mode).
pub const ACTION_DIM: usize = 4;
/// Joint bilinear dimension: 1 (bias) + d_s + d_a + (d_s * d_a) = 45.
pub const JOINT_FEATURE_DIM: usize = 1 + STATE_DIM + ACTION_DIM + (STATE_DIM * ACTION_DIM);

/// Operational learning regime for the controller.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LearningRegime {
    /// Cold start with identity covariance A = I and b = 0.
    Cold,
    /// Pre-calibrated initial weights.
    Prior,
    /// Frozen test mode: update_policy = false (zero parameter drift, zero test leakage).
    FrozenTest,
    /// Active online learning with exploration decay.
    OnlineAnnealing,
}

/// Controller hyperparameters and configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControllerConfig {
    /// Initial exploration factor c_0 (default: 1.0).
    pub c0: f64,
    /// Exploration decay rate alpha_decay (default: 0.005).
    pub alpha_decay: f64,
    /// Tikhonov regularization epsilon for numerical stability (default: 1e-5).
    pub tikhonov_eps: f64,
    /// Operational learning regime.
    pub regime: LearningRegime,
}

impl Default for ControllerConfig {
    fn default() -> Self {
        Self {
            c0: 1.0,
            alpha_decay: 0.005,
            tikhonov_eps: 1e-5,
            regime: LearningRegime::OnlineAnnealing,
        }
    }
}

/// Normalized feature state observed from the environment and hardware.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureState {
    pub task_complexity: f64,
    pub available_ram_norm: f64,
    pub free_vram_norm: f64,
    pub prompt_len_norm: f64,
    pub is_code: f64,
    pub is_tabular: f64,
    pub is_multimodal: f64,
    pub is_web: f64,
}

impl FeatureState {
    pub fn new(
        task_complexity: f64,
        available_ram_gb: f64,
        free_vram_mb: f64,
        prompt_len: usize,
        is_code: bool,
        is_tabular: bool,
        is_multimodal: bool,
        is_web: bool,
    ) -> Self {
        Self {
            task_complexity: task_complexity.clamp(0.0, 1.0),
            available_ram_norm: (available_ram_gb / 64.0).clamp(0.0, 1.0),
            free_vram_norm: (free_vram_mb / 24000.0).clamp(0.0, 1.0),
            prompt_len_norm: ((prompt_len as f64) / 4000.0).clamp(0.0, 1.0),
            is_code: if is_code { 1.0 } else { 0.0 },
            is_tabular: if is_tabular { 1.0 } else { 0.0 },
            is_multimodal: if is_multimodal { 1.0 } else { 0.0 },
            is_web: if is_web { 1.0 } else { 0.0 },
        }
    }

    pub fn as_slice(&self) -> [f64; STATE_DIM] {
        [
            self.task_complexity,
            self.available_ram_norm,
            self.free_vram_norm,
            self.prompt_len_norm,
            self.is_code,
            self.is_tabular,
            self.is_multimodal,
            self.is_web,
        ]
    }
}

/// Multi-dimensional decision action selected by the policy.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DecisionAction {
    pub model_tier_norm: f64,
    pub consensus_panel_norm: f64,
    pub verification_depth_norm: f64,
    pub search_mode_norm: f64,
    #[serde(default)]
    pub arm_id: usize,
    #[serde(default)]
    pub model_tier: String,
    #[serde(default)]
    pub consensus_panel_size: usize,
    #[serde(default)]
    pub verification_depth: usize,
    #[serde(default)]
    pub search_mode: String,
}

impl DecisionAction {
    pub fn as_slice(&self) -> [f64; ACTION_DIM] {
        [
            self.model_tier_norm,
            self.consensus_panel_norm,
            self.verification_depth_norm,
            self.search_mode_norm,
        ]
    }

    pub fn default_single() -> Self {
        Self {
            model_tier_norm: 0.25,
            consensus_panel_norm: 0.2,
            verification_depth_norm: 0.0,
            search_mode_norm: 0.0,
            arm_id: 0,
            model_tier: "single_fast".to_string(),
            consensus_panel_size: 1,
            verification_depth: 0,
            search_mode: "none".to_string(),
        }
    }

    pub fn default_candidate_actions() -> Vec<Self> {
        vec![
            // Arm 0: Single Workhorse Model (Fast execution, no consensus)
            Self {
                model_tier_norm: 0.25,
                consensus_panel_norm: 0.2, // 1 model (1/5)
                verification_depth_norm: 0.0, // No AST/mutation
                search_mode_norm: 0.0,
                arm_id: 0,
                model_tier: "single_fast".to_string(),
                consensus_panel_size: 1,
                verification_depth: 0,
                search_mode: "none".to_string(),
            },
            // Arm 1: Single Model + Static Verification (AST/Lint checks)
            Self {
                model_tier_norm: 0.5,
                consensus_panel_norm: 0.2, // 1 model
                verification_depth_norm: 0.33, // Depth 1: AST/Lint
                search_mode_norm: 0.0,
                arm_id: 1,
                model_tier: "single_verified".to_string(),
                consensus_panel_size: 1,
                verification_depth: 1,
                search_mode: "none".to_string(),
            },
            // Arm 2: Dual-Model Consensus Panel (2 models + test sandbox)
            Self {
                model_tier_norm: 0.5,
                consensus_panel_norm: 0.4, // 2 models (2/5)
                verification_depth_norm: 0.67, // Depth 2: Test Sandbox
                search_mode_norm: 0.0,
                arm_id: 2,
                model_tier: "dual_consensus".to_string(),
                consensus_panel_size: 2,
                verification_depth: 2,
                search_mode: "none".to_string(),
            },
            // Arm 3: Triple-Model Fusion Ensemble + Mutation Certification
            Self {
                model_tier_norm: 0.75,
                consensus_panel_norm: 0.6, // 3 models (3/5)
                verification_depth_norm: 1.0, // Depth 3: Full Mutation Gate
                search_mode_norm: 0.0,
                arm_id: 3,
                model_tier: "triple_fusion".to_string(),
                consensus_panel_size: 3,
                verification_depth: 3,
                search_mode: "none".to_string(),
            },
            // Arm 4: Multi-Model Deep Research + Multimodal Grounding
            Self {
                model_tier_norm: 1.0,
                consensus_panel_norm: 0.6, // 3 models
                verification_depth_norm: 1.0,
                search_mode_norm: 1.0, // Deep web research enabled
                arm_id: 4,
                model_tier: "deep_research_fusion".to_string(),
                consensus_panel_size: 3,
                verification_depth: 3,
                search_mode: "deep".to_string(),
            },
        ]
    }
}

/// Advantage binning telemetry tracking policy performance over raw/single model baseline.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AdvantageStats {
    pub rl_greater_than_raw: usize,
    pub rl_equal_to_raw: usize,
    pub rl_less_than_raw: usize,
    pub win_rate_percent: f64,
}

/// Comprehensive RL telemetry snapshot returned via HTTP/IPC and displayed in HugOS UI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RLTelemetry {
    pub regime: String,
    pub decisions_count: usize,
    pub exploration_rate: f64,
    pub advantage: AdvantageStats,
    pub mean_regret: f64,
    pub r_early: f64,
    pub r_late: f64,
    pub temporal_improvement: bool,
}

/// Extracts joint bilinear features phi(s, a) of dimension 45.
pub fn extract_joint_features(s: &FeatureState, a: &DecisionAction) -> Vec<f64> {
    let s_vec = s.as_slice();
    let a_vec = a.as_slice();
    let mut phi = Vec::with_capacity(JOINT_FEATURE_DIM);

    // 1. Bias term
    phi.push(1.0);

    // 2. Linear state terms (8)
    phi.extend_from_slice(&s_vec);

    // 3. Linear action terms (4)
    phi.extend_from_slice(&a_vec);

    // 4. Bilinear interaction terms s (x) a (32)
    for si in &s_vec {
        for aj in &a_vec {
            phi.push(si * aj);
        }
    }

    debug_assert_eq!(phi.len(), JOINT_FEATURE_DIM);
    phi
}

/// Computes Cholesky decomposition L L^T = A + eps * I.
pub fn cholesky_decompose(a: &[Vec<f64>], tikhonov_eps: f64) -> Result<Vec<Vec<f64>>> {
    let n = a.len();
    if n == 0 {
        return Err(anyhow::anyhow!("Matrix dimension cannot be zero"));
    }
    let mut l = vec![vec![0.0; n]; n];

    for i in 0..n {
        for j in 0..=i {
            let mut sum = 0.0;
            for k in 0..j {
                sum += l[i][k] * l[j][k];
            }
            if i == j {
                let diag = a[i][i] + tikhonov_eps;
                let val = diag - sum;
                if val <= 0.0 {
                    l[i][j] = (val.abs() + 1e-10).sqrt();
                } else {
                    l[i][j] = val.sqrt();
                }
            } else {
                if l[j][j].abs() < 1e-12 {
                    l[i][j] = 0.0;
                } else {
                    let a_ij = a[i][j];
                    l[i][j] = (a_ij - sum) / l[j][j];
                }
            }
        }
    }
    Ok(l)
}

/// Solves L y = b and L^T x = y via forward and back substitution.
pub fn cholesky_solve(l: &[Vec<f64>], b: &[f64]) -> Vec<f64> {
    let n = l.len();
    let mut y = vec![0.0; n];

    // Forward solve: L y = b
    for i in 0..n {
        let mut sum = 0.0;
        for k in 0..i {
            sum += l[i][k] * y[k];
        }
        let denom = if l[i][i].abs() < 1e-12 { 1e-12 } else { l[i][i] };
        y[i] = (b[i] - sum) / denom;
    }

    // Backward solve: L^T x = y
    let mut x = vec![0.0; n];
    for i in (0..n).rev() {
        let mut sum = 0.0;
        for k in (i + 1)..n {
            sum += l[k][i] * x[k];
        }
        let denom = if l[i][i].abs() < 1e-12 { 1e-12 } else { l[i][i] };
        x[i] = (y[i] - sum) / denom;
    }
    x
}

/// Computes numerically stable Tikhonov-regularized covariance inverse A^{-1}.
pub fn stable_covariance_inverse(a: &[Vec<f64>], tikhonov_eps: f64) -> Result<Vec<Vec<f64>>> {
    let n = a.len();
    let l = cholesky_decompose(a, tikhonov_eps)?;

    // Invert L (lower triangular) to get L^{-1}
    let mut l_inv = vec![vec![0.0; n]; n];
    for i in 0..n {
        let denom = if l[i][i].abs() < 1e-12 { 1e-12 } else { l[i][i] };
        l_inv[i][i] = 1.0 / denom;
        for j in 0..i {
            let mut sum = 0.0;
            for k in j..i {
                sum += l[i][k] * l_inv[k][j];
            }
            l_inv[i][j] = -sum / denom;
        }
    }

    // A^{-1} = (L^{-1})^T * L^{-1}
    let mut a_inv = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..n {
            let mut sum = 0.0;
            let start = i.max(j);
            for k in start..n {
                sum += l_inv[k][i] * l_inv[k][j];
            }
            a_inv[i][j] = sum;
        }
    }
    Ok(a_inv)
}

/// The 6-Pillar Sound Multi-Objective Adaptive Controller.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveController {
    pub config: ControllerConfig,
    /// Covariance matrix A in R^{45 x 45}.
    pub a_matrix: Vec<Vec<f64>>,
    /// Reward-weighted feature accumulator b in R^{45}.
    pub b_vector: Vec<f64>,
    /// Step / decision counter t.
    pub t: usize,
    /// Cumulative instantaneous regret.
    pub total_regret: f64,
    /// Direct advantage counters.
    pub rl_greater_than_raw: usize,
    pub rl_equal_to_raw: usize,
    pub rl_less_than_raw: usize,
    /// Rolling early rewards queue (first 25 rewards).
    pub early_rewards: VecDeque<f64>,
    /// Rolling late rewards queue (most recent 25 rewards).
    pub late_rewards: VecDeque<f64>,
}

impl Default for AdaptiveController {
    fn default() -> Self {
        Self::new(ControllerConfig::default())
    }
}

impl AdaptiveController {
    pub fn new(config: ControllerConfig) -> Self {
        let mut a_matrix = vec![vec![0.0; JOINT_FEATURE_DIM]; JOINT_FEATURE_DIM];
        // Initialize with Identity matrix (Ridge prior)
        for i in 0..JOINT_FEATURE_DIM {
            a_matrix[i][i] = 1.0;
        }
        let b_vector = vec![0.0; JOINT_FEATURE_DIM];

        Self {
            config,
            a_matrix,
            b_vector,
            t: 0,
            total_regret: 0.0,
            rl_greater_than_raw: 0,
            rl_equal_to_raw: 0,
            rl_less_than_raw: 0,
            early_rewards: VecDeque::with_capacity(25),
            late_rewards: VecDeque::with_capacity(25),
        }
    }

    /// Calculates current time-decayed exploration annealing factor c(t).
    pub fn exploration_rate(&self) -> f64 {
        self.config.c0 / (1.0 + self.config.alpha_decay * (self.t as f64))
    }

    /// Selects optimal action maximizing LinUCB score: phi^T \hat{theta} + c(t) sqrt(phi^T A^{-1} phi).
    pub fn select_action(
        &mut self,
        state: &FeatureState,
        candidate_actions: &[DecisionAction],
    ) -> (DecisionAction, f64) {
        if candidate_actions.is_empty() {
            let default_act = DecisionAction::default_single();
            return (default_act, 0.0);
        }

        // Solve for parameter vector theta = A^{-1} b using Cholesky
        let l = match cholesky_decompose(&self.a_matrix, self.config.tikhonov_eps) {
            Ok(decomp) => decomp,
            Err(_) => vec![vec![1.0; JOINT_FEATURE_DIM]; JOINT_FEATURE_DIM],
        };
        let theta = cholesky_solve(&l, &self.b_vector);
        let a_inv = match stable_covariance_inverse(&self.a_matrix, self.config.tikhonov_eps) {
            Ok(inv) => inv,
            Err(_) => vec![vec![1.0; JOINT_FEATURE_DIM]; JOINT_FEATURE_DIM],
        };

        let c_t = if self.config.regime == LearningRegime::FrozenTest {
            0.0 // Pure deterministic exploitation in frozen test evaluation
        } else {
            self.exploration_rate()
        };

        let mut best_idx = 0;
        let mut best_score = f64::NEG_INFINITY;

        for (idx, action) in candidate_actions.iter().enumerate() {
            let phi = extract_joint_features(state, action);

            // Linear mean expectation: mu = phi^T theta
            let mu: f64 = phi.iter().zip(theta.iter()).map(|(p, th)| p * th).sum();

            // Uncertainty variance: phi^T A^{-1} phi
            let mut variance = 0.0;
            for i in 0..JOINT_FEATURE_DIM {
                let mut row_sum = 0.0;
                for j in 0..JOINT_FEATURE_DIM {
                    row_sum += a_inv[i][j] * phi[j];
                }
                variance += phi[i] * row_sum;
            }
            let sigma = variance.max(0.0).sqrt();
            let ucb_score = mu + c_t * sigma;

            if ucb_score > best_score {
                best_score = ucb_score;
                best_idx = idx;
            }
        }

        (candidate_actions[best_idx].clone(), best_score)
    }

    /// Updates policy weights A and b with observed reward, tracking advantage binning and regret.
    pub fn update(
        &mut self,
        state: &FeatureState,
        action: &DecisionAction,
        reward: f64,
        baseline_reward: Option<f64>,
    ) {
        // Enforce Frozen Test invariant: zero parameter drift, zero test leakage
        if self.config.regime == LearningRegime::FrozenTest {
            return;
        }

        let phi = extract_joint_features(state, action);

        // A <- A + phi phi^T
        for i in 0..JOINT_FEATURE_DIM {
            for j in 0..JOINT_FEATURE_DIM {
                self.a_matrix[i][j] += phi[i] * phi[j];
            }
        }

        // b <- b + R * phi
        for i in 0..JOINT_FEATURE_DIM {
            self.b_vector[i] += reward * phi[i];
        }

        self.t += 1;

        // Reward trajectory tracking
        if self.early_rewards.len() < 25 {
            self.early_rewards.push_back(reward);
        }
        self.late_rewards.push_back(reward);
        if self.late_rewards.len() > 25 {
            self.late_rewards.pop_front();
        }

        // Advantage binning & counterfactual margin against single-model baseline
        if let Some(r_base) = baseline_reward {
            let margin = reward - r_base;
            if margin > 1e-5 {
                self.rl_greater_than_raw += 1;
            } else if margin < -1e-5 {
                self.rl_less_than_raw += 1;
            } else {
                self.rl_equal_to_raw += 1;
            }

            let regret = (r_base - reward).max(0.0);
            self.total_regret += regret;
        }
    }

    /// Sets the operational learning regime.
    pub fn set_regime(&mut self, regime: LearningRegime) {
        self.config.regime = regime;
    }

    /// Returns comprehensive RL telemetry for monitoring and visualization.
    pub fn telemetry(&self) -> RLTelemetry {
        let total_advantage = self.rl_greater_than_raw + self.rl_equal_to_raw + self.rl_less_than_raw;
        let win_rate = if total_advantage > 0 {
            (self.rl_greater_than_raw as f64 / total_advantage as f64) * 100.0
        } else {
            0.0
        };

        let mean_regret = if self.t > 0 {
            self.total_regret / (self.t as f64)
        } else {
            0.0
        };

        let r_early = if !self.early_rewards.is_empty() {
            self.early_rewards.iter().sum::<f64>() / (self.early_rewards.len() as f64)
        } else {
            0.0
        };

        let r_late = if !self.late_rewards.is_empty() {
            self.late_rewards.iter().sum::<f64>() / (self.late_rewards.len() as f64)
        } else {
            0.0
        };

        let regime_str = match self.config.regime {
            LearningRegime::FrozenTest => "FrozenTest".to_string(),
            LearningRegime::Cold => "Cold".to_string(),
            LearningRegime::Prior => "Prior".to_string(),
            LearningRegime::OnlineAnnealing => "OnlineAnnealing".to_string(),
        };

        RLTelemetry {
            regime: regime_str,
            decisions_count: self.t,
            exploration_rate: self.exploration_rate(),
            advantage: AdvantageStats {
                rl_greater_than_raw: self.rl_greater_than_raw,
                rl_equal_to_raw: self.rl_equal_to_raw,
                rl_less_than_raw: self.rl_less_than_raw,
                win_rate_percent: win_rate,
            },
            mean_regret,
            r_early,
            r_late,
            temporal_improvement: r_late > r_early,
        }
    }

    /// Serializes and saves policy checkpoint to SQLite/JSON storage.
    pub fn save_checkpoint(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("Failed creating directory: {:?}", parent))?;
        }
        let json_data = serde_json::to_string_pretty(self)
            .context("Failed serializing AdaptiveController")?;
        std::fs::write(path, json_data)
            .with_context(|| format!("Failed saving checkpoint to {:?}", path))?;
        Ok(())
    }

    /// Deserializes and loads policy checkpoint from storage.
    pub fn load_checkpoint(path: &Path) -> Result<Self> {
        let json_data = std::fs::read_to_string(path)
            .with_context(|| format!("Failed reading checkpoint from {:?}", path))?;
        let controller: Self = serde_json::from_str(&json_data)
            .context("Failed deserializing AdaptiveController")?;
        Ok(controller)
    }

    /// Loads checkpoint if available, otherwise returns default initialized controller.
    pub fn load_or_default(path: &Path) -> Self {
        if path.exists() {
            if let Ok(ctrl) = Self::load_checkpoint(path) {
                return ctrl;
            }
        }
        Self::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feature_expansion_dimension() {
        let state = FeatureState::new(0.8, 32.0, 12000.0, 1500, true, false, false, false);
        let action = DecisionAction::default_single();
        let phi = extract_joint_features(&state, &action);
        assert_eq!(phi.len(), 45);
        assert_eq!(phi[0], 1.0); // Bias
    }

    #[test]
    fn test_tikhonov_cholesky_inversion_positive_definite() {
        let mut controller = AdaptiveController::default();
        let state = FeatureState::new(0.5, 16.0, 8000.0, 500, true, false, false, false);
        let action = DecisionAction::default_single();

        // Perform synthetic updates
        controller.update(&state, &action, 1.0, Some(0.8));

        let a_inv = stable_covariance_inverse(&controller.a_matrix, controller.config.tikhonov_eps)
            .expect("Inversion should succeed");
        assert_eq!(a_inv.len(), 45);
        assert_eq!(a_inv[0].len(), 45);

        // Verify diagonal elements are strictly positive (positive definiteness)
        for i in 0..45 {
            assert!(
                a_inv[i][i] > 0.0,
                "Diagonal element a_inv[{}][{}] must be > 0, got {}",
                i,
                i,
                a_inv[i][i]
            );
        }
    }

    #[test]
    fn test_exploration_annealing_decay() {
        let mut controller = AdaptiveController::default();
        let initial_c = controller.exploration_rate();
        assert!((initial_c - 1.0).abs() < 1e-6);

        // Advance steps
        controller.t = 100;
        let c_100 = controller.exploration_rate();
        assert!(c_100 < initial_c);

        controller.t = 1000;
        let c_1000 = controller.exploration_rate();
        assert!(c_1000 < c_100);
        assert!(c_1000 > 0.0);
    }

    #[test]
    fn test_frozen_test_mode_locks_parameters() {
        let mut controller = AdaptiveController::new(ControllerConfig {
            c0: 1.0,
            alpha_decay: 0.005,
            tikhonov_eps: 1e-5,
            regime: LearningRegime::FrozenTest,
        });

        let state = FeatureState::new(0.9, 64.0, 16000.0, 3000, true, false, true, false);
        let action = DecisionAction::default_single();

        let initial_a = controller.a_matrix.clone();
        let initial_b = controller.b_vector.clone();
        let initial_t = controller.t;

        // Attempt update in frozen test mode
        controller.update(&state, &action, 1.0, Some(0.5));

        assert_eq!(controller.a_matrix, initial_a);
        assert_eq!(controller.b_vector, initial_b);
        assert_eq!(controller.t, initial_t);
    }

    #[test]
    fn test_direct_advantage_binning() {
        let mut controller = AdaptiveController::default();
        let state = FeatureState::new(0.5, 32.0, 8000.0, 500, true, false, false, false);
        let action = DecisionAction::default_single();

        // 1. RL outperformed raw baseline
        controller.update(&state, &action, 1.0, Some(0.6));
        assert_eq!(controller.rl_greater_than_raw, 1);
        assert_eq!(controller.rl_equal_to_raw, 0);
        assert_eq!(controller.rl_less_than_raw, 0);

        // 2. RL equal to raw baseline
        controller.update(&state, &action, 0.7, Some(0.7));
        assert_eq!(controller.rl_greater_than_raw, 1);
        assert_eq!(controller.rl_equal_to_raw, 1);
        assert_eq!(controller.rl_less_than_raw, 0);

        // 3. RL lower than raw baseline
        controller.update(&state, &action, 0.4, Some(0.9));
        assert_eq!(controller.rl_greater_than_raw, 1);
        assert_eq!(controller.rl_equal_to_raw, 1);
        assert_eq!(controller.rl_less_than_raw, 1);

        let telem = controller.telemetry();
        assert!((telem.advantage.win_rate_percent - 33.333333333333336).abs() < 1e-4);
    }

    #[test]
    fn test_policy_checkpoint_serialization() {
        let temp_dir = std::env::temp_dir();
        let checkpoint_path = temp_dir.join("test_adaptive_rl_policy.json");

        let mut controller = AdaptiveController::default();
        let state = FeatureState::new(0.7, 32.0, 10000.0, 1200, true, false, false, false);
        let action = DecisionAction::default_single();

        controller.update(&state, &action, 0.95, Some(0.75));
        controller.save_checkpoint(&checkpoint_path).expect("Save should succeed");

        let loaded = AdaptiveController::load_checkpoint(&checkpoint_path).expect("Load should succeed");
        assert_eq!(loaded.t, 1);
        assert_eq!(loaded.rl_greater_than_raw, 1);
        assert_eq!(loaded.a_matrix.len(), 45);

        let _ = std::fs::remove_file(checkpoint_path);
    }
}

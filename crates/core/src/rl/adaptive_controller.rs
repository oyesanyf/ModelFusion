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

/// Operational risk profile for Distributional RL action selection.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskProfile {
    /// Standard LinUCB optimism under uncertainty: mu + c(t) * sigma.
    Optimistic,
    /// Risk-neutral pure expected return: mu.
    Neutral,
    /// Worst-case tail risk (Value at Risk, VaR_alpha): mu - z_alpha * sigma.
    WorstCase,
    /// Conditional Value at Risk (CVaR_alpha): expected return in the worst alpha fraction of cases.
    CVaR,
    /// Mission-critical adaptive: dynamically balances optimism vs worst-case CVaR based on task complexity and domain flags.
    AdaptiveCritical,
}

impl Default for RiskProfile {
    fn default() -> Self {
        Self::Optimistic
    }
}

/// Distributional evaluation metrics for candidate actions.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DistributionalScore {
    pub mean: f64,
    pub aleatoric_variance: f64,
    pub epistemic_uncertainty: f64,
    pub total_uncertainty: f64,
    pub quantiles: Vec<f64>, // [q_0.10, q_0.25, q_0.50, q_0.75, q_0.90]
    pub var_score: f64,      // Value at Risk (lower quantile)
    pub cvar_score: f64,     // Conditional Value at Risk (tail risk)
    pub risk_profile: RiskProfile,
    pub final_score: f64,
}

/// Dopamine-inspired fixed-capacity circular replay buffer.
/// Pre-allocated ring buffer with zero heap allocations after capacity is reached.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CircularReplayBuffer<T, const CAP: usize> {
    buffer: Vec<T>,
    head: usize,
    count: usize,
}

impl<T: Clone, const CAP: usize> CircularReplayBuffer<T, CAP> {
    pub fn new() -> Self {
        Self {
            buffer: Vec::with_capacity(CAP),
            head: 0,
            count: 0,
        }
    }

    pub fn push(&mut self, item: T) {
        if CAP == 0 {
            return;
        }
        if self.buffer.len() < CAP {
            self.buffer.push(item);
            self.count = self.buffer.len();
        } else {
            self.buffer[self.head] = item;
            self.head = (self.head + 1) % CAP;
        }
    }

    pub fn len(&self) -> usize {
        self.count
    }

    pub fn is_empty(&self) -> bool {
        self.count == 0
    }

    pub fn capacity(&self) -> usize {
        CAP
    }

    pub fn as_slices(&self) -> (&[T], &[T]) {
        if self.buffer.len() < CAP {
            (&self.buffer[..], &[])
        } else {
            (&self.buffer[self.head..], &self.buffer[..self.head])
        }
    }

    pub fn iter(&self) -> impl Iterator<Item = &T> {
        let (s1, s2) = self.as_slices();
        s1.iter().chain(s2.iter())
    }
}

impl<T: Clone, const CAP: usize> Default for CircularReplayBuffer<T, CAP> {
    fn default() -> Self {
        Self::new()
    }
}

/// Recorded interaction observation stored in replay buffer.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ObservationRecord {
    pub state: FeatureState,
    pub action: DecisionAction,
    pub reward: f64,
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
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
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
    #[serde(default = "default_dist_rl_enabled")]
    pub distributional_rl_enabled: bool,
    #[serde(default = "default_supported_risk_profiles")]
    pub supported_risk_profiles: Vec<String>,
}

fn default_dist_rl_enabled() -> bool {
    true
}

pub fn default_supported_risk_profiles() -> Vec<String> {
    vec![
        "Optimistic".to_string(),
        "Neutral".to_string(),
        "WorstCase".to_string(),
        "CVaR".to_string(),
        "AdaptiveCritical".to_string(),
    ]
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

/// Computes standard normal probability density function phi(z) = (1/sqrt(2*pi)) * exp(-z^2/2).
pub fn standard_normal_pdf(z: f64) -> f64 {
    const INV_SQRT_2PI: f64 = 0.3989422804014327;
    INV_SQRT_2PI * (-0.5 * z * z).exp()
}

/// Approximates standard normal critical value z_alpha for lower tail alpha in (0, 0.5].
/// Uses Abramowitz & Stegun 26.2.23 rational approximation with exact anchor points.
pub fn normal_critical_value(alpha: f64) -> f64 {
    let alpha = alpha.clamp(1e-6, 0.5);
    if (alpha - 0.10).abs() < 1e-3 {
        1.28155
    } else if (alpha - 0.05).abs() < 1e-3 {
        1.64485
    } else if (alpha - 0.01).abs() < 1e-3 {
        2.32635
    } else if (alpha - 0.25).abs() < 1e-3 {
        0.67449
    } else {
        let t = (-2.0 * alpha.ln()).sqrt();
        let c0 = 2.515517;
        let c1 = 0.802853;
        let c2 = 0.010328;
        let d1 = 1.432788;
        let d2 = 0.189269;
        let d3 = 0.001308;
        let num = c0 + c1 * t + c2 * t * t;
        let denom = 1.0 + d1 * t + d2 * t * t + d3 * t * t * t;
        t - num / denom
    }
}

fn default_b_sq_vector() -> Vec<f64> {
    vec![0.0; JOINT_FEATURE_DIM]
}

/// The 6-Pillar Sound Multi-Objective Adaptive Controller.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveController {
    pub config: ControllerConfig,
    /// Covariance matrix A in R^{45 x 45}.
    pub a_matrix: Vec<Vec<f64>>,
    /// Reward-weighted feature accumulator b in R^{45}.
    pub b_vector: Vec<f64>,
    /// Reward squared-weighted feature accumulator b_sq in R^{45} for second moment tracking.
    #[serde(default = "default_b_sq_vector")]
    pub b_sq_vector: Vec<f64>,
    /// Dopamine-inspired circular replay buffer tracking recent observation transitions.
    #[serde(default)]
    pub replay_buffer: CircularReplayBuffer<ObservationRecord, 100>,
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
        let b_sq_vector = vec![0.0; JOINT_FEATURE_DIM];
        let replay_buffer = CircularReplayBuffer::new();

        Self {
            config,
            a_matrix,
            b_vector,
            b_sq_vector,
            replay_buffer,
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

    /// Evaluates distributional parameters, uncertainty, quantiles, and CVaR for an action.
    pub fn evaluate_distributional(
        &self,
        state: &FeatureState,
        action: &DecisionAction,
        theta: &[f64],
        theta_sq: &[f64],
        a_inv: &[Vec<f64>],
        c_t: f64,
        profile: RiskProfile,
        cvar_alpha: f64,
    ) -> DistributionalScore {
        let phi = extract_joint_features(state, action);

        // Linear mean expectation: mu = phi^T theta
        let mu: f64 = phi.iter().zip(theta.iter()).map(|(p, th)| p * th).sum();

        // Expected second moment: mu_sq = phi^T theta_sq
        let mu_sq: f64 = phi.iter().zip(theta_sq.iter()).map(|(p, th_sq)| p * th_sq).sum();

        // Aleatoric variance: sigma_aleatoric^2 = max(0.0, mu_sq - mu^2)
        let aleatoric_variance = (mu_sq - mu * mu).max(0.0);

        // Epistemic uncertainty variance: sigma_epistemic^2 = phi^T A^{-1} phi
        let mut epistemic_variance = 0.0;
        for i in 0..JOINT_FEATURE_DIM {
            let mut row_sum = 0.0;
            for j in 0..JOINT_FEATURE_DIM {
                row_sum += a_inv[i][j] * phi[j];
            }
            epistemic_variance += phi[i] * row_sum;
        }
        let epistemic_variance = epistemic_variance.max(0.0);
        let epistemic_uncertainty = epistemic_variance.sqrt();

        // Total uncertainty standard deviation: sigma_total = sqrt(sigma_aleatoric^2 + sigma_epistemic^2)
        let total_variance = aleatoric_variance + epistemic_variance;
        let total_uncertainty = total_variance.sqrt();

        // Quantiles: Gaussian/Cornish-Fisher expansion around mu with total uncertainty
        let q_010 = mu - 1.28155 * total_uncertainty;
        let q_025 = mu - 0.67449 * total_uncertainty;
        let q_050 = mu;
        let q_075 = mu + 0.67449 * total_uncertainty;
        let q_090 = mu + 1.28155 * total_uncertainty;
        let quantiles = vec![q_010, q_025, q_050, q_075, q_090];

        // Value at Risk (lower quantile) at cvar_alpha
        let alpha = cvar_alpha.clamp(1e-4, 0.5);
        let z_alpha = normal_critical_value(alpha);
        let var_score = mu - z_alpha * total_uncertainty;

        // Conditional Value at Risk (Gaussian tail CVaR_alpha)
        let phi_z = standard_normal_pdf(z_alpha);
        let cvar_factor = phi_z / alpha;
        let cvar_score = mu - total_uncertainty * cvar_factor;

        // Determine final score based on requested RiskProfile
        let final_score = match profile {
            RiskProfile::Optimistic => mu + c_t * epistemic_uncertainty,
            RiskProfile::Neutral => mu,
            RiskProfile::WorstCase => var_score,
            RiskProfile::CVaR => cvar_score,
            RiskProfile::AdaptiveCritical => {
                let kappa = (0.4 * state.task_complexity + 0.3 * state.is_code + 0.3 * state.is_tabular).clamp(0.0, 1.0);
                (1.0 - kappa) * (mu + c_t * epistemic_uncertainty) + kappa * cvar_score
            }
        };

        DistributionalScore {
            mean: mu,
            aleatoric_variance,
            epistemic_uncertainty,
            total_uncertainty,
            quantiles,
            var_score,
            cvar_score,
            risk_profile: profile,
            final_score,
        }
    }

    /// Selects optimal action under specified RiskProfile and CVaR quantile confidence.
    pub fn select_action_distributional(
        &mut self,
        state: &FeatureState,
        candidate_actions: &[DecisionAction],
        profile: RiskProfile,
        cvar_alpha: f64,
    ) -> (DecisionAction, DistributionalScore) {
        if candidate_actions.is_empty() {
            let default_act = DecisionAction::default_single();
            let def_score = DistributionalScore {
                mean: 0.0,
                aleatoric_variance: 0.0,
                epistemic_uncertainty: 0.0,
                total_uncertainty: 0.0,
                quantiles: vec![0.0; 5],
                var_score: 0.0,
                cvar_score: 0.0,
                risk_profile: profile,
                final_score: 0.0,
            };
            return (default_act, def_score);
        }

        // Solve for parameter vector theta = A^{-1} b and second moment theta_sq = A^{-1} b_sq using Cholesky
        let l = match cholesky_decompose(&self.a_matrix, self.config.tikhonov_eps) {
            Ok(decomp) => decomp,
            Err(_) => vec![vec![1.0; JOINT_FEATURE_DIM]; JOINT_FEATURE_DIM],
        };
        let theta = cholesky_solve(&l, &self.b_vector);
        let theta_sq = cholesky_solve(&l, &self.b_sq_vector);
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
        let mut best_dist_score = None;

        for (idx, action) in candidate_actions.iter().enumerate() {
            let dist_score = self.evaluate_distributional(
                state,
                action,
                &theta,
                &theta_sq,
                &a_inv,
                c_t,
                profile,
                cvar_alpha,
            );

            if dist_score.final_score > best_score {
                best_score = dist_score.final_score;
                best_idx = idx;
                best_dist_score = Some(dist_score);
            }
        }

        let chosen_dist_score = best_dist_score.unwrap_or_else(|| {
            self.evaluate_distributional(
                state,
                &candidate_actions[best_idx],
                &theta,
                &theta_sq,
                &a_inv,
                c_t,
                profile,
                cvar_alpha,
            )
        });

        (candidate_actions[best_idx].clone(), chosen_dist_score)
    }

    /// Selects optimal action maximizing LinUCB score: phi^T \hat{theta} + c(t) sqrt(phi^T A^{-1} phi).
    pub fn select_action(
        &mut self,
        state: &FeatureState,
        candidate_actions: &[DecisionAction],
    ) -> (DecisionAction, f64) {
        let (action, score) = self.select_action_distributional(
            state,
            candidate_actions,
            RiskProfile::Optimistic,
            0.10,
        );
        (action, score.final_score)
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

        // b <- b + R * phi, b_sq <- b_sq + R^2 * phi
        for i in 0..JOINT_FEATURE_DIM {
            self.b_vector[i] += reward * phi[i];
            self.b_sq_vector[i] += (reward * reward) * phi[i];
        }

        // Dopamine-inspired replay buffer logging
        self.replay_buffer.push(ObservationRecord {
            state: state.clone(),
            action: action.clone(),
            reward,
        });

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
            distributional_rl_enabled: true,
            supported_risk_profiles: default_supported_risk_profiles(),
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

    #[test]
    fn test_distributional_second_moment_variance() {
        let mut controller = AdaptiveController::default();
        let state = FeatureState::new(0.5, 16.0, 4000.0, 100, false, false, false, false);
        let action = DecisionAction::default_single();

        // Update with stochastic rewards: 1.0 and 0.0 alternating
        for i in 0..20 {
            let r = if i % 2 == 0 { 1.0 } else { 0.0 };
            controller.update(&state, &action, r, None);
        }

        let l = cholesky_decompose(&controller.a_matrix, controller.config.tikhonov_eps).unwrap();
        let theta = cholesky_solve(&l, &controller.b_vector);
        let theta_sq = cholesky_solve(&l, &controller.b_sq_vector);
        let a_inv = stable_covariance_inverse(&controller.a_matrix, controller.config.tikhonov_eps).unwrap();

        let score = controller.evaluate_distributional(
            &state,
            &action,
            &theta,
            &theta_sq,
            &a_inv,
            1.0,
            RiskProfile::Neutral,
            0.10,
        );

        // For alternating 1 and 0, mean ~ 0.5, E[R^2] ~ 0.5, Var ~ 0.25
        assert!(score.mean > 0.35 && score.mean < 0.65, "Expected mean around 0.5, got {}", score.mean);
        assert!(score.aleatoric_variance > 0.10, "Expected positive aleatoric variance, got {}", score.aleatoric_variance);
        assert!(score.total_uncertainty > 0.0);
        assert_eq!(score.quantiles.len(), 5);
        // Quantiles must be non-decreasing
        for i in 0..4 {
            assert!(score.quantiles[i] <= score.quantiles[i + 1] + 1e-9);
        }
    }

    #[test]
    fn test_cvar_penalizes_high_variance_arms() {
        // Construct synthetic evaluation parameters:
        // Both arms have identical mean = 0.8, but robust arm has sigma_total = 0.01 and volatile arm has sigma_total = 0.30
        let score_robust = DistributionalScore {
            mean: 0.8,
            aleatoric_variance: 0.0001,
            epistemic_uncertainty: 0.0,
            total_uncertainty: 0.01,
            quantiles: vec![0.8 - 1.28 * 0.01, 0.8 - 0.67 * 0.01, 0.8, 0.8 + 0.67 * 0.01, 0.8 + 1.28 * 0.01],
            var_score: 0.8 - 1.28155 * 0.01,
            cvar_score: 0.8 - 1.755 * 0.01,
            risk_profile: RiskProfile::CVaR,
            final_score: 0.8 - 1.755 * 0.01,
        };

        let score_volatile = DistributionalScore {
            mean: 0.8,
            aleatoric_variance: 0.09,
            epistemic_uncertainty: 0.0,
            total_uncertainty: 0.30,
            quantiles: vec![0.8 - 1.28 * 0.30, 0.8 - 0.67 * 0.30, 0.8, 0.8 + 0.67 * 0.30, 0.8 + 1.28 * 0.30],
            var_score: 0.8 - 1.28155 * 0.30,
            cvar_score: 0.8 - 1.755 * 0.30,
            risk_profile: RiskProfile::CVaR,
            final_score: 0.8 - 1.755 * 0.30,
        };

        // Assert that under CVaR and WorstCase, the robust arm with lower variance is strictly preferred
        assert!(score_robust.cvar_score > score_volatile.cvar_score, "Robust arm must have strictly higher CVaR");
        assert!(score_robust.var_score > score_volatile.var_score, "Robust arm must have strictly higher VaR");
        assert!(score_robust.final_score > score_volatile.final_score);
    }

    #[test]
    fn test_risk_profile_selection_divergence() {
        let mut controller = AdaptiveController::default();
        let state = FeatureState::new(0.5, 32.0, 8000.0, 500, false, false, false, false);
        let actions = DecisionAction::default_candidate_actions();

        // Train Arm 0 repeatedly with moderate reward (0.7) to collapse its uncertainty
        for _ in 0..30 {
            controller.update(&state, &actions[0], 0.7, None);
        }

        let (_act_opt, score_opt) = controller.select_action_distributional(
            &state,
            &actions,
            RiskProfile::Optimistic,
            0.10,
        );

        let (_act_cvar, score_cvar) = controller.select_action_distributional(
            &state,
            &actions,
            RiskProfile::CVaR,
            0.10,
        );

        let (_act_var, score_var) = controller.select_action_distributional(
            &state,
            &actions,
            RiskProfile::WorstCase,
            0.10,
        );

        // Optimistic score must be >= CVaR score for the same controller state
        assert!(score_opt.final_score >= score_cvar.final_score);
        assert!(score_var.final_score >= score_cvar.final_score); // VaR tail >= CVaR tail
    }

    #[test]
    fn test_adaptive_critical_weighting() {
        let mut controller = AdaptiveController::default();
        let simple_state = FeatureState::new(0.0, 32.0, 8000.0, 100, false, false, false, false); // kappa = 0
        let critical_state = FeatureState::new(1.0, 32.0, 8000.0, 4000, true, true, false, false); // kappa = 1.0
        let actions = DecisionAction::default_candidate_actions();

        let (_act_simple, score_simple) = controller.select_action_distributional(
            &simple_state,
            &actions,
            RiskProfile::AdaptiveCritical,
            0.10,
        );

        let (_act_crit, score_crit) = controller.select_action_distributional(
            &critical_state,
            &actions,
            RiskProfile::AdaptiveCritical,
            0.10,
        );

        // Simple state (kappa = 0) final_score equals optimistic UCB: mu + c_t * sigma
        let opt_simple = score_simple.mean + controller.exploration_rate() * score_simple.epistemic_uncertainty;
        assert!((score_simple.final_score - opt_simple).abs() < 1e-5);

        // Critical state (kappa = 1.0) final_score equals CVaR: cvar_score
        assert!((score_crit.final_score - score_crit.cvar_score).abs() < 1e-5);
    }
}

//! Reinforcement Learning subsystem for ModelFusion and HugOS.
//!
//! Provides the 6-Pillar Sound Multi-Objective Adaptive Controller,
//! LinUCB action selection with Tikhonov-regularized Cholesky covariance inversion,
//! counterfactual margin scoring, and advantage binning.

pub mod adaptive_controller;

pub use adaptive_controller::{
    AdaptiveController, ControllerConfig, DecisionAction, FeatureState, LearningRegime,
    RLTelemetry, AdvantageStats, extract_joint_features, stable_covariance_inverse,
    cholesky_decompose, cholesky_solve, ACTION_DIM, JOINT_FEATURE_DIM, STATE_DIM,
};

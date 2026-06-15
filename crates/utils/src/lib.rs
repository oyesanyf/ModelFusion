//! Utility helpers for ModelFusion.
//!
//! Modules:
//! - [`folder_manager`] — directory scaffolding and backup management
//! - [`performance`]    — operation timing and metrics tracking
//! - [`rate_limiter`]   — adaptive sliding-window rate limiting

pub mod folder_manager;
pub mod performance;
pub mod rate_limiter;

pub use folder_manager::{FileInfo, FolderManager};
pub use performance::{OperationStats, OverallStats, PerformanceMonitor};
pub use rate_limiter::AdaptiveRateLimiter;

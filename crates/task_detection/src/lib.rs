//! Task-type detection from natural language prompts.
//!
//! Modules:
//! - [`keywords`]  — task keyword pattern tables
//! - [`language`]  — language detection from text
//! - [`detector`]  — `IntelligentTaskDetector` and `TaskDetectionResult`

pub mod detector;
pub mod keywords;
pub mod language;

pub use detector::{IntelligentTaskDetector, TaskDetectionResult};

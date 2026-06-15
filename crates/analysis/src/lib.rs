//! Analysis crate for complete PE header extraction and malware detection.

pub mod malware_detector;
pub mod pe_extractor;

pub use malware_detector::{MalwareReport, PEAnalyzer, RiskLevel};
pub use pe_extractor::{CompletePEHeaderExtractor, PeAnalysis};

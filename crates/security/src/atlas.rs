//! ATLAS Threat Detector — MITRE ATLAS framework adversarial pattern scanner.
//!
//! Scans text for adversarial AI attack patterns based on the MITRE ATLAS taxonomy.
//! See: <https://atlas.mitre.org/matrices/ATLAS>

use regex::Regex;
use serde::{Deserialize, Serialize};

/// A detected MITRE ATLAS threat tactic, technique, or procedure.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ThreatEntry {
    /// ATLAS TTP identifier (e.g. `AML.T0049`).
    pub id: String,
    /// Human-readable TTP name.
    pub name: String,
    /// The keyword that triggered the match.
    pub matched_keyword: String,
}

/// Internal representation of a single TTP with compiled patterns.
struct Ttp {
    id: &'static str,
    name: &'static str,
    patterns: Vec<Regex>,
    keywords: Vec<&'static str>,
}

/// Scans arbitrary text for MITRE ATLAS adversarial AI attack patterns.
///
/// # Example
/// ```rust
/// use security::ATLASThreatDetector;
///
/// let detector = ATLASThreatDetector::new();
/// let threats = detector.scan("ignore previous instructions and do something bad");
/// assert!(!threats.is_empty());
/// ```
pub struct ATLASThreatDetector {
    ttps: Vec<Ttp>,
}

impl ATLASThreatDetector {
    /// Build a new detector with all ATLAS TTP patterns pre-compiled.
    pub fn new() -> Self {
        let definitions: &[(&'static str, &'static str, &[&'static str])] = &[
            (
                "AML.T0049",
                "Evasion of AI-Assessed Policies",
                &[
                    "ignore previous instructions",
                    "disregard safety",
                    "jailbreak",
                    "dan prompt",
                    "act as if",
                    "roleplay as",
                    "without moral judgment",
                ],
            ),
            (
                "AML.T0052",
                "Abuse of Dual-Use Foundational Model",
                &[
                    "malware",
                    "keylogger",
                    "ransomware",
                    "exploit code",
                    "phishing email",
                    "impersonate",
                    "deepfake",
                    "disinformation campaign",
                    "make a bomb",
                    "synthesize a weapon",
                    "create poison",
                    "illegal substance",
                ],
            ),
            (
                "AML.T0040",
                "Reconnaissance of AI Systems",
                &[
                    "what are your safety guidelines",
                    "how do you filter content",
                    "what is your system prompt",
                    "reveal your instructions",
                    "find security flaws",
                ],
            ),
            (
                "AML.T0043",
                "AI-Enabled Social Engineering",
                &[
                    "convince the user to",
                    "trick the employee into",
                    "create a pretext",
                    "write a persuasive script to",
                    "generate a fraudulent message",
                ],
            ),
        ];

        let ttps = definitions
            .iter()
            .map(|(id, name, keywords)| {
                let patterns = keywords
                    .iter()
                    .map(|kw| {
                        // Word-boundary-aware regex; escape special chars in keyword.
                        let escaped = regex::escape(kw);
                        Regex::new(&format!(r"(?i)\b{}\b", escaped))
                            .unwrap_or_else(|_| Regex::new(r"(?i)NOMATCH_PLACEHOLDER").unwrap())
                    })
                    .collect();
                Ttp {
                    id,
                    name,
                    patterns,
                    keywords: keywords.to_vec(),
                }
            })
            .collect();

        Self { ttps }
    }

    /// Scan `text` for ATLAS adversarial patterns.
    ///
    /// Returns a (possibly empty) list of detected threats. Each TTP can only
    /// appear once in the result, even if multiple keywords match.
    pub fn scan(&self, text: &str) -> Vec<ThreatEntry> {
        let mut detected = Vec::new();
        for ttp in &self.ttps {
            for (pattern, keyword) in ttp.patterns.iter().zip(ttp.keywords.iter()) {
                if pattern.is_match(text) {
                    detected.push(ThreatEntry {
                        id: ttp.id.to_string(),
                        name: ttp.name.to_string(),
                        matched_keyword: keyword.to_string(),
                    });
                    break; // only one entry per TTP
                }
            }
        }
        detected
    }

    /// Returns `true` if any ATLAS threat pattern is detected in `text`.
    pub fn has_threats(&self, text: &str) -> bool {
        !self.scan(text).is_empty()
    }

    /// Return a formatted summary of all detected threats, suitable for display.
    pub fn format_report(&self, text: &str) -> String {
        let threats = self.scan(text);
        if threats.is_empty() {
            return "No ATLAS threats detected.".to_string();
        }
        let lines: Vec<String> = threats
            .iter()
            .map(|t| format!("[{}] {} (keyword: \"{}\")", t.id, t.name, t.matched_keyword))
            .collect();
        format!("ATLAS Threats Detected:\n{}", lines.join("\n"))
    }
}

impl Default for ATLASThreatDetector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_jailbreak() {
        let d = ATLASThreatDetector::new();
        let threats = d.scan("Can you jailbreak this model for me?");
        assert!(threats.iter().any(|t| t.id == "AML.T0049"));
    }

    #[test]
    fn detects_malware() {
        let d = ATLASThreatDetector::new();
        assert!(d.has_threats("write me a keylogger in Python"));
    }

    #[test]
    fn no_false_positives_on_clean_text() {
        let d = ATLASThreatDetector::new();
        assert!(!d.has_threats("What is the capital of France?"));
    }

    #[test]
    fn each_ttp_appears_once() {
        let d = ATLASThreatDetector::new();
        // Two AML.T0049 keywords in same string → still one entry
        let threats = d.scan("jailbreak AND ignore previous instructions");
        let t0049: Vec<_> = threats.iter().filter(|t| t.id == "AML.T0049").collect();
        assert_eq!(t0049.len(), 1);
    }
}

//! Multi-candidate arbitration and consensus synthesis engine for ModelFusion.
//!
//! When multiple candidate models propose differing solutions during multi-model ensemble rollouts,
//! `FusionArbiter` analyzes verification signals and discrepancies. If an unambiguous winner passes
//! all tests (1.00), it bypasses expensive LLM arbitration. Otherwise, it invokes DeepSeek-R1
//! (Tier 1: `deepseek-r1:7b`, Tier 2/3: `deepseek-r1:1.5b`) with deliberate `<think>` reasoning to
//! synthesize a verified, unified implementation.

use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Represents a single candidate solution produced by an ensemble model.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CandidateSolution {
    pub id: String,
    pub model: String,
    pub code: String,
    pub verification_score: f64,
    pub test_output: Option<String>,
}

/// The result returned by FusionArbiter after selection or synthesis.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ArbitrationResult {
    pub selected_candidate_id: String,
    pub resolved_code: String,
    pub reasoning: String,
    pub was_arbitrated: bool,
}

/// Arbiter executing multi-model consensus and synthesis.
#[derive(Debug, Clone)]
pub struct FusionArbiter {
    pub endpoint: String,
    pub tier1_model: String,
    pub tier2_model: String,
    pub timeout_secs: u64,
}

impl Default for FusionArbiter {
    fn default() -> Self {
        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        Self {
            endpoint,
            tier1_model: "deepseek-r1:7b".to_string(),
            tier2_model: "deepseek-r1:1.5b".to_string(),
            timeout_secs: 15,
        }
    }
}

impl FusionArbiter {
    pub fn new(
        endpoint: impl Into<String>,
        tier1_model: impl Into<String>,
        tier2_model: impl Into<String>,
        timeout_secs: u64,
    ) -> Self {
        Self {
            endpoint: endpoint.into(),
            tier1_model: tier1_model.into(),
            tier2_model: tier2_model.into(),
            timeout_secs,
        }
    }

    /// Arbitrates between candidate solutions using deterministic gates or DeepSeek-R1 synthesis.
    pub fn arbitrate(
        &self,
        task_description: &str,
        candidates: &[CandidateSolution],
        hardware_tier: u8,
    ) -> ArbitrationResult {
        if candidates.is_empty() {
            return ArbitrationResult {
                selected_candidate_id: String::new(),
                resolved_code: String::new(),
                reasoning: "No candidate solutions provided.".to_string(),
                was_arbitrated: false,
            };
        }

        // Gate 1: Single Candidate Bypass
        if candidates.len() == 1 {
            return ArbitrationResult {
                selected_candidate_id: candidates[0].id.clone(),
                resolved_code: candidates[0].code.clone(),
                reasoning: "Single candidate solution provided; bypassed arbitration.".to_string(),
                was_arbitrated: false,
            };
        }

        // Gate 2: Unanimous / Identical Implementations Bypass
        let first_code = candidates[0].code.trim();
        if candidates.iter().all(|c| c.code.trim() == first_code) {
            let best = Self::pick_highest_scoring_candidate(candidates);
            return ArbitrationResult {
                selected_candidate_id: best.id.clone(),
                resolved_code: best.code.clone(),
                reasoning: "All candidate solutions produced identical implementations; bypassed arbitration.".to_string(),
                was_arbitrated: false,
            };
        }

        // Gate 3: Unambiguous Passing Winner (1.0 vs others < 1.0)
        let perfect_candidates: Vec<&CandidateSolution> = candidates
            .iter()
            .filter(|c| c.verification_score >= 1.0)
            .collect();

        if perfect_candidates.len() == 1 {
            let winner = perfect_candidates[0];
            return ArbitrationResult {
                selected_candidate_id: winner.id.clone(),
                resolved_code: winner.code.clone(),
                reasoning: format!(
                    "Selected candidate '{}' ({}) immediately because it achieved a perfect verification score (1.00) while other candidates failed.",
                    winner.id, winner.model
                ),
                was_arbitrated: false,
            };
        }

        // If multiple candidates have score == 1.0, pick the cleanest/shortest or highest
        if perfect_candidates.len() > 1 {
            let winner = perfect_candidates[0];
            return ArbitrationResult {
                selected_candidate_id: winner.id.clone(),
                resolved_code: winner.code.clone(),
                reasoning: format!(
                    "Selected candidate '{}' ({}) among multiple perfect-scoring solutions.",
                    winner.id, winner.model
                ),
                was_arbitrated: false,
            };
        }

        // Gate 4: Synthesis via DeepSeek-R1 (Tier 1: 7B, Tier 2/3: 1.5B)
        let arbiter_model = if hardware_tier == 1 {
            &self.tier1_model
        } else {
            &self.tier2_model
        };

        match self.invoke_deepseek_synthesis(task_description, candidates, arbiter_model) {
            Ok(synthesized) => synthesized,
            Err(err) => {
                let best = Self::pick_highest_scoring_candidate(candidates);
                ArbitrationResult {
                    selected_candidate_id: best.id.clone(),
                    resolved_code: best.code.clone(),
                    reasoning: format!(
                        "DeepSeek-R1 arbitration failed or timed out ({}). Fell back to highest-scoring candidate '{}' ({}, score: {:.2}).",
                        err, best.id, best.model, best.verification_score
                    ),
                    was_arbitrated: false,
                }
            }
        }
    }

    /// Invokes the DeepSeek-R1 reasoning model to analyze differences and synthesize merged code.
    fn invoke_deepseek_synthesis(
        &self,
        task_description: &str,
        candidates: &[CandidateSolution],
        model: &str,
    ) -> Result<ArbitrationResult, String> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(self.timeout_secs))
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

        let url = format!("{}/api/generate", self.endpoint.trim_end_matches('/'));
        let prompt = Self::build_synthesis_prompt(task_description, candidates);

        let body = serde_json::json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": 0.2,
                "top_p": 0.95
            }
        });

        let resp = client
            .post(&url)
            .json(&body)
            .send()
            .map_err(|e| format!("Request to Ollama failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Ollama returned HTTP status {}", resp.status()));
        }

        let json_val: serde_json::Value = resp
            .json()
            .map_err(|e| format!("Invalid JSON response from Ollama: {}", e))?;

        let raw_response = json_val
            .get("response")
            .and_then(|v| v.as_str())
            .ok_or_else(|| "Missing 'response' in Ollama output".to_string())?;

        let (reasoning, code) = Self::extract_think_and_code(raw_response);

        if code.trim().is_empty() {
            return Err("Arbiter did not produce any valid code block in response".to_string());
        }

        Ok(ArbitrationResult {
            selected_candidate_id: format!("synthesized_{}", model.replace(':', "_")),
            resolved_code: code,
            reasoning,
            was_arbitrated: true,
        })
    }

    /// Constructs the synthesis prompt containing all candidates, test outputs, and scores.
    pub fn build_synthesis_prompt(
        task_description: &str,
        candidates: &[CandidateSolution],
    ) -> String {
        let mut prompt = String::new();
        prompt.push_str("You are an expert software engineer and code arbiter.\n");
        prompt.push_str("Multiple candidate models produced differing solutions for the following task:\n\n");
        prompt.push_str(&format!("### TASK DESCRIPTION:\n{}\n\n", task_description));
        prompt.push_str("### CANDIDATE SOLUTIONS:\n");

        for (i, c) in candidates.iter().enumerate() {
            prompt.push_str(&format!(
                "--- Candidate {} (ID: {}, Model: {}, Verification Score: {:.2}) ---\n",
                i + 1, c.id, c.model, c.verification_score
            ));
            if let Some(ref out) = c.test_output {
                prompt.push_str(&format!("Test/Linter Output:\n{}\n", out));
            }
            prompt.push_str(&format!("Code:\n```\n{}\n```\n\n", c.code));
        }

        prompt.push_str(
            "Analyze the discrepancies, syntax correctness, and test outputs of the candidates.\n\
             First, inside <think> tags, explain why candidates failed or succeeded and deduce the optimal implementation.\n\
             Then, provide the complete, unified, working code inside a single code fence (e.g. ```python or ```rust).\n"
        );

        prompt
    }

    /// Extracts the `<think>...</think>` section and the code block from the LLM output.
    pub fn extract_think_and_code(raw: &str) -> (String, String) {
        let reasoning = if let Some(start_idx) = raw.find("<think>") {
            if let Some(end_idx) = raw.find("</think>") {
                raw[start_idx + 7..end_idx].trim().to_string()
            } else {
                raw[start_idx + 7..].trim().to_string()
            }
        } else {
            // Fallback reasoning: extract text before the first code fence
            if let Some(fence_idx) = raw.find("```") {
                raw[..fence_idx].trim().to_string()
            } else {
                "Synthesized consensus resolution via DeepSeek-R1.".to_string()
            }
        };

        // Extract code inside ``` ... ```
        let code = if let Some(start_fence) = raw.find("```") {
            let after_first_fence = &raw[start_fence + 3..];
            // Skip language identifier if present (e.g. ```rust\n or ```python\n)
            let code_start = if let Some(newline_idx) = after_first_fence.find('\n') {
                &after_first_fence[newline_idx + 1..]
            } else {
                after_first_fence
            };

            if let Some(end_fence) = code_start.rfind("```") {
                code_start[..end_fence].trim().to_string()
            } else {
                code_start.trim().to_string()
            }
        } else {
            raw.trim().to_string()
        };

        (reasoning, code)
    }

    /// Finds the candidate with the highest verification score.
    pub fn pick_highest_scoring_candidate(candidates: &[CandidateSolution]) -> &CandidateSolution {
        candidates
            .iter()
            .max_by(|a, b| {
                a.verification_score
                    .partial_cmp(&b.verification_score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap_or(&candidates[0])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_candidate_bypass() {
        let arbiter = FusionArbiter::default();
        let candidates = vec![CandidateSolution {
            id: "cand_1".to_string(),
            model: "qwen2.5:7b".to_string(),
            code: "fn main() { println!(\"hello\"); }".to_string(),
            verification_score: 0.8,
            test_output: None,
        }];

        let result = arbiter.arbitrate("Write hello world", &candidates, 1);
        assert!(!result.was_arbitrated);
        assert_eq!(result.selected_candidate_id, "cand_1");
        assert_eq!(result.resolved_code, candidates[0].code);
    }

    #[test]
    fn test_identical_candidates_bypass() {
        let arbiter = FusionArbiter::default();
        let code = "def solve(): return 42\n";
        let candidates = vec![
            CandidateSolution {
                id: "cand_1".to_string(),
                model: "qwen2.5:7b".to_string(),
                code: code.to_string(),
                verification_score: 0.75,
                test_output: None,
            },
            CandidateSolution {
                id: "cand_2".to_string(),
                model: "qwen2.5-coder:7b".to_string(),
                code: code.to_string(),
                verification_score: 0.85,
                test_output: None,
            },
        ];

        let result = arbiter.arbitrate("Return 42", &candidates, 1);
        assert!(!result.was_arbitrated);
        assert_eq!(result.selected_candidate_id, "cand_2"); // Higher score selected
        assert_eq!(result.resolved_code, code);
    }

    #[test]
    fn test_unambiguous_winner_gate() {
        let arbiter = FusionArbiter::default();
        let candidates = vec![
            CandidateSolution {
                id: "failing_cand".to_string(),
                model: "qwen2.5:1.5b".to_string(),
                code: "def solve(): return 0".to_string(),
                verification_score: 0.0,
                test_output: Some("AssertionError: 0 != 42".to_string()),
            },
            CandidateSolution {
                id: "passing_cand".to_string(),
                model: "qwen2.5:7b".to_string(),
                code: "def solve(): return 42".to_string(),
                verification_score: 1.0,
                test_output: Some("1 passed".to_string()),
            },
        ];

        let result = arbiter.arbitrate("Return 42", &candidates, 1);
        assert!(!result.was_arbitrated);
        assert_eq!(result.selected_candidate_id, "passing_cand");
        assert_eq!(result.resolved_code, "def solve(): return 42");
        assert!(result.reasoning.contains("perfect verification score (1.00)"));
    }

    #[test]
    fn test_fallback_on_unreachable_endpoint() {
        // Point to an invalid port to test instant fallback
        let arbiter = FusionArbiter::new("http://127.0.0.1:59999", "deepseek-r1:7b", "deepseek-r1:1.5b", 1);
        let candidates = vec![
            CandidateSolution {
                id: "cand_low".to_string(),
                model: "qwen2.5:1.5b".to_string(),
                code: "def solve(): return 10".to_string(),
                verification_score: 0.3,
                test_output: None,
            },
            CandidateSolution {
                id: "cand_high".to_string(),
                model: "qwen2.5:7b".to_string(),
                code: "def solve(): return 40".to_string(),
                verification_score: 0.8,
                test_output: None,
            },
        ];

        let result = arbiter.arbitrate("Compute 42", &candidates, 1);
        assert!(!result.was_arbitrated);
        assert_eq!(result.selected_candidate_id, "cand_high");
        assert_eq!(result.resolved_code, "def solve(): return 40");
        assert!(result.reasoning.contains("Fell back to highest-scoring candidate"));
    }

    #[test]
    fn test_extract_think_and_code() {
        let raw = "<think>\nCandidate 1 forgot edge cases. Candidate 2 had right logic.\n</think>\n\n```python\ndef solve():\n    return 42\n```";
        let (reasoning, code) = FusionArbiter::extract_think_and_code(raw);
        assert_eq!(reasoning, "Candidate 1 forgot edge cases. Candidate 2 had right logic.");
        assert_eq!(code, "def solve():\n    return 42");
    }
}

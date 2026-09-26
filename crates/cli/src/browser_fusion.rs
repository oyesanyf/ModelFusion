//! Multi-model consensus and fusion arbitration for autonomous browser operations.
//!
//! Synthesizes decisions from specialized models:
//! - Fast NLP DOM Specialist (`qwen2.5:7b` / `qwen2.5:14b`): Set-of-Mark parsing and quick DOM action proposal.
//! - Vision Specialist (`qwen2.5-vl` / `llama3.2-vision`): Visual layout grounding and screenshot verification.
//! - Deep Reasoning Arbiter (`deepseek-r1:7b` / `deepseek-r1:1.5b` or `qwen2.5:32b`): Multi-step planning and discrepancy resolution.

use modelfusion_core::browser::BrowserAction;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Category of model specialist participating in browser fusion.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SpecialistType {
    DomSpecialist,
    VisionSpecialist,
    PlanningSpecialist,
}

/// A proposed action submitted by a specialist model.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BrowserActionProposal {
    pub model: String,
    pub specialist: SpecialistType,
    pub action: BrowserAction,
    pub rationale: String,
    pub confidence: f64,
}

/// Type of consensus reached by the browser fusion arbiter.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConsensusType {
    /// Only one specialist submitted an action.
    SingleBypass,
    /// All participating specialists proposed equivalent actions.
    Unanimous,
    /// Clear high-confidence winner among conflicting proposals.
    DominantWinner,
    /// DeepSeek-R1 synthesized consensus resolution across conflicting signals.
    ArbiterSynthesized,
    /// Fallback to highest confidence candidate when synthesis is unreachable.
    FallbackHighestConfidence,
}

/// The final arbitration decision for a browser operation step.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BrowserArbitrationDecision {
    pub selected_action: BrowserAction,
    pub consensus: ConsensusType,
    pub confidence: f64,
    pub reasoning: String,
    pub participating_models: Vec<String>,
}

/// Browser Fusion Arbiter coordinating multi-model consensus for web navigation.
#[derive(Clone)]
pub struct BrowserFusionArbiter {
    pub endpoint: String,
    pub dom_model: String,
    pub vision_model: String,
    pub reasoning_model: String,
    pub timeout_secs: u64,
}

impl Default for BrowserFusionArbiter {
    fn default() -> Self {
        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        Self {
            endpoint,
            dom_model: "qwen2.5:7b".to_string(),
            vision_model: "qwen2.5-vl".to_string(),
            reasoning_model: "deepseek-r1:7b".to_string(),
            timeout_secs: 20,
        }
    }
}

impl BrowserFusionArbiter {
    pub fn new(
        endpoint: impl Into<String>,
        dom_model: impl Into<String>,
        vision_model: impl Into<String>,
        reasoning_model: impl Into<String>,
        timeout_secs: u64,
    ) -> Self {
        Self {
            endpoint: endpoint.into(),
            dom_model: dom_model.into(),
            vision_model: vision_model.into(),
            reasoning_model: reasoning_model.into(),
            timeout_secs,
        }
    }

    /// Arbitrates between candidate browser actions using deterministic consensus gates or DeepSeek-R1.
    pub fn arbitrate(
        &self,
        goal: &str,
        page_context: &str,
        proposals: &[BrowserActionProposal],
    ) -> BrowserArbitrationDecision {
        if proposals.is_empty() {
            return BrowserArbitrationDecision {
                selected_action: BrowserAction::GetCleanDom { max_chars: Some(10_000) },
                consensus: ConsensusType::FallbackHighestConfidence,
                confidence: 0.1,
                reasoning: "No action proposals provided; defaulted to refreshing DOM.".to_string(),
                participating_models: Vec::new(),
            };
        }

        let participating_models: Vec<String> = proposals.iter().map(|p| p.model.clone()).collect();

        // Gate 1: Single Candidate Bypass
        if proposals.len() == 1 {
            let single = &proposals[0];
            return BrowserArbitrationDecision {
                selected_action: single.action.clone(),
                consensus: ConsensusType::SingleBypass,
                confidence: single.confidence,
                reasoning: format!("Single proposal from '{}'; bypassed arbitration.", single.model),
                participating_models,
            };
        }

        // Gate 2: Unanimous Action Check
        let first_action = &proposals[0].action;
        let is_unanimous = proposals.iter().all(|p| &p.action == first_action);
        if is_unanimous {
            let avg_conf = proposals.iter().map(|p| p.confidence).sum::<f64>() / (proposals.len() as f64);
            return BrowserArbitrationDecision {
                selected_action: first_action.clone(),
                consensus: ConsensusType::Unanimous,
                confidence: avg_conf,
                reasoning: format!(
                    "Unanimous agreement across all {} specialists on proposed action.",
                    proposals.len()
                ),
                participating_models,
            };
        }

        // Gate 3: Clear Dominant Winner (confidence >= 0.85 and at least 0.35 higher than next best)
        let mut sorted = proposals.to_vec();
        sorted.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap_or(std::cmp::Ordering::Equal));
        if sorted[0].confidence >= 0.85 && (sorted[0].confidence - sorted[1].confidence) >= 0.35 {
            let best = &sorted[0];
            return BrowserArbitrationDecision {
                selected_action: best.action.clone(),
                consensus: ConsensusType::DominantWinner,
                confidence: best.confidence,
                reasoning: format!(
                    "Dominant proposal from '{}' (confidence: {:.2} vs {:.2}). Rationale: {}",
                    best.model, best.confidence, sorted[1].confidence, best.rationale
                ),
                participating_models,
            };
        }

        // Gate 4: DeepSeek-R1 / Qwen 2.5 32B Multi-Modal Reasoning Synthesis
        match self.invoke_reasoning_arbiter(goal, page_context, proposals) {
            Ok(decision) => decision,
            Err(err) => {
                let best = &sorted[0];
                BrowserArbitrationDecision {
                    selected_action: best.action.clone(),
                    consensus: ConsensusType::FallbackHighestConfidence,
                    confidence: best.confidence * 0.8,
                    reasoning: format!(
                        "Reasoning arbitration failed ({}). Fell back to highest-confidence proposal from '{}': {}",
                        err, best.model, best.rationale
                    ),
                    participating_models,
                }
            }
        }
    }

    /// Invokes the DeepSeek-R1 reasoning model to analyze specialist discrepancies and choose the optimal action.
    fn invoke_reasoning_arbiter(
        &self,
        goal: &str,
        page_context: &str,
        proposals: &[BrowserActionProposal],
    ) -> Result<BrowserArbitrationDecision, String> {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(self.timeout_secs))
            .build()
            .map_err(|e| format!("HTTP client build failed: {}", e))?;

        let prompt = Self::build_arbitration_prompt(goal, page_context, proposals);
        let url = format!("{}/api/generate", self.endpoint.trim_end_matches('/'));

        let body = serde_json::json!({
            "model": self.reasoning_model,
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
            .map_err(|e| format!("Request to Ollama arbiter failed: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Arbiter model returned HTTP status {}", resp.status()));
        }

        let json_val: serde_json::Value = resp
            .json()
            .map_err(|e| format!("Invalid JSON response from arbiter: {}", e))?;

        let raw_response = json_val
            .get("response")
            .and_then(|v| v.as_str())
            .ok_or_else(|| "Missing 'response' in arbiter output".to_string())?;

        let (think, selected_action) = Self::extract_think_and_action(raw_response, proposals)?;

        let participating_models: Vec<String> = proposals.iter().map(|p| p.model.clone()).collect();

        Ok(BrowserArbitrationDecision {
            selected_action,
            consensus: ConsensusType::ArbiterSynthesized,
            confidence: 0.92,
            reasoning: think,
            participating_models,
        })
    }

    /// Constructs the synthesis prompt for the reasoning arbiter.
    pub fn build_arbitration_prompt(
        goal: &str,
        page_context: &str,
        proposals: &[BrowserActionProposal],
    ) -> String {
        let mut prompt = String::new();
        prompt.push_str("You are an expert autonomous web agent arbiter.\n");
        prompt.push_str("A browser task is in progress, and specialized models have submitted differing proposed actions.\n\n");
        prompt.push_str(&format!("### USER GOAL:\n{}\n\n", goal));
        prompt.push_str(&format!("### CURRENT PAGE CONTEXT:\n{}\n\n", page_context));
        prompt.push_str("### SPECIALIST PROPOSALS:\n");

        for (i, p) in proposals.iter().enumerate() {
            let spec_name = match p.specialist {
                SpecialistType::DomSpecialist => "DOM Specialist",
                SpecialistType::VisionSpecialist => "Vision Specialist",
                SpecialistType::PlanningSpecialist => "Planning Specialist",
            };
            prompt.push_str(&format!(
                "Proposal {} (Model: {}, Role: {}, Confidence: {:.2}):\n- Action: {:?}\n- Rationale: {}\n\n",
                i + 1, p.model, spec_name, p.confidence, p.action, p.rationale
            ));
        }

        prompt.push_str(
            "Analyze the proposals against the current page state and overall goal.\n\
             Inside <think>...</think> tags, explain which proposal is safest and most effective, or formulate the optimal action.\n\
             Then output the selected proposal number as 'SELECT: <number>' or provide the JSON action inside ```json ... ```.\n"
        );

        prompt
    }

    /// Parses `<think>` reasoning and identifies the chosen action.
    pub fn extract_think_and_action(
        raw: &str,
        proposals: &[BrowserActionProposal],
    ) -> Result<(String, BrowserAction), String> {
        let reasoning = if let Some(start_idx) = raw.find("<think>") {
            if let Some(end_idx) = raw.find("</think>") {
                raw[start_idx + 7..end_idx].trim().to_string()
            } else {
                raw[start_idx + 7..].trim().to_string()
            }
        } else {
            "Consensus synthesized by DeepSeek-R1.".to_string()
        };

        // Check for "SELECT: <N>"
        if let Some(pos) = raw.find("SELECT:") {
            let rest = raw[pos + 7..].trim();
            let num_str: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
            if let Ok(idx) = num_str.parse::<usize>() {
                if idx >= 1 && idx <= proposals.len() {
                    return Ok((reasoning, proposals[idx - 1].action.clone()));
                }
            }
        }

        // Check for JSON action fence
        if let Some(start_fence) = raw.find("```json") {
            let after = &raw[start_fence + 7..];
            if let Some(end_fence) = after.find("```") {
                let json_str = after[..end_fence].trim();
                if let Ok(parsed_action) = serde_json::from_str::<BrowserAction>(json_str) {
                    return Ok((reasoning, parsed_action));
                }
            }
        }

        // Fallback: choose highest confidence proposal
        if let Some(best) = proposals.iter().max_by(|a, b| a.confidence.partial_cmp(&b.confidence).unwrap()) {
            Ok((reasoning, best.action.clone()))
        } else {
            Err("Failed to resolve action from arbiter response".to_string())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use modelfusion_core::browser::ElementTarget;

    #[test]
    fn test_single_proposal_bypass() {
        let arbiter = BrowserFusionArbiter::default();
        let proposals = vec![BrowserActionProposal {
            model: "qwen2.5:7b".to_string(),
            specialist: SpecialistType::DomSpecialist,
            action: BrowserAction::Click {
                target: ElementTarget::ByMark(1),
            },
            rationale: "Target is the search button".to_string(),
            confidence: 0.95,
        }];

        let decision = arbiter.arbitrate("Search models", "Page with search button", &proposals);
        assert_eq!(decision.consensus, ConsensusType::SingleBypass);
        assert_eq!(decision.selected_action, proposals[0].action);
    }

    #[test]
    fn test_unanimous_consensus_gate() {
        let arbiter = BrowserFusionArbiter::default();
        let action = BrowserAction::Navigate {
            url: "https://huggingface.co".to_string(),
        };
        let proposals = vec![
            BrowserActionProposal {
                model: "qwen2.5:7b".to_string(),
                specialist: SpecialistType::DomSpecialist,
                action: action.clone(),
                rationale: "Go to homepage".to_string(),
                confidence: 0.88,
            },
            BrowserActionProposal {
                model: "qwen2.5-vl".to_string(),
                specialist: SpecialistType::VisionSpecialist,
                action: action.clone(),
                rationale: "Homepage navigation required".to_string(),
                confidence: 0.92,
            },
        ];

        let decision = arbiter.arbitrate("Visit HuggingFace", "Blank tab", &proposals);
        assert_eq!(decision.consensus, ConsensusType::Unanimous);
        assert_eq!(decision.selected_action, action);
    }

    #[test]
    fn test_dominant_winner_gate() {
        let arbiter = BrowserFusionArbiter::default();
        let winning_action = BrowserAction::Click {
            target: ElementTarget::BySelector("#login-button".to_string()),
        };
        let proposals = vec![
            BrowserActionProposal {
                model: "qwen2.5:7b".to_string(),
                specialist: SpecialistType::DomSpecialist,
                action: winning_action.clone(),
                rationale: "Clear login button selector in DOM".to_string(),
                confidence: 0.95,
            },
            BrowserActionProposal {
                model: "qwen2.5-vl".to_string(),
                specialist: SpecialistType::VisionSpecialist,
                action: BrowserAction::Scroll {
                    direction: "down".to_string(),
                    amount: Some(300),
                },
                rationale: "Visual ambiguity".to_string(),
                confidence: 0.40,
            },
        ];

        let decision = arbiter.arbitrate("Login", "Page with login button", &proposals);
        assert_eq!(decision.consensus, ConsensusType::DominantWinner);
        assert_eq!(decision.selected_action, winning_action);
    }

    #[test]
    fn test_extract_think_and_action() {
        let raw = "<think>\nDOM Specialist identified correct button, vision model was uncertain.\n</think>\n\nSELECT: 1";
        let proposals = vec![BrowserActionProposal {
            model: "qwen2.5:7b".to_string(),
            specialist: SpecialistType::DomSpecialist,
            action: BrowserAction::Click {
                target: ElementTarget::ByMark(5),
            },
            rationale: "Search button".to_string(),
            confidence: 0.85,
        }];

        let (think, action) = BrowserFusionArbiter::extract_think_and_action(raw, &proposals).unwrap();
        assert!(think.contains("DOM Specialist identified correct button"));
        assert_eq!(action, proposals[0].action);
    }

    #[test]
    fn test_find_browser_launcher_bat() {
        let bat = find_browser_launcher_bat();
        assert!(bat.is_some(), "Should locate hugos-browser.bat");
    }
}

/// Locates the `hugos-browser.bat` script across workspace and installation paths.
pub fn find_browser_launcher_bat() -> Option<std::path::PathBuf> {
    // 1. Check relative to current executable
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(dir) = exe_path.parent() {
            let p1 = dir.join("../../browser/Chromium-win32-x64/hugos-browser.bat");
            if p1.is_file() {
                return p1.canonicalize().ok().or(Some(p1));
            }
            let p2 = dir.join("../Chromium-win32-x64/hugos-browser.bat");
            if p2.is_file() {
                return p2.canonicalize().ok().or(Some(p2));
            }
        }
    }

    // 2. Check current working directory
    let cwd_candidates = [
        "browser/Chromium-win32-x64/hugos-browser.bat",
        "Chromium-win32-x64/hugos-browser.bat",
    ];
    for cand in cwd_candidates {
        let p = std::path::PathBuf::from(cand);
        if p.is_file() {
            return p.canonicalize().ok().or(Some(p));
        }
    }

    // 3. Check installed production location
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        let p = std::path::PathBuf::from(local_app_data).join("HugOS Browser/Chromium-win32-x64/hugos-browser.bat");
        if p.is_file() {
            return Some(p);
        }
    }

    None
}

/// Spawns the HugOS Intelligent Chromium Browser with optional startup URL.
pub fn launch_hugos_browser(url: Option<&str>) -> Result<(), String> {
    let bat_path = find_browser_launcher_bat()
        .ok_or_else(|| "Could not locate hugos-browser.bat. Ensure HugOS Browser is present in browser/Chromium-win32-x64/.".to_string())?;

    println!("🚀 [BROWSER] Spawning HugOS Browser Engine: {}", bat_path.display());
    let mut cmd = std::process::Command::new("cmd");
    cmd.args(["/c", bat_path.to_str().unwrap()]);
    if let Some(u) = url {
        cmd.arg(u);
    }
    cmd.spawn()
        .map_err(|e| format!("Failed to spawn hugos-browser.bat: {}", e))?;
    Ok(())
}


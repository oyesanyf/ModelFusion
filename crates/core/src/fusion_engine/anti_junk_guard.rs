//! Anti-Junk, Grounding & Accuracy Guard for Abliterated Local Model Fusion.
//!
//! Abliterated local models eliminate cloud safety false-refusals on authorized defensive
//! security audits, but without deterministic output guards they can suffer from:
//!   1. Token/line repetition loops (common in Q4_K_M GGUF weights),
//!   2. Leaked `<think>...</think>` chain-of-thought fragments,
//!   3. Empty meta-commentary / generic security boilerplate,
//!   4. Hallucinated file paths not present in the grounded input context,
//!   5. Malformed JSON when a structured schema is required.
//!
//! This module scores, cleans, and filters candidate responses before consensus judging
//! and validates the final synthesized output so local abliterated ModelFusion achieves
//! frontier-grade factual precision on grounded verification & triage workloads.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

use crate::providers::is_refusal_response;

fn think_block_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?is)<think>.*?</think>").expect("valid think regex"))
}

fn file_path_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(
            r#"(?x)
            (?:^|[\s`'"\(\[\{,:;])
            (
                (?:\.github/|[A-Za-z0-9_.-]+/)
                [A-Za-z0-9_./-]*
                [A-Za-z0-9_-]
                \.(?:py|rs|ts|tsx|js|jsx|mjs|cjs|go|java|rb|php|c|cc|cpp|h|hpp|cs|yml|yaml|json|toml|sh|ps1|sql|html|xml|md|tf|kt|swift)
            )
            (?:$|[\s`'"\)\]\},:;\#])
            "#,
        )
        .expect("valid file path regex")
    })
}

fn leading_close_think_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?is)^.*</think>").expect("valid closing think regex"))
}

fn trailing_open_think_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"(?is)<think>.*$").expect("valid open think regex"))
}

/// Linear-time O(n) check for 24+ consecutive identical characters (excluding Markdown dividers).
fn has_repeated_char_stutter(text: &str) -> bool {
    let mut prev: Option<char> = None;
    let mut run: usize = 0;
    for ch in text.chars() {
        let is_divider = matches!(ch, '-' | '=' | '*' | '#' | '_' | '~' | '`' | ' ' | '\t' | '\n' | '\r');
        if is_divider {
            prev = None;
            run = 0;
            continue;
        }
        if prev == Some(ch) {
            run += 1;
            if run >= 24 {
                return true;
            }
        } else {
            prev = Some(ch);
            run = 1;
        }
    }
    false
}

/// Grounding verification metrics comparing concrete evidence cited by a model
/// against the grounded prompt/context supplied to it.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GroundingReport {
    pub prompt_file_count: usize,
    pub cited_file_count: usize,
    pub grounded_paths: Vec<String>,
    pub hallucinated_paths: Vec<String>,
    pub grounding_ratio: f64,
}

/// Deterministic quality & accuracy verdict for a single model response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardVerdict {
    pub accepted: bool,
    pub cleaned_text: String,
    pub quality_score: f64,
    pub rejection_reasons: Vec<String>,
    pub grounding: GroundingReport,
    pub json_valid: Option<bool>,
}

/// Strips `<think>...</think>` reasoning blocks and unclosed `<think>` tags cleanly.
pub fn strip_think_blocks(raw: &str) -> String {
    let stripped = think_block_re().replace_all(raw, "");
    let stripped = leading_close_think_re().replace(&stripped, "");
    let stripped = trailing_open_think_re().replace(&stripped, "");
    stripped.trim().to_string()
}

/// Detects degenerate repetition loops (repeated lines, repeated 6-word n-grams,
/// character stuttering, or severe lexical diversity collapse).
pub fn detect_repetition_loop(text: &str) -> Option<String> {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return None;
    }

    if has_repeated_char_stutter(trimmed) {
        return Some("character_stutter_loop".to_string());
    }

    // 1. Repeated substantive lines (>= 20 chars appearing >= 3 times)
    let mut line_counts: HashMap<String, usize> = HashMap::new();
    for line in trimmed.lines() {
        let norm = line.trim().to_lowercase();
        if norm.len() >= 20
            && !norm.starts_with("```")
            && !norm.chars().all(|c| "-=*#_~| ".contains(c))
        {
            let count = line_counts.entry(norm).or_insert(0);
            *count += 1;
            if *count >= 3 {
                return Some("repeated_line_loop".to_string());
            }
        }
    }

    // 2. Sliding 6-word n-gram repetition (>= 4 identical 6-grams)
    let words: Vec<String> = trimmed
        .split_whitespace()
        .map(|w| {
            w.trim_matches(|c: char| !c.is_alphanumeric() && c != '_' && c != '-')
                .to_lowercase()
        })
        .filter(|w| !w.is_empty())
        .collect();

    if words.len() >= 24 {
        let mut ngram_counts: HashMap<String, usize> = HashMap::new();
        for win in words.windows(6) {
            let key = win.join(" ");
            let count = ngram_counts.entry(key).or_insert(0);
            *count += 1;
            if *count >= 4 {
                return Some("repeated_ngram_loop".to_string());
            }
        }
    }

    // 3. Severe token-diversity collapse on longer responses (>= 50 words, < 20% unique words)
    if words.len() >= 50 {
        let unique: HashSet<&String> = words.iter().collect();
        let ratio = unique.len() as f64 / words.len() as f64;
        if ratio < 0.20 {
            return Some(format!("low_lexical_diversity({:.2})", ratio));
        }
    }

    None
}

/// Detects empty meta-commentary / generic filler slop that lacks grounded technical evidence.
pub fn detect_meta_slop(text: &str) -> Option<String> {
    let lower = text.trim().to_lowercase();
    if lower.is_empty() {
        return Some("empty_response".to_string());
    }

    const HARD_SLOP_MARKERS: &[&str] = &[
        "in summary, the key steps to continue",
        "the code snippet provided is well-structured",
        "aligns with best practices",
        "based on the judge analysis",
        "the panel agrees that",
        "i don't have access to your files",
        "without access to the actual source code",
        "here is a hypothetical example of how",
    ];

    for marker in HARD_SLOP_MARKERS {
        if lower.contains(marker) {
            return Some(format!("meta_slop:{}", marker));
        }
    }

    // Detect placeholder template stubs that abliterated models occasionally emit verbatim
    if lower.contains("\"rationale\": \"...\"")
        || lower.contains("\"raw_request\": \"...\"")
        || lower.contains("todo: fill in vulnerability")
    {
        return Some("placeholder_template_stub".to_string());
    }

    None
}

/// Extracts normalized relative source-code / workflow file paths from text.
pub fn extract_file_paths(text: &str) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for cap in file_path_re().captures_iter(text) {
        if let Some(m) = cap.get(1) {
            let norm = m
                .as_str()
                .trim_start_matches("./")
                .replace('\\', "/")
                .to_lowercase();
            // Skip obvious URL fragments or version strings
            if norm.starts_with("http/") || norm.starts_with("https/") {
                continue;
            }
            if seen.insert(norm.clone()) {
                out.push(norm);
            }
        }
    }
    out
}

fn path_basename(path: &str) -> &str {
    path.rsplit('/').next().unwrap_or(path)
}

/// Verifies whether file paths cited by the model actually exist in the grounded prompt/context.
pub fn verify_grounding(prompt: &str, response: &str) -> GroundingReport {
    let prompt_paths = extract_file_paths(prompt);
    let cited_paths = extract_file_paths(response);

    if prompt_paths.is_empty() || cited_paths.is_empty() {
        return GroundingReport {
            prompt_file_count: prompt_paths.len(),
            cited_file_count: cited_paths.len(),
            grounded_paths: Vec::new(),
            hallucinated_paths: Vec::new(),
            grounding_ratio: 1.0,
        };
    }

    let prompt_lower = prompt.to_lowercase().replace('\\', "/");
    let prompt_basenames: HashSet<&str> = prompt_paths.iter().map(|p| path_basename(p)).collect();

    let mut grounded = Vec::new();
    let mut hallucinated = Vec::new();

    for cited in cited_paths {
        let base = path_basename(&cited);
        let exact_in_prompt = prompt_paths.iter().any(|p| p == &cited || p.ends_with(&cited) || cited.ends_with(p));
        let base_in_prompt = prompt_basenames.contains(base) || prompt_lower.contains(&cited);
        if exact_in_prompt || base_in_prompt {
            grounded.push(cited);
        } else {
            hallucinated.push(cited);
        }
    }

    let total = grounded.len() + hallucinated.len();
    let grounding_ratio = if total == 0 {
        1.0
    } else {
        grounded.len() as f64 / total as f64
    };

    GroundingReport {
        prompt_file_count: prompt_paths.len(),
        cited_file_count: total,
        grounded_paths: grounded,
        hallucinated_paths: hallucinated,
        grounding_ratio,
    }
}

/// Returns true if the prompt explicitly requests a strict JSON output payload.
pub fn prompt_requires_json(prompt: &str) -> bool {
    let lower = prompt.to_lowercase();
    lower.contains("return a valid json object only")
        || lower.contains("output only valid json")
        || lower.contains("return only valid json")
        || lower.contains("strict json matching")
        || lower.contains("critical: output only valid json")
}

/// Attempts to parse a JSON object or array from a cleaned LLM output (handling code fences).
pub fn parse_json_payload(cleaned: &str) -> Option<serde_json::Value> {
    let mut text = cleaned.trim().to_string();
    if text.is_empty() {
        return None;
    }

    if let Some(idx) = text.find("```json") {
        let rest = &text[idx + 7..];
        if let Some(end) = rest.find("```") {
            text = rest[..end].trim().to_string();
        }
    } else if text.starts_with("```") {
        let rest = text.trim_start_matches("```");
        if let Some(end) = rest.find("```") {
            text = rest[..end].trim().to_string();
        }
    }

    if let Ok(val) = serde_json::from_str::<serde_json::Value>(&text) {
        return Some(val);
    }

    // Try extracting the outermost JSON object or array span
    if let (Some(start), Some(end)) = (text.find('{'), text.rfind('}')) {
        if start < end {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&text[start..=end]) {
                return Some(val);
            }
        }
    }
    if let (Some(start), Some(end)) = (text.find('['), text.rfind(']')) {
        if start < end {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&text[start..=end]) {
                return Some(val);
            }
        }
    }

    None
}

/// Runs all deterministic anti-junk, refusal, repetition, JSON-schema, and grounding checks
/// against a model response. Returns a `GuardVerdict` with cleaned output and a 0..1 quality score.
pub fn evaluate_candidate_response(
    prompt: &str,
    raw_response: &str,
    is_security_audit: bool,
) -> GuardVerdict {
    let mut rejection_reasons = Vec::new();
    let trimmed_raw = raw_response.trim();

    if trimmed_raw.is_empty() || trimmed_raw.starts_with("MODEL ERROR") {
        rejection_reasons.push("model_error_or_empty".to_string());
        return GuardVerdict {
            accepted: false,
            cleaned_text: String::new(),
            quality_score: 0.0,
            rejection_reasons,
            grounding: GroundingReport::default(),
            json_valid: None,
        };
    }

    let cleaned = strip_think_blocks(trimmed_raw);
    if cleaned.len() < 4 {
        rejection_reasons.push("empty_after_think_strip".to_string());
        return GuardVerdict {
            accepted: false,
            cleaned_text: cleaned,
            quality_score: 0.0,
            rejection_reasons,
            grounding: GroundingReport::default(),
            json_valid: None,
        };
    }

    if is_refusal_response(&cleaned) {
        rejection_reasons.push("safety_refusal".to_string());
    }

    if let Some(loop_reason) = detect_repetition_loop(&cleaned) {
        rejection_reasons.push(loop_reason);
    }

    if let Some(slop_reason) = detect_meta_slop(&cleaned) {
        rejection_reasons.push(slop_reason);
    }

    let requires_json = prompt_requires_json(prompt);
    let json_valid = if requires_json {
        let valid = parse_json_payload(&cleaned).is_some();
        if !valid {
            rejection_reasons.push("invalid_required_json".to_string());
        }
        Some(valid)
    } else {
        None
    };

    let grounding = verify_grounding(prompt, &cleaned);
    if is_security_audit
        && grounding.prompt_file_count > 0
        && !grounding.hallucinated_paths.is_empty()
    {
        // Strict anti-hallucination gate: reject security audit responses that invent paths
        // with zero real grounded paths or >= 2 hallucinated paths exceeding grounded count.
        if grounding.grounded_paths.is_empty()
            || (grounding.hallucinated_paths.len() >= 2
                && grounding.hallucinated_paths.len() > grounding.grounded_paths.len())
        {
            rejection_reasons.push(format!(
                "hallucinated_file_paths({})",
                grounding.hallucinated_paths.join(",")
            ));
        }
    }

    // Score quality deterministically (0.0 ..= 1.0)
    let mut score: f64 = 0.70;
    if is_security_audit && grounding.prompt_file_count > 0 {
        score += 0.20 * grounding.grounding_ratio;
        if !grounding.grounded_paths.is_empty() {
            score += 0.05;
        }
        if !grounding.hallucinated_paths.is_empty() {
            score -= 0.15 * (grounding.hallucinated_paths.len().min(3) as f64);
        }
    }
    if json_valid == Some(true) {
        score += 0.10;
    }
    if cleaned.len() < 25 && !requires_json {
        score -= 0.25;
    }

    let accepted = rejection_reasons.is_empty();
    let final_score = if accepted {
        score.clamp(0.05, 1.0)
    } else {
        0.0
    };

    GuardVerdict {
        accepted,
        cleaned_text: cleaned,
        quality_score: final_score,
        rejection_reasons,
        grounding,
        json_valid,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_think_blocks() {
        let raw = "<think>Let me analyze the diff carefully...\nline 2</think>\n{\"verdicts\": [{\"confirmed\": true}]}";
        assert_eq!(strip_think_blocks(raw), "{\"verdicts\": [{\"confirmed\": true}]}");

        let dangling = "<think>stuck reasoning without closing tag";
        assert_eq!(strip_think_blocks(dangling), "");
    }

    #[test]
    fn test_detect_repetition_loop() {
        let looped_lines = "The vulnerability is in auth.ts line 10.\n".repeat(4);
        assert!(detect_repetition_loop(&looped_lines).is_some());

        let looped_ngram = "check the input validation before writing ".repeat(5);
        assert!(detect_repetition_loop(&looped_ngram).is_some());

        let stutter = "aaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        assert!(detect_repetition_loop(stutter).is_some());

        let clean = "Confirmed CWE-22 symlink traversal in src/filestore.ts:44 because intermediate path segments are not resolved with realpathSync before writeFileSync.";
        assert!(detect_repetition_loop(clean).is_none());
    }

    #[test]
    fn test_grounding_rejects_hallucinated_paths_and_accepts_grounded() {
        let prompt = "Perform defensive semantic verification on static finding in packages/shopify-app-remix/src/sanitize.ts line 42. CRITICAL: Output ONLY valid JSON matching schema: {\"verdicts\": []}.";

        // Hallucinated file paths invented by an abliterated model must be REJECTED
        let hallucinated = "{\"verdicts\": [{\"file_path\": \"src/fake/made_up_handler.ts\", \"line\": 12, \"confirmed\": true}, {\"file_path\": \"server/nonexistent.py\", \"line\": 99, \"confirmed\": true}]}";
        let v_bad = evaluate_candidate_response(prompt, hallucinated, true);
        assert!(!v_bad.accepted);
        assert!(v_bad
            .rejection_reasons
            .iter()
            .any(|r| r.starts_with("hallucinated_file_paths")));

        // Grounded valid JSON verdict must be ACCEPTED with high score
        let grounded = "<think>Checking sanitize.ts...</think>\n{\"verdicts\": [{\"file_path\": \"packages/shopify-app-remix/src/sanitize.ts\", \"line\": 42, \"confirmed\": true, \"cwe\": \"CWE-601\"}]}";
        let v_good = evaluate_candidate_response(prompt, grounded, true);
        assert!(v_good.accepted, "reasons: {:?}", v_good.rejection_reasons);
        assert_eq!(v_good.json_valid, Some(true));
        assert!(v_good.quality_score >= 0.90);
        assert!(v_good.cleaned_text.starts_with("{\"verdicts\""));
    }

    #[test]
    fn test_meta_slop_and_broken_json_rejected() {
        let prompt = "Audit src/auth.py. CRITICAL: Output ONLY valid JSON matching schema: {\"verdicts\": []}.";
        let slop = "In summary, the key steps to continue are reviewing the architecture which aligns with best practices.";
        let v = evaluate_candidate_response(prompt, slop, true);
        assert!(!v.accepted);
        assert!(v.rejection_reasons.iter().any(|r| r.starts_with("meta_slop")));
        assert!(v.rejection_reasons.iter().any(|r| r == "invalid_required_json"));
    }
}

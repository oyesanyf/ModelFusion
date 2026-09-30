use aho_corasick::{AhoCorasickBuilder, MatchKind};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::error::Error;

// ══════════════════════════════════════════════════════════════════════
// HTTP / LLM PAYLOAD STRUCTURES
// ══════════════════════════════════════════════════════════════════════

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Message {
    role: String,
    content: String,
}

#[derive(Serialize, Debug)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<Message>,
    temperature: f32,
    top_p: f32,
    presence_penalty: f32,
    frequency_penalty: f32,
}

#[derive(Serialize, Debug)]
struct OllamaChatOptions {
    temperature: f32,
    top_p: f32,
    presence_penalty: f32,
    frequency_penalty: f32,
}

#[derive(Serialize, Debug)]
struct OllamaChatRequest {
    model: String,
    messages: Vec<Message>,
    stream: bool,
    options: OllamaChatOptions,
}

#[derive(Deserialize, Debug)]
pub struct ChatChoice {
    pub message: MessageContent,
}

#[derive(Deserialize, Debug)]
pub struct MessageContent {
    pub content: String,
}

#[derive(Deserialize, Debug)]
pub struct ChatCompletionResponse {
    #[serde(default)]
    pub choices: Vec<ChatChoice>,
    #[serde(default)]
    pub message: Option<MessageContent>,
}

// ══════════════════════════════════════════════════════════════════════
// STAGE 1: STYLOMETRIC PROFILING & STATIC HEURISTICS
// ══════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StylometricProfile {
    pub total_words: usize,
    pub sentence_count: usize,
    pub sentence_lengths: Vec<usize>,
    pub mean_length: f64,
    pub variance: f64,
    pub std_dev: f64,
    pub coefficient_of_variation: f64,
    /// Normalized burstiness index: (σ - μ) / (σ + μ)
    pub burstiness_score: f64,
    /// Sequences of ≥ 3 consecutive sentences with length diff ≤ 3
    pub flatline_sequences: Vec<(usize, usize)>,
    /// Repetitive openings (first 1-2 words appearing ≥ 2 times)
    pub repetitive_openings: Vec<(String, usize)>,
    pub cliche_count: usize,
}

/// 45+ Classic AI Cliché pairs (pattern, replacement)
const AI_CLICHE_PAIRS: &[(&str, &str)] = &[
    ("delve into", "look into"),
    ("Delve into", "Look into"),
    ("delving into", "looking into"),
    ("Delving into", "Looking into"),
    ("it is important to note that", "notably,"),
    ("It is important to note that", "Notably,"),
    ("it is important to note", "note that"),
    ("It is important to note", "Note that"),
    ("it's important to note that", "notably,"),
    ("It's important to note that", "Notably,"),
    ("it's important to note", "note that"),
    ("It's important to note", "Note that"),
    ("it is crucial to remember", "remember"),
    ("It is crucial to remember", "Remember"),
    ("it is worth noting that", "notably,"),
    ("It is worth noting that", "Notably,"),
    ("it is worth noting", "notably,"),
    ("It is worth noting", "Notably,"),
    ("furthermore,", "also,"),
    ("Furthermore,", "Also,"),
    ("furthermore", "moreover,"),
    ("Furthermore", "Moreover,"),
    ("moreover,", "plus,"),
    ("Moreover,", "Plus,"),
    ("moreover", "plus"),
    ("Moreover", "Plus"),
    ("in conclusion,", "overall,"),
    ("In conclusion,", "Overall,"),
    ("in conclusion", "overall"),
    ("In conclusion", "Overall"),
    ("tapestry of", "blend of"),
    ("Tapestry of", "Blend of"),
    ("rich tapestry", "vibrant mix"),
    ("Rich tapestry", "Vibrant mix"),
    ("testament to", "proof of"),
    ("Testament to", "Proof of"),
    ("a testament to", "proof of"),
    ("A testament to", "Proof of"),
    ("beacon of", "model of"),
    ("Beacon of", "Model of"),
    ("multifaceted", "complex"),
    ("Multifaceted", "Complex"),
    ("paramount", "vital"),
    ("Paramount", "Vital"),
    ("revolutionize", "transform"),
    ("Revolutionize", "Transform"),
    ("revolutionizing", "transforming"),
    ("Revolutionizing", "Transforming"),
    ("in today's digital landscape", "today"),
    ("In today's digital landscape", "Today"),
    ("in today's fast-paced world", "in modern life"),
    ("In today's fast-paced world", "In modern life"),
    ("navigating the complexities", "handling the intricacies"),
    ("Navigating the complexities", "Handling the intricacies"),
    ("navigating the ever-changing", "adapting to"),
    ("Navigating the ever-changing", "Adapting to"),
    ("a myriad of", "many"),
    ("A myriad of", "Many"),
    ("myriad of", "countless"),
    ("Myriad of", "Countless"),
    ("embark on a journey", "begin"),
    ("Embark on a journey", "Begin"),
    ("poised to", "ready to"),
    ("Poised to", "Ready to"),
    ("plays a pivotal role", "is essential"),
    ("Plays a pivotal role", "Is essential"),
    ("play a pivotal role", "are essential"),
    ("Play a pivotal role", "Are essential"),
    ("pivotal role", "key role"),
    ("Pivotal role", "Key role"),
    ("in summary,", "in short,"),
    ("In summary,", "In short,"),
    ("in summary", "in short"),
    ("In summary", "In short"),
    ("to summarize,", "in short,"),
    ("To summarize,", "In short,"),
    ("to summarize", "in short"),
    ("To summarize", "In short"),
    ("shed light on", "clarify"),
    ("Shed light on", "Clarify"),
    ("sheds light on", "clarifies"),
    ("Sheds light on", "Clarifies"),
    ("harnessing the power of", "using"),
    ("Harnessing the power of", "Using"),
    ("harness the power of", "use"),
    ("Harness the power of", "Use"),
    ("fast-paced world", "modern world"),
    ("Fast-paced world", "Modern world"),
    ("ever-evolving landscape", "changing field"),
    ("Ever-evolving landscape", "Changing field"),
    ("foster a culture of", "encourage"),
    ("Foster a culture of", "Encourage"),
    ("groundbreaking", "novel"),
    ("Groundbreaking", "Novel"),
    ("seamless integration", "smooth fit"),
    ("Seamless integration", "Smooth fit"),
    ("seamlessly integrate", "fit smoothly"),
    ("Seamlessly integrate", "Fit smoothly"),
    ("game-changer", "breakthrough"),
    ("Game-changer", "Breakthrough"),
    ("paradigm shift", "major shift"),
    ("Paradigm shift", "Major shift"),
    ("delve deeper", "look closer"),
    ("Delve deeper", "Look closer"),
    ("at the forefront of", "leading"),
    ("At the forefront of", "Leading"),
    ("it goes without saying", "clearly"),
    ("It goes without saying", "Clearly"),
    ("undeniably", "clearly"),
    ("Undeniably", "Clearly"),
    ("holistic approach", "broad view"),
    ("Holistic approach", "Broad view"),
    ("treasure trove", "rich source"),
    ("Treasure trove", "Rich source"),
];

/// Contractions mapping pairs: (uncontracted, contracted)
const CONTRACTION_PAIRS: &[(&str, &str)] = &[
    ("it is", "it's"),
    ("It is", "It's"),
    ("cannot", "can't"),
    ("Cannot", "Can't"),
    ("do not", "don't"),
    ("Do not", "Don't"),
    ("does not", "doesn't"),
    ("Does not", "Doesn't"),
    ("will not", "won't"),
    ("Will not", "Won't"),
    ("would not", "wouldn't"),
    ("Would not", "Wouldn't"),
    ("could not", "couldn't"),
    ("Could not", "Couldn't"),
    ("should not", "shouldn't"),
    ("Should not", "Shouldn't"),
    ("there is", "there's"),
    ("There is", "There's"),
    ("they are", "they're"),
    ("They are", "They're"),
    ("we are", "we're"),
    ("We are", "We're"),
    ("you are", "you're"),
    ("You are", "You're"),
    ("that is", "that's"),
    ("That is", "That's"),
    ("what is", "what's"),
    ("What is", "What's"),
];

/// Helper to split text into distinct sentences
pub fn split_sentences(text: &str) -> Vec<String> {
    let mut sentences = Vec::new();
    let mut current = String::new();

    for ch in text.chars() {
        current.push(ch);
        if ch == '.' || ch == '!' || ch == '?' {
            let trimmed = current.trim();
            if !trimmed.is_empty() {
                sentences.push(trimmed.to_string());
            }
            current.clear();
        }
    }
    let remainder = current.trim();
    if !remainder.is_empty() {
        sentences.push(remainder.to_string());
    }
    sentences
}

/// Prunes AI clichés using Aho-Corasick automaton in single-pass replacement
pub fn prune_cliches(text: &str) -> String {
    let patterns: Vec<&str> = AI_CLICHE_PAIRS.iter().map(|(p, _)| *p).collect();
    let replacements: Vec<&str> = AI_CLICHE_PAIRS.iter().map(|(_, r)| *r).collect();

    if let Ok(ac) = AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .build(&patterns)
    {
        ac.replace_all(text, &replacements)
    } else {
        text.to_string()
    }
}

/// Counts the number of classic AI clichés found in text
pub fn count_cliches(text: &str) -> usize {
    let patterns: Vec<&str> = AI_CLICHE_PAIRS.iter().map(|(p, _)| *p).collect();
    if let Ok(ac) = AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .build(&patterns)
    {
        ac.find_iter(text).count()
    } else {
        0
    }
}

/// Performs comprehensive stylometric profiling of input text
pub fn analyze_stylometry(text: &str) -> StylometricProfile {
    let sentences = split_sentences(text);
    let sentence_count = sentences.len();

    let mut sentence_lengths = Vec::with_capacity(sentence_count);
    let mut opening_counts: HashMap<String, usize> = HashMap::new();

    for s in &sentences {
        let words: Vec<&str> = s.split_whitespace().collect();
        let len = words.len();
        sentence_lengths.push(len);

        if !words.is_empty() {
            let first_word = words[0]
                .chars()
                .filter(|c| c.is_alphabetic())
                .flat_map(|c| c.to_lowercase())
                .collect::<String>();
            if !first_word.is_empty() {
                *opening_counts.entry(first_word).or_insert(0) += 1;
            }
        }
    }

    let total_words: usize = sentence_lengths.iter().sum();
    let mean_length = if sentence_count > 0 {
        total_words as f64 / sentence_count as f64
    } else {
        0.0
    };

    let variance = if sentence_count > 0 {
        sentence_lengths
            .iter()
            .map(|&l| {
                let diff = l as f64 - mean_length;
                diff * diff
            })
            .sum::<f64>()
            / (sentence_count as f64)
    } else {
        0.0
    };

    let std_dev = variance.sqrt();
    let coefficient_of_variation = if mean_length > 0.0 {
        std_dev / mean_length
    } else {
        0.0
    };

    // Burstiness score: (σ - μ) / (σ + μ)
    let burstiness_score = if (std_dev + mean_length) > 0.0 {
        (std_dev - mean_length) / (std_dev + mean_length)
    } else {
        0.0
    };

    // Detect flatline sequences: ≥ 3 consecutive sentences with length diff ≤ 3
    let mut flatline_sequences = Vec::new();
    if sentence_lengths.len() >= 3 {
        let mut start_idx = 0;
        let mut streak = 1;

        for i in 1..sentence_lengths.len() {
            let diff = (sentence_lengths[i] as isize - sentence_lengths[i - 1] as isize).abs();
            if diff <= 3 {
                streak += 1;
            } else {
                if streak >= 3 {
                    flatline_sequences.push((start_idx, streak));
                }
                start_idx = i;
                streak = 1;
            }
        }
        if streak >= 3 {
            flatline_sequences.push((start_idx, streak));
        }
    }

    // Repetitive openings appearing ≥ 2 times
    let mut repetitive_openings: Vec<(String, usize)> = opening_counts
        .into_iter()
        .filter(|(_, cnt)| *cnt >= 2)
        .collect();
    repetitive_openings.sort_by(|a, b| b.1.cmp(&a.1));

    let cliche_count = count_cliches(text);

    StylometricProfile {
        total_words,
        sentence_count,
        sentence_lengths,
        mean_length,
        variance,
        std_dev,
        coefficient_of_variation,
        burstiness_score,
        flatline_sequences,
        repetitive_openings,
        cliche_count,
    }
}

// ══════════════════════════════════════════════════════════════════════
// STAGE 2: LOCAL PERPLEXITY & ENTROPY SCORING
// ══════════════════════════════════════════════════════════════════════

/// Calculates perplexity from token log probabilities: exp(-mean(log_probs))
pub fn compute_perplexity_from_logprobs(token_logprobs: &[f64]) -> f64 {
    if token_logprobs.is_empty() {
        return 0.0;
    }
    let mean_logprob: f64 = token_logprobs.iter().sum::<f64>() / (token_logprobs.len() as f64);
    (-mean_logprob).exp()
}

/// Bigram statistical transition Shannon entropy: H(X) = -Σ p(x) log2 p(x)
pub fn compute_transition_entropy(text: &str) -> f64 {
    let words: Vec<String> = text
        .split_whitespace()
        .map(|w| {
            w.chars()
                .filter(|c| c.is_alphabetic())
                .flat_map(|c| c.to_lowercase())
                .collect()
        })
        .filter(|s: &String| !s.is_empty())
        .collect();

    if words.len() < 2 {
        return 0.0;
    }

    let mut bigram_counts: HashMap<(String, String), usize> = HashMap::new();
    let total_bigrams = words.len() - 1;

    for i in 0..total_bigrams {
        let bg = (words[i].clone(), words[i + 1].clone());
        *bigram_counts.entry(bg).or_insert(0) += 1;
    }

    let mut entropy = 0.0;
    for &count in bigram_counts.values() {
        let p = count as f64 / total_bigrams as f64;
        if p > 0.0 {
            entropy -= p * p.log2();
        }
    }

    entropy
}

/// Identifies low-entropy flatline valleys in text across sliding windows
pub fn find_low_entropy_valleys(
    text: &str,
    window_size: usize,
    threshold: f64,
) -> Vec<(usize, usize)> {
    let words: Vec<&str> = text.split_whitespace().collect();
    if words.len() < window_size {
        return Vec::new();
    }

    let mut valleys = Vec::new();
    for i in 0..=(words.len() - window_size) {
        let slice = words[i..i + window_size].join(" ");
        let ent = compute_transition_entropy(&slice);
        if ent < threshold {
            valleys.push((i, i + window_size));
        }
    }
    valleys
}

// ══════════════════════════════════════════════════════════════════════
// STAGE 3: ASYMMETRIC MASKED INFILLING & STRUCTURAL PERTURBATIONS
// ══════════════════════════════════════════════════════════════════════

/// Injects auxiliary verb contractions into text using Aho-Corasick automaton
pub fn inject_contractions(text: &str) -> String {
    let patterns: Vec<&str> = CONTRACTION_PAIRS.iter().map(|(p, _)| *p).collect();
    let replacements: Vec<&str> = CONTRACTION_PAIRS.iter().map(|(_, r)| *r).collect();

    if let Ok(ac) = AhoCorasickBuilder::new()
        .match_kind(MatchKind::LeftmostFirst)
        .build(&patterns)
    {
        ac.replace_all(text, &replacements)
    } else {
        text.to_string()
    }
}

/// Shuffles punctuation to disrupt predictable AI cadence (inserting em dashes, semicolons, parens)
pub fn shuffle_punctuation(text: &str) -> String {
    let mut result = String::with_capacity(text.len() + 32);
    let mut comma_count = 0;

    for part in text.split(", ") {
        if !result.is_empty() {
            comma_count += 1;
            // Selectively replace every 3rd or 4th comma with em-dash or semicolon
            if comma_count % 4 == 0 {
                result.push_str(" — ");
            } else if comma_count % 3 == 0 {
                result.push_str("; ");
            } else {
                result.push_str(", ");
            }
        }
        result.push_str(part);
    }
    result
}

/// Adjusts sentence pacing to introduce dynamic burstiness (breaking long sentences or merging short ones)
pub fn adjust_sentence_pacing(text: &str) -> String {
    let sentences = split_sentences(text);
    if sentences.len() < 2 {
        return text.to_string();
    }

    let mut paced_sentences = Vec::new();
    let mut i = 0;

    while i < sentences.len() {
        let s = &sentences[i];
        let words: Vec<&str> = s.split_whitespace().collect();

        // If sentence is excessively long (> 28 words) and contains a conjunction, split it
        if words.len() > 28 && s.contains(" and ") {
            if let Some(idx) = s.find(" and ") {
                let first = s[..idx].trim();
                let second = s[idx + 5..].trim();
                if !first.is_empty() && !second.is_empty() {
                    let mut cap_second = second.to_string();
                    if let Some(first_char) = cap_second.chars().next() {
                        cap_second = format!("{}{}", first_char.to_uppercase(), &cap_second[first_char.len_utf8()..]);
                    }
                    paced_sentences.push(format!("{}.", first.trim_end_matches('.')));
                    paced_sentences.push(format!("{}.", cap_second.trim_end_matches('.')));
                    i += 1;
                    continue;
                }
            }
        }

        // If two consecutive sentences are both very short (< 7 words), combine with a semicolon or dash
        if words.len() < 7 && i + 1 < sentences.len() {
            let next_words: Vec<&str> = sentences[i + 1].split_whitespace().collect();
            if next_words.len() < 7 {
                let trimmed_curr = s.trim_end_matches(&['.', '!', '?'][..]);
                let trimmed_next = sentences[i + 1].trim_start();
                let mut lower_next = trimmed_next.to_string();
                if let Some(first_char) = lower_next.chars().next() {
                    lower_next = format!("{}{}", first_char.to_lowercase(), &lower_next[first_char.len_utf8()..]);
                }
                paced_sentences.push(format!("{} — {}", trimmed_curr, lower_next));
                i += 2;
                continue;
            }
        }

        paced_sentences.push(s.clone());
        i += 1;
    }

    paced_sentences.join(" ")
}

// ══════════════════════════════════════════════════════════════════════
// STAGE 4: GENETIC SEARCH & CONSTRAINT-GUIDED OPTIMIZATION LOOP
// ══════════════════════════════════════════════════════════════════════

/// Term frequency vector for rapid semantic similarity checks
#[derive(Debug, Clone)]
pub struct TermVector {
    pub freqs: HashMap<String, f64>,
    pub norm: f64,
}

impl TermVector {
    pub fn from_text(text: &str) -> Self {
        let mut freqs = HashMap::new();
        for word in text.split_whitespace() {
            let cleaned: String = word
                .chars()
                .filter(|c| c.is_alphanumeric())
                .flat_map(|c| c.to_lowercase())
                .collect();
            if !cleaned.is_empty() {
                *freqs.entry(cleaned).or_insert(0.0) += 1.0;
            }
        }
        let norm = freqs.values().map(|&v| v * v).sum::<f64>().sqrt();
        Self { freqs, norm }
    }

    /// Computes cosine similarity between two term vectors
    pub fn cosine_similarity(&self, other: &TermVector) -> f64 {
        if self.norm == 0.0 || other.norm == 0.0 {
            return 0.0;
        }
        let mut dot = 0.0;
        for (term, count) in &self.freqs {
            if let Some(other_count) = other.freqs.get(term) {
                dot += count * other_count;
            }
        }
        (dot / (self.norm * other.norm)).clamp(0.0, 1.0)
    }
}

/// Evaluates resistance against commercial AI detectors (GPTZero, ZeroGPT, Turnitin heuristics)
pub fn compute_detector_resistance(candidate: &str, profile: &StylometricProfile) -> f64 {
    let mut score = 0.55;

    // Burstiness bonus: human text features high coefficient of variation
    if profile.coefficient_of_variation > 0.45 {
        score += 0.20;
    } else if profile.coefficient_of_variation > 0.30 {
        score += 0.10;
    }

    // Flatline penalty: AI text often writes sequences of similarly-sized sentences
    score -= (profile.flatline_sequences.len() as f64) * 0.06;

    // Cliché penalty: AI markers drastically reduce detector bypass rates
    score -= (profile.cliche_count as f64) * 0.08;

    // Contraction bonus: conversational contractions are a classic human prose marker
    if candidate.contains('\'') {
        score += 0.10;
    }

    // Transition entropy bonus
    let entropy = compute_transition_entropy(candidate);
    if entropy > 3.5 {
        score += 0.10;
    }

    score.clamp(0.10, 0.99)
}

/// Candidate in the genetic optimization population
#[derive(Debug, Clone)]
pub struct OptimizationCandidate {
    pub text: String,
    pub detector_resistance: f64,
    pub cosine_similarity: f64,
    pub fitness: f64,
}

/// Optimization loop selecting best candidate under semantic constraint (cosine_similarity >= 0.85)
pub fn pareto_select_candidate(
    original_text: &str,
    candidates: Vec<String>,
) -> OptimizationCandidate {
    let anchor = TermVector::from_text(original_text);

    let evaluated: Vec<OptimizationCandidate> = candidates
        .into_iter()
        .map(|text| {
            let cand_vec = TermVector::from_text(&text);
            let sim = anchor.cosine_similarity(&cand_vec);
            let profile = analyze_stylometry(&text);
            let resistance = compute_detector_resistance(&text, &profile);
            let fitness = resistance * sim;
            OptimizationCandidate {
                text,
                detector_resistance: resistance,
                cosine_similarity: sim,
                fitness,
            }
        })
        .collect();

    // Prioritize candidates that satisfy the >= 0.85 semantic fidelity constraint
    let valid_pool: Vec<&OptimizationCandidate> = evaluated
        .iter()
        .filter(|c| c.cosine_similarity >= 0.85)
        .collect();

    if !valid_pool.is_empty() {
        let best = valid_pool
            .into_iter()
            .max_by(|a, b| a.fitness.partial_cmp(&b.fitness).unwrap_or(std::cmp::Ordering::Equal))
            .unwrap();
        best.clone()
    } else if let Some(best) = evaluated.into_iter().max_by(|a, b| {
        a.cosine_similarity
            .partial_cmp(&b.cosine_similarity)
            .unwrap_or(std::cmp::Ordering::Equal)
    }) {
        best
    } else {
        let profile = analyze_stylometry(original_text);
        let resistance = compute_detector_resistance(original_text, &profile);
        OptimizationCandidate {
            text: original_text.to_string(),
            detector_resistance: resistance,
            cosine_similarity: 1.0,
            fitness: resistance,
        }
    }
}

// ══════════════════════════════════════════════════════════════════════
// PROSE HUMANIZER ENGINE
// ══════════════════════════════════════════════════════════════════════

pub struct ProseHumanizer {
    client: Client,
    endpoint: String,
    model: String,
    system_instruction: String,
}

impl ProseHumanizer {
    pub fn new(endpoint: &str, model: &str) -> Self {
        let ep = endpoint.trim().trim_end_matches('/');
        let final_endpoint = if ep.ends_with("/chat/completions") || ep.ends_with("/api/chat") {
            ep.to_string()
        } else {
            format!("{}/v1/chat/completions", ep)
        };

        let system_instruction = "You are an expert human prose editor. Your goal is to rewrite \
            synthetic, stiff, or robotic text into completely natural, fluid human writing.\n\
            STRICT RULES:\n\
            1. Vary sentence lengths intentionally to create organic rhythm and burstiness.\n\
            2. Eliminate all classic AI transition clichés (e.g. 'delve into', 'testament to', 'rich tapestry', 'furthermore').\n\
            3. Use natural contractions (it's, don't, won't, can't, doesn't).\n\
            4. Keep all original facts, meaning, and intent 100% intact.\n\
            5. Return ONLY the rewritten text with zero conversational filler, introductions, or apologies."
            .to_string();

        Self {
            client: Client::builder()
                .no_proxy()
                .timeout(std::time::Duration::from_secs(120))
                .build()
                .unwrap_or_else(|_| Client::new()),
            endpoint: final_endpoint,
            model: model.to_string(),
            system_instruction,
        }
    }

    /// Primary entrypoint: executes 4-stage stylometric optimization and genetic Pareto selection
    pub async fn humanize(&self, input_text: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
        let trimmed = input_text.trim();
        if trimmed.is_empty() {
            return Ok(String::new());
        }

        // ── Candidate 1: Pure Heuristic Stylometric Mutation ──
        let cand1 = {
            let pruned = prune_cliches(trimmed);
            let contracted = inject_contractions(&pruned);
            let paced = adjust_sentence_pacing(&contracted);
            shuffle_punctuation(&paced)
        };

        // ── Candidate 2: LLM Sampling (with elevated temperature & penalties) ──
        let cand2 = self.sample_llm(trimmed).await.unwrap_or_default();

        // ── Candidate 3: Hybrid (LLM Generation + Stylometric Post-Processing) ──
        let mut candidates = vec![cand1];
        if !cand2.is_empty() {
            let cand3 = {
                let pruned = prune_cliches(&cand2);
                let contracted = inject_contractions(&pruned);
                adjust_sentence_pacing(&contracted)
            };
            candidates.push(cand2);
            candidates.push(cand3);
        }

        // ── Candidate 4: Alternate Heuristic Variation ──
        let cand4 = {
            let contracted = inject_contractions(trimmed);
            prune_cliches(&contracted)
        };
        candidates.push(cand4);

        // ── Stage 4: Pareto Selection Loop Under Semantic Anchor ──
        let selected = pareto_select_candidate(trimmed, candidates);
        Ok(selected.text)
    }

    /// Internal sampling query to LLM endpoint
    async fn sample_llm(&self, input_text: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
        let messages = vec![
            Message {
                role: "system".to_string(),
                content: self.system_instruction.clone(),
            },
            Message {
                role: "user".to_string(),
                content: format!(
                    "Rewrite the following passage into natural, highly human prose with varied sentence lengths:\n\n{}",
                    input_text
                ),
            },
        ];

        let request_payload = ChatCompletionRequest {
            model: self.model.clone(),
            messages: messages.clone(),
            temperature: 0.92,
            top_p: 0.95,
            presence_penalty: 0.50,
            frequency_penalty: 0.45,
        };

        let send_res = self
            .client
            .post(&self.endpoint)
            .json(&request_payload)
            .send()
            .await;

        match send_res {
            Ok(resp) if resp.status().is_success() => {
                let parsed: ChatCompletionResponse = resp.json().await?;
                if let Some(choice) = parsed.choices.into_iter().next() {
                    return Ok(choice.message.content.trim().to_string());
                } else if let Some(msg) = parsed.message {
                    return Ok(msg.content.trim().to_string());
                }
            }
            Ok(resp) if resp.status().as_u16() == 404 && self.endpoint.ends_with("/v1/chat/completions") => {
                let alt_endpoint = self.endpoint.replace("/v1/chat/completions", "/api/chat");
                let alt_payload = OllamaChatRequest {
                    model: self.model.clone(),
                    messages,
                    stream: false,
                    options: OllamaChatOptions {
                        temperature: 0.92,
                        top_p: 0.95,
                        presence_penalty: 0.50,
                        frequency_penalty: 0.45,
                    },
                };
                let alt_resp = self.client.post(&alt_endpoint).json(&alt_payload).send().await?;
                if alt_resp.status().is_success() {
                    let parsed: ChatCompletionResponse = alt_resp.json().await?;
                    if let Some(choice) = parsed.choices.into_iter().next() {
                        return Ok(choice.message.content.trim().to_string());
                    } else if let Some(msg) = parsed.message {
                        return Ok(msg.content.trim().to_string());
                    }
                }
            }
            _ => {}
        }

        Err("LLM sample unavailable".into())
    }
}

// ══════════════════════════════════════════════════════════════════════
// UNIT TESTS
// ══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_humanizer_construction() {
        let h1 = ProseHumanizer::new("http://127.0.0.1:11434", "qwen2.5:7b");
        assert_eq!(h1.endpoint, "http://127.0.0.1:11434/v1/chat/completions");
        assert_eq!(h1.model, "qwen2.5:7b");

        let h2 = ProseHumanizer::new("http://127.0.0.1:11434/api/chat", "qwen2.5:14b");
        assert_eq!(h2.endpoint, "http://127.0.0.1:11434/api/chat");
    }

    #[test]
    fn test_deserialization_openai_format() {
        let json_data = r#"{
            "choices": [
                {
                    "message": {
                        "content": "This is natural human prose with varied rhythm."
                    }
                }
            ]
        }"#;
        let res: ChatCompletionResponse = serde_json::from_str(json_data).unwrap();
        assert_eq!(res.choices.len(), 1);
        assert_eq!(res.choices[0].message.content, "This is natural human prose with varied rhythm.");
    }

    #[test]
    fn test_deserialization_ollama_format() {
        let json_data = r#"{
            "message": {
                "content": "Flowing organic human sentences."
            }
        }"#;
        let res: ChatCompletionResponse = serde_json::from_str(json_data).unwrap();
        assert_eq!(res.message.unwrap().content, "Flowing organic human sentences.");
    }

    #[test]
    fn test_stylometric_profile() {
        let text = "This is first sentence. This is second sentence. This is third sentence.";
        let profile = analyze_stylometry(text);

        assert_eq!(profile.sentence_count, 3);
        assert_eq!(profile.sentence_lengths, vec![4, 4, 4]);
        assert_eq!(profile.total_words, 12);
        assert!((profile.mean_length - 4.0).abs() < 1e-4);
        assert!((profile.variance - 0.0).abs() < 1e-4);
        assert!((profile.std_dev - 0.0).abs() < 1e-4);
        assert!((profile.coefficient_of_variation - 0.0).abs() < 1e-4);
        // Flatline sequence detected (3 consecutive sentences with identical or near-identical length)
        assert_eq!(profile.flatline_sequences.len(), 1);
        assert_eq!(profile.flatline_sequences[0], (0, 3));
        // Repetitive opening 'this' appears 3 times
        assert!(profile.repetitive_openings.iter().any(|(w, c)| w == "this" && *c == 3));
    }

    #[test]
    fn test_ahocorasick_cliche_pruning() {
        let text = "Furthermore, it is important to note that this is a testament to the rich tapestry of modern tech.";
        let pruned = prune_cliches(text);

        assert!(!pruned.contains("Furthermore,"));
        assert!(!pruned.contains("it is important to note that"));
        assert!(!pruned.contains("testament to"));
        assert!(!pruned.contains("rich tapestry"));
        assert!(pruned.contains("Also,") || pruned.contains("also,"));
        assert!(pruned.contains("notably,") || pruned.contains("Notably,"));
        assert!(pruned.contains("proof of"));
        assert!(pruned.contains("vibrant mix"));
    }

    #[test]
    fn test_contraction_injection() {
        let text = "It is true that they are not here, and we cannot go because you are late.";
        let contracted = inject_contractions(text);

        assert!(contracted.contains("It's"));
        assert!(contracted.contains("they're"));
        assert!(contracted.contains("can't"));
        assert!(contracted.contains("you're"));
    }

    #[test]
    fn test_compute_perplexity() {
        // Empty logprobs
        assert_eq!(compute_perplexity_from_logprobs(&[]), 0.0);

        // All logprobs = -1.0 -> mean = -1.0 -> exp(-(-1.0)) = e ≈ 2.7182818
        let logprobs = vec![-1.0, -1.0, -1.0];
        let ppl = compute_perplexity_from_logprobs(&logprobs);
        assert!((ppl - std::f64::consts::E).abs() < 1e-4);

        // logprobs with mean = -2.0 -> exp(2.0) ≈ 7.389056
        let logprobs2 = vec![-1.0, -3.0];
        let ppl2 = compute_perplexity_from_logprobs(&logprobs2);
        assert!((ppl2 - (2.0f64).exp()).abs() < 1e-4);
    }

    #[test]
    fn test_genetic_optimization_loop() {
        let original = "It is important to note that we cannot ignore these critical system issues today, and we must proceed with care.";
        let cand1 = "Note that we can't ignore these critical system issues today, and we must proceed with care.";
        let cand2 = "Completely unrelated text about baking blueberry muffins in France.";

        let selected = pareto_select_candidate(original, vec![cand1.to_string(), cand2.to_string()]);
        // The unrelated candidate (low cosine similarity) must be rejected
        assert_ne!(selected.text, cand2);
        // The high-similarity humanized candidate must be selected
        assert_eq!(selected.text, cand1);
        assert!(selected.cosine_similarity >= 0.85);
        assert!(selected.detector_resistance > 0.5);
    }
}

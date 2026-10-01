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
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    temperature: f32,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_p: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    presence_penalty: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    frequency_penalty: Option<f32>,
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

/// 160+ Classic AI Cliché and Latinate formal pairs (pattern, replacement)
const AI_CLICHE_PAIRS: &[(&str, &str)] = &[
    ("delve into", "look into"),
    ("Delve into", "Look into"),
    ("delving into", "looking into"),
    ("Delving into", "Looking into"),
    ("delves into", "looks into"),
    ("Delves into", "Looks into"),
    ("delve deeper", "look closer"),
    ("Delve deeper", "Look closer"),
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
    ("it goes without saying", "clearly"),
    ("It goes without saying", "Clearly"),
    ("furthermore,", "also,"),
    ("Furthermore,", "Also,"),
    ("furthermore", "also"),
    ("Furthermore", "Also"),
    ("moreover,", "plus,"),
    ("Moreover,", "Plus,"),
    ("moreover", "plus"),
    ("Moreover", "Plus"),
    ("in conclusion,", "overall,"),
    ("In conclusion,", "Overall,"),
    ("in conclusion", "overall"),
    ("In conclusion", "Overall"),
    ("in summary,", "in short,"),
    ("In summary,", "In short,"),
    ("in summary", "in short"),
    ("In summary", "In short"),
    ("to summarize,", "in short,"),
    ("To summarize,", "In short,"),
    ("to summarize", "in short"),
    ("To summarize", "In short"),
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
    ("revolutionized", "transformed"),
    ("Revolutionized", "Transformed"),
    ("in today's digital landscape", "today"),
    ("In today's digital landscape", "Today"),
    ("in today's fast-paced world", "in modern life"),
    ("In today's fast-paced world", "In modern life"),
    ("fast-paced world", "modern world"),
    ("Fast-paced world", "Modern world"),
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
    ("shed light on", "clarify"),
    ("Shed light on", "Clarify"),
    ("sheds light on", "clarifies"),
    ("Sheds light on", "Clarifies"),
    ("harnessing the power of", "using"),
    ("Harnessing the power of", "Using"),
    ("harness the power of", "use"),
    ("Harness the power of", "Use"),
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
    ("seamlessly integrates", "fits smoothly"),
    ("Seamlessly integrates", "Fits smoothly"),
    ("seamlessly integrated", "fit smoothly"),
    ("Seamlessly integrated", "Fit smoothly"),
    ("seamlessly", "smoothly"),
    ("Seamlessly", "Smoothly"),
    ("game-changer", "breakthrough"),
    ("Game-changer", "Breakthrough"),
    ("paradigm shift", "major shift"),
    ("Paradigm shift", "Major shift"),
    ("at the forefront of", "leading"),
    ("At the forefront of", "Leading"),
    ("undeniably", "clearly"),
    ("Undeniably", "Clearly"),
    ("holistic approach", "broad view"),
    ("Holistic approach", "Broad view"),
    ("treasure trove", "rich source"),
    ("Treasure trove", "Rich source"),
    // Latinate & Formal AI Overused Words -> Conversational Phrasal Verbs
    ("utilize", "use"),
    ("Utilize", "Use"),
    ("utilizes", "uses"),
    ("Utilizes", "Uses"),
    ("utilizing", "using"),
    ("Utilizing", "Using"),
    ("utilized", "used"),
    ("Utilized", "Used"),
    ("utilization", "use"),
    ("Utilization", "Use"),
    ("facilitate", "help"),
    ("Facilitate", "Help"),
    ("facilitates", "helps"),
    ("Facilitates", "Helps"),
    ("facilitating", "helping"),
    ("Facilitating", "Helping"),
    ("facilitated", "helped"),
    ("Facilitated", "Helped"),
    ("commence", "start"),
    ("Commence", "Start"),
    ("commences", "starts"),
    ("Commences", "Starts"),
    ("commencing", "starting"),
    ("Commencing", "Starting"),
    ("commenced", "started"),
    ("Commenced", "Started"),
    ("demonstrate", "show"),
    ("Demonstrate", "Show"),
    ("demonstrates", "shows"),
    ("Demonstrates", "Shows"),
    ("demonstrating", "showing"),
    ("Demonstrating", "Showing"),
    ("demonstrated", "showed"),
    ("Demonstrated", "Showed"),
    ("underscore", "highlight"),
    ("Underscore", "Highlight"),
    ("underscores", "highlights"),
    ("Underscores", "Highlights"),
    ("underscoring", "highlighting"),
    ("Underscoring", "Highlighting"),
    ("underscored", "highlighted"),
    ("Underscored", "Highlighted"),
    ("comprehensive", "thorough"),
    ("Comprehensive", "Thorough"),
    ("crucial", "key"),
    ("Crucial", "Key"),
    ("vital", "key"),
    ("Vital", "Key"),
    ("imperative", "needed"),
    ("Imperative", "Needed"),
    ("intricate", "subtle"),
    ("Intricate", "Subtle"),
    ("nuanced", "detailed"),
    ("Nuanced", "Detailed"),
    ("subsequently", "then"),
    ("Subsequently", "Then"),
    ("consequently", "as a result"),
    ("Consequently", "As a result"),
    ("nevertheless", "still"),
    ("Nevertheless", "Still"),
    ("nonetheless", "even so"),
    ("Nonetheless", "Even so"),
    ("in order to", "to"),
    ("In order to", "To"),
    ("due to the fact that", "because"),
    ("Due to the fact that", "Because"),
    ("serves as", "acts as"),
    ("Serves as", "Acts as"),
    ("stands as", "is"),
    ("Stands as", "Is"),
    ("foster", "build"),
    ("Foster", "Build"),
    ("fosters", "builds"),
    ("Fosters", "Builds"),
    ("fostering", "building"),
    ("Fostering", "Building"),
    ("fostered", "built"),
    ("Fostered", "Built"),
    ("align with", "fit with"),
    ("Align with", "Fit with"),
    ("aligns with", "fits with"),
    ("Aligns with", "Fits with"),
    ("aligning with", "fitting with"),
    ("Aligning with", "Fitting with"),
    ("overarching", "main"),
    ("Overarching", "Main"),
    ("cornerstone", "foundation"),
    ("Cornerstone", "Foundation"),
    ("interplay", "interaction"),
    ("Interplay", "Interaction"),
    ("resonate with", "strike a chord with"),
    ("Resonate with", "Strike a chord with"),
    ("resonates with", "strikes a chord with"),
    ("Resonates with", "Strikes a chord with"),
    ("ever-evolving", "constantly changing"),
    ("Ever-evolving", "Constantly changing"),
    ("fast-paced", "quick"),
    ("Fast-paced", "Quick"),
];

/// Contractions mapping pairs: (uncontracted, contracted) covering all auxiliary forms
const CONTRACTION_PAIRS: &[(&str, &str)] = &[
    ("it is", "it's"),
    ("It is", "It's"),
    ("that is", "that's"),
    ("That is", "That's"),
    ("what is", "what's"),
    ("What is", "What's"),
    ("there is", "there's"),
    ("There is", "There's"),
    ("here is", "here's"),
    ("Here is", "Here's"),
    ("cannot", "can't"),
    ("Cannot", "Can't"),
    ("could not", "couldn't"),
    ("Could not", "Couldn't"),
    ("do not", "don't"),
    ("Do not", "Don't"),
    ("does not", "doesn't"),
    ("Does not", "Doesn't"),
    ("did not", "didn't"),
    ("Did not", "Didn't"),
    ("will not", "won't"),
    ("Will not", "Won't"),
    ("would not", "wouldn't"),
    ("Would not", "Wouldn't"),
    ("should not", "shouldn't"),
    ("Should not", "Shouldn't"),
    ("must not", "mustn't"),
    ("Must not", "Mustn't"),
    ("they are", "they're"),
    ("They are", "They're"),
    ("we are", "we're"),
    ("We are", "We're"),
    ("you are", "you're"),
    ("You are", "You're"),
    ("they have", "they've"),
    ("They have", "They've"),
    ("we have", "we've"),
    ("We have", "We've"),
    ("you have", "you've"),
    ("You have", "You've"),
    ("I have", "I've"),
    ("they will", "they'll"),
    ("They will", "They'll"),
    ("we will", "we'll"),
    ("We will", "We'll"),
    ("you will", "you'll"),
    ("You will", "You'll"),
    ("I will", "I'll"),
    ("are not", "aren't"),
    ("Are not", "Aren't"),
    ("is not", "isn't"),
    ("Is not", "Isn't"),
    ("was not", "wasn't"),
    ("Was not", "Wasn't"),
    ("were not", "weren't"),
    ("Were not", "Weren't"),
    ("has not", "hasn't"),
    ("Has not", "Hasn't"),
    ("have not", "haven't"),
    ("Have not", "Haven't"),
    ("had not", "hadn't"),
    ("Had not", "Hadn't"),
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

/// Injects radical burstiness and sentence length diversity into text to defeat commercial AI detectors.
/// Restructures uniform sentences, inserts punchy short sentences, and uses em dashes,
/// colons, or parenthetical phrases.
pub fn inject_burstiness_and_variety(text: &str) -> String {
    let raw_sentences = split_sentences(text);
    if raw_sentences.is_empty() {
        return text.to_string();
    }

    let mut result_sentences: Vec<String> = Vec::new();
    let punchy_bridges = [
        "And that's key.",
        "Here's why.",
        "Truth is, it's that simple.",
        "That's a big deal.",
        "Now, that's what counts.",
        "Here's the reality.",
        "Naturally, that's essential.",
        "We've seen this work.",
    ];
    let mut bridge_idx = 0;

    for (i, s) in raw_sentences.iter().enumerate() {
        let words: Vec<&str> = s.split_whitespace().collect();
        let len = words.len();

        // If this is a very long sentence (> 24 words) with a conjunction or comma,
        // break it into a punchy short sentence and a clause.
        if len > 24 {
            if let Some(pos) = s.find(", and ") {
                let first = s[..pos].trim();
                let second = s[pos + 6..].trim();
                if !first.is_empty() && !second.is_empty() {
                    let mut cap_second = second.to_string();
                    if let Some(fc) = cap_second.chars().next() {
                        cap_second = format!("{}{}", fc.to_uppercase(), &cap_second[fc.len_utf8()..]);
                    }
                    result_sentences.push(format!("{}.", first.trim_end_matches(&['.', '!', '?'][..])));
                    result_sentences.push(format!("{}.", cap_second.trim_end_matches(&['.', '!', '?'][..])));
                    continue;
                }
            } else if let Some(pos) = s.find("; ") {
                let first = s[..pos].trim();
                let second = s[pos + 2..].trim();
                if !first.is_empty() && !second.is_empty() {
                    let mut cap_second = second.to_string();
                    if let Some(fc) = cap_second.chars().next() {
                        cap_second = format!("{}{}", fc.to_uppercase(), &cap_second[fc.len_utf8()..]);
                    }
                    result_sentences.push(format!("{}.", first.trim_end_matches(&['.', '!', '?'][..])));
                    result_sentences.push(format!("{}.", cap_second.trim_end_matches(&['.', '!', '?'][..])));
                    continue;
                }
            }
        }

        // Check if consecutive sentences have very similar length (diff <= 3)
        if i > 0 {
            let prev_words: Vec<&str> = raw_sentences[i - 1].split_whitespace().collect();
            let prev_len = prev_words.len();
            let diff = (len as isize - prev_len as isize).abs();

            if diff <= 3 && len >= 8 && len <= 22 {
                // Insert a short punchy bridge between them to destroy AI cadence
                let bridge = punchy_bridges[bridge_idx % punchy_bridges.len()];
                bridge_idx += 1;
                result_sentences.push(bridge.to_string());
            }
        }

        // Add parenthetical or em-dash nuance to selected medium sentences
        if len > 14 && s.contains(", ") && !s.contains("—") && !s.contains('(') {
            let modified = s.replacen(", ", " — ", 1);
            result_sentences.push(modified);
        } else {
            result_sentences.push(s.clone());
        }
    }

    // Ensure we have at least one short punchy sentence (<= 5 words) if total words >= 20
    let total_words: usize = result_sentences.iter().map(|s| s.split_whitespace().count()).sum();
    let has_short = result_sentences.iter().any(|s| s.split_whitespace().count() <= 5);
    if total_words >= 20 && !has_short {
        result_sentences.insert(0, "Here's the reality.".to_string());
    }

    // Guarantee that conversational contractions are present in the final prose
    if !result_sentences.iter().any(|s| s.contains('\'')) {
        result_sentences.push("And that's key.".to_string());
    }

    // Guarantee that human punctuation (—, :, or () is present
    let has_human_punct = result_sentences.iter().any(|s| s.contains('—') || s.contains(':') || s.contains('('));
    if !has_human_punct && result_sentences.len() >= 2 {
        if let Some(longest) = result_sentences.iter_mut().max_by_key(|s| s.len()) {
            if longest.contains(", ") {
                *longest = longest.replacen(", ", " — ", 1);
            } else {
                *longest = format!("{} — it's proven.", longest.trim_end_matches(&['.', '!', '?'][..]));
            }
        }
    }

    result_sentences.join(" ")
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

    // Spread bonus: large difference between longest and shortest sentence
    let min_len = profile.sentence_lengths.iter().copied().min().unwrap_or(0);
    let max_len = profile.sentence_lengths.iter().copied().max().unwrap_or(0);
    if max_len >= min_len + 15 {
        score += 0.08;
    } else if max_len >= min_len + 8 {
        score += 0.04;
    }

    // Flatline penalty: AI text often writes sequences of similarly-sized sentences
    score -= (profile.flatline_sequences.len() as f64) * 0.06;

    // Cliché penalty: AI markers drastically reduce detector bypass rates
    score -= (profile.cliche_count as f64) * 0.08;

    // Contraction bonus: conversational contractions are a classic human prose marker
    if candidate.contains('\'') {
        score += 0.10;
    }

    // Human punctuation bonus: em-dashes, colons, or parentheses
    if candidate.contains('—') || candidate.contains(':') || candidate.contains('(') {
        score += 0.05;
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

/// Optimization loop selecting best candidate under semantic constraint (cosine_similarity >= 0.55)
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
            let fitness = resistance.powi(2) * sim;
            OptimizationCandidate {
                text,
                detector_resistance: resistance,
                cosine_similarity: sim,
                fitness,
            }
        })
        .collect();

    // Prioritize candidates that satisfy the >= 0.55 semantic fidelity constraint
    let valid_pool: Vec<&OptimizationCandidate> = evaluated
        .iter()
        .filter(|c| c.cosine_similarity >= 0.55)
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
            fitness: resistance.powi(2),
        }
    }
}

// ══════════════════════════════════════════════════════════════════════
// PROSE HUMANIZER ENGINE (HYBRID ARCHITECTURE)
// ══════════════════════════════════════════════════════════════════════

pub struct ProseHumanizer {
    client: Client,
    endpoint: String,
    model: String,
    hf_token: Option<String>,
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

        let system_instruction = "You are an elite ghostwriter and prose humanizer. Your task is to rewrite text so that it reads like an authentic, thoughtful human wrote it by hand. It must pass all commercial AI detectors (QuillBot, Turnitin, GPTZero, CopyLeaks) with 0% AI score.\n\
        MANDATORY STYLOMETRIC LAWS:\n\
        1. RADICAL BURSTINESS: Strictly vary sentence lengths. Mix very short sentences (3 to 6 words) with long, flowing descriptive sentences (25 to 35 words). Never allow two consecutive sentences of similar length.\n\
        2. VOCABULARY UNPREDICTABILITY: Never use standard AI buzzwords (delve, tapestry, crucial, testament, pivotal, foster, realm, landscape, multifaceted, paramount, underscore, comprehensive, facilitate, utilize, vital, moreover, furthermore, seamlessly, revolutionize, intricate, nuanced). Use everyday, down-to-earth words and phrasal verbs (e.g. 'work with' instead of 'utilize', 'dig into' instead of 'delve', 'show' instead of 'demonstrate', 'set up' instead of 'implement').\n\
        3. COLLOQUIAL SYNTAX & CONTRACTIONS: Use natural contractions throughout (it's, don't, won't, can't, doesn't, we've, they're). Use natural conversational bridges ('Truth is,', 'Now,', 'And here's why:', 'Naturally,', 'Still,').\n\
        4. HUMAN PUNCTUATION: Use occasional em dashes (—), colons (:), and parenthetical thoughts to reflect human thought progression.\n\
        5. PRESERVE 100% OF FACTS & MEANING: Never drop facts, data, arguments, or technical meaning. Keep all details accurate.\n\
        6. OUTPUT ONLY THE REWRITTEN PROSE: Zero introductory throat-clearing, zero meta commentary, zero quotation marks around the entire text.".to_string();

        let hf_token = std::env::var("HF_TOKEN").or_else(|_| std::env::var("HUGGINGFACE_TOKEN")).ok();

        Self {
            client: Client::builder()
                .no_proxy()
                .timeout(std::time::Duration::from_secs(8))
                .build()
                .unwrap_or_else(|_| Client::new()),
            endpoint: final_endpoint,
            model: model.to_string(),
            hf_token,
            system_instruction,
        }
    }

    pub fn with_hf_token(mut self, token: Option<String>) -> Self {
        if token.is_some() {
            self.hf_token = token;
        }
        self
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
            let bursty = inject_burstiness_and_variety(&contracted);
            let paced = adjust_sentence_pacing(&bursty);
            shuffle_punctuation(&paced)
        };

        // ── Candidate 2: LLM Sampling (from Hugging Face Router or local Ollama) ──
        let cand2 = self.sample_llm(trimmed).await.unwrap_or_default();

        // ── Candidate 3: Hybrid (LLM Generation + Stylometric Post-Processing) ──
        let mut candidates = vec![cand1];
        if !cand2.is_empty() {
            let cand3 = {
                let pruned = prune_cliches(&cand2);
                let contracted = inject_contractions(&pruned);
                let bursty = inject_burstiness_and_variety(&contracted);
                adjust_sentence_pacing(&bursty)
            };
            candidates.push(cand2);
            candidates.push(cand3);
        }

        // ── Candidate 4: Alternate Heuristic Variation ──
        let cand4 = {
            let contracted = inject_contractions(trimmed);
            let pruned = prune_cliches(&contracted);
            inject_burstiness_and_variety(&pruned)
        };
        candidates.push(cand4);

        // ── Candidate 5: Additional Burstiness Variation ──
        let cand5 = {
            let pruned = prune_cliches(trimmed);
            let bursty = inject_burstiness_and_variety(&pruned);
            let contracted = inject_contractions(&bursty);
            shuffle_punctuation(&contracted)
        };
        candidates.push(cand5);

        // ── Stage 4: Pareto Selection Loop Under Semantic Anchor ──
        let selected = pareto_select_candidate(trimmed, candidates);
        Ok(selected.text)
    }

    /// Internal sampling query to LLM endpoint with Hugging Face Router and Ollama fallback
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
            max_tokens: Some(1024),
            temperature: 0.95,
            top_p: Some(0.92),
            presence_penalty: Some(0.60),
            frequency_penalty: Some(0.65),
        };

        // 1. If an HF token is configured or model looks like a HF repo, query Hugging Face Router API
        if let Some(ref token) = self.hf_token {
            let hf_payload = ChatCompletionRequest {
                model: self.model.clone(),
                messages: messages.clone(),
                max_tokens: Some(1024),
                temperature: 0.7,
                top_p: None,
                presence_penalty: None,
                frequency_penalty: None,
            };
            let hf_urls = [
                &self.endpoint,
                "https://router.huggingface.co/v1/chat/completions",
                "https://api-inference.huggingface.co/v1/chat/completions",
            ];
            for &url in &hf_urls {
                let send_res = self
                    .client
                    .post(url)
                    .header("Authorization", format!("Bearer {}", token))
                    .header("Content-Type", "application/json")
                    .json(&hf_payload)
                    .send()
                    .await;

                if let Ok(resp) = send_res {
                    if resp.status().is_success() {
                        if let Ok(parsed) = resp.json::<ChatCompletionResponse>().await {
                            if let Some(choice) = parsed.choices.into_iter().next() {
                                return Ok(choice.message.content.trim().to_string());
                            } else if let Some(msg) = parsed.message {
                                return Ok(msg.content.trim().to_string());
                            }
                        }
                    }
                }
            }
        }

        // 2. Primary configured endpoint query
        let mut req_builder = self.client.post(&self.endpoint).json(&request_payload);
        if let Some(ref token) = self.hf_token {
            req_builder = req_builder.header("Authorization", format!("Bearer {}", token));
        }
        let send_res = req_builder.send().await;

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
                    messages: messages.clone(),
                    stream: false,
                    options: OllamaChatOptions {
                        temperature: 0.95,
                        top_p: 0.92,
                        presence_penalty: 0.60,
                        frequency_penalty: 0.65,
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

        // 3. Fallback to local Ollama if remote HF failed or was unreachable
        if self.hf_token.is_some() || self.endpoint.contains("huggingface.co") {
            let local_ollama_urls = [
                "http://127.0.0.1:11434/v1/chat/completions",
                "http://127.0.0.1:11434/api/chat",
            ];
            for &fallback_url in &local_ollama_urls {
                if fallback_url.ends_with("/api/chat") {
                    let alt_payload = OllamaChatRequest {
                        model: "qwen2.5:7b".to_string(),
                        messages: messages.clone(),
                        stream: false,
                        options: OllamaChatOptions {
                            temperature: 0.95,
                            top_p: 0.92,
                            presence_penalty: 0.60,
                            frequency_penalty: 0.65,
                        },
                    };
                    if let Ok(resp) = self.client.post(fallback_url).json(&alt_payload).send().await {
                        if resp.status().is_success() {
                            if let Ok(parsed) = resp.json::<ChatCompletionResponse>().await {
                                if let Some(choice) = parsed.choices.into_iter().next() {
                                    return Ok(choice.message.content.trim().to_string());
                                } else if let Some(msg) = parsed.message {
                                    return Ok(msg.content.trim().to_string());
                                }
                            }
                        }
                    }
                } else {
                    let local_payload = ChatCompletionRequest {
                        model: "qwen2.5:7b".to_string(),
                        messages: messages.clone(),
                        max_tokens: Some(1024),
                        temperature: 0.95,
                        top_p: Some(0.92),
                        presence_penalty: Some(0.60),
                        frequency_penalty: Some(0.65),
                    };
                    if let Ok(resp) = self.client.post(fallback_url).json(&local_payload).send().await {
                        if resp.status().is_success() {
                            if let Ok(parsed) = resp.json::<ChatCompletionResponse>().await {
                                if let Some(choice) = parsed.choices.into_iter().next() {
                                    return Ok(choice.message.content.trim().to_string());
                                } else if let Some(msg) = parsed.message {
                                    return Ok(msg.content.trim().to_string());
                                }
                            }
                        }
                    }
                }
            }
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
    fn test_aggressive_cliche_pruning() {
        let text = "We must utilize this tool to facilitate collaboration, commence the project, demonstrate the results, and underscore our comprehensive approach. Furthermore, it is important to note the rich tapestry of innovations.";
        let pruned = prune_cliches(text);
        assert!(!pruned.contains("utilize"));
        assert!(!pruned.contains("facilitate"));
        assert!(!pruned.contains("commence"));
        assert!(!pruned.contains("demonstrate"));
        assert!(!pruned.contains("underscore"));
        assert!(!pruned.contains("comprehensive"));
        assert!(!pruned.contains("Furthermore,"));
        assert!(!pruned.contains("it is important to note"));
        assert!(!pruned.contains("rich tapestry"));
        assert!(pruned.contains("use"));
        assert!(pruned.contains("help"));
        assert!(pruned.contains("start"));
        assert!(pruned.contains("show"));
        assert!(pruned.contains("highlight"));
        assert!(pruned.contains("thorough"));
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
    fn test_burstiness_injection() {
        let text = "Artificial intelligence continues to transform modern software development across many sectors. Machine learning algorithms provide advanced automation for complex workflows. Organizations must adopt these technologies to maintain competitive operational efficiency.";
        let bursty = inject_burstiness_and_variety(text);
        let profile = analyze_stylometry(&bursty);
        assert!(profile.sentence_count >= 3);
        assert!(bursty != text);
        // Ensure there is sentence length variation
        let min_len = profile.sentence_lengths.iter().copied().min().unwrap_or(0);
        let max_len = profile.sentence_lengths.iter().copied().max().unwrap_or(0);
        assert!(max_len > min_len, "Expected sentence length variation");
        assert!(profile.flatline_sequences.is_empty(), "Flatline sequences must be broken");
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
        assert!(selected.cosine_similarity >= 0.55);
        assert!(selected.detector_resistance > 0.5);
    }

    #[test]
    fn test_pareto_selection_permits_paraphrase() {
        let original = "Organizations must utilize comprehensive artificial intelligence frameworks to facilitate workflow optimization.";
        // cand_robotic keeps AI words
        let cand_robotic = "Organizations must utilize comprehensive artificial intelligence frameworks to facilitate workflow optimization.";
        // cand_human has lower cosine similarity (~0.58), but high detector resistance (>0.90)
        let cand_human = "Organizations must use thorough artificial intelligence frameworks to help workflow optimization. It's clear — and it works. Consider this now.";

        let selected = pareto_select_candidate(original, vec![cand_robotic.to_string(), cand_human.to_string()]);
        assert_eq!(selected.text, cand_human);
        assert!(selected.cosine_similarity >= 0.55);
        assert!(selected.detector_resistance > 0.85);
    }

    #[test]
    fn test_detector_resistance_score_exceeds_90() {
        let text = "Teams use thorough AI tools to help speed up everyday workflows. It's that simple — and it works. Consider this now.";
        let profile = analyze_stylometry(text);
        let score = compute_detector_resistance(text, &profile);
        assert!(score >= 0.90, "Detector resistance score was {} (expected >= 0.90)", score);
    }
}

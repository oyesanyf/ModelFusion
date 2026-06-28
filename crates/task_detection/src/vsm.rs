use std::collections::{HashMap, HashSet};
use serde::{Deserialize, Serialize};

/// List of standard English stop words to filter out uninformative noise terms.
const STOP_WORDS: &[&str] = &[
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
];

/// A sparse term weight vector representing an embedding in vector space.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TermVector {
    pub weights: HashMap<String, f64>,
}

impl TermVector {
    /// Tokenize a prompt and build its term weight vector (raw term frequency).
    pub fn from_prompt(prompt: &str) -> Self {
        let stop_set: HashSet<&str> = STOP_WORDS.iter().cloned().collect();
        let mut weights = HashMap::new();
        
        // Clean and tokenize the prompt
        let cleaned = prompt
            .to_lowercase()
            .replace(|c: char| !c.is_alphanumeric() && c != ' ', " ");
        
        let tokens: Vec<&str> = cleaned
            .split_whitespace()
            .filter(|token| !stop_set.contains(token) && token.len() > 1)
            .collect();
            
        let total_tokens = tokens.len() as f64;
        if total_tokens > 0.0 {
            for token in tokens {
                *weights.entry(token.to_string()).or_insert(0.0) += 1.0;
            }
            // Normalize counts to term frequencies
            for (_, val) in weights.iter_mut() {
                *val /= total_tokens;
            }
        }
        
        let mut vector = TermVector { weights };
        vector.normalize();
        vector
    }

    /// Normalize the vector to unit length (L2 norm).
    pub fn normalize(&mut self) {
        let sum_squares: f64 = self.weights.values().map(|w| w * w).sum();
        if sum_squares > 0.0 {
            let magnitude = sum_squares.sqrt();
            for (_, val) in self.weights.iter_mut() {
                *val /= magnitude;
            }
        }
    }

    /// Compute the Cosine Similarity with another term vector.
    pub fn cosine_similarity(&self, other: &Self) -> f64 {
        let mut dot_product = 0.0;
        for (term, &w1) in &self.weights {
            if let Some(&w2) = other.weights.get(term) {
                dot_product += w1 * w2;
            }
        }
        dot_product
    }

    /// Update a category centroid embedding using an Exponential Moving Average (EMA).
    ///
    /// - `alpha`: learning rate (0.0 to 1.0).
    /// - `prune_threshold`: weights below this value are removed to prevent feature inflation/drift.
    pub fn update_centroid(&mut self, exemplar: &Self, alpha: f64, prune_threshold: f64) {
        // Create union of all terms
        let mut new_weights = HashMap::new();
        let all_keys: HashSet<&String> = self.weights.keys().chain(exemplar.weights.keys()).collect();
        
        for key in all_keys {
            let old_w = *self.weights.get(key).unwrap_or(&0.0);
            let new_w = *exemplar.weights.get(key).unwrap_or(&0.0);
            
            // EMA update formula
            let updated_w = (1.0 - alpha) * old_w + alpha * new_w;
            if updated_w >= prune_threshold {
                new_weights.insert(key.clone(), updated_w);
            }
        }
        
        self.weights = new_weights;
        self.normalize(); // Re-normalize to unit length to prevent drift
    }
}

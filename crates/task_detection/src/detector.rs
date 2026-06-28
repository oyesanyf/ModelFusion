//! Intelligent task detector implementation.

use crate::keywords::{get_general_knowledge_patterns, get_task_patterns};
use crate::language::detect_language;
use crate::vsm::TermVector;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::sync::Mutex;

/// Result of task detection analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDetectionResult {
    pub task_type: String,
    pub language: String,
    pub confidence: f64,
    pub context: String,
    pub attributes: HashMap<String, serde_json::Value>,
    pub extraction_method: String,
}

/// Detects task type from natural language prompts using keyword patterns and TF-IDF embeddings.
pub struct IntelligentTaskDetector {
    /// Thread-safe task category centroids.
    centroids: Mutex<HashMap<String, TermVector>>,
    /// Simple thread-safe cache with a max size.
    cache: Mutex<HashMap<String, TaskDetectionResult>>,
    cache_max_size: usize,
}

impl Default for IntelligentTaskDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl IntelligentTaskDetector {
    /// Create a new detector.
    pub fn new() -> Self {
        Self {
            centroids: Mutex::new(build_initial_centroids()),
            cache: Mutex::new(HashMap::new()),
            cache_max_size: 256,
        }
    }

    /// Detect the most likely task type from a prompt.
    pub fn detect_task_type(&self, prompt: &str) -> TaskDetectionResult {
        // Check cache first
        if let Ok(cache) = self.cache.lock() {
            if let Some(cached) = cache.get(prompt) {
                return cached.clone();
            }
        }

        // Run hybrid detection
        let result = self.detect_hybrid(prompt);

        // Store in cache
        if let Ok(mut cache) = self.cache.lock() {
            if cache.len() >= self.cache_max_size {
                cache.clear();
            }
            cache.insert(prompt.to_string(), result.clone());
        }

        result
    }

    /// Run the hybrid detection combining exact regex keyword match and VSM cosine similarity.
    fn detect_hybrid(&self, prompt: &str) -> TaskDetectionResult {
        let prompt_lower = self.to_lower_case(prompt);
        let prompt_vector = TermVector::from_prompt(prompt);
        
        let mut regex_scores = HashMap::new();
        let mut cosine_scores = HashMap::new();
        let mut final_scores = HashMap::new();
        
        let task_patterns = get_task_patterns();
        
        // 1. Calculate regex exact matching scores
        for (task_type, patterns) in task_patterns {
            let mut score = 0;
            for re in patterns {
                if re.is_match(&prompt_lower) {
                    score += 1;
                }
            }
            regex_scores.insert(task_type.clone(), score);
        }

        // 2. Calculate cosine similarity matching scores
        if let Ok(centroids) = self.centroids.lock() {
            for (task_type, centroid) in centroids.iter() {
                let similarity = prompt_vector.cosine_similarity(centroid);
                cosine_scores.insert(task_type.clone(), similarity);
            }
        }

        // Special handling for question-answering to distinguish between extractive and generative
        if let Some(&qa_score) = regex_scores.get("question-answering") {
            if qa_score > 0 {
                let gk_patterns = get_general_knowledge_patterns();
                if gk_patterns.iter().any(|re| re.is_match(&prompt_lower)) {
                    // Boost text-generation
                    let text_gen_score = regex_scores.entry("text-generation".to_string()).or_insert(0);
                    *text_gen_score += 2;
                    // Reset question-answering
                    regex_scores.insert("question-answering".to_string(), 0);
                    
                    // Boost text-generation cosine score slightly as well
                    let text_gen_cosine = cosine_scores.entry("text-generation".to_string()).or_insert(0.0);
                    *text_gen_cosine = (*text_gen_cosine + 0.3).min(1.0);
                    cosine_scores.insert("question-answering".to_string(), 0.0);
                }
            }
        }

        // 3. Combine scores: 40% regex pattern weight + 60% term embedding similarity weight
        let mut best_task = "text-generation".to_string();
        let mut max_score = -1.0;
        let mut has_matches = false;

        let all_tasks = vec![
            "text-classification", "text-generation", "translation", "summarization",
            "question-answering", "image-classification", "object-detection",
            "automatic-speech-recognition", "code-analysis", "malware-detection"
        ];

        for task in all_tasks {
            let reg_score = *regex_scores.get(task).unwrap_or(&0) as f64;
            let cos_score = *cosine_scores.get(task).unwrap_or(&0.0);
            
            // Normalize regex score to a 0.0 - 1.0 scale
            let reg_score_norm = (reg_score / 3.0).min(1.0);
            
            // Hybrid score formula
            let combined_score = reg_score_norm * 0.4 + cos_score * 0.6;
            final_scores.insert(task.to_string(), combined_score);

            if combined_score > max_score {
                max_score = combined_score;
                best_task = task.to_string();
                if reg_score > 0.0 || cos_score > 0.1 {
                    has_matches = true;
                }
            }
        }

        // Detect language
        let detected_language = detect_language(prompt);

        let (task_type, confidence, context) = if !has_matches {
            (
                "text-generation".to_string(),
                0.5,
                "general text generation".to_string(),
            )
        } else {
            let ctx = format!("hybrid-embedding {}", best_task);
            (best_task, max_score, ctx)
        };

        let mut attributes = HashMap::new();
        attributes.insert("hybrid_scores".to_string(), json!(final_scores));
        attributes.insert("regex_scores".to_string(), json!(regex_scores));
        attributes.insert("cosine_scores".to_string(), json!(cosine_scores));

        TaskDetectionResult {
            task_type,
            language: detected_language,
            confidence,
            context,
            attributes,
            extraction_method: "hybrid_vsm".to_string(),
        }
    }

    /// Register feedback/usage correction to dynamically shift the task centroid vector.
    ///
    /// This keeps task routing fresh while employing a unit L2 norm and term pruning
    /// threshold to prevent semantic drift.
    pub fn register_feedback(&self, prompt: &str, corrected_task: &str) {
        let exemplar = TermVector::from_prompt(prompt);
        
        if let Ok(mut centroids) = self.centroids.lock() {
            if let Some(centroid) = centroids.get_mut(corrected_task) {
                // Update with 15% learning rate and 0.01 weight pruning threshold
                centroid.update_centroid(&exemplar, 0.15, 0.01);
                log::info!("Updated task centroid for '{}' based on feedback.", corrected_task);
            } else {
                centroids.insert(corrected_task.to_string(), exemplar);
            }
        }

        // Clear the cache to apply updated centroid weights
        if let Ok(mut cache) = self.cache.lock() {
            cache.clear();
        }
    }

    /// Helper method to mimic prompt lower-casing.
    fn to_lower_case(&self, s: &str) -> String {
        s.to_lowercase()
    }

    /// Get metadata for a specific task type.
    pub fn get_task_metadata(&self, task_type: &str) -> serde_json::Value {
        let task_metadata = json!({
            "text-classification": {
                "description": "Classify text into categories",
                "examples": ["sentiment analysis", "topic classification", "spam detection"],
                "file_types": [".txt", ".csv", ".json"],
                "models": ["bert-base-uncased", "distilbert-base-uncased"]
            },
            "text-generation": {
                "description": "Generate text content",
                "examples": ["story writing", "article generation", "code explanation"],
                "file_types": [".txt", ".md", ".py", ".js"],
                "models": ["gpt2", "gpt2-medium", "distilgpt2"]
            },
            "image-classification": {
                "description": "Classify images into categories",
                "examples": ["object recognition", "scene classification", "image identification"],
                "file_types": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                "models": ["google/vit-base-patch16-224", "microsoft/resnet-50"]
            },
            "summarization": {
                "description": "Summarize text content",
                "examples": ["document summarization", "article summarization", "meeting notes"],
                "file_types": [".txt", ".md", ".pdf"],
                "models": ["facebook/bart-large-cnn", "t5-base"]
            },
            "translation": {
                "description": "Translate text between languages",
                "examples": ["English to Spanish", "French to German", "multilingual translation"],
                "file_types": [".txt", ".md"],
                "models": ["Helsinki-NLP/opus-mt-en-es", "t5-base"]
            },
            "code-analysis": {
                "description": "Analyze and explain code",
                "examples": ["code review", "bug detection", "code explanation"],
                "file_types": [".py", ".js", ".java", ".cpp", ".c"],
                "models": ["microsoft/codebert-base", "gpt2"]
            }
        });

        task_metadata.get(task_type).cloned().unwrap_or(json!({
            "description": "Unknown task type",
            "examples": [],
            "file_types": [],
            "models": []
        }))
    }
}

/// Construct initial centroids using predefined task keywords.
fn build_initial_centroids() -> HashMap<String, TermVector> {
    let mut centroids = HashMap::new();
    let task_keywords = vec![
        (
            "text-classification",
            "classify categorize sentiment emotion topic spam fake real positive negative label classification"
        ),
        (
            "text-generation",
            "generate write create compose story poem article essay text content explain generation"
        ),
        (
            "translation",
            "translate convert language english spanish french german chinese japanese portuguese translation"
        ),
        (
            "summarization",
            "summarize summary brief condense extract key points main idea overview summarization"
        ),
        (
            "question-answering",
            "answer question what is how to why explain describe define tell me query"
        ),
        (
            "image-classification",
            "image picture photo visual object scene identify recognize what is this what's in this classification"
        ),
        (
            "object-detection",
            "detect find locate objects bounding box where is position coordinates detection"
        ),
        (
            "automatic-speech-recognition",
            "speech audio voice transcribe transcription listen hear convert speech speech to text recognition"
        ),
        (
            "code-analysis",
            "code program script function class bug error vulnerability review explain code analysis"
        ),
        (
            "malware-detection",
            "malware virus trojan spyware ransomware malicious threat security scan detect threat detection"
        )
    ];

    for (task, keywords) in task_keywords {
        centroids.insert(task.to_string(), TermVector::from_prompt(keywords));
    }
    
    centroids
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hybrid_classification() {
        let detector = IntelligentTaskDetector::new();
        
        let r1 = detector.detect_task_type("translate this code into French");
        assert_eq!(r1.task_type, "translation");

        let r2 = detector.detect_task_type("explain how this python class works");
        assert_eq!(r2.task_type, "code-analysis");

        let r3 = detector.detect_task_type("write a short story about a coding robot");
        assert_eq!(r3.task_type, "text-generation");
    }

    #[test]
    fn test_feedback_learning_and_drift_prevention() {
        let detector = IntelligentTaskDetector::new();

        // 1. Initial classification of a custom slang prompt
        let prompt = "glitchy crash on line 42";
        let _r_init = detector.detect_task_type(prompt);
        
        // 2. Correct it to code-analysis via feedback
        detector.register_feedback(prompt, "code-analysis");

        // 3. Check that similar slang now maps to code-analysis with higher confidence
        let r_after = detector.detect_task_type("glitchy line 42");
        assert_eq!(r_after.task_type, "code-analysis");

        // 4. Verify drift prevention (L2 norm should be exactly 1.0, and terms are pruned)
        {
            let centroids = detector.centroids.lock().unwrap();
            let centroid = centroids.get("code-analysis").unwrap();
            let sum_sq: f64 = centroid.weights.values().map(|w| w * w).sum();
            assert!((sum_sq - 1.0).abs() < 1e-5, "Centroid L2 norm is not normalized: {}", sum_sq);
            assert!(centroid.weights.values().all(|&w| w >= 0.01), "Pruned weights still present");
        }
    }
}


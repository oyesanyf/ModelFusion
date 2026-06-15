//! Intelligent task detector implementation.

use crate::keywords::{get_general_knowledge_patterns, get_task_patterns};
use crate::language::detect_language;
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

/// Detects task type from natural language prompts using keyword patterns.
pub struct IntelligentTaskDetector {
    // Simple thread-safe cache with a max size.
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
            cache: Mutex::new(HashMap::new()),
            cache_max_size: 256,
        }
    }

    /// Detect the most likely task type from a prompt.
    pub fn detect_task_type(&self, prompt: &str) -> TaskDetectionResult {
        // Check cache first
        if let Ok(mut cache) = self.cache.lock() {
            if let Some(cached) = cache.get(prompt) {
                return cached.clone();
            }
        }

        // Detect task with keywords
        let result = self.detect_with_keywords(prompt);

        // Store in cache
        if let Ok(mut cache) = self.cache.lock() {
            if cache.len() >= self.cache_max_size {
                // Clear the cache to prevent unbounded growth if it gets too large
                cache.clear();
            }
            cache.insert(prompt.to_string(), result.clone());
        }

        result
    }

    /// Run the keyword detection logic.
    fn detect_with_keywords(&self, prompt: &str) -> TaskDetectionResult {
        let prompt_lower = self.to_lower_case(prompt);
        let mut scores = HashMap::new();
        let task_patterns = get_task_patterns();

        // Calculate scores for each task type
        for (task_type, patterns) in task_patterns {
            let mut score = 0;
            for re in patterns {
                if re.is_match(&prompt_lower) {
                    score += 1;
                }
            }
            scores.insert(task_type.clone(), score);
        }

        // Special handling for question-answering to distinguish between extractive and generative
        if let Some(&qa_score) = scores.get("question-answering") {
            if qa_score > 0 {
                let gk_patterns = get_general_knowledge_patterns();
                if gk_patterns.iter().any(|re| re.is_match(&prompt_lower)) {
                    // Boost text-generation
                    let text_gen_score = scores.entry("text-generation".to_string()).or_insert(0);
                    *text_gen_score += 2;
                    // Reset question-answering
                    scores.insert("question-answering".to_string(), 0);
                }
            }
        }

        // Detect language
        let detected_language = detect_language(prompt);

        // Get best task type
        let mut best_task = "text-generation".to_string();
        let mut max_score = 0;
        let mut has_matches = false;

        for (task, &score) in &scores {
            if score > max_score {
                max_score = score;
                best_task = task.clone();
                has_matches = true;
            }
        }

        let (task_type, confidence, context) = if !has_matches {
            (
                "text-generation".to_string(),
                0.5,
                "general text generation".to_string(),
            )
        } else {
            let conf = (max_score as f64 / 3.0).min(1.0);
            let ctx = format!("keyword-based {}", best_task);
            (best_task, conf, ctx)
        } ;

        let mut attributes = HashMap::new();
        let scores_json = json!(scores);
        attributes.insert("keyword_scores".to_string(), scores_json);

        TaskDetectionResult {
            task_type,
            language: detected_language,
            confidence,
            context,
            attributes,
            extraction_method: "keyword_matching".to_string(),
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

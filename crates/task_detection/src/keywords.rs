//! Keyword patterns for task type detection.

use regex::Regex;
use std::collections::HashMap;
use std::sync::OnceLock;

/// Get the mapping of task types to their keyword regex patterns.
pub fn get_task_patterns() -> &'static HashMap<String, Vec<Regex>> {
    static PATTERNS: OnceLock<HashMap<String, Vec<Regex>>> = OnceLock::new();
    PATTERNS.get_or_init(|| {
        let raw_patterns = vec![
            (
                "text-classification",
                vec![
                    "classify", "categorize", "sentiment", "emotion", "topic",
                    "spam", "fake", "real", "positive", "negative", "label",
                ],
            ),
            (
                "text-generation",
                vec![
                    "generate", "write", "create", "compose", "story",
                    "poem", "article", "essay", "text", "content", "explain",
                ],
            ),
            (
                "translation",
                vec![
                    "translate", "convert", "language", "english", "spanish",
                    "french", "german", "chinese", "japanese", "portuguese",
                ],
            ),
            (
                "summarization",
                vec![
                    "summarize", "summary", "brief", "condense", "extract",
                    "key points", "main idea", "overview",
                ],
            ),
            (
                "question-answering",
                vec![
                    "answer", "question", "what is", "how to", "why",
                    "explain", "describe", "define", "tell me",
                ],
            ),
            (
                "image-classification",
                vec![
                    "image", "picture", "photo", "visual", "object",
                    "scene", "identify", "recognize", "what is this", "what's in this",
                ],
            ),
            (
                "object-detection",
                vec![
                    "detect", "find", "locate", "objects", "bounding box",
                    "where is", "position", "coordinates",
                ],
            ),
            (
                "automatic-speech-recognition",
                vec![
                    "speech", "audio", "voice", "transcribe", "transcription",
                    "listen", "hear", "convert speech", "speech to text",
                ],
            ),
            (
                "code-analysis",
                vec![
                    "code", "program", "script", "function", "class",
                    "bug", "error", "vulnerability", "review", "explain code",
                ],
            ),
            (
                "malware-detection",
                vec![
                    "malware", "virus", "trojan", "spyware", "ransomware",
                    "malicious", "threat", "security", "scan", "detect threat",
                ],
            ),
        ];

        raw_patterns
            .into_iter()
            .map(|(task, keywords)| {
                let regexes = keywords
                    .into_iter()
                    .map(|kw| Regex::new(&format!("(?i){}", regex_escape(kw))).unwrap())
                    .collect();
                (task.to_string(), regexes)
            })
            .collect()
    })
}

/// Helper to escape regex special characters, though our keywords are simple.
fn regex_escape(s: &str) -> String {
    let mut escaped = String::new();
    for c in s.chars() {
        if "\\^$.|?*+()[]{}".contains(c) {
            escaped.push('\\');
        }
        escaped.push(c);
    }
    escaped
}

/// Specific general knowledge patterns to filter QA into text generation.
pub fn get_general_knowledge_patterns() -> &'static Vec<Regex> {
    static GENERAL_KNOWLEDGE: OnceLock<Vec<Regex>> = OnceLock::new();
    GENERAL_KNOWLEDGE.get_or_init(|| {
        let patterns = vec![
            r"what is the capital of",
            r"what is the population of",
            r"who is the president of",
            r"when was",
            r"where is",
            r"how many",
            r"what year",
            r"what country",
            r"what city",
            r"what language",
            r"what currency",
            r"what religion",
            r"what is the largest",
            r"what is the smallest",
            r"what is the oldest",
            r"what is the newest",
        ];
        patterns
            .into_iter()
            .map(|p| Regex::new(&format!("(?i){}", p)).unwrap())
            .collect()
    })
}

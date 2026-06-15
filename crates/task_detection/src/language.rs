//! Language detection helpers.

use regex::Regex;
use std::collections::HashMap;
use std::sync::OnceLock;

/// Get the mapping of language codes to their regex patterns.
pub fn get_language_patterns() -> &'static HashMap<String, Vec<Regex>> {
    static PATTERNS: OnceLock<HashMap<String, Vec<Regex>>> = OnceLock::new();
    PATTERNS.get_or_init(|| {
        let raw_patterns = vec![
            (
                "en",
                vec![
                    r"\b(english|en)\b",
                    r"\b(the|a|an|is|are|was|were)\b",
                ],
            ),
            (
                "es",
                vec![
                    r"\b(español|espanol|es)\b",
                    r"\b(el|la|los|las|es|son|era|eran)\b",
                ],
            ),
            (
                "fr",
                vec![
                    r"\b(français|francais|fr)\b",
                    r"\b(le|la|les|est|sont|était|étaient)\b",
                ],
            ),
            (
                "de",
                vec![
                    r"\b(deutsch|de)\b",
                    r"\b(der|die|das|ist|sind|war|waren)\b",
                ],
            ),
            (
                "zh",
                vec![
                    r"\b(中文|chinese|zh)\b",
                    r"[\u4e00-\u9fff]",
                ],
            ),
            (
                "ja",
                vec![
                    r"\b(日本語|japanese|ja)\b",
                    r"[\u3040-\u309f\u30a0-\u30ff]",
                ],
            ),
        ];

        raw_patterns
            .into_iter()
            .map(|(lang, patterns)| {
                let regexes = patterns
                    .into_iter()
                    .map(|p| Regex::new(&format!("(?i){}", p)).unwrap())
                    .collect();
                (lang.to_string(), regexes)
            })
            .collect()
    })
}

/// Detect the language of a prompt using the pre-defined patterns.
pub fn detect_language(prompt: &str) -> String {
    let patterns = get_language_patterns();
    for (lang_code, regexes) in patterns {
        for re in regexes {
            if re.is_match(prompt) {
                return lang_code.clone();
            }
        }
    }
    "en".to_string()
}

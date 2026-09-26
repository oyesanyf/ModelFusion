//! Semantic DOM pruner and Set-of-Mark (SoM) tagger for ModelFusion browser workflows.
//!
//! Prunes verbose DOM trees to extract essential semantic content while stripping scripts,
//! styles, inline SVGs, comments, and boilerplate. Injects Set-of-Mark indices (`[1]`, `[2]`, etc.)
//! into interactive elements (buttons, links, inputs, selects), reducing LLM token consumption
//! by 85-95% while maintaining complete actionability.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Configuration options for DOM pruning.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DomPrunerOptions {
    /// Maximum length of the pruned output text in characters (default: 80,000).
    pub max_text_len: usize,
    /// Maximum number of interactive elements to mark (default: 500).
    pub max_interactive_elements: usize,
    /// Whether to include hyperlinks (`href` targets) in output text.
    pub include_links: bool,
    /// Whether to include image `alt` descriptions in output text.
    pub include_images: bool,
}

impl Default for DomPrunerOptions {
    fn default() -> Self {
        Self {
            max_text_len: 80_000,
            max_interactive_elements: 500,
            include_links: true,
            include_images: true,
        }
    }
}

/// An interactive element identified in the DOM with an assigned Set-of-Mark index.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InteractiveElement {
    /// Set-of-Mark integer identifier (1-indexed).
    pub id: usize,
    /// HTML tag name (e.g., "button", "a", "input", "select", "textarea").
    pub tag: String,
    /// Semantic element category (e.g., "button", "text", "search", "link", "checkbox", "submit").
    pub element_type: String,
    /// Visible text label, placeholder, aria-label, or value.
    pub text: String,
    /// CSS selector or targeted query to locate this element via CDP.
    pub selector: String,
    /// Attribute key-value pairs (href, id, name, placeholder, role, etc.).
    pub attributes: HashMap<String, String>,
}

/// The result of semantic DOM pruning.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PrunedDom {
    /// Token-optimized semantic representation of the document with Set-of-Mark tags.
    pub text: String,
    /// List of interactive elements extracted and marked with indices.
    pub interactive_elements: Vec<InteractiveElement>,
    /// Original HTML character count before pruning.
    pub original_char_count: usize,
    /// Pruned text character count.
    pub pruned_char_count: usize,
    /// Percentage reduction in token/character volume (0.0 to 100.0).
    pub token_reduction_pct: f64,
}

impl PrunedDom {
    /// Looks up an interactive element by its Set-of-Mark ID.
    pub fn find_element(&self, mark_id: usize) -> Option<&InteractiveElement> {
        self.interactive_elements.iter().find(|el| el.id == mark_id)
    }

    /// Finds interactive elements matching a substring in their text or attributes.
    pub fn find_by_text(&self, query: &str) -> Vec<&InteractiveElement> {
        let q = query.to_lowercase();
        self.interactive_elements
            .iter()
            .filter(|el| {
                el.text.to_lowercase().contains(&q)
                    || el.attributes.values().any(|v| v.to_lowercase().contains(&q))
            })
            .collect()
    }
}

/// Core engine for DOM pruning and Set-of-Mark injection.
pub struct DomPruner;

impl DomPruner {
    /// Prunes raw HTML content according to the provided options.
    pub fn prune_html(raw_html: &str, options: &DomPrunerOptions) -> PrunedDom {
        let original_char_count = raw_html.len();
        if original_char_count == 0 {
            return PrunedDom {
                text: String::new(),
                interactive_elements: Vec::new(),
                original_char_count: 0,
                pruned_char_count: 0,
                token_reduction_pct: 0.0,
            };
        }

        // Step 1: Strip scripts, styles, SVGs, iframes, noscripts, and HTML comments
        let cleaned_html = Self::strip_non_content_tags(raw_html);

        // Step 2: Extract interactive elements and inject Set-of-Mark tags
        let (marked_text, interactive_elements) =
            Self::extract_and_mark_elements(&cleaned_html, options);

        // Step 3: Format semantic structure (headings, lists, paragraphs)
        let structured_text = Self::format_semantic_text(&marked_text, options);

        // Step 4: Enforce character limits to prevent token blowup
        let final_text = if structured_text.len() > options.max_text_len {
            let mut truncated = structured_text[..options.max_text_len].to_string();
            truncated.push_str("\n\n[... Truncated due to size limit ...]");
            truncated
        } else {
            structured_text
        };

        let pruned_char_count = final_text.len();
        let reduction = if original_char_count > 0 {
            let saved = original_char_count.saturating_sub(pruned_char_count);
            (saved as f64 / original_char_count as f64) * 100.0
        } else {
            0.0
        };

        PrunedDom {
            text: final_text,
            interactive_elements,
            original_char_count,
            pruned_char_count,
            token_reduction_pct: (reduction * 100.0).round() / 100.0,
        }
    }

    /// Strips `<script>`, `<style>`, `<svg>`, `<noscript>`, `<iframe`, and HTML comments.
    fn strip_non_content_tags(html: &str) -> String {
        // Strip comments <!-- ... -->
        let re_comments = Regex::new(r"(?s)<!--.*?-->").unwrap();
        let html_no_comments = re_comments.replace_all(html, " ");

        // Strip scripts
        let re_script = Regex::new(r"(?si)<script\b[^>]*>.*?</script>").unwrap();
        let s1 = re_script.replace_all(&html_no_comments, " ");

        // Strip styles
        let re_style = Regex::new(r"(?si)<style\b[^>]*>.*?</style>").unwrap();
        let s2 = re_style.replace_all(&s1, " ");

        // Strip SVGs
        let re_svg = Regex::new(r"(?si)<svg\b[^>]*>.*?</svg>").unwrap();
        let s3 = re_svg.replace_all(&s2, " ");

        // Strip noscript
        let re_noscript = Regex::new(r"(?si)<noscript\b[^>]*>.*?</noscript>").unwrap();
        let s4 = re_noscript.replace_all(&s3, " ");

        // Strip iframe
        let re_iframe = Regex::new(r"(?si)<iframe\b[^>]*>.*?</iframe>").unwrap();
        let s5 = re_iframe.replace_all(&s4, " ");

        // Strip meta and link tags
        let re_meta = Regex::new(r"(?si)<(meta|link)\b[^>]*>").unwrap();
        let s6 = re_meta.replace_all(&s5, " ");

        s6.to_string()
    }

    /// Extracts interactive elements and injects Set-of-Mark markers.
    fn extract_and_mark_elements(
        html: &str,
        options: &DomPrunerOptions,
    ) -> (String, Vec<InteractiveElement>) {
        let mut elements: Vec<InteractiveElement> = Vec::new();
        let mut counter = 1;

        // Pattern matching interactive and structural tags with zero backreferences:
        let re_tag = Regex::new(
            r#"(?si)<a\b([^>]*)>(.*?)</a>|<button\b([^>]*)>(.*?)</button>|<select\b([^>]*)>(.*?)</select>|<textarea\b([^>]*)>(.*?)</textarea>|<input\b([^>]*)>|<h([1-6])\b([^>]*)>(.*?)</h[1-6]>|<li\b([^>]*)>(.*?)</li>|<img\b([^>]*)>"#
        ).unwrap();

        let mut output = String::with_capacity(html.len());
        let mut last_end = 0;

        for cap in re_tag.captures_iter(html) {
            let full_match = cap.get(0).unwrap();
            let start = full_match.start();
            let end = full_match.end();

            output.push_str(&html[last_end..start]);
            last_end = end;

            // Determine tag name and attribute string
            let (tag_name, attrs_raw, inner_html) = if let Some(m) = cap.get(1) {
                ("a".to_string(), m.as_str(), cap.get(2).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(3) {
                ("button".to_string(), m.as_str(), cap.get(4).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(5) {
                ("select".to_string(), m.as_str(), cap.get(6).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(7) {
                ("textarea".to_string(), m.as_str(), cap.get(8).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(9) {
                ("input".to_string(), m.as_str(), "")
            } else if let Some(lvl) = cap.get(10) {
                (format!("h{}", lvl.as_str()), cap.get(11).map(|m| m.as_str()).unwrap_or(""), cap.get(12).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(13) {
                ("li".to_string(), m.as_str(), cap.get(14).map(|m| m.as_str()).unwrap_or(""))
            } else if let Some(m) = cap.get(15) {
                ("img".to_string(), m.as_str(), "")
            } else {
                continue;
            };

            let attrs = Self::parse_attributes(attrs_raw);
            let is_interactive = Self::is_interactive_tag(&tag_name, &attrs);

            if is_interactive && counter <= options.max_interactive_elements {
                let mark_id = counter;
                counter += 1;

                let text_label = Self::extract_element_label(&tag_name, inner_html, &attrs);
                let element_type = Self::determine_element_type(&tag_name, &attrs);
                let selector = Self::build_selector(&tag_name, mark_id, &attrs, &text_label);

                elements.push(InteractiveElement {
                    id: mark_id,
                    tag: tag_name.clone(),
                    element_type: element_type.clone(),
                    text: text_label.clone(),
                    selector,
                    attributes: attrs.clone(),
                });

                // Format the Set-of-Mark inline representation
                let mut mark_repr = format!("[{}]({}: \"{}\"", mark_id, element_type, text_label);
                if options.include_links {
                    if let Some(href) = attrs.get("href") {
                        if !href.trim().is_empty() && !href.starts_with('#') && !href.starts_with("javascript:") {
                            mark_repr.push_str(&format!(", href: \"{}\"", href.trim()));
                        }
                    }
                }
                mark_repr.push(')');
                output.push_str(&mark_repr);
            } else {
                // If not interactive, preserve text or structural contents
                if Self::is_structural_heading(&tag_name) {
                    let level = tag_name.chars().nth(1).unwrap_or('1');
                    let hashes = "#".repeat(level.to_digit(10).unwrap_or(1) as usize);
                    let inner_clean = Self::strip_html_tags(inner_html);
                    output.push_str(&format!("\n\n{} {}\n", hashes, inner_clean.trim()));
                } else if tag_name == "p" || tag_name == "div" || tag_name == "section" || tag_name == "article" {
                    output.push_str(&format!(" {} ", inner_html));
                } else if tag_name == "li" {
                    let inner_clean = Self::strip_html_tags(inner_html);
                    output.push_str(&format!("\n- {}", inner_clean.trim()));
                } else if tag_name == "img" && options.include_images {
                    if let Some(alt) = attrs.get("alt") {
                        if !alt.trim().is_empty() {
                            output.push_str(&format!(" [Image: \"{}\"] ", alt.trim()));
                        }
                    }
                } else {
                    output.push_str(inner_html);
                }
            }
        }

        output.push_str(&html[last_end..]);
        (output, elements)
    }

    /// Determines if a tag and its attributes constitute an actionable interactive element.
    fn is_interactive_tag(tag: &str, attrs: &HashMap<String, String>) -> bool {
        match tag {
            "button" | "input" | "select" | "textarea" => true,
            "a" => attrs.contains_key("href") || attrs.contains_key("onclick"),
            _ => {
                if let Some(role) = attrs.get("role") {
                    let r = role.to_lowercase();
                    if r == "button"
                        || r == "link"
                        || r == "checkbox"
                        || r == "menuitem"
                        || r == "tab"
                        || r == "searchbox"
                        || r == "switch"
                    {
                        return true;
                    }
                }
                attrs.contains_key("onclick") || attrs.contains_key("tabindex")
            }
        }
    }

    /// Extracts clean visible label or fallback description for an interactive element.
    fn extract_element_label(
        tag: &str,
        inner_html: &str,
        attrs: &HashMap<String, String>,
    ) -> String {
        // Priority 1: aria-label
        if let Some(aria) = attrs.get("aria-label") {
            if !aria.trim().is_empty() {
                return aria.trim().to_string();
            }
        }

        // Priority 2: inner text (stripped of tags)
        let inner_text = Self::strip_html_tags(inner_html).trim().to_string();
        if !inner_text.is_empty() {
            return inner_text;
        }

        // Priority 3: placeholder
        if let Some(ph) = attrs.get("placeholder") {
            if !ph.trim().is_empty() {
                return ph.trim().to_string();
            }
        }

        // Priority 4: value attribute
        if let Some(val) = attrs.get("value") {
            if !val.trim().is_empty() {
                return val.trim().to_string();
            }
        }

        // Priority 5: title attribute
        if let Some(title) = attrs.get("title") {
            if !title.trim().is_empty() {
                return title.trim().to_string();
            }
        }

        // Priority 6: name or id attribute
        if let Some(name) = attrs.get("name") {
            return format!("name:{}", name);
        }
        if let Some(id) = attrs.get("id") {
            return format!("id:{}", id);
        }

        format!("unlabeled_{}", tag)
    }

    /// Identifies element category (submit, text, button, checkbox, link, etc.).
    fn determine_element_type(tag: &str, attrs: &HashMap<String, String>) -> String {
        if tag == "a" {
            return "Link".to_string();
        }
        if tag == "button" {
            return "Button".to_string();
        }
        if tag == "select" {
            return "Select".to_string();
        }
        if tag == "textarea" {
            return "Textarea".to_string();
        }
        if tag == "input" {
            let t = attrs.get("type").map(|s| s.as_str()).unwrap_or("text").to_lowercase();
            return match t.as_str() {
                "submit" => "SubmitButton".to_string(),
                "button" => "Button".to_string(),
                "checkbox" => "Checkbox".to_string(),
                "radio" => "Radio".to_string(),
                "search" => "SearchInput".to_string(),
                "password" => "PasswordInput".to_string(),
                "email" => "EmailInput".to_string(),
                _ => "Input".to_string(),
            };
        }
        if let Some(role) = attrs.get("role") {
            return role.clone();
        }
        tag.to_string()
    }

    /// Builds a reliable CDP selector for an interactive element.
    fn build_selector(
        tag: &str,
        mark_id: usize,
        attrs: &HashMap<String, String>,
        label: &str,
    ) -> String {
        if let Some(id) = attrs.get("id") {
            if !id.trim().is_empty() && !id.contains(' ') {
                return format!("#{}", id.trim());
            }
        }
        if let Some(name) = attrs.get("name") {
            if !name.trim().is_empty() {
                return format!("{}[name=\"{}\"]", tag, name.trim());
            }
        }
        if let Some(data_id) = attrs.get("data-testid") {
            return format!("[data-testid=\"{}\"]", data_id);
        }
        if let Some(aria) = attrs.get("aria-label") {
            return format!("{}[aria-label=\"{}\"]", tag, aria);
        }
        if !label.is_empty() && !label.starts_with("unlabeled_") && label.len() < 30 {
            return format!("{}:has-text(\"{}\")", tag, label);
        }
        format!("{}:nth-of-type({})", tag, mark_id)
    }

    /// Formats the raw pruned text into clean Markdown-like structure.
    fn format_semantic_text(text: &str, _options: &DomPrunerOptions) -> String {
        // Strip remaining HTML tags
        let plain = Self::strip_html_tags(text);

        // Normalize multiple blank lines to at most two
        let re_multi_newlines = Regex::new(r"\n{3,}").unwrap();
        let s1 = re_multi_newlines.replace_all(&plain, "\n\n");

        // Normalize multiple inline whitespace
        let re_multi_spaces = Regex::new(r"[ \t]{2,}").unwrap();
        let s2 = re_multi_spaces.replace_all(&s1, " ");

        // Trim each line
        let mut result = String::with_capacity(s2.len());
        for line in s2.lines() {
            let trimmed = line.trim();
            if !trimmed.is_empty() {
                result.push_str(trimmed);
                result.push('\n');
            } else {
                result.push('\n');
            }
        }

        result.trim().to_string()
    }

    /// Strips all HTML tags while preserving text contents.
    pub fn strip_html_tags(html: &str) -> String {
        let re_tags = Regex::new(r"<[^>]*>").unwrap();
        re_tags.replace_all(html, " ").to_string()
    }

    /// Parses HTML tag attribute strings into a HashMap.
    fn parse_attributes(attr_str: &str) -> HashMap<String, String> {
        let mut map = HashMap::new();
        let re_attr = Regex::new(r#"([a-zA-Z0-9_\-]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?"#).unwrap();

        for cap in re_attr.captures_iter(attr_str) {
            let key = cap[1].to_lowercase();
            let val = cap
                .get(2)
                .or_else(|| cap.get(3))
                .or_else(|| cap.get(4))
                .map(|m| m.as_str().to_string())
                .unwrap_or_else(|| "true".to_string());
            map.insert(key, val);
        }

        map
    }

    fn is_structural_heading(tag: &str) -> bool {
        matches!(tag, "h1" | "h2" | "h3" | "h4" | "h5" | "h6")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_script_style_svg_stripping() {
        let raw = r#"
            <html>
                <head>
                    <title>Test Page</title>
                    <style>.hidden { display: none; }</style>
                    <script>console.log("secret"); alert(1);</script>
                </head>
                <body>
                    <!-- A comment here -->
                    <svg width="100" height="100"><circle cx="50" cy="50" r="40" /></svg>
                    <h1>Welcome to HugOS</h1>
                    <p>The open-source multi-modal operating system.</p>
                </body>
            </html>
        "#;

        let options = DomPrunerOptions::default();
        let pruned = DomPruner::prune_html(raw, &options);

        assert!(!pruned.text.contains("console.log"));
        assert!(!pruned.text.contains(".hidden"));
        assert!(!pruned.text.contains("circle cx"));
        assert!(!pruned.text.contains("A comment here"));
        assert!(pruned.text.contains("# Welcome to HugOS"));
        assert!(pruned.text.contains("The open-source multi-modal operating system."));
        assert!(pruned.token_reduction_pct > 30.0);
    }

    #[test]
    fn test_set_of_mark_extraction() {
        let raw = r#"
            <div>
                <a href="https://huggingface.co/models" id="models-link">Explore Models</a>
                <button type="submit" id="search-btn">Search</button>
                <input type="text" name="q" placeholder="Search 2M+ models..." />
                <select name="sort">
                    <option value="downloads">Most Downloads</option>
                </select>
            </div>
        "#;

        let options = DomPrunerOptions::default();
        let pruned = DomPruner::prune_html(raw, &options);

        assert_eq!(pruned.interactive_elements.len(), 4);

        let el1 = pruned.find_element(1).expect("Element 1 should exist");
        assert_eq!(el1.tag, "a");
        assert_eq!(el1.text, "Explore Models");
        assert_eq!(el1.selector, "#models-link");

        let el2 = pruned.find_element(2).expect("Element 2 should exist");
        assert_eq!(el2.tag, "button");
        assert_eq!(el2.text, "Search");

        let el3 = pruned.find_element(3).expect("Element 3 should exist");
        assert_eq!(el3.tag, "input");
        assert_eq!(el3.attributes.get("name").unwrap(), "q");

        // Verify Set-of-Mark tags exist in the text representation
        assert!(pruned.text.contains("[1](Link: \"Explore Models\""));
        assert!(pruned.text.contains("[2](Button: \"Search\")"));
        assert!(pruned.text.contains("[3](Input: \"Search 2M+ models...\")"));
    }

    #[test]
    fn test_token_reduction_ratio() {
        let mut huge_page = String::from("<html><head><style>");
        for i in 0..500 {
            huge_page.push_str(&format!(".class_{} {{ color: red; margin: 10px; }}\n", i));
        }
        huge_page.push_str("</style><script>");
        for i in 0..500 {
            huge_page.push_str(&format!("function f{}() {{ return {}; }}\n", i, i));
        }
        huge_page.push_str("</script></head><body><h1>Content</h1><button>Click</button></body></html>");

        let options = DomPrunerOptions::default();
        let pruned = DomPruner::prune_html(&huge_page, &options);

        assert!(pruned.token_reduction_pct >= 90.0, "Expected >=90% token reduction, got {:.2}%", pruned.token_reduction_pct);
    }
}

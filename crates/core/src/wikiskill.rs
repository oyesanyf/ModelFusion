//! WikiSkill: Wikipedia Knowledge Retrieval, Deep Section Extraction, Cross-Reference Linking & Skill Distillation Engine.
//! Inspired by Stahl-G/wikiskill and native multi-modal agent experience compiling.

use anyhow::{anyhow, Result};
use reqwest;
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Strips HTML tags (e.g. `<span class="searchmatch">...</span>`, `<p>`, `<b>`) and unescapes basic HTML entities.
pub fn strip_html_tags(input: &str) -> String {
    let mut output = String::with_capacity(input.len());
    let mut in_tag = false;

    for ch in input.chars() {
        if ch == '<' {
            in_tag = true;
        } else if ch == '>' {
            in_tag = false;
        } else if !in_tag {
            output.push(ch);
        }
    }

    // Unescape common HTML entities
    output
        .replace("&quot;", "\"")
        .replace("&apos;", "'")
        .replace("&#039;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&#160;", " ")
}

/// A search hit returned from Wikipedia search API.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WikiSearchResult {
    pub title: String,
    pub page_id: u64,
    pub snippet: String,
    pub url: String,
    pub word_count: usize,
}

/// A hierarchical section of a Wikipedia article.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WikiSection {
    pub index: String,
    pub line: String,
    pub level: usize,
    pub anchor: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
}

/// Detailed Wikipedia article content including lead extract, section outline, cross-references, and citations.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WikiArticleDetail {
    pub title: String,
    pub page_id: u64,
    pub url: String,
    pub extract: String,
    pub sections: Vec<WikiSection>,
    pub cross_references: Vec<String>,
    pub citations: Vec<String>,
    pub categories: Vec<String>,
}

/// Synthesized knowledge distillation report with key takeaways and verified citations.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WikiDistillationReport {
    pub topic: String,
    pub article: WikiArticleDetail,
    pub related_results: Vec<WikiSearchResult>,
    pub distilled_summary: String,
    pub key_takeaways: Vec<String>,
    pub grounded_citations: Vec<String>,
}

/// URL encode helper for query parameters
fn encode_uri_component(val: &str) -> String {
    let mut encoded = String::new();
    for b in val.bytes() {
        match b {
            b'a'..=b'z' | b'A'..=b'Z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                encoded.push(b as char);
            }
            b' ' => encoded.push_str("%20"),
            _ => {
                encoded.push_str(&format!("%{:02X}", b));
            }
        }
    }
    encoded
}

/// Format title for Wikipedia URLs (spaces replaced with underscores)
pub fn format_wiki_title_url(title: &str) -> String {
    let formatted = title.trim().replace(' ', "_");
    format!("https://en.wikipedia.org/wiki/{}", encode_uri_component(&formatted))
}

/// Parses the JSON response from Wikipedia's `action=query&list=search` API.
pub fn parse_wikipedia_search_json(json_str: &str) -> Result<Vec<WikiSearchResult>> {
    let v: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| anyhow!("Failed to parse Wikipedia search JSON: {}", e))?;

    let search_arr = match v.get("query").and_then(|q| q.get("search")).and_then(|s| s.as_array()) {
        Some(arr) => arr,
        None => return Ok(Vec::new()),
    };

    let mut results = Vec::new();
    for item in search_arr {
        let title = item.get("title").and_then(|t| t.as_str()).unwrap_or("").to_string();
        if title.is_empty() {
            continue;
        }
        let page_id = item.get("pageid").and_then(|p| p.as_u64()).unwrap_or(0);
        let raw_snippet = item.get("snippet").and_then(|s| s.as_str()).unwrap_or("");
        let clean_snippet = strip_html_tags(raw_snippet);
        let word_count = item.get("wordcount").and_then(|w| w.as_u64()).unwrap_or(0) as usize;
        let url = format_wiki_title_url(&title);

        results.push(WikiSearchResult {
            title,
            page_id,
            snippet: clean_snippet,
            url,
            word_count,
        });
    }

    Ok(results)
}

/// Parses the JSON response from Wikipedia's `action=parse&prop=sections` API.
pub fn parse_wikipedia_sections_json(json_str: &str) -> Result<Vec<WikiSection>> {
    let v: serde_json::Value = serde_json::from_str(json_str)
        .map_err(|e| anyhow!("Failed to parse Wikipedia sections JSON: {}", e))?;

    let sections_arr = match v.get("parse").and_then(|p| p.get("sections")).and_then(|s| s.as_array()) {
        Some(arr) => arr,
        None => return Ok(Vec::new()),
    };

    let mut sections = Vec::new();
    for s in sections_arr {
        let index = s.get("index").and_then(|i| i.as_str()).unwrap_or("").to_string();
        let raw_line = s.get("line").and_then(|l| l.as_str()).unwrap_or("");
        let line = strip_html_tags(raw_line);
        let level = s.get("level")
            .and_then(|l| l.as_str())
            .and_then(|l_str| l_str.parse::<usize>().ok())
            .or_else(|| s.get("level").and_then(|l| l.as_u64()).map(|u| u as usize))
            .unwrap_or(2);
        let anchor = s.get("anchor").and_then(|a| a.as_str()).unwrap_or("").to_string();

        if !line.is_empty() {
            sections.push(WikiSection {
                index,
                line,
                level,
                anchor,
                content: None,
            });
        }
    }

    Ok(sections)
}

/// Parses internal links, external citations, and categories from Wikipedia's `action=query` API.
pub fn parse_wikipedia_query_links_and_extlinks(json_str: &str) -> (Vec<String>, Vec<String>, Vec<String>) {
    let v: serde_json::Value = match serde_json::from_str(json_str) {
        Ok(val) => val,
        Err(_) => return (Vec::new(), Vec::new(), Vec::new()),
    };

    let mut cross_refs = Vec::new();
    let mut citations = Vec::new();
    let mut categories = Vec::new();

    if let Some(pages) = v.get("query").and_then(|q| q.get("pages")).and_then(|p| p.as_object()) {
        for (_page_id, page_data) in pages {
            // Extract internal cross-reference links
            if let Some(links) = page_data.get("links").and_then(|l| l.as_array()) {
                for l in links {
                    if let Some(title) = l.get("title").and_then(|t| t.as_str()) {
                        // Skip internal Wikipedia meta pages
                        if !title.starts_with("Wikipedia:")
                            && !title.starts_with("Template:")
                            && !title.starts_with("Help:")
                            && !title.starts_with("Category:")
                            && !cross_refs.contains(&title.to_string())
                        {
                            cross_refs.push(title.to_string());
                        }
                    }
                }
            }

            // Extract external citations
            if let Some(extlinks) = page_data.get("extlinks").and_then(|el| el.as_array()) {
                for el in extlinks {
                    if let Some(url) = el.get("*").and_then(|u| u.as_str()) {
                        let trimmed = url.trim();
                        if !trimmed.is_empty() && !citations.contains(&trimmed.to_string()) {
                            citations.push(trimmed.to_string());
                        }
                    }
                }
            }

            // Extract categories
            if let Some(cats) = page_data.get("categories").and_then(|c| c.as_array()) {
                for c in cats {
                    if let Some(cat_title) = c.get("title").and_then(|t| t.as_str()) {
                        let clean_cat = cat_title.trim_start_matches("Category:").trim().to_string();
                        if !clean_cat.is_empty() && !categories.contains(&clean_cat) {
                            categories.push(clean_cat);
                        }
                    }
                }
            }
        }
    }

    (cross_refs, citations, categories)
}

/// Parses plain text lead extract from Wikipedia query JSON.
pub fn parse_wikipedia_extract_json(json_str: &str) -> (String, u64, String) {
    let v: serde_json::Value = match serde_json::from_str(json_str) {
        Ok(val) => val,
        Err(_) => return (String::new(), 0, String::new()),
    };

    if let Some(pages) = v.get("query").and_then(|q| q.get("pages")).and_then(|p| p.as_object()) {
        for (page_id_str, page_data) in pages {
            let pid = page_id_str.parse::<u64>().unwrap_or(0);
            let title = page_data.get("title").and_then(|t| t.as_str()).unwrap_or("").to_string();
            let extract = page_data.get("extract").and_then(|e| e.as_str()).unwrap_or("").trim().to_string();
            return (extract, pid, title);
        }
    }

    (String::new(), 0, String::new())
}

/// Searches Wikipedia for the specified query string, returning ranked search hits.
pub async fn search_wikipedia(query: &str, limit: usize) -> Result<Vec<WikiSearchResult>> {
    let clean_q = query.trim();
    if clean_q.is_empty() {
        return Ok(Vec::new());
    }

    let encoded_query = encode_uri_component(clean_q);
    let clamped_limit = limit.clamp(1, 50);
    let url = format!(
        "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={}&utf8=1&format=json&srlimit={}",
        encoded_query, clamped_limit
    );

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .user_agent("ModelFusion-WikiSkill/1.0 (https://github.com/oyesanyf/ModelFusion)")
        .build()?;

    let resp = client.get(&url).send().await?;
    if !resp.status().is_success() {
        return Err(anyhow!("Wikipedia search HTTP error: {}", resp.status()));
    }

    let body = resp.text().await?;
    parse_wikipedia_search_json(&body)
}

/// Fetches section outlines for a Wikipedia article.
pub async fn fetch_wikipedia_sections(title: &str) -> Result<Vec<WikiSection>> {
    let clean_title = title.trim();
    if clean_title.is_empty() {
        return Ok(Vec::new());
    }

    let encoded_title = encode_uri_component(clean_title);
    let url = format!(
        "https://en.wikipedia.org/w/api.php?action=parse&page={}&prop=sections&format=json",
        encoded_title
    );

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .user_agent("ModelFusion-WikiSkill/1.0 (https://github.com/oyesanyf/ModelFusion)")
        .build()?;

    let resp = client.get(&url).send().await?;
    if !resp.status().is_success() {
        return Err(anyhow!("Wikipedia sections HTTP error: {}", resp.status()));
    }

    let body = resp.text().await?;
    parse_wikipedia_sections_json(&body)
}

/// Fetches a complete Wikipedia article detail: extract, section tree, cross-references, and external citations.
pub async fn fetch_wikipedia_article(title: &str) -> Result<WikiArticleDetail> {
    let clean_title = title.trim();
    if clean_title.is_empty() {
        return Err(anyhow!("Article title cannot be empty"));
    }

    let encoded_title = encode_uri_component(clean_title);
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .user_agent("ModelFusion-WikiSkill/1.0 (https://github.com/oyesanyf/ModelFusion)")
        .build()?;

    // 1. Fetch extract, internal links, external citations, and categories
    let query_url = format!(
        "https://en.wikipedia.org/w/api.php?action=query&prop=extracts|info|links|extlinks|categories&exintro=1&explaintext=1&titles={}&inprop=url&pllimit=40&ellimit=30&cllimit=20&format=json",
        encoded_title
    );

    let query_resp = client.get(&query_url).send().await?;
    let query_body = if query_resp.status().is_success() {
        query_resp.text().await?
    } else {
        String::new()
    };

    let (extract, page_id, resolved_title) = parse_wikipedia_extract_json(&query_body);
    let (cross_refs, citations, categories) = parse_wikipedia_query_links_and_extlinks(&query_body);
    let final_title = if !resolved_title.is_empty() { resolved_title } else { clean_title.to_string() };
    let article_url = format_wiki_title_url(&final_title);

    // 2. Fetch section structure
    let sections = fetch_wikipedia_sections(&final_title).await.unwrap_or_default();

    Ok(WikiArticleDetail {
        title: final_title,
        page_id,
        url: article_url,
        extract,
        sections,
        cross_references: cross_refs,
        citations,
        categories,
    })
}

/// Distills Wikipedia knowledge for a topic: queries search, resolves authoritative page,
/// extracts section tree, cross-references, and citations, and generates key takeaways.
pub async fn distill_wikipedia_knowledge(topic: &str, max_sections: usize) -> Result<WikiDistillationReport> {
    let clean_topic = topic.trim();
    if clean_topic.is_empty() {
        return Err(anyhow!("Topic query cannot be empty"));
    }

    // 1. Search Wikipedia
    let search_results = search_wikipedia(clean_topic, 6).await?;
    if search_results.is_empty() {
        return Err(anyhow!("No Wikipedia articles found matching topic '{}'", clean_topic));
    }

    // 2. Select authoritative top article
    let top_hit = search_results[0].clone();
    let article = fetch_wikipedia_article(&top_hit.title).await?;

    // 3. Generate key takeaways from lead extract and sections
    let mut takeaways = Vec::new();
    if !article.extract.is_empty() {
        let sentences: Vec<&str> = article.extract
            .split(". ")
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();
        for sentence in sentences.into_iter().take(3) {
            let mut formatted = sentence.to_string();
            if !formatted.ends_with('.') {
                formatted.push('.');
            }
            takeaways.push(formatted);
        }
    }

    // Add key section headers to takeaways
    let section_limit = max_sections.max(3);
    for s in article.sections.iter().take(section_limit) {
        if !s.line.is_empty() && !s.line.eq_ignore_ascii_case("references") && !s.line.eq_ignore_ascii_case("see also") && !s.line.eq_ignore_ascii_case("external links") {
            takeaways.push(format!("Key Section: {}", s.line));
        }
    }

    // 4. Grounded citations
    let mut grounded_citations = Vec::new();
    for (idx, cite) in article.citations.iter().take(8).enumerate() {
        grounded_citations.push(format!("[{}] {}", idx + 1, cite));
    }

    let related_results = search_results.into_iter().skip(1).collect();

    Ok(WikiDistillationReport {
        topic: clean_topic.to_string(),
        article,
        related_results,
        distilled_summary: top_hit.snippet.clone(),
        key_takeaways: takeaways,
        grounded_citations,
    })
}

/// Formats a `WikiDistillationReport` into clean, publication-ready markdown.
pub fn format_wiki_markdown(report: &WikiDistillationReport) -> String {
    let mut md = String::new();
    let art = &report.article;

    md.push_str(&format!("📖 **Wikipedia Knowledge Distillation: [{}]({})**\n\n", art.title, art.url));

    if !art.extract.is_empty() {
        md.push_str("### Summary\n");
        md.push_str(&art.extract);
        md.push_str("\n\n");
    } else if !report.distilled_summary.is_empty() {
        md.push_str("### Summary\n");
        md.push_str(&report.distilled_summary);
        md.push_str("\n\n");
    }

    if !report.key_takeaways.is_empty() {
        md.push_str("### Key Findings & Structural Takeaways\n");
        for t in &report.key_takeaways {
            md.push_str(&format!("- {}\n", t));
        }
        md.push_str("\n");
    }

    if !art.sections.is_empty() {
        md.push_str("### Deep Section Retrieval\n");
        for s in art.sections.iter().take(12) {
            let indent = "  ".repeat(s.level.saturating_sub(2));
            md.push_str(&format!("{}- **{}** (`#{}`)\n", indent, s.line, s.anchor));
        }
        md.push_str("\n");
    }

    if !art.cross_references.is_empty() {
        md.push_str("### Related Cross-References\n");
        let sample_refs: Vec<String> = art.cross_references.iter().take(10).map(|r| {
            format!("[{}](https://en.wikipedia.org/wiki/{})", r, encode_uri_component(&r.replace(' ', "_")))
        }).collect();
        md.push_str(&sample_refs.join(" • "));
        md.push_str("\n\n");
    }

    if !report.grounded_citations.is_empty() {
        md.push_str("### Verified Citations & External Grounding\n");
        for c in &report.grounded_citations {
            md.push_str(&format!("- {}\n", c));
        }
        md.push_str("\n");
    }

    if !report.related_results.is_empty() {
        md.push_str("### Related Wikipedia Articles\n");
        for (i, rel) in report.related_results.iter().take(4).enumerate() {
            md.push_str(&format!("{}. **[{}]({})**", i + 1, rel.title, rel.url));
            if !rel.snippet.is_empty() {
                md.push_str(&format!(" — {}\n", rel.snippet));
            } else {
                md.push('\n');
            }
        }
    }

    md
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_html_tags() {
        let input = "In <span class=\"searchmatch\">deep</span> <b>learning</b>, &quot;transformers&quot; are great &amp; powerful.";
        let expected = "In deep learning, \"transformers\" are great & powerful.";
        assert_eq!(strip_html_tags(input), expected);
    }

    #[test]
    fn test_format_wiki_title_url() {
        let title = "Transformer (deep learning architecture)";
        let url = format_wiki_title_url(title);
        assert_eq!(url, "https://en.wikipedia.org/wiki/Transformer_%28deep_learning_architecture%29");
    }

    #[test]
    fn test_parse_wikipedia_search_json() {
        let mock_json = r#"{
            "query": {
                "search": [
                    {
                        "ns": 0,
                        "title": "Transformer (deep learning)",
                        "pageid": 63973680,
                        "size": 128450,
                        "wordcount": 8940,
                        "snippet": "A <span class=\"searchmatch\">transformer</span> is a deep learning architecture based on self-attention.",
                        "timestamp": "2026-01-01T00:00:00Z"
                    }
                ]
            }
        }"#;

        let results = parse_wikipedia_search_json(mock_json).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].title, "Transformer (deep learning)");
        assert_eq!(results[0].page_id, 63973680);
        assert_eq!(results[0].word_count, 8940);
        assert_eq!(results[0].snippet, "A transformer is a deep learning architecture based on self-attention.");
        assert_eq!(results[0].url, "https://en.wikipedia.org/wiki/Transformer_%28deep_learning%29");
    }

    #[test]
    fn test_parse_wikipedia_sections_json() {
        let mock_json = r#"{
            "parse": {
                "title": "Transformer (deep learning)",
                "pageid": 63973680,
                "sections": [
                    { "toclevel": 1, "level": "2", "line": "History", "number": "1", "index": "1", "anchor": "History" },
                    { "toclevel": 2, "level": "3", "line": "Predecessors", "number": "1.1", "index": "2", "anchor": "Predecessors" },
                    { "toclevel": 1, "level": "2", "line": "Architecture", "number": "2", "index": "3", "anchor": "Architecture" }
                ]
            }
        }"#;

        let sections = parse_wikipedia_sections_json(mock_json).unwrap();
        assert_eq!(sections.len(), 3);
        assert_eq!(sections[0].line, "History");
        assert_eq!(sections[0].level, 2);
        assert_eq!(sections[0].index, "1");
        assert_eq!(sections[1].line, "Predecessors");
        assert_eq!(sections[1].level, 3);
        assert_eq!(sections[2].line, "Architecture");
    }

    #[test]
    fn test_parse_wikipedia_links_and_citations() {
        let mock_json = r#"{
            "query": {
                "pages": {
                    "63973680": {
                        "pageid": 63973680,
                        "title": "Transformer (deep learning)",
                        "links": [
                            { "ns": 0, "title": "Attention (machine learning)" },
                            { "ns": 0, "title": "Natural language processing" },
                            { "ns": 4, "title": "Wikipedia:Neutral point of view" }
                        ],
                        "extlinks": [
                            { "*": "https://arxiv.org/abs/1706.03762" },
                            { "*": "https://ai.googleblog.com" }
                        ],
                        "categories": [
                            { "ns": 14, "title": "Category:Deep learning architectures" }
                        ]
                    }
                }
            }
        }"#;

        let (cross_refs, citations, categories) = parse_wikipedia_query_links_and_extlinks(mock_json);
        assert_eq!(cross_refs, vec!["Attention (machine learning)", "Natural language processing"]);
        assert_eq!(citations, vec!["https://arxiv.org/abs/1706.03762", "https://ai.googleblog.com"]);
        assert_eq!(categories, vec!["Deep learning architectures"]);
    }

    #[test]
    fn test_format_wiki_markdown() {
        let report = WikiDistillationReport {
            topic: "Transformers".to_string(),
            article: WikiArticleDetail {
                title: "Transformer (deep learning)".to_string(),
                page_id: 63973680,
                url: "https://en.wikipedia.org/wiki/Transformer".to_string(),
                extract: "Transformers are neural network models based on self-attention.".to_string(),
                sections: vec![
                    WikiSection { index: "1".into(), line: "History".into(), level: 2, anchor: "History".into(), content: None },
                    WikiSection { index: "2".into(), line: "Architecture".into(), level: 2, anchor: "Architecture".into(), content: None },
                ],
                cross_references: vec!["Attention".into(), "BERT".into()],
                citations: vec!["https://arxiv.org/abs/1706.03762".into()],
                categories: vec!["Machine learning".into()],
            },
            related_results: vec![],
            distilled_summary: "Snippet overview".to_string(),
            key_takeaways: vec!["Transformers revolutionized NLP.".to_string()],
            grounded_citations: vec!["[1] https://arxiv.org/abs/1706.03762".to_string()],
        };

        let md = format_wiki_markdown(&report);
        assert!(md.contains("📖 **Wikipedia Knowledge Distillation"));
        assert!(md.contains("Transformer (deep learning)"));
        assert!(md.contains("Transformers are neural network models based on self-attention."));
        assert!(md.contains("Deep Section Retrieval"));
        assert!(md.contains("- **History** (`#History`)"));
        assert!(md.contains("[1] https://arxiv.org/abs/1706.03762"));
    }
}

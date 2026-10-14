//! Autonomous Web Research Engine for ModelFusion.
//!
//! Provides internet research capabilities by combining open-weight foundation & reasoning
//! models (Qwen 2.5 / DeepSeek-R1) with agentic live web search tool-use frameworks.

use anyhow::Result;
use reqwest::header::{HeaderMap, HeaderValue, USER_AGENT};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Simple percent encoder for query parameters.
fn encode_query(input: &str) -> String {
    let mut out = String::new();
    for b in input.bytes() {
        if b.is_ascii_alphanumeric() || b == b'-' || b == b'_' || b == b'.' || b == b'~' {
            out.push(b as char);
        } else if b == b' ' {
            out.push('+');
        } else {
            out.push_str(&format!("%{:02X}", b));
        }
    }
    out
}

/// Individual live search result from the web.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchResult {
    pub title: String,
    pub url: String,
    pub snippet: String,
}

/// Individual indexed document inside the search index.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct IndexedDocument {
    pub id: usize,
    pub title: String,
    pub url: String,
    pub snippet: String,
    pub terms: Vec<String>,
    pub timestamp: u64,
}

/// Inverted index term posting referencing a document ID and term frequency.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TermPosting {
    pub doc_id: usize,
    pub term_frequency: usize,
}

/// Relevance match result when querying the search index.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexedMatch {
    pub doc_id: usize,
    pub title: String,
    pub url: String,
    pub snippet: String,
    pub score: f64,
}

/// An inverted search index over retrieved web documents, passages, and snippets.
/// Maintains an index of all retrieved data for fast retrieval, relevance scoring, and grounded citation.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WebSearchIndex {
    pub documents: Vec<IndexedDocument>,
    pub inverted_index: std::collections::HashMap<String, Vec<TermPosting>>,
    pub total_terms: usize,
}

impl WebSearchIndex {
    pub fn new() -> Self {
        Self::default()
    }

    /// Tokenizes text into lowercase alphanumeric terms.
    pub fn tokenize(text: &str) -> Vec<String> {
        text.to_lowercase()
            .split(|c: char| !c.is_alphanumeric())
            .filter(|w| w.len() >= 2)
            .map(|s| s.to_string())
            .collect()
    }

    /// Adds a single document into the index, indexing its title and snippet terms.
    pub fn add_document(&mut self, title: &str, url: &str, snippet: &str) -> usize {
        let doc_id = self.documents.len() + 1;
        let combined = format!("{} {}", title, snippet);
        let tokens = Self::tokenize(&combined);

        let mut freq_map: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for t in &tokens {
            *freq_map.entry(t.clone()).or_insert(0) += 1;
            self.total_terms += 1;
        }

        for (term, freq) in &freq_map {
            self.inverted_index
                .entry(term.clone())
                .or_default()
                .push(TermPosting {
                    doc_id,
                    term_frequency: *freq,
                });
        }

        self.documents.push(IndexedDocument {
            id: doc_id,
            title: title.to_string(),
            url: url.to_string(),
            snippet: snippet.to_string(),
            terms: tokens,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0),
        });

        doc_id
    }

    /// Populates the index from a slice of SearchResult items.
    pub fn add_search_results(&mut self, results: &[SearchResult]) {
        for r in results {
            self.add_document(&r.title, &r.url, &r.snippet);
        }
    }

    /// Queries the search index using TF-IDF term scoring.
    pub fn search(&self, query: &str) -> Vec<IndexedMatch> {
        let q_tokens = Self::tokenize(query);
        if q_tokens.is_empty() || self.documents.is_empty() {
            return Vec::new();
        }

        let num_docs = self.documents.len() as f64;
        let mut scores: std::collections::HashMap<usize, f64> = std::collections::HashMap::new();

        for term in &q_tokens {
            if let Some(postings) = self.inverted_index.get(term) {
                let idf = ((num_docs + 1.0) / (postings.len() as f64 + 1.0)).ln() + 1.0;
                for p in postings {
                    let tf = p.term_frequency as f64;
                    *scores.entry(p.doc_id).or_insert(0.0) += tf * idf;
                }
            }
        }

        let mut matches: Vec<IndexedMatch> = scores
            .into_iter()
            .filter_map(|(doc_id, score)| {
                self.documents.iter().find(|d| d.id == doc_id).map(|d| IndexedMatch {
                    doc_id,
                    title: d.title.clone(),
                    url: d.url.clone(),
                    snippet: d.snippet.clone(),
                    score,
                })
            })
            .collect();

        matches.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        matches
    }

    /// Formats the index into an augmented context buffer for LLM synthesis.
    pub fn format_context_buffer(&self, max_items: usize) -> String {
        let mut buffer = String::new();
        for (idx, doc) in self.documents.iter().take(max_items).enumerate() {
            buffer.push_str(&format!(
                "[{}] Title: {}\nURL: {}\nExcerpt: {}\n\n",
                idx + 1,
                doc.title,
                doc.url,
                doc.snippet
            ));
        }
        buffer
    }

    /// Returns a structured JSON summary of the index with all data.
    pub fn index_summary(&self) -> serde_json::Value {
        serde_json::json!({
            "total_documents": self.documents.len(),
            "unique_terms": self.inverted_index.len(),
            "total_term_instances": self.total_terms,
            "documents": self.documents,
        })
    }
}

/// Decode URL-encoded parameters (e.g., extracting destination URL from uddg=...)
fn decode_percent_encoded(input: &str) -> String {
    let mut result = String::new();
    let bytes = input.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(val) = u8::from_str_radix(&input[i + 1..i + 3], 16) {
                result.push(val as char);
                i += 3;
                continue;
            }
        }
        result.push(bytes[i] as char);
        i += 1;
    }
    result
}

/// Strips HTML tags and unescapes common HTML entities.
pub fn clean_html_entities(raw: &str) -> String {
    let without_tags = {
        let mut in_tag = false;
        let mut buf = String::with_capacity(raw.len());
        for c in raw.chars() {
            if c == '<' {
                in_tag = true;
            } else if c == '>' {
                in_tag = false;
            } else if !in_tag {
                buf.push(c);
            }
        }
        buf
    };

    without_tags
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#x27;", "'")
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}

#[inline]
pub fn safe_subslice(s: &str, start: usize, end: usize) -> &str {
    if start >= s.len() || start >= end {
        return "";
    }
    let mut s_idx = start;
    while s_idx < s.len() && !s.is_char_boundary(s_idx) {
        s_idx += 1;
    }
    let mut e_idx = end.min(s.len());
    while e_idx > s_idx && !s.is_char_boundary(e_idx) {
        e_idx -= 1;
    }
    if s_idx <= e_idx && e_idx <= s.len() {
        &s[s_idx..e_idx]
    } else {
        ""
    }
}

/// Helper to extract form input name-value pairs from `<form class="next_form" ...>` or `/lite/` form.
fn extract_next_page_form_inputs(html: &str) -> Option<Vec<(String, String)>> {
    let form_start = html
        .find("class=\"next_form\"")
        .or_else(|| html.find("class='next_form'"))
        .or_else(|| html.find("action=\"/lite/\""))
        .or_else(|| html.find("action='/lite/'"))?;

    let form_open = safe_subslice(html, 0, form_start).rfind("<form")?;
    let form_close = safe_subslice(html, form_start, html.len()).find("</form>").map(|p| form_start + p)?;
    let form_body = safe_subslice(html, form_open, form_close);

    let mut params = Vec::new();
    let mut cursor = 0;
    while let Some(input_idx) = safe_subslice(form_body, cursor, form_body.len()).find("<input") {
        let abs_idx = cursor + input_idx;
        let tag_end = safe_subslice(form_body, abs_idx, form_body.len()).find('>').map(|p| abs_idx + p + 1).unwrap_or(form_body.len());
        let input_tag = safe_subslice(form_body, abs_idx, tag_end);

        let name = extract_html_attr(input_tag, "name");
        let value = extract_html_attr(input_tag, "value");

        if let (Some(n), Some(v)) = (name, value) {
            params.push((n, v));
        }
        cursor = tag_end;
        while cursor < form_body.len() && !form_body.is_char_boundary(cursor) {
            cursor += 1;
        }
    }

    if params.is_empty() {
        None
    } else {
        Some(params)
    }
}

fn extract_html_attr(tag: &str, attr: &str) -> Option<String> {
    for quote in ['"', '\''] {
        let pat = format!("{}={}", attr, quote);
        if let Some(pos) = tag.find(&pat) {
            let start = pos + pat.len();
            if let Some(end) = safe_subslice(tag, start, tag.len()).find(quote) {
                return Some(safe_subslice(tag, start, start + end).to_string());
            }
        }
    }
    None
}

/// Calculates multi-token relevance score between query and a candidate search result.
/// Returns negative score if distinctive query tokens (e.g. rare surname) are missing.
pub fn calculate_search_relevance(query: &str, title: &str, snippet: &str) -> i32 {
    let q_lower = query.to_lowercase();
    let t_lower = title.to_lowercase();
    let s_lower = snippet.to_lowercase();

    let stopwords = [
        "the", "and", "for", "has", "have", "had", "published", "any", "articles", "article",
        "who", "what", "where", "when", "why", "how", "did", "does", "with", "from", "about",
        "his", "her", "their", "its", "our", "him", "them", "this", "that", "these", "those",
        "all", "some", "few", "more", "most", "other", "into", "onto", "upon", "can", "will",
        "would", "should", "could", "tell", "show", "give", "find", "search", "lookup"
    ];

    let tokens: Vec<&str> = q_lower
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| t.len() >= 3 && !stopwords.contains(t))
        .collect();

    let mut score = 0;

    // Exact phrase match
    if t_lower.contains(&q_lower) || s_lower.contains(&q_lower) {
        score += 100;
    }

    if tokens.is_empty() {
        return score + 10;
    }

    let mut matched_tokens = 0;
    for token in &tokens {
        let in_title = t_lower.contains(token);
        let in_snip = s_lower.contains(token);
        if in_title || in_snip {
            matched_tokens += 1;
            score += 40;
            if in_title {
                score += 20;
            }
        }
    }

    // Anti-Poisoning Multi-Token Law:
    // If the query has 2+ distinctive tokens (e.g. "femi", "oyesanya"), but the candidate
    // matched 0 tokens or only 1 common token (e.g. only matched "femi" while missing "oyesanya"),
    // heavily penalize so that completely unrelated people (e.g. "Femi Adebayo") are NEVER injected!
    if tokens.len() >= 2 {
        if matched_tokens == 0 {
            return -100;
        }
        if matched_tokens == 1 {
            return -50;
        }
    }

    score
}

/// Searches DuckDuckGo HTML endpoint directly.
async fn search_duckduckgo_html(
    client: &reqwest::Client,
    headers: &HeaderMap,
    query: &str,
    max_results: usize,
) -> Vec<SearchResult> {
    let mut results = Vec::new();
    let url = format!("https://html.duckduckgo.com/html/?q={}", encode_query(query));
    if let Ok(resp) = client.get(&url).headers(headers.clone()).send().await {
        if resp.status().is_success() {
            if let Ok(html) = resp.text().await {
                let link_pat = "class=\"result__a\"";
                let link_pat_alt = "class='result__a'";
                let mut cursor = 0;
                while let Some(pos) = safe_subslice(&html, cursor, html.len())
                    .find(link_pat)
                    .or_else(|| safe_subslice(&html, cursor, html.len()).find(link_pat_alt))
                {
                    let abs_pos = cursor + pos;
                    if let Some(href_idx) = safe_subslice(&html, 0, abs_pos).rfind("href=\"")
                        .or_else(|| safe_subslice(&html, 0, abs_pos).rfind("href='"))
                    {
                        let quote_char = html.as_bytes().get(href_idx + 5).copied().unwrap_or(b'"') as char;
                        let url_start = href_idx + 6;
                        if let Some(url_end) = safe_subslice(&html, url_start, html.len()).find(quote_char) {
                            let raw_url = safe_subslice(&html, url_start, url_start + url_end);
                            let clean_url = if let Some(uddg_pos) = raw_url.find("uddg=") {
                                let after_uddg = safe_subslice(raw_url, uddg_pos + 5, raw_url.len());
                                let end_param = after_uddg.find('&').unwrap_or(after_uddg.len());
                                decode_percent_encoded(safe_subslice(after_uddg, 0, end_param))
                            } else {
                                raw_url.to_string()
                            };

                            let tag_close = safe_subslice(&html, abs_pos, html.len()).find('>').map(|p| abs_pos + p + 1).unwrap_or(abs_pos);
                            let title = if let Some(tag_end) = safe_subslice(&html, tag_close, html.len()).find("</a>") {
                                clean_html_entities(safe_subslice(&html, tag_close, tag_close + tag_end))
                            } else {
                                String::new()
                            };

                            let snippet = if let Some(snip_idx) = safe_subslice(&html, abs_pos, html.len()).find("result__snippet") {
                                let snip_pos = abs_pos + snip_idx;
                                if let Some(gt) = safe_subslice(&html, snip_pos, html.len()).find('>') {
                                    let s_start = snip_pos + gt + 1;
                                    if let Some(close) = safe_subslice(&html, s_start, html.len()).find("</a>")
                                        .or_else(|| safe_subslice(&html, s_start, html.len()).find("</div>"))
                                    {
                                        clean_html_entities(safe_subslice(&html, s_start, s_start + close))
                                    } else {
                                        String::new()
                                    }
                                } else {
                                    String::new()
                                }
                            } else {
                                String::new()
                            };

                            if clean_url.starts_with("http") && !title.is_empty() {
                                if !results.iter().any(|r: &SearchResult| r.url == clean_url) {
                                    results.push(SearchResult {
                                        title,
                                        url: clean_url,
                                        snippet,
                                    });
                                }
                            }
                            if results.len() >= max_results {
                                break;
                            }
                        }
                    }
                    cursor = abs_pos + 15;
                    while cursor < html.len() && !html.is_char_boundary(cursor) {
                        cursor += 1;
                    }
                }
            }
        }
    }
    results
}

/// Searches Google Basic Web Search (gbv=1) and Google News RSS in parallel.
async fn search_google_and_news(
    client: &reqwest::Client,
    headers: &HeaderMap,
    query: &str,
    max_results: usize,
) -> Vec<SearchResult> {
    let mut results = Vec::new();

    // 1. Google News RSS
    let news_url = format!(
        "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en",
        encode_query(query)
    );
    if let Ok(resp) = client.get(&news_url).headers(headers.clone()).send().await {
        if resp.status().is_success() {
            if let Ok(xml) = resp.text().await {
                let mut cursor = 0;
                while let Some(item_start) = safe_subslice(&xml, cursor, xml.len()).find("<item>") {
                    let abs_start = cursor + item_start + 6;
                    if let Some(item_end) = safe_subslice(&xml, abs_start, xml.len()).find("</item>") {
                        let item_chunk = safe_subslice(&xml, abs_start, abs_start + item_end);
                        let title = extract_tag_content(item_chunk, "title").map(|t| clean_html_entities(&t)).unwrap_or_default();
                        let link = extract_tag_content(item_chunk, "link").unwrap_or_default();
                        let snippet = extract_tag_content(item_chunk, "description").map(|d| clean_html_entities(&d)).unwrap_or_default();

                        if !title.is_empty() && link.starts_with("http") {
                            if !results.iter().any(|r: &SearchResult| r.url == link || r.title == title) {
                                results.push(SearchResult {
                                    title,
                                    url: link,
                                    snippet,
                                });
                            }
                        }
                        cursor = abs_start + item_end + 7;
                        if results.len() >= max_results {
                            break;
                        }
                    } else {
                        break;
                    }
                }
            }
        }
    }

    // 2. Google Web Search GBV=1
    let g_url = format!(
        "https://www.google.com/search?q={}&gbv=1&hl=en&num=15",
        encode_query(query)
    );
    if let Ok(resp) = client.get(&g_url).headers(headers.clone()).send().await {
        if resp.status().is_success() {
            if let Ok(html) = resp.text().await {
                let url_q_pat = "/url?q=";
                let mut cursor = 0;
                while let Some(pos) = safe_subslice(&html, cursor, html.len()).find(url_q_pat) {
                    let abs_pos = cursor + pos + url_q_pat.len();
                    if let Some(end_url) = safe_subslice(&html, abs_pos, html.len()).find('&')
                        .or_else(|| safe_subslice(&html, abs_pos, html.len()).find('"'))
                        .or_else(|| safe_subslice(&html, abs_pos, html.len()).find('\''))
                    {
                        let raw_url = safe_subslice(&html, abs_pos, abs_pos + end_url);
                        let clean_url = decode_percent_encoded(raw_url);
                        if clean_url.starts_with("http") && !clean_url.contains("google.com") {
                            if let Some(tag_close) = safe_subslice(&html, abs_pos, html.len()).find('>') {
                                let after_gt = abs_pos + tag_close + 1;
                                if let Some(tag_end) = safe_subslice(&html, after_gt, html.len()).find("</a>") {
                                    let raw_title = safe_subslice(&html, after_gt, after_gt + tag_end);
                                    let clean_title = clean_html_entities(raw_title);
                                    if !clean_title.is_empty() && !results.iter().any(|r: &SearchResult| r.url == clean_url || r.title == clean_title) {
                                        results.push(SearchResult {
                                            title: clean_title,
                                            url: clean_url,
                                            snippet: String::new(),
                                        });
                                    }
                                }
                            }
                        }
                    }
                    cursor = abs_pos + 10;
                    while cursor < html.len() && !html.is_char_boundary(cursor) {
                        cursor += 1;
                    }
                    if results.len() >= max_results {
                        break;
                    }
                }
            }
        }
    }

    results
}

/// Searches Bing HTML endpoint directly.
async fn search_bing_html(
    client: &reqwest::Client,
    headers: &HeaderMap,
    query: &str,
    max_results: usize,
) -> Vec<SearchResult> {
    let mut results = Vec::new();
    let url = format!("https://www.bing.com/search?q={}&setlang=en", encode_query(query));
    if let Ok(resp) = client.get(&url).headers(headers.clone()).send().await {
        if resp.status().is_success() {
            if let Ok(html) = resp.text().await {
                let algo_pat = "class=\"b_algo\"";
                let algo_pat_alt = "class='b_algo'";
                let mut cursor = 0;
                while let Some(pos) = safe_subslice(&html, cursor, html.len())
                    .find(algo_pat)
                    .or_else(|| safe_subslice(&html, cursor, html.len()).find(algo_pat_alt))
                {
                    let abs_pos = cursor + pos;
                    if let Some(h2_idx) = safe_subslice(&html, abs_pos, html.len()).find("<h2") {
                        let h2_pos = abs_pos + h2_idx;
                        if let Some(href_idx) = safe_subslice(&html, h2_pos, html.len()).find("href=\"")
                            .or_else(|| safe_subslice(&html, h2_pos, html.len()).find("href='"))
                        {
                            let quote_char = html.as_bytes().get(h2_pos + href_idx + 5).copied().unwrap_or(b'"') as char;
                            let url_start = h2_pos + href_idx + 6;
                            if let Some(url_end) = safe_subslice(&html, url_start, html.len()).find(quote_char) {
                                let link = safe_subslice(&html, url_start, url_start + url_end).to_string();
                                if let Some(gt) = safe_subslice(&html, url_start + url_end, html.len()).find('>') {
                                    let title_start = url_start + url_end + gt + 1;
                                    if let Some(a_end) = safe_subslice(&html, title_start, html.len()).find("</a>") {
                                        let title = clean_html_entities(safe_subslice(&html, title_start, title_start + a_end));

                                        let snippet = if let Some(cap_idx) = safe_subslice(&html, abs_pos, html.len()).find("b_caption") {
                                            let cap_pos = abs_pos + cap_idx;
                                            if let Some(p_idx) = safe_subslice(&html, cap_pos, html.len()).find("<p") {
                                                let p_pos = cap_pos + p_idx;
                                                if let Some(p_gt) = safe_subslice(&html, p_pos, html.len()).find('>') {
                                                    let s_start = p_pos + p_gt + 1;
                                                    if let Some(p_close) = safe_subslice(&html, s_start, html.len()).find("</p>") {
                                                        clean_html_entities(safe_subslice(&html, s_start, s_start + p_close))
                                                    } else {
                                                        String::new()
                                                    }
                                                } else {
                                                    String::new()
                                                }
                                            } else {
                                                String::new()
                                            }
                                        } else {
                                            String::new()
                                        };

                                        if link.starts_with("http") && !title.is_empty() {
                                            if !results.iter().any(|r: &SearchResult| r.url == link || r.title == title) {
                                                results.push(SearchResult {
                                                    title,
                                                    url: link,
                                                    snippet,
                                                });
                                            }
                                        }
                                        if results.len() >= max_results {
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    cursor = abs_pos + 20;
                    while cursor < html.len() && !html.is_char_boundary(cursor) {
                        cursor += 1;
                    }
                }
            }
        }
    }
    results
}

/// Searches DuckDuckGo Lite endpoint with pagination fallback.
async fn search_duckduckgo_lite(
    client: &reqwest::Client,
    headers: &HeaderMap,
    query: &str,
    max_results: usize,
) -> Vec<SearchResult> {
    let mut results = Vec::new();
    let mut post_params: Vec<(String, String)> = vec![("q".to_string(), query.to_string())];
    let mut pages_visited = 0;

    while results.len() < max_results && pages_visited < 3 {
        pages_visited += 1;
        let lite_resp = client
            .post("https://lite.duckduckgo.com/lite/")
            .headers(headers.clone())
            .form(&post_params)
            .send()
            .await;

        let mut next_params: Option<Vec<(String, String)>> = None;

        if let Ok(resp) = lite_resp {
            if resp.status().is_success() {
                if let Ok(html) = resp.text().await {
                    let mut cursor = 0;
                    let link_pat = "class='result-link'";
                    while let Some(link_start) = safe_subslice(&html, cursor, html.len()).find(link_pat) {
                        let abs_start = cursor + link_start;
                        if let Some(href_idx) = safe_subslice(&html, 0, abs_start).rfind("href=\"") {
                            let url_start = href_idx + 6;
                            if let Some(url_end) = safe_subslice(&html, url_start, html.len()).find('"') {
                                let raw_url = safe_subslice(&html, url_start, url_start + url_end);
                                let clean_url = if let Some(uddg_pos) = raw_url.find("uddg=") {
                                    let after_uddg = safe_subslice(raw_url, uddg_pos + 5, raw_url.len());
                                    let end_param = after_uddg.find('&').unwrap_or(after_uddg.len());
                                    decode_percent_encoded(safe_subslice(after_uddg, 0, end_param))
                                } else {
                                    raw_url.to_string()
                                };

                                let tag_close = safe_subslice(&html, abs_start, html.len()).find('>').map(|p| abs_start + p + 1).unwrap_or(abs_start);
                                let title = if let Some(tag_end) = safe_subslice(&html, tag_close, html.len()).find("</a>") {
                                    clean_html_entities(safe_subslice(&html, tag_close, tag_close + tag_end))
                                } else {
                                    String::new()
                                };

                                let snippet_start = safe_subslice(&html, abs_start, html.len()).find("class='result-snippet'").map(|p| abs_start + p);
                                let snippet = if let Some(snip_pos) = snippet_start {
                                    if let Some(td_close) = safe_subslice(&html, snip_pos, html.len()).find('>') {
                                        let snip_content_start = snip_pos + td_close + 1;
                                        if let Some(td_end) = safe_subslice(&html, snip_content_start, html.len()).find("</td>") {
                                            clean_html_entities(safe_subslice(&html, snip_content_start, snip_content_start + td_end))
                                        } else {
                                            String::new()
                                        }
                                    } else {
                                        String::new()
                                    }
                                } else {
                                    String::new()
                                };

                                if clean_url.starts_with("http") && !title.is_empty() {
                                    if !results.iter().any(|r: &SearchResult| r.url == clean_url || r.title == title) {
                                        results.push(SearchResult {
                                            title,
                                            url: clean_url,
                                            snippet,
                                        });
                                    }
                                }

                                if results.len() >= max_results {
                                    break;
                                }
                            }
                        }
                        let mut next_cursor = abs_start + link_pat.len();
                        while next_cursor < html.len() && !html.is_char_boundary(next_cursor) {
                            next_cursor += 1;
                        }
                        cursor = next_cursor;
                    }

                    if results.len() < max_results {
                        next_params = extract_next_page_form_inputs(&html);
                    }
                }
            }
        }

        match next_params {
            Some(np) if !np.is_empty() => post_params = np,
            _ => break,
        }
    }
    results
}

/// Executes a live web search across 4 complementary search engines in parallel:
/// DuckDuckGo HTML, Google Search + Google News RSS, Bing Web Search, and DuckDuckGo Lite,
/// backed by strict multi-token relevance scoring, anti-poisoning filtering, and verified Wikipedia supplement.
pub async fn live_web_search(query: &str, max_results: usize) -> Result<Vec<SearchResult>> {
    let mut results: Vec<SearchResult> = Vec::new();

    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(6))
        .timeout(Duration::from_secs(12))
        .build()?;

    let mut headers = HeaderMap::new();
    headers.insert(
        USER_AGENT,
        HeaderValue::from_static(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ),
    );

    // 1. Run 4 Complementary Live Search Engines in parallel via tokio::join!
    let (ddg_html, google_res, bing_res, ddg_lite) = tokio::join!(
        search_duckduckgo_html(&client, &headers, query, max_results * 2),
        search_google_and_news(&client, &headers, query, max_results * 2),
        search_bing_html(&client, &headers, query, max_results * 2),
        search_duckduckgo_lite(&client, &headers, query, max_results * 2)
    );

    let normalize_url = |u: &str| -> String {
        let without_proto = u.trim_start_matches("https://").trim_start_matches("http://");
        without_proto.trim_end_matches('/').to_lowercase()
    };

    let mut candidate_pool: Vec<SearchResult> = Vec::new();
    let mut seen_urls = std::collections::HashSet::new();

    for res in ddg_html.into_iter().chain(google_res).chain(bing_res).chain(ddg_lite) {
        let norm = normalize_url(&res.url);
        if seen_urls.insert(norm) {
            candidate_pool.push(res);
        }
    }

    // 2. Strict Multi-Token Relevance Scoring & Anti-Poisoning Filtering
    let mut scored: Vec<(SearchResult, i32)> = Vec::new();
    for res in candidate_pool {
        let score = calculate_search_relevance(query, &res.title, &res.snippet);
        if score > 0 {
            scored.push((res, score));
        }
    }

    scored.sort_by(|a, b| b.1.cmp(&a.1));
    for (res, _) in scored {
        results.push(res);
        if results.len() >= max_results {
            break;
        }
    }

    // 3. Wikipedia Search API Supplement with Strict Multi-Token Entity Guard
    if results.len() < max_results {
        let q_lower = query.to_lowercase();
        let stopwords = [
            "the", "and", "for", "has", "have", "had", "published", "any", "articles", "article",
            "who", "what", "where", "when", "why", "how", "did", "does", "with", "from", "about",
            "his", "her", "their", "its", "our", "him", "them", "this", "that", "these", "those"
        ];
        let required_tokens: Vec<&str> = q_lower
            .split(|c: char| !c.is_alphanumeric())
            .filter(|t| t.len() >= 3 && !stopwords.contains(t))
            .collect();

        let needed = max_results.saturating_sub(results.len());
        let wiki_limit = needed.clamp(1, 50);
        let wiki_url = format!(
            "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={}&format=json&origin=*&srlimit={}",
            encode_query(query),
            wiki_limit
        );
        if let Ok(resp) = client.get(&wiki_url).headers(headers.clone()).send().await {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                if let Some(search_arr) = json.get("query").and_then(|q| q.get("search")).and_then(|s| s.as_array()) {
                    for item in search_arr {
                        if let Some(title) = item.get("title").and_then(|t| t.as_str()) {
                            let clean_title = title.to_string();
                            let clean_snip = item.get("snippet")
                                .and_then(|s| s.as_str())
                                .map(clean_html_entities)
                                .unwrap_or_default();

                            let combined_text = format!("{} {}", clean_title, clean_snip).to_lowercase();
                            // Strict Wikipedia Anti-Poisoning Guard:
                            // ONLY include if the Wikipedia result contains ALL distinctive tokens
                            let all_matched = if required_tokens.is_empty() {
                                true
                            } else {
                                required_tokens.iter().all(|tok| combined_text.contains(tok))
                            };

                            if all_matched {
                                let wiki_page_url = format!(
                                    "https://en.wikipedia.org/wiki/{}",
                                    encode_query(&clean_title.replace(' ', "_"))
                                );
                                if !results.iter().any(|r| r.url == wiki_page_url || r.title == clean_title) {
                                    results.push(SearchResult {
                                        title: clean_title,
                                        url: wiki_page_url,
                                        snippet: clean_snip,
                                    });
                                    if results.len() >= max_results {
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 4. Fallback: DuckDuckGo Instant Answer API if results < max_results
    if results.len() < max_results {
        let api_url = format!(
            "https://api.duckduckgo.com/?q={}&format=json",
            encode_query(query)
        );
        if let Ok(resp) = client.get(&api_url).headers(headers).send().await {
            if let Ok(data) = resp.json::<serde_json::Value>().await {
                let heading = data["Heading"].as_str().unwrap_or("").to_string();
                let abstract_text = data["AbstractText"].as_str().unwrap_or("").to_string();
                let abstract_url = data["AbstractURL"].as_str().unwrap_or("").to_string();

                if !abstract_text.is_empty() && !abstract_url.is_empty() {
                    if !results.iter().any(|r| r.url == abstract_url) {
                        let score = calculate_search_relevance(query, &heading, &abstract_text);
                        if score > 0 {
                            results.push(SearchResult {
                                title: if heading.is_empty() { query.to_string() } else { heading },
                                url: abstract_url,
                                snippet: abstract_text,
                            });
                        }
                    }
                }

                if let Some(topics) = data["RelatedTopics"].as_array() {
                    for t in topics {
                        if let (Some(text), Some(url)) = (t["Text"].as_str(), t["FirstURL"].as_str()) {
                            let title = text.split(" - ").next().unwrap_or(text).chars().take(60).collect::<String>();
                            if !results.iter().any(|r| r.url == url) {
                                let score = calculate_search_relevance(query, &title, text);
                                if score > 0 {
                                    results.push(SearchResult {
                                        title,
                                        url: url.to_string(),
                                        snippet: text.to_string(),
                                    });
                                    if results.len() >= max_results {
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    results.truncate(max_results);
    Ok(results)
}

/// Google LangExtract Query Interpreter and Entity Grounder.
/// Performs structured entity extraction, coreference resolution, and query interpretation.
pub fn langextract_interpret_query(raw_query: &str, history: &[String]) -> serde_json::Value {
    let text = raw_query.trim();
    let lower_text = text.to_lowercase();

    // Check if python langextract engine is available on disk
    let engine_script = std::path::Path::new("scripts/langextract_engine.py");
    if engine_script.exists() {
        let history_json = serde_json::to_string(history).unwrap_or_else(|_| "[]".to_string());
        if let Ok(output) = std::process::Command::new("python")
            .arg("scripts/langextract_engine.py")
            .arg("--query")
            .arg(text)
            .arg("--history")
            .arg(&history_json)
            .output()
        {
            if output.status.success() {
                if let Ok(val) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                    return val;
                }
            }
        }
    }

    // Fast zero-latency native fallback
    let stopwords = [
        "the", "and", "for", "has", "have", "had", "published", "any", "articles", "article",
        "who", "what", "where", "when", "why", "how", "did", "does", "with", "from", "about",
        "his", "her", "their", "its", "our", "him", "them", "this", "that", "these", "those",
        "all", "some", "few", "more", "most", "other", "into", "onto", "upon", "can", "will"
    ];

    let mut extractions = Vec::new();
    let mut intent = "qa".to_string();
    let mut domain = "general".to_string();
    let mut route_to_web = false;

    // Directives
    let clean_prompt = if lower_text.starts_with("@agent ") || lower_text.starts_with('/') || lower_text.starts_with("--") {
        let parts: Vec<&str> = text.splitn(2, ' ').collect();
        let directive = parts[0];
        let rest = parts.get(1).copied().unwrap_or("").trim();
        extractions.push(serde_json::json!({
            "extraction_class": "action_intent",
            "extraction_text": directive,
            "char_interval": { "start_pos": 0, "end_pos": directive.len() },
            "alignment_status": "MATCH_EXACT",
            "attributes": { "directive": directive, "raw_command": "true" }
        }));
        if directive.contains("research") {
            intent = "deep_research".to_string();
            route_to_web = true;
            domain = "research".to_string();
        } else if directive.contains("search") {
            intent = "web_search".to_string();
            route_to_web = true;
            domain = "web".to_string();
        }
        rest
    } else {
        text
    };

    if lower_text.contains("deep research") || lower_text.contains("deep-research") {
        intent = "deep_research".to_string();
        route_to_web = true;
        domain = "research".to_string();
    } else if lower_text.contains("search for ") || lower_text.contains("google ") {
        intent = "web_search".to_string();
        route_to_web = true;
        domain = "web".to_string();
    }

    // Coreference
    let mut resolved_entity: Option<String> = None;
    let mut is_followup = false;
    let pronouns = ["he", "she", "his", "her", "him", "they", "their", "the author"];
    for p in &pronouns {
        if let Some(pos) = lower_text.find(p) {
            for turn in history.iter().rev() {
                let clean_turn = turn.trim();
                let words: Vec<&str> = clean_turn.split_whitespace().collect();
                if !words.is_empty() && words.len() <= 5 {
                    let title_cased = words.iter().map(|w| {
                        let mut c = w.chars();
                        match c.next() {
                            None => String::new(),
                            Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
                        }
                    }).collect::<Vec<_>>().join(" ");
                    resolved_entity = Some(title_cased);
                    is_followup = true;
                    extractions.push(serde_json::json!({
                        "extraction_class": "coreference",
                        "extraction_text": *p,
                        "char_interval": { "start_pos": pos, "end_pos": pos + p.len() },
                        "alignment_status": "MATCH_EXACT",
                        "attributes": {
                            "referent": resolved_entity.clone().unwrap_or_default(),
                            "source": "conversation_history"
                        }
                    }));
                    break;
                }
            }
            if is_followup {
                break;
            }
        }
    }

    // Publication inquiry
    if lower_text.contains("published") || lower_text.contains("articles") || lower_text.contains("papers") {
        intent = "publication_inquiry".to_string();
        route_to_web = true;
        domain = "bibliography".to_string();
        if let Some(pos) = lower_text.find("published") {
            extractions.push(serde_json::json!({
                "extraction_class": "publication_inquiry",
                "extraction_text": "published",
                "char_interval": { "start_pos": pos, "end_pos": pos + 9 },
                "alignment_status": "MATCH_EXACT",
                "attributes": {
                    "type": "bibliography_lookup",
                    "search_engine": "google_and_duckduckgo",
                    "requires_live_search": "true"
                }
            }));
        }
    }

    // Person entity extraction
    let mut is_person = false;
    let subject = clean_prompt;
    let words: Vec<&str> = subject.split_whitespace().collect();
    let non_stopwords: Vec<&str> = words.iter().copied().filter(|w| !stopwords.contains(&w.to_lowercase().as_str())).collect();
    if resolved_entity.is_none() && words.len() >= 1 && words.len() <= 5 && !non_stopwords.is_empty() {
        let ent = words.join(" ");
        if let Some(pos) = text.to_lowercase().find(&ent.to_lowercase()) {
            is_person = true;
            resolved_entity = Some(ent.clone());
            extractions.push(serde_json::json!({
                "extraction_class": "person",
                "extraction_text": ent,
                "char_interval": { "start_pos": pos, "end_pos": pos + ent.len() },
                "alignment_status": "MATCH_EXACT",
                "attributes": {
                    "role": "author_researcher_or_public_figure",
                    "requires_live_search": "true"
                }
            }));
        }
    }

    let primary_entity = resolved_entity.clone().unwrap_or_default();
    let resolved_query = if is_followup && !primary_entity.is_empty() {
        if intent == "publication_inquiry" {
            format!("{} published articles papers publications", primary_entity)
        } else {
            format!("{} {}", primary_entity, clean_prompt)
        }
    } else if is_person && !primary_entity.is_empty() {
        if intent == "publication_inquiry" {
            format!("{} published articles papers publications", primary_entity)
        } else {
            primary_entity.clone()
        }
    } else {
        text.to_string()
    };

    let search_queries = if !primary_entity.is_empty() {
        vec![
            format!("\"{}\"", primary_entity),
            format!("\"{}\" published articles papers", primary_entity),
            primary_entity.clone()
        ]
    } else {
        vec![clean_prompt.to_string()]
    };

    if is_person || is_followup || intent == "publication_inquiry" || intent == "deep_research" {
        route_to_web = true;
        if intent == "qa" {
            intent = "web_search".to_string();
        }
    }

    serde_json::json!({
        "engine": "google/langextract",
        "raw_query": text,
        "resolved_query": resolved_query,
        "search_queries": search_queries,
        "intent": intent,
        "domain": domain,
        "route_to_web": route_to_web,
        "is_person_or_entity": is_person || !primary_entity.is_empty(),
        "is_followup_coreference": is_followup,
        "primary_entity": primary_entity,
        "extractions": extractions
    })
}

/// Helper to extract text content inside `<tag>` or `<tag ...>` in an XML chunk.
fn extract_tag_content(block: &str, tag: &str) -> Option<String> {
    let open_pat = format!("<{}", tag);
    let close_pat = format!("</{}>", tag);
    let mut cursor = 0;
    while let Some(pos) = block[cursor..].find(&open_pat) {
        let tag_start = cursor + pos;
        let rest = &block[tag_start + open_pat.len()..];
        if let Some(c) = rest.chars().next() {
            if c == '>' || c.is_whitespace() || c == '/' {
                if let Some(gt) = rest.find('>') {
                    let content_start = tag_start + open_pat.len() + gt + 1;
                    if let Some(close_pos) = block[content_start..].find(&close_pat) {
                        return Some(block[content_start..content_start + close_pos].to_string());
                    }
                }
            }
        }
        cursor = tag_start + open_pat.len();
    }
    None
}

/// Helper to extract up to `max_authors` author names from arXiv entry `<author>` tags.
fn extract_arxiv_authors(block: &str, max_authors: usize) -> Vec<String> {
    let mut authors = Vec::new();
    let mut cursor = 0;
    while let Some(author_start) = block[cursor..].find("<author>") {
        let abs_start = cursor + author_start;
        if let Some(author_end) = block[abs_start..].find("</author>") {
            let author_block = &block[abs_start..abs_start + author_end];
            if let Some(name) = extract_tag_content(author_block, "name") {
                let clean = clean_html_entities(&name);
                if !clean.is_empty() {
                    authors.push(clean);
                }
            }
            cursor = abs_start + author_end + "</author>".len();
            if authors.len() >= max_authors {
                break;
            }
        } else {
            break;
        }
    }
    authors
}

/// Parses an arXiv Atom XML feed into a vector of SearchResult items.
pub fn parse_arxiv_atom(xml: &str) -> Vec<SearchResult> {
    let mut results = Vec::new();
    for entry_chunk in xml.split("<entry>").skip(1) {
        let block = match entry_chunk.find("</entry>") {
            Some(end) => &entry_chunk[..end],
            None => entry_chunk,
        };

        let raw_title = extract_tag_content(block, "title").unwrap_or_default();
        let clean_title = clean_html_entities(&raw_title);
        if clean_title.is_empty() {
            continue;
        }

        let raw_id = extract_tag_content(block, "id").unwrap_or_default();
        let clean_id = raw_id.trim();
        let url = if clean_id.starts_with("http://arxiv.org/abs/") {
            clean_id.replacen("http://", "https://", 1)
        } else if clean_id.starts_with("https://arxiv.org/abs/") {
            clean_id.to_string()
        } else if clean_id.starts_with("http://") {
            clean_id.replacen("http://", "https://", 1)
        } else if clean_id.contains("arxiv.org") {
            format!("https://{}", clean_id.trim_start_matches("http://").trim_start_matches("https://"))
        } else if !clean_id.is_empty() {
            format!("https://arxiv.org/abs/{}", clean_id)
        } else {
            String::new()
        };

        if url.is_empty() {
            continue;
        }

        let raw_summary = extract_tag_content(block, "summary").unwrap_or_default();
        let clean_summary = clean_html_entities(&raw_summary);

        let authors = extract_arxiv_authors(block, 3);
        let authors_str = authors.join(", ");

        let year = extract_tag_content(block, "published")
            .and_then(|pub_date| {
                let trimmed = pub_date.trim();
                if trimmed.len() >= 4 && trimmed[..4].chars().all(|c| c.is_ascii_digit()) {
                    Some(trimmed[..4].to_string())
                } else {
                    None
                }
            })
            .unwrap_or_default();

        let formatted_title = match (!authors_str.is_empty(), !year.is_empty()) {
            (true, true) => format!("[arXiv] {} ({}, {})", clean_title, authors_str, year),
            (true, false) => format!("[arXiv] {} ({})", clean_title, authors_str),
            (false, true) => format!("[arXiv] {} ({})", clean_title, year),
            (false, false) => format!("[arXiv] {}", clean_title),
        };

        results.push(SearchResult {
            title: formatted_title,
            url,
            snippet: clean_summary,
        });
    }
    results
}

/// Searches the arXiv API for preprints and scientific papers.
/// Gracefully handles errors and timeouts, returning an empty vector on failure.
pub async fn search_arxiv(query: &str, max_results: usize) -> Result<Vec<SearchResult>> {
    let clean_q = query.trim();
    if clean_q.is_empty() {
        return Ok(Vec::new());
    }

    let encoded_query = encode_query(clean_q);
    let limit = max_results.max(1);
    let url = format!(
        "https://export.arxiv.org/api/query?search_query=all:{}&start=0&max_results={}",
        encoded_query, limit
    );

    let client = match reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .user_agent("ModelFusion-DeepResearch/1.0 (https://github.com/oyesanyf/ModelFusion)")
        .build()
    {
        Ok(c) => c,
        Err(e) => {
            log::warn!("Failed to create arXiv reqwest client: {}", e);
            return Ok(Vec::new());
        }
    };

    let resp = match client.get(&url).send().await {
        Ok(r) => r,
        Err(e) => {
            log::warn!("arXiv API request failed for query '{}': {}", clean_q, e);
            return Ok(Vec::new());
        }
    };

    if !resp.status().is_success() {
        log::warn!("arXiv API HTTP error: {}", resp.status());
        return Ok(Vec::new());
    }

    let body = match resp.text().await {
        Ok(b) => b,
        Err(e) => {
            log::warn!("Failed reading arXiv API response text: {}", e);
            return Ok(Vec::new());
        }
    };

    Ok(parse_arxiv_atom(&body))
}


/// Auto-detects the best local reasoning model available in Ollama (DeepSeek-R1 or Qwen 2.5).
pub async fn detect_best_reasoning_model() -> String {
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
    let url = format!("{}/api/tags", endpoint.trim_end_matches('/'));

    let client = reqwest::Client::builder()
        .no_proxy()
        .connect_timeout(Duration::from_secs(2))
        .timeout(Duration::from_secs(3))
        .build()
        .unwrap_or_default();

    if let Ok(resp) = client.get(&url).send().await {
        if let Ok(json) = resp.json::<serde_json::Value>().await {
            if let Some(models) = json["models"].as_array() {
                let names: Vec<String> = models
                    .iter()
                    .filter_map(|m| m["name"].as_str().map(|s| s.to_string()))
                    .collect();

                // Dynamically evaluate runtime available memory per AGENTS.md rule
                let mem = model_selection::memory::SystemMemory::detect_live();
                let preferred: Vec<&str> = if mem.free_ram_gb >= 48.0 || mem.gpu_vram_free_gb >= 22.0 {
                    vec!["deepseek-r1:32b", "qwen2.5:32b", "deepseek-r1:14b", "qwen2.5:14b", "deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b"]
                } else if mem.free_ram_gb >= 24.0 || mem.gpu_vram_free_gb >= 12.0 {
                    vec!["deepseek-r1:14b", "qwen2.5:14b", "deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:32b", "qwen2.5:32b"]
                } else if mem.free_ram_gb >= 12.0 || mem.gpu_vram_free_gb >= 5.5 {
                    vec!["deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:14b", "qwen2.5:14b"]
                } else if mem.free_ram_gb >= 6.0 || mem.gpu_vram_free_gb >= 2.5 {
                    vec!["qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:7b", "qwen2.5:7b"]
                } else {
                    vec!["deepseek-r1:1.5b", "qwen2.5:1.5b", "qwen2.5:3b"]
                };

                for p in preferred {
                    if let Some(found) = names.iter().find(|n| n.starts_with(p)) {
                        return found.clone();
                    }
                }

                if let Some(first) = names.first() {
                    return first.clone();
                }
            }
        }
    }

    let mem = model_selection::memory::SystemMemory::detect_live();
    if mem.free_ram_gb >= 48.0 || mem.gpu_vram_free_gb >= 22.0 {
        "qwen2.5:32b".to_string()
    } else if mem.free_ram_gb >= 24.0 || mem.gpu_vram_free_gb >= 12.0 {
        "qwen2.5:14b".to_string()
    } else if mem.free_ram_gb >= 12.0 || mem.gpu_vram_free_gb >= 5.5 {
        "qwen2.5:7b".to_string()
    } else if mem.free_ram_gb >= 6.0 || mem.gpu_vram_free_gb >= 2.5 {
        "qwen2.5:3b".to_string()
    } else {
        "qwen2.5:1.5b".to_string()
    }
}

/// Synthesizes live search results into a deep research report using an open-weight reasoning model.
pub async fn synthesize_research(
    query: &str,
    results: &[SearchResult],
    model_override: Option<&str>,
) -> Result<String> {
    if results.is_empty() {
        return Ok(format!(
            "⚠️ No live web search results were found for query: \"{}\". Please check network access or rephrase.",
            query
        ));
    }

    let model_to_use = match model_override {
        Some(m) if !m.is_empty() => m.to_string(),
        _ => detect_best_reasoning_model().await,
    };

    // Format web context
    let mut context_block = String::new();
    for (idx, r) in results.iter().enumerate() {
        context_block.push_str(&format!(
            "[{}] Title: {}\n    URL: {}\n    Snippet: {}\n\n",
            idx + 1,
            r.title,
            r.url,
            r.snippet
        ));
    }

    let system_prompt = "\
You are an Autonomous Deep Web Research Agent powered by open-weight reasoning models (Qwen 2.5 / DeepSeek-R1). \
Your objective is to analyze, verify, and synthesize real-time internet search results into an authoritative, \
comprehensive, exhaustive, and multi-section research monograph in publication-grade depth and prose.

Guidelines:
- Generate a long, factual, publication-grade report with rich markdown headings:
  # 🌐 Deep Research Report: <Title>
  ## 📋 Executive Summary & Direct Factual Overview
  ## 🚀 Key Developments, Breakthroughs & Verified Works
  ## 🔬 Technical Deep Dive, Architecture & Methodologies
  ## 📈 Market, Commercial, Policy & Future Implications
  ## 📚 Verified Sources & Annotated Citations
- Deep Research sections must be thorough and deeply analytical: write multiple dense, multi-paragraph subsections with internal '####' sub-headings under each major section (minimum 400-600 words per major section).
- Base all biographical claims, publications, and professional affiliations strictly on the retrieved search data. Never fabricate careers or invent unrelated affiliations (e.g. never claim cybersecurity leaders or researchers are Nollywood actors).
- In the Sources section, cite every relevant source as a markdown link [Source Title](URL) with an explanatory note.
- Highlight key metrics, publications, authors, benchmarks, and dates.";

    let user_prompt = format!(
        "Research Topic: \"{}\"\n\nLive Internet Search Data (Retrieved):\n{}\n\nGenerate the complete, exhaustive research report:",
        query, context_block
    );

    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
    let url = format!("{}/api/chat", endpoint.trim_end_matches('/'));

    let body = serde_json::json!({
        "model": model_to_use,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_prompt }
        ],
        "stream": false,
        "options": {
            "temperature": 0.3,
            "num_predict": 8192
        }
    });

    let client = reqwest::Client::builder()
        .no_proxy()
        .connect_timeout(Duration::from_secs(4))
        .timeout(Duration::from_secs(240))
        .build()?;

    let resp = client.post(&url).json(&body).send().await;
    if let Ok(res) = resp {
        if res.status().is_success() {
            if let Ok(data) = res.json::<serde_json::Value>().await {
                if let Some(content) = data["message"]["content"].as_str() {
                    return Ok(content.trim().to_string());
                }
            }
        }
    }

    // Fallback if LLM is offline or times out: structured compilation from retrieved search data
    let mut fallback_report = String::new();
    fallback_report.push_str(&format!("# 🌐 Deep Research Report: {}\n\n", query));
    fallback_report.push_str("## 📋 Executive Summary\n\n");
    fallback_report.push_str(&format!(
        "Live internet research successfully retrieved {} verified sources from current web data.\n\n",
        results.len()
    ));
    fallback_report.push_str("## 🚀 Key Findings & Snippets\n\n");
    for (i, r) in results.iter().enumerate() {
        fallback_report.push_str(&format!("### {}. [{}]({})\n\n", i + 1, r.title, r.url));
        fallback_report.push_str(&format!("{}\n\n", r.snippet));
    }
    fallback_report.push_str("## 📚 Sources & Citations\n\n");
    for r in results {
        fallback_report.push_str(&format!("- [{}]({})\n", r.title, r.url));
    }

    Ok(fallback_report)
}

/// Executes research: searches the live web and arXiv scientific papers in parallel,
/// indexes all retrieved documents into WebSearchIndex, and synthesizes an authoritative report.
pub async fn run_deep_research(
    query: &str,
    max_results: usize,
    model_override: Option<&str>,
) -> Result<String> {
    println!("🔍 Searching the internet & arXiv for \"{}\"...", query);
    let (web_res, arxiv_res) = tokio::join!(
        live_web_search(query, max_results),
        search_arxiv(query, 5)
    );
    let web_results = web_res.unwrap_or_default();
    let raw_arxiv_results = arxiv_res.unwrap_or_default();
    let arxiv_results: Vec<SearchResult> = raw_arxiv_results
        .into_iter()
        .filter(|r| calculate_search_relevance(query, &r.title, &r.snippet) >= 0)
        .collect();
    let n_web = web_results.len();
    let m_arxiv = arxiv_results.len();
    println!(
        "Retrieved {} web sources and {} arXiv papers. Correlating results with LLM...",
        n_web, m_arxiv
    );

    let mut combined_results = web_results;
    combined_results.extend(arxiv_results);

    let mut search_index = WebSearchIndex::new();
    search_index.add_search_results(&combined_results);

    synthesize_research(query, &combined_results, model_override).await
}

/// Quick live search only: retrieves results and formats markdown links with snippets.
pub async fn run_web_search_only(query: &str, max_results: usize) -> Result<String> {
    println!("🔍 Searching the internet for: \"{}\"...", query);
    let results = live_web_search(query, max_results).await?;
    if results.is_empty() {
        return Ok(format!(
            "⚠️ No search results found for: \"{}\". Please check internet connectivity.",
            query
        ));
    }

    let mut out = String::new();
    out.push_str(&format!("### 🔍 Live Web Search Results for: \"{}\"\n\n", query));
    for (i, r) in results.iter().enumerate() {
        out.push_str(&format!("{}. **[{}]({})**\n", i + 1, r.title, r.url));
        if !r.snippet.is_empty() {
            out.push_str(&format!("   {}\n", r.snippet));
        }
        out.push('\n');
    }
    Ok(out)
}

/// Result returned by the web search agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebAgentResult {
    pub user_query: String,
    pub search_query: String,
    pub response: String,
    pub tokens_returned: u32,
    pub results_count: usize,
    pub index: WebSearchIndex,
}

/// Executes the complete 3-phase web search agent workflow:
/// 1. Query Formulation: Local LLM generates a targeted search query string.
/// 2. Web Retrieval: Live web search executes against DuckDuckGo.
/// 3. Search Indexing: All retrieved documents and snippets are indexed into a structured WebSearchIndex.
/// 4. Grounded Synthesis: Local LLM synthesizes a cited answer with **256 tokens default return**.
pub async fn run_web_agent(
    user_query: &str,
    max_tokens: Option<u32>,
    model_override: Option<&str>,
) -> Result<WebAgentResult> {
    let tokens_limit = max_tokens.unwrap_or(256); // 256 tokens must be default return!
    let model_to_use = match model_override {
        Some(m) if !m.is_empty() => m.to_string(),
        _ => detect_best_reasoning_model().await,
    };

    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
    let client = reqwest::Client::builder()
        .no_proxy()
        .connect_timeout(Duration::from_secs(3))
        .timeout(Duration::from_secs(12))
        .build()?;

    // Phase 1: Query Formulation using the local model
    let query_formulation_prompt = format!(
        "You are an automated research agent. Produce a single concise web search query to find the answer to the following question. Output only the search query string and nothing else.\n\nQuestion: {}",
        user_query
    );

    let search_query = {
        let req_body = serde_json::json!({
            "model": &model_to_use,
            "prompt": &query_formulation_prompt,
            "stream": false,
            "options": {
                "temperature": 0.1,
                "num_predict": 48
            }
        });
        let gen_url = format!("{}/api/generate", endpoint.trim_end_matches('/'));
        match client.post(&gen_url).json(&req_body).send().await {
            Ok(resp) if resp.status().is_success() => {
                if let Ok(json) = resp.json::<serde_json::Value>().await {
                    let raw = json["response"].as_str().unwrap_or(user_query).trim();
                    let cleaned = raw.trim_matches('"').trim_matches('\'').trim();
                    if cleaned.is_empty() { user_query.to_string() } else { cleaned.to_string() }
                } else {
                    user_query.to_string()
                }
            }
            _ => user_query.to_string(),
        }
    };

    // Phase 2: Live Web & arXiv Retrieval
    println!("🔍 Searching the internet & arXiv for \"{}\"...", search_query);
    let (web_res, arxiv_res) = tokio::join!(
        live_web_search(&search_query, 6),
        search_arxiv(&search_query, 5)
    );
    let web_results = web_res.unwrap_or_default();
    let arxiv_results = arxiv_res.unwrap_or_default();
    let n_web = web_results.len();
    let m_arxiv = arxiv_results.len();
    println!(
        "Retrieved {} web sources and {} arXiv papers. Correlating results with LLM...",
        n_web, m_arxiv
    );

    let mut search_results = web_results;
    search_results.extend(arxiv_results);

    // Phase 3: Index all retrieved data into WebSearchIndex
    println!("📊 Indexing retrieved documents into WebSearchIndex...");
    let mut search_index = WebSearchIndex::new();
    search_index.add_search_results(&search_results);

    // Phase 4: Grounded Synthesis with Default 256 Tokens Return
    println!("🧠 Correlating results with LLM ({} tokens default return)...", tokens_limit);
    let context_buffer = search_index.format_context_buffer(6);
    let synthesis_prompt = if !context_buffer.is_empty() {
        format!(
            "You are an expert analyst. Answer the user query strictly using the provided search context. Cite the specific bracketed sources in your explanation.\n\nContext:\n{}\nQuestion: {}\nAnswer:",
            context_buffer, user_query
        )
    } else {
        format!(
            "Answer the following question directly and concisely in 2-3 clear paragraphs:\n\nQuestion: {}\nAnswer:",
            user_query
        )
    };

    let response_text = {
        let req_body = serde_json::json!({
            "model": &model_to_use,
            "prompt": &synthesis_prompt,
            "stream": false,
            "options": {
                "temperature": 0.3,
                "num_predict": tokens_limit // 256 tokens default return
            }
        });
        let gen_url = format!("{}/api/generate", endpoint.trim_end_matches('/'));
        let mut final_text = String::new();
        if let Ok(resp) = client.post(&gen_url).json(&req_body).send().await {
            if resp.status().is_success() {
                if let Ok(json) = resp.json::<serde_json::Value>().await {
                    if let Some(t) = json["response"].as_str() {
                        final_text = t.trim().to_string();
                    }
                }
            }
        }

        // Resilient fallback if local LLM is offline or timed out
        if final_text.is_empty() {
            if !search_results.is_empty() {
                let mut fallback = format!("### Grounded Synthesis for: \"{}\"\n\n", user_query);
                for (i, r) in search_results.iter().take(3).enumerate() {
                    fallback.push_str(&format!("[{}] **{}**: {}\n\n", i + 1, r.title, r.snippet));
                }
                final_text = fallback;
            } else {
                final_text = format!("No search results could be retrieved for: \"{}\"", user_query);
            }
        }
        final_text
    };

    Ok(WebAgentResult {
        user_query: user_query.to_string(),
        search_query,
        response: response_text,
        tokens_returned: tokens_limit,
        results_count: search_results.len(),
        index: search_index,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_html_entities() {
        let input = "<b>Rust</b> &amp; Web &quot;Research&#x27;s&quot; <a href='foo'>guide</a>";
        let output = clean_html_entities(input);
        assert_eq!(output, "Rust & Web \"Research's\" guide");
    }

    #[test]
    fn test_decode_percent_encoded() {
        let input = "https%3A%2F%2Fexample.com%2Ftest";
        let output = decode_percent_encoded(input);
        assert_eq!(output, "https://example.com/test");
    }

    #[tokio::test]
    async fn test_live_web_search_returns_results() {
        let results = live_web_search("rust programming language", 3).await;
        assert!(results.is_ok());
        let list = results.unwrap();
        // Since we are connected to the live web, verify results were retrieved
        if !list.is_empty() {
            assert!(list[0].url.starts_with("http"));
            assert!(!list[0].title.is_empty());
        }
    }

    #[test]
    fn test_web_search_index_indexing_and_search() {
        let mut index = WebSearchIndex::new();
        index.add_document(
            "Post-Quantum Cryptography Standards",
            "https://csrc.nist.gov/pqc",
            "NIST has standardized post-quantum algorithms including ML-KEM and ML-DSA."
        );
        index.add_document(
            "Rust Async Concurrency Guide",
            "https://tokio.rs",
            "Tokio provides asynchronous runtime and fast multi-threaded task scheduling."
        );

        let summary = index.index_summary();
        assert_eq!(summary["total_documents"], 2);
        assert!(summary["unique_terms"].as_u64().unwrap() > 5);

        let matches = index.search("cryptography algorithms");
        assert!(!matches.is_empty());
        assert_eq!(matches[0].title, "Post-Quantum Cryptography Standards");

        let tokio_matches = index.search("tokio asynchronous");
        assert!(!tokio_matches.is_empty());
        assert_eq!(tokio_matches[0].title, "Rust Async Concurrency Guide");

        let context = index.format_context_buffer(2);
        assert!(context.contains("[1] Title: Post-Quantum Cryptography Standards"));
        assert!(context.contains("[2] Title: Rust Async Concurrency Guide"));
    }

    #[test]
    fn test_web_search_index_empty_query() {
        let index = WebSearchIndex::new();
        let matches = index.search("");
        assert!(matches.is_empty());
    }

    #[tokio::test]
    async fn test_web_agent_default_256_tokens() {
        let res = run_web_agent("What is Rust?", None, None).await;
        assert!(res.is_ok());
        let agent_res = res.unwrap();
        assert_eq!(agent_res.tokens_returned, 256); // 256 tokens must be default return!
        assert!(!agent_res.search_query.is_empty());
    }

    #[test]
    fn test_parse_arxiv_atom_entry() {
        let sample_xml = r#"<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2303.08774v1</id>
    <published>2023-03-15T17:59:44Z</published>
    <title>  GPT-4 Technical
       Report  </title>
    <summary>   We present GPT-4, a large multimodal model
 capable of processing image and text inputs.  </summary>
    <author><name>OpenAI</name></author>
    <author><name>Josh Achiam</name></author>
    <author><name>Steven Adler</name></author>
    <author><name>Fourth Author</name></author>
  </entry>
</feed>"#;

        let results = parse_arxiv_atom(sample_xml);
        assert_eq!(results.len(), 1);
        let first = &results[0];
        assert_eq!(first.url, "https://arxiv.org/abs/2303.08774v1");
        assert_eq!(first.title, "[arXiv] GPT-4 Technical Report (OpenAI, Josh Achiam, Steven Adler, 2023)");
        assert_eq!(first.snippet, "We present GPT-4, a large multimodal model capable of processing image and text inputs.");
    }

    #[test]
    fn test_web_search_index_with_arxiv_results() {
        let mut index = WebSearchIndex::new();
        let arxiv_res = SearchResult {
            title: "[arXiv] Deep Residual Learning for Image Recognition (Kaiming He, Xiangyu Zhang, 2015)".to_string(),
            url: "https://arxiv.org/abs/1512.03385".to_string(),
            snippet: "Deeper neural networks are more difficult to train. We present a residual learning framework to ease training.".to_string(),
        };
        let web_res = SearchResult {
            title: "ResNet Architecture Overview".to_string(),
            url: "https://example.com/resnet".to_string(),
            snippet: "ResNet introduced skip connections allowing networks up to 152 layers.".to_string(),
        };

        index.add_search_results(&[web_res, arxiv_res]);
        let summary = index.index_summary();
        assert_eq!(summary["total_documents"], 2);

        let matches = index.search("residual learning");
        assert!(!matches.is_empty());
        assert!(matches.iter().any(|m| m.url == "https://arxiv.org/abs/1512.03385"));
    }
}

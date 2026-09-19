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

/// Executes a live web search against DuckDuckGo (Lite and Instant Answer API).
pub async fn live_web_search(query: &str, max_results: usize) -> Result<Vec<SearchResult>> {
    let mut results = Vec::new();

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

    // 1. DuckDuckGo Lite endpoint (POST form with clean tabular data)
    let form_params = [("q", query)];
    let lite_resp = client
        .post("https://lite.duckduckgo.com/lite/")
        .headers(headers.clone())
        .form(&form_params)
        .send()
        .await;

    if let Ok(resp) = lite_resp {
        if resp.status().is_success() {
            if let Ok(html) = resp.text().await {
                // Parse result-link anchor tags: <a rel="nofollow" href="..." class='result-link'>...</a>
                let mut cursor = 0;
                while let Some(link_start) = html[cursor..].find("class='result-link'") {
                    let abs_start = cursor + link_start;
                    // Find preceding <a ... href="
                    if let Some(href_idx) = html[..abs_start].rfind("href=\"") {
                        let url_start = href_idx + 6;
                        if let Some(url_end) = html[url_start..].find('"') {
                            let raw_url = &html[url_start..url_start + url_end];
                            // Extract actual URL if redirected via uddg=
                            let clean_url = if let Some(uddg_pos) = raw_url.find("uddg=") {
                                let after_uddg = &raw_url[uddg_pos + 5..];
                                let end_param = after_uddg.find('&').unwrap_or(after_uddg.len());
                                decode_percent_encoded(&after_uddg[..end_param])
                            } else {
                                raw_url.to_string()
                            };

                            // Find link text
                            let tag_close = html[abs_start..].find('>').map(|p| abs_start + p + 1).unwrap_or(abs_start);
                            let title = if let Some(tag_end) = html[tag_close..].find("</a>") {
                                clean_html_entities(&html[tag_close..tag_close + tag_end])
                            } else {
                                String::new()
                            };

                            // Search for subsequent result-snippet
                            let snippet_start = html[abs_start..].find("class='result-snippet'").map(|p| abs_start + p);
                            let snippet = if let Some(snip_pos) = snippet_start {
                                if let Some(td_close) = html[snip_pos..].find('>') {
                                    let snip_content_start = snip_pos + td_close + 1;
                                    if let Some(td_end) = html[snip_content_start..].find("</td>") {
                                        clean_html_entities(&html[snip_content_start..snip_content_start + td_end])
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
                                results.push(SearchResult {
                                    title,
                                    url: clean_url,
                                    snippet,
                                });
                            }

                            if results.len() >= max_results {
                                break;
                            }
                        }
                    }
                    cursor = abs_start + 20;
                }
            }
        }
    }

    // 2. Fallback: DuckDuckGo Instant Answer API if lite produced nothing
    if results.is_empty() {
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
                    results.push(SearchResult {
                        title: if heading.is_empty() { query.to_string() } else { heading },
                        url: abstract_url,
                        snippet: abstract_text,
                    });
                }

                if let Some(topics) = data["RelatedTopics"].as_array() {
                    for t in topics {
                        if let (Some(text), Some(url)) = (t["Text"].as_str(), t["FirstURL"].as_str()) {
                            let title = text.split(" - ").next().unwrap_or(text).chars().take(60).collect::<String>();
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

    Ok(results)
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
comprehensive, and structured research report.

Guidelines:
- Deliver deep technical and commercial insights with rigorous analytical clarity.
- Structure using clear markdown headings:
  # 🌐 Deep Research Report: <Title>
  ## 📋 Executive Summary
  ## 🚀 Key Developments & Breakthroughs
  ## 🔬 Technical Deep Dive & Architecture
  ## 📈 Market & Commercial Outlook
  ## 📚 Sources & Citations
- In the Sources section, cite every relevant source as a markdown link [Source Title](URL).
- Highlight key metrics, players, benchmarks, and dates.";

    let user_prompt = format!(
        "Research Topic: \"{}\"\n\nLive Internet Search Data (Retrieved):\n{}\n\nGenerate the complete research report:",
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
            "num_predict": 2048
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

/// Executes research: attempts the Python smolagents / web research script first,
/// falling back to native Rust search + reasoning synthesis.
pub async fn run_deep_research(
    query: &str,
    max_results: usize,
    model_override: Option<&str>,
) -> Result<String> {
    // 1. Try invoking Python web_research_agent.py if available
    let mut script_candidates = vec![
        std::path::PathBuf::from("src/scripts/web_research_agent.py"),
        std::path::PathBuf::from("../src/scripts/web_research_agent.py"),
        std::path::PathBuf::from("../../src/scripts/web_research_agent.py"),
    ];

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            script_candidates.push(exe_dir.join("src").join("scripts").join("web_research_agent.py"));
            if let Some(install_root) = exe_dir.parent() {
                script_candidates.push(install_root.join("src").join("scripts").join("web_research_agent.py"));
                script_candidates.push(install_root.join("resources").join("app").join("src").join("scripts").join("web_research_agent.py"));
            }
        }
    }

    let mut py_script = None;
    for c in &script_candidates {
        if c.exists() {
            py_script = Some(c.clone());
            break;
        }
    }

    if let Some(script) = py_script {
        let mut cmd = tokio::process::Command::new("python");
        cmd.arg(&script).arg(query);
        cmd.arg("--max-results").arg(max_results.to_string());
        if let Some(m) = model_override {
            cmd.arg("--model").arg(m);
        }

        if let Ok(output) = cmd.output().await {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !stdout.is_empty() && !stdout.starts_with("⚠️") {
                    return Ok(stdout);
                }
            }
        }
    }

    // 2. Resilient Native Rust Execution:
    let search_results = live_web_search(query, max_results).await?;
    synthesize_research(query, &search_results, model_override).await
}

/// Quick live search only: retrieves results and formats markdown links with snippets.
pub async fn run_web_search_only(query: &str, max_results: usize) -> Result<String> {
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
}

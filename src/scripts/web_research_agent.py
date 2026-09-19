"""
Web Research Agent for ModelFusion & HugOS IDE
==============================================
Autonomous internet research agent combining open-weight foundation/reasoning
models (Qwen 2.5 / DeepSeek-R1) with agentic tool-use frameworks:
1. smolagents (CodeAgent + DuckDuckGoSearchTool + HfApiModel / local Ollama)
2. Standalone fallback: DuckDuckGo live web search + text extractor + reasoning synthesis
"""

import os
import sys
import io
import json
import re
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

OLLAMA_ENDPOINT = os.environ.get("LOCAL_OLLAMA_ENDPOINT", "http://127.0.0.1:11434").rstrip('/')

def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape common entities."""
    # Remove script and style tags
    clean = re.sub(r'<script[\s\S]*?</script>', ' ', raw_html, flags=re.IGNORECASE)
    clean = re.sub(r'<style[\s\S]*?</style>', ' ', clean, flags=re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#x27;', "'").replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def search_duckduckgo(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Query DuckDuckGo Lite / HTML for live internet search results."""
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # 1. Try DuckDuckGo Lite (clean tabular results)
    try:
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request("https://lite.duckduckgo.com/lite/", data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract links and snippets from DDG lite table
        link_matches = re.findall(
            r"<a rel=\"nofollow\" href=\"([^\"]+)\" class=['\"]result-link['\"][^>]*>([\s\S]*?)</a>",
            html
        )
        snippet_matches = re.findall(
            r"<td class=['\"]result-snippet['\"][^>]*>([\s\S]*?)</td>",
            html
        )

        for i in range(min(len(link_matches), max_results)):
            raw_url, raw_title = link_matches[i]
            # DDG lite wraps external URLs in /l/?kh=-1&uddg=...
            clean_url = raw_url
            if "uddg=" in raw_url:
                m = re.search(r'uddg=([^&]+)', raw_url)
                if m:
                    clean_url = urllib.parse.unquote(m.group(1))

            title = clean_html(raw_title)
            snippet = clean_html(snippet_matches[i]) if i < len(snippet_matches) else ""
            if clean_url.startswith("http") and title:
                results.append({
                    "title": title,
                    "url": clean_url,
                    "snippet": snippet
                })
    except Exception as e:
        sys.stderr.write(f"[WebResearch] DDG Lite search exception: {e}\n")

    # 2. Fallback to DuckDuckGo Instant Answer API if lite returned nothing
    if not results:
        try:
            api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                
            heading = data.get("Heading", "")
            abstract = data.get("AbstractText", "")
            source_url = data.get("AbstractURL", "")
            if abstract and source_url:
                results.append({
                    "title": heading or query,
                    "url": source_url,
                    "snippet": abstract
                })
            for topic in data.get("RelatedTopics", []):
                if isinstance(topic, dict) and "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic["Text"].split(" - ")[0] if " - " in topic["Text"] else topic["Text"][:60],
                        "url": topic["FirstURL"],
                        "snippet": topic["Text"]
                    })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            sys.stderr.write(f"[WebResearch] DDG API exception: {e}\n")

    return results[:max_results]

def pick_reasoning_model() -> str:
    """Select the best open-weight reasoning model in local Ollama based on detected hardware memory."""
    free_ram_gb = 16.0
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            free_ram_gb = stat.ullAvailPhys / (1024 ** 3)
    except Exception:
        pass

    if free_ram_gb >= 48.0:
        preferred = ["deepseek-r1:32b", "qwen2.5:32b", "deepseek-r1:14b", "qwen2.5:14b", "deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b"]
        default_model = "qwen2.5:32b"
    elif free_ram_gb >= 24.0:
        preferred = ["deepseek-r1:14b", "qwen2.5:14b", "deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:32b", "qwen2.5:32b"]
        default_model = "qwen2.5:14b"
    elif free_ram_gb >= 12.0:
        preferred = ["deepseek-r1:8b", "deepseek-r1:7b", "qwen2.5:7b", "qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:14b", "qwen2.5:14b"]
        default_model = "qwen2.5:7b"
    elif free_ram_gb >= 6.0:
        preferred = ["qwen2.5:3b", "deepseek-r1:1.5b", "qwen2.5:1.5b", "deepseek-r1:7b", "qwen2.5:7b"]
        default_model = "qwen2.5:3b"
    else:
        preferred = ["deepseek-r1:1.5b", "qwen2.5:1.5b", "qwen2.5:3b"]
        default_model = "qwen2.5:1.5b"

    try:
        req = urllib.request.Request(f"{OLLAMA_ENDPOINT}/api/tags", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            installed = [m.get("name", "") for m in data.get("models", [])]
            for p in preferred:
                for m in installed:
                    if m.startswith(p):
                        return m
            if installed:
                return installed[0]
    except Exception:
        pass
    return default_model

def run_smolagents(query: str) -> Optional[str]:
    """Execute research prompt using Hugging Face smolagents library if installed."""
    try:
        from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel
        search_tool = DuckDuckGoSearchTool()
        
        # Check if HF_TOKEN is configured; if so, use HF inference model
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
        if hf_token:
            model = HfApiModel("Qwen/Qwen2.5-72B-Instruct", token=hf_token)
        else:
            # Point smolagents to local Ollama via OpenAI-compatible endpoint
            from smolagents import OpenAIServerModel
            local_model_name = pick_reasoning_model()
            model = OpenAIServerModel(
                model_id=local_model_name,
                api_base=f"{OLLAMA_ENDPOINT}/v1",
                api_key="ollama"
            )

        agent = CodeAgent(
            tools=[search_tool],
            model=model,
            additional_authorized_imports=["requests", "bs4", "json", "re"]
        )
        report = agent.run(f"Conduct comprehensive, deep internet research on: '{query}'. Provide key findings, technical analysis, and references.")
        return str(report)
    except ImportError:
        return None
    except Exception as e:
        sys.stderr.write(f"[WebResearch] smolagents execution failed: {e}. Falling back to native research agent.\n")
        return None

def synthesize_with_reasoning_model(query: str, search_results: List[Dict[str, str]], model_name: Optional[str] = None) -> str:
    """Synthesize web research results into a structured report using open-weight reasoning model."""
    if not model_name:
        model_name = pick_reasoning_model()

    # Build structured context block
    context_lines = []
    for idx, item in enumerate(search_results, start=1):
        context_lines.append(f"[{idx}] Title: {item['title']}")
        context_lines.append(f"    URL: {item['url']}")
        context_lines.append(f"    Snippet: {item['snippet']}\n")
    context_text = "\n".join(context_lines)

    system_prompt = (
        "You are an Autonomous Deep Web Research Agent powered by open-weight reasoning models (Qwen 2.5 / DeepSeek-R1). "
        "Your task is to analyze, verify, and synthesize real-time internet search results into an authoritative, "
        "comprehensive, and structured research report.\n\n"
        "Guidelines:\n"
        "- Synthesize facts objectively with analytical depth.\n"
        "- Format using markdown with clear headings: Executive Summary, Key Developments & Breakthroughs, "
        "Technical Deep Dive, Market & Commercial Outlook, and Sources & Citations.\n"
        "- In the Sources section, cite every relevant source as a clickable markdown link [Title](URL).\n"
        "- Highlight key numbers, dates, benchmarks, and commercial players."
    )

    user_prompt = (
        f"Research Query: \"{query}\"\n\n"
        f"Retrieved Live Web Search Data:\n"
        f"{context_text}\n\n"
        "Generate the complete, structured research report based on these real-time web results."
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_ENDPOINT}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=240) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            content = res_json.get("message", {}).get("content", "")
            if content:
                # If the reasoning model uses <think> tags (like DeepSeek-R1), format nicely
                return content.strip()
    except Exception as e:
        sys.stderr.write(f"[WebResearch] Ollama synthesis error: {e}\n")

    # Fallback template report if LLM call fails
    report = [
        f"# 🌐 Autonomous Web Research Report: {query}",
        "",
        "## Executive Summary",
        f"Live search retrieved {len(search_results)} relevant sources from the web.",
        "",
        "## Key Findings & Snippets",
    ]
    for idx, item in enumerate(search_results, start=1):
        report.append(f"### {idx}. [{item['title']}]({item['url']})")
        report.append(f"{item['snippet']}\n")
    report.append("## Sources & Citations")
    for item in search_results:
        report.append(f"- [{item['title']}]({item['url']})")

    return "\n".join(report)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ModelFusion Autonomous Web Research Agent")
    parser.add_argument("query", nargs="?", help="Research topic or search query")
    parser.add_argument("--query", dest="query_opt", help="Research query (named flag)")
    parser.add_argument("--search-only", action="store_true", help="Only return search results without LLM synthesis")
    parser.add_argument("--max-results", type=int, default=8, help="Max search results to retrieve")
    parser.add_argument("--model", type=str, default=None, help="Force specific reasoning model")
    args = parser.parse_args()

    query = args.query or args.query_opt
    if not query:
        # Default query for testing
        query = "Find the latest commercial developments in solid-state batteries in 2026 and summarize key players."

    # If user only wants quick web search snippets
    if args.search_only:
        results = search_duckduckgo(query, max_results=args.max_results)
        print(f"### 🔍 Live Web Search Results for: \"{query}\"\n")
        for idx, item in enumerate(results, start=1):
            print(f"{idx}. **[{item['title']}]({item['url']})**")
            print(f"   {item['snippet']}\n")
        return

    # 1. Try smolagents if available
    smol_result = run_smolagents(query)
    if smol_result:
        print(smol_result)
        return

    # 2. Native high-performance web research workflow
    results = search_duckduckgo(query, max_results=args.max_results)
    if not results:
        print(f"⚠️ No web search results could be retrieved for: \"{query}\". Please check your network connection.")
        return

    report = synthesize_with_reasoning_model(query, results, model_name=args.model)
    print(report)

if __name__ == "__main__":
    main()

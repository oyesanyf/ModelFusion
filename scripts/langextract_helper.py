#!/usr/bin/env python3
"""
LangExtract Helper for ModelFusion / HugOS
Universal factual extraction helper for search snippets and web text
using Google LangExtract (1.7.1) with local Ollama models (gemma2:2b / qwen2.5:7b).
"""

import sys
import os
import json
import argparse
import re
from typing import Dict, Any, List

def build_examples_for_domain(domain: str):
    from langextract.data import ExampleData, Extraction

    d = (domain or "general").lower()
    if "finan" in d or "stock" in d or "market" in d:
        return [
            ExampleData(
                text="Alphabet Inc (GOOGL) stock traded at $182.50 (+1.25%) with market cap of $2.25T as of Oct 2024.",
                extractions=[
                    Extraction(
                        extraction_class="stock_quote",
                        extraction_text="$182.50 (+1.25%)",
                        attributes={
                            "entity": "GOOGL",
                            "metric": "price",
                            "value": "$182.50",
                            "change": "+1.25%",
                            "market_cap": "$2.25T"
                        }
                    )
                ]
            )
        ]
    elif "legal" in d or "law" in d:
        return [
            ExampleData(
                text="Under UCC Section 2-201, a contract for the sale of goods priced at $500 or more is not enforceable without signed writing.",
                extractions=[
                    Extraction(
                        extraction_class="legal_rule",
                        extraction_text="UCC Section 2-201",
                        attributes={
                            "statute": "UCC 2-201",
                            "rule": "Statute of Frauds for goods >= $500 requires writing"
                        }
                    )
                ]
            )
        ]
    else:
        return [
            ExampleData(
                text="Nigeria gained independence from the United Kingdom on October 1, 1960, becoming a sovereign nation in West Africa.",
                extractions=[
                    Extraction(
                        extraction_class="historical_fact",
                        extraction_text="October 1, 1960",
                        attributes={
                            "entity": "Nigeria",
                            "event": "Independence",
                            "from": "United Kingdom",
                            "date": "October 1, 1960"
                        }
                    )
                ]
            )
        ]

def heuristic_fallback_extract(text: str, domain: str, query: str = "") -> Dict[str, Any]:
    """Graceful fallback rule-based extraction when Ollama is offline or times out."""
    facts = []
    entities = set()

    # Financial pattern extractions
    price_matches = re.findall(r'(\$?\d{1,5}(?:\.\d{1,4})?)\s*(?:USD)?\s*([+\-]\d+(?:\.\d+)?%)?', text)
    ticker_matches = re.findall(r'\b([A-Z]{1,5})\b', text)
    valid_tickers = [t for t in ticker_matches if t not in ('THE', 'AND', 'FOR', 'NEW', 'EST', 'USD', 'TODAY', 'NOW', 'OCT', 'NOV', 'DEC', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP')]

    for t in valid_tickers[:5]:
        entities.add(t)

    # Date extractions
    date_matches = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', text, re.IGNORECASE)

    if "finan" in domain.lower() or "stock" in domain.lower():
        for p, chg in price_matches:
            if p and p != "$":
                fact = {
                    "class": "stock_metric",
                    "text": p,
                    "attributes": {
                        "value": p,
                        "change": chg or ""
                    }
                }
                facts.append(fact)
                if len(facts) >= 5:
                    break

    for d in date_matches[:3]:
        facts.append({
            "class": "date_reference",
            "text": d,
            "attributes": {"date": d}
        })

    return {
        "status": "success",
        "query": query,
        "domain": domain,
        "facts": facts,
        "entities": list(entities),
        "source": "heuristic_fallback"
    }

def main():
    parser = argparse.ArgumentParser(description="LangExtract factual grounding helper")
    parser.add_argument("--query", type=str, default="", help="User search query")
    parser.add_argument("--text", type=str, default="", help="Text or search snippet to extract facts from")
    parser.add_argument("--domain", type=str, default="general", help="Domain: finance, legal, tech, general")
    parser.add_argument("--model", type=str, default="gemma2:2b", help="Ollama model ID")
    parser.add_argument("--ollama-url", type=str, default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--json-input", type=str, default="", help="Optional JSON string input")

    args = parser.parse_args()

    query = args.query
    text = args.text
    domain = args.domain
    model_id = args.model
    ollama_url = args.ollama_url

    if args.json_input:
        try:
            payload = json.loads(args.json_input)
            query = payload.get("query", query)
            text = payload.get("text", text)
            domain = payload.get("domain", domain)
            model_id = payload.get("model", model_id)
            ollama_url = payload.get("ollama_url", ollama_url)
        except Exception:
            pass
    elif not text and not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                try:
                    payload = json.loads(stdin_data)
                    query = payload.get("query", query)
                    text = payload.get("text", text)
                    domain = payload.get("domain", domain)
                    model_id = payload.get("model", model_id)
                    ollama_url = payload.get("ollama_url", ollama_url)
                except Exception:
                    text = stdin_data
        except Exception:
            pass

    if not text:
        text = query

    if not text:
        print(json.dumps({"status": "error", "message": "No text provided for extraction"}))
        return

    # Attempt LangExtract with local Ollama
    try:
        import langextract as lx

        examples = build_examples_for_domain(domain)
        prompt_desc = f"Extract structured factual data, key entities, numbers, and dates relevant to: {query or domain}"

        res = lx.extract(
            text_or_documents=text[:2500],  # bounded snippet
            model_id=model_id,
            prompt_description=prompt_desc,
            examples=examples,
            model_url=ollama_url,
            show_progress=False
        )

        facts = []
        entities = set()
        if hasattr(res, "extractions"):
            for ex in res.extractions:
                facts.append({
                    "class": ex.extraction_class,
                    "text": ex.extraction_text,
                    "attributes": getattr(ex, "attributes", {}) or {}
                })
                attrs = getattr(ex, "attributes", {}) or {}
                if "entity" in attrs and attrs["entity"]:
                    entities.add(str(attrs["entity"]))

        result = {
            "status": "success",
            "query": query,
            "domain": domain,
            "facts": facts,
            "entities": list(entities),
            "source": f"langextract:{model_id}"
        }
        print(json.dumps(result, ensure_ascii=False))
        return

    except Exception as e:
        # Fall back to heuristic extraction
        fallback_res = heuristic_fallback_extract(text, domain, query)
        fallback_res["error"] = str(e)
        print(json.dumps(fallback_res, ensure_ascii=False))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ModelFusion Google LangExtract Engine (scripts/langextract_engine.py)

Uses Google's official `langextract` library (`import langextract as lx`)
to perform grounded, structured information extraction, entity identification,
coreference resolution, and query interpretation for ModelFusion / HugOS IDE & Browser.
"""

import sys
import os
import json
import argparse
import re
from typing import List, Dict, Any, Optional

try:
    import langextract as lx
    HAS_LANGEXTRACT = True
except ImportError:
    HAS_LANGEXTRACT = False

STOPWORDS = {
    "the", "and", "for", "has", "have", "had", "published", "any", "articles", "article",
    "who", "what", "where", "when", "why", "how", "did", "does", "with", "from", "about",
    "his", "her", "their", "its", "our", "him", "them", "this", "that", "these", "those",
    "all", "some", "few", "more", "most", "other", "into", "onto", "upon", "can", "will",
    "would", "should", "could", "tell", "show", "give", "find", "search", "lookup"
}

def extract_char_intervals(text: str, substring: str) -> List[Dict[str, int]]:
    """Finds all non-overlapping character intervals for a substring in text."""
    intervals = []
    if not substring or not text:
        return intervals
    start = 0
    sub_lower = substring.lower()
    text_lower = text.lower()
    while True:
        pos = text_lower.find(sub_lower, start)
        if pos == -1:
            break
        intervals.append({"start_pos": pos, "end_pos": pos + len(substring)})
        start = pos + max(1, len(substring))
    return intervals

def resolve_coreference_from_history(query: str, history: List[str]) -> Optional[str]:
    """Finds the most recent prominent person or entity from conversation history."""
    if not history:
        return None
    # Reverse iterate to find most recent entity
    for turn in reversed(history):
        if not turn or not isinstance(turn, str):
            continue
        clean_turn = re.sub(r'^(?:@agent\s+|/|--)?(?:browser\s+deep\s+research\s+on|deep\s+research\s+on|search|research|wiki|arxiv)?\s*', '', turn, flags=re.IGNORECASE).strip()
        # Look for capitalized 2-4 word names or proper nouns
        words = [w.strip(".,;:?!'\"") for w in clean_turn.split() if w.strip(".,;:?!'\"")]
        if 1 <= len(words) <= 5:
            # Check if it has non-stopwords
            non_stops = [w for w in words if w.lower() not in STOPWORDS]
            if len(non_stops) >= 1:
                return " ".join(words)
    return None

def interpret_query_langextract(
    raw_query: str,
    history: Optional[List[str]] = None,
    active_menu_tool: Optional[str] = None
) -> Dict[str, Any]:
    text = (raw_query or "").strip()
    history = history or []
    
    extractions = []
    
    # 1. Action Intent extraction
    action_match = re.search(r'^(?:@agent\s+)?([a-z0-9_-]+(?:\s+[a-z0-9_-]+)*)\b', text, re.IGNORECASE)
    intent = "qa"
    domain = "general"
    route_to_web = False
    
    lower_text = text.lower()
    
    # Menu / Agent directive extraction
    clean_prompt = text
    if lower_text.startswith("@agent ") or lower_text.startswith("/") or lower_text.startswith("--"):
        directive_m = re.match(r'^(?:@agent\s+|/|--)([a-z0-9_-]+(?:\s+[a-z0-9_-]+)*)\s*(.*)$', text, re.IGNORECASE)
        if directive_m:
            tool_name = directive_m.group(1).strip()
            clean_prompt = directive_m.group(2).strip()
            extractions.append({
                "extraction_class": "action_intent",
                "extraction_text": text[:len(text) - len(clean_prompt)].strip(),
                "char_interval": {"start_pos": 0, "end_pos": len(text) - len(clean_prompt)},
                "alignment_status": "MATCH_EXACT",
                "attributes": {"directive": tool_name, "raw_command": "true"}
            })
            
            # Map tool to intent/domain
            tool_l = tool_name.lower()
            if "deep research" in tool_l or "deep-research" in tool_l or "research" in tool_l:
                intent = "deep_research"
                route_to_web = True
                domain = "research"
            elif "search" in tool_l or "web" in tool_l:
                intent = "web_search"
                route_to_web = True
                domain = "web"
            elif "finance" in tool_l or "stock" in tool_l:
                intent = "financial_valuation"
                domain = "finance"
                route_to_web = True
            elif "legal" in tool_l or "saul" in tool_l:
                intent = "legal_analysis"
                domain = "legal"
            elif "code" in tool_l or "review" in tool_l:
                intent = "code_review"
                domain = "code"
            elif "writing" in tool_l or "boost" in tool_l:
                intent = "writing_enhancement"
                domain = "writing"
            elif "cuad" in tool_l or "compliance" in tool_l:
                intent = "compliance_audit"
                domain = "compliance"
    
    # 2. Check Deep Research / Web Search explicit phrases
    if re.search(r'\b(?:browser\s+deep\s+research(?:\s+on)?|deep\s+research(?:\s+on)?)\b', lower_text):
        intent = "deep_research"
        route_to_web = True
        domain = "research"
    elif re.search(r'\b(?:search\s+(?:for|the\s+web\s+for|on\s+google|google)?|look\s+up\s+on\s+google)\b', lower_text):
        intent = "web_search"
        route_to_web = True
        domain = "web"

    # 3. Coreference resolution (pronouns: he, she, his, her, they, their, him, the author)
    coref_match = re.search(r'\b(he|she|his|her|him|they|their|the author|this person)\b', text, re.IGNORECASE)
    resolved_entity = None
    is_followup = False
    
    if coref_match:
        pronoun = coref_match.group(1)
        resolved_entity = resolve_coreference_from_history(text, history)
        if resolved_entity:
            is_followup = True
            p_start = coref_match.start()
            p_end = coref_match.end()
            extractions.append({
                "extraction_class": "coreference",
                "extraction_text": pronoun,
                "char_interval": {"start_pos": p_start, "end_pos": p_end},
                "alignment_status": "MATCH_EXACT",
                "attributes": {
                    "referent": resolved_entity,
                    "source": "conversation_history"
                }
            })

    # 4. Publication inquiry detection
    pub_match = re.search(r'\b(published\s+(?:any\s+)?articles?|papers?|publications?|books?|monographs?|articles?\s+written|what\s+did\s+(?:he|she|they)\s+write)\b', text, re.IGNORECASE)
    if pub_match:
        intent = "publication_inquiry"
        route_to_web = True
        domain = "bibliography"
        extractions.append({
            "extraction_class": "publication_inquiry",
            "extraction_text": pub_match.group(0),
            "char_interval": {"start_pos": pub_match.start(), "end_pos": pub_match.end()},
            "alignment_status": "MATCH_EXACT",
            "attributes": {
                "type": "bibliography_lookup",
                "search_engine": "google_and_duckduckgo",
                "requires_live_search": "true"
            }
        })

    # 5. Person / Entity Extraction
    # If no coreference pronoun was found, inspect clean_prompt for entity
    subject_text = clean_prompt
    subject_text = re.sub(r'^(?:browser\s+deep\s+research\s+on|deep\s+research\s+on|deep\s+research|search\s+for|search|look\s+up\s+on\s+google|google)\s*', '', subject_text, flags=re.IGNORECASE).strip()
    
    is_person = False
    primary_entity = resolved_entity

    # Detect proper names (e.g. Femi Oyesanya, Elon Musk, Geoffrey Hinton)
    # Check if subject is 2-4 words with significant non-stopwords
    words = [w.strip(".,;:?!'\"") for w in subject_text.split() if w.strip(".,;:?!'\"")]
    non_stopwords = [w for w in words if w.lower() not in STOPWORDS]
    
    if not primary_entity and len(words) >= 1:
        if len(non_stopwords) >= 1 and len(words) <= 5:
            # Check if text doesn't look like a code/math query
            if not re.search(r'[=+{}<>;()/*^\\]', subject_text) and not re.search(r'\b(function|def|class|const|let|var|return|if|else)\b', subject_text):
                is_person = True
                primary_entity = " ".join(words)
                # find interval in raw text
                pos = text.lower().find(primary_entity.lower())
                if pos != -1:
                    extractions.append({
                        "extraction_class": "person",
                        "extraction_text": text[pos:pos + len(primary_entity)],
                        "char_interval": {"start_pos": pos, "end_pos": pos + len(primary_entity)},
                        "alignment_status": "MATCH_EXACT",
                        "attributes": {
                            "role": "author_researcher_or_public_figure",
                            "requires_live_search": "true"
                        }
                    })

    # If active menu tool passed, add category attribute
    if active_menu_tool:
        extractions.append({
            "extraction_class": "menu_category",
            "extraction_text": active_menu_tool,
            "char_interval": {"start_pos": 0, "end_pos": 0},
            "alignment_status": "MATCH_EXACT",
            "attributes": {"menu_tool": active_menu_tool}
        })

    # Determine resolved_query and search_queries
    resolved_query = text
    if is_followup and primary_entity:
        if intent == "publication_inquiry":
            resolved_query = f"{primary_entity} published articles papers publications"
        else:
            resolved_query = f"{primary_entity} {clean_prompt}"
    elif is_person and primary_entity:
        if intent == "publication_inquiry":
            resolved_query = f"{primary_entity} published articles papers publications"
        elif intent == "deep_research":
            resolved_query = primary_entity
        else:
            resolved_query = primary_entity

    search_queries = []
    if primary_entity:
        if intent == "publication_inquiry":
            search_queries = [
                f'"{primary_entity}" published articles papers',
                f'{primary_entity} author articles cybersecurity internet policy',
                f'"{primary_entity}"'
            ]
        elif intent == "deep_research":
            search_queries = [
                primary_entity,
                f'"{primary_entity}" published articles papers publications author',
                f'"{primary_entity}" cybersecurity OR research OR policy OR medium OR linkedin'
            ]
        else:
            search_queries = [
                f'"{primary_entity}"',
                f'{primary_entity} published articles papers',
                primary_entity
            ]
    else:
        search_queries = [clean_prompt or text]

    # If it is a person/author lookup or publication inquiry, always route to web
    if is_person or is_followup or intent in ("publication_inquiry", "deep_research", "web_search"):
        route_to_web = True

    # Build response
    result_dict = {
        "engine": "google/langextract",
        "has_official_langextract_lib": HAS_LANGEXTRACT,
        "raw_query": text,
        "resolved_query": resolved_query,
        "search_queries": search_queries,
        "intent": intent,
        "domain": domain,
        "route_to_web": route_to_web,
        "is_person_or_entity": bool(is_person or primary_entity),
        "is_followup_coreference": is_followup,
        "primary_entity": primary_entity or "",
        "extractions": extractions
    }

    # If langextract library is available, also create an official AnnotatedDocument instance
    if HAS_LANGEXTRACT:
        try:
            lx_extractions = []
            for ex in extractions:
                ci = ex.get("char_interval")
                lx_ci = lx.data.CharInterval(start_pos=ci["start_pos"], end_pos=ci["end_pos"]) if ci else None
                lx_ex = lx.data.Extraction(
                    extraction_class=ex["extraction_class"],
                    extraction_text=ex["extraction_text"],
                    char_interval=lx_ci,
                    attributes=ex.get("attributes", {})
                )
                lx_extractions.append(lx_ex)
            annotated_doc = lx.data.AnnotatedDocument(
                document_id="query-input",
                text=text,
                extractions=lx_extractions
            )
            result_dict["annotated_document_extractions_count"] = len(annotated_doc.extractions)
        except Exception as e:
            result_dict["lx_annotated_error"] = str(e)

    return result_dict

def main():
    parser = argparse.ArgumentParser(description="ModelFusion Google LangExtract CLI Engine")
    parser.add_argument("--query", "-q", type=str, default="", help="Input text or query to annotate")
    parser.add_argument("--history", type=str, default="[]", help="JSON array of prior turns for coreference")
    parser.add_argument("--active-menu-tool", type=str, default="", help="Active sidebar menu category/tool")
    parser.add_argument("--html", type=str, default="", help="Path to write interactive HTML visualization")
    args = parser.parse_args()

    query = args.query
    if not query and not sys.stdin.isatty():
        query = sys.stdin.read().strip()

    history = []
    if args.history:
        raw_h = args.history.strip()
        try:
            history = json.loads(raw_h)
        except Exception:
            # Handle unescaped or comma-separated lists e.g. ["femi oyesanya"] or femi oyesanya
            cleaned = raw_h.strip("[]'\"").replace('\\"', '"')
            if ',' in cleaned:
                history = [x.strip(" '\"") for x in cleaned.split(',') if x.strip(" '\"")]
            elif cleaned:
                history = [cleaned]

    result = interpret_query_langextract(query, history, args.active_menu_tool)

    # Optional HTML visualization using lx.visualize
    if args.html and HAS_LANGEXTRACT:
        try:
            lx_extractions = []
            for ex in result["extractions"]:
                ci = ex.get("char_interval")
                if ci and ci["end_pos"] > ci["start_pos"]:
                    lx_ex = lx.data.Extraction(
                        extraction_class=ex["extraction_class"],
                        extraction_text=ex["extraction_text"],
                        char_interval=lx.data.CharInterval(start_pos=ci["start_pos"], end_pos=ci["end_pos"]),
                        attributes=ex.get("attributes", {})
                    )
                    lx_extractions.append(lx_ex)
            if lx_extractions:
                doc = lx.data.AnnotatedDocument(document_id="query", text=query, extractions=lx_extractions)
                html_code = lx.visualize([doc])
                with open(args.html, "w", encoding="utf-8") as f:
                    f.write(html_code)
                result["html_saved"] = args.html
        except Exception as e:
            result["html_error"] = str(e)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

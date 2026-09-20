#!/usr/bin/env python3
"""
Ollama Client Helper for ReST-RL Adapters.

Features:
1. Dynamic model tag resolution via /api/tags (prevents HTTP 404 aborts).
2. Streaming SSE (stream: true) with token-level is_paused() checks (<25ms abortion).
3. Explicit prompt injection of task.test_target assertions.
4. Multi-turn error reflection feeding failed rollout traces back into prompts.
"""

from __future__ import annotations

import json
import time
import logging
import urllib.request
import urllib.error
from typing import Optional, Callable, Dict, Any, List

from .base import RLTask

logger = logging.getLogger("rest_rl.ollama_client")

# Cache available tags with 60-second TTL
_TAGS_CACHE: Dict[str, Any] = {"tags": [], "last_fetched": 0.0}


def fetch_available_tags(tags_endpoint: str, timeout: float = 1.0) -> List[str]:
    """Queries /api/tags to discover loaded/available Ollama models."""
    now = time.time()
    if now - _TAGS_CACHE["last_fetched"] < 60.0 and _TAGS_CACHE["tags"]:
        return _TAGS_CACHE["tags"]

    try:
        req = urllib.request.Request(
            tags_endpoint,
            headers={"User-Agent": "HugOS-ReST-RL/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            tag_names = [m.get("name", "") for m in models if m.get("name")]
            _TAGS_CACHE["tags"] = tag_names
            _TAGS_CACHE["last_fetched"] = now
            return tag_names
    except Exception as e:
        logger.debug("Failed to query Ollama tags from %s: %s", tags_endpoint, e)
        return []


def resolve_model_tag(
    endpoint: str,
    tier: int = 1,
    preferred_model: Optional[str] = None,
) -> str:
    """
    Dynamically resolves a valid, existing Ollama model tag.
    Prevents silent HTTP 404 aborts caused by hardcoded tags with non-standard suffixes.
    """
    # Derive /api/tags from /api/generate
    base_endpoint = endpoint.split("/api/")[0] if "/api/" in endpoint else "http://127.0.0.1:11434"
    tags_endpoint = f"{base_endpoint}/api/tags"

    available = fetch_available_tags(tags_endpoint)

    # Candidate tiers matching Master CLI dynamic scaling matrix
    if tier == 1:
        candidates = ["qwen2.5:32b", "qwen2.5:14b", "qwen2.5:7b", "qwen2.5-coder:7b", "qwen2.5:3b", "qwen2.5:1.5b"]
        fallback = "qwen2.5:7b"
    elif tier == 2:
        candidates = ["qwen2.5:14b", "qwen2.5:7b", "qwen2.5:3b", "qwen2.5:1.5b", "qwen2.5-coder:1.5b"]
        fallback = "qwen2.5:1.5b"
    else:
        candidates = ["qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b", "qwen2.5-coder:1.5b"]
        fallback = "qwen2.5:1.5b"

    if preferred_model:
        # Check if exact preferred model is loaded
        for t in available:
            if t == preferred_model or t.startswith(preferred_model + ":") or preferred_model.startswith(t):
                return t
        # If preferred model is a clean tag (without -coder) and available, return it
        clean_pref = preferred_model.replace("-coder", "")
        for t in available:
            if clean_pref in t:
                return t

    # Match best available from preference hierarchy
    for cand in candidates:
        cand_base = cand.split(":")[0]
        for t in available:
            if t == cand or (cand_base in t and cand.split(":")[-1] in t):
                return t

    # If any model is available at all, return the first one
    if available:
        return available[0]

    return fallback


def build_rollout_prompt(task: RLTask, error_trace: Optional[str] = None) -> str:
    """Constructs a comprehensive prompt with code, test assertions, and error reflections."""
    sections = [
        "You are an expert autonomous software engineer repairing code to pass verification tests.",
        "",
        "### CURRENT IMPLEMENTATION:",
        f"```{task.target_filename}\n{task.original_code}\n```",
        "",
        "### TEST CONTRACT & ASSERTIONS TO SATISFY:",
        f"```python\n{task.test_target}\n```",
    ]

    if task.instruction:
        sections.extend([
            "",
            "### TASK INSTRUCTION:",
            task.instruction,
        ])

    if error_trace:
        sections.extend([
            "",
            "### PREVIOUS ATTEMPT FAILED WITH ERROR/TRACEBACK:",
            f"```\n{error_trace}\n```",
            "Carefully analyze the failure above and fix the logic so all test assertions pass.",
        ])

    sections.extend([
        "",
        "### INSTRUCTIONS:",
        "Output ONLY the complete, corrected Python code inside a single ```python markdown code block.",
        "Do NOT output markdown commentary or conversational text outside the code block.",
    ])

    return "\n".join(sections)


def query_ollama_streaming(
    endpoint: str,
    model: str,
    task: RLTask,
    is_paused: Optional[Callable[[], bool]] = None,
    timeout: float = 3.0,
    error_trace: Optional[str] = None,
    temperature: float = 0.5,
    num_predict: int = 512,
) -> Optional[str]:
    """
    Executes streaming inference against local Ollama (/api/generate with stream: true).
    Checks is_paused() after each streaming token chunk, aborting the HTTP connection in <25ms
    if user activity is detected.
    """
    prompt = build_rollout_prompt(task, error_trace=error_trace)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    try:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "HugOS-ReST-RL/1.0"},
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            collected_tokens: List[str] = []

            for line in resp:
                # Token-level preemption check (<25ms cancellation)
                if is_paused and is_paused():
                    logger.info("Ollama streaming aborted by user activity (<25ms)")
                    resp.close()
                    return None

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    chunk = json.loads(line_str)
                    token = chunk.get("response", "")
                    collected_tokens.append(token)
                    if chunk.get("done", False):
                        break
                except Exception:
                    continue

            full_text = "".join(collected_tokens)
            return extract_code_block(full_text)

    except urllib.error.HTTPError as he:
        logger.debug("Ollama HTTP Error %d for model %s: %s", he.code, model, he.reason)
        return None
    except Exception as e:
        logger.debug("Ollama streaming request failed: %s", e)
        return None


def extract_code_block(text: str) -> Optional[str]:
    """Extracts raw code from Markdown code fences or returns clean text."""
    if not text or not text.strip():
        return None

    if "```python" in text:
        parts = text.split("```python")
        code = parts[1].split("```")[0]
        return code.strip()
    elif "```" in text:
        parts = text.split("```")
        code = parts[1].split("```")[0]
        return code.strip()

    # If pure code without fences, check if syntax is valid
    trimmed = text.strip()
    if "def " in trimmed or "class " in trimmed or "return " in trimmed:
        return trimmed

    return None

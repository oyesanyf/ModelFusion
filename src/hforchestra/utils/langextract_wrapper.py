#!/usr/bin/env python3
"""
Centralized LangExtract invocation wrapper.
Defaults to GPT-5 nano via OpenAI; configurable via config/langextract_config.json
and environment variables. Minimal surface area change for callers.
"""

import os
import json
import io
import contextlib
from typing import Any, List, Optional


def _load_config() -> dict:
    config_path = os.path.join("config", "langextract_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Safe defaults
        return {
            "provider": "openai",
            "model_id": "gpt-5-nano",
            "api_key_env": "OPENAI_API_KEY",
            "fence_output": True,
            "use_schema_constraints": False,
            "disable_gemini": True,
        }


# Eagerly strip Gemini keys at module load time if config requires it.
# This prevents langextract from auto-initializing with Gemini.
_cfg = _load_config()


def extract_with_config(
    lx_module: Any,
    *,
    text_or_documents: Any,
    prompt_description: str,
    examples: Optional[List[Any]] = None,
    override_model_id: Optional[str] = None,
    override_api_key: Optional[str] = None,
    **kwargs,
) -> Any:
    """Centralized wrapper for langextract with config-driven model selection."""
    cfg = _cfg  # Use module-level config

    # Check if LangExtract is enabled
    if not cfg.get("enabled", True):
        # Return a mock result when disabled
        class MockResult:
            def __init__(self):
                self.extractions = []
                self.confidence = 0.0
        return MockResult()

    # Environment sanitization is now handled in core.env_setup at startup.
    # This wrapper now only needs to pass the correct arguments.

    provider = cfg.get("provider", "openai")
    model_id = override_model_id or os.getenv("LANGEXTRACT_MODEL_ID") or cfg.get("model_id")
    api_key_env = cfg.get("api_key_env")
    api_key = override_api_key or os.getenv(api_key_env) if api_key_env else None

    # Optional flags (safe defaults)
    fence_output = cfg.get("fence_output", True)
    use_schema_constraints = cfg.get("use_schema_constraints", False)

    # Defer to langextract; keep kwargs extensible
    verbose = os.getenv("HFORCH_LANGEXTRACT_VERBOSE", "false").lower() in ("1", "true", "yes")

    if os.getenv("HFORCH_DEBUG"):
        print(f"[DEBUG] LangExtract calling with provider={provider} model={model_id}")

    if verbose:
        return lx_module.extract(
            text_or_documents=text_or_documents,
            prompt_description=prompt_description,
            examples=examples or [],
            model_id=model_id,
            api_key=api_key,
            fence_output=fence_output,
            use_schema_constraints=use_schema_constraints,
            **kwargs,
        )

    # Silence verbose library prints
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        return lx_module.extract(
            text_or_documents=text_or_documents,
            prompt_description=prompt_description,
            examples=examples or [],
            model_id=model_id,
            api_key=api_key,
            fence_output=fence_output,
            use_schema_constraints=use_schema_constraints,
            **kwargs,
        )



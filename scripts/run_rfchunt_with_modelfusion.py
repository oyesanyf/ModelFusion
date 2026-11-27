#!/usr/bin/env python3
"""
ModelFusion <-> RFCHunt Local Abliterated Security Bridge (`scripts/run_rfchunt_with_modelfusion.py`).
=====================================================================================================
Runs allowlisted RFCHunt defensive workflows against the local ModelFusion HTTP server (:5000)
and Ollama (:11434) with strict loopback endpoint validation, <=400ms health probes,
process-scoped environment isolation (zero Registry/PATH mutation), and direct in-process
invocation of `revenue_cli.run_revenue_cli`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ALLOWED_SUBCOMMANDS: Tuple[str, ...] = (
    "fast-ooda",
    "ensemble-audit",
    "freshness-watch",
    "linux-poc",
    "eligibility-check",
    "h1-draft-stage",
    "check-drafts",
    "qa-drafts",
)

ABLITERATED_SECURITY_CATALOG: Tuple[Dict[str, object], ...] = (
    {
        "ollama_tag": "huihui_ai/foundation-sec-abliterated:8b",
        "role": "boundary_security_primary",
        "min_ram_gb": 5.5,
    },
    {
        "ollama_tag": "huihui_ai/qwen2.5-coder-abliterated:7b",
        "role": "protocol_code_auditor",
        "min_ram_gb": 5.5,
    },
    {
        "ollama_tag": "huihui_ai/gemma-3-12b-abliterated",
        "role": "reasoning_arbiter",
        "min_ram_gb": 8.0,
    },
    {
        "ollama_tag": "hf.co/bartowski/glm-4-9b-chat-abliterated-GGUF:Q4_K_M",
        "role": "glm4_9b_compact",
        "min_ram_gb": 6.0,
    },
    {
        "ollama_tag": "hf.co/byroneverson/glm-4-9b-chat-abliterated",
        "role": "glm4_9b_dense",
        "min_ram_gb": 6.0,
    },
    {
        "ollama_tag": "hf.co/byroneverson/LongWriter-glm4-9b-abliterated",
        "role": "longwriter_report",
        "min_ram_gb": 6.0,
    },
)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def validate_loopback_http_url(raw_url: str, fallback: str) -> str:
    """Restricts local daemon URLs to http/https on loopback hosts only."""
    candidate = str(raw_url or "").strip() or fallback
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise ValueError(f"Endpoint must be a loopback http/https URL, got: {candidate!r}")
    return candidate.rstrip("/")


def probe_http_fast(url: str, timeout_sec: float = 0.4) -> bool:
    """Fast <=400ms health probe so offline daemons never stall startup."""
    safe_url = validate_loopback_http_url(url, "http://127.0.0.1:5000")
    eff_timeout = min(max(float(timeout_sec), 0.05), 0.4)
    try:
        req = urllib.request.Request(safe_url, method="GET")
        with urllib.request.urlopen(req, timeout=eff_timeout) as resp:  # noqa: S310
            return 200 <= int(resp.status) < 500
    except Exception:
        return False


def discover_ollama_tags(ollama_endpoint: str, timeout_sec: float = 0.4) -> List[str]:
    base = validate_loopback_http_url(ollama_endpoint, "http://127.0.0.1:11434")
    url = f"{base}/api/tags"
    eff_timeout = min(max(float(timeout_sec), 0.05), 0.4)
    try:
        with urllib.request.urlopen(url, timeout=eff_timeout) as resp:  # noqa: S310
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return [
                    str(m.get("name"))
                    for m in (data.get("models") or [])
                    if isinstance(m, dict) and m.get("name")
                ]
    except Exception:
        pass
    return []


def build_scoped_env_vars(
    *,
    modelfusion_endpoint: str,
    ollama_endpoint: str,
    hugos_cdp_url: str,
    use_modelfusion_server: bool,
    preferred_model: Optional[str] = None,
) -> Dict[str, str]:
    mf_url = validate_loopback_http_url(modelfusion_endpoint, "http://127.0.0.1:5000")
    ol_url = validate_loopback_http_url(ollama_endpoint, "http://127.0.0.1:11434")
    cdp_url = validate_loopback_http_url(hugos_cdp_url, "http://127.0.0.1:9222")
    updates: Dict[str, str] = {
        "PYTHONIOENCODING": "utf-8",
        "MODELFUSION_ENDPOINT": mf_url,
        "RFCHUNT_USE_MODELFUSION": "1" if use_modelfusion_server else "0",
        "OLLAMA_ENDPOINT": ol_url,
        "LOCAL_OLLAMA_ENDPOINT": ol_url,
        "RFCHUNT_HUGOS_CDP_URL": cdp_url,
        "RFCHUNT_ENABLE_ANTI_JUNK_GUARD": "1",
    }
    if preferred_model and preferred_model.strip():
        updates["RFCHUNT_LLM_MODEL"] = preferred_model.strip()
        updates["LOCAL_MODEL"] = preferred_model.strip()
    return updates


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run RFCHunt defensive workflows on ModelFusion + local abliterated models."
    )
    parser.add_argument(
        "--rfchunt-root",
        default=os.environ.get("RFCHUNT_ROOT", r"d:\harfile\rfchunt"),
        help="Path to local RFCHunt repository root.",
    )
    parser.add_argument(
        "--modelfusion-endpoint",
        default=os.environ.get("MODELFUSION_ENDPOINT", "http://127.0.0.1:5000"),
        help="ModelFusion HTTP server base URL (default: http://127.0.0.1:5000).",
    )
    parser.add_argument(
        "--ollama-endpoint",
        default=os.environ.get("LOCAL_OLLAMA_ENDPOINT", "http://127.0.0.1:11434"),
        help="Local Ollama endpoint (default: http://127.0.0.1:11434).",
    )
    parser.add_argument(
        "--hugos-cdp-url",
        default=os.environ.get("RFCHUNT_HUGOS_CDP_URL", "http://127.0.0.1:9222"),
        help="HugOS Browser CDP endpoint for Draft-only HITL staging (default: http://127.0.0.1:9222).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Explicit abliterated Ollama model override (e.g. huihui_ai/foundation-sec-abliterated:8b).",
    )
    parser.add_argument(
        "--list-abliterated",
        action="store_true",
        help="Print the synchronized ModelFusion/RFCHunt abliterated catalog & live daemon status, then exit.",
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        choices=ALLOWED_SUBCOMMANDS,
        help="RFCHunt revenue_cli.py subcommand to execute.",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments forwarded verbatim to RFCHunt revenue_cli.py.",
    )

    ns = parser.parse_args(argv)
    mf_base = validate_loopback_http_url(ns.modelfusion_endpoint, "http://127.0.0.1:5000")
    ol_base = validate_loopback_http_url(ns.ollama_endpoint, "http://127.0.0.1:11434")
    mf_up = probe_http_fast(f"{mf_base}/health") or probe_http_fast(mf_base)
    installed_tags = discover_ollama_tags(ol_base)
    installed_abliterated = [
        t for t in installed_tags if "abliterat" in t.lower() or "obliterat" in t.lower() or "foundation-sec" in t.lower()
    ]

    if ns.list_abliterated or not ns.subcommand:
        summary = {
            "modelfusion_endpoint": mf_base,
            "modelfusion_server_reachable": mf_up,
            "ollama_endpoint": ol_base,
            "ollama_installed_count": len(installed_tags),
            "installed_abliterated_security_models": installed_abliterated,
            "catalog_count": len(ABLITERATED_SECURITY_CATALOG),
            "catalog": list(ABLITERATED_SECURITY_CATALOG),
        }
        print(json.dumps(summary, indent=2))
        return 0

    rfchunt_root = Path(ns.rfchunt_root).resolve()
    entry = rfchunt_root / "revenue_cli.py"
    if not entry.is_file():
        print(f"[ERROR] RFCHunt entrypoint not found: {entry}", file=sys.stderr)
        return 2

    forwarded = list(ns.extra_args or [])
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    env_updates = build_scoped_env_vars(
        modelfusion_endpoint=mf_base,
        ollama_endpoint=ol_base,
        hugos_cdp_url=ns.hugos_cdp_url,
        use_modelfusion_server=mf_up,
        preferred_model=ns.model,
    )
    saved_env = {k: os.environ.get(k) for k in env_updates}
    orig_cwd = os.getcwd()
    inserted_root = str(rfchunt_root) not in sys.path
    try:
        os.environ.update(env_updates)
        if inserted_root:
            sys.path.insert(0, str(rfchunt_root))
        os.chdir(str(rfchunt_root))
        spec = importlib.util.spec_from_file_location("rfchunt_revenue_cli", str(entry))
        if spec is None or spec.loader is None:
            print(f"[ERROR] Unable to load module spec from {entry}", file=sys.stderr)
            return 2
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return int(mod.run_revenue_cli([ns.subcommand, *forwarded]))
    finally:
        os.chdir(orig_cwd)
        if inserted_root and str(rfchunt_root) in sys.path:
            sys.path.remove(str(rfchunt_root))
        for k, prev in saved_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev


if __name__ == "__main__":
    raise SystemExit(main())

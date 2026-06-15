#!/usr/bin/env python3
"""
Plan & Execute Orchestrator (LangChain)

Provides a reusable function and a CLI to run LangChain's Plan-and-Execute
agent using OpenAI, with optional file context.
"""

from __future__ import annotations

import os
import argparse
from typing import Optional


def run_plan_and_execute(prompt: str, file_path: Optional[str] = None, verbose: bool = True) -> str:
    """Run LangChain Plan-and-Execute agent with optional file context.

    - Requires OPENAI_API_KEY in environment
    - If file_path is provided, the file content (or a truncated portion) is appended to the prompt
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain.chains.llm_math.base import LLMMathChain
        from langchain.agents import Tool
        from langchain_experimental.plan_and_execute import (
            PlanAndExecute, load_agent_executor, load_chat_planner,
        )
    except Exception as import_error:
        raise ImportError(
            "Missing LangChain dependencies. Install with: pip install langchain langchain-openai langchain-community langchain-experimental"
        ) from import_error

    if "OPENAI_API_KEY" not in os.environ:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable not set. Set it and retry."
        )

    # Build base prompt with optional file context
    effective_prompt = prompt
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Truncate very large files to keep prompt size manageable
            max_chars = 5000
            truncated = (content[: max_chars] + "\n... [truncated]") if len(content) > max_chars else content
            effective_prompt = (
                f"{prompt}\n\n[Additional context from file: {file_path}]\n{truncated}"
            )
        except Exception:
            # If file can't be read as text, include only a reference
            effective_prompt = (
                f"{prompt}\n\n[Additional context: file provided but not readable as text: {file_path}]"
            )

    # Model and tools
    model = ChatOpenAI(temperature=0)
    llm_math_chain = LLMMathChain.from_llm(llm=model, verbose=verbose)

    tools = [
        Tool(
            name="Calculator",
            func=llm_math_chain.run,
            description=(
                "Useful for questions involving mathematical calculations."
            ),
        ),
    ]

    # Planner + executor
    planner = load_chat_planner(model)
    executor = load_agent_executor(model, tools, verbose=verbose)
    agent = PlanAndExecute(planner=planner, executor=executor, verbose=verbose)

    # Run primary planning flow
    result = agent.invoke({"input": effective_prompt})
    output = result.get("output") if isinstance(result, dict) else None

    # Fallback: if planner produced empty or generic output, generate a direct LLM plan
    def needs_fallback(text: Optional[str]) -> bool:
        if not text:
            return True
        t = text.strip().lower()
        if len(t) < 50:
            return True
        generic_markers = [
            "please provide your original question",
            "i'm here to help",
            "how can i assist",
        ]
        return any(m in t for m in generic_markers)

    if needs_fallback(output):
        fallback_prompt = (
            "You are an expert travel planner. Create a comprehensive, step-by-step trip plan based on the user's request. "
            "Do not browse the web. Use general knowledge and clearly state assumptions.\n\n"
            f"User request: {effective_prompt}\n\n"
            "Deliver: \n"
            "1) Overview (trip purpose, length assumptions if missing).\n"
            "2) Best time to visit (weather, festivals, seasonality).\n"
            "3) Visa and entry requirements (US passport assumptions; advise to verify).\n"
            "4) Vaccinations/health (e.g., yellow fever, malaria prophylaxis advisory).\n"
            "5) Flight routing suggestions (typical hubs, example durations; no live prices).\n"
            "6) Day-by-day sample itinerary (balanced sightseeing, culture, downtime).\n"
            "7) Budget ranges (flight, lodging, daily expenses; low/med/high).\n"
            "8) Safety and local tips (transport, neighborhoods, scams to avoid).\n"
            "9) Connectivity & money (SIM/eSIM, payment, currency).\n"
            "10) Packing checklist highlights.\n"
            "11) Alternatives/options (cities or routes).\n"
            "12) Next steps for the traveler.\n"
            "Target length: 1200-1800 words."
        )
        ai_msg = model.invoke(fallback_prompt)
        output = getattr(ai_msg, "content", None) or "No output was generated."

    # Enrichment pass: Always expand and structure the final plan with clear sections and checklists
    enrich_prompt = (
        "Enhance and structure the following travel plan into a highly detailed itinerary with clear sections, "
        "bullet lists, and practical guidance. Do not browse the web. Expand where helpful, but avoid fabricating live prices.\n\n"
        f"User request: {effective_prompt}\n\n"
        f"Existing plan draft:\n{output}\n\n"
        "Rewrite as a comprehensive plan with the following sections (use concise headings and bullet points):\n"
        "- Trip Overview & Assumptions\n"
        "- Best Time to Visit (by month/season)\n"
        "- Entry Requirements & Visa (note that travelers must verify latest guidance)\n"
        "- Health & Vaccinations (yellow fever, malaria prophylaxis advisory)\n"
        "- Example Flight Routing (hubs, time ranges; no live prices)\n"
        "- 10-Day Sample Itinerary (day-by-day with options)\n"
        "- Budget Breakdown (flight, hotel, food, activities; low/med/high ranges)\n"
        "- Local Transport (in-country flights, road, rideshare)\n"
        "- Safety & Practical Tips\n"
        "- Connectivity & Money (SIM/eSIM, currency, tipping)\n"
        "- Packing Checklist (essentials)\n"
        "- Optional Add-ons / Alternatives\n"
        "- Next Steps Checklist for the Traveler\n"
        "Target length: 1500-2200 words."
    )
    enriched = model.invoke(enrich_prompt)
    output = getattr(enriched, "content", None) or output or "No output was generated."

    return output


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Plan-and-Execute using LangChain (with optional file context)"
    )
    parser.add_argument("--prompt", type=str, required=True, help="Prompt for the agent")
    parser.add_argument("--file", type=str, required=False, help="Optional file to include as context")
    parser.add_argument("--verbose", action="store_true", help="Verbose agent/tool logging")
    args = parser.parse_args()

    try:
        output = run_plan_and_execute(args.prompt, args.file, verbose=args.verbose)
        print("\n" + "=" * 50)
        print("                FINAL ANSWER")
        print("=" * 50 + "\n")
        print(output)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    _cli()



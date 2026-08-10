"""
Test Suite: Slash Command Extraction & False Positive Prevention
================================================================
Tests the server-side fast interception logic to ensure:
  1. Real user-typed slash commands ARE intercepted correctly.
  2. System XML context (customizationsUpdate, editorContext, etc.)
     containing paths like /mcp or /evolve do NOT trigger false positives.
  3. The /evolve command in particular does NOT return an MCP response.
  4. Compaction requests still get fast-intercepted.
"""

import urllib.request
import json
import time
import sys
import io

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


SERVER = "http://127.0.0.1:5000"

def safe_str(s):
    return s.encode('ascii', 'replace').decode('ascii')

def send_orchestrate(prompt, label=""):
    """Send a prompt to /orchestrate and return the response content."""
    url = f"{SERVER}/orchestrate"
    payload = {
        "prompt": prompt,
        "backend": "ollama",
        "device": "gpu",
        "budget": 7,
        "selection_strategy": "multi_objective",
        "fusion": False,
        "ollama": True,
        "gpu": True,
        "cpu": False,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            elapsed = (time.time() - start) * 1000
            # Response is HTTP chunked — strip chunk framing
            text = raw.decode('utf-8', errors='ignore').strip()
            # Try to parse as JSON
            try:
                obj = json.loads(text)
                content = obj.get("content", text)
            except json.JSONDecodeError:
                # May have chunk length prefixes — try stripping
                lines = text.split('\n')
                json_lines = [l for l in lines if l.strip().startswith('{')]
                if json_lines:
                    try:
                        obj = json.loads(json_lines[0])
                        content = obj.get("content", json_lines[0])
                    except:
                        content = text
                else:
                    content = text
            return True, content, elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, str(e), elapsed


def test_case(name, prompt, expect_contains=None, expect_not_contains=None):
    """Run a single test case and report pass/fail."""
    ok, content, ms = send_orchestrate(prompt, name)
    safe_content = safe_str(content[:200].replace('\n', ' '))

    passed = True
    reasons = []

    if not ok:
        passed = False
        reasons.append(f"HTTP error: {content}")
    else:
        if expect_contains:
            for ec in expect_contains:
                if ec.lower() not in content.lower():
                    passed = False
                    reasons.append(f"Expected '{ec}' not found in response")
        if expect_not_contains:
            for enc in expect_not_contains:
                if enc.lower() in content.lower():
                    passed = False
                    reasons.append(f"Unexpected '{enc}' found in response")

    status = "PASS" if passed else "FAIL"
    icon = "✅" if passed else "❌"
    print(f"  {icon} [{ms:7.1f}ms] {status} | {name}")
    if not passed:
        for r in reasons:
            print(f"              -> {r}")
    print(f"              -> Response: {safe_content}")
    return passed


# ═══════════════════════════════════════════════════════════════════
#  MAIN TEST EXECUTION
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 78)
    print("  SLASH COMMAND EXTRACTION TEST SUITE")
    print("  Tests fast interception, true positives, and false positives")
    print("=" * 78)

    results = []

    # ── Section 1: True Positive Tests ──────────────────────────────
    # User explicitly types a slash command. Server should intercept it.
    print("\n── Section 1: TRUE POSITIVE — User typed slash commands ──")

    results.append(test_case(
        "/stats — direct user command",
        "System: You are HugOS AI.\nUser: /stats",
        expect_contains=["database"],
    ))

    results.append(test_case(
        "/sysinfo — direct user command",
        "System: You are HugOS AI.\nUser: /sysinfo",
        expect_contains=["system", "hardware"],
    ))

    results.append(test_case(
        "/mcp — direct user command",
        "System: You are HugOS AI.\nUser: /mcp",
        expect_contains=["mcp", "engine"],
    ))

    results.append(test_case(
        "/evolve — direct user command",
        "System: You are HugOS AI.\nUser: /evolve",
        expect_contains=["evolve", "optimization"],
        expect_not_contains=["mcp engine"],
    ))

    results.append(test_case(
        "/keys — direct user command",
        "System: You are HugOS AI.\nUser: /keys",
        expect_contains=["api key"],
    ))

    results.append(test_case(
        "/tasks — direct user command",
        "System: You are HugOS AI.\nUser: /tasks",
        expect_contains=["task"],
    ))

    results.append(test_case(
        "/security — direct user command",
        "System: You are HugOS AI.\nUser: /security",
        expect_contains=["security"],
    ))

    results.append(test_case(
        "/refactor — direct user command",
        "System: You are HugOS AI.\nUser: /refactor",
        expect_contains=["refactor"],
    ))

    results.append(test_case(
        "/cache-stats — direct user command",
        "System: You are HugOS AI.\nUser: /cache-stats",
        expect_contains=["cache"],
    ))

    results.append(test_case(
        "/performance-stats — direct user command",
        "System: You are HugOS AI.\nUser: /performance-stats",
        expect_contains=["performance"],
    ))

    results.append(test_case(
        "/decision-stats — direct user command",
        "System: You are HugOS AI.\nUser: /decision-stats",
        expect_contains=["decision"],
    ))

    results.append(test_case(
        "unknown /invalidcmd — should show unknown message",
        "System: You are HugOS AI.\nUser: /invalidcmd",
        expect_contains=["unknown"],
    ))

    # ── Section 2: FALSE POSITIVE — System context & file paths ──
    print("\n── Section 2: FALSE POSITIVE — System context, file paths & URLs ──")

    # Simulate the exact VS Code prompt structure from the bug report
    evolve_with_system_context = (
        'You are an expert AI programming assistant, working with a user in the VS Code editor.\n'
        'When asked for your name, you must respond with "GitHub Copilot".\n'
        '\nuser: <environment_info>\nThe user\'s current OS is: Windows\n</environment_info>\n'
        '<workspace_info>\nI am working in a workspace with the following folders:\n- d:\\harfile\\test\n</workspace_info>\n'
        '<context>\nThe current date is 2026-07-29.\n'
        '<customizationsUpdate>\n'
        'The available instructions, skills, and agents have changed.\n'
        'Available agents: @agent with commands /mcp, /stats, /sysinfo, /keys, /tasks, /evolve, /security, /refactor\n'
        'src/vs/workbench/contrib/mcp/common/mcpRegistry.ts\n'
        'src/vs/workbench/contrib/chat/browser/aiCustomization/mcpListWidget.ts\n'
        '</customizationsUpdate>\n'
        '</context>\n'
        '<editorContext>\nThe user\'s current file is d:\\harfile\\test\\test-user-data\\temp_evolution\\initial_program.py.\n</editorContext>\n'
        '<reminderInstructions>\nDo not repeat instructions.\n</reminderInstructions>\n'
        '\nuser: @agent /evolve'
    )

    results.append(test_case(
        "/evolve with full VS Code context (BUG REPRO)",
        evolve_with_system_context,
        expect_contains=["evolve", "optimization"],
        expect_not_contains=["mcp engine"],
    ))

    # Test: system context has /mcp paths but user says "capital of India"
    plain_text_with_mcp_context = (
        'You are an expert AI programming assistant.\n'
        '\nuser: <context>\n'
        '<customizationsUpdate>\n'
        'Available: /mcp, /stats, /sysinfo, /keys, /tasks, /evolve, /security\n'
        'src/vs/workbench/contrib/mcp/common/mcpRegistry.ts\n'
        '</customizationsUpdate>\n'
        '</context>\n'
        '\nuser: capital of India'
    )

    results.append(test_case(
        "Plain question with /mcp in system context — should NOT intercept",
        plain_text_with_mcp_context,
        expect_not_contains=["mcp engine", "openevolve", "api key status", "security audit"],
    ))

    # Test: user mentions file path ending in .py
    results.append(test_case(
        "File path /mcp.py in query — should NOT intercept as /mcp",
        "System: You are HugOS AI.\nUser: Can you check the file /mcp.py for syntax errors?",
        expect_not_contains=["mcp engine"],
    ))

    # Test: user mentions directory path /src/vs/workbench/mcp/
    results.append(test_case(
        "Directory path /src/vs/mcp/ in query — should NOT intercept",
        "System: You are HugOS AI.\nUser: Look at /src/vs/workbench/mcp/registry.ts",
        expect_not_contains=["mcp engine"],
    ))

    # Test: system context has /mcp paths, user explicitly types /stats
    stats_with_mcp_context = (
        'You are an expert AI programming assistant.\n'
        '\nuser: <context>\n'
        '<customizationsUpdate>\n'
        'Available: /mcp, /evolve, /security\n'
        '</customizationsUpdate>\n'
        '</context>\n'
        '\nuser: /stats'
    )

    results.append(test_case(
        "/stats with /mcp in system context — should ONLY return stats",
        stats_with_mcp_context,
        expect_contains=["database"],
        expect_not_contains=["mcp engine", "openevolve"],
    ))

    # ── Section 3: Conversation compaction interception ─────────────
    print("\n── Section 3: COMPACTION — Background compaction fast path ──")

    compaction_prompt = (
        'Your task is to create a comprehensive, detailed summary of the entire conversation.\n'
        '\nuser: Summarize the conversation history so far.\n'
        'The following is a compressed version of the preceeding history in the current conversation.\n'
        '<user>\ncapital of India\n</user>\n'
        '<assistant>\nNew Delhi\n</assistant>'
    )

    results.append(test_case(
        "Compaction request — should fast-intercept",
        compaction_prompt,
        expect_contains=["summary"],
    ))

    # Test: @agent command with attachments block at the start of user message (EXACT BUG REPRO)
    attachments_with_agent_cmd = (
        'You are an expert AI programming assistant.\n'
        '\nuser: <attachments>\n'
        '<attachment id="file:import math.py">\n'
        'Excerpt from import math.py:\n'
        'import math\ndef sqrt(n): return math.sqrt(n)\n'
        '</attachment>\n'
        '</attachments>\n'
        '@agent /evolve'
    )

    results.append(test_case(
        "@agent /evolve with attachments block — should run evolve",
        attachments_with_agent_cmd,
        expect_contains=["evolve"],
    ))

    # Test: Prompt with attachments only (user attached code and invoked @agent without explicit slash cmd)
    attachments_only_prompt = (
        'You are an expert AI programming assistant.\n'
        '\nuser: <attachments>\n'
        '<attachment id="file:import math.py">\n'
        'User active selection:\n'
        'import math\n'
        '</attachment>\n'
        '</attachments>'
    )

    results.append(test_case(
        "User message starting with attachments — should NOT return empty fast interception",
        attachments_only_prompt,
        expect_not_contains=["Fast interception: Empty user prompt"],
    ))

    # ── Summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    icon = "✅" if failed == 0 else "❌"
    print(f"  {icon}  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 78)

    sys.exit(0 if failed == 0 else 1)

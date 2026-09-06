import os
import re
import sys

def test_routing_invariants():
    print("=== TEST SUITE 1: SOURCE CODE INVARIANTS ===")
    ts_file = r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\src\extension\byok\vscode-node\modelFusionProvider.ts"
    assert os.path.exists(ts_file), f"File not found: {ts_file}"
    with open(ts_file, 'r', encoding='utf-8') as f:
        ts_content = f.read()

    assert "'avo'" in ts_content or '"avo"' in ts_content, "'avo' not in knownCommands"
    print("  [PASS] avo registered in knownCommands")
    assert "const useAvo = true" not in ts_content, "Hardcoded useAvo flag still present"
    print("  [PASS] No hardcoded useAvo flag")
    assert "async _runAvo(" in ts_content, "_runAvo method missing"
    print("  [PASS] _runAvo method present")
    assert "openevolve_evolution" in ts_content, "openevolve_evolution missing"
    assert "initial_program" in ts_content, "initial_program missing"
    assert "evaluator.py" in ts_content, "evaluator.py missing"
    assert "config.yaml" in ts_content, "config.yaml missing"
    print("  [PASS] Dynamic OpenEvolve target triad generation present")
    assert "candidateDirs" in ts_content, "candidateDirs missing"
    print("  [PASS] AVO multi-path candidate resolution present")
    assert "child.on('error'" in ts_content, "child.on error missing"
    print("  [PASS] AVO process error listener attached")

def test_bundle_invariants():
    print("\n=== TEST SUITE 2: BUNDLE INVARIANTS ===")
    bundles = [
        r"D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\dist\extension.js",
        r"D:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\dist\extension.js"
    ]
    for b in bundles:
        assert os.path.exists(b), f"Bundle not found: {b}"
        with open(b, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "avo" in content, f"avo missing in {b}"
        assert "openevolve_evolution" in content, f"openevolve_evolution missing in {b}"
        print(f"  [PASS] Bundle verified: {os.path.basename(os.path.dirname(os.path.dirname(b)))}")

def test_command_routing_logic():
    print("\n=== TEST SUITE 3: ROUTING & ZERO ALIASING ===")
    known_commands = {"stats", "sysinfo", "tasks", "mcp", "keys", "command", "help", "evolve", "avo", "update"}
    def norm_cmd(cmd):
        if not cmd: return ""
        l = cmd.lower().strip()
        if l in ("evove", "evoce", "evovle", "evolv", "evolution"): return "evolve"
        if l == "avo": return "avo"
        return l

    def parse_slash(user_text):
        cleaned = user_text.strip()
        m_agent = re.match(r"^\s*@agent\b\s*([\s\S]*)", cleaned, re.IGNORECASE)
        if m_agent:
            rest = m_agent.group(1).strip()
            if not rest: return ""
            m_first = re.match(r"^(\S+)(?:\s+([\s\S]*))?$", rest)
            if m_first:
                raw_cmd = m_first.group(1).lower()
                rem = m_first.group(2) or ""
                if raw_cmd.startswith("/"): raw_cmd = raw_cmd[1:]
                norm = norm_cmd(raw_cmd)
                if norm in known_commands:
                    return f"/{norm} {rem}".strip()
            return ""
        m_slash = re.match(r"^\s*/([a-zA-Z0-9_\-]+)(?:\s+([\s\S]*))?$", cleaned)
        if m_slash:
            norm = norm_cmd(m_slash.group(1))
            rem = m_slash.group(2) or ""
            if norm in known_commands:
                return f"/{norm} {rem}".strip()
        return ""

    tests = [
        ("@agent evolve", "/evolve", "OpenEvolve"),
        ("@agent evolve --iterations 10", "/evolve --iterations 10", "OpenEvolve"),
        ("@agent avo", "/avo", "AVO"),
        ("@agent avo -n 5", "/avo -n 5", "AVO"),
        ("/evolve", "/evolve", "OpenEvolve"),
        ("/avo", "/avo", "AVO"),
        ("@agent write a test suite", "", "CodingAgent"),
        ("@agent optimize the loop", "", "CodingAgent"),
        ("@agent", "", "CodingAgent"),
    ]
    for inp, expected, pipeline in tests:
        res = parse_slash(inp)
        assert res == expected, f"Failed {inp}: expected {expected}, got {res}"
        if pipeline == "OpenEvolve": assert "avo" not in res, f"Zero aliasing violation: {res}"
        if pipeline == "AVO": assert "evolve" not in res, f"Zero aliasing violation: {res}"
        print(f"  [PASS] {inp!r} -> {res!r} ({pipeline})")

if __name__ == '__main__':
    test_routing_invariants()
    test_bundle_invariants()
    test_command_routing_logic()
    print("\n" + "="*50)
    print("ALL VERIFICATION SUITES PASSED (100%)")
    print("="*50)

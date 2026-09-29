#!/usr/bin/env python3
"""
ModelFusion MCP Server Artifacts Generator & Synchronizer
Connects to live target/release/cli.exe --mcp, extracts all 173 tools via MCP JSON-RPC 2.0,
and synchronizes:
  - mcp/mcp_tools.json
  - mcp/mcp_tools.csv
  - docs/screens/mcp_tools_explorer.html
  - <brain>/mcp_tools_explorer.html
  - <brain>/mcp_tools_catalog.md
  - mcp/tools_reference.md
  - <brain>/mcp_tools.json
  - <brain>/mcp_tools.csv
"""

import json
import os
import sys
import subprocess
import csv
import shutil
import re

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRAIN_DIR = r"C:\Users\oyesanyf\.gemini\antigravity\brain\b6ef927a-8ffc-4ecd-b7ed-90b470e8fc34"

CATEGORY_ORDER = [
    ("core", "Core Orchestration"),
    ("code", "Code Intelligence"),
    ("web", "Autonomous Browser & Research"),
    ("agent", "Autonomous Agents & Reasoning"),
    ("nlp", "NLP & Linguistics"),
    ("vision", "Computer Vision"),
    ("audio", "Audio & Speech"),
    ("multimodal", "Multi-Modal & Domain Sciences"),
    ("tabular", "ACDSO AutoML & Tabular Data"),
    ("pe_binary", "CyberSecurity & Binary Forensics"),
    ("system", "System Telemetry & Lifecycle"),
]

CATEGORY_KEY_TO_NAME = dict(CATEGORY_ORDER)


def query_mcp_tools():
    cli_bin = os.path.join(REPO_ROOT, "target", "release", "cli.exe")
    if not os.path.isfile(cli_bin):
        raise FileNotFoundError(f"CLI binary not found at {cli_bin}. Run cargo build --release --bin cli first.")

    print(f"[*] Connecting to live MCP server: {cli_bin} --mcp")
    proc = subprocess.Popen(
        [cli_bin, "--mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1
    )

    try:
        # Step 1: Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ModelFusion-ArtifactUpdater", "version": "1.0.0"}
            }
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        init_line = proc.stdout.readline()
        init_data = json.loads(init_line)
        server_info = init_data.get("result", {}).get("serverInfo", {})
        print(f" <- Initialized: {server_info.get('name')} v{server_info.get('version')}")

        # Step 2: Initialized notification
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        proc.stdin.flush()

        # Step 3: tools/list
        tools_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        proc.stdin.write(json.dumps(tools_req) + "\n")
        proc.stdin.flush()

        tools_line = proc.stdout.readline()
        tools_data = json.loads(tools_line)
        raw_tools = tools_data.get("result", {}).get("tools", [])

        print(f" <- Received {len(raw_tools)} tools from live MCP server.")
        return raw_tools
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


def generate_sample_call(tool, idx):
    props = tool.get("inputSchema", {}).get("properties", {})
    reqs = tool.get("inputSchema", {}).get("required", [])
    args = {}

    for r in reqs:
        p_info = props.get(r, {})
        p_type = p_info.get("type", "string")
        if p_type == "number":
            args[r] = 7.0
        elif p_type == "integer":
            args[r] = 5
        elif p_type == "boolean":
            args[r] = True
        elif p_type == "array":
            args[r] = ["--prompt", "sample argument"]
        else:
            desc = p_info.get("description", "")
            if "file" in r or "path" in r:
                args[r] = "src/main.rs"
            elif "task" in r:
                args[r] = "text-generation"
            elif "prompt" in r or "query" in r or "text" in r:
                args[r] = "Sample analysis instruction"
            else:
                args[r] = "sample_value"

    if not reqs and props:
        for k in list(props.keys())[:2]:
            p_info = props[k]
            p_type = p_info.get("type", "string")
            if p_type == "number":
                args[k] = 3.0
            elif p_type == "integer":
                args[k] = 1
            elif p_type == "boolean":
                args[k] = True
            elif p_type == "array":
                args[k] = ["sample"]
            else:
                args[k] = "sample"

    return {
        "jsonrpc": "2.0",
        "id": idx,
        "method": "tools/call",
        "params": {
            "name": tool["name"],
            "arguments": args
        }
    }


def update_artifacts():
    raw_tools = query_mcp_tools()
    assert len(raw_tools) == 173, f"Expected 173 tools, but got {len(raw_tools)}"

    # Build enriched tools list
    tools_list = []
    category_counts = {}
    for idx, t in enumerate(raw_tools, 1):
        raw_cat = t.get("category", "unknown")
        human_cat = CATEGORY_KEY_TO_NAME.get(raw_cat, raw_cat.replace("_", " ").title())
        category_counts[human_cat] = category_counts.get(human_cat, 0) + 1

        item = {
            "index": idx,
            "name": t["name"],
            "category": human_cat,
            "raw_category": raw_cat,
            "cmd": t.get("cmd", ""),
            "icon": t.get("icon", "🔧"),
            "label": t.get("label", t["name"]),
            "description": t.get("description", ""),
            "inputSchema": t.get("inputSchema", {})
        }
        tools_list.append(item)

    print("\n--- Category Breakdown ---")
    for key, human in CATEGORY_ORDER:
        cnt = category_counts.get(human, 0)
        print(f"  {human}: {cnt}")
    print(f"Total: {len(tools_list)} tools\n")

    # 1. Write mcp/mcp_tools.json
    mcp_json_path = os.path.join(REPO_ROOT, "mcp", "mcp_tools.json")
    with open(mcp_json_path, "w", encoding="utf-8") as f:
        json.dump(raw_tools, f, indent=2, ensure_ascii=False)
    print(f"[OK] Wrote {mcp_json_path} ({len(raw_tools)} tools)")

    # 2. Write mcp/mcp_tools.csv
    mcp_csv_path = os.path.join(REPO_ROOT, "mcp", "mcp_tools.csv")
    with open(mcp_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Index", "Name", "Category", "ParametersCount", "RequiredParameters", "Description"])
        for t in tools_list:
            props = t["inputSchema"].get("properties", {})
            reqs = t["inputSchema"].get("required", [])
            req_str = ", ".join(reqs) if reqs else "*None*"
            writer.writerow([
                t["index"],
                t["name"],
                t["category"],
                len(props),
                req_str,
                t["description"]
            ])
    print(f"[OK] Wrote {mcp_csv_path}")

    # 3. Update docs/screens/mcp_tools_explorer.html
    explorer_path = os.path.join(REPO_ROOT, "docs", "screens", "mcp_tools_explorer.html")
    with open(explorer_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(r'\b\d{3}-Tool Interactive Explorer\b', '173-Tool Interactive Explorer', html)
    html = re.sub(r'catalog of \d{3} high-performance tools', 'catalog of 173 high-performance tools', html)
    html = re.sub(r'Total Tools: <strong>\d{3}</strong>', 'Total Tools: <strong>173</strong>', html)
    html = re.sub(r'Showing: <strong id="lbl-count">\d{3}</strong>', 'Showing: <strong id="lbl-count">173</strong>', html)
    html = re.sub(r'<button class="cat-btn active" data-cat="all">All \(\d{3}\)</button>', '<button class="cat-btn active" data-cat="all">All (173)</button>', html)

    # Format JSON payload for TOOLS_DATA in HTML
    tools_for_html = []
    for t in tools_list:
        tools_for_html.append({
            "name": t["name"],
            "index": t["index"],
            "category": t["category"],
            "cmd": t["cmd"],
            "icon": t["icon"],
            "label": t["label"],
            "description": t["description"],
            "inputSchema": t["inputSchema"]
        })

    prefix = "const TOOLS_DATA = "
    idx1 = html.find(prefix)
    if idx1 == -1:
        raise ValueError("Could not find 'const TOOLS_DATA = ' in explorer HTML")
    idx2 = html.find(";\n", idx1)
    if idx2 == -1:
        idx2 = html.find(";\r\n", idx1)

    new_tools_json = json.dumps(tools_for_html, ensure_ascii=False)
    html = html[:idx1 + len(prefix)] + new_tools_json + html[idx2:]

    with open(explorer_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Updated {explorer_path} with 173 tools")

    # 4. Mirror explorer to brain
    os.makedirs(BRAIN_DIR, exist_ok=True)
    brain_explorer_path = os.path.join(BRAIN_DIR, "mcp_tools_explorer.html")
    shutil.copy2(explorer_path, brain_explorer_path)
    print(f"[OK] Mirrored explorer to {brain_explorer_path}")

    # Mirror JSON & CSV to brain
    shutil.copy2(mcp_json_path, os.path.join(BRAIN_DIR, "mcp_tools.json"))
    shutil.copy2(mcp_csv_path, os.path.join(BRAIN_DIR, "mcp_tools.csv"))
    print(f"[OK] Mirrored JSON and CSV to brain directory")

    # 5. Generate C:\Users\oyesanyf\.gemini\antigravity\brain\b6ef927a-8ffc-4ecd-b7ed-90b470e8fc34\mcp_tools_catalog.md
    brain_catalog_path = os.path.join(BRAIN_DIR, "mcp_tools_catalog.md")
    catalog_md = generate_catalog_markdown(tools_list, category_counts)
    with open(brain_catalog_path, "w", encoding="utf-8") as f:
        f.write(catalog_md)
    print(f"[OK] Wrote {brain_catalog_path} (full 173-tool catalog, {len(catalog_md.splitlines())} lines)")

    # 6. Generate mcp/tools_reference.md
    ref_path = os.path.join(REPO_ROOT, "mcp", "tools_reference.md")
    ref_md = generate_tools_reference(tools_list, category_counts)
    with open(ref_path, "w", encoding="utf-8") as f:
        f.write(ref_md)
    print(f"[OK] Wrote {ref_path} (full 173-tool reference manual, {len(ref_md.splitlines())} lines)")

    print("\n[SUCCESS] All 173-tool MCP artifacts generated and synchronized successfully!")


def generate_catalog_markdown(tools_list, category_counts):
    lines = [
        "# ModelFusion MCP Server • 173-Tool Master Catalog",
        '> **Specification**: Model Context Protocol (MCP) `protocolVersion: "2024-11-05"`  ',
        '> **Transport**: Standard JSON-RPC 2.0 over `stdio` (`target/release/cli.exe --mcp`)  ',
        '> **Total Registered Tools**: **173** across 11 functional domains  ',
        '> **Machine-Readable Exports**: [`mcp/mcp_tools.json`](file:///d:/harfile/ModelFusion/mcp/mcp_tools.json) • [`mcp/mcp_tools.csv`](file:///d:/harfile/ModelFusion/mcp/mcp_tools.csv) • [Interactive HTML Explorer](file:///d:/harfile/ModelFusion/docs/screens/mcp_tools_explorer.html)',
        "",
        "---",
        "",
        "## 📊 Master Tool Index (173 Tools)",
        "",
        "| # | Tool Name | Functional Domain | Params | Required | Primary Use Case |",
        "| :-: | :--- | :--- | :-: | :--- | :--- |",
    ]

    for t in tools_list:
        props = t["inputSchema"].get("properties", {})
        reqs = t["inputSchema"].get("required", [])
        req_str = f"`{', '.join(reqs)}`" if reqs else "*None*"
        desc_short = t["description"].split(".")[0].replace("|", "-")
        if len(desc_short) > 85:
            desc_short = desc_short[:82] + "..."
        lines.append(f"| {t['index']} | [`{t['name']}`](#{t['name']}) | **{t['category']}** | {len(props)} | {req_str} | {desc_short} |")

    lines.extend([
        "",
        "---",
        "",
        "## 🛠️ Complete Functional Specifications & Schema Reference",
        ""
    ])

    for key, human in CATEGORY_ORDER:
        group_tools = [t for t in tools_list if t["raw_category"] == key]
        lines.extend([
            f"### {human} ({len(group_tools)} Tools)",
            ""
        ])

        for t in group_tools:
            props = t["inputSchema"].get("properties", {})
            reqs = t["inputSchema"].get("required", [])
            req_str = f"`{', '.join(reqs)}`" if reqs else "*None*"

            lines.extend([
                f"#### `{t['name']}`",
                f"**Description**: {t['description']}",
                "",
                f"- **Tool Index**: #{t['index']}",
                f"- **Category**: {t['category']}",
                f"- **CLI Command Alias**: `{t['cmd'].strip()}`" if t['cmd'] else "",
                f"- **Required Parameters**: {req_str}",
                "",
                "**Parameters**:",
                "",
                "| Parameter | Type | Required | Description |",
                "| :--- | :--- | :-: | :--- |"
            ])

            if not props:
                lines.append("| *(none)* | `void` | ❌ No | No arguments required |")
            else:
                for p_name, p_val in props.items():
                    p_type = p_val.get("type", "string")
                    is_req = "✅ Yes" if p_name in reqs else "❌ No"
                    p_desc = p_val.get("description", "").replace("|", "-")
                    lines.append(f"| `{p_name}` | `{p_type}` | {is_req} | {p_desc} |")

            sample_call = generate_sample_call(t, t["index"])
            lines.extend([
                "",
                "<details>",
                "<summary><b>View JSON-RPC 2.0 Call Example</b></summary>",
                "",
                "```json",
                json.dumps(sample_call, indent=2, ensure_ascii=False),
                "```",
                "</details>",
                "",
                "---",
                ""
            ])

    return "\n".join(lines)


def generate_tools_reference(tools_list, category_counts):
    lines = [
        "# ModelFusion MCP Server • Tools Reference Manual",
        "",
        "The **ModelFusion Model Context Protocol (MCP) Server** exposes **173 specialized tools** over standard JSON-RPC 2.0 stdio (`protocolVersion: \"2024-11-05\"`). These tools connect frontier desktop assistants (Claude Desktop, Cursor, Google Antigravity, VS Code, Zed) to ModelFusion's local multi-modal engine, ACDSO Pareto AutoML, ReST-RL preemption, and 2M+ model catalog.",
        "",
        "---",
        "",
        "## 📑 Table of Contents",
    ]

    for num, (key, human) in enumerate(CATEGORY_ORDER, 1):
        count = category_counts.get(human, 0)
        anchor = re.sub(r'[^a-z0-9\-]', '', human.lower().replace(" ", "-").replace("&", "").replace("/", ""))
        lines.append(f"{num}. [{human} ({count} Tools)](#{num}-{anchor})")

    lines.extend([
        "",
        "---",
        ""
    ])

    for num, (key, human) in enumerate(CATEGORY_ORDER, 1):
        group_tools = [t for t in tools_list if t["raw_category"] == key]
        anchor = re.sub(r'[^a-z0-9\-]', '', human.lower().replace(" ", "-").replace("&", "").replace("/", ""))
        lines.extend([
            f"## {num}. {human}",
            ""
        ])

        for t in group_tools:
            lines.extend([
                f"### `{t['name']}`",
                f"* **Label**: {t['label']} {t['icon']}",
                f"* **Category**: {human}",
                f"* **Description**: {t['description']}",
                f"* **CLI Equivalent**: `{t['cmd'].strip()}`" if t['cmd'] else "",
                f"* **Input Schema**:",
                "  ```json",
                "  " + json.dumps(t["inputSchema"], indent=2, ensure_ascii=False).replace("\n", "\n  "),
                "  ```",
                f"* **Example Call**:",
                "  ```json",
                "  " + json.dumps(generate_sample_call(t, t["index"]), indent=2, ensure_ascii=False).replace("\n", "\n  "),
                "  ```",
                "",
                "---",
                ""
            ])

    return "\n".join(lines)


if __name__ == "__main__":
    update_artifacts()

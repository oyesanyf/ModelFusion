import json
import re

with open(r'D:\harfile\ModelFusion\.agents\explorer_2\tools_extracted.json', 'r', encoding='utf-8') as f:
    tools = json.load(f)

with open(r'D:\harfile\ModelFusion\crates\cli\src\main.rs', 'r', encoding='utf-8') as f:
    main_rs = f.read()

# Locate match name in tools/call
call_start = main_rs.find('let result_text = match name {')
call_end = main_rs.find('let response = serde_json::json!({', call_start)
call_block = main_rs[call_start:call_end]

# Find all explicitly handled arms in match name
explicit_arms = re.findall(r'"([^"]+)"\s*=>', call_block)
has_other_fallback = "other =>" in call_block or "_ =>" in call_block

print(f"Total tools in tools/list: {len(tools)}")
print(f"Explicit match arms in tools/call: {len(explicit_arms)}")
print(f"Explicit arms list: {explicit_arms}")
print(f"Has catch-all fallback arm: {has_other_fallback}")

# Check which tools are handled explicitly vs fallback
explicit_set = set(explicit_arms)
fallback_tools = []
unhandled_tools = []

for t in tools:
    tname = t["name"]
    if tname in explicit_set:
        pass
    elif has_other_fallback:
        fallback_tools.append(tname)
    else:
        unhandled_tools.append(tname)

print(f"\nExplicitly handled tools count: {len(explicit_set)}")
print(f"Fallback handled tools count: {len(fallback_tools)}")
print(f"Unhandled tools count: {len(unhandled_tools)}")
if unhandled_tools:
    print(f"Unhandled tools: {unhandled_tools}")

print("\n--- Fallback handler details ---")
print("Fallback matches on 'other' and runs:")
print("  flag_name = other.replace('_', '-')")
print("  cmd_args = vec![format!('--{}', flag_name)]")
print("  extracts: text/prompt/input -> --prompt <text>")
print("  extracts: file -> --file <file>")
print("  extracts: language -> --language <lang>")
print("  extracts: gpu -> --gpu")
print("  runs: run_cli_subcommand(&cmd_args, &db_path_resolved).await")


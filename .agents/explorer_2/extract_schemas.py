import json
import re

with open(r'D:\harfile\ModelFusion\crates\cli\src\main.rs', 'r', encoding='utf-8') as f:
    content = f.read()

# Locate "tools": [ ... ]
start = content.find('"tools": [')
if start == -1:
    print("Could not find tools array")
    exit(1)

# Find matching closing bracket
pos = start + len('"tools": [')
bracket_depth = 1
tools_json_str = "["
while pos < len(content) and bracket_depth > 0:
    char = content[pos]
    if char == '[':
        bracket_depth += 1
    elif char == ']':
        bracket_depth -= 1
    tools_json_str += char
    pos += 1

try:
    tools = json.loads(tools_json_str)
    print(f"Successfully parsed {len(tools)} tools from main.rs JSON")
    with open(r'D:\harfile\ModelFusion\.agents\explorer_2\tools_extracted.json', 'w', encoding='utf-8') as out:
        json.dump(tools, out, indent=2)
except Exception as e:
    print(f"Error parsing JSON: {e}")
    # Try alternate parse

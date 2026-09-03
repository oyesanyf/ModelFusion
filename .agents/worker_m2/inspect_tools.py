import json

with open(r'D:\harfile\ModelFusion\.agents\explorer_2\tools_extracted.json', 'r', encoding='utf-8') as f:
    tools = json.load(f)

print(f"Total tools: {len(tools)}")
for i, t in enumerate(tools):
    name = t.get("name")
    req = t.get("inputSchema", {}).get("required", [])
    props = list(t.get("inputSchema", {}).get("properties", {}).keys())
    desc = t.get("description", "")[:60]
    print(f"{i+1:02d}. {name:<32} required={req} props={props}")

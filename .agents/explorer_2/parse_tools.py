import re
import json

with open(r'D:\harfile\ModelFusion\crates\cli\src\main.rs', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract tools array from tools/list response
start_idx = text.find('"tools": [')
end_idx = text.find(']\n\n                }', start_idx)
if end_idx == -1:
    end_idx = text.find(']\r\n\r\n                }', start_idx)
if end_idx == -1:
    end_idx = text.find(']', start_idx)

# Find all tool definitions
tools_block = text[start_idx:end_idx+1]
names = re.findall(r'"name":\s*"([^"]+)"', tools_block)
print(f"Total tools in tools/list: {len(names)}")
for i, name in enumerate(names, 1):
    print(f"{i:2d}. {name}")

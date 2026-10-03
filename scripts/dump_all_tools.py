import re
import json

with open('browser/ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

categories_blocks = re.findall(r'<div class="tool-category">(.*?)</div>\s*</div>', content, re.DOTALL)
tools_by_cat = {}
all_tools_list = []
total = 0

for cat_block in categories_blocks:
    title_match = re.search(r'class="cat-title">([^<]+)</span>', cat_block)
    cat_title = title_match.group(1).strip() if title_match else 'Unknown'
    
    # Match button tags
    btn_matches = re.finditer(r'<button\s+([^>]*class="[^"]*tool-item-btn[^"]*"[^>]*)>(.*?)</button>', cat_block, re.DOTALL)
    items = []
    for bm in btn_matches:
        attrs = bm.group(1)
        inner = bm.group(2)
        
        lbl_m = re.search(r'class="tool-label">([^<]+)</span>', inner)
        lbl = lbl_m.group(1).strip() if lbl_m else 'NoLabel'
        
        tag_m = re.search(r'class="tool-tag">([^<]+)</span>', inner)
        tag = tag_m.group(1).strip() if tag_m else ''
        
        cmd_m = re.search(r'data-cmd="([^"]*)"', attrs)
        data_cmd = cmd_m.group(1) if cmd_m else ''
        
        id_m = re.search(r'id="([^"]*)"', attrs)
        btn_id = id_m.group(1) if id_m else ''
        
        onclick_m = re.search(r'onclick="([^"]*)"', attrs)
        onclick = onclick_m.group(1) if onclick_m else ''
        
        tool_id_m = re.search(r'data-tool-id="([^"]*)"', attrs)
        tool_id = tool_id_m.group(1) if tool_id_m else ''
        
        item = {
            'category': cat_title,
            'label': lbl,
            'tag': tag,
            'data_cmd': data_cmd,
            'id': btn_id,
            'tool_id': tool_id,
            'onclick': onclick
        }
        items.append(item)
        all_tools_list.append(item)
        
    tools_by_cat[cat_title] = items
    total += len(items)

print(f'Total tools found: {total}')
for cat, items in tools_by_cat.items():
    print(f'\n=== {cat} ({len(items)} items) ===')
    for it in items:
        action = it['data_cmd'] or it['onclick'] or it['id']
        print(f'  - [{it["label"]}] ({it["tag"]}) => {action}')

with open('IDE/reports/tools_dump.json', 'w', encoding='utf-8') as out:
    json.dump({'total': total, 'categories': tools_by_cat, 'all_tools': all_tools_list}, out, indent=2)

import re

with open('browser/ui/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Check for any fetch with bare /api or /health
matches = list(re.finditer(r'fetch\s*\(\s*([\'\"`])(\/(?:api|health)[^\'\"`]*?)\1', text))
print(f"Found {len(matches)} bare /api or /health fetches:")
for m in matches:
    line_num = text[:m.start()].count('\n') + 1
    print(f"  Line {line_num}: {m.group(0)}")

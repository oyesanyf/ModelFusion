import re

with open('browser/ui/index.html', encoding='utf-8') as f:
    content = f.read()

for m in re.finditer(r'data-category="([^"]+)"', content):
    print('Category attr:', m.group(1))

# Check for jobs tools
for line in content.splitlines():
    if 'apply-jobs' in line or 'tool_jobs' in line or 'job' in line.lower() and 'button' in line:
        print('Tool line:', line.strip())

import re

with open(r'crates/cli/src/main.rs', 'r', encoding='utf-8') as f:
    code = f.read()

start = code.find('pub fn canonicalize_command')
end = code.find('pub fn detect_natural_language_research', start)
canon_fn = code[start:end]

lines = [l.strip() for l in canon_fn.split('\n') if '=> Some(' in l]
mapped = {}
for line in lines:
    lhs, rhs = line.split('=>')
    m_canonical = re.search(r'Some\("([^"]+)"\)', rhs)
    if not m_canonical:
        continue
    canonical = m_canonical.group(1)
    keys = re.findall(r'"([a-z0-9]+)"', lhs)
    for k in keys:
        mapped[k] = canonical

print(f'Total mapped keys in canonicalize_command: {len(mapped)}')

from check_flags import help_flags

missing = []
for flag in help_flags:
    k = re.sub(r'[^a-z0-9]', '', flag.lower())
    if k not in mapped:
        missing.append((flag, k))

print('Missing help flags in mapped:', missing)
if not missing:
    print('ALL 159 FLAGS ARE MAPPED IN canonicalize_command!')

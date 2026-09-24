import os
import re

with open('IDE/HugOS.wxs', 'r', encoding='utf-8') as f:
    c = f.read()

files = re.findall(r'<File Id="fil_\d+" Source="([^"]+)"', c)
print(f'Total files in wxs: {len(files)}')

missing = []
total_bytes = 0
for f in files:
    full = os.path.join('IDE', f)
    if not os.path.isfile(full):
        missing.append(f)
    else:
        total_bytes += os.path.getsize(full)

print(f'Missing files: {len(missing)}')
if missing:
    print('Sample missing:', missing[:5])
print(f'Total uncompressed payload size: {total_bytes / (1024*1024):.2f} MB')

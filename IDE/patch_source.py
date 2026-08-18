import json, os, re

cmds = ['stats', 'sysinfo', 'tasks', 'security', 'refactor', 'doc', 'dataanalyst', 'datascience', 'jupyter', 'pe-header-extraction', 'export-pdf', 'decision-stats', 'performance-stats', 'cache-stats', 'code-vulnerability-detection', 'score', 'judge', 'plan', 'context-auto', 'context', 'debug', 'delegation', 'enable-ml', 'error', 'full', 'innovate', 'ml-analytics', 'ml-learning', 'update', 'restore', 'clearcache', 'ml-retrain', 'search-query', 'demo-hyde', 'add-documents', 'model-ranking', 'model-recommendations', 'analytics-demo']

# 1. Patch package.json
pkg_path = r'd:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json'
print(f'Patching {pkg_path}')
with open(pkg_path, 'r', encoding='utf-8') as f:
    pkg = json.load(f)

changed = False
for p in pkg.get('contributes', {}).get('chatParticipants', []):
    if 'commands' in p:
        existing = {c['name']: c for c in p['commands']}
        for cmd in cmds:
            if cmd not in existing:
                p['commands'].append({'name': cmd, 'description': f'ModelFusion /{cmd} command'})
                changed = True

if changed:
    with open(pkg_path, 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=4)
    print(f'Updated {pkg_path}')
else:
    print(f'No changes needed for {pkg_path}')

# 2. Patch constants.ts
const_path = r'd:\harfile\ModelFusion\IDE\vscode\extensions\copilot\src\extension\common\constants.ts'
print(f'Patching {const_path}')
with open(const_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the agentsToCommands block, specifically Intent.Agent
# export const agentsToCommands...
# [Intent.Agent]: {
m = re.search(r'\[Intent\.Agent\]:\s*\{([^}]+)\}', content)
if m:
    agent_block = m.group(1)
    existing_cmds = set(re.findall(r"'([a-zA-Z0-9_-]+)'\s*:", agent_block))
    
    additions = []
    for cmd in cmds:
        if cmd not in existing_cmds:
            additions.append(f"\t\t'{cmd}': Intent.Agent,")
    
    if additions:
        new_agent_block = agent_block.rstrip() + "\n" + "\n".join(additions) + "\n\t"
        content = content.replace(m.group(1), new_agent_block)
        with open(const_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {const_path} with {len(additions)} commands')
    else:
        print(f'No changes needed for {const_path}')

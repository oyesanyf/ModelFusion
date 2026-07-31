import glob, os, json, re

cmds = ['evolve', 'stats', 'sysinfo', 'sys-info', 'tasks', 'security', 'refactor', 'doc', 'dataanalyst', 'datascience', 'jupyter', 'pe-header-extraction', 'export-pdf', 'decision-stats', 'performance-stats', 'cache-stats', 'code-vulnerability-detection', 'score', 'judge', 'plan', 'context-auto', 'context', 'debug', 'delegation', 'enable-ml', 'error', 'full', 'innovate', 'ml-analytics', 'ml-learning', 'update', 'restore', 'clearcache', 'ml-retrain', 'search-query', 'demo-hyde', 'add-documents', 'model-ranking', 'model-recommendations', 'analytics-demo']

# 1. Update package.json in BOTH folders
base_dirs = [
    r'd:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64'
]

for base_dir in base_dirs:
    for pkg_path in glob.glob(os.path.join(base_dir, '**', 'extensions', 'copilot', 'package.json'), recursive=True):
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

# 2. Update x4 in extension.js
for base_dir in base_dirs:
    for ext_path in glob.glob(os.path.join(base_dir, '**', 'extensions', 'copilot', 'dist', 'extension.js'), recursive=True):
        print(f'Patching {ext_path}')
        with open(ext_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        m = re.search(r'x4=\{editAgent:\{([^\}]+)\},vscode:\{', content)
        if m:
            edit_agent_str = m.group(1)
            # Find what is already there
            existing_cmds = re.findall(r'([a-zA-Z0-9_-]+):\"editAgent\"', edit_agent_str)
            existing_cmds = set(existing_cmds)
            
            additions = []
            for cmd in cmds:
                # Need to quote the key if it has hyphens
                key = f'\"{cmd}\"' if '-' in cmd else cmd
                if cmd not in existing_cmds and f'\"{cmd}\"' not in edit_agent_str and f'{cmd}:' not in edit_agent_str:
                    additions.append(f'{key}:\"editAgent\"')
            
            if additions:
                new_edit_agent_str = edit_agent_str + ',' + ','.join(additions)
                content = content.replace(f'editAgent:{{{edit_agent_str}}}', f'editAgent:{{{new_edit_agent_str}}}')
                with open(ext_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Updated x4 in {ext_path} with {len(additions)} commands')

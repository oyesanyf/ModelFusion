import json
cmds = ['comment', 'comments', 'command', 'commands', 'help', 'stats', 'sysinfo', 'tasks', 'security', 'refactor', 'doc', 'dataanalyst', 'datascience', 'jupyter', 'pe-header-extraction', 'export-pdf', 'decision-stats', 'performance-stats', 'cache-stats', 'code-vulnerability-detection', 'score', 'judge', 'plan', 'context-auto', 'context', 'debug', 'delegation', 'enable-ml', 'error', 'full', 'innovate', 'ml-analytics', 'ml-learning', 'update', 'restore', 'clearcache', 'ml-retrain', 'search-query', 'demo-hyde', 'add-documents', 'model-ranking', 'model-recommendations', 'analytics-demo']

pkgs = [
    r'd:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json'
]

for pkg_path in pkgs:
    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg = json.load(f)
        
        changed = False
        participants = pkg.get('contributes', {}).get('chatParticipants', [])
        for p in participants:
            if 'commands' in p:
                existing = {c['name']: c for c in p['commands']}
                added_count = 0
                for cmd in cmds:
                    if cmd not in existing:
                        p['commands'].append({'name': cmd, 'description': f'ModelFusion /{cmd} command'})
                        changed = True
                        added_count += 1
                if added_count > 0:
                    name = p.get('name', 'Unknown')
                    print(f'Added {added_count} commands to participant {name}')
        if changed:
            with open(pkg_path, 'w', encoding='utf-8') as f:
                json.dump(pkg, f, indent=4)
            print(f'Patched {pkg_path}')
        else:
            print(f'No changes needed for {pkg_path}')
    except Exception as e:
        print(f'Error reading {pkg_path}: {e}')

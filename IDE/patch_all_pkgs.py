import json, os, copy

cmds = ['stats', 'sysinfo', 'tasks', 'security', 'refactor', 'doc', 'dataanalyst', 'datascience', 'jupyter', 'pe-header-extraction', 'export-pdf', 'decision-stats', 'performance-stats', 'cache-stats', 'code-vulnerability-detection', 'score', 'judge', 'plan', 'context-auto', 'context', 'debug', 'delegation', 'enable-ml', 'error', 'full', 'innovate', 'ml-analytics', 'ml-learning', 'update', 'restore', 'clearcache', 'ml-retrain', 'search-query', 'demo-hyde', 'add-documents', 'model-ranking', 'model-recommendations', 'analytics-demo']

command_objs = [{'name': c, 'description': f'ModelFusion /{c} command'} for c in cmds]

def patch_pkg(pkg_path):
    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg = json.load(f)
        
        changed = False
        participants = pkg.get('contributes', {}).get('chatParticipants', [])
        for p in participants:
            if 'commands' in p:
                existing = {c['name']: c for c in p['commands']}
                for cmd in command_objs:
                    if cmd['name'] not in existing:
                        p['commands'].append(copy.deepcopy(cmd))
                        changed = True
        
        if changed:
            with open(pkg_path, 'w', encoding='utf-8') as f:
                json.dump(pkg, f, indent=4)
            print(f'Patched {pkg_path}')
    except Exception as e:
        pass

for root, dirs, files in os.walk(r'd:\harfile\ModelFusion\IDE'):
    if 'node_modules' in dirs: dirs.remove('node_modules')
    if 'package.json' in files:
        patch_pkg(os.path.join(root, 'package.json'))

print('Done patching all package.json files.')

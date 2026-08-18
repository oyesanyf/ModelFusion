import re
cmds = ['stats', 'sysinfo', 'tasks', 'security', 'refactor', 'doc', 'dataanalyst', 'datascience', 'jupyter', 'pe-header-extraction', 'export-pdf', 'decision-stats', 'performance-stats', 'cache-stats', 'code-vulnerability-detection', 'score', 'judge', 'plan', 'context-auto', 'context', 'debug', 'delegation', 'enable-ml', 'error', 'full', 'innovate', 'ml-analytics', 'ml-learning', 'update', 'restore', 'clearcache', 'ml-retrain', 'search-query', 'demo-hyde', 'add-documents', 'model-ranking', 'model-recommendations', 'analytics-demo']

ext_path = r'd:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\dist\extension.js'
try:
    with open(ext_path, 'r', encoding='utf-8') as f:
        content = f.read()

    m = re.search(r'x4=\{editAgent:\{([^\}]+)\},vscode:\{', content)
    if m:
        edit_agent_str = m.group(1)
        existing_cmds = re.findall(r'([a-zA-Z0-9_-]+):\"editAgent\"', edit_agent_str)
        existing_cmds = set(existing_cmds)

        additions = []
        for cmd in cmds:
            key = f'\"{cmd}\"' if '-' in cmd else cmd
            if cmd not in existing_cmds and f'\"{cmd}\"' not in edit_agent_str and f'{cmd}:' not in edit_agent_str:
                additions.append(f'{key}:\"editAgent\"')

        if additions:
            new_edit_agent_str = edit_agent_str + ',' + ','.join(additions)
            content = content.replace(f'editAgent:{{{edit_agent_str}}}', f'editAgent:{{{new_edit_agent_str}}}')
            with open(ext_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Updated x4 in {ext_path} with {len(additions)} commands')
        else:
            print('No x4 additions needed.')
    else:
        print('Could not find x4 in extension.js!')
except Exception as e:
    print('Error:', e)

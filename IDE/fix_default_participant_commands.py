import json, os

cmds_to_add = [
    {"name": "stats", "description": "Display ModelFusion SQLite database statistics and model counts"},
    {"name": "sysinfo", "description": "Display system hardware specifications (CPU, RAM, GPU)"},
    {"name": "sys-info", "description": "Display system hardware specifications (CPU, RAM, GPU)"},
    {"name": "tasks", "description": "List available task categories and models"},
    {"name": "evolve", "description": "Run OpenEvolve logic and code optimization pipeline"},
    {"name": "decision-stats", "description": "Display decision-making statistics"},
    {"name": "performance-stats", "description": "Display performance metrics and timing statistics"},
    {"name": "cache-stats", "description": "Display cache usage and hit statistics"},
    {"name": "clearcache", "description": "Clear ModelFusion cache"}
]

pkgs = [
    r'd:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json'
]

for pkg_path in pkgs:
    if not os.path.exists(pkg_path):
        continue
    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        participants = data.get("contributes", {}).get("chatParticipants", [])
        updated = False
        for p in participants:
            # Inject into all participants (default, agent, etc.)
            existing = {c["name"] for c in p.get("commands", [])}
            for cmd in cmds_to_add:
                if cmd["name"] not in existing:
                    p.setdefault("commands", []).append(cmd)
                    updated = True
                    print(f"Added {cmd['name']} to participant {p.get('id')} in {pkg_path}")
        
        if updated:
            with open(pkg_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"Successfully saved {pkg_path}")
    except Exception as e:
        print(f"Error updating {pkg_path}: {e}")

print("Done updating all package.json files.")

import json

pkg_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json"

with open(pkg_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cp = data["contributes"]["chatParticipants"]
for p in cp:
    print(f"Participant: {p.get('id')} / {p.get('name')}")
    cmds = p.get("commands", [])
    print(f"  Commands ({len(cmds)}):")
    for c in cmds:
        print(f"    - /{c.get('name')}: {c.get('description')}")

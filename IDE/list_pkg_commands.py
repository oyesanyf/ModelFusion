import json

pkg_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json"

with open(pkg_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for p in data["contributes"]["chatParticipants"]:
    print(f"Participant ID: {p.get('id')}")
    for c in p.get("commands", []):
        print(f"  - /{c.get('name')}")

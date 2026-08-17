import json

pkg_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json"

with open(pkg_path, "r", encoding="utf-8") as f:
    data = json.load(f)

contributes = data.get("contributes", {})
print("Contributes keys:", list(contributes.keys()))

if "chatParticipants" in contributes:
    print("chatParticipants:", json.dumps(contributes["chatParticipants"], indent=2)[:2000])

if "commands" in contributes:
    print("Commands count:", len(contributes["commands"]))
    for cmd in contributes["commands"][:10]:
        print("  -", cmd.get("command"))

import os, glob, json

def clean_package(pkg_path):
    print(f"Cleaning {pkg_path}")
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    changed = False
    participants = pkg.get("contributes", {}).get("chatParticipants", [])
    
    # Native commands for specific participants
    native_cmds = {
        "github.copilot.vscode": ["search"],
        "github.copilot.terminalPanel": ["explain"],
    }
    
    for p in participants:
        pid = p.get("id")
        cmds = p.get("commands", [])
        new_cmds = []
        seen = set()
        
        for c in cmds:
            name = c.get("name")
            # 1. Remove typo 'evovle'
            if name == "evovle":
                changed = True
                continue
            
            # 2. If it's a sub-participant (like vscode or terminalPanel), strip injected ModelFusion commands
            if pid in native_cmds and name not in native_cmds[pid]:
                changed = True
                continue
            
            # 3. Deduplicate exact command names
            if name not in seen:
                seen.add(name)
                new_cmds.append(c)
            else:
                changed = True
                
        p["commands"] = new_cmds
        
    if changed:
        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, indent=4)
        print(f"Successfully cleaned {pkg_path}")
    else:
        print(f"No changes needed for {pkg_path}")

base_dirs = [
    r"d:\harfile\ModelFusion\IDE\vscode-126-extract",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64",
    r"d:\harfile\ModelFusion\IDE"
]

for base in base_dirs:
    for pkg_path in glob.glob(os.path.join(base, "**", "extensions", "copilot", "package.json"), recursive=True):
        clean_package(pkg_path)

# Also fix patch_all_commands.py so it doesn't re-add typos or duplicate to all participants
patch_script = r"d:\harfile\ModelFusion\IDE\patch_all_commands.py"
if os.path.exists(patch_script):
    with open(patch_script, "r", encoding="utf-8") as f:
        content = f.read()
    # Remove evovle from script
    if "'evovle'" in content or '"evovle"' in content:
        content = content.replace("'evovle', ", "").replace('"evovle", ', "")
        with open(patch_script, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Cleaned typo from {patch_script}")

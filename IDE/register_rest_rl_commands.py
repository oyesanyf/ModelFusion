#!/usr/bin/env python3
"""
Registers /rl and /restrl slash commands in copilot extension package.json across
IDE source, packaging staging, and versioned runtime directories.
"""

import os
import json
import glob

CANDIDATE_PATHS = [
    r"d:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\package.json",
    r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\package.json",
]

# Add any other versioned directories under VSCode-win32-x64
extra = glob.glob(r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\*\resources\app\extensions\copilot\package.json")
for p in extra:
    if p not in CANDIDATE_PATHS:
        CANDIDATE_PATHS.append(p)

# Also check LOCALAPPDATA
localapp = os.environ.get("LOCALAPPDATA", "")
if localapp:
    CANDIDATE_PATHS.append(os.path.join(localapp, r"HugOS IDE\resources\app\extensions\copilot\package.json"))
    for p in glob.glob(os.path.join(localapp, r"HugOS IDE\*\resources\app\extensions\copilot\package.json")):
        if p not in CANDIDATE_PATHS:
            CANDIDATE_PATHS.append(p)


def patch_package_json(filepath):
    if not os.path.isfile(filepath):
        print(f"[SKIP] File not found: {filepath}")
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read {filepath}: {e}")
        return False

    modified = False
    contributes = data.get("contributes", {})
    participants = contributes.get("chatParticipants", [])

    new_commands = [
        {
            "name": "rl",
            "description": "HugOS ReST-RL / GRPO reinforcement learning subsystem (status, start, stop, enqueue)"
        },
        {
            "name": "restrl",
            "description": "HugOS ReST-RL / GRPO reinforcement learning subsystem (status, start, stop, enqueue)"
        }
    ]

    for p in participants:
        if "commands" in p and isinstance(p["commands"], list):
            existing_names = {c.get("name") for c in p["commands"] if isinstance(c, dict)}
            for nc in new_commands:
                if nc["name"] not in existing_names:
                    p["commands"].append(nc)
                    modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Registered /rl and /restrl in: {filepath}")
        return True
    else:
        print(f"[INFO] /rl and /restrl already registered in: {filepath}")
        return False


if __name__ == "__main__":
    count = 0
    for p in CANDIDATE_PATHS:
        if patch_package_json(p):
            count += 1
    print(f"\nCompleted patching {count} package.json files.")

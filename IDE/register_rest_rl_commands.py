#!/usr/bin/env python3
"""
Registers @rl and @restrl first-class chat participants and /rl /restrl slash commands in
copilot extension package.json across IDE source, packaging staging, and versioned runtime directories.
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
    contributes = data.setdefault("contributes", {})
    participants = contributes.setdefault("chatParticipants", [])

    rl_commands = [
        {"name": "status", "description": "Display ReST-RL daemon state, queue length, and hardware tier"},
        {"name": "start", "description": "Start the HugOS ReST-RL autonomous reasoning daemon"},
        {"name": "stop", "description": "Halt the HugOS ReST-RL autonomous reasoning daemon"},
        {"name": "enqueue", "description": "Enqueue a reasoning or test-repair task for background execution"}
    ]

    # 1. Register @rl and @restrl first-class chat participants
    existing_participant_names = {p.get("name") for p in participants if isinstance(p, dict)}
    existing_participant_ids = {p.get("id") for p in participants if isinstance(p, dict)}

    participants_to_register = [
        {
            "id": "hugos.rest_rl",
            "name": "rl",
            "fullName": "HugOS ReST-RL",
            "description": "HugOS ReST-RL / GRPO autonomous reasoning daemon",
            "locations": ["panel"],
            "commands": rl_commands
        },
        {
            "id": "hugos.restrl",
            "name": "restrl",
            "fullName": "HugOS ReST-RL",
            "description": "HugOS ReST-RL / GRPO autonomous reasoning daemon",
            "locations": ["panel"],
            "commands": rl_commands
        }
    ]

    for np in participants_to_register:
        if np["name"] not in existing_participant_names and np["id"] not in existing_participant_ids:
            participants.append(np)
            existing_participant_names.add(np["name"])
            existing_participant_ids.add(np["id"])
            modified = True
        else:
            # Update existing entry to ensure commands and locations are complete
            for p in participants:
                if p.get("name") == np["name"] or p.get("id") == np["id"]:
                    if "commands" not in p:
                        p["commands"] = list(rl_commands)
                        modified = True
                    else:
                        existing_cmds = {c.get("name") for c in p["commands"] if isinstance(c, dict)}
                        for cmd in rl_commands:
                            if cmd["name"] not in existing_cmds:
                                p["commands"].append(cmd)
                                modified = True
                    if "locations" not in p:
                        p["locations"] = ["panel"]
                        modified = True

    # 2. Also register /rl and /restrl slash commands in existing participants for slash autocomplete
    slash_commands = [
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
        if p.get("name") in ("agent", "copilot", "terminal"):
            if "commands" in p and isinstance(p["commands"], list):
                existing_names = {c.get("name") for c in p["commands"] if isinstance(c, dict)}
                for sc in slash_commands:
                    if sc["name"] not in existing_names:
                        p["commands"].append(sc)
                        modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Registered @rl, @restrl, /rl, and /restrl in: {filepath}")
        return True
    else:
        print(f"[INFO] @rl, @restrl, /rl, and /restrl already up to date in: {filepath}")
        return False


if __name__ == "__main__":
    count = 0
    for p in CANDIDATE_PATHS:
        if patch_package_json(p):
            count += 1
    print(f"\nCompleted patching {count} package.json files.")

import json

pkg_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json"

with open(pkg_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Master list of slash commands to register in VS Code Chat UI autocomplete
commands_to_add = [
    {"name": "stats", "description": "Display ModelFusion SQLite database statistics and model counts"},
    {"name": "sysinfo", "description": "Display system hardware specifications (CPU, RAM, GPU)"},
    {"name": "sys-info", "description": "Display system hardware specifications (CPU, RAM, GPU)"},
    {"name": "tasks", "description": "List available task categories and models"},
    {"name": "evolve", "description": "Run OpenEvolve logic and code optimization pipeline"},
    {"name": "security", "description": "Perform cybersecurity audit and fix vulnerabilities in active code"},
    {"name": "refactor", "description": "Refactor code for readability, performance, and structure"},
    {"name": "optimize", "description": "Optimize code algorithms and memory performance"},
    {"name": "doc", "description": "Generate comprehensive technical documentation and docstrings"},
    {"name": "dataanalyst", "description": "Run Data Analyst workflow on CSV/Excel datasets"},
    {"name": "datascience", "description": "Run comprehensive Data Science machine learning pipeline"},
    {"name": "jupyter", "description": "Generate interactive Jupyter Notebook code"},
    {"name": "pe-header-extraction", "description": "Extract and analyze PE executable headers"},
    {"name": "export-pdf", "description": "Export analysis results to PDF report"},
    {"name": "decision-stats", "description": "Display decision-making statistics"},
    {"name": "performance-stats", "description": "Display performance metrics and timing statistics"},
    {"name": "cache-stats", "description": "Display cache usage and hit statistics"},
    {"name": "code-vulnerability-detection", "description": "Detect and repair code vulnerabilities"},
    {"name": "gpu", "description": "Toggle GPU hardware acceleration"},
    {"name": "cpu", "description": "Toggle CPU execution mode"},
    {"name": "ollama", "description": "Switch local backend to Ollama"},
    {"name": "openvino", "description": "Switch local backend to OpenVINO"},
    {"name": "fusion", "description": "Toggle Multi-Model Fusion Mode"},
    {"name": "cot", "description": "Toggle Chain-Of-Thought reasoning mode"},
    {"name": "score", "description": "Toggle response evaluation scoring"},
    {"name": "judge", "description": "Toggle LLM-as-a-Judge evaluation"},
    {"name": "plan", "description": "Toggle AI-powered planning mode"}
]

chat_participants = data["contributes"]["chatParticipants"]

for participant in chat_participants:
    if "commands" in participant:
        existing_names = {c["name"] for c in participant["commands"]}
        for cmd in commands_to_add:
            if cmd["name"] not in existing_names:
                participant["commands"].append(cmd)
                existing_names.add(cmd["name"])

with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Successfully registered all slash commands in {pkg_path}!")

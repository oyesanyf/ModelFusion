import os
import glob

# Master list of all CLI flags and tasks from cli.exe --help
all_cli_tasks = [
    "text-classification", "token-classification", "question-answering", "text-generation",
    "summarization", "translation", "fill-mask", "text2text-generation", "language-detection",
    "grammar-correction", "paraphrase-generation", "causal-language-modeling", "zero-shot-classification",
    "feature-extraction", "sentence-similarity", "anonymization", "coreference-resolution", "spam-detection",
    "malware-text-detection", "phishing-detection", "pii-detection", "hate-speech-detection",
    "cyberbullying-detection", "fake-news-detection", "legal-judgment-classification",
    "contract-clause-classification", "case-outcome-prediction", "financial-ner", "legal-ner",
    "biomedical-ner", "chemical-reaction-ner", "financial-sentiment-analysis",
    "scientific-abstract-summarization", "emotion-detection", "sarcasm-detection", "stance-detection",
    "bias-detection", "hallucination-detection", "reading-level-assessment", "generation-groundedness",
    "citation-intent-classification", "code-vulnerability-detection", "code-summary-generation",
    "code-clone-detection", "image-classification", "object-detection", "image-segmentation",
    "visual-question-answering", "document-question-answering", "zero-shot-image-classification",
    "depth-estimation", "image-feature-extraction", "automatic-speech-recognition", "audio-classification",
    "voice-activity-detection", "emotion-recognition", "video-classification", "text-to-speech",
    "text-to-image", "image-super-resolution", "table-question-answering", "feature-ranking",
    "security", "fix", "review", "explain", "tests", "refactor", "optimize", "doc", "dataanalyst",
    "datascience", "jupyter", "pe-header-extraction", "export-pdf", "prepare-model", "prepare-all-models"
]

base_dir = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89"

# We will inject the comprehensive task list into the cliCodeCommands set in extension.js
js_set = 'new Set([' + ','.join(f'"{t}"' for t in all_cli_tasks) + '])'

print(f"Generated task set with {len(all_cli_tasks)} commands.")

# Also let's ensure all .agents/commands markdown files are updated if needed
commands_dir = r"d:\harfile\ModelFusion\.agents\commands"
os.makedirs(commands_dir, exist_ok=True)

for task in all_cli_tasks:
    filepath = os.path.join(commands_dir, f"{task}.md")
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\ndescription: ModelFusion {task} directive\n---\n\nExecute {task} via cli.exe with active context.\n")
        # non-hyphenated alias
        alias = task.replace("-", "")
        if alias != task:
            alias_path = os.path.join(commands_dir, f"{alias}.md")
            if not os.path.exists(alias_path):
                with open(alias_path, "w", encoding="utf-8") as f:
                    f.write(f"---\ndescription: ModelFusion {task} directive\n---\n\nExecute {task} via cli.exe with active context.\n")

print("Created all missing command files in .agents/commands/")

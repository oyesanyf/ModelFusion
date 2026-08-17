import json
import re

raw_help = """
      --file <FILE>
      --folder <FOLDER>
      --prompt <PROMPT>
      --task <TASK>
      --budget <BUDGET>
      --chain-of-thought
      --config <CONFIG>
      --enable-ml
      --use-openai
      --verbose
      --debug
      --selection-strategy <SELECTION_STRATEGY>
      --language <LANGUAGE>
      --gpu
      --cpu
      --api-keys <API_KEYS>
      --sys-info
      --save-model
      --load-model <LOAD_MODEL>
      --enable-ml-selection
      --ml-learning
      --ml-ensemble-method <ML_ENSEMBLE_METHOD>
      --ml-confidence-threshold <ML_CONFIDENCE_THRESHOLD>
      --ml-analytics
      --ml-retrain
      --ml-cleanup <ML_CLEANUP>
      --sinq
      --sinq-nbits <SINQ_NBITS>
      --sinq-group-size <SINQ_GROUP_SIZE>
      --sinq-tiling-mode <SINQ_TILING_MODE>
      --sinq-method <SINQ_METHOD>
      --enable-innovations
      --workflow-optimization
      --semantic-analysis
      --temporal-tracking
      --predictive-mode
      --innovation-level <INNOVATION_LEVEL>
      --enable-hyde
      --use-hyde
      --hyde-variants
      --add-documents <ADD_DOCUMENTS>
      --search-query <SEARCH_QUERY>
      --top-k <TOP_K>
      --demo-hyde
      --stats
      --tasks [<TASKS>]
      --update
      --restore
      --decision-stats
      --novel-ai-stats
      --performance-stats
      --cache-stats
      --clearcache
      --analytics-demo
      --model-ranking [<MODEL_RANKING>]
      --model-recommendations
      --full
      --fusion
      --fusion-models <FUSION_MODELS>
      --fusion-mode <FUSION_MODE>
      --ollama
      --openvino
      --onnx
      --vllm
      --model <MODEL>
      --prepare-model <PREPARE_MODEL>
      --prepare-all-models
      --weight-format <WEIGHT_FORMAT>
      --ov-model-dir <OV_MODEL_DIR>
      --context-auto
      --context <CONTEXT>
      --report <REPORT>
      --reporttype <REPORTTYPE>
      --delegation
      --recursion
      --getvino
      --getvino-interval <GETVINO_INTERVAL>
      --real-options
      --prompt-quality-scoring
      --ml-fallback <ML_FALLBACK>
      --jupyter
      --dataanalyst
      --datascience
      --export-pdf
      --score
      --judge
      --plan
      --pe-header-extraction
      --sentiment
      --question
      --ner
      --summary
      --text-classification
      --token-classification
      --question-answering
      --text-generation
      --summarization
      --translation
      --fill-mask
      --text2text-generation
      --language-detection
      --grammar-correction
      --paraphrase-generation
      --causal-language-modeling
      --zero-shot-classification
      --feature-extraction
      --sentence-similarity
      --anonymization
      --coreference-resolution
      --spam-detection
      --malware-text-detection
      --phishing-detection
      --pii-detection
      --hate-speech-detection
      --cyberbullying-detection
      --fake-news-detection
      --legal-judgment-classification
      --contract-clause-classification
      --case-outcome-prediction
      --financial-ner
      --legal-ner
      --biomedical-ner
      --chemical-reaction-ner
      --financial-sentiment-analysis
      --scientific-abstract-summarization
      --emotion-detection
      --sarcasm-detection
      --stance-detection
      --bias-detection
      --hallucination-detection
      --reading-level-assessment
      --generation-groundedness
      --citation-intent-classification
      --code-vulnerability-detection
      --code-summary-generation
      --code-clone-detection
      --image-classification
      --object-detection
      --image-segmentation
      --visual-question-answering
      --document-question-answering
      --zero-shot-image-classification
      --depth-estimation
      --image-feature-extraction
      --automatic-speech-recognition
      --audio-classification
      --voice-activity-detection
      --emotion-recognition
      --video-classification
      --text-to-speech
      --text-to-image
      --image-super-resolution
      --table-question-answering
      --feature-ranking
      --db-path <DB_PATH>
      --server
      --enable-slash-commands
      --port <PORT>
      --mcp
      --patch-ide
"""

# Extract all --flag names
flag_names = set(re.findall(r'--([a-zA-Z0-9-]+)', raw_help))

# Exclude internal flags not meant for chat slash commands
exclude = {"h", "help", "V", "version", "patch-ide", "ide-src-dir", "shallow", "vscode-tag"}
flag_names = flag_names - exclude

# Build list of commands and non-hyphenated aliases
commands_list = []
seen = set()

for flag in sorted(flag_names):
    if flag not in seen:
        commands_list.append({"name": flag, "description": f"ModelFusion /{flag} command"})
        seen.add(flag)
    alias = flag.replace("-", "")
    if alias != flag and alias not in seen:
        commands_list.append({"name": alias, "description": f"ModelFusion /{alias} command (alias for /{flag})"})
        seen.add(alias)

print(f"Total commands & aliases to register in package.json: {len(commands_list)}")

pkg_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json"

with open(pkg_path, "r", encoding="utf-8") as f:
    pkg_data = json.load(f)

for participant in pkg_data["contributes"]["chatParticipants"]:
    if "commands" in participant:
        existing = {c["name"]: c for c in participant["commands"]}
        for cmd in commands_list:
            if cmd["name"] not in existing:
                participant["commands"].append(cmd)
            else:
                existing[cmd["name"]]["description"] = cmd["description"]

with open(pkg_path, "w", encoding="utf-8") as f:
    json.dump(pkg_data, f, indent=2)

print(f"Successfully updated {pkg_path} with all {len(commands_list)} commands from cli.exe --help!")

import re

help_flags = [
    'file', 'folder', 'prompt', 'task', 'budget', 'chain-of-thought', 'config',
    'enable-ml', 'use-openai', 'verbose', 'debug', 'selection-strategy', 'language',
    'gpu', 'cpu', 'api-keys', 'sys-info', 'save-model', 'load-model',
    'enable-ml-selection', 'ml-learning', 'ml-ensemble-method', 'ml-confidence-threshold',
    'ml-analytics', 'ml-retrain', 'ml-cleanup', 'sinq', 'sinq-nbits', 'sinq-group-size',
    'sinq-tiling-mode', 'sinq-method', 'enable-innovations', 'workflow-optimization',
    'semantic-analysis', 'temporal-tracking', 'predictive-mode', 'innovation-level',
    'enable-hyde', 'use-hyde', 'hyde-variants', 'add-documents', 'search-query',
    'research', 'search', 'top-k', 'demo-hyde', 'active-model', 'stats', 'tasks',
    'update', 'updatedb', 'max-models', 'restore', 'decision-stats', 'novel-ai-stats',
    'performance-stats', 'cache-stats', 'clearcache', 'analytics-demo', 'model-ranking',
    'model-recommendations', 'full', 'fusion', 'fusion-models', 'fusion-mode', 'ollama',
    'openvino', 'onnx', 'vllm', 'model', 'prepare-model', 'prepare-all-models',
    'weight-format', 'ov-model-dir', 'context-auto', 'context', 'report', 'reporttype',
    'delegation', 'recursion', 'getvino', 'getvino-interval', 'real-options',
    'prompt-quality-scoring', 'ml-fallback', 'jupyter', 'dataanalyst', 'datascience',
    'export-pdf', 'score', 'judge', 'plan', 'pe-header-extraction', 'sentiment',
    'question', 'ner', 'summary', 'text-classification', 'token-classification',
    'question-answering', 'text-generation', 'summarization', 'translation', 'fill-mask',
    'text2text-generation', 'language-detection', 'grammar-correction',
    'paraphrase-generation', 'causal-language-modeling', 'zero-shot-classification',
    'feature-extraction', 'sentence-similarity', 'anonymization', 'coreference-resolution',
    'spam-detection', 'malware-text-detection', 'phishing-detection', 'pii-detection',
    'hate-speech-detection', 'cyberbullying-detection', 'fake-news-detection',
    'legal-judgment-classification', 'contract-clause-classification',
    'case-outcome-prediction', 'financial-ner', 'legal-ner', 'biomedical-ner',
    'chemical-reaction-ner', 'financial-sentiment-analysis',
    'scientific-abstract-summarization', 'emotion-detection', 'sarcasm-detection',
    'stance-detection', 'bias-detection', 'hallucination-detection',
    'reading-level-assessment', 'generation-groundedness',
    'citation-intent-classification', 'code-vulnerability-detection',
    'code-summary-generation', 'code-clone-detection', 'image-classification',
    'object-detection', 'image-segmentation', 'visual-question-answering',
    'document-question-answering', 'zero-shot-image-classification', 'depth-estimation',
    'image-feature-extraction', 'automatic-speech-recognition', 'audio-classification',
    'voice-activity-detection', 'emotion-recognition', 'video-classification',
    'text-to-speech', 'text-to-image', 'image-super-resolution',
    'table-question-answering', 'feature-ranking'
]

print(f"Total flags in help: {len(help_flags)}")

with open(r'crates/cli/src/main.rs', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('pub fn canonicalize_command')
end = content.find('pub fn detect_natural_language_research', start)
canon_fn = content[start:end]

missing = []
for flag in help_flags:
    clean = re.sub(r'[^a-zA-Z0-9]', '', flag).lower()
    if f'"{clean}"' not in canon_fn:
        missing.append((flag, clean))

print(f"Missing in canonicalize_command: {len(missing)}")
for m in missing:
    print(' ', m)

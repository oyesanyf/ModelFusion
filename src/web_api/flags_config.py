"""
Comprehensive flag configuration for HFOrchestra CLI
Based on the actual CLI help output
"""

# Comprehensive flag definitions organized by category
ALL_FLAGS = {
    "basic": [
        {"name": "--prompt", "type": "string", "description": "Prompt/question for processing", "required": False},
        {"name": "--file", "type": "string", "description": "Input file path (100+ formats supported)", "required": False},
        {"name": "--task", "type": "string", "description": "Process a task (alias for --prompt)", "required": False},
        {"name": "--budget", "type": "float", "description": "Budget in dollars (default: 10.0)", "required": False},
        {"name": "--config", "type": "string", "description": "Configuration file path", "required": False},
        {"name": "--language", "type": "string", "description": "Processing language (en, es, fr, de, etc.)", "required": False},
        {"name": "--api-keys", "type": "string", "description": "JSON file containing API keys", "required": False},
        {"name": "--load-model", "type": "string", "description": "Load pre-trained ML model from file", "required": False},
        {"name": "--verbose", "type": "boolean", "description": "Enable verbose logging", "required": False},
        {"name": "--debug", "type": "boolean", "description": "Enable debug mode", "required": False},
        {"name": "--gpu", "type": "boolean", "description": "Force GPU/CUDA usage", "required": False},
        {"name": "--cpu", "type": "boolean", "description": "Force CPU-only execution", "required": False},
    ],
    
    "ai_enhancements": [
        {"name": "--chain-of-thought", "type": "boolean", "description": "Apply Tree-of-Thoughts reasoning", "required": False},
        {"name": "--enable-ml", "type": "boolean", "description": "Enable additional ML features", "required": False},
        {"name": "--use-openai", "type": "boolean", "description": "Use OpenAI models instead of HuggingFace", "required": False},
        {"name": "--save-model", "type": "boolean", "description": "Save trained ML models", "required": False},
        {"name": "--plan", "type": "boolean", "description": "Enable AI-powered planning (LangChain)", "required": False},
        {"name": "--score", "type": "boolean", "description": "Enable response evaluation scoring", "required": False},
        {"name": "--judge", "type": "boolean", "description": "Enable LLM-as-a-Judge evaluation", "required": False},
    ],
    
    "model_selection": [
        {"name": "--selection-strategy", "type": "select", "options": ["hyperparameter_tuning", "cross_validation", "ensemble_methods", "multi_objective", "bayesian_optimization", "meta_learning", "ml_enhanced", "ml_ensemble", "ml_voting", "ml_consensus", "ml_stacking", "ml_adaptive"], "description": "Enhanced model selection strategy", "required": False},
        {"name": "--enable-ml-selection", "type": "boolean", "description": "Enable ML-based model selection", "required": False},
        {"name": "--ml-learning", "type": "boolean", "description": "Enable learning from task execution", "required": False},
        {"name": "--ml-ensemble-method", "type": "select", "options": ["voting", "weighted_voting", "consensus", "stacking", "adaptive"], "description": "Ensemble method for ML selection", "required": False},
        {"name": "--ml-confidence-threshold", "type": "float", "description": "Minimum confidence threshold (0.0-1.0)", "required": False},
        {"name": "--ml-fallback", "type": "boolean", "description": "Enable fallback to enhanced selector", "required": False},
        {"name": "--ml-analytics", "type": "boolean", "description": "Show ML performance statistics", "required": False},
        {"name": "--ml-retrain", "type": "boolean", "description": "Force retraining of ML models", "required": False},
        {"name": "--ml-cleanup", "type": "integer", "description": "Clean up ML training data older than N days", "required": False},
    ],
    
    "sinq_quantization": [
        {"name": "--sinq", "type": "boolean", "description": "Enable SINQ quantization", "required": False},
        {"name": "--sinq-nbits", "type": "select", "options": ["2", "3", "4", "5", "6", "8"], "description": "Bit-width for SINQ quantization", "required": False},
        {"name": "--sinq-group-size", "type": "select", "options": ["64", "128"], "description": "Weights per quantization group", "required": False},
        {"name": "--sinq-tiling-mode", "type": "select", "options": ["1D", "2D"], "description": "Weight matrix tiling strategy", "required": False},
        {"name": "--sinq-method", "type": "select", "options": ["sinq", "asinq"], "description": "SINQ quantization method", "required": False},
    ],
    
    "innovation_system": [
        {"name": "--enable-innovations", "type": "boolean", "description": "Enable all innovation systems", "required": False},
        {"name": "--workflow-optimization", "type": "boolean", "description": "Enable workflow optimization", "required": False},
        {"name": "--semantic-analysis", "type": "boolean", "description": "Enable semantic analysis", "required": False},
        {"name": "--temporal-tracking", "type": "boolean", "description": "Enable temporal change tracking", "required": False},
        {"name": "--predictive-mode", "type": "boolean", "description": "Enable predictive capabilities", "required": False},
        {"name": "--innovation-level", "type": "select", "options": ["1", "2", "3"], "description": "Innovation system level", "required": False},
        {"name": "--full", "type": "boolean", "description": "Enable comprehensive analysis mode", "required": False},
    ],
    
    "hyde_search": [
        {"name": "--enable-hyde", "type": "boolean", "description": "Enable HyDE (Hypothetical Document Embeddings)", "required": False},
        {"name": "--use-hyde", "type": "boolean", "description": "Use interactive HyDE question refinement", "required": False},
        {"name": "--hyde-variants", "type": "boolean", "description": "Use multiple HyDE variants", "required": False},
        {"name": "--add-documents", "type": "string", "description": "Add documents to search index (comma-separated)", "required": False},
        {"name": "--search-query", "type": "string", "description": "Perform semantic search", "required": False},
        {"name": "--top-k", "type": "integer", "description": "Number of top results to return", "required": False},
        {"name": "--demo-hyde", "type": "boolean", "description": "Run HyDE and embeddings demo", "required": False},
    ],
    
    "data_analysis": [
        {"name": "--data-analyst", "type": "boolean", "description": "Run comprehensive data analyst workflow", "required": False},
        {"name": "--datanalyst", "type": "boolean", "description": "Alias for --data-analyst", "required": False},
        {"name": "--datascience", "type": "boolean", "description": "Run comprehensive Data Science workflow with PDF export", "required": False},
        {"name": "--jupyter", "type": "boolean", "description": "Launch Jupyter notebook for data analysis", "required": False},
        {"name": "--export-pdf", "type": "boolean", "description": "Export analysis results to PDF report", "required": False},
    ],
    
    "system_control": [
        {"name": "--delegation", "type": "boolean", "description": "Use delegation pattern", "required": False},
        {"name": "--recursion", "type": "boolean", "description": "Use recursive task decomposition", "required": False},
        {"name": "--real-options", "type": "boolean", "description": "Enable real options analysis", "required": False},
        {"name": "--prompt-quality-scoring", "type": "boolean", "description": "Enable prompt quality scoring", "required": False},
    ],
    
    "system_stats": [
        {"name": "--stats", "type": "boolean", "description": "Show model categorization statistics", "required": False},
        {"name": "--tasks", "type": "string", "description": "List models and tasks (filter by: audio, image, text)", "required": False},
        {"name": "--update", "type": "boolean", "description": "Update the HuggingFace models database", "required": False},
        {"name": "--restore", "type": "boolean", "description": "Restore config and database from backup", "required": False},
        {"name": "--decision-stats", "type": "boolean", "description": "Show decision-making statistics", "required": False},
        {"name": "--novel-ai-stats", "type": "boolean", "description": "Show novel AI component statistics", "required": False},
        {"name": "--performance-stats", "type": "boolean", "description": "Show performance metrics", "required": False},
        {"name": "--cache-stats", "type": "boolean", "description": "Show cache usage statistics", "required": False},
        {"name": "--clearcache", "type": "boolean", "description": "Clear all cached data", "required": False},
        {"name": "--analytics-demo", "type": "boolean", "description": "Run advanced model analytics demo", "required": False},
        {"name": "--model-ranking", "type": "string", "description": "Show model ranking for a specific task", "required": False},
        {"name": "--model-recommendations", "type": "boolean", "description": "Get personalized model recommendations", "required": False},
        {"name": "--help", "type": "string", "description": "Show help (use 'all' or specific flag name)", "required": False},
    ],
    
    "text_tasks_basic": [
        {"name": "--text-classification", "type": "boolean", "description": "Text classification task", "required": False},
        {"name": "--token-classification", "type": "boolean", "description": "Token classification (NER) task", "required": False},
        {"name": "--question-answering", "type": "boolean", "description": "Question answering task", "required": False},
        {"name": "--text-generation", "type": "boolean", "description": "Text generation task", "required": False},
        {"name": "--summarization", "type": "boolean", "description": "Text summarization task", "required": False},
        {"name": "--translation", "type": "boolean", "description": "Text translation task", "required": False},
        {"name": "--fill-mask", "type": "boolean", "description": "Fill mask task", "required": False},
        {"name": "--text2text-generation", "type": "boolean", "description": "Text-to-text generation task", "required": False},
    ],
    
    "text_tasks_language": [
        {"name": "--language-detection", "type": "boolean", "description": "Language detection task", "required": False},
        {"name": "--grammar-correction", "type": "boolean", "description": "Grammar correction task", "required": False},
        {"name": "--paraphrase-generation", "type": "boolean", "description": "Paraphrase generation task", "required": False},
        {"name": "--causal-language-modeling", "type": "boolean", "description": "Causal language modeling task", "required": False},
    ],
    
    "text_tasks_advanced": [
        {"name": "--zero-shot-classification", "type": "boolean", "description": "Zero-shot classification task", "required": False},
        {"name": "--feature-extraction", "type": "boolean", "description": "Feature extraction task", "required": False},
        {"name": "--sentence-similarity", "type": "boolean", "description": "Sentence similarity task", "required": False},
        {"name": "--anonymization", "type": "boolean", "description": "Text anonymization task", "required": False},
        {"name": "--coreference-resolution", "type": "boolean", "description": "Coreference resolution task", "required": False},
    ],
    
    "text_tasks_legacy": [
        {"name": "--sentiment", "type": "boolean", "description": "Basic sentiment analysis", "required": False},
        {"name": "--question", "type": "boolean", "description": "Question answering mode", "required": False},
        {"name": "--ner", "type": "boolean", "description": "Named entity recognition", "required": False},
        {"name": "--summary", "type": "boolean", "description": "Text summarization", "required": False},
    ],
    
    "security_tasks": [
        {"name": "--spam-detection", "type": "boolean", "description": "Spam detection task", "required": False},
        {"name": "--malware-text-detection", "type": "boolean", "description": "Malware text detection task", "required": False},
        {"name": "--phishing-detection", "type": "boolean", "description": "Phishing detection task", "required": False},
        {"name": "--pii-detection", "type": "boolean", "description": "PII detection task", "required": False},
        {"name": "--hate-speech-detection", "type": "boolean", "description": "Hate speech detection task", "required": False},
        {"name": "--cyberbullying-detection", "type": "boolean", "description": "Cyberbullying detection task", "required": False},
        {"name": "--fake-news-detection", "type": "boolean", "description": "Fake news detection task", "required": False},
        {"name": "--pe-header-extraction", "type": "boolean", "description": "Extract PE headers from Windows executables", "required": False},
    ],
    
    "legal_tasks": [
        {"name": "--legal-judgment-classification", "type": "boolean", "description": "Legal judgment classification task", "required": False},
        {"name": "--contract-clause-classification", "type": "boolean", "description": "Contract clause classification task", "required": False},
        {"name": "--case-outcome-prediction", "type": "boolean", "description": "Case outcome prediction task", "required": False},
    ],
    
    "domain_tasks": [
        {"name": "--financial-ner", "type": "boolean", "description": "Financial named entity recognition", "required": False},
        {"name": "--legal-ner", "type": "boolean", "description": "Legal named entity recognition", "required": False},
        {"name": "--biomedical-ner", "type": "boolean", "description": "Biomedical named entity recognition", "required": False},
        {"name": "--chemical-reaction-ner", "type": "boolean", "description": "Chemical reaction named entity recognition", "required": False},
        {"name": "--financial-sentiment-analysis", "type": "boolean", "description": "Financial sentiment analysis", "required": False},
        {"name": "--scientific-abstract-summarization", "type": "boolean", "description": "Scientific abstract summarization", "required": False},
    ],
    
    "content_analysis": [
        {"name": "--emotion-detection", "type": "boolean", "description": "Emotion detection task", "required": False},
        {"name": "--sarcasm-detection", "type": "boolean", "description": "Sarcasm detection task", "required": False},
        {"name": "--stance-detection", "type": "boolean", "description": "Stance detection task", "required": False},
        {"name": "--bias-detection", "type": "boolean", "description": "Bias detection task", "required": False},
        {"name": "--hallucination-detection", "type": "boolean", "description": "Hallucination detection task", "required": False},
        {"name": "--reading-level-assessment", "type": "boolean", "description": "Reading level assessment task", "required": False},
        {"name": "--generation-groundedness", "type": "boolean", "description": "Generation groundedness task", "required": False},
        {"name": "--citation-intent-classification", "type": "boolean", "description": "Citation intent classification task", "required": False},
    ],
    
    "code_tasks": [
        {"name": "--code-vulnerability-detection", "type": "boolean", "description": "Code vulnerability detection task", "required": False},
        {"name": "--code-summary-generation", "type": "boolean", "description": "Code summary generation task", "required": False},
        {"name": "--code-clone-detection", "type": "boolean", "description": "Code clone detection task", "required": False},
    ],
    
    "image_tasks": [
        {"name": "--image-classification", "type": "boolean", "description": "Image classification task", "required": False},
        {"name": "--object-detection", "type": "boolean", "description": "Object detection task", "required": False},
        {"name": "--image-segmentation", "type": "boolean", "description": "Image segmentation task", "required": False},
        {"name": "--visual-question-answering", "type": "boolean", "description": "Visual question answering task", "required": False},
        {"name": "--document-question-answering", "type": "boolean", "description": "Document question answering task", "required": False},
        {"name": "--zero-shot-image-classification", "type": "boolean", "description": "Zero-shot image classification task", "required": False},
        {"name": "--depth-estimation", "type": "boolean", "description": "Depth estimation task", "required": False},
        {"name": "--image-feature-extraction", "type": "boolean", "description": "Image feature extraction task", "required": False},
    ],
    
    "audio_tasks": [
        {"name": "--automatic-speech-recognition", "type": "boolean", "description": "Automatic speech recognition task", "required": False},
        {"name": "--audio-classification", "type": "boolean", "description": "Audio classification task", "required": False},
        {"name": "--voice-activity-detection", "type": "boolean", "description": "Voice activity detection task", "required": False},
        {"name": "--emotion-recognition", "type": "boolean", "description": "Emotion recognition from audio task", "required": False},
    ],
    
    "video_tasks": [
        {"name": "--video-classification", "type": "boolean", "description": "Video classification task", "required": False},
    ],
    
    "generation_tasks": [
        {"name": "--text-to-speech", "type": "boolean", "description": "Text-to-speech task", "required": False},
        {"name": "--text-to-image", "type": "boolean", "description": "Text-to-image generation task", "required": False},
        {"name": "--image-super-resolution", "type": "boolean", "description": "Image super-resolution task", "required": False},
    ],
    
    "structured_data": [
        {"name": "--table-question-answering", "type": "boolean", "description": "Table question answering task", "required": False},
        {"name": "--feature-ranking", "type": "boolean", "description": "Feature ranking task", "required": False},
    ],
}


//! ModelFusion Master MCP Tools Catalog
//! Single source of truth for all 161+ Model Context Protocol tools across Master CLI, HugOS IDE, HugOS Browser, and MCP stdio server.

pub fn get_master_mcp_tools() -> Vec<serde_json::Value> {
    vec![
        serde_json::json!({
            "name": "execute",
            "cmd": "cli.exe ",
            "icon": "🖥️",
            "category": "core",
            "label": "Universal CLI Execute",
            "description": "Execute ModelFusion CLI with ANY combination of flags",
            "inputSchema": {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}, "description": "Array of CLI arguments (e.g. ['--prompt', 'explain recursion', '--gpu'])"}}, "required": ["args"]}
        }),
        serde_json::json!({
            "name": "quick_answer",
            "cmd": "@agent quick ",
            "icon": "⚡",
            "category": "core",
            "label": "Quick Answer",
            "description": "Fast direct answer for general knowledge questions (non-coding) via Ollama in 2-3s",
            "inputSchema": {"type": "object", "properties": {"question": {"type": "string", "description": "The question to answer"}, "model": {"type": "string", "description": "Ollama model (default: qwen2.5:3b)"}}, "required": ["question"]}
        }),
        serde_json::json!({
            "name": "orchestrate",
            "cmd": "@agent orchestrate ",
            "icon": "🎼",
            "category": "core",
            "label": "Full Orchestrator",
            "description": "Full pipeline: task detection → model selection → multi-model deliberation → execution",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Task prompt or instruction"}, "budget": {"type": "number", "description": "Model parameter budget in billions"}, "selection_strategy": {"type": "string", "description": "Selection strategy"}, "gpu": {"type": "boolean"}, "cpu": {"type": "boolean"}, "fusion": {"type": "boolean", "description": "Enable multi-model consensus"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "analyze_file",
            "cmd": "@agent file ",
            "icon": "📄",
            "category": "code",
            "label": "Analyze File",
            "description": "Analyze, review, or process a specific file with ModelFusion",
            "inputSchema": {"type": "object", "properties": {"file": {"type": "string", "description": "Absolute path to file"}, "prompt": {"type": "string", "description": "Instructions or questions about file"}}, "required": ["file", "prompt"]}
        }),
        serde_json::json!({
            "name": "analyze_folder",
            "cmd": "@agent folder ",
            "icon": "📁",
            "category": "code",
            "label": "Analyze Folder",
            "description": "Analyze, audit, or review an entire directory/project",
            "inputSchema": {"type": "object", "properties": {"folder": {"type": "string", "description": "Absolute path to folder"}, "prompt": {"type": "string", "description": "Instructions or review goals"}}, "required": ["folder", "prompt"]}
        }),
        serde_json::json!({
            "name": "browser",
            "cmd": "@agent browser ",
            "icon": "🌐",
            "category": "web",
            "label": "Browser Automation",
            "description": "Navigate, interact, and automate web workflows",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Browser Automation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "video",
            "cmd": "@agent video ",
            "icon": "🎬",
            "category": "multimodal",
            "label": "Video Analysis",
            "description": "Process video streams, extract keyframes, classify actions & video QA",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Video Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "browser_deep_research",
            "cmd": "@agent browser deep research on ",
            "icon": "🔍",
            "category": "web",
            "label": "Deep Research",
            "description": "Autonomous multi-step web research & synthesis",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Deep Research"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "arxiv",
            "cmd": "@agent arxiv ",
            "icon": "📚",
            "category": "web",
            "label": "arXiv Papers",
            "description": "Direct search of arXiv scientific preprints and research papers",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for arXiv Papers"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "wiki",
            "cmd": "@agent wiki ",
            "icon": "📖",
            "category": "web",
            "label": "Wikipedia Knowledge Distillation",
            "description": "Distill Wikipedia knowledge with deep section retrieval, cross-reference linking, and verified citation grounding",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Topic or query to distill from Wikipedia"}, "file": {"type": "string", "description": "Optional file path or target context"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "markers",
            "cmd": "@agent markers ",
            "icon": "🎯",
            "category": "web",
            "label": "Visual Element Markers",
            "description": "Numeric visual element grounding with 90% token reduction",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        serde_json::json!({
            "name": "som",
            "cmd": "@agent markers ",
            "icon": "🎯",
            "category": "web",
            "label": "Visual Element Markers",
            "description": "Numeric visual element grounding with 90% token reduction",
            "inputSchema": {"type": "object", "properties": {}}
        }),
        serde_json::json!({
            "name": "summarize",
            "cmd": "@agent summarize",
            "icon": "📑",
            "category": "web",
            "label": "Summarize Page",
            "description": "Extract and summarize active web page content",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Summarize Page"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "search",
            "cmd": "@agent search ",
            "icon": "🔎",
            "category": "web",
            "label": "Web Search Grounding",
            "description": "Live web search grounding with verified citations",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}
        }),
        serde_json::json!({
            "name": "web_agent",
            "cmd": "@agent web-agent ",
            "icon": "🌐",
            "category": "web",
            "label": "Web Search Agent",
            "description": "Search internet, build inverted index, and correlate results with LLM",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Web Search Agent"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "search_index",
            "cmd": "@agent search-index ",
            "icon": "📑",
            "category": "web",
            "label": "Search Index",
            "description": "Build and query in-memory inverted search index over web data",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Search Index"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "browser_navigate",
            "cmd": "@agent browser navigate ",
            "icon": "🧭",
            "category": "web",
            "label": "Browser Navigate",
            "description": "Direct viewport navigation to specific URL",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Browser Navigate"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "browser_extract",
            "cmd": "@agent browser extract ",
            "icon": "📋",
            "category": "web",
            "label": "DOM Extraction",
            "description": "Extract structured clean text and interactive nodes from DOM",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for DOM Extraction"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "acdso",
            "cmd": "@agent acdso ",
            "icon": "📊",
            "category": "tabular",
            "label": "ACDSO AutoML",
            "description": "5-objective Pareto causal AutoML on datasets",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for ACDSO AutoML"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "datascience",
            "cmd": "@agent datascience ",
            "icon": "📈",
            "category": "tabular",
            "label": "Data Science",
            "description": "Full data science workflow and pipeline",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Data Science"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "dataanalyst",
            "cmd": "@agent dataanalyst ",
            "icon": "🔬",
            "category": "tabular",
            "label": "Data Analyst",
            "description": "Exploratory data analysis & statistical profiling",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Data Analyst"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "timeseries",
            "cmd": "@agent timeseries ",
            "icon": "⏳",
            "category": "tabular",
            "label": "Time-Series",
            "description": "Time-series forecasting with Pareto horizon",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Time-Series"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "predict",
            "cmd": "@agent predict ",
            "icon": "🎯",
            "category": "tabular",
            "label": "AutoML Predict",
            "description": "Target variable inference on tabular models",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for AutoML Predict"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "decision",
            "cmd": "@agent decision ",
            "icon": "⚖️",
            "category": "tabular",
            "label": "Decision Engine",
            "description": "Prescriptive decision optimization & counterfactuals",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Decision Engine"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "tabular_classification",
            "cmd": "@agent tabular-classification ",
            "icon": "🏷️",
            "category": "tabular",
            "label": "Tabular Classify",
            "description": "Gradient-boosted decision trees and ensemble classifiers",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Tabular Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "tabular_regression",
            "cmd": "@agent tabular-regression ",
            "icon": "📉",
            "category": "tabular",
            "label": "Tabular Regress",
            "description": "Continuous target estimation and causal effect regression",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Tabular Regress"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "feature_engineering",
            "cmd": "@agent feature-engineering ",
            "icon": "⚙️",
            "category": "tabular",
            "label": "Feature Engineer",
            "description": "Automated polynomial, categorical, and interaction features",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Feature Engineer"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "data_clean",
            "cmd": "@agent data-clean ",
            "icon": "🧹",
            "category": "tabular",
            "label": "Dataset Cleaner",
            "description": "Imputation, outlier removal, and schema validation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Dataset Cleaner"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "correlation_matrix",
            "cmd": "@agent correlation ",
            "icon": "🔢",
            "category": "tabular",
            "label": "Correlation Matrix",
            "description": "Pearson, Spearman, and mutual information correlation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Correlation Matrix"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "anomaly_detection",
            "cmd": "@agent anomaly-detection ",
            "icon": "🚨",
            "category": "tabular",
            "label": "Anomaly Detection",
            "description": "Isolation Forest and Local Outlier Factor anomaly scoring",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Anomaly Detection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "pareto_frontier",
            "cmd": "@agent pareto ",
            "icon": "📐",
            "category": "tabular",
            "label": "Pareto Optimizer",
            "description": "Multi-objective trade-off surface computation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Pareto Optimizer"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "clustering",
            "cmd": "@agent clustering ",
            "icon": "🫧",
            "category": "tabular",
            "label": "Data Clustering",
            "description": "K-Means, HDBSCAN, and spectral clustering partitions",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Data Clustering"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "model_interpretability",
            "cmd": "@agent shap-explain ",
            "icon": "💡",
            "category": "tabular",
            "label": "SHAP Interpretability",
            "description": "Shapley additive explanations and feature importance",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for SHAP Interpretability"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "vision",
            "cmd": "@agent vision ",
            "icon": "👁️",
            "category": "vision",
            "label": "Vision Analysis",
            "description": "Object detection, OCR, and visual Q&A",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Vision Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_classification",
            "cmd": "@agent image-classification ",
            "icon": "🏷️",
            "category": "vision",
            "label": "Image Classify",
            "description": "Zero-shot vision classification across open models",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "object_detection",
            "cmd": "@agent object-detection ",
            "icon": "📦",
            "category": "vision",
            "label": "Object Detection",
            "description": "Visual bounding boxes and multi-target detection",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Object Detection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "vqa",
            "cmd": "@agent vqa ",
            "icon": "❓",
            "category": "vision",
            "label": "Visual QA",
            "description": "Direct Q&A on attached images & visual assets",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Visual QA"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_segmentation",
            "cmd": "@agent image-segmentation ",
            "icon": "✂️",
            "category": "vision",
            "label": "Image Segment",
            "description": "Semantic and instance pixel-level segmentation masks",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Segment"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text_to_image",
            "cmd": "@agent text-to-image ",
            "icon": "🎨",
            "category": "vision",
            "label": "Text to Image",
            "description": "High-fidelity diffusion image generation from prompt",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text to Image"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_to_text",
            "cmd": "@agent image-to-text ",
            "icon": "📝",
            "category": "vision",
            "label": "Image Captioning",
            "description": "Dense visual captioning and narrative extraction",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Captioning"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_to_image",
            "cmd": "@agent image-to-image ",
            "icon": "🖼️",
            "category": "vision",
            "label": "Image to Image",
            "description": "Style transfer, super-resolution, and image refinement",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image to Image"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "depth_estimation",
            "cmd": "@agent depth-estimation ",
            "icon": "📏",
            "category": "vision",
            "label": "Depth Estimation",
            "description": "Monocular 3D depth map and surface normal estimation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Depth Estimation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "doc_vqa",
            "cmd": "@agent doc-vqa ",
            "icon": "📄",
            "category": "vision",
            "label": "Document VQA",
            "description": "Visual document understanding on invoices, receipts & forms",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Document VQA"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "zero_shot_image",
            "cmd": "@agent zero-shot-image ",
            "icon": "🎯",
            "category": "vision",
            "label": "Zero-Shot Image",
            "description": "Open-vocabulary image classification without fine-tuning",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Zero-Shot Image"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "zero_shot_detect",
            "cmd": "@agent zero-shot-detect ",
            "icon": "🔍",
            "category": "vision",
            "label": "Zero-Shot Detect",
            "description": "Open-vocabulary bounding box object localization",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Zero-Shot Detect"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "mask_generation",
            "cmd": "@agent mask-generation ",
            "icon": "🎭",
            "category": "vision",
            "label": "Mask Generation",
            "description": "Segment Anything (SAM) promptable foreground masks",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Mask Generation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "keypoint_detection",
            "cmd": "@agent keypoint-detection ",
            "icon": "📍",
            "category": "vision",
            "label": "Keypoint Detect",
            "description": "Human pose, facial landmarks, and skeletal joint tracking",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Keypoint Detect"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "video_classification",
            "cmd": "@agent video-classification ",
            "icon": "🎬",
            "category": "vision",
            "label": "Video Classify",
            "description": "Action recognition, temporal scene cuts, and video tags",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Video Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text_to_video",
            "cmd": "@agent text-to-video ",
            "icon": "📹",
            "category": "vision",
            "label": "Text to Video",
            "description": "Temporal video sequence generation from text description",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text to Video"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "unconditional_image",
            "cmd": "@agent unconditional-image ",
            "icon": "✨",
            "category": "vision",
            "label": "Image Synthesis",
            "description": "Unconditional generative synthesis from learned priors",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Synthesis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "ocr",
            "cmd": "@agent ocr ",
            "icon": "🔤",
            "category": "vision",
            "label": "OCR Text Extract",
            "description": "Multi-language printed and handwritten optical text reading",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for OCR Text Extract"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "face_detection",
            "cmd": "@agent face-detection ",
            "icon": "👤",
            "category": "vision",
            "label": "Face Detection",
            "description": "Facial bounding boxes, expression, and demographic cues",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Face Detection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_enhance",
            "cmd": "@agent image-enhance ",
            "icon": "🌟",
            "category": "vision",
            "label": "Image Super-Res",
            "description": "Denoising, deblurring, and 4x AI resolution upscaling",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Super-Res"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "inpainting",
            "cmd": "@agent inpainting ",
            "icon": "🖌️",
            "category": "vision",
            "label": "Image Inpainting",
            "description": "Masked area reconstruction and contextual object removal",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Image Inpainting"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "image_similarity",
            "cmd": "@agent image-similarity ",
            "icon": "🪞",
            "category": "vision",
            "label": "Visual Similarity",
            "description": "CLIP embedding cosine similarity between images",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Visual Similarity"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "nsfw_detect",
            "cmd": "@agent nsfw-detect ",
            "icon": "🛡️",
            "category": "vision",
            "label": "NSFW Filter",
            "description": "Safety filtering, sensitive content, and moderation check",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for NSFW Filter"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "scene_understanding",
            "cmd": "@agent scene-understanding ",
            "icon": "🏞️",
            "category": "vision",
            "label": "Scene Parsing",
            "description": "Indoor/outdoor holistic scene topology and spatial parsing",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Scene Parsing"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "color_palette",
            "cmd": "@agent color-palette ",
            "icon": "🎨",
            "category": "vision",
            "label": "Palette Extraction",
            "description": "Dominant hexadecimal color palette and visual harmony",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Palette Extraction"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "asr",
            "cmd": "@agent asr ",
            "icon": "🎙️",
            "category": "audio",
            "label": "Speech-to-Text",
            "description": "Automatic speech recognition via Whisper models",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Speech-to-Text"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "tts",
            "cmd": "@agent tts ",
            "icon": "🔊",
            "category": "audio",
            "label": "Text-to-Speech",
            "description": "Text synthesis into natural audible speech",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text-to-Speech"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "audio",
            "cmd": "@agent audio ",
            "icon": "🎵",
            "category": "audio",
            "label": "Audio Classify",
            "description": "Sound event detection & voice activity analysis",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Audio Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "vad",
            "cmd": "@agent vad ",
            "icon": "🗣️",
            "category": "audio",
            "label": "Voice Activity",
            "description": "Real-time speech vs silence endpoint segmentation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Voice Activity"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "audio_to_audio",
            "cmd": "@agent audio-to-audio ",
            "icon": "🎚️",
            "category": "audio",
            "label": "Audio Denoise",
            "description": "Background noise cancellation and voice isolation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Audio Denoise"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text_to_audio",
            "cmd": "@agent text-to-audio ",
            "icon": "🎶",
            "category": "audio",
            "label": "Text to Sound",
            "description": "Synthesize custom sound effects and acoustic ambiances",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text to Sound"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "speaker_diarization",
            "cmd": "@agent speaker-diarization ",
            "icon": "👥",
            "category": "audio",
            "label": "Speaker Diarization",
            "description": "Who spoke when: multi-speaker segmentation & clustering",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Speaker Diarization"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "speaker_id",
            "cmd": "@agent speaker-id ",
            "icon": "🆔",
            "category": "audio",
            "label": "Speaker ID",
            "description": "Voiceprint embedding verification and speaker matching",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Speaker ID"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "music_gen",
            "cmd": "@agent music-gen ",
            "icon": "🎼",
            "category": "audio",
            "label": "Music Generation",
            "description": "Instrumental and polyphonic music generation from prompts",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Music Generation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "sound_event",
            "cmd": "@agent sound-event ",
            "icon": "🔔",
            "category": "audio",
            "label": "Sound Event Detect",
            "description": "Identify siren, glass break, baby cry, and environmental cues",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Sound Event Detect"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "speech_enhance",
            "cmd": "@agent speech-enhance ",
            "icon": "🎧",
            "category": "audio",
            "label": "Speech Enhance",
            "description": "Spectral restoration and vocal clarity enhancement",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Speech Enhance"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "source_separation",
            "cmd": "@agent source-separation ",
            "icon": "✂️",
            "category": "audio",
            "label": "Audio Separation",
            "description": "Stems splitting: vocals, drums, bass, and instruments",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Audio Separation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "voice_emotion",
            "cmd": "@agent voice-emotion ",
            "icon": "😊",
            "category": "audio",
            "label": "Voice Emotion",
            "description": "Prosodic speech emotion and affective state recognition",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Voice Emotion"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "audio_lang_id",
            "cmd": "@agent audio-lang-id ",
            "icon": "🌍",
            "category": "audio",
            "label": "Spoken Language ID",
            "description": "Identify spoken language across 100+ global dialects",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Spoken Language ID"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "tempo",
            "cmd": "@agent tempo ",
            "icon": "⏱️",
            "category": "audio",
            "label": "Tempo & BPM",
            "description": "Rhythm tracking, beat onset, and BPM tempo estimation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Tempo & BPM"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "nlp",
            "cmd": "@agent nlp ",
            "icon": "📝",
            "category": "nlp",
            "label": "NLP Pipeline",
            "description": "Sentiment, NER, translation, and text classification",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for NLP Pipeline"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text_generation",
            "cmd": "@agent text-generation ",
            "icon": "✍️",
            "category": "nlp",
            "label": "Text Generation",
            "description": "Open-ended causal text completion and synthesis",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text Generation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text2text",
            "cmd": "@agent text2text ",
            "icon": "🔄",
            "category": "nlp",
            "label": "Text-to-Text",
            "description": "Seq2Seq transformation, rewriting, and standardization",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text-to-Text"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "translation",
            "cmd": "@agent translation ",
            "icon": "🌐",
            "category": "nlp",
            "label": "Translation",
            "description": "Neural machine translation across 200+ languages",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Translation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "question_answering",
            "cmd": "@agent question-answering ",
            "icon": "💬",
            "category": "nlp",
            "label": "Question Answering",
            "description": "Extractive and generative reading comprehension",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Question Answering"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "table_qa",
            "cmd": "@agent table-qa ",
            "icon": "📊",
            "category": "nlp",
            "label": "Table QA",
            "description": "Direct natural language querying over tabular structures",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Table QA"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "zero_shot",
            "cmd": "@agent zero-shot ",
            "icon": "🎯",
            "category": "nlp",
            "label": "Zero-Shot Text",
            "description": "Categorize text into arbitrary candidate label sets",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Zero-Shot Text"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "text_classification",
            "cmd": "@agent text-classification ",
            "icon": "🏷️",
            "category": "nlp",
            "label": "Text Classify",
            "description": "Fine-tuned intent, category, and sentiment labels",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "token_classification",
            "cmd": "@agent token-classification ",
            "icon": "🔠",
            "category": "nlp",
            "label": "Token Classify",
            "description": "Token-level entity, POS tag, and boundary classification",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Token Classify"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "sentence_similarity",
            "cmd": "@agent sentence-similarity ",
            "icon": "🔗",
            "category": "nlp",
            "label": "Sentence Similarity",
            "description": "Bi-encoder semantic similarity scoring and ranking",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Sentence Similarity"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "conversational",
            "cmd": "@agent conversational ",
            "icon": "🗣️",
            "category": "nlp",
            "label": "Chat Assistant",
            "description": "Multi-turn persona-grounded conversational agent",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Chat Assistant"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "fill_mask",
            "cmd": "@agent fill-mask ",
            "icon": "🎭",
            "category": "nlp",
            "label": "Masked LM Fill",
            "description": "Predict masked tokens via bidirectional context",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Masked LM Fill"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "multiple_choice",
            "cmd": "@agent multiple-choice ",
            "icon": "🔘",
            "category": "nlp",
            "label": "Multiple Choice",
            "description": "Select most plausible completion from candidate options",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Multiple Choice"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "sentiment",
            "cmd": "@agent sentiment ",
            "icon": "❤️",
            "category": "nlp",
            "label": "Sentiment Analysis",
            "description": "Positive, negative, neutral, and emotional intensity",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Sentiment Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "summarize_text",
            "cmd": "@agent summarize-text ",
            "icon": "📜",
            "category": "nlp",
            "label": "Text Summarize",
            "description": "Abstractive and extractive multi-paragraph summarization",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text Summarize"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "grammar",
            "cmd": "@agent grammar ",
            "icon": "✍️",
            "category": "nlp",
            "label": "Grammar Check",
            "description": "Orthographic, syntactic, and stylistic error correction",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Grammar Check"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "paraphrase",
            "cmd": "@agent paraphrase ",
            "icon": "🔁",
            "category": "nlp",
            "label": "Paraphraser",
            "description": "Alternative phrasing preserving core semantic intent",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Paraphraser"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "ner",
            "cmd": "@agent ner ",
            "icon": "🏷️",
            "category": "nlp",
            "label": "Named Entity Rec",
            "description": "Extract names, locations, dates, and organizations",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Named Entity Rec"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "keywords",
            "cmd": "@agent keywords ",
            "icon": "🔑",
            "category": "nlp",
            "label": "Keyword Extractor",
            "description": "KeyBERT and TF-IDF keyphrase significance extraction",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Keyword Extractor"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "semantic_search",
            "cmd": "@agent semantic-search ",
            "icon": "🔎",
            "category": "nlp",
            "label": "Semantic Search",
            "description": "Dense vector retrieval over embedded corpus documents",
            "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "description": "'search' to query, 'add' to index documents, 'demo' to run demo"}, "query": {"type": "string", "description": "Search query (for 'search' action)"}, "documents_path": {"type": "string", "description": "Path to documents to add (for 'add' action)"}, "top_k": {"type": "integer", "description": "Number of results (default: 5)"}, "use_hyde": {"type": "boolean", "description": "Use interactive HyDE refinement"}, "hyde_variants": {"type": "boolean", "description": "Generate multiple HyDE variants"}}, "required": ["action"]}
        }),
        serde_json::json!({
            "name": "hallucination_eval",
            "cmd": "@agent hallucination-eval ",
            "icon": "🛡️",
            "category": "nlp",
            "label": "Hallucination Check",
            "description": "Cross-reference text claims against source ground truth",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Hallucination Check"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "prompt_expand",
            "cmd": "@agent prompt-expand ",
            "icon": "🪄",
            "category": "nlp",
            "label": "Prompt Expander",
            "description": "Enrich sparse prompts with context and constraints",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Prompt Expander"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "chain_of_thought",
            "cmd": "@agent chain-of-thought ",
            "icon": "🧠",
            "category": "nlp",
            "label": "Chain-of-Thought",
            "description": "Step-by-step rationalized deductive derivation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Chain-of-Thought"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "toxicity",
            "cmd": "@agent toxicity ",
            "icon": "⚠️",
            "category": "nlp",
            "label": "Toxicity Detection",
            "description": "Identify profanity, harassment, hate speech, and threats",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Toxicity Detection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "intent",
            "cmd": "@agent intent ",
            "icon": "🎯",
            "category": "nlp",
            "label": "Intent Recognition",
            "description": "Identify actionable user objective and routing class",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Intent Recognition"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "relation_extract",
            "cmd": "@agent relation-extract ",
            "icon": "🕸️",
            "category": "nlp",
            "label": "Relation Extraction",
            "description": "Extract subject-predicate-object knowledge triples",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Relation Extraction"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "topic_model",
            "cmd": "@agent topic-model ",
            "icon": "🗂️",
            "category": "nlp",
            "label": "Topic Modeling",
            "description": "Unsupervised discovery of semantic themes across docs",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Topic Modeling"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "simplify",
            "cmd": "@agent simplify ",
            "icon": "💡",
            "category": "nlp",
            "label": "Text Simplifier",
            "description": "Convert dense academic jargon into plain English",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Text Simplifier"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "lang_detect",
            "cmd": "@agent lang-detect ",
            "icon": "🔤",
            "category": "nlp",
            "label": "Language Detection",
            "description": "Determine ISO language code from raw text snippet",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Language Detection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "citation",
            "cmd": "@agent citation ",
            "icon": "📖",
            "category": "nlp",
            "label": "Citation Generator",
            "description": "Generate BibTeX, APA, IEEE, and Chicago references",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Citation Generator"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "code",
            "cmd": "@agent code ",
            "icon": "💻",
            "category": "code",
            "label": "Code Intelligence",
            "description": "Code generation, vulnerability scanning & refactoring",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Intelligence"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "code_gen",
            "cmd": "@agent code-gen ",
            "icon": "⚡",
            "category": "code",
            "label": "Code Generation",
            "description": "Multi-language function and module synthesis",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Generation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "infill",
            "cmd": "@agent infill ",
            "icon": "🧩",
            "category": "code",
            "label": "Code Infilling",
            "description": "Fill-in-the-middle code completion from context",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Infilling"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "code_review",
            "cmd": "@agent code-review ",
            "icon": "🧐",
            "category": "code",
            "label": "Code Review",
            "description": "Automated code review for maintainability & bugs",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Review"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "refactor",
            "cmd": "@agent refactor ",
            "icon": "🔨",
            "category": "code",
            "label": "Code Refactoring",
            "description": "Restructure code without altering functional behavior",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Refactoring"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "test_gen",
            "cmd": "@agent test-gen ",
            "icon": "🧪",
            "category": "code",
            "label": "Unit Test Gen",
            "description": "Generate high-coverage unit tests and assertions",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Unit Test Gen"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "graph_index",
            "cmd": "@agent graph-index ",
            "icon": "🕸️",
            "category": "code",
            "label": "Code Graph Index",
            "description": "Extract AST relationships & call graphs",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Graph Index"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "rest_rl",
            "cmd": "@agent rest-rl status",
            "icon": "⚡",
            "category": "system",
            "label": "ReST-RL Daemon",
            "description": "Sub-8ms Windows Job Object RL repair engine",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for ReST-RL Daemon"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "ast_parse",
            "cmd": "@agent ast-parse ",
            "icon": "🌲",
            "category": "code",
            "label": "AST Tree Parse",
            "description": "Parse source into concrete syntax trees and tokens",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for AST Tree Parse"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "docstring",
            "cmd": "@agent docstring ",
            "icon": "📝",
            "category": "code",
            "label": "Docstring Gen",
            "description": "Synthesize Google/Sphinx/Rustdoc documentation comments",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Docstring Gen"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "type_infer",
            "cmd": "@agent type-infer ",
            "icon": "🏷️",
            "category": "code",
            "label": "Type Inference",
            "description": "Infer strong static types for dynamic languages",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Type Inference"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "sql",
            "cmd": "@agent sql ",
            "icon": "🗄️",
            "category": "code",
            "label": "SQL Generator",
            "description": "Translate natural language queries into optimized SQL",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for SQL Generator"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "regex",
            "cmd": "@agent regex ",
            "icon": "🔍",
            "category": "code",
            "label": "Regex Builder",
            "description": "Construct and explain complex regular expressions",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Regex Builder"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "git_commit",
            "cmd": "@agent git-commit ",
            "icon": "📦",
            "category": "code",
            "label": "Git Commit Message",
            "description": "Generate Conventional Commit messages from diffs",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Git Commit Message"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "lint_fix",
            "cmd": "@agent lint-fix ",
            "icon": "🪛",
            "category": "code",
            "label": "Automated Lint Fix",
            "description": "Auto-repair linting, formatting, and stylistic warnings",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Automated Lint Fix"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "perf_audit",
            "cmd": "@agent perf-audit ",
            "icon": "⏱️",
            "category": "code",
            "label": "Performance Profiler",
            "description": "Algorithmic complexity Big-O analysis and bottlenecks",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Performance Profiler"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "deps",
            "cmd": "@agent deps ",
            "icon": "📦",
            "category": "code",
            "label": "Dependency Analysis",
            "description": "Detect obsolete or vulnerable third-party dependencies",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Dependency Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "api_docs",
            "cmd": "@agent api-docs ",
            "icon": "📚",
            "category": "code",
            "label": "API Doc Generator",
            "description": "Generate OpenAPI / Swagger specifications from code",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for API Doc Generator"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "code_translate",
            "cmd": "@agent code-translate ",
            "icon": "🔀",
            "category": "code",
            "label": "Code Translation",
            "description": "Transpile code between Python, Rust, TS, Go, C++",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Code Translation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "dockerfile",
            "cmd": "@agent dockerfile ",
            "icon": "🐳",
            "category": "code",
            "label": "Dockerfile Gen",
            "description": "Generate multi-stage secure container Dockerfiles",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Dockerfile Gen"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "security",
            "cmd": "@agent security ",
            "icon": "🛡️",
            "category": "pe_binary",
            "label": "Security Analysis",
            "description": "Malware, phishing, PII, and exploit detection",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Security Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "pe",
            "cmd": "@agent pe ",
            "icon": "🔬",
            "category": "pe_binary",
            "label": "PE Header Forensics",
            "description": "Extract PE headers and binary forensics from .exe/.dll",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for PE Header Forensics"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "vuln_scan",
            "cmd": "@agent vuln-scan ",
            "icon": "🪲",
            "category": "pe_binary",
            "label": "Vulnerability Scan",
            "description": "Static analysis for buffer overflows, use-after-free, injection",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Vulnerability Scan"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "malware_analysis",
            "cmd": "@agent malware-analysis ",
            "icon": "🦠",
            "category": "pe_binary",
            "label": "Malware Analysis",
            "description": "Heuristic static malware indicators and evasion patterns",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Malware Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "mem_forensics",
            "cmd": "@agent mem-forensics ",
            "icon": "💾",
            "category": "pe_binary",
            "label": "Memory Forensics",
            "description": "Analyze core dumps, heap allocations, and stack frames",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Memory Forensics"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "pii_scan",
            "cmd": "@agent pii-scan ",
            "icon": "🔒",
            "category": "pe_binary",
            "label": "PII Scanner",
            "description": "Discover SSNs, credit cards, emails, and confidential data",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for PII Scanner"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "entropy",
            "cmd": "@agent entropy ",
            "icon": "📐",
            "category": "pe_binary",
            "label": "Entropy Scan",
            "description": "Compute Shannon entropy to detect packed or encrypted sections",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Entropy Scan"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "strings",
            "cmd": "@agent strings ",
            "icon": "🧵",
            "category": "pe_binary",
            "label": "Strings Extractor",
            "description": "Extract and filter printable ASCII and Unicode strings",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Strings Extractor"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "exploit",
            "cmd": "@agent exploit ",
            "icon": "💥",
            "category": "pe_binary",
            "label": "Exploit Analyzer",
            "description": "Assess proof-of-concept exploits and remediation steps",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Exploit Analyzer"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "decompile",
            "cmd": "@agent decompile ",
            "icon": "🧬",
            "category": "pe_binary",
            "label": "Decompilation",
            "description": "Explain disassembled assembly and high-level pseudocode",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Decompilation"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "net_audit",
            "cmd": "@agent net-audit ",
            "icon": "🌐",
            "category": "pe_binary",
            "label": "Network Traffic Audit",
            "description": "Inspect PCAP captures and suspicious beaconing traffic",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Network Traffic Audit"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "yara",
            "cmd": "@agent yara ",
            "icon": "📜",
            "category": "pe_binary",
            "label": "YARA Rule Gen",
            "description": "Synthesize YARA detection rules for indicators of compromise",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for YARA Rule Gen"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "tls_inspect",
            "cmd": "@agent tls-inspect ",
            "icon": "🔐",
            "category": "pe_binary",
            "label": "TLS Inspector",
            "description": "Verify certificates, cipher suites, and handshake health",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for TLS Inspector"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "owasp",
            "cmd": "@agent owasp ",
            "icon": "🛡️",
            "category": "pe_binary",
            "label": "OWASP Audit",
            "description": "Comprehensive audit against OWASP Top 10 vulnerabilities",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for OWASP Audit"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "packer_detect",
            "cmd": "@agent packer-detect ",
            "icon": "📦",
            "category": "pe_binary",
            "label": "Packer Detector",
            "description": "Detect UPX, Themida, VMProtect, and known binary packers",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Packer Detector"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "secret_scan",
            "cmd": "@agent secret-scan ",
            "icon": "🔑",
            "category": "pe_binary",
            "label": "Secret Leak Scan",
            "description": "Identify committed API tokens, private keys, and passwords",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Secret Leak Scan"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "medical",
            "cmd": "@agent medical ",
            "icon": "🏥",
            "category": "multimodal",
            "label": "Medical Analysis",
            "description": "Clinical notes analysis, biomedical research summarization",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Medical Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "legal",
            "cmd": "@agent legal ",
            "icon": "⚖️",
            "category": "multimodal",
            "label": "Legal Review",
            "description": "Contract clause analysis, indemnification and liability audit",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Legal Review"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "finance",
            "cmd": "@agent finance ",
            "icon": "💰",
            "category": "multimodal",
            "label": "Financial Analysis",
            "description": "Balance sheet parsing, earnings call sentiment & ratios",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Financial Analysis"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "robotics",
            "cmd": "@agent robotics ",
            "icon": "🤖",
            "category": "multimodal",
            "label": "Robotics Kinematics",
            "description": "Inverse kinematics, trajectory planning, and actuator dynamics",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Robotics Kinematics"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "rl",
            "cmd": "@agent rl ",
            "icon": "🎮",
            "category": "multimodal",
            "label": "Reinforcement Learning",
            "description": "Markov decision processes, Q-learning, and policy gradients",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Reinforcement Learning"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "graph_ml",
            "cmd": "@agent graph-ml ",
            "icon": "🕸️",
            "category": "multimodal",
            "label": "Graph ML",
            "description": "Node classification and link prediction on knowledge graphs",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Graph ML"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "chemistry",
            "cmd": "@agent chemistry ",
            "icon": "🧪",
            "category": "multimodal",
            "label": "Molecular Chemistry",
            "description": "SMILES molecular representation and reaction properties",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Molecular Chemistry"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "climate",
            "cmd": "@agent climate ",
            "icon": "🌍",
            "category": "multimodal",
            "label": "Climate Science",
            "description": "Atmospheric sensor modeling and weather trend forecasting",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Climate Science"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "patent",
            "cmd": "@agent patent ",
            "icon": "📜",
            "category": "multimodal",
            "label": "Patent Prior Art",
            "description": "Cross-reference claims and patent infringement discovery",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Patent Prior Art"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "tab_domain",
            "cmd": "@agent tab-domain ",
            "icon": "📑",
            "category": "multimodal",
            "label": "Domain Tabular",
            "description": "Healthcare and financial domain-specific tabular modeling",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Domain Tabular"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "fusion",
            "cmd": "@agent fusion ",
            "icon": "🧠",
            "category": "multimodal",
            "label": "Multimodal Fusion",
            "description": "Cross-modal late fusion combining vision, text, and data",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Multimodal Fusion"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "av_align",
            "cmd": "@agent av-align ",
            "icon": "🎬",
            "category": "multimodal",
            "label": "Audio-Visual Grounding",
            "description": "Align audio spectrogram events with visual video frames",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Audio-Visual Grounding"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "physics",
            "cmd": "@agent physics ",
            "icon": "⚛️",
            "category": "multimodal",
            "label": "Physics Modeling",
            "description": "Hamiltonian and classical Newtonian mechanics simulations",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Physics Modeling"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "bioinformatics",
            "cmd": "@agent bioinformatics ",
            "icon": "🧬",
            "category": "multimodal",
            "label": "Bioinformatics",
            "description": "DNA sequence alignment and protein folding predictions",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Bioinformatics"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "geospatial",
            "cmd": "@agent geospatial ",
            "icon": "🗺️",
            "category": "multimodal",
            "label": "GIS Geospatial",
            "description": "Geohash coordinate queries and satellite imagery analytics",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for GIS Geospatial"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "goal",
            "cmd": "@agent goal ",
            "icon": "🎯",
            "category": "agent",
            "label": "Autonomous Goal",
            "description": "Multi-turn autonomous goal-directed agent loop",
            "inputSchema": {"type": "object", "properties": {"goal": {"type": "string", "description": "High-level goal description"}}, "required": ["goal"]}
        }),
        serde_json::json!({
            "name": "plan",
            "cmd": "@agent plan ",
            "icon": "📋",
            "category": "agent",
            "label": "Planning Engine",
            "description": "Deconstruct complex tasks into executable steps",
            "inputSchema": {"type": "object", "properties": {"task": {"type": "string", "description": "Task description to plan"}}, "required": ["task"]}
        }),
        serde_json::json!({
            "name": "grill_me",
            "cmd": "@agent grill-me ",
            "icon": "🔥",
            "category": "agent",
            "label": "Grill Me Mode",
            "description": "Adversarial requirements interview & stress-testing",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Grill Me Mode"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "boost",
            "cmd": "@agent boost ",
            "icon": "🚀",
            "category": "agent",
            "label": "Reasoning Boost",
            "description": "Deep multi-perspective reasoning & rigorous verification",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Complex prompt or query"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "agentic_loop",
            "cmd": "@agent agentic-loop ",
            "icon": "🔄",
            "category": "agent",
            "label": "Agentic Loop",
            "description": "Recursive auto-chaining for up to 256k tokens",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Prompt for large generation"}, "target_tokens": {"type": "integer", "description": "Target token budget (up to 262144)"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "explain",
            "cmd": "@agent explain ",
            "icon": "💡",
            "category": "agent",
            "label": "Explain Concept",
            "description": "Step-by-step reasoning and deep conceptual explanation",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Explain Concept"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "cot",
            "cmd": "@agent cot ",
            "icon": "🧠",
            "category": "agent",
            "label": "Chain-of-Thought",
            "description": "Explicit chain-of-thought derivation with evidence checks",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Chain-of-Thought"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "critic",
            "cmd": "@agent critic ",
            "icon": "🧐",
            "category": "agent",
            "label": "Self-Critique",
            "description": "Adversarially evaluate draft solutions for edge case flaws",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Self-Critique"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "synthesize",
            "cmd": "@agent synthesize ",
            "icon": "🪢",
            "category": "agent",
            "label": "Synthesis Engine",
            "description": "Synthesize multiple divergent viewpoints into one consensus",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Synthesis Engine"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "decompose",
            "cmd": "@agent decompose ",
            "icon": "🧩",
            "category": "agent",
            "label": "Decomposition",
            "description": "Break massive requirements into atomic subtasks",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Decomposition"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "delegate",
            "cmd": "@agent delegate ",
            "icon": "🤝",
            "category": "agent",
            "label": "Subagent Delegate",
            "description": "Dispatch specialized micro-tasks to background subagents",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Subagent Delegate"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "verify",
            "cmd": "@agent verify ",
            "icon": "✅",
            "category": "agent",
            "label": "Step Verification",
            "description": "Formal verification of outputs against input constraints",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Step Verification"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "backtrack",
            "cmd": "@agent backtrack ",
            "icon": "↩️",
            "category": "agent",
            "label": "Backtrack Rollback",
            "description": "Rollback erroneous reasoning branches to previous valid state",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Backtrack Rollback"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "reflection",
            "cmd": "@agent reflection ",
            "icon": "🪞",
            "category": "agent",
            "label": "Error Reflection",
            "description": "Analyze execution failure traces and synthesize self-corrections",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Error Reflection"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "adversarial",
            "cmd": "@agent adversarial ",
            "icon": "⚔️",
            "category": "agent",
            "label": "Adversarial Test",
            "description": "Subject assumptions and architecture to worst-case stresses",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Adversarial Test"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "update",
            "cmd": "@agent update",
            "icon": "⚡",
            "category": "system",
            "label": "Update Catalog",
            "description": "Fast curated update (~6,500 models & dynamic Ollama sizing)",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Update Catalog"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "updatedb",
            "cmd": "@agent updatedb",
            "icon": "🚀",
            "category": "system",
            "label": "Full Registry Crawler",
            "description": "Crawl all 2M+ models from Hugging Face Hub",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Full Registry Crawler"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "active_model",
            "cmd": "@agent active-model",
            "icon": "🤖",
            "category": "system",
            "label": "Active Model",
            "description": "Inspect currently loaded Ollama model & memory",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for Active Model"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "sys_info",
            "cmd": "@agent sys-info",
            "icon": "🖥️",
            "category": "system",
            "label": "System Info",
            "description": "Hardware resources, runtime RAM/VRAM, and active models",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for System Info"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "fusion_status",
            "cmd": "@agent fusion-status",
            "icon": "🧠",
            "category": "system",
            "label": "ModelFusion Status",
            "description": "Multi-modal catalog count and consensus telemetry",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Input text or instructions for ModelFusion Status"}, "file": {"type": "string", "description": "Optional file path or target dataset"}, "gpu": {"type": "boolean", "description": "Enable GPU acceleration"}}}
        }),
        serde_json::json!({
            "name": "detect_watermark",
            "cmd": "@agent watermark ",
            "icon": "🔍",
            "category": "writing",
            "label": "AI Watermark Detection",
            "description": "Detect statistical AI green-list token watermarks (Kirchenbauer et al.) in text or spatial LSB steganographic anomalies in images",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Optional inline text or text file path to evaluate for token watermark"},
                    "image_path": {"type": "string", "description": "Optional absolute path to PNG/JPEG image for LSB entropy scan"}
                }
            }
        }),
        serde_json::json!({
            "name": "writing_boost",
            "cmd": "@agent boost ",
            "icon": "🚀",
            "category": "writing",
            "label": "Writing & Reasoning Boost",
            "description": "High-compute multi-agent / multi-sample reasoning & prose refinement boost (/boost)",
            "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Complex prose, problem, or query to boost"}}, "required": ["prompt"]}
        }),
        serde_json::json!({
            "name": "humanize",
            "cmd": "@agent humanize ",
            "icon": "✍️",
            "category": "writing",
            "label": "Humanize AI Prose",
            "description": "Rewrite passage into natural, fluid human prose using anti-AI stylometry",
            "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "description": "AI-generated text or file path to humanize"}}, "required": ["text"]}
        }),
        serde_json::json!({
            "name": "computer_use",
            "cmd": "@agent computer-use ",
            "icon": "🖥️",
            "category": "agent",
            "label": "OS Computer Use (UI-TARS)",
            "description": "Autonomous OS computer use via UI-TARS multimodal action grounding and screen perception",
            "inputSchema": {"type": "object", "properties": {"goal": {"type": "string", "description": "High-level desktop automation task or goal to execute"}}, "required": ["goal"]}
        }),
    ]
}

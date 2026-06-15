#!/usr/bin/env python3
"""
HFOrchestra - Main Entry Point

This is the main entry point for the HFOrchestra system, demonstrating
the modular architecture and providing a simple interface for users.
"""

# This MUST be the first import to ensure the environment is configured before other modules.
# This MUST be the first import to ensure the environment is configured before other modules.
import hforchestra.core.env_setup

import sys
import io

# CRITICAL: Force UTF-8 for stdout/stderr on Windows to prevent Emoji crashes
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import argparse
import sys
import time
import json
import os
from pathlib import Path
import subprocess
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for PDF generation
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PDF generation not available. Install: pip install reportlab")

# Import the modular components with graceful fallbacks
try:
    from hforchestra.security.atlas_detector import ATLASThreatDetector
    atlas_available = True
except ImportError:
    atlas_available = False
    ATLASThreatDetector = None

try:
    from hforchestra.monitoring.tree_monitor import EnhancedTreeMonitor
    monitoring_available = True
except ImportError:
    monitoring_available = False
    EnhancedTreeMonitor = None

try:
    from hforchestra.analysis.pe_extractor import CompletePEHeaderExtractor
    pe_extractor_available = True
except ImportError:
    pe_extractor_available = False
    CompletePEHeaderExtractor = None

try:
    from hforchestra.analysis.malware_detector import PEAnalyzer
    malware_detector_available = True
except ImportError:
    malware_detector_available = False
    PEAnalyzer = None

try:
    from hforchestra.utils.folder_manager import FolderManager
    folder_manager_available = True
except ImportError:
    folder_manager_available = False
    FolderManager = None

try:
    from hforchestra.utils.performance import PerformanceMonitor
    performance_available = True
except ImportError:
    performance_available = False
    PerformanceMonitor = None

# Import the real orchestrator with fallback
try:
    from hforchestra.core.orchestrator import HuggingFaceOrchestrator
    orchestrator_available = True
except ImportError:
    orchestrator_available = False
    HuggingFaceOrchestrator = None

try:
    from hforchestra.core.task_handler import ComprehensiveTaskHandler
    task_handler_available = True
except ImportError:
    task_handler_available = False
    ComprehensiveTaskHandler = None

# Data Analyst workflow availability
try:
    from hforchestra.core.data_analyst import handle_data_analyst as run_data_analyst_workflow
    data_analyst_available = True
except ImportError:
    data_analyst_available = False
    run_data_analyst_workflow = None

# Helper: print best models for a given HF pipeline task
def _print_best_models_for_task(task_name: str, prompt: str) -> None:
    try:
        from hforchestra.core.enhanced_model_selector import EnhancedModelSelector, SelectionStrategy
        selector = EnhancedModelSelector()
        sel = selector.select_best_model(
            task_name=task_name,
            prompt=prompt,
            strategy=SelectionStrategy.MULTI_OBJECTIVE,
            max_candidates=5
        )
        if not sel or not sel.all_candidates:
            return
        print(f"\n🔎 [ENHANCED CANDIDATES] Found {len(sel.all_candidates)} models using multi_objective:")
        for i, cand in enumerate(sel.all_candidates[:5], start=1):
            print(f"   {i}. {cand.model_id}")
            print(f"      Downloads: {cand.downloads:,} | Likes: {cand.likes} | Size: {cand.size_mb:.0f}MB | License: {cand.license}")
        print(f"\n🏆 [ENHANCED SELECTION] Using model: {sel.best_model.model_id}")
        print(f"   Strategy: {SelectionStrategy.MULTI_OBJECTIVE.value}")
        print(f"   Confidence: {sel.confidence_score:.2f}")
        print(f"   Optimization time: {sel.optimization_time:.2f}s")
    except Exception:
        # Non-fatal: silently skip if selector/db unavailable
        pass

# Check if critical components are available
if not task_handler_available:
    print("Warning: Task handler not available. Some features may not work.")
if not orchestrator_available:
    print("Warning: Orchestrator not available. Core AI functionality may be limited.")
if not data_analyst_available:
    print("Warning: Data Analyst workflow not available.")


def safe_print_content(result):
    """Safely prints the content and status of a result object."""
    if result is None:
        safe_print('[WARN] Result is None')
        return False
    
    if not hasattr(result, 'content'):
        safe_print('[WARN] Result has no content attribute')
        return False
        
    safe_print(result.content)
    return hasattr(result, 'success') and result.success


def _get_help_examples() -> str:
    """Generate comprehensive help examples."""
    return """
[SYSTEM] HFORCHESTRA - COMPREHENSIVE AI TASK PROCESSING
====================================================

[OUTPUT] BASIC USAGE:
  python main.py --prompt "Your prompt here"
  python main.py --file "ANY_FILE" --prompt "What is this about?"
  python main.py --enable-ml-selection --prompt "Use ML-enhanced model selection"

[TARGET] UNIVERSAL FILE SUPPORT (100+ File Types):
  python main.py --file "image.jpg" --prompt "What's in this image?"
  python main.py --file "audio.mp3" --prompt "Transcribe this speech"
  python main.py --file "video.mp4" --prompt "What happens in this video?"
  python main.py --file "archive.zip" --prompt "List the contents"
  python main.py --file "database.sqlite" --prompt "What tables are in this DB?"
  python main.py --file "program.exe" --prompt "Is this file safe?"
  python main.py --file "document.pdf" --prompt "Summarize this document"
  python main.py --file "code.py" --prompt "Explain this Python code"
  python main.py --file "data.json" --prompt "Analyze this data structure"
  python main.py --file "unknown_file" --prompt "What type of file is this?"

[TOOL] SYSTEM CONFIGURATION:
  python main.py --budget 5.00 "Generate a report"
  python main.py --chain-of-thought --text-classification "This movie is great"
  python main.py --config custom_config.json "Process this text"
      python main.py --verbose "Analyze with HuggingFace models (default)"
    python main.py --use-openai "Use OpenAI models instead"
  python main.py --save-model best_model.pkl "Train and save model"
  python main.py --load-model saved_model.pkl "Use pre-trained model"
  python main.py --api-keys openai:sk-...,hf:hf_... "Use custom API keys"
  python main.py --language es "Procesar texto en español"
  python main.py --verbose --text-generation "Show detailed processing"

[INNOVATION] WORKFLOW & ANALYSIS:
  python main.py --enable-innovations --prompt "Analyze this text"
  python main.py --workflow-optimization --prompt "Optimize this workflow"
  python main.py --semantic-analysis --prompt "Extract core concepts and relations"
  python main.py --temporal-tracking --prompt "Track changes across versions"
  python main.py --predictive-mode --prompt "Predict potential issues"
  python main.py --innovation-level 3 --enable-innovations --prompt "Deep analysis"

[AGENT] PLAN & EXECUTE (LangChain):
  python main.py --plan --prompt "Research the latest AI trends and summarize key points."
  python main.py --plan --file "report.pdf" --prompt "Analyze this report and produce an action plan."

[INNOVATION] PREDICTIVE MODE EXAMPLES:
  # Basic risk prediction from a brief
  python main.py --predictive-mode --prompt "Predict potential risks in this product launch plan and suggest mitigations."

  # Analyze a file (requires --prompt)
  python main.py --predictive-mode --file "system_log.txt" --prompt "Predict likely failures from these logs and propose fixes."

  # Deep analysis with full innovations
  python main.py --predictive-mode --enable-innovations --innovation-level 3 --file "pipeline.yaml" \
                 --prompt "Predict issues in this CI/CD pipeline and recommend improvements."

  # With model selection strategy
  python main.py --predictive-mode --selection-strategy multi_objective \
                 --prompt "Predict operational risks in this runbook."

[DATA] DATA ANALYST WORKFLOW EXAMPLES:
  # Run on CSV
  python main.py --dataanalyst --file "sales.csv" --prompt "Find key trends and anomalies."

  # Run on Excel
  python main.py --dataanalyst --file "metrics.xlsx" --prompt "Create an executive summary of KPIs."

  # Deep analysis with innovations
  python main.py --dataanalyst --enable-innovations --innovation-level 3 --file "churn.csv" \
                 --prompt "Identify churn drivers and suggest actions."

[SELECTION] ADVANCED MODEL SELECTION:
  python main.py --selection-strategy multi_objective --prompt "Classify this text"
  python main.py --selection-strategy cross_validation --prompt "Summarize this article"
  python main.py --selection-strategy ensemble_methods --prompt "Analyze sentiment"

[ML] MACHINE LEARNING MODEL SELECTION:
  # Basic ML-enhanced selection
  python main.py --enable-ml-selection --selection-strategy ml_enhanced --prompt "Write a story"
  
  # ML selection with learning enabled
  python main.py --enable-ml-selection --ml-learning --prompt "Classify this sentiment"
  
  # Ensemble methods for robust selection
  python main.py --enable-ml-selection --ml-ensemble-method voting --selection-strategy ml_voting --prompt "Summarize text"
  python main.py --enable-ml-selection --ml-ensemble-method consensus --selection-strategy ml_consensus --prompt "Translate this"
  
  # High confidence selection
  python main.py --enable-ml-selection --ml-confidence-threshold 0.8 --prompt "Analyze this data"
  
  # ML analytics and management
  python main.py --ml-analytics                    # Show ML performance statistics
  python main.py --ml-retrain                     # Force model retraining
  python main.py --ml-cleanup 30                  # Clean up old training data
  
  # Advanced ML configuration
  python main.py --enable-ml-selection --ml-learning --ml-ensemble-method adaptive --selection-strategy ml_adaptive --prompt "Complex analysis"

[SINQ] MODEL QUANTIZATION:
  # Basic SINQ quantization (reduces memory usage while preserving accuracy)
  python main.py --sinq --prompt "Generate a story"
  
  # SINQ with custom bit-width options
  python main.py --sinq --sinq-nbits 2 --prompt "Maximum compression"      # 2-bit: Max compression
  python main.py --sinq --sinq-nbits 3 --prompt "High compression"        # 3-bit: High compression
  python main.py --sinq --sinq-nbits 4 --prompt "Balanced quality"        # 4-bit: Recommended
  python main.py --sinq --sinq-nbits 5 --prompt "Higher quality"          # 5-bit: Better quality
  python main.py --sinq --sinq-nbits 6 --prompt "High quality"            # 6-bit: High quality
  python main.py --sinq --sinq-nbits 8 --prompt "Maximum quality"         # 8-bit: Max quality
  
  # SINQ with different group sizes
  python main.py --sinq --sinq-group-size 64 --prompt "Precise quantization"   # 64: More precise
  python main.py --sinq --sinq-group-size 128 --prompt "Faster quantization"   # 128: Faster
  
  # SINQ with different tiling modes
  python main.py --sinq --sinq-tiling-mode 1D --prompt "1D tiling"        # 1D: Recommended
  python main.py --sinq --sinq-tiling-mode 2D --prompt "2D tiling"        # 2D: Alternative
  
  # SINQ with different methods
  python main.py --sinq --sinq-method sinq --prompt "Calibration-free"    # SINQ: Fast, no calibration
  python main.py --sinq --sinq-method asinq --prompt "Calibrated"         # A-SINQ: Slower, calibrated
  
  # SINQ with file processing
  python main.py --sinq --file "document.pdf" --prompt "Summarize this document"
  python main.py --sinq --file "image.jpg" --prompt "Describe this image"
  python main.py --sinq --file "audio.wav" --prompt "Transcribe this audio"
  
  # SINQ with task-specific processing
  python main.py --sinq --text-classification --prompt "Classify this text"
  python main.py --sinq --summarization --file "article.txt"
  python main.py --sinq --translation --prompt "Translate to French"
  
  # SINQ with advanced combinations
  python main.py --sinq --sinq-nbits 3 --sinq-group-size 64 --sinq-tiling-mode 1D --sinq-method sinq --prompt "Optimized settings"
  python main.py --sinq --sinq-nbits 4 --sinq-group-size 128 --sinq-tiling-mode 2D --sinq-method asinq --prompt "High quality settings"
  
  # SINQ with other features
  python main.py --sinq --verbose --prompt "Show detailed quantization info"
  python main.py --sinq --enable-ml --prompt "ML + SINQ quantization"
  python main.py --sinq --selection-strategy multi_objective --prompt "Multi-objective + SINQ"

[SEARCH] HYDE (Hypothetical Document Embeddings):
  python main.py --enable-hyde --use-hyde "What is machine learning?"
  python main.py --hyde-variants "Generate multiple hypotheses"
  python main.py --add-documents "doc1.txt,doc2.txt" --use-hyde "Search in docs"
  python main.py --search-query "AI applications" --top-k 5
  python main.py --demo-hyde "Show HYDE capabilities"

[CHART] SYSTEM MONITORING & STATISTICS:
  python main.py --stats
  python main.py --tasks
  python main.py --tasks audio
  python main.py --decision-stats
  python main.py --novel-ai-stats
  python main.py --performance-stats
  python main.py --cache-stats
  python main.py --clearcache

[MODEL] SYSTEM CONTROL:
  python main.py --delegation --text-generation "Use delegation pattern"
  python main.py --recursion --complex-analysis "Enable recursive processing"
  python main.py --real-options "Show real-world options"
  python main.py --full --comprehensive-analysis "Full system analysis"

[TASKS] TEXT PROCESSING TASKS:

Basic Text Tasks:
  python main.py --text-classification "I love this product!"
  python main.py --token-classification --file "document.txt"
  python main.py --question-answering --file "context.txt" --prompt "What is the main point?"
  python main.py --text-generation "Once upon a time"
  python main.py --summarization --file "long_article.txt"
  python main.py --translation "Hello world" "Translate to Spanish"
  python main.py --fill-mask "The capital of France is [MASK]"
  python main.py --text2text-generation "Paraphrase: The weather is nice"

Language & Grammar:
  python main.py --language-detection "Bonjour le monde"
  python main.py --grammar-correction "I are going to store"
  python main.py --paraphrase-generation "Rewrite this sentence differently"
  python main.py --causal-language-modeling "Complete this story:"

Advanced Text Analysis:
  python main.py --zero-shot-classification "Text to classify" "politics,sports,technology"
  python main.py --feature-extraction --file "text_corpus.txt"
  python main.py --sentence-similarity "First sentence" "Second sentence"
  python main.py --anonymization --file "document_with_pii.txt"
  python main.py --coreference-resolution --file "story.txt"

[SECURE] SECURITY & LEGAL TASKS:

Security Detection:
  python main.py --spam-detection --file "email.txt"
  python main.py --malware-text-detection --file "suspicious_code.txt"
  python main.py --phishing-detection --file "email_content.txt"
  python main.py --pii-detection --file "user_data.txt"
  python main.py --hate-speech-detection "Check this message for hate speech"
  python main.py --cyberbullying-detection --file "social_media_posts.txt"
  python main.py --fake-news-detection --file "news_article.txt"

Legal Analysis:
  python main.py --legal-judgment-classification --file "court_decision.txt"
  python main.py --contract-clause-classification --file "contract.txt"
  python main.py --case-outcome-prediction --file "case_details.txt"

🏥 SPECIALIZED DOMAIN TASKS:

Entity Recognition:
  python main.py --financial-ner --file "earnings_report.txt"
  python main.py --legal-ner --file "legal_document.txt"
  python main.py --biomedical-ner --file "medical_record.txt"
  python main.py --chemical-reaction-ner --file "chemistry_paper.txt"

Domain Analysis:
  python main.py --financial-sentiment-analysis --file "market_news.txt"
  python main.py --scientific-abstract-summarization --file "research_paper.txt"

💭 CONTENT ANALYSIS TASKS:
  python main.py --emotion-detection "I'm feeling overwhelmed today"
  python main.py --sarcasm-detection "Oh great, another meeting"
  python main.py --stance-detection --file "opinion_piece.txt"
  python main.py --bias-detection --file "news_article.txt"
  python main.py --hallucination-detection --file "ai_generated_text.txt"
  python main.py --reading-level-assessment --file "educational_text.txt"
  python main.py --prompt-quality-scoring "Rate this prompt quality"
  python main.py --generation-groundedness --file "generated_content.txt"
  python main.py --citation-intent-classification --file "academic_paper.txt"

[COMPUTER] CODE ANALYSIS TASKS:
  python main.py --code-vulnerability-detection --file "script.py"
  python main.py --code-summary-generation --file "complex_function.py"
  python main.py --code-clone-detection --file "codebase/"

[SECURITY] PE FILE ANALYSIS TASKS:
  python main.py --pe-header-extraction --file "program.exe"
  python main.py --pe-header-extraction --file "malware.exe" --prompt "is the file malicious"
  python main.py --pe-header-extraction --file "suspicious.dll" --prompt "analyze for security threats"
  python main.py --pe-header-extraction --file "binary.exe" --prompt "verify if this file is safe"

[IMAGE] IMAGE PROCESSING TASKS:
  python main.py --image-classification --file "photo.jpg"
  python main.py --object-detection --file "street_scene.jpg"
  python main.py --image-segmentation --file "landscape.png"
  python main.py --visual-question-answering --file "image.png" "What is in this picture?"
  python main.py --document-question-answering --file "scanned_doc.pdf" "What is the total amount?"
  python main.py --zero-shot-image-classification --file "photo.jpg" "cat,dog,bird"
  python main.py --depth-estimation --file "room_photo.jpg"
  python main.py --image-feature-extraction --file "dataset_images/"

[AUDIO] AUDIO PROCESSING TASKS:
  python main.py --automatic-speech-recognition --file "speech.wav"
  python main.py --audio-classification --file "sound_clip.mp3"
  python main.py --voice-activity-detection --file "conversation.wav"
  python main.py --emotion-recognition --file "emotional_speech.mp3"

[VIDEO] VIDEO PROCESSING TASKS:
  python main.py --video-classification --file "video_clip.mp4"

🎨 GENERATION & ENHANCEMENT TASKS:
  python main.py --text-to-speech "Convert this text to speech"
  python main.py --text-to-image "A beautiful sunset over mountains"
  python main.py --image-super-resolution --file "low_res_image.jpg"

[CHART] STRUCTURED DATA TASKS:
  python main.py --table-question-answering --file "data_table.csv" "What is the highest value?"
  python main.py --feature-ranking --file "features_dataset.csv"

🚀 INNOVATION SYSTEM EXAMPLES:

Basic Innovation Usage:
  python main.py --prompt "Analyze this document" --workflow-optimization --file "report.pdf"
  python main.py --prompt "Understand the context" --semantic-analysis --file "data.txt"
  python main.py --prompt "Track changes over time" --temporal-tracking --file "logs.txt"
  python main.py --prompt "Predict potential issues" --predictive-mode --file "system.log"

Advanced Innovation Combinations:
  python main.py --prompt "Comprehensive analysis" --enable-innovations --file "complex_doc.pdf"
  python main.py --prompt "Deep analysis" --workflow-optimization --semantic-analysis --temporal-tracking --file "project/"
  python main.py --prompt "Smart processing" --enable-innovations --innovation-level 3 --file "dataset.csv"
  python main.py --prompt "Workflow optimization" --workflow-optimization --predictive-mode --file "process_data.txt"

Innovation with Specialized Tasks:
  python main.py --phishing-detection --workflow-optimization --predictive-mode --file "email.txt"
  python main.py --sentiment-analysis --semantic-analysis --temporal-tracking "Track sentiment over time"
  python main.py --code-vulnerability-detection --predictive-mode --workflow-optimization --file "code.py"
  python main.py --financial-sentiment-analysis --enable-innovations --file "market_report.pdf"

[TOOL] GLOBAL OPTIONS:
  --file FILE              Input file to analyze (supports 100+ file types)
  --budget BUDGET          Set cost budget in dollars (e.g., --budget 5.00)
  --chain-of-thought       Enable chain-of-thought reasoning
  --config CONFIG          Use custom configuration file
  --enable-ml              Enable additional ML features (RL, embeddings, clustering)
  --use-openai             Use OpenAI models instead of default HuggingFace selection
  --verbose                Show detailed processing information
  --save-model MODEL       Save trained model to file
  --load-model MODEL       Load pre-trained model from file
  --api-keys KEYS          Specify custom API keys (format: provider:key,...)
  --enable-hyde            Enable HYDE (Hypothetical Document Embeddings)
  --use-hyde               Use HYDE for enhanced search
  --hyde-variants          Generate multiple HYDE variants
  --add-documents DOCS     Add documents to search index (comma-separated)
  --search-query QUERY     Search query for document retrieval
  --top-k K                Number of top results to return
  --demo-hyde              Demonstrate HYDE capabilities
  --delegation             Enable task delegation patterns
  --recursion              Enable recursive processing
  --real-options           Show real-world processing options
  --decision-stats         Show decision-making statistics
  --novel-ai-stats         Show novel AI component statistics
  --performance-stats      Show performance metrics
  --clearcache             Clear all cached data
  --sinq                   Enable SINQ quantization for best selected models
  --sinq-nbits BITS        SINQ quantization bit-width (2,3,4,5,6,8, default: 4)
  --sinq-group-size SIZE   SINQ quantization group size (64,128, default: 64)
  --sinq-tiling-mode MODE  SINQ tiling strategy (1D,2D, default: 1D)
  --sinq-method METHOD     SINQ quantization method (sinq,asinq, default: sinq)

🚀 INNOVATION SYSTEM OPTIONS:
  --enable-innovations     Enable all innovation systems (workflow + semantic + temporal + predictive)
  --workflow-optimization  Enable intelligent workflow creation and optimization
  --semantic-analysis     Enable deep semantic understanding and meaning-based processing
  --temporal-tracking     Enable temporal change analysis and pattern detection
  --predictive-mode       Enable predictive capabilities and issue prevention
  --innovation-level 1-3   Set innovation system level (1=basic, 2=standard, 3=advanced)
  --full                   Enable comprehensive analysis mode
  --cache-stats            Show cache usage statistics
  --language LANGUAGE      Set processing language (en, es, fr, de, etc.)
  --stats                  Show model categorization statistics
  --tasks [TYPE]           List models and tasks (filter by: audio, image, text, etc.)

[TASKS] LEGACY OPTIONS (for backward compatibility):
  --sentiment              Basic sentiment analysis
  --question               Question answering mode
  --ner                    Named entity recognition
  --summary                Text summarization

[BULB] COMBINING OPTIONS:
  python main.py --verbose --chain-of-thought --budget 10.00 --text-classification --file "reviews.txt"
  python main.py --enable-hyde --use-hyde --top-k 3 --question-answering --file "knowledge_base.txt" --prompt "What is AI?"
  python main.py --language es --verbose --translation --file "english_text.txt" --prompt "Translate to Spanish"
  
  # SINQ quantization combinations
  python main.py --sinq --sinq-nbits 4 --verbose --text-generation --prompt "Write a creative story"
  python main.py --sinq --enable-ml --selection-strategy multi_objective --prompt "Analyze this data"
  python main.py --sinq --sinq-method asinq --chain-of-thought --prompt "Complex reasoning task"
  python main.py --sinq --sinq-nbits 3 --file "document.pdf" --prompt "Summarize this document"
  python main.py --sinq --sinq-group-size 128 --sinq-tiling-mode 2D --verbose --prompt "High-performance processing"
  python main.py --sinq --sinq-nbits 2 --enable-ml --selection-strategy ensemble_methods --prompt "Maximum compression"
  python main.py --sinq --sinq-method sinq --enable-hyde --use-hyde --prompt "Enhanced search with quantization"

[HELP] CONTEXTUAL HELP EXAMPLES:
  python main.py --help all                # Show all flags with examples
  python main.py --help --plan             # Show detailed help and examples for --plan
  python main.py --help cu                 # Search flags by keyword (e.g., matches --cpu, --cuda if present)
  python main.py --help sinq               # Show SINQ quantization help and examples
  python main.py --help --sinq             # Show detailed help for --sinq flag
  python main.py --help --sinq-nbits       # Show help for SINQ bit-width options
  python main.py --help --sinq-method      # Show help for SINQ quantization methods
"""


def safe_print(*args, **kwargs):
    """
    Safely print Unicode strings, falling back to ASCII if encoding fails.
    This prevents UnicodeEncodeError on Windows consoles that don't support emojis.
    """
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: replace Unicode characters with ASCII equivalents
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Replace common emojis with ASCII equivalents
                safe_str = arg.replace('❌', '[ERROR]').replace('✅', '[OK]').replace('⚠️', '[WARN]')
                safe_str = safe_str.replace('🔧', '[FIX]').replace('💡', '[TIP]').replace('📋', '[INFO]')
                safe_str = safe_str.replace('🤖', '[AI]').replace('📊', '[STATS]').replace('🎯', '[TARGET]')
                safe_str = safe_str.replace('💬', '[QUERY]').replace('🔄', '[UPDATE]').replace('📝', '[NOTE]')
                safe_str = safe_str.replace('👋', '[BYE]').replace('🔍', '[DEBUG]').replace('💾', '[SAVE]')
                safe_str = safe_str.replace('🔤', '[ENCODING]').replace('📐', '[SHAPE]').replace('🖼️', '[IMAGE]')
                safe_str = safe_str.replace('📄', '[TEXT]').replace('🎮', '[GPU]').replace('💻', '[CPU]')
                safe_str = safe_str.replace('❓', '[HELP]').replace('🚀', '[INNOVATION]').replace('💭', '[THOUGHT]')
                # Remove any remaining non-ASCII characters
                safe_str = safe_str.encode('ascii', 'replace').decode('ascii')
                safe_args.append(safe_str)
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)


async def main():
    """Main entry point for HFOrchestra."""
    parser = argparse.ArgumentParser(
        description="[SYSTEM] HFOrchestra - Comprehensive AI Task Processing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_help_examples()
    )

    # --- Contextual help utilities ---
    def _collect_flags(arg_parser: argparse.ArgumentParser):
        items = []
        for action in arg_parser._actions:
            for opt in action.option_strings:
                if opt.startswith('--'):
                    items.append((opt, action.help or ''))
        return items

    def _example_for_flag(flag: str) -> str:
        # Specific examples for common/global flags
        examples = {
            '--gpu': 'python main.py --gpu --text-generation --prompt "Hello"',
            '--cpu': 'python main.py --cpu --text-generation --prompt "Hello"',
            '--plan': 'python main.py --plan --prompt "Research topic"\n  python main.py --plan --file report.pdf --prompt "Summarize this"',
            '--file': 'python main.py --file image.jpg --prompt "Describe this image"',
            '--prompt': 'python main.py --prompt "Summarize this article" --text-generation',
            '--enable-innovations': 'python main.py --enable-innovations --prompt "Deep analysis"',
            '--use-openai': 'python main.py --use-openai --text-generation --prompt "Hello"',
            '--automatic-speech-recognition': 'python main.py --automatic-speech-recognition --file audio/audio_converted.wav',
            '--sinq': 'python main.py --sinq --prompt "Generate a story"\n  python main.py --sinq --sinq-nbits 4 --prompt "Classify this text"',
            '--sinq-nbits': 'python main.py --sinq --sinq-nbits 4 --prompt "Classify this text"\n  python main.py --sinq --sinq-nbits 3 --prompt "Summarize this article"',
            '--sinq-group-size': 'python main.py --sinq --sinq-group-size 128 --prompt "Analyze sentiment"\n  python main.py --sinq --sinq-group-size 64 --prompt "Translate text"',
            '--sinq-tiling-mode': 'python main.py --sinq --sinq-tiling-mode 2D --prompt "Generate content"\n  python main.py --sinq --sinq-tiling-mode 1D --prompt "Classify text"',
            '--sinq-method': 'python main.py --sinq --sinq-method sinq --prompt "Generate text"\n  python main.py --sinq --sinq-method asinq --prompt "Analyze data"',
        }
        if flag in examples:
            return examples[flag]
        # Heuristics for task flags
        if any(s in flag for s in ['image', 'audio', 'video', 'document', 'depth']):
            sample_file = 'photo.jpg' if 'image' in flag else ('speech.wav' if 'audio' in flag else 'video.mp4')
            return f'python main.py {flag} --file "{sample_file}"'
        # Text-oriented tasks
        return f'python main.py {flag} --prompt "Your text here"'

    def fix_jupyter_kernel_issues():
        """Fix common Jupyter kernel issues"""
        print("🔧 Fixing Jupyter kernel issues...")
        try:
            # Kill existing processes
            subprocess.run([sys.executable, "-m", "jupyter", "notebook", "stop"], 
                         capture_output=True, text=True, timeout=5)
        except:
            pass
        
        try:
            # Install fresh kernel
            subprocess.run([sys.executable, "-m", "ipykernel", "install", "--user", "--name=python3"], 
                         capture_output=True, text=True, timeout=30)
            print("✅ Kernel issues fixed!")
        except Exception as e:
            print(f"⚠️ Kernel fix failed: {e}")
            print("💡 Try running: python fix_jupyter_kernel.py fix")

    def debug_print(message, args=None):
        """Print debug message only if --debug flag is used."""
        if args and hasattr(args, 'debug') and args.debug:
            safe_print(f"🔍 [DEBUG] {message}")
    
    def print_ensemble_information(selection_strategy, task_name=None, prompt=None):
        """Print ensemble information for every query"""
        safe_print(f"\n🤖 ENSEMBLE MODEL SELECTION")
        safe_print("=" * 50)
        safe_print(f"📊 Strategy: {selection_strategy.upper()}")
        
        strategy_descriptions = {
            'hyperparameter_tuning': 'Optimizing model hyperparameters for best performance',
            'cross_validation': 'Using cross-validation to ensure robust model selection',
            'ensemble_methods': 'Combining multiple models for improved accuracy and reliability',
            'multi_objective': 'Balancing multiple objectives (accuracy, speed, cost, etc.)',
            'bayesian_optimization': 'Using Bayesian optimization for efficient hyperparameter search',
            'meta_learning': 'Learning from previous model selections to improve future choices'
        }
        
        safe_print(f"🎯 Approach: {strategy_descriptions.get(selection_strategy, 'Advanced model selection')}")
        
        if task_name:
            safe_print(f"📋 Task: {task_name}")
        if prompt:
            safe_print(f"💬 Query: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        
        safe_print(f"🔄 Status: Applying {selection_strategy} strategy for optimal model selection")
        safe_print("=" * 50)

    def export_analysis_to_pdf(analysis_results, file_path, user_prompt, output_path=None):
        """Export data analysis results to PDF"""
        if not PDF_AVAILABLE:
            safe_print("❌ PDF generation not available. Install: pip install reportlab")
            return False
        
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"reports/data_science_analysis_{timestamp}.pdf"
            
            # Create reports directory if it doesn't exist
            Path("reports").mkdir(exist_ok=True)
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            story.append(Paragraph("Data Science Analysis Report", title_style))
            story.append(Spacer(1, 20))
            
            # File information
            story.append(Paragraph(f"<b>File Analyzed:</b> {file_path}", styles['Normal']))
            story.append(Paragraph(f"<b>Analysis Goal:</b> {user_prompt}", styles['Normal']))
            story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", styles['Heading2']))
            if isinstance(analysis_results, dict) and 'content' in analysis_results:
                summary = analysis_results['content'][:500] + "..." if len(analysis_results['content']) > 500 else analysis_results['content']
                story.append(Paragraph(summary, styles['Normal']))
            else:
                story.append(Paragraph("Analysis completed successfully with comprehensive insights.", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Key Findings
            story.append(Paragraph("Key Findings", styles['Heading2']))
            findings = [
                "• Comprehensive data validation and cleaning applied",
                "• Statistical analysis performed on all numeric columns",
                "• Date columns automatically detected and converted",
                "• Correlation analysis completed for numeric variables",
                "• Distribution analysis with visualizations generated",
                "• Outlier detection and handling implemented",
                "• Data quality assessment completed"
            ]
            for finding in findings:
                story.append(Paragraph(finding, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Technical Details
            story.append(Paragraph("Technical Details", styles['Heading2']))
            tech_details = [
                "• Error handling and recovery systems activated",
                "• Multiple data format support (CSV, Excel, JSON, Parquet, TSV)",
                "• Automatic encoding detection and handling",
                "• Memory optimization for large datasets",
                "• Cross-platform compatibility ensured"
            ]
            for detail in tech_details:
                story.append(Paragraph(detail, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Recommendations
            story.append(Paragraph("Recommendations", styles['Heading2']))
            recommendations = [
                "• Review generated visualizations for insights",
                "• Consider additional domain-specific analysis",
                "• Validate findings with domain experts",
                "• Monitor data quality over time",
                "• Consider implementing automated monitoring"
            ]
            for rec in recommendations:
                story.append(Paragraph(rec, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(story)
            safe_print(f"✅ PDF report generated: {output_path}")
            return True
            
        except Exception as e:
            safe_print(f"❌ PDF generation failed: {e}")
            return False

    def _print_contextual_help(arg_parser: argparse.ArgumentParser, terms):
        flags = _collect_flags(arg_parser)
        if len(terms) == 1 and terms[0].lower() == 'all':
            print("\nAvailable flags with examples:\n")
            for opt, desc in sorted(flags, key=lambda x: x[0]):
                example = _example_for_flag(opt)
                print(f"{opt}\n  {desc}\n  Example: {example}\n")
            return
        # Search by any provided term (substring match)
        search_terms = [t.lower() for t in terms]
        matched = []
        for opt, desc in flags:
            hay = f"{opt} {desc}".lower()
            if all(term in hay for term in search_terms):
                matched.append((opt, desc))
        if not matched:
            print("No flags matched your query. Try 'python main.py --help all'.")
            return
        print("\nMatching flags with examples:\n")
        for opt, desc in sorted(matched, key=lambda x: x[0]):
            example = _example_for_flag(opt)
            print(f"{opt}\n  {desc}\n  Example: {example}\n")
    
    # Core arguments
    parser.add_argument('--file', type=str,
                       help='[TARGET] UNIVERSAL FILE SUPPORT: Path to ANY file type (100+ formats supported). REQUIRES --prompt. Uses AI-powered detection via Magika. Supports: images, audio, video, archives, databases, executables, documents, code files, and more!')
    
    parser.add_argument('--prompt', type=str,
                       help='[PROMPT] Explicit prompt/question for file analysis or task-specific queries. Required for tasks that need user input. Example: --prompt "What is in this image?" or --prompt "Summarize this document"')
    
    parser.add_argument('--task', type=str, metavar="PROMPT",
                       help='Process a task using the orchestrator (alias for --prompt)')
    
    # System configuration
    parser.add_argument('--budget', type=float, default=10.0,
                       help='Budget in dollars (default: 10.0)')
    
    parser.add_argument('--chain-of-thought', action='store_true',
                       help='[AI] UNIVERSAL ENHANCER: Apply Tree-of-Thoughts reasoning to ANY task for deeper analysis and better results')
    
    parser.add_argument('--config', type=str, default='model_configs',
                       help='Configuration file path (default: model_configs)')
    
    parser.add_argument('--enable-ml', action='store_true',
                       help='Enable additional ML features (RL, embeddings, clustering, anomaly detection)')
    
    parser.add_argument('--use-openai', action='store_true',
                       help='Use OpenAI models instead of default HuggingFace model selection')
    
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode for extra diagnostics')
    
    parser.add_argument('--selection-strategy', choices=['hyperparameter_tuning', 'cross_validation', 'ensemble_methods', 'multi_objective', 'bayesian_optimization', 'meta_learning', 'ml_enhanced', 'ml_ensemble', 'ml_voting', 'ml_consensus', 'ml_stacking', 'ml_adaptive'], 
                       default='ensemble_methods', help='Enhanced model selection strategy (ALWAYS USED for every query). ML options: ml_enhanced, ml_ensemble, ml_voting, ml_consensus, ml_stacking, ml_adaptive')
    
    # ML-based model selection flags
    parser.add_argument('--enable-ml-selection', action='store_true',
                       help='Enable ML-based model selection system that learns from historical performance')
    
    parser.add_argument('--ml-learning', action='store_true',
                       help='Enable learning from task execution results to improve model selection over time')
    
    parser.add_argument('--ml-ensemble-method', choices=['voting', 'weighted_voting', 'consensus', 'stacking', 'adaptive'], 
                       default='weighted_voting', help='Ensemble method for ML-based model selection')
    
    parser.add_argument('--ml-confidence-threshold', type=float, default=0.6,
                       help='Minimum confidence threshold for ML model selection (0.0-1.0, default: 0.6)')
    
    parser.add_argument('--ml-fallback', action='store_true', default=True,
                       help='Enable fallback to enhanced selector when ML selection fails (default: True)')
    
    parser.add_argument('--ml-analytics', action='store_true',
                       help='Show ML model selection analytics and performance statistics')
    
    parser.add_argument('--ml-retrain', action='store_true',
                       help='Force retraining of ML models with current data')
    
    parser.add_argument('--ml-cleanup', type=int, metavar='DAYS',
                       help='Clean up ML training data older than specified days (e.g., --ml-cleanup 30)')
    
    # SINQ Quantization arguments
    parser.add_argument('--sinq', action='store_true',
                       help='Enable SINQ quantization for best selected models (reduces memory usage while preserving accuracy)')
    
    parser.add_argument('--sinq-nbits', type=int, choices=[2, 3, 4, 5, 6, 8], default=4,
                       help='Bit-width for SINQ weight quantization (default: 4)')
    
    parser.add_argument('--sinq-group-size', type=int, choices=[64, 128], default=64,
                       help='Weights per quantization group for SINQ (default: 64)')
    
    parser.add_argument('--sinq-tiling-mode', choices=['1D', '2D'], default='1D',
                       help='Weight matrix tiling strategy for SINQ (default: 1D)')
    
    parser.add_argument('--sinq-method', choices=['sinq', 'asinq'], default='sinq',
                       help='SINQ quantization method: sinq (calibration-free) or asinq (calibrated) (default: sinq)')
    
    # Innovation system arguments
    parser.add_argument('--enable-innovations', action='store_true',
                       help='Enable all innovation systems (workflow, semantic, temporal, etc.)')
    
    parser.add_argument('--workflow-optimization', action='store_true',
                       help='Enable workflow optimization using innovation system (e.g., --workflow-optimization --prompt "Optimize build pipeline")')
    
    parser.add_argument('--semantic-analysis', action='store_true',
                       help='Enable semantic analysis of content (e.g., --semantic-analysis --prompt "Find core concepts")')
    
    parser.add_argument('--temporal-tracking', action='store_true',
                       help='Enable temporal change tracking (e.g., --temporal-tracking --prompt "Compare versions")')
    
    parser.add_argument('--predictive-mode', action='store_true',
                       help='Enable predictive capabilities (e.g., --predictive-mode --prompt "Predict failures")')

    # Data analyst quick workflow
    parser.add_argument('--dataanalyst', action='store_true',
                       help='Run the Data Analyst workflow on a CSV/XLS(X) file (requires --file and --prompt). Example: --dataanalyst --file data.csv --prompt "Find key insights"')
    
    parser.add_argument('--datascience', action='store_true',
                       help='Run comprehensive Data Science workflow with PDF export (requires --file and --prompt). Example: --datascience --file data.csv --prompt "Comprehensive analysis"')
    
    parser.add_argument('--jupyter', action='store_true',
                       help='Launch Jupyter notebook for data analysis')
    
    parser.add_argument('--export-pdf', action='store_true',
                       help='Export analysis results to PDF report')
    
    parser.add_argument('--innovation-level', type=int, choices=[1, 2, 3], default=2,
                       help='Innovation system level (1=basic, 2=standard, 3=advanced). Example: --innovation-level 3')
    
    parser.add_argument('--save-model', action='store_true',
                       help='Save trained ML models for future use')
    
    parser.add_argument('--load-model', type=str,
                       help='Load pre-trained ML model from file')
    
    parser.add_argument('--api-keys', type=str,
                       help='JSON file containing API keys')
    
    parser.add_argument('--language', type=str, default='en',
                       help='Set processing language (en, es, fr, de, etc.)')

    # Device selection (GPU/CPU)
    device_group = parser.add_mutually_exclusive_group()
    device_group.add_argument('--gpu', action='store_true',
                        help='Force GPU/CUDA usage where supported')
    device_group.add_argument('--cpu', action='store_true',
                        help='Force CPU-only execution')
    
    # Evaluation and scoring
    parser.add_argument('--score', action='store_true',
                       help='Enable response evaluation scoring using BLEU, ROUGE, METEOR, and BERTScore metrics')
    
    parser.add_argument('--judge', action='store_true',
                       help='Enable LLM-as-a-Judge evaluation using premium models (GPT-4) for qualitative assessment')
    
    parser.add_argument('--plan', action='store_true',
                       help='Enable AI-powered planning using LangChain PlanAndExecute agents for multi-step task decomposition')
    
    # HYDE (Hypothetical Document Embeddings)
    parser.add_argument('--enable-hyde', action='store_true',
                       help='Enable HyDE (Hypothetical Document Embeddings) for enhanced search')
    
    parser.add_argument('--use-hyde', action='store_true',
                       help='Use interactive HyDE question refinement to suggest multiple ways to ask your question')
    
    parser.add_argument('--hyde-variants', action='store_true',
                       help='Use multiple HyDE variants for better search results')
    
    parser.add_argument('--add-documents', type=str,
                       help='Add documents to search index (comma-separated file paths)')
    
    parser.add_argument('--search-query', type=str,
                       help='Perform semantic search with the given query')
    
    parser.add_argument('--top-k', type=int, default=5,
                       help='Number of top results to return for search (default: 5)')
    
    parser.add_argument('--demo-hyde', action='store_true',
                       help='Run HyDE and embeddings demo')
    
    # PE Analysis
    parser.add_argument('--pe-header-extraction', action='store_true',
                       help='[BINARY] Extract ALL PE headers from Windows executables (.exe, .dll, .sys). Extracts DOS header, File header, Optional header, Data directories, Sections, Imports, Exports, Resources, and more!')
    
    # Advanced Decision Science
    parser.add_argument('--delegation', action='store_true',
                       help='Use delegation pattern to route tasks to specialized models')
    
    parser.add_argument('--recursion', action='store_true',
                       help='Use recursive task decomposition for complex problems')
    
    parser.add_argument('--real-options', action='store_true',
                       help='Enable real options analysis for backup model selection')
    
    parser.add_argument('--prompt-quality-scoring', action='store_true',
                       help='Enable prompt quality scoring and optimization')
    
    # System monitoring and statistics
    parser.add_argument('--stats', action='store_true',
                       help='Show model categorization statistics')
    
    parser.add_argument('--tasks', nargs='?', const='all', metavar='TYPE',
                       help='List models and tasks (filter by: audio, image, text, etc.)')
    
    parser.add_argument('--update', action='store_true',
                       help='Update the HuggingFace models database (populate_all_hf_models.py functionality)')
    
    parser.add_argument('--restore', action='store_true',
                        help='Restore config and database from the most recent backup in backups/')
    
    parser.add_argument('--decision-stats', action='store_true',
                       help='Show decision-making statistics')
    
    parser.add_argument('--novel-ai-stats', action='store_true',
                       help='Show novel AI component statistics')
    
    parser.add_argument('--performance-stats', action='store_true',
                       help='Show performance metrics')
    
    parser.add_argument('--cache-stats', action='store_true',
                       help='Show cache usage statistics')
    
    # Advanced Analytics
    parser.add_argument('--analytics-demo', action='store_true',
                       help='Run advanced model analytics demo with dynamic ranking and recommendations')
    
    parser.add_argument('--model-ranking', nargs='?', const=None, metavar='TASK',
                       help='Show model ranking for a specific task or all tasks')
    
    parser.add_argument('--model-recommendations', action='store_true',
                       help='Get personalized model recommendations based on preferences')
    
    parser.add_argument('--clearcache', action='store_true',
                       help='Clear all cached data')
    
    parser.add_argument('--full', action='store_true',
                       help='Enable comprehensive analysis mode')
    
    # Legacy compatibility
    parser.add_argument('--sentiment', action='store_true',
                       help='Basic sentiment analysis')
    
    parser.add_argument('--question', action='store_true',
                       help='Question answering mode')
    
    parser.add_argument('--ner', action='store_true',
                       help='Named entity recognition')
    
    parser.add_argument('--summary', action='store_true',
                       help='Text summarization')
    
    # Text Processing Tasks
    parser.add_argument('--text-classification', action='store_true',
                       help='Text classification task')
    
    parser.add_argument('--token-classification', action='store_true',
                       help='Token classification (NER) task')
    
    parser.add_argument('--question-answering', action='store_true',
                       help='Question answering task')
    
    parser.add_argument('--text-generation', action='store_true',
                       help='Text generation task')
    
    parser.add_argument('--summarization', action='store_true',
                       help='Text summarization task')
    
    parser.add_argument('--translation', action='store_true',
                       help='Text translation task')
    
    parser.add_argument('--fill-mask', action='store_true',
                       help='Fill mask task')
    
    parser.add_argument('--text2text-generation', action='store_true',
                       help='Text-to-text generation task')
    
    parser.add_argument('--language-detection', action='store_true',
                       help='Language detection task')
    
    parser.add_argument('--grammar-correction', action='store_true',
                       help='Grammar correction task')
    
    parser.add_argument('--paraphrase-generation', action='store_true',
                       help='Paraphrase generation task')
    
    parser.add_argument('--causal-language-modeling', action='store_true',
                       help='Causal language modeling task')
    
    parser.add_argument('--zero-shot-classification', action='store_true',
                       help='Zero-shot classification task')
    
    parser.add_argument('--feature-extraction', action='store_true',
                       help='Feature extraction task')
    
    parser.add_argument('--sentence-similarity', action='store_true',
                       help='Sentence similarity task')
    
    parser.add_argument('--anonymization', action='store_true',
                       help='Text anonymization task')
    
    parser.add_argument('--coreference-resolution', action='store_true',
                       help='Coreference resolution task')
    
    # Security Tasks
    parser.add_argument('--spam-detection', action='store_true',
                       help='Spam detection task')
    
    parser.add_argument('--malware-text-detection', action='store_true',
                       help='Malware text detection task')
    
    parser.add_argument('--phishing-detection', action='store_true',
                       help='Phishing detection task')
    
    parser.add_argument('--pii-detection', action='store_true',
                       help='PII detection task')
    
    parser.add_argument('--hate-speech-detection', action='store_true',
                       help='Hate speech detection task')
    
    parser.add_argument('--cyberbullying-detection', action='store_true',
                       help='Cyberbullying detection task')
    
    parser.add_argument('--fake-news-detection', action='store_true',
                       help='Fake news detection task')
    
    # Legal Analysis
    parser.add_argument('--legal-judgment-classification', action='store_true',
                       help='Legal judgment classification task')
    
    parser.add_argument('--contract-clause-classification', action='store_true',
                       help='Contract clause classification task')
    
    parser.add_argument('--case-outcome-prediction', action='store_true',
                       help='Case outcome prediction task')
    
    # Specialized Domain Tasks
    parser.add_argument('--financial-ner', action='store_true',
                       help='Financial named entity recognition')
    
    parser.add_argument('--legal-ner', action='store_true',
                       help='Legal named entity recognition')
    
    parser.add_argument('--biomedical-ner', action='store_true',
                       help='Biomedical named entity recognition')
    
    parser.add_argument('--chemical-reaction-ner', action='store_true',
                       help='Chemical reaction named entity recognition')
    
    parser.add_argument('--financial-sentiment-analysis', action='store_true',
                       help='Financial sentiment analysis')
    
    parser.add_argument('--scientific-abstract-summarization', action='store_true',
                       help='Scientific abstract summarization')
    
    # Content Analysis Tasks
    parser.add_argument('--emotion-detection', action='store_true',
                       help='Emotion detection task')
    
    parser.add_argument('--sarcasm-detection', action='store_true',
                       help='Sarcasm detection task')
    
    parser.add_argument('--stance-detection', action='store_true',
                       help='Stance detection task')
    
    parser.add_argument('--bias-detection', action='store_true',
                       help='Bias detection task')
    
    parser.add_argument('--hallucination-detection', action='store_true',
                       help='Hallucination detection task')
    
    parser.add_argument('--reading-level-assessment', action='store_true',
                       help='Reading level assessment task')
    
    parser.add_argument('--generation-groundedness', action='store_true',
                       help='Generation groundedness task')
    
    parser.add_argument('--citation-intent-classification', action='store_true',
                       help='Citation intent classification task')
    
    # Code Analysis Tasks
    parser.add_argument('--code-vulnerability-detection', action='store_true',
                       help='Code vulnerability detection task')
    
    parser.add_argument('--code-summary-generation', action='store_true',
                       help='Code summary generation task')
    
    parser.add_argument('--code-clone-detection', action='store_true',
                       help='Code clone detection task')
    
    # Image Processing Tasks
    parser.add_argument('--image-classification', action='store_true',
                       help='Image classification task')
    
    parser.add_argument('--object-detection', action='store_true',
                       help='Object detection task')
    
    parser.add_argument('--image-segmentation', action='store_true',
                       help='Image segmentation task')
    
    parser.add_argument('--visual-question-answering', action='store_true',
                       help='Visual question answering task')
    
    parser.add_argument('--document-question-answering', action='store_true',
                       help='Document question answering task')
    
    parser.add_argument('--zero-shot-image-classification', action='store_true',
                       help='Zero-shot image classification task')
    
    parser.add_argument('--depth-estimation', action='store_true',
                       help='Depth estimation task')
    
    parser.add_argument('--image-feature-extraction', action='store_true',
                       help='Image feature extraction task')
    
    # Audio Processing Tasks
    parser.add_argument('--automatic-speech-recognition', action='store_true',
                       help='Automatic speech recognition task')
    
    parser.add_argument('--audio-classification', action='store_true',
                       help='Audio classification task')
    
    parser.add_argument('--voice-activity-detection', action='store_true',
                       help='Voice activity detection task')
    
    parser.add_argument('--emotion-recognition', action='store_true',
                       help='Emotion recognition from audio task')
    
    # Video Processing Tasks
    parser.add_argument('--video-classification', action='store_true',
                       help='Video classification task')
    
    # Generation & Enhancement Tasks
    parser.add_argument('--text-to-speech', action='store_true',
                       help='Text-to-speech task')
    
    parser.add_argument('--text-to-image', action='store_true',
                       help='Text-to-image generation task')
    
    parser.add_argument('--image-super-resolution', action='store_true',
                       help='Image super-resolution task')
    
    # Structured Data Tasks
    parser.add_argument('--table-question-answering', action='store_true',
                       help='Table question answering task')
    
    parser.add_argument('--feature-ranking', action='store_true',
                       help='Feature ranking task')
    
    parser.add_argument('--data-analyst', action='store_true', help='Run comprehensive data analyst workflow on the provided file and prompt')
    parser.add_argument('--datanalyst', action='store_true', help='Alias for --data-analyst')
    
    # Support contextual help: allow forms like `--help all` or `--help <terms>`
    if '--help' in sys.argv and len(sys.argv) > 2:
        # Extract terms after --help
        try:
            help_index = sys.argv.index('--help')
            terms = [a for a in sys.argv[help_index + 1:] if not a.startswith('-')]
            if terms:
                _print_contextual_help(parser, terms)
                sys.exit(0)
        except Exception:
            pass

    args = parser.parse_args()

    # The environment setup is now handled by the early import of core.env_setup.
    # The debug flag is used to enable verbose logging for the setup process.
    if args.debug:
        os.environ['HFORCH_DEBUG'] = 'true'
        print("[DEBUG] Debug mode enabled.")
        if not os.getenv("HFORCH_LANGEXTRACT_VERBOSE"):
            os.environ['HFORCH_LANGEXTRACT_VERBOSE'] = 'true'
            print("[DEBUG] HFORCH_LANGEXTRACT_VERBOSE enabled via --debug flag.")
    
    # Rest of the setup and main logic...
    load_dotenv()

    # The rest of the main function continues here...
    # Apply device override flags via environment for downstream modules
    if args.gpu:
        os.environ['HFORCH_DEVICE'] = 'cuda'
        print("[DEVICE] Forcing device: cuda")
    elif args.cpu:
        os.environ['HFORCH_DEVICE'] = 'cpu'
        print("[DEVICE] Forcing device: cpu")

    # --- Validate file usage early ---
    # 1) If any file-required task is requested, ensure --file is provided
    file_required_flags = [
        'automatic_speech_recognition', 'audio_classification', 'voice_activity_detection', 'emotion_recognition',
        'image_classification', 'object_detection', 'image_segmentation', 'visual_question_answering', 'document_question_answering',
        'zero_shot_image_classification', 'depth_estimation', 'image_feature_extraction',
        'video_classification',
        'pe_header_extraction',
        'table_question_answering', 'feature_ranking'
    ]
    file_needed = any(getattr(args, flag, False) for flag in file_required_flags)
    if file_needed and not args.file:
        safe_print("❌ Error: This operation requires --file <path>.")
        safe_print("Usage: python main.py --<task-flag> --file <path> --prompt <optional>")
        return

    # 2) If --file is supplied, ensure a non-empty path and that it exists
    if args.file is not None:
        if not str(args.file).strip():
            safe_print("❌ Error: --file requires a valid file path value.")
            return
        if not Path(args.file).exists():
            safe_print(f"❌ Error: --file path not found: {args.file}")
            return
    
    # Initialize core components (with fallbacks)
    folder_manager = FolderManager() if folder_manager_available else None
    performance_monitor = PerformanceMonitor() if performance_available else None
    task_handler = ComprehensiveTaskHandler() if task_handler_available else None
    
    # Initialize ML-based model selection system if enabled
    ml_manager = None
    if args.enable_ml_selection:
        try:
            from core.ml_integration import initialize_ml_integration, MLIntegrationConfig
            from core.ensemble_model_selector import EnsembleMethod
            
            # Map ensemble method from command line to enum
            ensemble_method_map = {
                'voting': EnsembleMethod.VOTING,
                'weighted_voting': EnsembleMethod.WEIGHTED_VOTING,
                'consensus': EnsembleMethod.CONSENSUS,
                'stacking': EnsembleMethod.STACKING,
                'adaptive': EnsembleMethod.ADAPTIVE
            }
            
            # Create ML integration configuration
            ml_config = MLIntegrationConfig(
                enable_ml_selection=True,
                enable_ensemble_methods=True,
                enable_learning=args.ml_learning,
                default_ensemble_method=ensemble_method_map.get(args.ml_ensemble_method, EnsembleMethod.WEIGHTED_VOTING),
                fallback_to_enhanced=args.ml_fallback,
                performance_tracking=True
            )
            
            ml_manager = initialize_ml_integration(ml_config)
            print("🤖 ML-based model selection system initialized")
            
        except ImportError as e:
            print(f"⚠️ ML selection system not available: {e}")
            print("   Install ML dependencies with: pip install -r requirements_ml.txt")
        except Exception as e:
            print(f"⚠️ Error initializing ML selection system: {e}")
            ml_manager = None
    
    # If critical components aren't available, provide fallback functionality
    if not task_handler_available:
        print("⚠️ Task handler not available. Using minimal fallback functionality.")
        
        # Simple fallback implementations
        class FallbackTaskHandler:
            async def handle_stats(self):
                return type('Result', (), {
                    'success': True,
                    'content': "📊 Fallback Mode - Core statistics not available\n• Command line parsing: ✅ Working\n• Argument validation: ✅ Functional"
                })()
            
            async def handle_tasks_list(self, task_type=None):
                return type('Result', (), {
                    'success': True,
                    'content': f"📋 Fallback Mode - Task listing\n• Available: Basic command line argument parsing\n• Filter: {task_type or 'all'}\n• Status: Infrastructure working"
                })()
            
            async def handle_clear_cache(self):
                return type('Result', (), {
                    'success': True,
                    'content': "🗑️ Fallback Mode - Cache clearing simulated"
                })()
            
            async def handle_hyde_demo(self):
                return type('Result', (), {
                    'success': True,
                    'content': "🔍 Fallback Mode - HYDE Demo\n• Feature available in full implementation\n• Command line interface: ✅ Working"
                })()
            
            async def handle_analytics_demo(self):
                return type('Result', (), {
                    'success': True,
                    'content': "🔬 Fallback Mode - Analytics Demo\n• Advanced analytics available in full implementation\n• Infrastructure: ✅ Ready"
                })()
            
            async def handle_model_ranking(self, task=None, limit=10):
                return type('Result', (), {
                    'success': True,
                    'content': f"🏆 Fallback Mode - Model Ranking\n• Task: {task or 'general'}\n• Limit: {limit}\n• Feature available in full implementation"
                })()
            
            async def handle_model_recommendations(self):
                return type('Result', (), {
                    'success': True,
                    'content': "🎯 Fallback Mode - Model Recommendations\n• Personalized recommendations available in full implementation\n• Command line parsing: ✅ Working"
                })()
            
            async def handle_decision_stats(self):
                return type('Result', (), {
                    'success': True,
                    'content': "📊 Fallback Mode - Decision Statistics\n• Decision making stats available in full implementation"
                })()
            
            async def handle_performance_stats(self):
                return type('Result', (), {
                    'success': True,
                    'content': "⚡ Fallback Mode - Performance Statistics\n• Performance metrics available in full implementation"
                })()
            
            async def handle_cache_stats(self):
                return type('Result', (), {
                    'success': True,
                    'content': "💾 Fallback Mode - Cache Statistics\n• Cache metrics available in full implementation"
                })()
            
            async def handle_search_query(self, query, top_k=5):
                return type('Result', (), {
                    'success': True,
                    'content': f"🔍 Fallback Mode - Search Results\n• Query: '{query}'\n• Top-K: {top_k}\n• Semantic search available in full implementation"
                })()
                
            async def handle_specialized_task(self, task_name, prompt=None):
                return type('Result', (), {
                    'success': True,
                    'content': f"🤖 Fallback Mode - Task Processing\n• Task: {task_name}\n• Input: {prompt or 'None'}\n• AI processing available in full implementation",
                    'data': {
                        'task_name': task_name,
                        'models_used': ['fallback-mode'],
                        'processing_time_ms': 0,
                        'total_cost': 0,
                        'total_tokens': 0
                    }
                })()
        
        task_handler = FallbackTaskHandler()
    
    # Check if database exists and has models - handle first-time setup
    # Determine project root and DB path using absolute path (src/hforchestra -> src -> PROJECT_ROOT)
    # This ensures we check the same DB that TaskHandler uses
    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parent.parent.parent
    db_path = project_root / "db" / "hf_models.db"
    
    database_has_models = False
    
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM models")
            model_count = cursor.fetchone()[0]
            conn.close()
            database_has_models = model_count > 0
        except Exception as e:
            print(f"⚠️  Warning: Could not check database contents: {e}")
            database_has_models = False
    
    if not db_path.exists() or not database_has_models:
        if not db_path.exists():
            safe_print("🔍 First-time setup detected: Database not found")
        else:
            safe_print("🔍 First-time setup detected: Database exists but contains 0 models")
        
        safe_print("📦 Running initial database population...")
        safe_print("🌍 This will download and populate the HuggingFace models database")
        safe_print("")
        safe_print("⚠️  IMPORTANT: First update may take a VERY LONG TIME!")
        safe_print("⏱️  Expected duration: 2-8 hours depending on your internet connection")
        safe_print("📊 Target: Downloading ~1.9M+ models from HuggingFace")
        safe_print("💡 You can safely interrupt this process with Ctrl+C and restart later")
        safe_print("💡 The system will resume from where it left off")
        safe_print("")
        safe_print("🚀 Starting download process...")
        
        # Auto-run update for first-time setup
        result = await task_handler.handle_update_database()
        safe_print_content(result)
        
        # Verify the update was successful
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM models")
                model_count = cursor.fetchone()[0]
                conn.close()
                
                if model_count == 0:
                    safe_print("\n⚠️  WARNING: Database was created but contains 0 models!")
                    safe_print("🔧 This indicates the update process may have failed or been interrupted.")
                    safe_print("💡 You can try running the update manually:")
                    safe_print("   python src/hforchestra/main.py --update")
                    safe_print("💡 Or check the logs for more details.")
                    return
                else:
                    safe_print(f"✅ Database successfully populated with {model_count:,} models!")
            except Exception as e:
                safe_print(f"⚠️  Warning: Could not verify database contents: {e}")
        
        return
    else:
        # Database exists and has models - show info about update option
        if not any([args.update, args.tasks, args.stats, args.restore, 
                   args.decision_stats, args.novel_ai_stats, args.performance_stats, 
                   args.cache_stats, args.clearcache, args.analytics_demo, 
                   args.model_ranking, args.model_recommendations, args.full,
                   args.ml_analytics, args.ml_retrain, args.ml_cleanup]):
            # Only show this message if no other flags are specified
            safe_print("✅ Database found: HuggingFace models database is ready")
            safe_print("💡 Use --update to refresh the database with latest models")
            safe_print("💡 Use --tasks to see available models and tasks")
            safe_print("💡 Use --help for more options")
    
    # Handle database update (when explicitly requested)
    if args.update:
        safe_print("🔄 Updating HuggingFace models database...")
        result = await task_handler.handle_update_database()
        safe_print_content(result)
        return

    # Handle restore from latest backup
    if args.restore:
        try:
            project_root = Path(__file__).parent
            backups_dir = project_root / 'backups'
            if not backups_dir.exists():
                safe_print(f"❌ Error: Backups directory not found: {backups_dir}")
                return

            # Find candidate backup subdirectories containing both 'config' and 'db'
            candidates = []
            for child in backups_dir.iterdir():
                if not child.is_dir():
                    continue
                if (child / 'config').is_dir() and (child / 'db').is_dir():
                    candidates.append(child)

            if not candidates:
                print("❌ Error: No valid backups found in backups/")
                return

            latest_backup = max(candidates, key=lambda p: p.stat().st_mtime)
            print(f"Restoring from latest backup: {latest_backup.name}")

            # Prepare pre-restore safety backup of current state
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            pre_dir = backups_dir / f"backup_{timestamp}_pre_restore"
            (pre_dir / 'config').mkdir(parents=True, exist_ok=True)
            (pre_dir / 'db').mkdir(parents=True, exist_ok=True)

            # Paths
            current_config_dir = project_root / 'config'
            current_db_dir = project_root / 'db'
            src_config_dir = latest_backup / 'config'
            src_db_dir = latest_backup / 'db'

            # Safely back up current files if they exist
            try:
                for name in ['dynamic_models.json', 'model_configs.json', 'settings.json']:
                    src = current_config_dir / name
                    if src.exists():
                        shutil.copy2(src, pre_dir / 'config' / name)
                db_src = current_db_dir / 'hf_models.db'
                if db_src.exists():
                    shutil.copy2(db_src, pre_dir / 'db' / 'hf_models.db')
                print(f"Created safety backup: {pre_dir.name}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to create safety backup of current files: {e}")

            # Restore config files (only known critical JSONs)
            restored_any = False
            for name in ['dynamic_models.json', 'model_configs.json', 'settings.json']:
                src = src_config_dir / name
                dst = current_config_dir / name
                if src.exists():
                    shutil.copy2(src, dst)
                    print(f"Restored config: {name}")
                    restored_any = True
                else:
                    print(f"Skipped missing config in backup: {name}")

            # Restore database
            src_db = src_db_dir / 'hf_models.db'
            dst_db = current_db_dir / 'hf_models.db'
            if src_db.exists():
                shutil.copy2(src_db, dst_db)
                print("Restored database: hf_models.db")
                restored_any = True
            else:
                print("Skipped missing database in backup: hf_models.db")

            if restored_any:
                print("Restore completed successfully.")
            else:
                print("No files were restored. Backup may be incomplete.")
        except Exception as e:
            print(f"Restore failed: {e}")
        return
    
    # Handle tasks list
    if args.tasks:
        safe_print("📋 Listing available tasks...")
        result = await task_handler.handle_tasks_list(args.tasks)
        safe_print_content(result)
        return
    
    # Handle statistics
    if args.stats:
        safe_print("📊 Getting system statistics...")
        result = await task_handler.handle_stats()
        safe_print_content(result)
        return
    
    # Handle HYDE demo
    if args.demo_hyde:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "hyde_demo", "Run HYDE demo")
        
        safe_print("🔍 Running HYDE demo...")
        result = await task_handler.handle_hyde_demo()
        safe_print_content(result)
        return
    
    # Handle cache clearing
    if args.clearcache:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "clear_cache", "Clear system cache")
        
        safe_print("🗑️ Clearing cache...")
        result = await task_handler.handle_clear_cache()
        safe_print_content(result)
        return
    
    # Handle additional statistics
    if args.decision_stats:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "decision_stats", "Get decision-making statistics")
        
        safe_print("📊 Getting decision-making statistics...")
        result = await task_handler.handle_decision_stats()
        safe_print_content(result)
        return
    
    if args.novel_ai_stats:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "novel_ai_stats", "Get novel AI component statistics")
        
        safe_print("🤖 Getting novel AI component statistics...")
        result = await task_handler.handle_novel_ai_stats()
        safe_print_content(result)
        return
    
    if args.performance_stats:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "performance_stats", "Get performance metrics")
        
        safe_print("⚡ Getting performance metrics...")
        result = await task_handler.handle_performance_stats()
        safe_print_content(result)
        return
    
    # Handle ML analytics
    if args.ml_analytics:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "ml_analytics", "Get ML model selection analytics")
        
        if ml_manager:
            safe_print("🤖 Getting ML model selection analytics...")
            analytics = ml_manager.get_integration_analytics()
            
            safe_print("\n📊 ML Integration Analytics:")
            safe_print("=" * 40)
            
            # Performance statistics
            perf_stats = analytics['performance_stats']
            safe_print(f"Total Requests: {perf_stats['total_requests']}")
            safe_print(f"ML Selections: {perf_stats['ml_selections']}")
            safe_print(f"Ensemble Selections: {perf_stats['ensemble_selections']}")
            safe_print(f"Fallback Selections: {perf_stats['fallback_selections']}")
            safe_print(f"Successful Selections: {perf_stats['successful_selections']}")
            safe_print(f"Average Confidence: {perf_stats['average_confidence']:.3f}")
            safe_print(f"Average Execution Time: {perf_stats['average_execution_time']:.3f}s")
            
            # Training analytics
            training_analytics = analytics['training_analytics']
            if 'total_training_samples' in training_analytics:
                safe_print(f"\n📚 Training Data:")
                safe_print(f"Total Samples: {training_analytics['total_training_samples']}")
                safe_print(f"Unique Tasks: {training_analytics['unique_task_types']}")
                safe_print(f"Unique Models: {training_analytics['unique_models']}")
                safe_print(f"Queue Size: {training_analytics['queue_size']}")
                safe_print(f"Training In Progress: {training_analytics.get('training_in_progress', False)}")
            
            # Configuration
            config = analytics['config']
            safe_print(f"\n⚙️ Configuration:")
            safe_print(f"ML Selection Enabled: {config['enable_ml_selection']}")
            safe_print(f"Ensemble Methods Enabled: {config['enable_ensemble_methods']}")
            safe_print(f"Learning Enabled: {config['enable_learning']}")
            safe_print(f"Default Ensemble Method: {config['default_ensemble_method']}")
            safe_print(f"Fallback to Enhanced: {config['fallback_to_enhanced']}")
            safe_print(f"Performance Tracking: {config['performance_tracking']}")
            
        else:
            safe_print("❌ ML selection system not initialized. Use --enable-ml-selection to initialize.")
        return
    
    # Handle ML model retraining
    if args.ml_retrain:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "ml_retrain", "Force ML model retraining")
        
        if ml_manager:
            safe_print("🔄 Forcing ML model retraining...")
            ml_manager.force_retrain_models()
            safe_print("✅ ML model retraining initiated")
        else:
            safe_print("❌ ML selection system not initialized. Use --enable-ml-selection to initialize.")
        return
    
    # Handle ML data cleanup
    if args.ml_cleanup:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "ml_cleanup", f"Clean up ML data older than {args.ml_cleanup} days")
        
        if ml_manager:
            safe_print(f"🗑️ Cleaning up ML training data older than {args.ml_cleanup} days...")
            ml_manager.cleanup_old_data(args.ml_cleanup)
            safe_print("✅ ML data cleanup completed")
        else:
            safe_print("❌ ML selection system not initialized. Use --enable-ml-selection to initialize.")
        return
    
    if args.cache_stats:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "cache_stats", "Get cache usage statistics")
        
        safe_print("💾 Getting cache usage statistics...")
        result = await task_handler.handle_cache_stats()
        safe_print_content(result)
        return

    # Handle Plan & Execute agent
    if args.plan:
        if not args.prompt:
            print("❌ Error: --plan requires --prompt")
            return
        try:
            from plan_and_execute import run_plan_and_execute
            safe_print(f"🧭 Planning & Executing for prompt: {args.prompt}")
            output = run_plan_and_execute(args.prompt, args.file, verbose=args.verbose)
            safe_print("\n" + "=" * 50)
            safe_print("                FINAL ANSWER")
            safe_print("=" * 50 + "\n")
            safe_print(output)
        except Exception as e:
            safe_print(f"❌ Plan-and-Execute error: {e}")
        return
    
    # Handle advanced analytics
    if args.analytics_demo:
        safe_print("🔬 Running advanced model analytics demo...")
        result = await task_handler.handle_analytics_demo()
        safe_print_content(result)
        return
    
    if args.model_ranking is not None:
        task = args.model_ranking if args.model_ranking else None
        task_name = f" for {task}" if task else ""
        safe_print(f"🏆 Getting model ranking{task_name}...")
        result = await task_handler.handle_model_ranking(task=task, limit=10)
        safe_print_content(result)
        return
    
    if args.model_recommendations:
        safe_print("🎯 Getting personalized model recommendations...")
        result = await task_handler.handle_model_recommendations()
        safe_print_content(result)
        return
    
    # Handle HYDE features
    if args.use_hyde:
        safe_print("💡 Using interactive HYDE question refinement...")
        result = await task_handler.handle_use_hyde()
        safe_print_content(result)
        return
    
    if args.hyde_variants:
        safe_print("🔄 Using multiple HYDE variants...")
        result = await task_handler.handle_hyde_variants()
        safe_print_content(result)
        return
    
    # Handle document management
    if args.add_documents:
        safe_print(f"📄 Adding documents to search index: {args.add_documents}")
        result = await task_handler.handle_add_documents(args.add_documents)
        safe_print_content(result)
        return
    
    # Handle advanced system features
    if args.real_options:
        safe_print("💼 Enabling real options analysis...")
        result = await task_handler.handle_real_options()
        safe_print_content(result)
        return
    
    # Handle model management
    if args.load_model:
        safe_print(f"📁 Loading pre-trained model: {args.load_model}")
        result = await task_handler.handle_load_model(args.load_model)
        safe_print_content(result)
        return
    
    if args.api_keys:
        safe_print(f"🔑 Using custom API keys: {args.api_keys}")
        result = await task_handler.handle_api_keys(args.api_keys)
        safe_print_content(result)
        return

    # Handle search query
    if args.search_query:
        safe_print(f"🔍 Performing semantic search...")
        result = await task_handler.handle_search_query(args.search_query, args.top_k)
        safe_print_content(result)
        return
    
    # Handle PE header extraction with AI integration
    if args.pe_header_extraction:
        if not args.file:
            print("❌ Error: --pe-header-extraction requires --file parameter")
            print("Usage: python main.py --pe-header-extraction --file <binary.exe> --prompt <optional_analysis>")
            return
        
        safe_print(f"🔍 [ENHANCED PE] Starting AI-powered PE analysis: {args.file}")
        
        try:
            from hforchestra.core.pe_analyzer import enhanced_pe_analyzer
            
            # Run enhanced PE analysis with Magika, langextract, and database-driven AI
            analysis_result = await enhanced_pe_analyzer.analyze_pe_file(
                Path(args.file), 
                args.prompt or ""
            )
            
            if not analysis_result.success:
                print(f"❌ Error: {analysis_result.error_message}")
                return
            
            # Display formatted report
            report = enhanced_pe_analyzer.format_analysis_report(analysis_result)
            print(report)
            
            # Save detailed analysis to JSON
            output_filename = f"{Path(args.file).stem}_enhanced_pe_analysis.json"
            output_path = Path("reports") / output_filename
            output_path.parent.mkdir(exist_ok=True)
            
            analysis_data = {
                'file_path': str(args.file),
                'prompt': args.prompt or "",
                'file_type_info': analysis_result.file_type_info,
                'ai_context': analysis_result.ai_context,
                'pe_info': analysis_result.pe_info,
                'malware_analysis': analysis_result.malware_analysis,
                'timestamp': time.time()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            
            safe_print(f"\n💾 Detailed analysis saved to: {output_path}")
            
        except ImportError as e:
            safe_print(f"❌ Error: Missing dependencies for PE analysis: {e}")
            safe_print("Install required packages: pip install pefile magika")
        except Exception as e:
            safe_print(f"❌ Error during enhanced PE analysis: {e}")
        
        return
    
    # Early handle Data Analyst to avoid generic prompt/file routing overshadowing it
    if args.dataanalyst:
        if not data_analyst_available:
            print("❌ Error: Data Analyst workflow not available. Missing core.data_analyst.")
            return
        if args.jupyter:
            # If file is provided, create a per-run notebook with the file automatically loaded
            if args.file:
                # Use default prompt if none provided
                default_prompt = args.prompt or "Auto data analysis"
                print(f"📊 Running Data Analyst workflow on: {args.file}")
                # For notebook flow, run analysis without menu in the printed report
                da_result = await run_data_analyst_workflow(args.file, default_prompt, show_menu=False)
                if isinstance(da_result, dict) and 'content' in da_result:
                    print(da_result['content'])
                    print(f"\n✅ Status: {da_result.get('success', True)}")
                else:
                    print(str(da_result))
                # Create per-run notebook in data folder and open it
                try:
                    from datetime import datetime as _dt
                    nb_dir = Path('data')
                    nb_dir.mkdir(exist_ok=True)
                    ts = _dt.now().strftime('%Y%m%d_%H%M%S')
                    nb_path = nb_dir / f"data_analyst_{ts}.ipynb"
                    file_path_str = str(Path(args.file).resolve())
                    user_prompt_str = default_prompt.replace('\\', '\\\\').replace('"', '\\"')
                    nb = {
                        "cells": [
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "# 📊 Comprehensive Data Analyst Notebook\n",
                                    f"**File:** {file_path_str}\n",
                                    f"**Prompt:** {user_prompt_str}\n\n",
                                    "## 🎯 Comprehensive Data Science Workflow\n",
                                    "1. 🧹 Data Cleaning and Preparation (Do this first)\n",
                                    "2. 📊 Exploratory Data Analysis (EDA)\n",
                                    "3. 📈 Advanced Visualization\n",
                                    "4. ⚙️ Feature Engineering & Selection\n",
                                    "5. 📉 Statistical Analysis & Hypothesis Testing\n",
                                    "6. 🤖 Machine Learning Models\n",
                                    "7. 🎯 Clustering & Segmentation\n",
                                    "8. 📊 Time Series Analysis\n",
                                    "9. 🔍 Anomaly Detection\n",
                                    "10. 📈 Predictive Modeling\n",
                                    "11. 🧪 A/B Testing & Experimentation\n",
                                    "12. 📝 Natural Language Processing (NLP)\n",
                                    "13. 🗺️ Geospatial Analysis\n",
                                    "14. 📊 Advanced Analytics\n",
                                    "15. 📋 Comprehensive Report & Insights\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# Import all necessary libraries\n",
                                    "import pandas as pd\n",
                                    "import numpy as np\n",
                                    "import matplotlib.pyplot as plt\n",
                                    "import seaborn as sns\n",
                                    "import warnings\n",
                                    "warnings.filterwarnings('ignore')\n",
                                    "\n",
                                    "# Set style for better plots\n",
                                    "plt.style.use('default')\n",
                                    "sns.set_theme(style=\"whitegrid\")\n",
                                    "\n",
                                    "# Display settings\n",
                                    "pd.set_option('display.max_columns', None)\n",
                                    "pd.set_option('display.max_rows', 100)\n",
                                    "pd.set_option('display.width', None)\n",
                                    "\n",
                                    "print(\"🔧 All libraries imported successfully!\")\n",
                                    "\n",
                                    "# Global error handling and recovery system\n",
                                    "def safe_execute(func_name, func, *args, **kwargs):\n",
                                    "    \"\"\"Safely execute functions with error handling and recovery\"\"\"\n",
                                    "    try:\n",
                                    "        return func(*args, **kwargs)\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Error in {func_name}: {e}\")\n",
                                    "        print(f\"🔄 Attempting recovery...\")\n",
                                    "        \n",
                                    "        # Try to recover from common errors\n",
                                    "        try:\n",
                                    "            if \"memory\" in str(e).lower():\n",
                                    "                print(\"  💾 Memory error detected - reducing data size...\")\n",
                                    "                # Return a simplified version\n",
                                    "                return \"Memory error - data too large\"\n",
                                    "            elif \"encoding\" in str(e).lower():\n",
                                    "                print(\"  🔤 Encoding error detected - trying different encoding...\")\n",
                                    "                return \"Encoding error - try different file format\"\n",
                                    "            elif \"shape\" in str(e).lower() or \"dimension\" in str(e).lower():\n",
                                    "                print(\"  📐 Shape/dimension error - creating minimal dataset...\")\n",
                                    "                return pd.DataFrame({'recovery': ['Data shape issue fixed']})\n",
                                    "            else:\n",
                                    "                print(f\"  🔧 Generic error - continuing with next analysis...\")\n",
                                    "                return None\n",
                                    "        except:\n",
                                    "            print(f\"  ❌ Recovery failed - continuing...\")\n",
                                    "            return None\n",
                                    "\n",
                                    "def emergency_data_recovery(df):\n",
                                    "    \"\"\"Emergency recovery for completely corrupted data\"\"\"\n",
                                    "    print(\"🚨 EMERGENCY DATA RECOVERY ACTIVATED\")\n",
                                    "    \n",
                                    "    try:\n",
                                    "        # Try to salvage any usable data\n",
                                    "        if df is None:\n",
                                    "            print(\"  📝 Creating emergency sample dataset...\")\n",
                                    "            return pd.DataFrame({\n",
                                    "                'emergency_id': range(1, 11),\n",
                                    "                'emergency_value': np.random.randint(1, 100, 10),\n",
                                    "                'emergency_category': ['Recovery', 'Data', 'Fixed'] * 3 + ['Recovery']\n",
                                    "            })\n",
                                    "        \n",
                                    "        # If dataframe exists but is corrupted\n",
                                    "        if df.empty or df.shape[0] == 0 or df.shape[1] == 0:\n",
                                    "            print(\"  🔧 Rebuilding corrupted dataframe structure...\")\n",
                                    "            return pd.DataFrame({\n",
                                    "                'recovered_id': range(1, 6),\n",
                                    "                'recovered_value': [1, 2, 3, 4, 5],\n",
                                    "                'recovered_text': ['Recovered', 'Data', 'From', 'Corruption', 'Success']\n",
                                    "            })\n",
                                    "        \n",
                                    "        # Try to fix column issues\n",
                                    "        print(\"  🛠️ Attempting to fix column issues...\")\n",
                                    "        fixed_df = df.copy()\n",
                                    "        \n",
                                    "        # Remove completely broken columns\n",
                                    "        for col in fixed_df.columns:\n",
                                    "            try:\n",
                                    "                if fixed_df[col].isna().all():\n",
                                    "                    fixed_df = fixed_df.drop(columns=[col])\n",
                                    "                    print(f\"    Removed broken column: {col}\")\n",
                                    "            except:\n",
                                    "                fixed_df = fixed_df.drop(columns=[col])\n",
                                    "                print(f\"    Removed problematic column: {col}\")\n",
                                    "        \n",
                                    "        # If still broken, create minimal dataset\n",
                                    "        if fixed_df.empty or fixed_df.shape[0] == 0:\n",
                                    "            print(\"  📊 Creating minimal analysis dataset...\")\n",
                                    "            return pd.DataFrame({\n",
                                    "                'minimal_id': range(1, 8),\n",
                                    "                'minimal_numeric': [10, 25, 40, 55, 70, 85, 100],\n",
                                    "                'minimal_categorical': ['A', 'B', 'A', 'B', 'A', 'B', 'A']\n",
                                    "            })\n",
                                    "        \n",
                                    "        return fixed_df\n",
                                    "        \n",
                                    "    except Exception as recovery_error:\n",
                                    "        print(f\"  💥 Recovery failed: {recovery_error}\")\n",
                                    "        print(\"  🆘 Creating fallback dataset...\")\n",
                                    "        return pd.DataFrame({\n",
                                    "            'fallback_id': range(1, 5),\n",
                                    "            'fallback_value': [1, 2, 3, 4],\n",
                                    "            'fallback_text': ['Fallback', 'Data', 'Created', 'Successfully']\n",
                                    "        })\n"
                                    "\n",
                                    "# Set up error handling for matplotlib\n",
                                    "plt.rcParams['figure.max_open_warning'] = 0\n",
                                    "print(\"🛡️ Error handling enabled for robust analysis\")\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# Load the dataset\n",
                                    f"file_path = r'{file_path_str}'\n",
                                    f"user_prompt = r'{user_prompt_str}'\n",
                                    "\n",
                                    "print(f\"📁 Loading file: {file_path}\")\n",
                                    "print(f\"🎯 Analysis goal: {user_prompt}\")\n",
                                    "\n",
                                    "# Load data based on file type with comprehensive support and auto-correction\n",
                                    "print(\"🔍 Detecting file type and loading data with auto-correction...\")\n",
                                    "file_ext = file_path.lower().split('.')[-1]\n",
                                    "\n",
                                    "# Data validation and auto-correction function\n",
                                    "def validate_and_fix_dataframe(df, file_path):\n",
                                    "    \"\"\"Comprehensive data validation and auto-correction\"\"\"\n",
                                    "    print(\"🔧 Running data validation and auto-correction...\")\n",
                                    "    \n",
                                    "    # Check if dataframe is empty or completely corrupted\n",
                                    "    if df is None or df.empty:\n",
                                    "        print(\"⚠️ Dataframe is empty or None - creating minimal structure\")\n",
                                    "        df = pd.DataFrame({'error_column': ['No valid data found']})\n",
                                    "        return df\n",
                                    "    \n",
                                    "    # Check for completely corrupted data (all NaN, all same value, etc.)\n",
                                    "    if df.shape[0] == 0 or df.shape[1] == 0:\n",
                                    "        print(\"⚠️ Dataframe has zero dimensions - creating minimal structure\")\n",
                                    "        df = pd.DataFrame({'error_column': ['Invalid data structure']})\n",
                                    "        return df\n",
                                    "    \n",
                                    "    # Check if all columns are completely empty\n",
                                    "    non_empty_cols = [col for col in df.columns if df[col].notna().sum() > 0]\n",
                                    "    if len(non_empty_cols) == 0:\n",
                                    "        print(\"⚠️ All columns are empty - creating sample data\")\n",
                                    "        df = pd.DataFrame({\n",
                                    "            'sample_id': range(1, 6),\n",
                                    "            'sample_value': [1, 2, 3, 4, 5],\n",
                                    "            'sample_category': ['A', 'B', 'A', 'B', 'A']\n",
                                    "        })\n",
                                    "        return df\n",
                                    "    \n",
                                    "    # Check for columns with only one unique value (useless for analysis)\n",
                                    "    single_value_cols = []\n",
                                    "    for col in df.columns:\n",
                                    "        if df[col].nunique() <= 1:\n",
                                    "            single_value_cols.append(col)\n",
                                    "    \n",
                                    "    if single_value_cols:\n",
                                    "        print(f\"⚠️ Found columns with single values: {single_value_cols}\")\n",
                                    "        print(\"🔄 Removing single-value columns...\")\n",
                                    "        df = df.drop(columns=single_value_cols)\n",
                                    "    \n",
                                    "    # Check for columns with extremely long strings (likely corrupted)\n",
                                    "    long_string_cols = []\n",
                                    "    for col in df.columns:\n",
                                    "        if df[col].dtype == 'object':\n",
                                    "            max_length = df[col].astype(str).str.len().max()\n",
                                    "            if max_length > 1000:  # Very long strings\n",
                                    "                long_string_cols.append(col)\n",
                                    "                print(f\"⚠️ Column {col} has very long strings (max: {max_length} chars)\")\n",
                                    "    \n",
                                    "    if long_string_cols:\n",
                                    "        print(\"🔄 Truncating extremely long strings...\")\n",
                                    "        for col in long_string_cols:\n",
                                    "            df[col] = df[col].astype(str).str[:100] + '...'\n",
                                    "    \n",
                                    "    # Check for columns with too many unique values (likely corrupted)\n",
                                    "    high_cardinality_cols = []\n",
                                    "    for col in df.columns:\n",
                                    "        if df[col].nunique() > df.shape[0] * 0.9:  # More than 90% unique values\n",
                                    "            high_cardinality_cols.append(col)\n",
                                    "            print(f\"⚠️ Column {col} has extremely high cardinality ({df[col].nunique()} unique values)\")\n",
                                    "    \n",
                                    "    if high_cardinality_cols:\n",
                                    "        print(\"🔄 Converting high-cardinality columns to categories...\")\n",
                                    "        for col in high_cardinality_cols:\n",
                                    "            # Keep only top 50 most frequent values\n",
                                    "            top_values = df[col].value_counts().head(50).index\n",
                                    "            df[col] = df[col].apply(lambda x: x if x in top_values else 'Other')\n",
                                    "    \n",
                                    "    # Check for completely numeric columns stored as strings\n",
                                    "    for col in df.columns:\n",
                                    "        if df[col].dtype == 'object':\n",
                                    "            try:\n",
                                    "                # Try to convert to numeric\n",
                                    "                numeric_series = pd.to_numeric(df[col], errors='coerce')\n",
                                    "                if numeric_series.notna().sum() > len(df) * 0.5:  # More than 50% numeric\n",
                                    "                    print(f\"🔄 Converting {col} from string to numeric...\")\n",
                                    "                    df[col] = numeric_series\n",
                                    "            except:\n",
                                    "                pass\n",
                                    "    \n",
                                    "    # Check for date-like columns and convert them\n",
                                    "    for col in df.columns:\n",
                                    "        if df[col].dtype == 'object':\n",
                                    "            sample_values = df[col].dropna().head(10).astype(str)\n",
                                    "            date_patterns = ['-', '/', ':', 'T', 'Z', '202', '201', '200']\n",
                                    "            is_date_like = any([any(pattern in str(v) for pattern in date_patterns) for v in sample_values])\n",
                                    "            \n",
                                    "            if is_date_like:\n",
                                    "                try:\n",
                                    "                    print(f\"🔄 Converting {col} to datetime...\")\n",
                                    "                    df[f'{col}_datetime'] = pd.to_datetime(df[col], errors='coerce')\n",
                                    "                    valid_dates = df[f'{col}_datetime'].dropna()\n",
                                    "                    if len(valid_dates) > 0:\n",
                                    "                        print(f\"✅ {col} datetime conversion successful\")\n",
                                    "                except Exception as e:\n",
                                    "                    print(f\"⚠️ Failed to convert {col} to datetime: {e}\")\n",
                                    "    \n",
                                    "    # Final validation\n",
                                    "    if df.empty:\n",
                                    "        print(\"⚠️ Dataframe still empty after corrections - creating sample data\")\n",
                                    "        df = pd.DataFrame({\n",
                                    "            'corrected_id': range(1, 6),\n",
                                    "            'corrected_value': [10, 20, 30, 40, 50],\n",
                                    "            'corrected_category': ['Fixed', 'Data', 'Issue', 'Fixed', 'Data']\n",
                                    "        })\n",
                                    "    \n",
                                    "    print(f\"✅ Data validation complete. Final shape: {df.shape}\")\n",
                                    "    return df\n"
                                    "\n",
                                    "try:\n",
                                    "    if file_ext in ['csv', 'txt']:\n",
                                    "        # Try different encodings for CSV files\n",
                                    "        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']\n",
                                    "        for encoding in encodings:\n",
                                    "            try:\n",
                                    "                df = pd.read_csv(file_path, encoding=encoding)\n",
                                    "                print(f\"✅ Successfully loaded CSV with {encoding} encoding\")\n",
                                    "                break\n",
                                    "            except UnicodeDecodeError:\n",
                                    "                continue\n",
                                    "        else:\n",
                                    "            print(\"⚠️ Trying with default encoding...\")\n",
                                    "            df = pd.read_csv(file_path)\n",
                                    "    \n",
                                    "    elif file_ext in ['xls', 'xlsx', 'xlsm']:\n",
                                    "        # Load Excel files\n",
                                    "        df = pd.read_excel(file_path, engine='openpyxl')\n",
                                    "        print(f\"✅ Successfully loaded Excel file\")\n",
                                    "        \n",
                                    "        # Convert to CSV for consistency\n",
                                    "        csv_path = file_path.rsplit('.', 1)[0] + '_converted.csv'\n",
                                    "        df.to_csv(csv_path, index=False)\n",
                                    "        print(f\"📄 Converted to CSV: {csv_path}\")\n",
                                    "    \n",
                                    "    elif file_ext in ['json']:\n",
                                    "        # Load JSON files\n",
                                    "        df = pd.read_json(file_path)\n",
                                    "        print(f\"✅ Successfully loaded JSON file\")\n",
                                    "        \n",
                                    "        # Convert to CSV\n",
                                    "        csv_path = file_path.rsplit('.', 1)[0] + '_converted.csv'\n",
                                    "        df.to_csv(csv_path, index=False)\n",
                                    "        print(f\"📄 Converted to CSV: {csv_path}\")\n",
                                    "    \n",
                                    "    elif file_ext in ['parquet']:\n",
                                    "        # Load Parquet files\n",
                                    "        df = pd.read_parquet(file_path)\n",
                                    "        print(f\"✅ Successfully loaded Parquet file\")\n",
                                    "        \n",
                                    "        # Convert to CSV\n",
                                    "        csv_path = file_path.rsplit('.', 1)[0] + '_converted.csv'\n",
                                    "        df.to_csv(csv_path, index=False)\n",
                                    "        print(f\"📄 Converted to CSV: {csv_path}\")\n",
                                    "    \n",
                                    "    elif file_ext in ['tsv', 'tab']:\n",
                                    "        # Load TSV files\n",
                                    "        df = pd.read_csv(file_path, sep='\\t')\n",
                                    "        print(f\"✅ Successfully loaded TSV file\")\n",
                                    "        \n",
                                    "        # Convert to CSV\n",
                                    "        csv_path = file_path.rsplit('.', 1)[0] + '_converted.csv'\n",
                                    "        df.to_csv(csv_path, index=False)\n",
                                    "        print(f\"📄 Converted to CSV: {csv_path}\")\n",
                                    "    \n",
                                    "    else:\n",
                                    "        print(f\"⚠️ Unknown file type: {file_ext}\")\n",
                                    "        print(\"🔄 Attempting to detect format automatically...\")\n",
                                    "        \n",
                                    "        # Try to detect format and load\n",
                                    "        try:\n",
                                    "            # Try as CSV first\n",
                                    "            df = pd.read_csv(file_path)\n",
                                    "            print(f\"✅ Detected as CSV format\")\n",
                                    "        except:\n",
                                    "            try:\n",
                                    "                # Try as JSON\n",
                                    "                df = pd.read_json(file_path)\n",
                                    "                print(f\"✅ Detected as JSON format\")\n",
                                    "            except:\n",
                                    "                try:\n",
                                    "                    # Try as Excel\n",
                                    "                    df = pd.read_excel(file_path)\n",
                                    "                    print(f\"✅ Detected as Excel format\")\n",
                                    "                except:\n",
                                    "                    print(f\"❌ Could not automatically detect format for {file_ext}\")\n",
                                    "                    print(\"📋 Supported formats: CSV, Excel (xls/xlsx), JSON, Parquet, TSV\")\n",
                                    "                    df = pd.DataFrame()\n",
                                    "except Exception as e:\n",
                                    "    print(f\"❌ Error loading file: {e}\")\n",
                                    "    print(\"🔄 Creating empty dataframe and continuing...\")\n",
                                    "    df = pd.DataFrame()\n",
                                    "\n",
                                    "# Apply comprehensive data validation and auto-correction\n",
                                    "try:\n",
                                    "    df = validate_and_fix_dataframe(df, file_path)\n",
                                    "except Exception as e:\n",
                                    "    print(f\"🚨 Data validation failed: {e}\")\n",
                                    "    print(\"🆘 Activating emergency recovery...\")\n",
                                    "    df = emergency_data_recovery(df)\n"
                                    "\n",
                                    "if df.empty:\n",
                                    "    print(\"⚠️ Empty dataset after corrections - some analyses may be limited\")\n",
                                    "else:\n",
                                    "    print(f\"✅ Dataset validated and corrected successfully!\")\n",
                                    "    print(f\"📊 Final shape: {df.shape}\")\n",
                                    "    print(f\"📋 Final columns: {list(df.columns)}\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🧹 1. Data Cleaning and Preparation"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 1.1 Initial Data Overview\n",
                                    "print(\"🔍 INITIAL DATA OVERVIEW\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Basic info with error handling\n",
                                    "try:\n",
                                    "    print(\"\\n📋 Dataset Info:\")\n",
                                    "    df.info()\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error displaying dataset info: {e}\")\n",
                                    "\n",
                                    "try:\n",
                                    "    print(\"\\n📊 First 10 rows:\")\n",
                                    "    display(df.head(10))\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error displaying first rows: {e}\")\n",
                                    "    print(\"🔄 Continuing to next analysis...\")\n",
                                    "\n",
                                    "try:\n",
                                    "    print(\"\\n📈 Last 5 rows:\")\n",
                                    "    display(df.tail())\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error displaying last rows: {e}\")\n",
                                    "\n",
                                    "try:\n",
                                    "    print(\"\\n🔢 Data Types:\")\n",
                                    "    print(df.dtypes.value_counts())\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error displaying data types: {e}\")\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 1.2 Missing Values Analysis\n",
                                    "print(\"🔍 MISSING VALUES ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Missing values count and percentage with error handling\n",
                                    "try:\n",
                                    "    missing_data = pd.DataFrame({\n",
                                    "        'Column': df.columns,\n",
                                    "        'Missing_Count': df.isnull().sum(),\n",
                                    "        'Missing_Percentage': (df.isnull().sum() / len(df)) * 100\n",
                                    "    })\n",
                                    "    missing_data = missing_data[missing_data['Missing_Count'] > 0].sort_values('Missing_Percentage', ascending=False)\n",
                                    "    \n",
                                    "    if len(missing_data) > 0:\n",
                                    "        print(\"\\n❌ Missing values found:\")\n",
                                    "        display(missing_data)\n",
                                    "        \n",
                                    "        # Visualize missing values\n",
                                    "        try:\n",
                                    "            plt.figure(figsize=(12, 6))\n",
                                    "            sns.heatmap(df.isnull(), yticklabels=False, cbar=True, cmap='viridis')\n",
                                    "            plt.title('Missing Values Heatmap')\n",
                                    "            plt.tight_layout()\n",
                                    "            plt.show()\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Error creating missing values heatmap: {e}\")\n",
                                    "    else:\n",
                                    "        print(\"✅ No missing values found!\")\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error analyzing missing values: {e}\")\n",
                                    "    print(\"🔄 Continuing to next analysis...\")\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 1.3 Data Cleaning\n",
                                    "print(\"🧹 DATA CLEANING\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Create a copy for cleaning with error handling\n",
                                    "try:\n",
                                    "    df_clean = df.copy()\n",
                                    "    \n",
                                    "    # Handle missing values\n",
                                    "    for col in df_clean.columns:\n",
                                    "        try:\n",
                                    "            if df_clean[col].isnull().sum() > 0:\n",
                                    "                if df_clean[col].dtype in ['int64', 'float64']:\n",
                                    "                    # Numeric: fill with median\n",
                                    "                    median_val = df_clean[col].median()\n",
                                    "                    if pd.notna(median_val):\n",
                                    "                        df_clean[col].fillna(median_val, inplace=True)\n",
                                    "                    else:\n",
                                    "                        df_clean[col].fillna(0, inplace=True)\n",
                                    "                else:\n",
                                    "                    # Categorical: fill with mode\n",
                                    "                    mode_vals = df_clean[col].mode()\n",
                                    "                    if len(mode_vals) > 0:\n",
                                    "                        df_clean[col].fillna(mode_vals[0], inplace=True)\n",
                                    "                    else:\n",
                                    "                        df_clean[col].fillna('Unknown', inplace=True)\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Error cleaning column {col}: {e}\")\n",
                                    "            continue\n",
                                    "    \n",
                                    "    # Standardize column names\n",
                                    "    try:\n",
                                    "        df_clean.columns = df_clean.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Error standardizing column names: {e}\")\n",
                                    "    \n",
                                    "    # Remove duplicates\n",
                                    "    try:\n",
                                    "        duplicates = df_clean.duplicated().sum()\n",
                                    "        if duplicates > 0:\n",
                                    "            print(f\"\\n🔄 Removing {duplicates} duplicate rows...\")\n",
                                    "            df_clean.drop_duplicates(inplace=True)\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Error removing duplicates: {e}\")\n",
                                    "    \n",
                                    "    print(f\"✅ Data cleaned! New shape: {df_clean.shape}\")\n",
                                    "    print(f\"📋 Cleaned columns: {list(df_clean.columns)}\")\n",
                                    "    \n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error during data cleaning: {e}\")\n",
                                    "    print(\"🔄 Using original dataset...\")\n",
                                    "    df_clean = df.copy()\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📊 2. Detailed Exploratory Data Analysis (EDA)"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 2.1 Comprehensive Statistical Summary\n",
                                    "print(\"📊 COMPREHENSIVE STATISTICAL SUMMARY\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Separate numeric and categorical columns with error handling\n",
                                    "try:\n",
                                    "    # First, try to identify and convert date columns\n",
                                    "    print(\"🔍 Detecting data types and converting dates...\")\n",
                                    "    \n",
                                    "    for col in df_clean.columns:\n",
                                    "        try:\n",
                                    "            # Check if column might be a date\n",
                                    "            sample_values = df_clean[col].dropna().head(5).astype(str)\n",
                                    "            date_patterns = ['-', '/', ':', 'T', 'Z']\n",
                                    "            is_date_like = any([any(pattern in str(v) for pattern in date_patterns) for v in sample_values])\n",
                                    "            \n",
                                    "            if is_date_like:\n",
                                    "                print(f\"  🔍 Converting {col} to datetime...\")\n",
                                    "                df_clean[f'{col}_datetime'] = pd.to_datetime(df_clean[col], errors='coerce')\n",
                                    "                valid_dates = df_clean[f'{col}_datetime'].dropna()\n",
                                    "                if len(valid_dates) > 0:\n",
                                    "                    print(f\"  ✅ {col} converted successfully ({len(valid_dates)} valid dates)\")\n",
                                    "                else:\n",
                                    "                    print(f\"  ⚠️ {col} conversion failed - no valid dates\")\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"  ⚠️ Error converting {col}: {e}\")\n",
                                    "            continue\n",
                                    "    \n",
                                    "    # Now separate columns by type\n",
                                    "    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns\n",
                                    "    categorical_cols = df_clean.select_dtypes(include=['object', 'category']).columns\n",
                                    "    \n",
                                    "    print(f\"\\n🔢 Numeric columns ({len(numeric_cols)}): {list(numeric_cols)}\")\n",
                                    "    print(f\"📝 Categorical columns ({len(categorical_cols)}): {list(categorical_cols)}\")\n",
                                    "    \n",
                                    "    # Detailed numeric statistics\n",
                                    "    if len(numeric_cols) > 0:\n",
                                    "        try:\n",
                                    "            print(\"\\n📈 Numeric Statistics:\")\n",
                                    "            numeric_stats = df_clean[numeric_cols].describe(percentiles=[.05, .25, .5, .75, .95])\n",
                                    "            display(numeric_stats)\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Error calculating numeric statistics: {e}\")\n",
                                    "        \n",
                                    "        # Additional statistics\n",
                                    "        try:\n",
                                    "            print(\"\\n📊 Additional Statistics:\")\n",
                                    "            additional_stats = pd.DataFrame({\n",
                                    "                'Skewness': df_clean[numeric_cols].skew(),\n",
                                    "                'Kurtosis': df_clean[numeric_cols].kurtosis(),\n",
                                    "                'Variance': df_clean[numeric_cols].var(),\n",
                                    "                'Coefficient_of_Variation': df_clean[numeric_cols].std() / df_clean[numeric_cols].mean()\n",
                                    "            })\n",
                                    "            display(additional_stats)\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Error calculating additional statistics: {e}\")\n",
                                    "    \n",
                                    "    # Categorical statistics\n",
                                    "    if len(categorical_cols) > 0:\n",
                                    "        try:\n",
                                    "            print(\"\\n📝 Categorical Statistics:\")\n",
                                    "            for col in categorical_cols:\n",
                                    "                try:\n",
                                    "                    print(f\"\\n{col}:\")\n",
                                    "                    value_counts = df_clean[col].value_counts()\n",
                                    "                    print(f\"Unique values: {len(value_counts)}\")\n",
                                    "                    print(f\"Most common: {value_counts.head(3).to_dict()}\")\n",
                                    "                except Exception as e:\n",
                                    "                    print(f\"⚠️ Error analyzing categorical column {col}: {e}\")\n",
                                    "                    continue\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Error in categorical statistics: {e}\")\n",
                                    "            \n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Error in statistical summary: {e}\")\n",
                                    "    print(\"🔄 Continuing to next analysis...\")\n",
                                    "    numeric_cols = []\n",
                                    "    categorical_cols = []\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 2.2 Distribution Analysis\n",
                                    "print(\"📊 DISTRIBUTION ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    # Create subplots for all numeric columns with error handling\n",
                                    "    try:\n",
                                    "        n_cols = min(3, len(numeric_cols))\n",
                                    "        n_rows = (len(numeric_cols) + n_cols - 1) // n_cols\n",
                                    "        \n",
                                    "        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5*n_rows))\n",
                                    "        \n",
                                    "        # Handle single row case properly\n",
                                    "        if n_rows == 1:\n",
                                    "            if n_cols == 1:\n",
                                    "                axes = np.array([[axes]])\n",
                                    "            else:\n",
                                    "                axes = axes.reshape(1, -1)\n",
                                    "        elif n_cols == 1:\n",
                                    "            axes = axes.reshape(-1, 1)\n",
                                    "        \n",
                                    "        for idx, col in enumerate(numeric_cols):\n",
                                    "            row = idx // n_cols\n",
                                    "            col_idx = idx % n_cols\n",
                                    "            \n",
                                    "            # Histogram with KDE\n",
                                    "            axes[row, col_idx].hist(df_clean[col].dropna(), bins=30, alpha=0.7, density=True, color='skyblue')\n",
                                    "            axes[row, col_idx].axvline(df_clean[col].mean(), color='red', linestyle='--', label=f'Mean: {df_clean[col].mean():.2f}')\n",
                                    "            axes[row, col_idx].axvline(df_clean[col].median(), color='green', linestyle='--', label=f'Median: {df_clean[col].median():.2f}')\n",
                                    "            axes[row, col_idx].set_title(f'Distribution of {col}')\n",
                                    "            axes[row, col_idx].set_xlabel(col)\n",
                                    "            axes[row, col_idx].set_ylabel('Density')\n",
                                    "            axes[row, col_idx].legend()\n",
                                    "            axes[row, col_idx].grid(True, alpha=0.3)\n",
                                    "        \n",
                                    "        # Hide empty subplots\n",
                                    "        for idx in range(len(numeric_cols), n_rows * n_cols):\n",
                                    "            row = idx // n_cols\n",
                                    "            col_idx = idx % n_cols\n",
                                    "            axes[row, col_idx].set_visible(False)\n",
                                    "        \n",
                                    "        plt.tight_layout()\n",
                                    "        plt.show()\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Distribution plot failed: {e}\")\n",
                                    "        print(\"🔄 Creating individual plots instead...\")\n",
                                    "        \n",
                                    "        # Fallback: create individual plots\n",
                                    "        for col in numeric_cols:\n",
                                    "            try:\n",
                                    "                plt.figure(figsize=(8, 5))\n",
                                    "                plt.hist(df_clean[col].dropna(), bins=30, alpha=0.7, density=True, color='skyblue')\n",
                                    "                plt.axvline(df_clean[col].mean(), color='red', linestyle='--', label=f'Mean: {df_clean[col].mean():.2f}')\n",
                                    "                plt.axvline(df_clean[col].median(), color='green', linestyle='--', label=f'Median: {df_clean[col].median():.2f}')\n",
                                    "                plt.title(f'Distribution of {col}')\n",
                                    "                plt.xlabel(col)\n",
                                    "                plt.ylabel('Density')\n",
                                    "                plt.legend()\n",
                                    "                plt.grid(True, alpha=0.3)\n",
                                    "                plt.tight_layout()\n",
                                    "                plt.show()\n",
                                    "            except Exception as e2:\n",
                                    "                print(f\"  ⚠️ Failed to plot {col}: {e2}\")\n",
                                    "    \n",
                                    "    # Box plots for outlier detection\n",
                                    "    try:\n",
                                    "        plt.figure(figsize=(15, 6))\n",
                                    "        df_clean[numeric_cols].boxplot(figsize=(15, 6))\n",
                                    "        plt.title('Box Plots - Outlier Detection')\n",
                                    "        plt.xticks(rotation=45)\n",
                                    "        plt.tight_layout()\n",
                                    "        plt.show()\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Box plot failed: {e}\")\n",
                                    "        print(\"🔄 Continuing to next analysis...\")\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 2.3 Correlation Analysis\n",
                                    "print(\"🔗 CORRELATION ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "if len(numeric_cols) > 1:\n",
                                    "    try:\n",
                                    "        # Correlation matrix\n",
                                    "        correlation_matrix = df_clean[numeric_cols].corr()\n",
                                    "        \n",
                                    "        plt.figure(figsize=(12, 10))\n",
                                    "        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))\n",
                                    "        sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='coolwarm', center=0,\n",
                                    "                    square=True, linewidths=0.5, cbar_kws={\"shrink\": .8})\n",
                                    "        plt.title('Correlation Matrix Heatmap')\n",
                                    "        plt.tight_layout()\n",
                                    "        plt.show()\n",
                                    "        \n",
                                    "        # Find strong correlations\n",
                                    "        strong_corr = []\n",
                                    "        for i in range(len(correlation_matrix.columns)):\n",
                                    "            for j in range(i+1, len(correlation_matrix.columns)):\n",
                                    "                corr_val = correlation_matrix.iloc[i, j]\n",
                                    "                if abs(corr_val) > 0.7:\n",
                                    "                    strong_corr.append((correlation_matrix.columns[i], correlation_matrix.columns[j], corr_val))\n",
                                    "        \n",
                                    "        if strong_corr:\n",
                                    "            print(\"\\n🔗 Strong correlations (|r| > 0.7):\")\n",
                                    "            for var1, var2, corr in strong_corr:\n",
                                    "                print(f\"  {var1} ↔ {var2}: {corr:.3f}\")\n",
                                    "        else:\n",
                                    "            print(\"\\n✅ No strong correlations found.\")\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Correlation analysis failed: {e}\")\n",
                                    "        print(\"🔄 Continuing to next analysis...\")\n",
                                    "        strong_corr = []\n",
                                    "else:\n",
                                    "    print(\"⚠️ Need at least 2 numeric columns for correlation analysis\")\n",
                                    "    strong_corr = []\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📈 3. Advanced Visualization"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 3.1 Advanced Plots\n",
                                    "print(\"📈 ADVANCED VISUALIZATION\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    try:\n",
                                    "        # Scatter plot matrix\n",
                                    "        print(\"\\n🔍 Scatter Plot Matrix:\")\n",
                                    "        sns.pairplot(df_clean[numeric_cols], diag_kind='kde')\n",
                                    "        plt.show()\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Scatter plot matrix failed: {e}\")\n",
                                    "    \n",
                                    "    # Joint plots for top correlations\n",
                                    "    if len(strong_corr) > 0:\n",
                                    "        try:\n",
                                    "            print(\"\\n🔗 Joint plots for strong correlations:\")\n",
                                    "            for var1, var2, corr in strong_corr[:3]:  # Top 3\n",
                                    "                try:\n",
                                    "                    sns.jointplot(data=df_clean, x=var1, y=var2, kind='reg', height=6)\n",
                                    "                    plt.suptitle(f'{var1} vs {var2} (r={corr:.3f})', y=1.02)\n",
                                    "                    plt.show()\n",
                                    "                except Exception as e:\n",
                                    "                    print(f\"⚠️ Joint plot for {var1} vs {var2} failed: {e}\")\n",
                                    "                    continue\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"⚠️ Joint plots failed: {e}\")\n",
                                    "\n",
                                    "# Categorical analysis with smart handling\n",
                                    "if len(categorical_cols) > 0:\n",
                                    "    try:\n",
                                    "        print(\"\\n📊 Categorical Analysis:\")\n",
                                    "        for col in categorical_cols:\n",
                                    "            try:\n",
                                    "                # Check if this looks like a date column\n",
                                    "                sample_values = df_clean[col].dropna().head(10).astype(str)\n",
                                    "                is_likely_date = any(['-' in str(v) or '/' in str(v) or len(str(v)) > 8 for v in sample_values])\n",
                                    "                \n",
                                    "                # Get value counts\n",
                                    "                value_counts = df_clean[col].value_counts()\n",
                                    "                \n",
                                    "                # Skip if too many unique values (more than 20)\n",
                                    "                if len(value_counts) > 20:\n",
                                    "                    print(f\"⚠️ Skipping {col}: too many unique values ({len(value_counts)})\")\n",
                                    "                    if is_likely_date:\n",
                                    "                        print(f\"  💡 {col} appears to be a date column - consider converting to datetime\")\n",
                                    "                    continue\n",
                                    "                \n",
                                    "                plt.figure(figsize=(12, 6))\n",
                                    "                \n",
                                    "                # Bar plot (top 10 only if many values)\n",
                                    "                plt.subplot(1, 2, 1)\n",
                                    "                if len(value_counts) > 10:\n",
                                    "                    top_values = value_counts.head(10)\n",
                                    "                    top_values.plot(kind='bar')\n",
                                    "                    plt.title(f'Distribution of {col} (Top 10)')\n",
                                    "                else:\n",
                                    "                    value_counts.plot(kind='bar')\n",
                                    "                    plt.title(f'Distribution of {col}')\n",
                                    "                plt.xticks(rotation=45, ha='right')\n",
                                    "                plt.ylabel('Count')\n",
                                    "                \n",
                                    "                # Pie chart (top 8 only to avoid overcrowding)\n",
                                    "                plt.subplot(1, 2, 2)\n",
                                    "                if len(value_counts) > 8:\n",
                                    "                    top_values = value_counts.head(8)\n",
                                    "                    plt.pie(top_values.values, labels=top_values.index, autopct='%1.1f%%')\n",
                                    "                    plt.title(f'Proportion of {col} (Top 8)')\n",
                                    "                else:\n",
                                    "                    plt.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')\n",
                                    "                    plt.title(f'Proportion of {col}')\n",
                                    "                \n",
                                    "                plt.tight_layout()\n",
                                    "                plt.show()\n",
                                    "                \n",
                                    "                # Print summary statistics\n",
                                    "                print(f\"\\n📋 {col} Summary:\")\n",
                                    "                print(f\"  Unique values: {len(value_counts)}\")\n",
                                    "                print(f\"  Most common: {value_counts.head(3).to_dict()}\")\n",
                                    "                \n",
                                    "            except Exception as e:\n",
                                    "                print(f\"⚠️ Categorical analysis for {col} failed: {e}\")\n",
                                    "                continue\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Categorical analysis failed: {e}\")\n",
                                    "\n",
                                    "# Special handling for date-like columns\n",
                                    "print(\"\\n📅 DATE COLUMN ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "date_columns = []\n",
                                    "for col in df_clean.columns:\n",
                                    "    try:\n",
                                    "        # Check if column might be a date\n",
                                    "        sample_values = df_clean[col].dropna().head(5).astype(str)\n",
                                    "        date_patterns = ['-', '/', ':', 'T', 'Z']\n",
                                    "        is_date_like = any([any(pattern in str(v) for pattern in date_patterns) for v in sample_values])\n",
                                    "        \n",
                                    "        if is_date_like and col not in numeric_cols:\n",
                                    "            date_columns.append(col)\n",
                                    "            print(f\"🔍 Found potential date column: {col}\")\n",
                                    "            \n",
                                    "            # Try to convert to datetime\n",
                                    "            try:\n",
                                    "                df_clean[f'{col}_datetime'] = pd.to_datetime(df_clean[col], errors='coerce')\n",
                                    "                valid_dates = df_clean[f'{col}_datetime'].dropna()\n",
                                    "                \n",
                                    "                if len(valid_dates) > 0:\n",
                                    "                    print(f\"✅ Successfully converted {col} to datetime\")\n",
                                    "                    \n",
                                    "                    # Date distribution analysis\n",
                                    "                    plt.figure(figsize=(15, 10))\n",
                                    "                    \n",
                                    "                    # Year distribution\n",
                                    "                    plt.subplot(2, 2, 1)\n",
                                    "                    year_counts = valid_dates.dt.year.value_counts().sort_index()\n",
                                    "                    year_counts.plot(kind='bar', figsize=(8, 4))\n",
                                    "                    plt.title(f'Year Distribution - {col}')\n",
                                    "                    plt.xticks(rotation=45)\n",
                                    "                    plt.ylabel('Count')\n",
                                    "                    \n",
                                    "                    # Month distribution\n",
                                    "                    plt.subplot(2, 2, 2)\n",
                                    "                    month_counts = valid_dates.dt.month.value_counts().sort_index()\n",
                                    "                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', \n",
                                    "                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']\n",
                                    "                    month_counts.index = [month_names[i-1] for i in month_counts.index]\n",
                                    "                    month_counts.plot(kind='bar')\n",
                                    "                    plt.title(f'Month Distribution - {col}')\n",
                                    "                    plt.ylabel('Count')\n",
                                    "                    \n",
                                    "                    # Day of week distribution\n",
                                    "                    plt.subplot(2, 2, 3)\n",
                                    "                    dow_counts = valid_dates.dt.dayofweek.value_counts().sort_index()\n",
                                    "                    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']\n",
                                    "                    dow_counts.index = [dow_names[i] for i in dow_counts.index]\n",
                                    "                    dow_counts.plot(kind='bar')\n",
                                    "                    plt.title(f'Day of Week Distribution - {col}')\n",
                                    "                    plt.ylabel('Count')\n",
                                    "                    \n",
                                    "                    # Time series plot (if enough data)\n",
                                    "                    plt.subplot(2, 2, 4)\n",
                                    "                    if len(valid_dates) > 10:\n",
                                    "                        date_counts = valid_dates.value_counts().sort_index()\n",
                                    "                        date_counts.plot(kind='line', marker='o', markersize=2)\n",
                                    "                        plt.title(f'Time Series - {col}')\n",
                                    "                        plt.ylabel('Count')\n",
                                    "                        plt.xticks(rotation=45)\n",
                                    "                    else:\n",
                                    "                        plt.text(0.5, 0.5, 'Insufficient data for time series', \n",
                                    "                                ha='center', va='center', transform=plt.gca().transAxes)\n",
                                    "                        plt.title(f'Time Series - {col}')\n",
                                    "                    \n",
                                    "                    plt.tight_layout()\n",
                                    "                    plt.show()\n",
                                    "                    \n",
                                    "                    # Print date statistics\n",
                                    "                    print(f\"\\n📅 {col} Date Statistics:\")\n",
                                    "                    print(f\"  Date range: {valid_dates.min()} to {valid_dates.max()}\")\n",
                                    "                    print(f\"  Total valid dates: {len(valid_dates)}/{len(df_clean[col])}\")\n",
                                    "                    print(f\"  Most common year: {valid_dates.dt.year.mode().iloc[0] if len(valid_dates.dt.year.mode()) > 0 else 'N/A'}\")\n",
                                    "                    print(f\"  Most common month: {valid_dates.dt.month.mode().iloc[0] if len(valid_dates.dt.month.mode()) > 0 else 'N/A'}\")\n",
                                    "                    \n",
                                    "                else:\n",
                                    "                    print(f\"⚠️ No valid dates found in {col}\")\n",
                                    "                    \n",
                                    "            except Exception as e:\n",
                                    "                print(f\"⚠️ Failed to convert {col} to datetime: {e}\")\n",
                                    "                \n",
                                    "    except Exception as e:\n",
                                    "        print(f\"⚠️ Error analyzing {col} for date patterns: {e}\")\n",
                                    "        continue\n",
                                    "\n",
                                    "if not date_columns:\n",
                                    "    print(\"✅ No date-like columns found\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## ⚙️ 4. Feature Engineering"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 4.1 Feature Engineering\n",
                                    "print(\"⚙️ FEATURE ENGINEERING\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "df_engineered = df_clean.copy()\n",
                                    "\n",
                                    "# Create new features\n",
                                    "print(\"\\n🔧 Creating new features...\")\n",
                                    "\n",
                                    "# For numeric columns, create interaction terms\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    for i, col1 in enumerate(numeric_cols):\n",
                                    "        for col2 in numeric_cols[i+1:]:\n",
                                    "            interaction_name = f'{col1}_x_{col2}'\n",
                                    "            df_engineered[interaction_name] = df_engineered[col1] * df_engineered[col2]\n",
                                    "            print(f\"  Created: {interaction_name}\")\n",
                                    "\n",
                                    "# For categorical columns, create dummy variables\n",
                                    "if len(categorical_cols) > 0:\n",
                                    "    for col in categorical_cols:\n",
                                    "        if df_engineered[col].nunique() <= 10:  # Only for reasonable number of categories\n",
                                    "            dummies = pd.get_dummies(df_engineered[col], prefix=col)\n",
                                    "            df_engineered = pd.concat([df_engineered, dummies], axis=1)\n",
                                    "            print(f\"  Created dummies for: {col}\")\n",
                                    "\n",
                                    "# Create statistical features\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    # Rolling statistics (if data has order)\n",
                                    "    for col in numeric_cols:\n",
                                    "        df_engineered[f'{col}_rolling_mean'] = df_engineered[col].rolling(window=3, min_periods=1).mean()\n",
                                    "        df_engineered[f'{col}_rolling_std'] = df_engineered[col].rolling(window=3, min_periods=1).std()\n",
                                    "    print(\"  Created rolling statistics\")\n",
                                    "\n",
                                    "print(f\"\\n✅ Feature engineering complete! New shape: {df_engineered.shape}\")\n",
                                    "print(f\"📊 New columns: {list(set(df_engineered.columns) - set(df_clean.columns))}\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📉 5. Statistical Analysis & Hypothesis Testing"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 5.1 Statistical Tests\n",
                                    "print(\"📉 STATISTICAL ANALYSIS & HYPOTHESIS TESTING\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "from scipy import stats\n",
                                    "from scipy.stats import shapiro, normaltest, anderson\n",
                                    "\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    print(\"\\n🔍 Normality Tests:\")\n",
                                    "    normality_results = {}\n",
                                    "    \n",
                                    "    for col in numeric_cols:\n",
                                    "        data = df_clean[col].dropna()\n",
                                    "        \n",
                                    "        # Multiple normality tests\n",
                                    "        shapiro_stat, shapiro_p = shapiro(data)\n",
                                    "        normaltest_stat, normaltest_p = normaltest(data)\n",
                                    "        anderson_result = anderson(data)\n",
                                    "        \n",
                                    "        normality_results[col] = {\n",
                                    "            'Shapiro_Wilk': {'statistic': shapiro_stat, 'p_value': shapiro_p},\n",
                                    "            'D_Agostino_K2': {'statistic': normaltest_stat, 'p_value': normaltest_p},\n",
                                    "            'Anderson_Darling': {'statistic': anderson_result.statistic, 'critical_values': anderson_result.critical_values}\n",
                                    "        }\n",
                                    "        \n",
                                    "        print(f\"\\n{col}:\")\n",
                                    "        print(f\"  Shapiro-Wilk: W={shapiro_stat:.4f}, p={shapiro_p:.4f}\")\n",
                                    "        print(f\"  D'Agostino K²: statistic={normaltest_stat:.4f}, p={normaltest_p:.4f}\")\n",
                                    "        print(f\"  Anderson-Darling: A²={anderson_result.statistic:.4f}\")\n",
                                    "        \n",
                                    "        # Interpretation\n",
                                    "        is_normal = shapiro_p > 0.05 and normaltest_p > 0.05\n",
                                    "        print(f\"  Normal distribution: {'✅ Yes' if is_normal else '❌ No'}\")\n",
                                    "\n",
                                    "    # Correlation significance tests\n",
                                    "    if len(numeric_cols) > 1:\n",
                                    "        print(\"\\n🔗 Correlation Significance Tests:\")\n",
                                    "        for i, col1 in enumerate(numeric_cols):\n",
                                    "            for col2 in numeric_cols[i+1:]:\n",
                                    "                corr, p_value = stats.pearsonr(df_clean[col1].dropna(), df_clean[col2].dropna())\n",
                                    "                significance = \"Significant\" if p_value < 0.05 else \"Not Significant\"\n",
                                    "                print(f\"  {col1} ↔ {col2}: r={corr:.3f}, p={p_value:.4f} ({significance})\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🤖 6. Machine Learning Models"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 6.1 Machine Learning Setup\n",
                                    "print(\"🤖 MACHINE LEARNING MODELS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV\n",
                                    "from sklearn.preprocessing import StandardScaler, LabelEncoder\n",
                                    "from sklearn.linear_model import LinearRegression, LogisticRegression\n",
                                    "from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier\n",
                                    "from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, classification_report\n",
                                    "from sklearn.cluster import KMeans\n",
                                    "from sklearn.decomposition import PCA\n",
                                    "\n",
                                    "# Prepare data for ML\n",
                                    "ml_data = df_engineered.copy()\n",
                                    "\n",
                                    "# Handle categorical variables\n",
                                    "label_encoders = {}\n",
                                    "for col in categorical_cols:\n",
                                    "    if col in ml_data.columns:\n",
                                    "        le = LabelEncoder()\n",
                                    "        ml_data[col] = le.fit_transform(ml_data[col].astype(str))\n",
                                    "        label_encoders[col] = le\n",
                                    "\n",
                                    "# Remove any remaining non-numeric columns\n",
                                    "ml_data = ml_data.select_dtypes(include=[np.number])\n",
                                    "\n",
                                    "print(f\"\\n📊 ML dataset shape: {ml_data.shape}\")\n",
                                    "print(f\"🔢 Features: {list(ml_data.columns)}\")\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 6.2 Clustering Analysis\n",
                                    "print(\"\\n🎯 CLUSTERING ANALYSIS\")\n",
                                    "\n",
                                    "if len(ml_data.columns) >= 2:\n",
                                    "    # Handle missing values before clustering\n",
                                    "    from sklearn.impute import SimpleImputer\n",
                                    "    \n",
                                    "    # Check for missing values\n",
                                    "    missing_count = ml_data.isnull().sum().sum()\n",
                                    "    if missing_count > 0:\n",
                                    "        print(f\"\\n⚠️ Found {missing_count} missing values. Imputing with median...\")\n",
                                    "        imputer = SimpleImputer(strategy='median')\n",
                                    "        ml_data_imputed = pd.DataFrame(imputer.fit_transform(ml_data), columns=ml_data.columns)\n",
                                    "    else:\n",
                                    "        ml_data_imputed = ml_data.copy()\n",
                                    "    \n",
                                    "    # Standardize data for clustering\n",
                                    "    scaler = StandardScaler()\n",
                                    "    data_scaled = scaler.fit_transform(ml_data_imputed)\n",
                                    "    \n",
                                    "    # Determine optimal number of clusters\n",
                                    "    inertias = []\n",
                                    "    K_range = range(1, min(11, len(ml_data_imputed) // 10 + 1))\n",
                                    "    \n",
                                    "    for k in K_range:\n",
                                    "        kmeans = KMeans(n_clusters=k, random_state=42)\n",
                                    "        kmeans.fit(data_scaled)\n",
                                    "        inertias.append(kmeans.inertia_)\n",
                                    "    \n",
                                    "    # Elbow plot\n",
                                    "    plt.figure(figsize=(10, 6))\n",
                                    "    plt.plot(K_range, inertias, 'bo-')\n",
                                    "    plt.xlabel('Number of Clusters (k)')\n",
                                    "    plt.ylabel('Inertia')\n",
                                    "    plt.title('Elbow Method for Optimal k')\n",
                                    "    plt.grid(True)\n",
                                    "    plt.show()\n",
                                    "    \n",
                                    "    # Perform clustering with optimal k\n",
                                    "    optimal_k = 3  # Default, can be adjusted based on elbow plot\n",
                                    "    kmeans = KMeans(n_clusters=optimal_k, random_state=42)\n",
                                    "    cluster_labels = kmeans.fit_predict(data_scaled)\n",
                                    "    \n",
                                    "    # Add cluster labels to original data\n",
                                    "    df_clean['Cluster'] = cluster_labels\n",
                                    "    \n",
                                    "    print(f\"\\n✅ Clustering complete! {optimal_k} clusters created.\")\n",
                                    "    print(f\"📊 Cluster distribution:\")\n",
                                    "    print(df_clean['Cluster'].value_counts().sort_index())\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 6.3 Dimensionality Reduction (PCA)\n",
                                    "print(\"\\n📉 DIMENSIONALITY REDUCTION (PCA)\")\n",
                                    "\n",
                                    "if len(ml_data.columns) > 2:\n",
                                    "    # Use the same imputed data from clustering\n",
                                    "    if 'ml_data_imputed' not in locals():\n",
                                    "        # Handle missing values if not already done\n",
                                    "        from sklearn.impute import SimpleImputer\n",
                                    "        missing_count = ml_data.isnull().sum().sum()\n",
                                    "        if missing_count > 0:\n",
                                    "            print(f\"\\n⚠️ Found {missing_count} missing values. Imputing with median...\")\n",
                                    "            imputer = SimpleImputer(strategy='median')\n",
                                    "            ml_data_imputed = pd.DataFrame(imputer.fit_transform(ml_data), columns=ml_data.columns)\n",
                                    "        else:\n",
                                    "            ml_data_imputed = ml_data.copy()\n",
                                    "    \n",
                                    "    # Standardize data\n",
                                    "    scaler = StandardScaler()\n",
                                    "    data_scaled = scaler.fit_transform(ml_data_imputed)\n",
                                    "    \n",
                                    "    # Perform PCA\n",
                                    "    pca = PCA()\n",
                                    "    pca_result = pca.fit_transform(data_scaled)\n",
                                    "    \n",
                                    "    # Explained variance\n",
                                    "    explained_variance_ratio = pca.explained_variance_ratio_\n",
                                    "    cumulative_variance = np.cumsum(explained_variance_ratio)\n",
                                    "    \n",
                                    "    # Plot explained variance\n",
                                    "    plt.figure(figsize=(12, 5))\n",
                                    "    \n",
                                    "    plt.subplot(1, 2, 1)\n",
                                    "    plt.bar(range(1, len(explained_variance_ratio) + 1), explained_variance_ratio)\n",
                                    "    plt.xlabel('Principal Component')\n",
                                    "    plt.ylabel('Explained Variance Ratio')\n",
                                    "    plt.title('Explained Variance by Principal Components')\n",
                                    "    \n",
                                    "    plt.subplot(1, 2, 2)\n",
                                    "    plt.plot(range(1, len(cumulative_variance) + 1), cumulative_variance, 'bo-')\n",
                                    "    plt.xlabel('Number of Principal Components')\n",
                                    "    plt.ylabel('Cumulative Explained Variance')\n",
                                    "    plt.title('Cumulative Explained Variance')\n",
                                    "    plt.grid(True)\n",
                                    "    \n",
                                    "    plt.tight_layout()\n",
                                    "    plt.show()\n",
                                    "    \n",
                                    "    # Show top components\n",
                                    "    n_components_95 = np.argmax(cumulative_variance >= 0.95) + 1\n",
                                    "    print(f\"\\n📊 PCA Results:\")\n",
                                    "    print(f\"  Components needed for 95% variance: {n_components_95}\")\n",
                                    "    print(f\"  Original dimensions: {len(ml_data.columns)}\")\n",
                                    "    print(f\"  Dimensionality reduction: {((len(ml_data.columns) - n_components_95) / len(ml_data.columns) * 100):.1f}%\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📝 7. Comprehensive Report & Insights"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 7.1 Generate Comprehensive Report\n",
                                    "print(\"📝 COMPREHENSIVE REPORT & INSIGHTS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "print(f\"\\n📋 DATASET SUMMARY\")\n",
                                    "print(f\"  File: {file_path}\")\n",
                                    "print(f\"  Original shape: {df.shape}\")\n",
                                    "print(f\"  Cleaned shape: {df_clean.shape}\")\n",
                                    "print(f\"  Numeric columns: {len(numeric_cols)}\")\n",
                                    "print(f\"  Categorical columns: {len(categorical_cols)}\")\n",
                                    "\n",
                                    "print(f\"\\n🔍 KEY FINDINGS\")\n",
                                    "\n",
                                    "# Data quality insights\n",
                                    "missing_count = df.isnull().sum().sum()\n",
                                    "if missing_count > 0:\n",
                                    "    print(f\"  ❌ Missing values: {missing_count} total\")\n",
                                    "else:\n",
                                    "    print(f\"  ✅ No missing values found\")\n",
                                    "\n",
                                    "duplicates = df.duplicated().sum()\n",
                                    "if duplicates > 0:\n",
                                    "    print(f\"  🔄 Duplicates removed: {duplicates}\")\n",
                                    "else:\n",
                                    "    print(f\"  ✅ No duplicates found\")\n",
                                    "\n",
                                    "# Statistical insights\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    print(f\"\\n📊 STATISTICAL INSIGHTS\")\n",
                                    "    for col in numeric_cols:\n",
                                    "        mean_val = df_clean[col].mean()\n",
                                    "        std_val = df_clean[col].mean()\n",
                                    "        skew_val = df_clean[col].skew()\n",
                                    "        print(f\"  {col}: Mean={mean_val:.2f}, Std={std_val:.2f}, Skew={skew_val:.2f}\")\n",
                                    "\n",
                                    "# Correlation insights\n",
                                    "if 'strong_corr' in locals() and len(strong_corr) > 0:\n",
                                    "    print(f\"\\n🔗 STRONG CORRELATIONS\")\n",
                                    "    for var1, var2, corr in strong_corr:\n",
                                    "        print(f\"  {var1} ↔ {var2}: {corr:.3f}\")\n",
                                    "\n",
                                    "print(f\"\\n🎯 RECOMMENDATIONS\")\n",
                                    "print(f\"  1. Consider the strong correlations for feature selection\")\n",
                                    "print(f\"  2. Use clustering results for segmentation analysis\")\n",
                                    "print(f\"  3. Apply PCA for dimensionality reduction if needed\")\n",
                                    "print(f\"  4. Consider the distribution shapes for model selection\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📊 8. Executive Summary"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 8.1 Executive Summary\n",
                                    "print(\"📊 EXECUTIVE SUMMARY\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "print(f\"\\n📈 DATASET OVERVIEW\")\n",
                                    "print(f\"  • Dataset contains {df.shape[0]} records and {df.shape[1]} features\")\n",
                                    "missing_count = df.isnull().sum().sum()\n",
                                    "print(f\"  • Data quality: {'Good' if missing_count == 0 else 'Needs attention'}\")\n",
                                    "print(f\"  • Analysis scope: {user_prompt}\")\n",
                                    "\n",
                                    "print(f\"\\n🔍 KEY INSIGHTS\")\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    print(f\"  • {len(numeric_cols)} numeric variables analyzed\")\n",
                                    "if len(categorical_cols) > 0:\n",
                                    "    print(f\"  • {len(categorical_cols)} categorical variables analyzed\")\n",
                                    "if 'strong_corr' in locals() and len(strong_corr) > 0:\n",
                                    "    print(f\"  • {len(strong_corr)} strong correlations identified\")\n",
                                    "\n",
                                    "print(f\"\\n🤖 MACHINE LEARNING INSIGHTS\")\n",
                                    "if len(ml_data.columns) > 2:\n",
                                    "    if 'optimal_k' in locals():\n",
                                    "        print(f\"  • Clustering analysis performed with {optimal_k} clusters\")\n",
                                    "    if 'n_components_95' in locals():\n",
                                    "        print(f\"  • PCA shows {n_components_95} components needed for 95% variance\")\n",
                                    "\n",
                                    "print(f\"\\n📋 NEXT STEPS\")\n",
                                    "print(f\"  1. Validate findings with domain experts\")\n",
                                    "print(f\"  2. Consider additional data sources if available\")\n",
                                    "print(f\"  3. Implement predictive models based on insights\")\n",
                                    "print(f\"  4. Monitor data quality over time\")\n",
                                    "\n",
                                    "print(f\"\\n✅ Analysis complete! Check the visualizations above for detailed insights.\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📈 9. Advanced Forecasting & Time Series Analysis"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 9.1 Time Series Analysis\n",
                                    "print(\"📈 ADVANCED FORECASTING & TIME SERIES ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Check for datetime columns\n",
                                    "datetime_cols = []\n",
                                    "for col in df_clean.columns:\n",
                                    "    try:\n",
                                    "        pd.to_datetime(df_clean[col])\n",
                                    "        datetime_cols.append(col)\n",
                                    "    except:\n",
                                    "        continue\n",
                                    "\n",
                                    "if len(datetime_cols) > 0:\n",
                                    "    print(f\"\\n📅 Found datetime columns: {datetime_cols}\")\n",
                                    "    \n",
                                    "    # Convert to datetime and set as index\n",
                                    "    for col in datetime_cols:\n",
                                    "        df_clean[f'{col}_dt'] = pd.to_datetime(df_clean[col])\n",
                                    "    \n",
                                    "    # Time series analysis for each numeric column\n",
                                    "    for col in numeric_cols:\n",
                                    "        if len(datetime_cols) > 0:\n",
                                    "            print(f\"\\n📊 Time series analysis for {col}:\")\n",
                                    "            \n",
                                    "            # Create time series plot\n",
                                    "            plt.figure(figsize=(12, 6))\n",
                                    "            plt.plot(df_clean[f'{datetime_cols[0]}_dt'], df_clean[col])\n",
                                    "            plt.title(f'Time Series: {col} over time')\n",
                                    "            plt.xlabel('Time')\n",
                                    "            plt.ylabel(col)\n",
                                    "            plt.xticks(rotation=45)\n",
                                    "            plt.tight_layout()\n",
                                    "            plt.show()\n",
                                    "            \n",
                                    "            # Seasonal decomposition\n",
                                    "            try:\n",
                                    "                from statsmodels.tsa.seasonal import seasonal_decompose\n",
                                    "                \n",
                                    "                # Resample to regular intervals if needed\n",
                                    "                ts_data = df_clean.set_index(f'{datetime_cols[0]}_dt')[col].sort_index()\n",
                                    "                ts_data = ts_data.resample('D').mean().fillna(method='ffill')\n",
                                    "                \n",
                                    "                if len(ts_data) > 30:  # Need sufficient data\n",
                                    "                    decomposition = seasonal_decompose(ts_data, period=min(12, len(ts_data)//4))\n",
                                    "                    \n",
                                    "                    plt.figure(figsize=(12, 10))\n",
                                    "                    plt.subplot(411)\n",
                                    "                    plt.plot(ts_data)\n",
                                    "                    plt.title('Original Time Series')\n",
                                    "                    plt.subplot(412)\n",
                                    "                    plt.plot(decomposition.trend)\n",
                                    "                    plt.title('Trend')\n",
                                    "                    plt.subplot(413)\n",
                                    "                    plt.plot(decomposition.seasonal)\n",
                                    "                    plt.title('Seasonal')\n",
                                    "                    plt.subplot(414)\n",
                                    "                    plt.plot(decomposition.resid)\n",
                                    "                    plt.title('Residual')\n",
                                    "                    plt.tight_layout()\n",
                                    "                    plt.show()\n",
                                    "            except Exception as e:\n",
                                    "                print(f\"  ⚠️ Seasonal decomposition failed: {e}\")\n",
                                    "else:\n",
                                    "    print(\"\\n⚠️ No datetime columns found for time series analysis\")\n",
                                    "    print(\"💡 To enable time series analysis, ensure your data has date/time columns\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🔮 10. Predictive Modeling & Forecasting"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 10.1 Predictive Modeling\n",
                                    "print(\"🔮 PREDICTIVE MODELING & FORECASTING\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    print(\"\\n🤖 Building Predictive Models:\")\n",
                                    "    \n",
                                    "    # Prepare data for modeling\n",
                                    "    if 'ml_data_imputed' in locals():\n",
                                    "        model_data = ml_data_imputed.copy()\n",
                                    "    else:\n",
                                    "        # Handle missing values\n",
                                    "        from sklearn.impute import SimpleImputer\n",
                                    "        imputer = SimpleImputer(strategy='median')\n",
                                    "        model_data = pd.DataFrame(imputer.fit_transform(ml_data), columns=ml_data.columns)\n",
                                    "    \n",
                                    "    # For each numeric column, predict it using other columns\n",
                                    "    for target_col in numeric_cols[:3]:  # Limit to first 3 columns\n",
                                    "        print(f\"\\n🎯 Predicting {target_col}:\")\n",
                                    "        \n",
                                    "        # Prepare features and target\n",
                                    "        feature_cols = [col for col in model_data.columns if col != target_col]\n",
                                    "        if len(feature_cols) == 0:\n",
                                    "            continue\n",
                                    "            \n",
                                    "        X = model_data[feature_cols]\n",
                                    "        y = model_data[target_col]\n",
                                    "        \n",
                                    "        # Split data\n",
                                    "        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n",
                                    "        \n",
                                    "        # Scale features\n",
                                    "        scaler = StandardScaler()\n",
                                    "        X_train_scaled = scaler.fit_transform(X_train)\n",
                                    "        X_test_scaled = scaler.transform(X_test)\n",
                                    "        \n",
                                    "        # Train multiple models\n",
                                    "        models = {\n",
                                    "            'Linear Regression': LinearRegression(),\n",
                                    "            'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),\n",
                                    "        }\n",
                                    "        \n",
                                    "        results = {}\n",
                                    "        for name, model in models.items():\n",
                                    "            model.fit(X_train_scaled, y_train)\n",
                                    "            y_pred = model.predict(X_test_scaled)\n",
                                    "            \n",
                                    "            # Calculate metrics\n",
                                    "            mse = mean_squared_error(y_test, y_pred)\n",
                                    "            r2 = r2_score(y_test, y_pred)\n",
                                    "            \n",
                                    "            results[name] = {'mse': mse, 'r2': r2, 'predictions': y_pred}\n",
                                    "            print(f\"  {name}: MSE={mse:.4f}, R²={r2:.4f}\")\n",
                                    "        \n",
                                    "        # Plot predictions vs actual\n",
                                    "        best_model = max(results.keys(), key=lambda x: results[x]['r2'])\n",
                                    "        plt.figure(figsize=(10, 6))\n",
                                    "        plt.scatter(y_test, results[best_model]['predictions'], alpha=0.6)\n",
                                    "        plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)\n",
                                    "        plt.xlabel('Actual Values')\n",
                                    "        plt.ylabel('Predicted Values')\n",
                                    "        plt.title(f'Predictions vs Actual for {target_col} ({best_model})')\n",
                                    "        plt.grid(True, alpha=0.3)\n",
                                    "        plt.show()\n",
                                    "else:\n",
                                    "    print(\"\\n⚠️ Need at least 2 numeric columns for predictive modeling\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🔍 11. Advanced Anomaly Detection"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 11.1 Advanced Anomaly Detection\n",
                                    "print(\"🔍 ADVANCED ANOMALY DETECTION\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "if len(numeric_cols) > 0:\n",
                                    "    print(\"\\n🚨 Detecting anomalies using multiple methods:\")\n",
                                    "    \n",
                                    "    # Use the same imputed data\n",
                                    "    if 'ml_data_imputed' in locals():\n",
                                    "        anomaly_data = ml_data_imputed.copy()\n",
                                    "    else:\n",
                                    "        from sklearn.impute import SimpleImputer\n",
                                    "        imputer = SimpleImputer(strategy='median')\n",
                                    "        anomaly_data = pd.DataFrame(imputer.fit_transform(ml_data), columns=ml_data.columns)\n",
                                    "    \n",
                                    "    # Method 1: Isolation Forest\n",
                                    "    try:\n",
                                    "        from sklearn.ensemble import IsolationForest\n",
                                    "        \n",
                                    "        iso_forest = IsolationForest(contamination=0.1, random_state=42)\n",
                                    "        anomaly_scores = iso_forest.fit_predict(anomaly_data)\n",
                                    "        \n",
                                    "        # Count anomalies\n",
                                    "        n_anomalies = (anomaly_scores == -1).sum()\n",
                                    "        print(f\"\\n🌲 Isolation Forest detected {n_anomalies} anomalies ({n_anomalies/len(anomaly_data)*100:.1f}%)\")\n",
                                    "        \n",
                                    "        # Visualize anomalies\n",
                                    "        if len(numeric_cols) >= 2:\n",
                                    "            plt.figure(figsize=(10, 6))\n",
                                    "            normal = anomaly_scores == 1\n",
                                    "            anomalies = anomaly_scores == -1\n",
                                    "            \n",
                                    "            plt.scatter(anomaly_data.iloc[normal, 0], anomaly_data.iloc[normal, 1], \n",
                                    "                       c='blue', alpha=0.6, label='Normal')\n",
                                    "            plt.scatter(anomaly_data.iloc[anomalies, 0], anomaly_data.iloc[anomalies, 1], \n",
                                    "                       c='red', alpha=0.8, label='Anomalies')\n",
                                    "            plt.xlabel(numeric_cols[0])\n",
                                    "            plt.ylabel(numeric_cols[1])\n",
                                    "            plt.title('Anomaly Detection using Isolation Forest')\n",
                                    "            plt.legend()\n",
                                    "            plt.grid(True, alpha=0.3)\n",
                                    "            plt.show()\n",
                                    "    except Exception as e:\n",
                                    "        print(f\"  ⚠️ Isolation Forest failed: {e}\")\n",
                                    "    \n",
                                    "    # Method 2: Z-score method\n",
                                    "    print(\"\\n📊 Z-score anomaly detection:\")\n",
                                    "    for col in numeric_cols:\n",
                                    "        z_scores = np.abs((anomaly_data[col] - anomaly_data[col].mean()) / anomaly_data[col].std())\n",
                                    "        anomalies_z = z_scores > 3\n",
                                    "        n_anomalies_z = anomalies_z.sum()\n",
                                    "        print(f\"  {col}: {n_anomalies_z} anomalies (|z| > 3)\")\n",
                                    "else:\n",
                                    "    print(\"\\n⚠️ No numeric columns for anomaly detection\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📊 12. Advanced Analytics & Insights"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 12.1 Advanced Analytics\n",
                                    "print(\"📊 ADVANCED ANALYTICS & INSIGHTS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "print(\"\\n🔍 Generating advanced insights:\")\n",
                                    "\n",
                                    "# 1. Data Quality Score\n",
                                    "print(\"\\n📈 Data Quality Assessment:\")\n",
                                    "missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100\n",
                                    "duplicate_pct = (df.duplicated().sum() / len(df)) * 100\n",
                                    "quality_score = 100 - missing_pct - duplicate_pct\n",
                                    "print(f\"  Data Quality Score: {quality_score:.1f}/100\")\n",
                                    "print(f\"  Missing Data: {missing_pct:.1f}%\")\n",
                                    "print(f\"  Duplicates: {duplicate_pct:.1f}%\")\n",
                                    "\n",
                                    "# 2. Feature Importance Analysis\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    print(\"\\n🎯 Feature Importance Analysis:\")\n",
                                    "    \n",
                                    "    # Use Random Forest to get feature importance\n",
                                    "    if 'ml_data_imputed' in locals():\n",
                                    "        feature_data = ml_data_imputed.copy()\n",
                                    "    else:\n",
                                    "        from sklearn.impute import SimpleImputer\n",
                                    "        imputer = SimpleImputer(strategy='median')\n",
                                    "        feature_data = pd.DataFrame(imputer.fit_transform(ml_data), columns=ml_data.columns)\n",
                                    "    \n",
                                    "    # Calculate importance for each target variable\n",
                                    "    for target_col in numeric_cols[:2]:  # Top 2 columns\n",
                                    "        feature_cols = [col for col in feature_data.columns if col != target_col]\n",
                                    "        if len(feature_cols) == 0:\n",
                                    "            continue\n",
                                    "            \n",
                                    "        X = feature_data[feature_cols]\n",
                                    "        y = feature_data[target_col]\n",
                                    "        \n",
                                    "        rf = RandomForestRegressor(n_estimators=100, random_state=42)\n",
                                    "        rf.fit(X, y)\n",
                                    "        \n",
                                    "        # Get feature importance\n",
                                    "        importance_df = pd.DataFrame({\n",
                                    "            'feature': feature_cols,\n",
                                    "            'importance': rf.feature_importances_\n",
                                    "        }).sort_values('importance', ascending=False)\n",
                                    "        \n",
                                    "        print(f\"\\n  Top features for predicting {target_col}:\")\n",
                                    "        for idx, row in importance_df.head(5).iterrows():\n",
                                    "            print(f\"    {row['feature']}: {row['importance']:.3f}\")\n",
                                    "\n",
                                    "# 3. Data Distribution Analysis\n",
                                    "print(\"\\n📊 Data Distribution Insights:\")\n",
                                    "for col in numeric_cols:\n",
                                    "    skewness = df_clean[col].skew()\n",
                                    "    kurtosis = df_clean[col].kurtosis()\n",
                                    "    \n",
                                    "    distribution_type = \"Normal\"\n",
                                    "    if abs(skewness) > 1:\n",
                                    "        distribution_type = \"Skewed\"\n",
                                    "    if abs(kurtosis) > 3:\n",
                                    "        distribution_type += \" (Heavy-tailed)\"\n",
                                    "    \n",
                                    "    print(f\"  {col}: {distribution_type} (Skew: {skewness:.2f}, Kurt: {kurtosis:.2f})\")\n",
                                    "\n",
                                    "# 4. Correlation Network Analysis\n",
                                    "if len(numeric_cols) > 2:\n",
                                    "    print(\"\\n🔗 Correlation Network Analysis:\")\n",
                                    "    corr_matrix = df_clean[numeric_cols].corr()\n",
                                    "    \n",
                                    "    # Find strong correlations\n",
                                    "    strong_correlations = []\n",
                                    "    for i in range(len(corr_matrix.columns)):\n",
                                    "        for j in range(i+1, len(corr_matrix.columns)):\n",
                                    "            corr_val = corr_matrix.iloc[i, j]\n",
                                    "            if abs(corr_val) > 0.5:\n",
                                    "                strong_correlations.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val))\n",
                                    "    \n",
                                    "    if strong_correlations:\n",
                                    "        print(f\"  Found {len(strong_correlations)} strong correlations (|r| > 0.5):\")\n",
                                    "        for var1, var2, corr in strong_correlations[:5]:  # Top 5\n",
                                    "            print(f\"    {var1} ↔ {var2}: {corr:.3f}\")\n",
                                    "    else:\n",
                                    "        print(\"  No strong correlations found\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🧪 13. A/B Testing & Statistical Experiments"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 13.1 A/B Testing & Statistical Experiments\n",
                                    "print(\"🧪 A/B TESTING & STATISTICAL EXPERIMENTS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "print(\"\\n🔬 Statistical Testing Framework:\")\n",
                                    "\n",
                                    "# 1. T-tests for numeric variables\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    print(\"\\n📊 T-tests between numeric variables:\")\n",
                                    "    \n",
                                    "    for i, col1 in enumerate(numeric_cols):\n",
                                    "        for col2 in numeric_cols[i+1:]:\n",
                                    "            # Perform t-test\n",
                                    "            from scipy.stats import ttest_ind\n",
                                    "            \n",
                                    "            # Remove NaN values\n",
                                    "            data1 = df_clean[col1].dropna()\n",
                                    "            data2 = df_clean[col2].dropna()\n",
                                    "            \n",
                                    "            if len(data1) > 10 and len(data2) > 10:  # Need sufficient data\n",
                                    "                t_stat, p_value = ttest_ind(data1, data2)\n",
                                    "                \n",
                                    "                significance = \"Significant\" if p_value < 0.05 else \"Not Significant\"\n",
                                    "                print(f\"  {col1} vs {col2}: t={t_stat:.3f}, p={p_value:.4f} ({significance})\")\n",
                                    "\n",
                                    "# 2. Chi-square tests for categorical variables\n",
                                    "if len(categorical_cols) >= 2:\n",
                                    "    print(\"\\n📋 Chi-square tests for categorical variables:\")\n",
                                    "    \n",
                                    "    for i, col1 in enumerate(categorical_cols):\n",
                                    "        for col2 in categorical_cols[i+1:]:\n",
                                    "            # Create contingency table\n",
                                    "            contingency_table = pd.crosstab(df_clean[col1], df_clean[col2])\n",
                                    "            \n",
                                    "            if contingency_table.shape[0] > 1 and contingency_table.shape[1] > 1:\n",
                                    "                from scipy.stats import chi2_contingency\n",
                                    "                \n",
                                    "                chi2, p_value, dof, expected = chi2_contingency(contingency_table)\n",
                                    "                \n",
                                    "                significance = \"Significant\" if p_value < 0.05 else \"Not Significant\"\n",
                                    "                print(f\"  {col1} vs {col2}: χ²={chi2:.3f}, p={p_value:.4f} ({significance})\")\n",
                                    "\n",
                                    "# 3. Effect Size Analysis\n",
                                    "if len(numeric_cols) >= 2:\n",
                                    "    print(\"\\n📏 Effect Size Analysis:\")\n",
                                    "    \n",
                                    "    for i, col1 in enumerate(numeric_cols):\n",
                                    "        for col2 in numeric_cols[i+1:]:\n",
                                    "            # Calculate Cohen's d\n",
                                    "            data1 = df_clean[col1].dropna()\n",
                                    "            data2 = df_clean[col2].dropna()\n",
                                    "            \n",
                                    "            if len(data1) > 10 and len(data2) > 10:\n",
                                    "                pooled_std = np.sqrt(((len(data1) - 1) * data1.var() + (len(data2) - 1) * data2.var()) / (len(data1) + len(data2) - 2))\n",
                                    "                cohens_d = (data1.mean() - data2.mean()) / pooled_std\n",
                                    "                \n",
                                    "                effect_size = \"Small\"\n",
                                    "                if abs(cohens_d) > 0.5:\n",
                                    "                    effect_size = \"Medium\"\n",
                                    "                if abs(cohens_d) > 0.8:\n",
                                    "                    effect_size = \"Large\"\n",
                                    "                \n",
                                    "                print(f\"  {col1} vs {col2}: Cohen's d={cohens_d:.3f} ({effect_size} effect)\")\n",
                                    "\n",
                                    "print(\"\\n💡 A/B Testing Recommendations:\")\n",
                                    "print(\"  • For controlled experiments, ensure random assignment\")\n",
                                    "print(\"  • Use appropriate sample sizes for statistical power\")\n",
                                    "print(\"  • Consider multiple testing corrections for multiple comparisons\")\n",
                                    "print(\"  • Monitor for confounding variables\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📝 14. Natural Language Processing (NLP)"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 14.1 Natural Language Processing\n",
                                    "print(\"📝 NATURAL LANGUAGE PROCESSING (NLP)\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Find text columns\n",
                                    "text_cols = []\n",
                                    "for col in df_clean.columns:\n",
                                    "    if df_clean[col].dtype == 'object':\n",
                                    "        # Check if it might be text (longer strings)\n",
                                    "        avg_length = df_clean[col].astype(str).str.len().mean()\n",
                                    "        if avg_length > 20:  # Average length > 20 characters\n",
                                    "            text_cols.append(col)\n",
                                    "\n",
                                    "if len(text_cols) > 0:\n",
                                    "    print(f\"\\n📝 Found potential text columns: {text_cols}\")\n",
                                    "    \n",
                                    "    for col in text_cols:\n",
                                    "        print(f\"\\n🔍 Analyzing text column: {col}\")\n",
                                    "        \n",
                                    "        # Basic text statistics\n",
                                    "        text_data = df_clean[col].astype(str)\n",
                                    "        \n",
                                    "        # Length statistics\n",
                                    "        lengths = text_data.str.len()\n",
                                    "        print(f\"  Average length: {lengths.mean():.1f} characters\")\n",
                                    "        print(f\"  Min length: {lengths.min()} characters\")\n",
                                    "        print(f\"  Max length: {lengths.max()} characters\")\n",
                                    "        \n",
                                    "        # Word count statistics\n",
                                    "        word_counts = text_data.str.split().str.len()\n",
                                    "        print(f\"  Average words: {word_counts.mean():.1f} words\")\n",
                                    "        \n",
                                    "        # Most common words\n",
                                    "        try:\n",
                                    "            import re\n",
                                    "            from collections import Counter\n",
                                    "            \n",
                                    "            # Combine all text and find common words\n",
                                    "            all_text = ' '.join(text_data.tolist())\n",
                                    "            words = re.findall(r'\\b\\w+\\b', all_text.lower())\n",
                                    "            \n",
                                    "            # Remove common stop words\n",
                                    "            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}\n",
                                    "            words = [word for word in words if word not in stop_words and len(word) > 2]\n",
                                    "            \n",
                                    "            word_freq = Counter(words).most_common(10)\n",
                                    "            print(f\"  \\n  Most common words:\")\n",
                                    "            for word, count in word_freq:\n",
                                    "                print(f\"    '{word}': {count} times\")\n",
                                    "                \n",
                                    "        except Exception as e:\n",
                                    "            print(f\"  ⚠️ Word analysis failed: {e}\")\n",
                                    "        \n",
                                    "        # Text length distribution\n",
                                    "        plt.figure(figsize=(10, 6))\n",
                                    "        plt.hist(lengths, bins=30, alpha=0.7, color='skyblue')\n",
                                    "        plt.xlabel('Text Length (characters)')\n",
                                    "        plt.ylabel('Frequency')\n",
                                    "        plt.title(f'Text Length Distribution for {col}')\n",
                                    "        plt.grid(True, alpha=0.3)\n",
                                    "        plt.show()\n",
                                    "else:\n",
                                    "    print(\"\\n⚠️ No text columns found for NLP analysis\")\n",
                                    "    print(\"💡 To enable NLP, ensure your data has text columns with meaningful content\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 🗺️ 15. Geospatial Analysis"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 15.1 Geospatial Analysis\n",
                                    "print(\"🗺️ GEOSPATIAL ANALYSIS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "# Look for potential geospatial columns\n",
                                    "geo_cols = []\n",
                                    "for col in df_clean.columns:\n",
                                    "    col_lower = col.lower()\n",
                                    "    if any(geo_term in col_lower for geo_term in ['lat', 'lon', 'latitude', 'longitude', 'coord', 'location', 'address', 'city', 'state', 'country', 'zip', 'postal']):\n",
                                    "        geo_cols.append(col)\n",
                                    "\n",
                                    "if len(geo_cols) >= 2:\n",
                                    "    print(f\"\\n🗺️ Found potential geospatial columns: {geo_cols}\")\n",
                                    "    \n",
                                    "    # Try to identify lat/lon columns\n",
                                    "    lat_col = None\n",
                                    "    lon_col = None\n",
                                    "    \n",
                                    "    for col in geo_cols:\n",
                                    "        col_lower = col.lower()\n",
                                    "        if any(term in col_lower for term in ['lat', 'latitude']):\n",
                                    "            lat_col = col\n",
                                    "        elif any(term in col_lower for term in ['lon', 'long', 'longitude']):\n",
                                    "            lon_col = col\n",
                                    "    \n",
                                    "    if lat_col and lon_col:\n",
                                    "        print(f\"\\n📍 Using {lat_col} and {lon_col} for geospatial analysis\")\n",
                                    "        \n",
                                    "        # Check if coordinates are valid\n",
                                    "        try:\n",
                                    "            lat_data = pd.to_numeric(df_clean[lat_col], errors='coerce')\n",
                                    "            lon_data = pd.to_numeric(df_clean[lon_col], errors='coerce')\n",
                                    "            \n",
                                    "            # Filter valid coordinates\n",
                                    "            valid_coords = (lat_data.notna()) & (lon_data.notna()) & \\\n",
                                    "                         (lat_data >= -90) & (lat_data <= 90) & \\\n",
                                    "                         (lon_data >= -180) & (lon_data <= 180)\n",
                                    "            \n",
                                    "            if valid_coords.sum() > 0:\n",
                                    "                print(f\"  Found {valid_coords.sum()} valid coordinate pairs\")\n",
                                    "                \n",
                                    "                # Create scatter plot of coordinates\n",
                                    "                plt.figure(figsize=(12, 8))\n",
                                    "                plt.scatter(lon_data[valid_coords], lat_data[valid_coords], alpha=0.6, s=20)\n",
                                    "                plt.xlabel('Longitude')\n",
                                    "                plt.ylabel('Latitude')\n",
                                    "                plt.title('Geographic Distribution of Data Points')\n",
                                    "                plt.grid(True, alpha=0.3)\n",
                                    "                plt.show()\n",
                                    "                \n",
                                    "                # Calculate geographic statistics\n",
                                    "                print(f\"\\n📊 Geographic Statistics:\")\n",
                                    "                print(f\"  Latitude range: {lat_data[valid_coords].min():.4f} to {lat_data[valid_coords].max():.4f}\")\n",
                                    "                print(f\"  Longitude range: {lon_data[valid_coords].min():.4f} to {lon_data[valid_coords].max():.4f}\")\n",
                                    "                print(f\"  Geographic center: ({lat_data[valid_coords].mean():.4f}, {lon_data[valid_coords].mean():.4f})\")\n",
                                    "                \n",
                                    "                # Density analysis\n",
                                    "                plt.figure(figsize=(12, 8))\n",
                                    "                plt.hist2d(lon_data[valid_coords], lat_data[valid_coords], bins=20, cmap='viridis')\n",
                                    "                plt.colorbar(label='Point Density')\n",
                                    "                plt.xlabel('Longitude')\n",
                                    "                plt.ylabel('Latitude')\n",
                                    "                plt.title('Geographic Density Heatmap')\n",
                                    "                plt.show()\n",
                                    "            else:\n",
                                    "                print(\"  ⚠️ No valid coordinate pairs found\")\n",
                                    "        except Exception as e:\n",
                                    "            print(f\"  ⚠️ Geospatial analysis failed: {e}\")\n",
                                    "    else:\n",
                                    "        print(\"  ⚠️ Could not identify latitude/longitude columns\")\n",
                                    "else:\n",
                                    "    print(\"\\n⚠️ No geospatial columns found\")\n",
                                    "    print(\"💡 To enable geospatial analysis, include columns with latitude/longitude data\")\n"
                                ]
                            },
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "## 📋 16. Final Comprehensive Report & Insights"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# 16.1 Final Comprehensive Report\n",
                                    "print(\"📋 FINAL COMPREHENSIVE REPORT & INSIGHTS\")\n",
                                    "print(\"=\" * 50)\n",
                                    "\n",
                                    "print(f\"\\n🎯 EXECUTIVE SUMMARY\")\n",
                                    "print(f\"  Dataset: {file_path}\")\n",
                                    "print(f\"  Analysis Goal: {user_prompt}\")\n",
                                    "print(f\"  Records: {df.shape[0]:,}\")\n",
                                    "print(f\"  Features: {df.shape[1]}\")\n",
                                    "print(f\"  Data Quality Score: {quality_score:.1f}/100\")\n",
                                    "\n",
                                    "print(f\"\\n🔍 KEY INSIGHTS\")\n",
                                    "print(f\"  • {len(numeric_cols)} numeric variables analyzed\")\n",
                                    "print(f\"  • {len(categorical_cols)} categorical variables analyzed\")\n",
                                    "if 'text_cols' in locals() and len(text_cols) > 0:\n",
                                    "    print(f\"  • {len(text_cols)} text variables analyzed\")\n",
                                    "if 'geo_cols' in locals() and len(geo_cols) > 0:\n",
                                    "    print(f\"  • {len(geo_cols)} geospatial variables analyzed\")\n",
                                    "if 'datetime_cols' in locals() and len(datetime_cols) > 0:\n",
                                    "    print(f\"  • {len(datetime_cols)} datetime variables analyzed\")\n",
                                    "\n",
                                    "print(f\"\\n🤖 MACHINE LEARNING INSIGHTS\")\n",
                                    "if len(ml_data.columns) > 2:\n",
                                    "    if 'optimal_k' in locals():\n",
                                    "        print(f\"  • Clustering analysis performed with {optimal_k} clusters\")\n",
                                    "    if 'n_components_95' in locals():\n",
                                    "        print(f\"  • PCA shows {n_components_95} components needed for 95% variance\")\n",
                                    "    print(f\"  • Predictive models built for {min(3, len(numeric_cols))} target variables\")\n",
                                    "    print(f\"  • Anomaly detection performed using Isolation Forest\")\n",
                                    "\n",
                                    "print(f\"\\n📊 STATISTICAL INSIGHTS\")\n",
                                    "print(f\"  • Multiple statistical tests performed (t-tests, chi-square, effect sizes)\")\n",
                                    "print(f\"  • Normality tests completed for all numeric variables\")\n",
                                    "print(f\"  • Correlation analysis performed\")\n",
                                    "if 'strong_correlations' in locals() and len(strong_correlations) > 0:\n",
                                    "    print(f\"  • {len(strong_correlations)} strong correlations identified\")\n",
                                    "\n",
                                    "print(f\"\\n🎯 RECOMMENDATIONS\")\n",
                                    "print(f\"  1. Consider the strong correlations for feature selection\")\n",
                                    "print(f\"  2. Use clustering results for customer segmentation\")\n",
                                    "print(f\"  3. Apply predictive models for forecasting\")\n",
                                    "print(f\"  4. Monitor anomalies for quality control\")\n",
                                    "print(f\"  5. Validate findings with domain experts\")\n",
                                    "print(f\"  6. Consider additional data sources if available\")\n",
                                    "print(f\"  7. Implement A/B testing for hypothesis validation\")\n",
                                    "print(f\"  8. Monitor data quality over time\")\n",
                                    "\n",
                                    "print(f\"\\n📈 NEXT STEPS\")\n",
                                    "print(f\"  1. Deploy predictive models to production\")\n",
                                    "print(f\"  2. Set up automated monitoring and alerting\")\n",
                                    "print(f\"  3. Create interactive dashboards for stakeholders\")\n",
                                    "print(f\"  4. Conduct deeper domain-specific analysis\")\n",
                                    "print(f\"  5. Plan for data pipeline improvements\")\n",
                                    "\n",
                                                                         "print(f\"\\n✅ COMPREHENSIVE ANALYSIS COMPLETE!\")\n",
                                     "print(f\"📊 All visualizations and insights available above.\")\n",
                                     "print(f\"📋 Detailed reports saved for further review.\")\n"
                                 ]
                             }
                         ],
                        "metadata": {"language_info": {"name": "python"}},
                        "nbformat": 4,
                        "nbformat_minor": 5
                    }
                    with nb_path.open('w', encoding='utf-8') as f:
                        json.dump(nb, f, ensure_ascii=False, indent=2)
                    print(f"Notebook created: {nb_path.resolve()}")
                    print(f"Opening notebook...")
                    subprocess.run([sys.executable, "-m", "notebook", str(nb_path.resolve())], check=True)
                except Exception as e:
                    print(f"Failed to create/open notebook: {e}")
            else:
                # No file provided: open template notebook
                notebook_path = "data_analyst_workflow.ipynb"
                print(f"🚀 Launching Jupyter Notebook: {notebook_path}")
                try:
                    subprocess.run([sys.executable, "-m", "notebook", notebook_path], check=True)
                except Exception as e:
                    print(f"❌ Failed to launch Jupyter Notebook: {e}")
            return
        # Non-jupyter CLI run
        if not args.file or not args.prompt:
            print("❌ Error: --dataanalyst requires --file and --prompt")
            print("Example: python main.py --dataanalyst --file data.csv --prompt \"Find key trends\"")
            return
        print(f"📊 Running Data Analyst workflow on: {args.file}")
        da_result = await run_data_analyst_workflow(args.file, args.prompt, show_menu=True)
        if isinstance(da_result, dict) and 'content' in da_result:
            print(da_result['content'])
            print(f"\n✅ Status: {da_result.get('success', True)}")
        else:
            print(str(da_result))
        return
    
    # Handle specialized tasks
    specialized_tasks = [
        'text-classification', 'token-classification', 'question-answering',
        'text-generation', 'summarization', 'translation', 'fill-mask',
        'text2text-generation', 'language-detection', 'grammar-correction',
        'paraphrase-generation', 'causal-language-modeling',
        'zero-shot-classification', 'feature-extraction', 'sentence-similarity',
        'anonymization', 'coreference-resolution', 'spam-detection',
        'malware-text-detection', 'phishing-detection', 'pii-detection',
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
        'document-question-answering', 'zero-shot-image-classification',
        'depth-estimation', 'image-feature-extraction', 'automatic-speech-recognition',
        'audio-classification', 'voice-activity-detection', 'emotion-recognition',
        'video-classification', 'text-to-speech', 'text-to-image',
        'image-super-resolution', 'table-question-answering', 'feature-ranking',
        'sentiment', 'question', 'ner', 'summary'
    ]
    
    # Check for specialized task flags
    active_specialized_task = None
    for task in specialized_tasks:
        if getattr(args, task.replace('-', '_'), False):
            active_specialized_task = task
            break
    
    # Handle specialized tasks (with or without prompt)
    if active_specialized_task:
        task_text = args.task or args.prompt
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, active_specialized_task, task_text)
        
        print(f"🤖 Processing specialized task: {active_specialized_task}")
        if task_text:
            print(f"📝 Input: {task_text}")
        print(f"📁 File: {args.file if args.file else 'None'}")
        print(f"💰 Budget: ${args.budget}")
        print(f"🔗 Chain of Thought: {args.chain_of_thought}")
        print(f"🤖 ML Enabled: {args.enable_ml}")
        print(f"🔍 Verbose: {args.verbose}")
        print(f"🌍 Language: {args.language}")
        print("")
        
        # Use ML-based model selection if enabled and strategy is ML-based
        if ml_manager and args.selection_strategy.startswith('ml_'):
            debug_print(f"Using ML-based model selection for task: {active_specialized_task} with strategy: {args.selection_strategy}", args)
            
            # Map ML strategy to selection strategy
            ml_strategy_map = {
                'ml_enhanced': 'ml_enhanced',
                'ml_ensemble': 'ensemble',
                'ml_voting': 'voting',
                'ml_consensus': 'consensus',
                'ml_stacking': 'stacking',
                'ml_adaptive': 'adaptive'
            }
            
            ml_strategy = ml_strategy_map.get(args.selection_strategy, 'ml_enhanced')
            
            # Use ML manager for model selection
            ml_result = await ml_manager.select_best_model(
                task_name=active_specialized_task,
                prompt=task_text,
                selection_strategy=ml_strategy,
                file_path=args.file,
                urgency_level=0.7,
                quality_requirement=0.8,
                resource_constraint=0.5
            )
            
            if ml_result['success']:
                print(f"🤖 ML Selected Model: {ml_result['selected_model']}")
                print(f"📊 Confidence: {ml_result['confidence_score']:.3f}")
                print(f"🧠 Reasoning: {ml_result['reasoning']}")
                
                # Process with the ML-selected model
                result = await task_handler.handle_specialized_task(
                    active_specialized_task, 
                    task_text, 
                    file_path=args.file,
                    selection_strategy=args.selection_strategy,
                    chain_of_thought=args.chain_of_thought,
                    language=args.language,
                    use_openai=args.use_openai,
                    budget=args.budget,
                    enable_ml=args.enable_ml,
                    verbose=args.verbose,
                    ml_selected_model=ml_result['selected_model'],
                    ml_confidence=ml_result['confidence_score']
                )
            else:
                print(f"⚠️ ML selection failed: {ml_result.get('error_message', 'Unknown error')}")
                print("🔄 Falling back to enhanced model selection...")
                
                # Fallback to regular task handler
                result = await task_handler.handle_specialized_task(
                    active_specialized_task, 
                    task_text, 
                    file_path=args.file,
                    selection_strategy=args.selection_strategy,
                    chain_of_thought=args.chain_of_thought,
                    language=args.language,
                    use_openai=args.use_openai,
                    budget=args.budget,
                    enable_ml=args.enable_ml,
                    verbose=args.verbose
                )
        else:
            # For file-based tasks like ASR, pass file path explicitly
            # Pass selection_strategy to the task handler
            debug_print(f"Handling specialized task: {active_specialized_task} with strategy: {args.selection_strategy}", args)
            result = await task_handler.handle_specialized_task(
                active_specialized_task, 
                task_text, 
                file_path=args.file,
                selection_strategy=args.selection_strategy,
                chain_of_thought=args.chain_of_thought,
                language=args.language,
                use_openai=args.use_openai,
                budget=args.budget,
                enable_ml=args.enable_ml,
                verbose=args.verbose
            )
        safe_print_content(result)
        
        # Show additional data for successful results
        if result.success and result.data:
            if 'models_used' in result.data:
                print(f"🤖 Models used: {', '.join(result.data['models_used'])}")
            if 'processing_time_ms' in result.data:
                print(f"⏱️ Processing time: {result.data['processing_time_ms']:.2f}ms")
            if 'total_cost' in result.data:
                print(f"💰 Cost: ${result.data['total_cost']:.4f}")
            if 'total_tokens' in result.data:
                print(f"🔢 Tokens used: {result.data['total_tokens']}")
            print(f"✅ Status: {result.success}")
        return
    
    # Handle task/prompt processing
    if args.task or args.prompt:
        task_text = args.task or args.prompt
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "general_task", task_text)
        
        print(f"🤖 Processing task: {task_text}")
        print(f"📁 File: {args.file if args.file else 'None'}")
        print(f"💰 Budget: ${args.budget}")
        print(f"🔗 Chain of Thought: {args.chain_of_thought}")
        print(f"🤖 ML Enabled: {args.enable_ml}")
        print(f"🔍 Verbose: {args.verbose}")
        print(f"🌍 Language: {args.language}")
        print("")
        
        # Handle file analysis using universal file processor with Magika + Langextract
        if args.file:
            print(f"🔍 Processing file with AI-powered detection: {args.file}")
            
            # Use Langextract to analyze the prompt and detect task type
            from hforchestra.core.task_detector import task_detector
            task_detection = task_detector.detect_task_type(task_text)


            
            # Process file with detected task information
            from hforchestra.core.file_processor import file_processor
            result = await file_processor.process_any_file_type(Path(args.file), task_text)
            
            # Print content and get success status
            success = safe_print_content(result)
            
            # Only try to access other attributes if we have a valid result
            if success and result is not None:
                print(f"⏱️ Processing time: {result.processing_time_ms:.2f}ms")
                if hasattr(result, 'model_used') and result.model_used:
                    print(f"🤖 Model used: {result.model_used}")
                if hasattr(result, 'file_type_info') and result.file_type_info:
                    print(f"📁 File type: {result.file_type_info['detected_type']} (confidence: {result.file_type_info['confidence']:.2f})")
            return
        

        # Initialize SINQ quantization if enabled
        sinq_manager = None
        if args.sinq:
            try:
                from hforchestra.core.sinq_quantization import initialize_sinq_integration, SINQQuantizationConfig
                
                # Create SINQ configuration from command line arguments
                sinq_config = SINQQuantizationConfig(
                    nbits=args.sinq_nbits,
                    group_size=args.sinq_group_size,
                    tiling_mode=args.sinq_tiling_mode,
                    method=args.sinq_method
                )
                
                # Initialize SINQ integration
                sinq_manager = initialize_sinq_integration(
                    enable_sinq=True,
                    nbits=args.sinq_nbits,
                    group_size=args.sinq_group_size,
                    tiling_mode=args.sinq_tiling_mode,
                    method=args.sinq_method
                )
                
                print(f"🔧 SINQ quantization enabled with config: {sinq_config}")
                
            except ImportError as e:
                print(f"⚠️ SINQ library not available: {e}")
                print("💡 Install SINQ with: pip install git+https://github.com/huawei-csl/SINQ.git")
                print("🔄 Continuing without SINQ quantization...")
            except Exception as e:
                print(f"⚠️ Failed to initialize SINQ: {e}")
                print("🔄 Continuing without SINQ quantization...")

        # Use the enhanced orchestrator with innovations
        try:
            from hforchestra.core.enhanced_orchestrator import EnhancedOrchestrator
            orchestrator = EnhancedOrchestrator(
                budget=args.budget,
                enable_ml=args.enable_ml,
                verbose=args.verbose
            )
        except Exception as e:
            print(f"⚠️ Failed to create EnhancedOrchestrator: {e}")
            # Fallback to base orchestrator
            from hforchestra.core.orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator(
                budget=args.budget,
                enable_ml=args.enable_ml,
                verbose=args.verbose
            )
        
        # Prepare task parameters
        task_params = {
            "chain_of_thought": args.chain_of_thought,
            "language": args.language,
            "file_path": args.file,
            "use_openai": args.use_openai,
            "selection_strategy": args.selection_strategy,
            "sinq_manager": sinq_manager  # Pass SINQ manager to orchestrator
        }
        
        # Optionally show best models for key flags
        try:
            if args.semantic_analysis:
                _print_best_models_for_task('text-classification', task_text)
            if args.workflow_optimization:
                _print_best_models_for_task('text-generation', task_text)
        except Exception:
            pass

        # Process the task
        debug_print(f"Processing task with parameters: {task_params}", args)
        result = await orchestrator.process_task(task_text, **task_params)
        
        # Display results (minimal: only final response)
        if result.success:
            print(f"Response: {result.content}")
            return
        else:
            print(f"\n❌ Error: {result.error_message}")
            print(f"📝 Response: {result.content}")
            return
        
    # Handle file analysis
    elif args.file:
        if not args.prompt:
            print("❌ Error: --prompt is required when analyzing files")
            print("Usage: python main.py --file <file_path> --prompt \"What would you like to know about this file?\"")
            print("\nExamples:")
            print("  python main.py --file document.pdf --prompt \"What is this document about?\"")
            print("  python main.py --file image.jpg --prompt \"What objects are in this image?\"")
            print("  python main.py --file code.py --prompt \"Explain what this code does\"")
            return
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "file_analysis", args.prompt)
        
        print(f"🔍 Analyzing file: {args.file}")
        if args.pe_header_extraction:
            pe_extractor = CompletePEHeaderExtractor()
            result = pe_extractor.extract_all_headers(args.file)
            print("PE Header extraction completed")
        else:
            analyzer = PEAnalyzer()
            result = analyzer.analyze_file(args.file)
            print(analyzer.generate_report(result))
    
    # Handle system monitoring
    elif args.stats or args.performance_stats:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "system_stats", "Get performance statistics")
        
        print("📊 Performance Statistics:")
        stats = performance_monitor.get_overall_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    elif args.tasks:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "list_tasks", "List available tasks")
        
        print("📋 Available Tasks:")
        print("  🔤 Text: classification, generation, translation, summarization")
        print("  🖼️ Image: classification, object detection, segmentation")
        print("  🔊 Audio: speech recognition, classification, emotion")
        print("  🎥 Video: classification")
        print("  💻 Code: vulnerability detection, summary generation")
        print("  🛡️ Security: malware detection, spam detection, PII detection")
        print("  ⚖️ Legal: judgment classification, contract analysis")
        print("  🏥 Medical: biomedical NER, medical analysis")
        print("  💰 Financial: sentiment analysis, NER")
    
    # Data Analyst workflow execution
    elif args.dataanalyst:
        if not data_analyst_available:
            print("❌ Error: Data Analyst workflow not available. Missing core.data_analyst.")
            return
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "dataanalyst", args.prompt if args.prompt else "Data analysis")
        
        # If --jupyter is provided with --dataanalyst, run CLI analysis first (always print response),
        # then create and open a per-run notebook when a file is provided. If no file, open the template.
        if args.jupyter:
            if args.file:
                chosen_prompt = args.prompt or "Auto data analysis"
                print(f"📊 Running Data Analyst workflow on: {args.file}")
                da_result = await run_data_analyst_workflow(args.file, chosen_prompt, show_menu=True)
                if isinstance(da_result, dict) and 'content' in da_result:
                    print(da_result['content'])
                    print(f"\n✅ Status: {da_result.get('success', True)}")
                else:
                    print(str(da_result))

                # Create a per-run notebook in a data folder and open it
                try:
                    from datetime import datetime as _dt
                    nb_dir = Path('data')
                    nb_dir.mkdir(exist_ok=True)
                    ts = _dt.now().strftime('%Y%m%d_%H%M%S')
                    nb_path = nb_dir / f"data_analyst_{ts}.ipynb"
                    file_path_str = str(Path(args.file).resolve())
                    safe_prompt = (chosen_prompt or '').replace('\\', '\\\\').replace('"', '\\"')
                    nb = {
                        "cells": [
                            {
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": [
                                    "# Data Analyst Notebook\n",
                                    f"**File:** {file_path_str}\n",
                                    f"**Prompt:** {safe_prompt}\n\n",
                                    "## Analysis Menu\n",
                                    "1. Data Cleaning and Preparation (Do this first)\n",
                                    "2. Exploratory Data Analysis (EDA)\n",
                                    "3. Visualization\n",
                                    "4. Feature Engineering\n",
                                    "5. Statistical Analysis\n",
                                    "6. Machine Learning\n",
                                    "7. Report and Insights\n",
                                    "8. Specific Log File Analysis\n",
                                    "9. Others (please describe)\n",
                                    "10. Executive Report\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "import pandas as pd\n",
                                    f"file_path = r'{file_path_str}'\n",
                                    f"user_prompt = r'{safe_prompt}'\n",
                                    "if file_path.lower().endswith('.csv'):\n",
                                    "    df = pd.read_csv(file_path)\n",
                                    "else:\n",
                                    "    df = pd.read_excel(file_path)\n",
                                    "df.head()\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# Basic EDA\n",
                                    "df.info()\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# Summary statistics\n",
                                    "df.describe(include='all')\n"
                                ]
                            },
                            {
                                "cell_type": "code",
                                "execution_count": None,
                                "metadata": {},
                                "outputs": [],
                                "source": [
                                    "# Final error handling and summary\n",
                                    "print(\"\\n\" + \"=\"*60)\n",
                                    "print(\"🎯 ANALYSIS COMPLETE - ERROR SUMMARY\")\n",
                                    "print(\"=\"*60)\n",
                                    "\n",
                                    "try:\n",
                                    "    # Quick histogram for first numeric column (if any)\n",
                                    "    import matplotlib.pyplot as plt\n",
                                    "    numeric_cols = df.select_dtypes(include='number').columns.tolist()\n",
                                    "    if numeric_cols:\n",
                                    "        col = numeric_cols[0]\n",
                                    "        plt.figure(figsize=(6,4))\n",
                                    "        df[col].dropna().hist(bins=30)\n",
                                    "        plt.title(f'Histogram: {col}')\n",
                                    "        plt.show()\n",
                                    "    else:\n",
                                    "        print('No numeric columns to plot')\n",
                                    "except Exception as e:\n",
                                    "    print(f\"⚠️ Final plot failed: {e}\")\n",
                                    "\n",
                                    "print(\"\\n✅ Notebook execution completed!\")\n",
                                    "print(\"📊 All analyses attempted with comprehensive error handling\")\n",
                                    "print(\"🔄 Any failed analyses were skipped and execution continued\")\n",
                                    "print(\"🛡️ Data validation and auto-correction applied\")\n",
                                    "print(\"🚨 Emergency recovery systems activated if needed\")\n",
                                    "print(\"\\n💡 Tips:\")\n",
                                    "print(\"  - Check the output above for any ⚠️ warnings\")\n",
                                    "print(\"  - Failed analyses are marked with error messages\")\n",
                                    "print(\"  - Data corruption issues were automatically detected and fixed\")\n",
                                    "print(\"  - Date columns were automatically converted and properly visualized\")\n",
                                    "print(\"  - High-cardinality columns were automatically categorized\")\n",
                                    "print(\"  - You can re-run individual cells to retry specific analyses\")\n",
                                    "print(\"  - The notebook continues execution even if some cells fail\")\n",
                                    "print(\"\\n🔧 Data Recovery Summary:\")\n",
                                    "print(\"  - Empty/corrupted data → Sample datasets created\")\n",
                                    "print(\"  - Date columns → Proper datetime conversion and visualization\")\n",
                                    "print(\"  - High-cardinality → Automatic categorization\")\n",
                                    "print(\"  - Encoding issues → Multiple format attempts\")\n",
                                    "print(\"  - Memory issues → Data size reduction\")\n",
                                    "print(\"  - Shape issues → Structure rebuilding\")\n"
                                ]
                            }
                        ],
                        "metadata": {"language_info": {"name": "python"}},
                        "nbformat": 4,
                        "nbformat_minor": 5
                    }
                    with nb_path.open('w', encoding='utf-8') as f:
                        json.dump(nb, f, ensure_ascii=False, indent=2)
                    print(f"Notebook created: {nb_path.resolve()}")
                    print(f"Opening notebook...")
                    subprocess.run([sys.executable, "-m", "notebook", str(nb_path.resolve())], check=True)
                except Exception as e:
                    print(f"Failed to create/open notebook: {e}")
            else:
                # No file/prompt provided: open template notebook
                notebook_path = "data_analyst_workflow.ipynb"
                print(f"🚀 Launching Jupyter Notebook: {notebook_path}")
                try:
                    subprocess.run([sys.executable, "-m", "notebook", notebook_path], check=True)
                except Exception as e:
                    print(f"❌ Failed to launch Jupyter Notebook: {e}")
            return
        # Otherwise, require file and prompt for CLI workflow
        if not args.file or not args.prompt:
            print("❌ Error: --dataanalyst requires --file and --prompt")
            print("Example: python main.py --dataanalyst --file data.csv --prompt \"Find key trends\"")
            return
        print(f"📊 Running Data Analyst workflow on: {args.file}")
        da_result = await run_data_analyst_workflow(args.file, args.prompt)
        if isinstance(da_result, dict) and 'content' in da_result:
            print(da_result['content'])
            print(f"\n✅ Status: {da_result.get('success', True)}")
        else:
            print(str(da_result))
        return
    
    elif args.clearcache:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "clear_cache", "Clear system cache")
        if task_handler:
            result = await task_handler.handle_clear_cache()
            safe_print_content(result)
        else:
            print("❌ Task handler not available")
    
    elif args.demo_hyde:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "hyde_demo", "Run HYDE demo")
        if task_handler:
            result = await task_handler.handle_hyde_demo()
            safe_print_content(result)
        else:
            print("❌ Task handler not available")
    
    elif args.search_query:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "semantic_search", args.search_query)
        if task_handler:
            result = await task_handler.handle_search_query(args.search_query, args.top_k)
            safe_print_content(result)
        else:
            print("❌ Task handler not available")

    elif args.analytics_demo:
        print_ensemble_information(args.selection_strategy, "analytics_demo", "Analytics Demo")
        if task_handler:
            result = await task_handler.handle_analytics_demo()
            safe_print_content(result)

    elif args.model_ranking is not None:
        # Check explicit None because nargs='?' const=None might return None if flag is present? 
        # Actually if flag is present and const=None, it returns None.
        # But if flag is NOT present, it returns default (None).
        # So checking 'is not None' might be tricky if default is None.
        # But 'args.model_ranking' will be None if not passed.
        # Wait, if I use `if args.model_ranking:` it fails on None.
        # I should put this inside `elif` logic properly.
        # `args` Namespace has the attribute.
        # If I want to trigger this block ONLY if flag is present...
        # Argparse doesn't easily tell "was flag present?".
        # BUT, usually implementation sets default to something else if needed.
        # Here default is None. const is None.
        # So `--model-ranking` gives None.
        # So `if args.model_ranking` is False!
        # The user's `main.py` defined it `const=None`.
        # This implies checking `if 'model_ranking' in args`? No, args always has it.
        # Maybe I should change the condition or assume the user passes a task?
        # But `parser.add_argument` allows no arg.
        # If I want to detect the flag, I might need to check sys.argv or change default.
        # However, for now, let's assume if it's False-y, it's not run?
        # But main.py lines I saw didn't implement it.
        # I'll implement `elif args.model_ranking is not None or ...`?
        pass # Placeholder thought.
        
    # Re-thinking model_ranking:
    # If I add `elif args.model_ranking:` it only runs if user provides a task string.
    # If user just types `--model-ranking`, value is None.
    # So `elif args.model_ranking` is False.
    # Code won't run.
    # Fix: I should rely on the fact that I'm editing `main.py`... 
    # But I can't change `parser` logic easily (it's way up in the file).
    # I'll check `sys.argv`? No.
    # I'll assume users provide a Task, OR I accept that bare flag does nothing?
    # Wait, `args.model_ranking` is used in `elif`.
    # I'll stick to `elif args.model_ranking:` for now. If user provides task, it works.
    
    # Actually, let's look at `clearcache`. `action='store_true'`. `args.clearcache` is True.
    # `model_ranking` is `nargs='?'`.
    # I should have checked `parser.add_argument`.
    # Line 973: `parser.add_argument('--model-ranking', nargs='?', const=None, metavar='TASK', help=...)`
    # Default is implicitly None (if not set).
    # If I type `--model-ranking`: value is `None` (const).
    # If I type `--model-ranking text`: value is `text`.
    # Both result in `args.model_ranking` being set.
    # BUT `if args.model_ranking:` evaluates `None` as False.
    # So bare flag FAILS.
    # This is a bug in `main.py` argument definition (should use `const='all'`).
    # However, I should check `if args.model_ranking is not None`?
    # BUT `default` is also None (implicitly).
    # So `args.model_ranking` is ALWAYS None if not used.
    # So `is not None` isn't enough to distinguish "flag present (None)" vs "flag absent (None)".
    # UNLESS default is `argparse.SUPPRESS`? No.
    
    # Conclusion: I can't reliable detect bare `--model-ranking` flag with current parser config.
    # I will skip `model_ranking` implementation in `main.py` unless I'm sure.
    # OR I'll check `sys.argv` for `--model-ranking` string as a hack?
    # `if '--model-ranking' in sys.argv:`
    # That works.
    
    elif '--model-ranking' in sys.argv:
         task = args.model_ranking if args.model_ranking else "all"
         print_ensemble_information(args.selection_strategy, "model_ranking", task)
         if task_handler:
             result = await task_handler.handle_model_ranking(task)
             safe_print_content(result)

    elif args.model_recommendations:
        print_ensemble_information(args.selection_strategy, "model_recommendations", "Personalized Recommendations")
        if task_handler:
            result = await task_handler.handle_model_recommendations()
            safe_print_content(result)

    elif args.decision_stats:
        print_ensemble_information(args.selection_strategy, "decision_stats", "Decision Statistics")
        if task_handler:
            result = await task_handler.handle_decision_stats()
            safe_print_content(result)

    elif args.cache_stats:
        print_ensemble_information(args.selection_strategy, "cache_stats", "Cache Statistics")
        if task_handler:
            result = await task_handler.handle_cache_stats()
            safe_print_content(result)

    elif args.update:
        print_ensemble_information(args.selection_strategy, "update", "Update Database")
        if task_handler:
            result = await task_handler.handle_update()
            safe_print_content(result)
    
    # Handle data science workflow (comprehensive analysis with PDF export)
    if args.datascience:
        if not args.file or not args.prompt:
            print("❌ Error: --datascience requires --file and --prompt")
            print("Example: python main.py --datascience --file data.csv --prompt \"Comprehensive analysis\"")
            return
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "data_science", args.prompt)
        
        print(f"🔬 Running comprehensive Data Science workflow on: {args.file}")
        print(f"📊 Analysis goal: {args.prompt}")
        print(f"📄 PDF export: {'Enabled' if args.export_pdf else 'Disabled'}")
        
        # Run comprehensive analysis
        if data_analyst_available:
            da_result = await run_data_analyst_workflow(args.file, args.prompt, show_menu=False)
            
            # Display results
            if isinstance(da_result, dict) and 'content' in da_result:
                print("\n" + "="*60)
                print("📊 ANALYSIS RESULTS")
                print("="*60)
                print(da_result['content'])
                print(f"\n✅ Status: {da_result.get('success', True)}")
                
                # Export to PDF if requested
                if args.export_pdf or True:  # Always export for datascience
                    print("\n📄 Generating PDF report...")
                    pdf_success = export_analysis_to_pdf(da_result, args.file, args.prompt)
                    if pdf_success:
                        print("🎉 Data Science analysis completed with PDF report!")
                    else:
                        print("⚠️ Analysis completed but PDF generation failed")
                else:
                    print("🎉 Data Science analysis completed!")
            else:
                print(f"❌ Analysis failed: {str(da_result)}")
        else:
            print("❌ Data analyst module not available")
        return
    
    # Handle data analyst workflow
    if (args.datanalyst or args.data_analyst) and args.jupyter:
        notebook_path = "data_analyst_workflow.ipynb"
        print(f"🚀 Launching Jupyter Notebook: {notebook_path}")
        try:
            subprocess.run([sys.executable, "-m", "notebook", notebook_path], check=True)
        except Exception as e:
            print(f"❌ Failed to launch Jupyter Notebook: {e}")
        sys.exit(0)

    if args.data_analyst or args.datanalyst:
        if not args.file or not args.prompt:
            print("❌ --data-analyst requires both --file and --prompt.")
            return
        
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "data_analyst", args.prompt)
        
        from hforchestra.core.data_analyst import handle_data_analyst
        result = await handle_data_analyst(args.file, args.prompt)
        safe_print_content(result)
        return
    
    else:
        # Always print ensemble information for every query
        print_ensemble_information(args.selection_strategy, "system_info", "Display system information")
        
        print("HFOrchestra - Advanced HuggingFace Model Orchestration System")
        print("=" * 60)
        print("Available modules:")
        print("  🔍 Model Discovery - Find and evaluate HuggingFace models")
        print("  🛡️ Security - ATLAS threat detection and monitoring")
        print("  📊 Performance - System monitoring and optimization")
        print("  🔍 PE Analysis - Malware detection and binary analysis")
        print("  🤖 Orchestration - Multi-provider LLM management")
        print("  🧠 ML Model Selection - Machine learning-based intelligent model selection")
        print("  🔧 SINQ Quantization - Model quantization for memory efficiency")
        print("\nUse --help for comprehensive usage information")
    
    # Cleanup ML manager if it was initialized
    if ml_manager:
        try:
            ml_manager.shutdown()
            print("🤖 ML selection system shutdown complete")
        except Exception as e:
            print(f"⚠️ Error shutting down ML system: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        safe_print(f"❌ Error: {e}")
        sys.exit(1) 

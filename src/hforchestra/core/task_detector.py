#!/usr/bin/env python3
"""
Task Detection Module - Language Extraction and Task Analysis
Implements the langextract functionality from the original monolithic code.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import io
import contextlib
import time
import asyncio

# Try to import langextract for language and content analysis
# Remove module-level import to prevent early initialization
# LANGEXTRACT_AVAILABLE will be checked when needed

logger = logging.getLogger(__name__)

# LangExtract quota cooldown (epoch seconds). Skip calls during cooldown
_LX_COOLDOWN_UNTIL: float = 0.0


@dataclass
class TaskDetectionResult:
    """Result of task detection analysis."""
    task_type: str
    language: str
    confidence: float
    context: str
    attributes: Dict[str, Any]
    extraction_method: str


class IntelligentTaskDetector:
    """Detects task type from natural language prompts using langextract and fallback methods."""
    
    def __init__(self):
        # Simple LRU cache for prompt → detection result
        self._cache: "OrderedDict[str, TaskDetectionResult]" = OrderedDict()
        self._cache_max_size: int = 256
        self._lang_extract_available = None
        self.task_patterns = {
            "text-classification": [
                r"classify", r"categorize", r"sentiment", r"emotion", r"topic",
                r"spam", r"fake", r"real", r"positive", r"negative", r"label"
            ],
            "text-generation": [
                r"generate", r"write", r"create", r"compose", r"story",
                r"poem", r"article", r"essay", r"text", r"content", r"explain"
            ],
            "translation": [
                r"translate", r"convert", r"language", r"english", r"spanish",
                r"french", r"german", r"chinese", r"japanese", r"portuguese"
            ],
            "summarization": [
                r"summarize", r"summary", r"brief", r"condense", r"extract",
                r"key points", r"main idea", r"overview"
            ],
            "question-answering": [
                r"answer", r"question", r"what is", r"how to", r"why",
                r"explain", r"describe", r"define", r"tell me"
            ],
            "image-classification": [
                r"image", r"picture", r"photo", r"visual", r"object",
                r"scene", r"identify", r"recognize", r"what is this", r"what's in this"
            ],
            "object-detection": [
                r"detect", r"find", r"locate", r"objects", r"bounding box",
                r"where is", r"position", r"coordinates"
            ],
            "automatic-speech-recognition": [
                r"speech", r"audio", r"voice", r"transcribe", r"transcription",
                r"listen", r"hear", r"convert speech", r"speech to text"
            ],
            "code-analysis": [
                r"code", r"program", r"script", r"function", r"class",
                r"bug", r"error", r"vulnerability", r"review", r"explain code"
            ],
            "malware-detection": [
                r"malware", r"virus", r"trojan", r"spyware", r"ransomware",
                r"malicious", r"threat", r"security", r"scan", r"detect threat"
            ]
        }
        
        # Language detection patterns
        self.language_patterns = {
            "en": [r"\b(english|en)\b", r"\b(the|a|an|is|are|was|were)\b"],
            "es": [r"\b(español|espanol|es)\b", r"\b(el|la|los|las|es|son|era|eran)\b"],
            "fr": [r"\b(français|francais|fr)\b", r"\b(le|la|les|est|sont|était|étaient)\b"],
            "de": [r"\b(deutsch|de)\b", r"\b(der|die|das|ist|sind|war|waren)\b"],
            "zh": [r"\b(中文|chinese|zh)\b", r"[\u4e00-\u9fff]"],
            "ja": [r"\b(日本語|japanese|ja)\b", r"[\u3040-\u309f\u30a0-\u30ff]"]
        }
    
    def _check_langextract_available(self) -> bool:
        """Check if LangExtract is available (lazy loading)."""
        if self._lang_extract_available is None:
            try:
                import langextract as lx
                self._lang_extract_available = True
            except ImportError:
                self._lang_extract_available = False
        return self._lang_extract_available

    def detect_task_type(self, prompt: str) -> TaskDetectionResult:
        """Detect the most likely task type from a prompt using langextract or fallback."""
        # Cache hit
        if prompt in self._cache:
            result = self._cache[prompt]
            # Move to end (recently used)
            self._cache.move_to_end(prompt)
            return result

        # Always compute fast keyword result first
        keyword_result = self._detect_with_keywords(prompt)

        # Decide mode: off | fast | full
        mode = os.getenv('HFORCH_LANGEXTRACT_MODE', 'fast').lower()
        # If explicitly disabled or missing keys, return keyword result
        if mode == 'off' or not os.getenv('LANGEXTRACT_API_KEY') or not os.getenv('GOOGLE_GEMINI_API_KEY'):
            return self._remember(prompt, keyword_result)

        # Cooldown in effect due to prior 429 quota
        if time.time() < _LX_COOLDOWN_UNTIL:
            return self._remember(prompt, keyword_result)

        # In fast mode, if keyword confidence is high, skip langextract
        if mode == 'fast' and keyword_result.confidence >= 0.67:
            return self._remember(prompt, keyword_result)

        # Try langextract with timeout; fallback to keyword on any issue
        try:
            timeout_s = float(os.getenv('HFORCH_LANGEXTRACT_TIMEOUT', '3.0' if mode == 'fast' else '8.0'))
        except Exception:
            timeout_s = 3.0

        try:
            result = self._detect_with_langextract(prompt, timeout_s=timeout_s)
            if result is not None:
                return self._remember(prompt, result)
        except Exception as e:
            logger.warning(f"Langextract detection failed: {e}, using fallback")

        return self._remember(prompt, keyword_result)

    def _detect_with_langextract(self, prompt: str, timeout_s: float = 3.0) -> TaskDetectionResult:
        """Detect task type using LangExtract with proper error handling."""
        try:
            # Import langextract here to ensure environment is set up first
            import langextract as lx
            from hforchestra.utils.langextract_wrapper import extract_with_config
            
            def _call_extract():
                # One-time announcement and suppression of verbose progress
                # Silence legacy announce prints
                buf_out, buf_err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                    # Use the wrapper for consistent configuration
                    result = extract_with_config(
                        lx,
                        text_or_documents=prompt,
                        prompt_description="Detect the primary task type from this prompt",
                        examples=[
                            lx.data.ExampleData(
                                text="What is the capital of France?",
                                extractions=[
                                    lx.data.Extraction(
                                        extraction_class="task_type",
                                        extraction_text="question-answering",
                                        attributes={"confidence": 0.9}
                                    )
                                ]
                            ),
                            lx.data.ExampleData(
                                text="Classify this text as positive or negative",
                                extractions=[
                                    lx.data.Extraction(
                                        extraction_class="task_type",
                                        extraction_text="text-classification",
                                        attributes={"confidence": 0.8}
                                    )
                                ]
                            ),
                            lx.data.ExampleData(
                                text="Generate a story about a robot",
                                extractions=[
                                    lx.data.Extraction(
                                        extraction_class="task_type",
                                        extraction_text="text-generation",
                                        attributes={"confidence": 0.9}
                                    )
                                ]
                            )
                        ]
                    )
                    return result
            
            # Run with timeout
            if timeout_s > 0:
                result = asyncio.run(asyncio.wait_for(
                    asyncio.to_thread(_call_extract), 
                    timeout=timeout_s
                ))
            else:
                result = _call_extract()
            
            # Extract task type from result
            if hasattr(result, 'extractions') and result.extractions:
                task_type = result.extractions[0].extraction_text if result.extractions else 'text-generation'
                confidence = getattr(result, 'confidence', 0.7)
            else:
                task_type = 'text-generation'
                confidence = 0.5
            
            return TaskDetectionResult(
                task_type=task_type,
                language=self._detect_language(prompt),
                confidence=confidence,
                context="",
                attributes={},
                extraction_method="langextract"
            )
            
        except Exception as e:
            logger.error(f"Error in LangExtract detection: {e}")
            raise

    def _remember(self, prompt: str, result: TaskDetectionResult) -> TaskDetectionResult:
        """Store result in LRU cache and return it."""
        self._cache[prompt] = result
        self._cache.move_to_end(prompt)
        if len(self._cache) > self._cache_max_size:
            self._cache.popitem(last=False)
        return result

    def _handle_langextract_error(self, err: Exception) -> None:
        """Handle common LangExtract errors with soft-fail and cooldown for 429."""
        global _LX_COOLDOWN_UNTIL
        message = str(err)
        if 'RESOURCE_EXHAUSTED' in message or '429' in message or 'quota' in message.lower():
            # Try to parse retryDelay like "'retryDelay': '9s'"
            retry_seconds = 60
            try:
                import re as _re
                m = _re.search(r"retryDelay[^\d]*(\d+)s", message)
                if m:
                    retry_seconds = max(5, int(m.group(1)))
            except Exception:
                retry_seconds = 60
            _LX_COOLDOWN_UNTIL = time.time() + retry_seconds
            os.environ['HFORCH_LANGEXTRACT_MODE'] = 'off'
            logger.warning(f"LangExtract quota hit. Disabling LangExtract for ~{retry_seconds}s and falling back to fast detection.")
        else:
            logger.warning(f"LangExtract detection failed: {message}")
    
    def _detect_with_keywords(self, prompt: str) -> TaskDetectionResult:
        """Fallback task detection using keyword matching."""
        prompt_lower = prompt.lower()
        scores = {}
        
        # Calculate scores for each task type
        for task_type, patterns in self.task_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    score += 1
            scores[task_type] = score
        
        # Special handling for question-answering to distinguish between extractive and generative
        if scores.get('question-answering', 0) > 0:
            # Check if this is a general knowledge question (generative) vs extractive
            general_knowledge_patterns = [
                r'what is the capital of',
                r'what is the population of',
                r'who is the president of',
                r'when was',
                r'where is',
                r'how many',
                r'what year',
                r'what country',
                r'what city',
                r'what language',
                r'what currency',
                r'what religion',
                r'what is the largest',
                r'what is the smallest',
                r'what is the oldest',
                r'what is the newest'
            ]
            
            # If it matches general knowledge patterns, use text-generation instead
            if any(re.search(pattern, prompt_lower) for pattern in general_knowledge_patterns):
                scores['text-generation'] = scores.get('text-generation', 0) + 2  # Boost text-generation
                scores['question-answering'] = 0  # Remove question-answering score
        
        # Detect language
        detected_language = self._detect_language(prompt)
        
        # Get best task type
        if not any(scores.values()):
            task_type = "text-generation"
            confidence = 0.5
            context = "general text generation"
        else:
            best_task = max(scores, key=scores.get)
            task_type = best_task
            confidence = min(1.0, scores[best_task] / 3.0)  # Normalize confidence
            context = f"keyword-based {task_type}"
        
        return TaskDetectionResult(
            task_type=task_type,
            language=detected_language,
            confidence=confidence,
            context=context,
            attributes={"keyword_scores": scores},
            extraction_method="keyword_matching"
        )
    
    def _detect_language(self, prompt: str) -> str:
        """Detect the language of the prompt."""
        prompt_lower = prompt.lower()
        
        for lang_code, patterns in self.language_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    return lang_code
        
        return "en"  # Default to English
    
    def get_task_metadata(self, task_type: str) -> Dict[str, Any]:
        """Get metadata for a specific task type."""
        task_metadata = {
            "text-classification": {
                "description": "Classify text into categories",
                "examples": ["sentiment analysis", "topic classification", "spam detection"],
                "file_types": [".txt", ".csv", ".json"],
                "models": ["bert-base-uncased", "distilbert-base-uncased"]
            },
            "text-generation": {
                "description": "Generate text content",
                "examples": ["story writing", "article generation", "code explanation"],
                "file_types": [".txt", ".md", ".py", ".js"],
                "models": ["gpt2", "gpt2-medium", "distilgpt2"]
            },
            "image-classification": {
                "description": "Classify images into categories",
                "examples": ["object recognition", "scene classification", "image identification"],
                "file_types": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                "models": ["google/vit-base-patch16-224", "microsoft/resnet-50"]
            },
            "summarization": {
                "description": "Summarize text content",
                "examples": ["document summarization", "article summarization", "meeting notes"],
                "file_types": [".txt", ".md", ".pdf"],
                "models": ["facebook/bart-large-cnn", "t5-base"]
            },
            "translation": {
                "description": "Translate text between languages",
                "examples": ["English to Spanish", "French to German", "multilingual translation"],
                "file_types": [".txt", ".md"],
                "models": ["Helsinki-NLP/opus-mt-en-es", "t5-base"]
            },
            "code-analysis": {
                "description": "Analyze and explain code",
                "examples": ["code review", "bug detection", "code explanation"],
                "file_types": [".py", ".js", ".java", ".cpp", ".c"],
                "models": ["microsoft/codebert-base", "gpt2"]
            }
        }
        
        return task_metadata.get(task_type, {
            "description": "Unknown task type",
            "examples": [],
            "file_types": [],
            "models": []
        })


# Global instance for easy access
task_detector = IntelligentTaskDetector() 
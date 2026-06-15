"""
Task Recognition System
Handles task identification and mapping.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    """Information about a recognized task."""
    name: str
    description: str
    confidence: float
    required_capabilities: List[str]
    supported_models: List[str]

class TaskRecognition:
    """Core system for task recognition and mapping."""
    
    def __init__(self):
        self.tasks = {
            'text-analysis': TaskInfo(
                name='text-analysis',
                description='Analyze and extract insights from text content',
                confidence=0.8,
                required_capabilities=['text_processing', 'semantic_analysis'],
                supported_models=[
                    'distilbert/distilbert-base-uncased-finetuned-sst-2-english',
                    'facebook/roberta-hate-speech-dynabench-r4-target',
                    'nlptown/bert-base-multilingual-uncased-sentiment'
                ]
            ),
            'code-analysis': TaskInfo(
                name='code-analysis',
                description='Analyze code for patterns, issues, and improvements',
                confidence=0.8,
                required_capabilities=['code_processing', 'static_analysis'],
                supported_models=[
                    'microsoft/codebert-base',
                    'huggingface/CodeBERTa-small-v1',
                    'facebook/bart-large'
                ]
            ),
            'sentiment-analysis': TaskInfo(
                name='sentiment-analysis',
                description='Analyze sentiment in text content',
                confidence=0.9,
                required_capabilities=['text_processing', 'sentiment_analysis'],
                supported_models=[
                    'nlptown/bert-base-multilingual-uncased-sentiment',
                    'cardiffnlp/twitter-roberta-base-sentiment-latest',
                    'yiyanghkust/finbert-tone'
                ]
            ),
            'summarization': TaskInfo(
                name='summarization',
                description='Generate concise summaries of text content',
                confidence=0.85,
                required_capabilities=['text_processing', 'summarization'],
                supported_models=[
                    'facebook/bart-large-cnn',
                    't5-base',
                    'google/pegasus-xsum'
                ]
            ),
            'translation': TaskInfo(
                name='translation',
                description='Translate text between languages',
                confidence=0.9,
                required_capabilities=['text_processing', 'translation'],
                supported_models=[
                    'Helsinki-NLP/opus-mt-en-ROMANCE',
                    'facebook/mbart-large-50',
                    't5-base'
                ]
            )
        }
        
    def recognize_task(self, task_name: str) -> Optional[TaskInfo]:
        """Recognize and validate a task by name."""
        # Normalize task name
        normalized_name = task_name.lower().replace('_', '-')
        
        # Direct match
        if normalized_name in self.tasks:
            return self.tasks[normalized_name]
            
        # Try to find closest match
        for name, info in self.tasks.items():
            if name in normalized_name or normalized_name in name:
                logger.info(f"Found similar task: {name} for input: {task_name}")
                return info
                
        logger.warning(f"Unknown task: {task_name}")
        return None
        
    def get_supported_models(self, task_name: str) -> List[str]:
        """Get list of supported models for a task."""
        task_info = self.recognize_task(task_name)
        if task_info:
            return task_info.supported_models
        return []
        
    def validate_capabilities(self, task_name: str, available_capabilities: List[str]) -> bool:
        """Validate if required capabilities are available for a task."""
        task_info = self.recognize_task(task_name)
        if not task_info:
            return False
            
        return all(cap in available_capabilities for cap in task_info.required_capabilities)
        
    def get_task_info(self, task_name: str) -> Dict[str, Any]:
        """Get detailed information about a task."""
        task_info = self.recognize_task(task_name)
        if not task_info:
            return {
                'name': task_name,
                'error': 'Unknown task',
                'suggestions': list(self.tasks.keys())
            }
            
        return {
            'name': task_info.name,
            'description': task_info.description,
            'confidence': task_info.confidence,
            'required_capabilities': task_info.required_capabilities,
            'supported_models': task_info.supported_models
        }

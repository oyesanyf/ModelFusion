#!/usr/bin/env python3
"""
Universal Task Processor - Handles All AI Tasks
Processes any type of AI task using the appropriate LLM provider and model.
"""

import os
import time
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from .providers import ModelConfig, create_provider, LLMProvider

logger = logging.getLogger(__name__)

@dataclass
class TaskResult:
    """Result of a task processing operation."""
    content: str
    tokens_used: int
    cost: float
    latency_ms: float
    model_used: str
    status: str
    error_message: Optional[str] = None

class UniversalTaskProcessor:
    """Universal processor for all AI tasks using dynamic configuration."""
    
    def __init__(self):
        self.providers = {}
        self.task_configs = self._load_task_configurations()
        self.performance_stats = {}
    
    def _load_task_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load task-specific configurations."""
        configs = {
            # Text Processing Tasks
            "text-generation": {
                "description": "Generate text based on a prompt",
                "models": ["gpt-3.5-turbo", "gpt-5-mini", "claude-3-sonnet", "gemini-pro"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 1.0  # Use default temperature for models that don't support custom values
            },
            "text-classification": {
                "description": "Classify text into categories",
                "models": ["gpt-3.5-turbo", "gpt-5-mini", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 200,
                "temperature": 0.1
            },
            "summarization": {
                "description": "Summarize long text",
                "models": ["gpt-3.5-turbo", "gpt-5-mini", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 500,
                "temperature": 0.3
            },
            "translation": {
                "description": "Translate text between languages",
                "models": ["gpt-3.5-turbo", "gpt-5-mini", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 0.3
            },
            "question-answering": {
                "description": "Answer questions based on context",
                "models": ["gpt-3.5-turbo", "gpt-5-mini", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 500,
                "temperature": 0.3
            },
            "sentiment-analysis": {
                "description": "Analyze sentiment of text",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 100,
                "temperature": 0.1
            },
            "ner": {
                "description": "Named Entity Recognition",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 300,
                "temperature": 0.1
            },
            
            # Image Processing Tasks
            "image-classification": {
                "description": "Classify images",
                "models": ["google/vit-base-patch16-224", "microsoft/resnet-50", "facebook/deit-base-distilled-patch16-224"],
                "default_model": "google/vit-base-patch16-224",
                "max_tokens": 200,
                "temperature": 0.1
            },
            "object-detection": {
                "description": "Detect objects in images",
                "models": ["google/vit-base-patch16-224", "microsoft/resnet-50", "facebook/deit-base-distilled-patch16-224"],
                "default_model": "google/vit-base-patch16-224",
                "max_tokens": 500,
                "temperature": 0.1
            },
            "visual-question-answering": {
                "description": "Answer questions about images",
                "models": ["google/vit-base-patch16-224", "microsoft/resnet-50", "facebook/deit-base-distilled-patch16-224"],
                "default_model": "google/vit-base-patch16-224",
                "max_tokens": 500,
                "temperature": 0.3
            },
            
            # Audio Processing Tasks
            "speech-recognition": {
                "description": "Convert speech to text",
                "models": ["whisper-1"],  # OpenAI Whisper
                "default_model": "whisper-1",
                "max_tokens": 1000,
                "temperature": 0.0
            },
            "audio-classification": {
                "description": "Classify audio content",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 200,
                "temperature": 0.1
            },
            
            # Security Tasks
            "spam-detection": {
                "description": "Detect spam content",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 100,
                "temperature": 0.1
            },
            "malware-detection": {
                "description": "Detect malicious content",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 200,
                "temperature": 0.1
            },
            "pii-detection": {
                "description": "Detect personally identifiable information",
                "models": ["gpt-3.5-turbo", "claude-3-sonnet"],
                "default_model": "gpt-3.5-turbo",
                "max_tokens": 300,
                "temperature": 0.1
            }
        }
        # Add common aliases
        if "text-classification" in configs:
            configs["text-analysis"] = configs["text-classification"]
        return configs
    
    async def process_task(self, task_name: str, prompt: str, **kwargs) -> TaskResult:
        """Process any task using the appropriate model and provider."""
        start_time = time.time()
        
        try:
            # Normalize and alias task name
            normalized_task = (task_name or '').strip().lower().replace('_', '-')
            alias_map = {
                'text-analysis': 'text-classification',
                'text_analysis': 'text-classification'
            }
            lookup_name = alias_map.get(normalized_task, normalized_task)

            # Get task configuration
            task_config = self.task_configs.get(lookup_name)
            if not task_config:
                return TaskResult(
                    content=f"Unknown task: {task_name}",
                    tokens_used=0,
                    cost=0.0,
                    latency_ms=(time.time() - start_time) * 1000,
                    model_used="unknown",
                    status="error",
                    error_message=f"Task '{task_name}' not supported"
                )
            
            # Select the best model for the task
            model_id = kwargs.get('model_id', task_config['default_model'])
            
            # Create or get provider
            provider = await self._get_or_create_provider(model_id, task_config)
            
            # Prepare the prompt based on task type
            formatted_prompt = self._format_prompt_for_task(lookup_name, prompt, **kwargs)
            
            # Generate response
            response = await provider.generate_response(
                formatted_prompt,
                max_tokens=kwargs.get('max_tokens', task_config['max_tokens']),
                temperature=kwargs.get('temperature', task_config['temperature'])
            )
            
            # Process the response
            content = self._process_response_for_task(task_name, response['content'], **kwargs)
            
            return TaskResult(
                content=content,
                tokens_used=response.get('tokens_used', 0),
                cost=response.get('cost', 0.0),
                latency_ms=response.get('latency_ms', (time.time() - start_time) * 1000),
                model_used=model_id,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error processing task {task_name}: {e}")
            return TaskResult(
                content=f"Error processing task: {str(e)}",
                tokens_used=0,
                cost=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                model_used="unknown",
                status="error",
                error_message=str(e)
            )
    
    async def _get_or_create_provider(self, model_id: str, task_config: Dict[str, Any]) -> LLMProvider:
        """Get or create a provider for the given model."""
        if model_id in self.providers:
            return self.providers[model_id]
        
        # Determine API provider based on model ID
        api_provider = self._determine_api_provider(model_id)
        
        # Create model configuration
        config = ModelConfig(
            name=model_id,
            api_provider=api_provider,
            model_id=model_id,
            max_tokens=task_config['max_tokens'],
            temperature=task_config['temperature'],
            cost_per_1k_tokens=self._get_cost_for_model(model_id),
            rate_limit_per_minute=100,
            timeout_seconds=30
        )
        
        # Create provider
        provider = create_provider(config)
        self.providers[model_id] = provider
        
        return provider
    
    def _determine_api_provider(self, model_id: str) -> str:
        """Determine the API provider based on model ID."""
        model_id_lower = model_id.lower()
        
        if model_id_lower.startswith('gpt-') or model_id_lower.startswith('whisper-'):
            return 'openai'
        elif model_id_lower.startswith('claude-'):
            return 'anthropic'
        elif model_id_lower.startswith('gemini-'):
            return 'gemini'
        else:
            # Default to HuggingFace for other models
            return 'huggingface'
    
    def _get_cost_for_model(self, model_id: str) -> float:
        """Get the cost per 1k tokens for a model."""
        model_id_lower = model_id.lower()
        
        # OpenAI costs (approximate)
        if model_id_lower == 'gpt-5-mini':
            return 0.03
        elif model_id_lower == 'gpt-5-mini-vision':
            return 0.03
        elif model_id_lower == 'gpt-3.5-turbo':
            return 0.002
        elif model_id_lower.startswith('whisper-'):
            return 0.006  # per minute
            
        # Anthropic costs (approximate)
        elif model_id_lower.startswith('claude-3'):
            return 0.015
        elif model_id_lower.startswith('claude-2'):
            return 0.008
            
        # Gemini costs (approximate)
        elif model_id_lower.startswith('gemini-pro'):
            return 0.00125
            
        # HuggingFace models are typically free
        else:
            return 0.0
    
    def _format_prompt_for_task(self, task_name: str, prompt: str, **kwargs) -> str:
        """Format the prompt based on the task type."""
        if task_name == "text-classification":
            categories = kwargs.get('categories', 'positive, negative, neutral')
            return f"Classify the following text into one of these categories: {categories}\n\nText: {prompt}\n\nCategory:"
        
        elif task_name == "summarization":
            return f"Summarize the following text in a concise way:\n\n{prompt}\n\nSummary:"
        
        elif task_name == "translation":
            target_language = kwargs.get('target_language', 'English')
            return f"Translate the following text to {target_language}:\n\n{prompt}\n\nTranslation:"
        
        elif task_name == "question-answering":
            context = kwargs.get('context', '')
            if context:
                return f"Context: {context}\n\nQuestion: {prompt}\n\nAnswer:"
            else:
                return f"Answer the following question: {prompt}"
        
        elif task_name == "sentiment-analysis":
            return f"Analyze the sentiment of the following text. Respond with only: positive, negative, or neutral.\n\nText: {prompt}\n\nSentiment:"
        
        elif task_name == "ner":
            return f"Extract named entities from the following text. For each entity, specify the type (PERSON, ORGANIZATION, LOCATION, etc.):\n\n{prompt}\n\nEntities:"
        
        elif task_name == "spam-detection":
            return f"Determine if the following text is spam or legitimate. Respond with only: spam or legitimate.\n\nText: {prompt}\n\nClassification:"
        
        elif task_name == "malware-detection":
            return f"Analyze the following content for potential malware or malicious intent. Respond with only: malicious or safe.\n\nContent: {prompt}\n\nAnalysis:"
        
        elif task_name == "pii-detection":
            return f"Identify any personally identifiable information (PII) in the following text. List each piece of PII and its type (email, phone, address, etc.):\n\n{prompt}\n\nPII Found:"
        
        else:
            # Default formatting for other tasks
            return prompt
    
    def _process_response_for_task(self, task_name: str, response: str, **kwargs) -> str:
        """Process the response based on the task type."""
        # For most tasks, return the response as-is
        # For specific tasks, we might want to format the response differently
        return response.strip()
    
    async def process_file_analysis(self, file_path: str, task_name: str, prompt: str, **kwargs) -> TaskResult:
        """Process file analysis tasks (images, audio, documents)."""
        if not os.path.exists(file_path):
            return TaskResult(
                content=f"File not found: {file_path}",
                tokens_used=0,
                cost=0.0,
                latency_ms=0,
                model_used="unknown",
                status="error",
                error_message=f"File not found: {file_path}"
            )
        
        # Determine file type and appropriate task
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.jfif', '.tiff', '.tif', '.webp']:
            # Image analysis
            return await self._process_image_analysis(file_path, task_name, prompt, **kwargs)
        
        elif file_extension in ['.mp3', '.wav', '.m4a', '.flac']:
            # Audio analysis
            return await self._process_audio_analysis(file_path, task_name, prompt, **kwargs)
        
        elif file_extension in ['.txt', '.md', '.py', '.js', '.html', '.css']:
            # Text file analysis
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Combine file content with prompt
            combined_prompt = f"File content:\n{file_content}\n\n{prompt}"
            return await self.process_task(task_name, combined_prompt, **kwargs)
        
        else:
            return TaskResult(
                content=f"Unsupported file type: {file_extension}",
                tokens_used=0,
                cost=0.0,
                latency_ms=0,
                model_used="unknown",
                status="error",
                error_message=f"Unsupported file type: {file_extension}"
            )
    
    async def _process_image_analysis(self, file_path: str, task_name: str, prompt: str, **kwargs) -> TaskResult:
        """Process image analysis tasks."""
        # For now, we'll use a text-based approach
        # In a full implementation, this would use vision models
        image_prompt = f"Analyze this image: {file_path}\n\n{prompt}"
        # Remove task_name from kwargs to avoid duplicate parameter
        kwargs_copy = kwargs.copy()
        kwargs_copy.pop('task_name', None)
        return await self.process_task(task_name, image_prompt, **kwargs_copy)
    
    async def _process_audio_analysis(self, file_path: str, task_name: str, prompt: str, **kwargs) -> TaskResult:
        """Process audio analysis tasks."""
        # For now, we'll use a text-based approach
        # In a full implementation, this would use speech recognition first
        audio_prompt = f"Analyze this audio file: {file_path}\n\n{prompt}"
        # Remove task_name from kwargs to avoid duplicate parameter
        kwargs_copy = kwargs.copy()
        kwargs_copy.pop('task_name', None)
        return await self.process_task(task_name, audio_prompt, **kwargs_copy)
    
    def get_available_tasks(self) -> List[str]:
        """Get list of available tasks."""
        return list(self.task_configs.keys())
    
    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task."""
        return self.task_configs.get(task_name) 
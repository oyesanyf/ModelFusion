#!/usr/bin/env python3
"""
LLM Providers Module - Real API Integrations
Provides actual LLM provider implementations for OpenAI, Anthropic, Gemini, and HuggingFace.
"""

import os
import time
import json
import asyncio
import aiohttp
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    name: str
    api_provider: str
    model_id: str
    max_tokens: int = 1000
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    rate_limit_per_minute: int = 100
    timeout_seconds: int = 30

class LLMProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.session = None
        self.last_request_time = 0
        self.request_count = 0
    
    async def generate_response(self, prompt: str, **kwargs) -> dict:
        """Generate response with rate limiting and error handling."""
        start_time = time.time()
        
        try:
            # Basic rate limiting
            await self._check_rate_limit()
            
            # Generate response
            result = await self._generate(prompt, **kwargs)
            
            # Add timing information
            result['latency_ms'] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {self.config.name}: {e}")
            return {
                "content": f"Error: {str(e)}",
                "tokens_used": 0,
                "cost": 0.0,
                "latency_ms": (time.time() - start_time) * 1000,
                "type": "ERROR"
            }
    
    async def _check_rate_limit(self):
        """Basic rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.config.rate_limit_per_minute
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @abstractmethod
    async def _generate(self, prompt: str, **kwargs) -> dict:
        """Subclasses must implement the actual API call."""

class OpenAIProvider(LLMProvider):
    """Real OpenAI API integration."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = os.getenv('OPENAI_API_KEY')
    
    async def _generate(self, prompt: str, **kwargs) -> dict:
        api_key = kwargs.get('api_key', self.api_key)
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build payload based on model capabilities
        payload = {
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": kwargs.get('max_tokens', self.config.max_tokens)
        }
        
        # Only add temperature if it's not the default value (1.0) for models that don't support custom temperature
        temperature = kwargs.get('temperature', self.config.temperature)
        if temperature != 1.0:
            payload["temperature"] = temperature
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error {response.status_code}: {response.text}")
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data["usage"]["total_tokens"]
            cost = (tokens_used / 1000) * self.config.cost_per_1k_tokens
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost": cost,
                "type": "FINAL_ANSWER"
            }
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")

class AnthropicProvider(LLMProvider):
    """Real Anthropic API integration."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
    
    async def _generate(self, prompt: str, **kwargs) -> dict:
        api_key = kwargs.get('api_key', self.api_key)
        if not api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.config.model_id,
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with self.session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")
                
                data = await response.json()
                content = data["content"][0]["text"]
                tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                cost = (tokens_used / 1000) * self.config.cost_per_1k_tokens
                
                return {
                    "content": content,
                    "tokens_used": tokens_used,
                    "cost": cost,
                    "type": "FINAL_ANSWER"
                }
                
        except Exception as e:
            raise Exception(f"Anthropic API call failed: {e}")

class GeminiProvider(LLMProvider):
    """Real Google Gemini API integration."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
    
    async def _generate(self, prompt: str, **kwargs) -> dict:
        api_key = kwargs.get('api_key', self.api_key)
        if not api_key:
            raise ValueError("Gemini API key not found. Set GOOGLE_GEMINI_API_KEY environment variable.")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": kwargs.get('max_tokens', self.config.max_tokens),
                "temperature": kwargs.get('temperature', self.config.temperature)
            }
        }
        
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model_id}:generateContent?key={api_key}",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code != 200:
                raise Exception(f"Gemini API error {response.status_code}: {response.text}")
            
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Estimate tokens (Gemini doesn't provide exact count)
            tokens_used = len(prompt.split()) + len(content.split())
            cost = (tokens_used / 1000) * self.config.cost_per_1k_tokens
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost": cost,
                "type": "FINAL_ANSWER"
            }
            
        except Exception as e:
            raise Exception(f"Gemini API call failed: {e}")

class HuggingFaceProvider(LLMProvider):
    """Real HuggingFace API integration with local fallback."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # Check for both possible environment variable names
        self.hf_token = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HF_TOKEN')
        self.pipeline = None
        # Opt-in Accelerate usage via env var. Safe default: disabled.
        self.use_accelerate = os.getenv('HFORCH_ACCELERATE', 'false').lower() in ('1', 'true', 'yes')
    
    async def _generate(self, prompt: str, **kwargs) -> dict:
        start_time = time.time()
        
        # Try HuggingFace Inference API first
        try:
            return await self._try_inference_api(prompt, **kwargs)
        except Exception as e:
            logger.warning(f"HuggingFace Inference API failed: {e}")
            
            # Fallback to local model
            try:
                return await self._try_local_model(prompt, **kwargs)
            except Exception as e2:
                raise Exception(f"Both HuggingFace API and local model failed: {e2}")
    
    async def _try_inference_api(self, prompt: str, **kwargs) -> dict:
        """Try HuggingFace Inference API."""
        if not self.hf_token:
            raise Exception("HuggingFace API key not found. Set either HUGGINGFACE_API_KEY or HF_TOKEN environment variable.")
        
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                "temperature": kwargs.get('temperature', self.config.temperature),
                "do_sample": True
            }
        }
        
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{self.config.model_id}",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code != 200:
                raise Exception(f"HuggingFace API error {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get('generated_text', '')
            elif isinstance(data, dict):
                content = data.get('generated_text', '')
            else:
                content = str(data)
            
            # Remove the input prompt from the response
            if content.startswith(prompt):
                content = content[len(prompt):].strip()
            
            # Estimate tokens
            tokens_used = len(prompt.split()) + len(content.split())
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost": 0.0,  # HuggingFace API is free
                "type": "FINAL_ANSWER"
            }
            
        except Exception as e:
            raise Exception(f"HuggingFace Inference API failed: {e}")
    
    async def _try_local_model(self, prompt: str, **kwargs) -> dict:
        """Try local HuggingFace model."""
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
            import torch
        except ImportError:
            raise Exception("transformers library not installed. Install with: pip install transformers torch")
        
        if self.pipeline is None:
            try:
                # Try to load the model
                # Respect global device override via env HFORCH_DEVICE (values: 'cuda'|'cpu')
                forced_device = os.getenv('HFORCH_DEVICE')
                if forced_device:
                    device_arg = 'cuda' if forced_device.lower() in ('cuda', 'gpu') else 'cpu'
                else:
                    device_arg = 'cuda' if torch.cuda.is_available() else 'cpu'
                if self.use_accelerate:
                    # Minimal, safe Accelerate usage: device_map="auto". No logic changes.
                    # Avoids manual .prepare(); lets Accelerate shard/place automatically.
                    self.pipeline = pipeline(
                        "text-generation",
                        model=self.config.model_id,
                        tokenizer=self.config.model_id,
                        device_map="auto",
                        torch_dtype=torch.float16 if torch.cuda.is_available() else None
                    )
                else:
                    self.pipeline = pipeline(
                        "text-generation",
                        model=self.config.model_id,
                        tokenizer=self.config.model_id,
                        device=device_arg
                    )
            except Exception as e:
                raise Exception(f"Failed to load local model {self.config.model_id}: {e}")
        
        try:
            # Generate response
            result = self.pipeline(
                prompt,
                max_new_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                do_sample=True,
                pad_token_id=self.pipeline.tokenizer.eos_token_id,
                return_full_text=False
            )
            
            content = result[0]['generated_text']
            
            # Estimate tokens
            tokens_used = len(prompt.split()) + len(content.split())
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost": 0.0,  # Local models are free
                "type": "FINAL_ANSWER"
            }
            
        except Exception as e:
            raise Exception(f"Local model generation failed: {e}")

# Factory function to create providers
def create_provider(config: ModelConfig) -> LLMProvider:
    """Create a provider based on configuration."""
    if config.api_provider == 'openai':
        return OpenAIProvider(config)
    elif config.api_provider == 'anthropic':
        return AnthropicProvider(config)
    elif config.api_provider == 'gemini':
        return GeminiProvider(config)
    elif config.api_provider == 'huggingface':
        return HuggingFaceProvider(config)
    else:
        raise ValueError(f"Unknown API provider: {config.api_provider}") 
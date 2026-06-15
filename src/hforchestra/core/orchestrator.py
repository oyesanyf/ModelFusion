#!/usr/bin/env python3
"""
HuggingFace Orchestrator - Main Orchestration Engine
Integrates all components to provide the complete AI task processing system.
"""

import os
import time
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from .task_processor import UniversalTaskProcessor, TaskResult
from .providers import ModelConfig, create_provider, LLMProvider
from .task_detector import task_detector

logger = logging.getLogger(__name__)

@dataclass
class OrchestrationResult:
    """Result of an orchestration operation."""
    success: bool
    content: str
    task_results: List[TaskResult]
    total_cost: float
    total_tokens: int
    total_latency_ms: float
    models_used: List[str]
    error_message: Optional[str] = None

class HuggingFaceOrchestrator:
    """Main orchestrator that integrates all components."""
    
    def __init__(self, budget: float = 10.0, enable_ml: bool = False, verbose: bool = False):
        self.budget = budget
        self.enable_ml = enable_ml
        self.verbose = verbose
        self.task_processor = UniversalTaskProcessor()
        self.performance_stats = {}
        self.total_cost = 0.0
        self.total_tokens = 0
        
        # Initialize API keys
        self.api_keys = self._load_api_keys()
        # Minimal, non-sensitive API key status output
        all_possible = ['openai', 'anthropic', 'gemini', 'huggingface']
        loaded = [p for p in all_possible if self.api_keys.get(p)]
        missing = [p for p in all_possible if not self.api_keys.get(p)]
        print("OK")
        print("API Keys Loaded:")
        if loaded:
            print("   " + ", ".join(f"{p}: [LOADED]" for p in loaded))
        if missing:
            print("   " + ", ".join(f"{p}: [MISSING]" for p in missing))
        if self.verbose:
            available_apis = list(self.api_keys.keys())
            print(f"Available API providers: {available_apis}")
        
        if self.verbose:
            logger.info(f"Orchestrator initialized with budget: ${budget}, ML: {enable_ml}")
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        keys = {}
        
        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            keys['openai'] = os.getenv('OPENAI_API_KEY')
        
        # Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            keys['anthropic'] = os.getenv('ANTHROPIC_API_KEY')
        
        # Google Gemini
        if os.getenv('GOOGLE_GEMINI_API_KEY'):
            keys['gemini'] = os.getenv('GOOGLE_GEMINI_API_KEY')
        
        # HuggingFace (check both possible environment variable names)
        if os.getenv('HUGGINGFACE_API_KEY'):
            keys['huggingface'] = os.getenv('HUGGINGFACE_API_KEY')
        elif os.getenv('HF_TOKEN'):
            keys['huggingface'] = os.getenv('HF_TOKEN')
        
        return keys
    
    async def process_task(self, prompt: str, **kwargs) -> OrchestrationResult:
        """Process a task using the orchestrator."""
        start_time = time.time()

        
        try:
            # Determine task type from prompt or kwargs
            task_name = kwargs.get('task_name', self._detect_task_type(prompt))
            
            # Check budget (only for OpenAI models - HuggingFace models are free)
            if kwargs.get('use_openai') and self.total_cost >= self.budget:
                return OrchestrationResult(
                    success=False,
                    content="Budget exceeded",
                    task_results=[],
                    total_cost=self.total_cost,
                    total_tokens=self.total_tokens,
                    total_latency_ms=(time.time() - start_time) * 1000,
                    models_used=[],
                    error_message="Budget limit reached (use HuggingFace models for free processing)"
                )
            
            # Process the task
            if kwargs.get('file_path'):
                # File analysis task
                # Remove task_name and file_path from kwargs to avoid duplicate parameters
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop('task_name', None)
                kwargs_copy.pop('file_path', None)
                # Also remove any other potential duplicate keys
                kwargs_copy.pop('prompt', None)
                
                result = await self.task_processor.process_file_analysis(
                    kwargs['file_path'], task_name, prompt, **kwargs_copy
                )
            elif kwargs.get('use_openai'):
                # Use OpenAI models when specifically requested
                result = await self.task_processor.process_task(task_name, prompt, **kwargs)
            else:
                # DEFAULT: Use HuggingFace model selection with langextract
                # Remove task_name from kwargs to avoid duplicate parameter
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop('task_name', None)
                result = await self._process_with_hf_models(task_name, prompt, **kwargs_copy)
            
            # Update statistics
            self.total_cost += result.cost
            self.total_tokens += result.tokens_used
            

            
            # Apply ML enhancements if enabled
            if self.enable_ml:
                result = await self._apply_ml_enhancements(result, prompt, **kwargs)
            
            return OrchestrationResult(
                success=result.status == "success",
                content=result.content,
                task_results=[result],
                total_cost=self.total_cost,
                total_tokens=self.total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                models_used=[result.model_used],
                error_message=result.error_message
            )
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return OrchestrationResult(
                success=False,
                content=f"Error: {str(e)}",
                task_results=[],
                total_cost=self.total_cost,
                total_tokens=self.total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                models_used=[],
                error_message=str(e)
            )
    
    def _detect_task_type(self, prompt: str) -> str:
        """Detect the type of task from the prompt."""
        prompt_lower = prompt.lower()
        
        # Question answering - but distinguish between extractive and generative
        if any(word in prompt_lower for word in ['what is', 'how', 'why', 'when', 'where', 'who']):
            # Check if this is a general knowledge question that should use text-generation
            general_knowledge_patterns = [
                'what is the capital of',
                'what is the population of',
                'who is the president of',
                'when was',
                'where is',
                'how many',
                'what year',
                'what country',
                'what city',
                'what language',
                'what currency',
                'what religion',
                'what is the largest',
                'what is the smallest',
                'what is the oldest',
                'what is the newest'
            ]
            
            # If it matches general knowledge patterns, use text-generation instead
            if any(pattern in prompt_lower for pattern in general_knowledge_patterns):
                return 'text-generation'
            else:
                return 'question-answering'
        
        # Translation
        if any(word in prompt_lower for word in ['translate', 'translation', 'in spanish', 'in french', 'in german']):
            return 'translation'
        
        # Summarization
        if any(word in prompt_lower for word in ['summarize', 'summary', 'brief', 'overview']):
            return 'summarization'
        
        # Sentiment analysis
        if any(word in prompt_lower for word in ['sentiment', 'emotion', 'feeling', 'mood']):
            return 'sentiment-analysis'
        
        # Named entity recognition
        if any(word in prompt_lower for word in ['entities', 'names', 'people', 'organizations', 'locations']):
            return 'ner'
        
        # Spam detection
        if any(word in prompt_lower for word in ['spam', 'legitimate', 'suspicious']):
            return 'spam-detection'
        
        # Malware detection
        if any(word in prompt_lower for word in ['malware', 'malicious', 'safe', 'dangerous']):
            return 'malware-detection'
        
        # PII detection
        if any(word in prompt_lower for word in ['personal', 'private', 'email', 'phone', 'address']):
            return 'pii-detection'
        
        # Default to text generation
        return 'text-generation'
    
    async def process_task_with_model(self, prompt: str, model_id: str, task_name: str = None, sinq_manager=None) -> OrchestrationResult:
        """Process a task with a specific model from the database."""
        start_time = time.time()
        
        try:
            logger.info(f"🚀 [DYNAMIC] Processing task with specific model: {model_id}")
            
            # Check if SINQ quantization should be applied
            quantized_model = None
            quantized_tokenizer = None
            quantization_metadata = {}
            
            if sinq_manager and sinq_manager.enable_sinq:
                try:
                    logger.info(f"🔧 [SINQ] Checking if model {model_id} should be quantized")
                    quantized_model, quantized_tokenizer, quantization_metadata = sinq_manager.process_model_with_sinq(
                        model_id=model_id,
                        task_name=task_name
                    )
                    
                    if quantized_model is not None:
                        logger.info(f"✅ [SINQ] Using quantized model: {model_id}")
                        logger.info(f"📊 [SINQ] Quantization time: {quantization_metadata.get('quantization_time', 0):.2f}s")
                    else:
                        logger.info(f"📋 [SINQ] Using original model: {model_id}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ [SINQ] Failed to quantize model {model_id}: {e}")
                    logger.info(f"🔄 [SINQ] Falling back to original model")
            
            # Create a model config for the specific model
            model_config = ModelConfig(
                name=f"{model_id}_{task_name}",
                api_provider="huggingface",  # Default to HuggingFace for database models
                model_id=model_id,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Add SINQ information to model config if available
            if quantization_metadata.get('quantized', False):
                model_config.quantization_info = quantization_metadata
            
            # Process the task with the specific model
            result = await self.task_processor.process_task(
                task_name or 'text-generation',
                prompt,
                model_config=model_config
            )
            
            # Build orchestration result
            total_latency = (time.time() - start_time) * 1000
            
            return OrchestrationResult(
                success=result.status == "success",
                content=result.content,
                task_results=[result],
                total_cost=0.0,  # HuggingFace models are free
                total_tokens=result.tokens_used,
                total_latency_ms=total_latency,
                models_used=[model_id],
                error_message=result.error_message if result.status != "success" else None
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing task with model {model_id}: {e}")
            return OrchestrationResult(
                success=False,
                content=f"Error processing task: {str(e)}",
                task_results=[],
                total_cost=0.0,
                total_tokens=0,
                total_latency_ms=(time.time() - start_time) * 1000,
                models_used=[model_id],
                error_message=str(e)
            )
    
    async def _process_with_hf_models(self, task_name: str, prompt: str, **kwargs) -> TaskResult:
        """Process task using Hugging Face model selection from database."""
        try:
            logger.info(f"🤖 [ML MODE] Using HuggingFace model selection for task: {task_name}")
            
            # Use langextract to detect task if not provided
            if not task_name or task_name == 'text-generation':
                detection_result = task_detector.detect_task_type(prompt)
                task_name = detection_result.task_type
                logger.info(f"🔍 [LANGEXTRACT] Detected task: {task_name} (confidence: {detection_result.confidence:.2f})")
            
            # Get best models using enhanced model selection
            try:
                from .enhanced_model_selector import EnhancedModelSelector, SelectionStrategy
                selector = EnhancedModelSelector()
                
                # Use enhanced model selection with strategy from kwargs
                strategy_name = kwargs.get('selection_strategy', 'multi_objective')
                strategy_map = {
                    'hyperparameter_tuning': SelectionStrategy.HYPERPARAMETER_TUNING,
                    'cross_validation': SelectionStrategy.CROSS_VALIDATION,
                    'ensemble_methods': SelectionStrategy.ENSEMBLE_METHODS,
                    'multi_objective': SelectionStrategy.MULTI_OBJECTIVE,
                    'bayesian_optimization': SelectionStrategy.BAYESIAN_OPTIMIZATION,
                    'meta_learning': SelectionStrategy.META_LEARNING
                }
                strategy = strategy_map.get(strategy_name, SelectionStrategy.MULTI_OBJECTIVE)
                
                print(f"🔎 [ENHANCED SELECTION] Searching models for task: {task_name} using {strategy.value}")

                selection_result = selector.select_best_model(
                    task_name=task_name,
                    prompt=prompt,
                    strategy=strategy,
                    max_candidates=20,
                    cv_folds=5
                )
                
                # Convert enhanced candidates to the format expected by the rest of the system
                models = []
                for candidate in selection_result.all_candidates[:5]:  # Top 5 for display
                    model_data = {
                        'model_id': candidate.model_id,
                        'pipeline_tag': candidate.pipeline_tag,
                        'downloads': candidate.downloads,
                        'likes': candidate.likes,
                        'decision_score': candidate.decision_score,
                        'capability_score': candidate.capability_score,
                        'efficiency_score': candidate.efficiency_score,
                        'popularity_score': candidate.popularity_score,
                        'description': '',
                        'tags': '[]',
                        'author': candidate.author,
                        'library_name': candidate.library_name,
                        'last_modified': None,
                        'license': candidate.license,
                        'task_keywords': '',
                        'architecture': '',
                        'input_size': '',
                        'num_classes': 0,
                        'model_size_mb': candidate.size_mb,
                        'size_mb': candidate.size_mb,
                        'popularity_score_normalized': candidate.popularity_score_normalized,
                        'engagement_score': candidate.engagement_score,
                        'lightweight_score': candidate.lightweight_score,
                        'task_match_score': candidate.task_match_score,
                        'language': '',
                        'language_details': '',
                        'license_details': '',
                        'base_model': candidate.base_model,
                        'datasets': candidate.datasets,
                        'metrics': candidate.metrics,
                        'widget_data': candidate.widget_data,
                        'model_index': '',
                        'inference_info': candidate.inference_info,
                        'disabled': False
                    }
                    models.append(model_data)
                
                if not models:
                    print(f"⚠️  [WARNING] No HuggingFace models found for task {task_name}, falling back to default")
                    logger.warning(f"No HuggingFace models found for task {task_name}, falling back to default")
                    return await self.task_processor.process_task(task_name, prompt, **kwargs)
                
                # Show enhanced model selection results
                print(f"📋 [ENHANCED CANDIDATES] Found {len(models)} models using {selection_result.selection_strategy.value}:")
                print(f"   ⏱️ Optimization time: {selection_result.optimization_time:.2f}s")
                print(f"   🎯 Confidence: {selection_result.confidence_score:.2f}")
                print(f"   📊 Evaluation metrics: {selection_result.evaluation_metrics}")
                
                for i, model in enumerate(models, 1):
                    score = model.get('decision_score', 0)
                    downloads = model.get('downloads', 0)
                    likes = model.get('likes', 0)
                    popularity_norm = model.get('popularity_score_normalized', 0)
                    engagement = model.get('engagement_score', 0)
                    task_match = model.get('task_match_score', 0)
                    lightweight = model.get('lightweight_score', 0)
                    author = model.get('author', 'Unknown')
                    library = model.get('library_name', 'Unknown')
                    license_info = model.get('license', '')
                    base_model = model.get('base_model', '')
                    size_mb = model.get('size_mb', 0)
                    
                    print(f"   {i}. {model['model_id']}")
                    print(f"      Score: {score:.3f} | Downloads: {downloads:,} | Likes: {likes:,}")
                    print(f"      Author: {author} | Library: {library}")
                    if size_mb > 0:
                        print(f"      Size: {size_mb:.1f}MB | License: {license_info}")
                    if popularity_norm > 0 or engagement > 0:
                        print(f"      Popularity: {popularity_norm:.2f} | Engagement: {engagement:.2f} | Lightweight: {lightweight:.2f}")
                    
                    # Show enhanced selection details if available
                    if i == 1:  # Best model
                        best_candidate = selection_result.all_candidates[0]
                        if best_candidate.cv_score:
                            print(f"      🔄 CV Score: {best_candidate.cv_score:.3f} ± {best_candidate.cv_std:.3f}")
                        if best_candidate.hp_optimized_score:
                            print(f"      🔧 Optimized: {best_candidate.hp_optimized_score:.3f}")
                        if best_candidate.ensemble_score:
                            print(f"      🎯 Ensemble: {best_candidate.ensemble_score:.3f}")
                        if best_candidate.meta_features and 'predicted_score' in best_candidate.meta_features:
                            print(f"      🧠 Meta-Learning: {best_candidate.meta_features['predicted_score']:.3f}")
                
                # Check if we should use true ensemble (multiple models)
                use_true_ensemble = (strategy == SelectionStrategy.ENSEMBLE_METHODS)
                
                if use_true_ensemble:
                    # Use TRUE ensemble - run multiple models and combine outputs
                    print(f"\n🎯 [TRUE ENSEMBLE] Running multiple models and combining outputs...")
                    ensemble_result = await self._run_ensemble_models(
                        task_name, prompt, selection_result.all_candidates[:3], **kwargs
                    )
                    
                    # Apply chain-of-thought to ensemble result if requested
                    print(f"🧠 [DEBUG] Checking chain_of_thought flag: {kwargs.get('chain_of_thought')}")
                    if kwargs.get('chain_of_thought'):
                        print("🧠 [DEBUG] Chain-of-thought requested - applying...")
                        ensemble_result = await self._apply_chain_of_thought(ensemble_result, prompt, **kwargs)
                    else:
                        print("🧠 [DEBUG] Chain-of-thought not requested")
                        # Surface the chain-of-thought output explicitly for user visibility
                        try:
                            print("\n🧠 CHAIN-OF-THOUGHT\n" + "="*50)
                            print(ensemble_result.content)
                            print("="*50)
                        except Exception:
                            pass
                    
                    return ensemble_result
                else:
                    # Use single best model (current behavior)
                    best_model = models[0]
                    best_candidate = selection_result.all_candidates[0]
                    
                    print(f"\n🏆 [ENHANCED SELECTION] Using model: {best_model['model_id']}")
                    print(f"   Strategy: {selection_result.selection_strategy.value}")
                    print(f"   Reasoning: {selection_result.reasoning}")
                    
                    # Show enhanced selection factors
                    selection_factors = []
                    if best_candidate.cv_score:
                        selection_factors.append(f"CV: {best_candidate.cv_score:.3f}")
                    if best_candidate.hp_optimized_score:
                        selection_factors.append(f"Optimized: {best_candidate.hp_optimized_score:.3f}")
                    if best_candidate.ensemble_score:
                        selection_factors.append(f"Ensemble: {best_candidate.ensemble_score:.3f}")
                    if best_candidate.meta_features and 'predicted_score' in best_candidate.meta_features:
                        selection_factors.append(f"Meta-Learning: {best_candidate.meta_features['predicted_score']:.3f}")
                    if best_candidate.meta_features and 'pareto_score' in best_candidate.meta_features:
                        selection_factors.append(f"Pareto: {best_candidate.meta_features['pareto_score']:.3f}")
                    
                    if selection_factors:
                        print(f"   Enhanced factors: {', '.join(selection_factors)}")
                    
                    # Show confidence and optimization details
                    print(f"   Confidence: {selection_result.confidence_score:.2f}")
                    print(f"   Optimization time: {selection_result.optimization_time:.2f}s")
                    
                    if len(models) > 1:
                        second_score = models[1].get('decision_score', 0)
                        best_score = best_model.get('decision_score', 0)
                        score_diff = best_score - second_score
                        if score_diff > 0.1:
                            print(f"   Margin: {score_diff:.3f} points ahead of runner-up")
                        else:
                            print(f"   Note: Close competition (only {score_diff:.3f} points ahead)")
                    logger.info(f"🏆 [SELECTED] Using model: {best_model['model_id']} (score: {best_model.get('decision_score', 0):.3f})")
                    
                    # Process with the selected HuggingFace model
                    print(f"🚀 [PROCESSING] Starting task with model: {best_model['model_id']}")
                    result = await self.process_task_with_model(prompt, best_model['model_id'], task_name)
                
                # Convert OrchestrationResult to TaskResult for consistency
                # HuggingFace models are free, so override cost to 0
                task_result = TaskResult(
                    content=result.content,
                    tokens_used=result.total_tokens,
                    cost=0.0,  # HuggingFace models are free
                    latency_ms=result.total_latency_ms,
                    model_used=best_model['model_id'],
                    status="success" if result.success else "error",
                    error_message=result.error_message
                )
                
                # Apply chain-of-thought to single model result if requested
                print(f"🧠 [DEBUG] Checking chain_of_thought flag: {kwargs.get('chain_of_thought')}")
                if kwargs.get('chain_of_thought'):
                    print("🧠 [DEBUG] Chain-of-thought requested - applying...")
                    task_result = await self._apply_chain_of_thought(task_result, prompt, **kwargs)
                else:
                    print("🧠 [DEBUG] Chain-of-thought not requested")
                    # Surface the chain-of-thought output explicitly for user visibility
                    try:
                        print("\n🧠 CHAIN-OF-THOUGHT\n" + "="*50)
                        print(task_result.content)
                        print("="*50)
                    except Exception:
                        pass
                
                return task_result
                
            except Exception as e:
                logger.error(f"Error with HuggingFace model selection: {e}")
                # Fallback to default processing
                return await self.task_processor.process_task(task_name, prompt, **kwargs)
                
        except Exception as e:
            logger.error(f"Error in _process_with_hf_models: {e}")
            # Fallback to default processing
            return await self.task_processor.process_task(task_name or 'text-generation', prompt, **kwargs)
    
    async def _apply_chain_of_thought(self, result: TaskResult, original_prompt: str, **kwargs) -> TaskResult:
        """Apply chain-of-thought reasoning to improve the result.
        Uses OpenAI when explicitly enabled; otherwise falls back to HuggingFace using the same model used for the answer or a safe default.
        """
        if result.status != "success":
            return result

        try:
            # Create a simple, direct chain-of-thought prompt
            cot_prompt = (
                f"Question: {original_prompt}\n"
                f"Answer: {result.content}\n\n"
                f"Think about this step by step:\n"
                f"1. The question asks for: {original_prompt}\n"
                f"2. My answer is: {result.content}\n"
                f"3. Is this answer correct?\n"
                f"4. What is the final answer?\n\n"
                f"Final answer:"
            )

            use_openai = kwargs.get('use_openai', False)

            if use_openai:
                # OpenAI path (requires API key); allow override via env
                openai_model = os.getenv('OPENAI_COT_MODEL', 'gpt-3.5-turbo')
                cot_result = await self.task_processor.process_task(
                    'text-generation',
                    cot_prompt,
                    model_id=openai_model,
                    max_tokens=200,  # Very short to prevent rambling
                    use_openai=True,
                )
                # Extract content from TaskResult
                cot_content = cot_result.content
                cot_tokens = cot_result.tokens_used
                cot_cost = cot_result.cost
            else:
                # HuggingFace path: reuse the same model if possible, otherwise a small safe default
                # If the model_used is "ensemble", use a specific model instead
                if result.model_used == "ensemble":
                    hf_model_id = os.getenv('HF_COT_MODEL', 'openai-community/gpt2')
                else:
                    hf_model_id = result.model_used or os.getenv('HF_COT_MODEL', 'openai-community/gpt2')
                cot_result = await self.task_processor.process_task(
                    'text-generation',
                    cot_prompt,
                    model_id=hf_model_id,
                    max_tokens=200,  # Very short to prevent rambling
                )
                # Extract content from TaskResult
                cot_content = cot_result.content
                cot_tokens = cot_result.tokens_used
                cot_cost = cot_result.cost

            # Update the result with enhanced content
            result.content = cot_content
            result.tokens_used += cot_tokens
            result.cost += cot_cost

            return result

        except Exception as e:
            logger.warning(f"Chain-of-thought failed: {e}")
            return result
    
    async def _apply_ml_enhancements(self, result: TaskResult, original_prompt: str, **kwargs) -> TaskResult:
        """Apply ML enhancements to improve the result."""
        if result.status != "success":
            return result
        
        try:
            # Apply multiple enhancements
            enhanced_result = await self._apply_quality_check(result, original_prompt)
            enhanced_result = await self._apply_fact_checking(enhanced_result, original_prompt)
            enhanced_result = await self._apply_style_improvement(enhanced_result, original_prompt)
            
            return enhanced_result
            
        except Exception as e:
            logger.warning(f"ML enhancements failed: {e}")
            return result
    
    async def _apply_quality_check(self, result: TaskResult, original_prompt: str) -> TaskResult:
        """Apply quality checking to the result."""
        try:
            quality_prompt = f"""
Rate the quality of this answer on a scale of 1-10 and suggest improvements:

Question: {original_prompt}
Answer: {result.content}

Quality assessment (1-10): 
Suggestions for improvement:
"""
            
            quality_result = await self.task_processor.process_task(
                'text-generation',
                quality_prompt,
                max_tokens=300,
                temperature=0.1
            )
            
            # Add quality assessment to the result
            result.content += f"\n\n--- Quality Assessment ---\n{quality_result.content}"
            result.tokens_used += quality_result.tokens_used
            result.cost += quality_result.cost
            
            return result
            
        except Exception as e:
            logger.warning(f"Quality check failed: {e}")
            return result
    
    async def _apply_fact_checking(self, result: TaskResult, original_prompt: str) -> TaskResult:
        """Apply fact checking to the result."""
        try:
            fact_check_prompt = f"""
Fact-check this answer and identify any potential inaccuracies:

Question: {original_prompt}
Answer: {result.content}

Fact-checking results:
- Accurate statements:
- Potential inaccuracies:
- Sources to verify:
"""
            
            fact_result = await self.task_processor.process_task(
                'text-generation',
                fact_check_prompt,
                max_tokens=400,
                temperature=0.1
            )
            
            # Add fact-checking to the result
            result.content += f"\n\n--- Fact-Checking ---\n{fact_result.content}"
            result.tokens_used += fact_result.tokens_used
            result.cost += fact_result.cost
            
            return result
            
        except Exception as e:
            logger.warning(f"Fact checking failed: {e}")
            return result
    
    async def _apply_style_improvement(self, result: TaskResult, original_prompt: str) -> TaskResult:
        """Apply style improvement to the result."""
        try:
            style_prompt = f"""
Improve the style and clarity of this answer while maintaining accuracy:

Original answer: {result.content}

Improved version:
"""
            
            style_result = await self.task_processor.process_task(
                'text-generation',
                style_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            # Replace content with improved version
            result.content = style_result.content
            result.tokens_used += style_result.tokens_used
            result.cost += style_result.cost
            
            return result
            
        except Exception as e:
            logger.warning(f"Style improvement failed: {e}")
            return result
    
    async def process_multiple_tasks(self, tasks: List[Dict[str, Any]]) -> OrchestrationResult:
        """Process multiple tasks in sequence."""
        start_time = time.time()
        all_results = []
        total_cost = 0.0
        total_tokens = 0
        models_used = []
        
        try:
            for task in tasks:
                # Check budget
                if total_cost >= self.budget:
                    break
                
                # Process individual task
                result = await self.process_task(
                    task['prompt'],
                    task_name=task.get('task_name', 'text-generation'),
                    **task
                )
                
                if result.success:
                    all_results.extend(result.task_results)
                    total_cost += sum(r.cost for r in result.task_results)
                    total_tokens += sum(r.tokens_used for r in result.task_results)
                    models_used.extend(result.models_used)
                
                # Update orchestrator stats
                self.total_cost = total_cost
                self.total_tokens = total_tokens
            
            # Combine all results
            combined_content = "\n\n".join([r.content for r in all_results])
            
            return OrchestrationResult(
                success=len(all_results) > 0,
                content=combined_content,
                task_results=all_results,
                total_cost=total_cost,
                total_tokens=total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                models_used=models_used
            )
            
        except Exception as e:
            logger.error(f"Error processing multiple tasks: {e}")
            return OrchestrationResult(
                success=False,
                content=f"Error: {str(e)}",
                task_results=[],
                total_cost=total_cost,
                total_tokens=total_tokens,
                total_latency_ms=(time.time() - start_time) * 1000,
                models_used=models_used,
                error_message=str(e)
            )
    
    def get_available_tasks(self) -> List[str]:
        """Get list of available tasks."""
        return self.task_processor.get_available_tasks()
    
    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task."""
        return self.task_processor.get_task_info(task_name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'budget_remaining': self.budget - self.total_cost,
            'budget_used_percentage': (self.total_cost / self.budget) * 100 if self.budget > 0 else 0,
            'available_apis': list(self.api_keys.keys()),
            'available_tasks': self.get_available_tasks()
        }
    
    async def _run_ensemble_models(self, task_name: str, prompt: str, candidates: List, **kwargs) -> TaskResult:
        """Run multiple models and combine their outputs for true ensemble."""
        import asyncio
        import time
        
        start_time = time.time()
        print(f"🎯 [ENSEMBLE] Running {len(candidates)} models in parallel...")
        
        # Run all models in parallel
        tasks = []
        for i, candidate in enumerate(candidates):
            model_id = candidate.model_id
            weight = candidate.ensemble_weight or (1.0 / len(candidates))
            print(f"   📊 Model {i+1}: {model_id} (weight: {weight:.3f})")
            
            task = asyncio.create_task(
                self._run_single_model_for_ensemble(task_name, prompt, model_id, weight)
            )
            tasks.append(task)
        
        # Wait for all models to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and combine outputs
        successful_results = []
        failed_models = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   ❌ Model {i+1} failed: {result}")
                failed_models.append(candidates[i].model_id)
            else:
                successful_results.append(result)
                print(f"   ✅ Model {i+1} completed: {result['content'][:50]}...")
        
        if not successful_results:
            return TaskResult(
                content="❌ All ensemble models failed",
                tokens_used=0,
                cost=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                model_used="ensemble_failed",
                status="failed",
                error_message="All ensemble models failed"
            )
        
        # Combine outputs using weighted voting/aggregation
        combined_content = self._combine_ensemble_outputs(successful_results, candidates)
        
        # Calculate total metrics
        total_tokens = sum(r['tokens_used'] for r in successful_results)
        total_cost = sum(r['cost'] for r in successful_results)
        total_latency = (time.time() - start_time) * 1000
        
        # Get all model IDs
        all_models = [r['model_used'] for r in successful_results]
        if failed_models:
            all_models.extend(failed_models)
        
        print(f"🎯 [ENSEMBLE] Combined {len(successful_results)} model outputs")
        print(f"   📊 Total tokens: {total_tokens}")
        print(f"   💰 Total cost: ${total_cost:.4f}")
        print(f"   ⏱️ Total time: {total_latency:.2f}ms")
        
        return TaskResult(
            content=combined_content,
            tokens_used=total_tokens,
            cost=total_cost,
            latency_ms=total_latency,
            model_used="ensemble",
            status="success"
        )
    
    async def _run_single_model_for_ensemble(self, task_name: str, prompt: str, model_id: str, weight: float) -> Dict:
        """Run a single model for ensemble processing."""
        try:
            result = await self.process_task_with_model(prompt, model_id, task_name)
            return {
                'content': result.content,
                'tokens_used': result.total_tokens,
                'cost': result.total_cost,
                'model_used': model_id,
                'weight': weight,
                'success': result.success
            }
        except Exception as e:
            raise e
    
    def _combine_ensemble_outputs(self, results: List[Dict], candidates: List) -> str:
        """Combine multiple model outputs using intelligent aggregation."""
        if len(results) == 1:
            return results[0]['content']
        
        # For text classification tasks, use voting
        if any('classification' in result.get('model_used', '') for result in results):
            return self._combine_classification_outputs(results, candidates)
        
        # For other tasks, use weighted averaging or consensus
        return self._combine_general_outputs(results, candidates)
    
    def _combine_classification_outputs(self, results: List[Dict], candidates: List) -> str:
        """Combine classification outputs using weighted voting."""
        # Extract classification labels (simplified)
        labels = []
        weights = []
        
        for result in results:
            content = result['content'].strip().lower()
            weight = result.get('weight', 1.0)
            
            # Simple label extraction (can be enhanced)
            if 'positive' in content:
                labels.append('Positive')
            elif 'negative' in content:
                labels.append('Negative')
            elif 'neutral' in content:
                labels.append('Neutral')
            else:
                labels.append(content)  # Use as-is
            
            weights.append(weight)
        
        # Weighted voting
        label_counts = {}
        for label, weight in zip(labels, weights):
            label_counts[label] = label_counts.get(label, 0) + weight
        
        # Get the most voted label
        final_label = max(label_counts.items(), key=lambda x: x[1])[0]
        
        # Create detailed ensemble report
        ensemble_report = f"🎯 ENSEMBLE CLASSIFICATION RESULT\n"
        ensemble_report += f"{'='*50}\n"
        ensemble_report += f"Final Prediction: {final_label}\n\n"
        ensemble_report += f"Individual Model Predictions:\n"
        
        for i, (result, candidate) in enumerate(zip(results, candidates)):
            ensemble_report += f"  {i+1}. {candidate.model_id}: {result['content']} (weight: {result.get('weight', 1.0):.3f})\n"
        
        ensemble_report += f"\nVoting Breakdown:\n"
        for label, count in label_counts.items():
            ensemble_report += f"  {label}: {count:.3f} votes\n"
        
        return ensemble_report
    
    def _combine_general_outputs(self, results: List[Dict], candidates: List) -> str:
        """Combine general outputs using consensus or averaging."""
        # For general tasks, show all outputs and create a summary
        combined = f"🎯 ENSEMBLE ANALYSIS RESULT\n"
        combined += f"{'='*50}\n\n"
        
        combined += f"Individual Model Outputs:\n"
        for i, (result, candidate) in enumerate(zip(results, candidates)):
            combined += f"\n📊 Model {i+1}: {candidate.model_id} (weight: {result.get('weight', 1.0):.3f})\n"
            combined += f"{'─'*30}\n"
            combined += f"{result['content']}\n"
        
        combined += f"\n🎯 ENSEMBLE SUMMARY:\n"
        combined += f"{'─'*30}\n"
        
        # Create a consensus summary (simplified)
        all_contents = [r['content'] for r in results]
        combined += f"Combined analysis from {len(results)} models:\n"
        combined += f"• Primary consensus: {all_contents[0]}\n"
        if len(all_contents) > 1:
            combined += f"• Supporting insights from {len(all_contents)-1} additional models\n"
        
        return combined

    def reset_statistics(self):
        """Reset orchestrator statistics."""
        self.total_cost = 0.0
        self.total_tokens = 0
        self.performance_stats = {} 
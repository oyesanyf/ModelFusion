#!/usr/bin/env python3
"""
Image Processing Module - Full Image Analysis Implementation
Implements comprehensive image analysis functionality from the original monolithic code.
"""

import os
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Try to import image processing libraries
try:
    import cv2
    import numpy as np
    from PIL import Image
    import torch
    from transformers import pipeline, AutoImageProcessor, AutoModelForImageClassification
    from sklearn.cluster import KMeans
    MULTIMODAL_AVAILABLE = True
    IMAGE_CLASSIFICATION_AVAILABLE = True
    print("[OK] Image processing libraries available")
except ImportError as e:
    MULTIMODAL_AVAILABLE = False
    IMAGE_CLASSIFICATION_AVAILABLE = False
    print(f"[WARN] Image processing libraries not available: {e}")

from .providers import ModelConfig, LLMProvider


@dataclass
class ImageAnalysisResult:
    """Result of image analysis."""
    success: bool
    content: str
    metadata: Dict[str, Any]
    classification: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    model_used: Optional[str] = None


class ImageClassificationProvider(LLMProvider):
    """Image classification provider using Hugging Face image classification models."""
    
    # Class-level cache for loaded models
    _model_cache = {}
    _cache_lock = asyncio.Lock()
    _loading_models = set()
    
    # Database path for model discovery
    _db_path = "db/hf_models.db"
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.classifier = None
        self.processor = None
        self.model_loaded = False
        
        # Set default model if not specified
        if not self.config.model_id or self.config.model_id == "auto":
            self.config.model_id = self._get_best_model_from_db()
    
    async def _ensure_model_loaded(self):
        """Ensure the image classification model is loaded."""
        if self.model_loaded and self.classifier:
            return
        
        model_id = self.config.model_id
        
        # Check if model is already being loaded
        if model_id in self._loading_models:
            # Wait for the model to finish loading
            while model_id in self._loading_models:
                await asyncio.sleep(0.1)
            if model_id in self._model_cache:
                self.classifier = self._model_cache[model_id]
                self.model_loaded = True
                return
        
        # Check if model is already cached
        if model_id in self._model_cache:
            self.classifier = self._model_cache[model_id]
            self.model_loaded = True
            return
        
        # Load the model
        async with self._cache_lock:
            if model_id in self._model_cache:
                self.classifier = self._model_cache[model_id]
                self.model_loaded = True
                return
            
            if model_id in self._loading_models:
                # Wait for loading to complete
                while model_id in self._loading_models:
                    await asyncio.sleep(0.1)
                if model_id in self._model_cache:
                    self.classifier = self._model_cache[model_id]
                    self.model_loaded = True
                    return
            
            # Start loading
            self._loading_models.add(model_id)
            
            try:
                if not IMAGE_CLASSIFICATION_AVAILABLE:
                    raise ImportError("Image classification libraries not available")
                
                print(f"[REFRESH] Loading image classification model: {model_id}")
                
                # Load model with timeout protection
                import concurrent.futures
                
                def load_classifier():
                    try:
                        return pipeline("image-classification", model=model_id)
                    except Exception as e:
                        print(f"[WARN] Failed to load {model_id}: {e}")
                        # Try fallback models
                        fallback_models = ["google/vit-base-patch16-224", "microsoft/resnet-50"]
                        for fallback_id in fallback_models:
                            if fallback_id != model_id:
                                try:
                                    print(f"[REFRESH] Trying fallback model: {fallback_id}")
                                    return pipeline("image-classification", model=fallback_id)
                                except Exception as fallback_e:
                                    print(f"[WARN] Fallback {fallback_id} failed: {fallback_e}")
                                    continue
                        raise Exception(f"All image classification models failed to load")
                
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    self.classifier = await asyncio.wait_for(
                        loop.run_in_executor(executor, load_classifier),
                        timeout=30.0  # 30 second timeout
                    )
                
                # Cache the model
                self._model_cache[model_id] = self.classifier
                self.model_loaded = True
                print(f"[OK] Image classification model loaded: {model_id}")
                
            except Exception as e:
                print(f"[ERROR] Failed to load image classification model {model_id}: {e}")
                raise e
            finally:
                self._loading_models.discard(model_id)
    
    async def classify_image(self, image_path: Path, top_k: int = 5) -> Dict[str, Any]:
        """Classify an image and return top predictions."""
        try:
            await self._ensure_model_loaded()
            
            if not self.classifier:
                return {
                    'error': 'Image classification model not loaded',
                    'predictions': [],
                    'model_used': self.config.model_id
                }
            
            # Load and preprocess image
            if not MULTIMODAL_AVAILABLE:
                return {
                    'error': 'PIL not available for image loading',
                    'predictions': [],
                    'model_used': self.config.model_id
                }
            
            # Classify image with timeout protection
            import concurrent.futures
            
            def classify_with_timeout():
                try:
                    return self.classifier(str(image_path), top_k=top_k)
                except Exception as e:
                    print(f"[WARN] Classification failed: {e}")
                    return []
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                predictions = await asyncio.wait_for(
                    loop.run_in_executor(executor, classify_with_timeout),
                    timeout=30.0  # 30 second timeout
                )
            
            return {
                'predictions': predictions,
                'model_used': self.config.model_id,
                'top_k': top_k,
                'image_path': str(image_path)
            }
            
        except Exception as e:
            return {
                'error': f'Image classification failed: {str(e)}',
                'predictions': [],
                'model_used': self.config.model_id
            }
    
    async def _generate(self, prompt: str, **kwargs) -> dict:
        """Generate response - not applicable for image classification."""
        return {
            "content": "Image classification provider does not support text generation",
            "tokens_used": 0,
            "cost": 0.0
        }
    
    @classmethod
    def get_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get list of available image classification models from database."""
        return cls._get_models_from_db()
    
    @classmethod
    def _get_models_from_db(cls) -> Dict[str, Dict[str, Any]]:
        """Get image classification models from database."""
        try:
            import sqlite3
            with sqlite3.connect(cls._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT model_id, author, pipeline_tag, tags, description, downloads, 
                           likes, last_modified, license, task_keywords, decision_score,
                           capability_score, efficiency_score, popularity_score
                    FROM models 
                    WHERE pipeline_tag = "image-classification"
                    ORDER BY decision_score DESC
                ''')
                
                models = {}
                for row in cursor.fetchall():
                    model_data = {
                        'model_id': row[0],
                        'author': row[1],
                        'pipeline_tag': row[2],
                        'tags': json.loads(row[3]) if row[3] else [],
                        'description': row[4],
                        'downloads': row[5],
                        'likes': row[6],
                        'last_modified': row[7],
                        'license': row[8],
                        'task_keywords': json.loads(row[9]) if row[9] else [],
                        'decision_score': row[10],
                        'capability_score': row[11],
                        'efficiency_score': row[12],
                        'popularity_score': row[13]
                    }
                    models[row[0]] = model_data
                
                return models
        except Exception as e:
            print(f"[WARN] Failed to load models from database: {e}")
            # Dynamic fallback to basic models
            fallback_model = os.getenv('DEFAULT_IMAGE_MODEL', 'google/vit-base-patch16-224')
            return {
                fallback_model: {
                    'model_id': fallback_model,
                    'decision_score': 0.85
                }
            }
    
    def _get_best_model_from_db(self) -> str:
        """Get the best image classification model from database with intelligent selection."""
        models = self._get_models_from_db()
        if models:
            # Sort by decision score and get top models
            sorted_models = sorted(models.items(), 
                                 key=lambda x: x[1].get('decision_score', 0), 
                                 reverse=True)
            return sorted_models[0][0]
        
        # Fallback to default model
        return os.getenv('DEFAULT_IMAGE_MODEL', 'google/vit-base-patch16-224')


class ImageProcessor:
    """Comprehensive image processing and analysis."""
    
    def __init__(self):
        self.classification_provider = None
        self._init_classification_provider()
    
    def _init_classification_provider(self):
        """Initialize the image classification provider."""
        try:
            config = ModelConfig(
                name="image_classifier",
                api_provider="image_classification",
                model_id="google/vit-base-patch16-224"
            )
            self.classification_provider = ImageClassificationProvider(config)
        except Exception as e:
            print(f"[WARN] Failed to initialize image classification provider: {e}")
    
    async def analyze_image_file(self, file_path: Path, include_classification: bool = True) -> Dict[str, Any]:
        """
        Analyze image files and extract comprehensive metadata, features, and classification.
        """
        if not MULTIMODAL_AVAILABLE:
            return {
                'error': 'Multimodal processing libraries not available',
                'suggestion': 'Install with: pip install opencv-python pillow'
            }
        
        try:
            # Load image with PIL
            with Image.open(file_path) as img:
                # Basic metadata
                width, height = img.size
                mode = img.mode
                format_name = img.format
                
                # Convert to RGB if needed for analysis
                if mode != 'RGB':
                    img_rgb = img.convert('RGB')
                else:
                    img_rgb = img
                
                # Convert to numpy array for OpenCV analysis
                img_array = np.array(img_rgb)
                
                # Color analysis
                mean_color = np.mean(img_array, axis=(0, 1))
                std_color = np.std(img_array, axis=(0, 1))
                
                # Brightness analysis
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                brightness = np.mean(gray)
                contrast = np.std(gray)
                
                # Edge detection for complexity analysis
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / (width * height)
                
                # Dominant colors using k-means
                pixels = img_array.reshape(-1, 3)
                kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
                kmeans.fit(pixels)
                dominant_colors = kmeans.cluster_centers_.astype(int)
                
                # File size
                file_size = file_path.stat().st_size
                
                # Base analysis result
                analysis_result = {
                    'type': 'image',
                    'format': format_name,
                    'dimensions': f'{width}x{height}',
                    'width': width,
                    'height': height,
                    'mode': mode,
                    'file_size_bytes': file_size,
                    'file_size_mb': file_size / (1024 * 1024),
                    'brightness': float(brightness),
                    'contrast': float(contrast),
                    'edge_density': float(edge_density),
                    'mean_color_rgb': mean_color.tolist(),
                    'std_color_rgb': std_color.tolist(),
                    'dominant_colors': dominant_colors.tolist(),
                    'aspect_ratio': width / height,
                    'total_pixels': width * height,
                    'analysis_method': 'opencv_pil_analysis'
                }
                
                # Add image classification if requested and available
                if include_classification and self.classification_provider:
                    try:
                        print("[TARGET] Performing image classification...")
                        
                        # Perform classification
                        classification_result = await self.classification_provider.classify_image(file_path, top_k=5)
                        
                        print(f"[SEARCH] Classification result: {classification_result}")
                        
                        if 'error' not in classification_result:
                            predictions = classification_result.get('predictions', [])
                            model_used = classification_result.get('model_used', 'unknown')
                            
                            print(f"[OK] Classification successful! Found {len(predictions)} predictions using {model_used}")
                            
                            # Store classification results prominently
                            analysis_result['classification'] = {
                                'predictions': predictions,
                                'model_used': model_used,
                                'top_k': classification_result.get('top_k', 5),
                                'model_selection_method': 'dynamic_database_selection',
                                'success': True
                            }
                            analysis_result['analysis_method'] = 'opencv_pil_analysis_with_dynamic_classification'
                            
                            # Also add to main analysis for easy access
                            analysis_result['ai_classification'] = {
                                'predictions': [
                                    {'label': pred.get('label', 'unknown'), 'confidence': pred.get('score', 0)*100} 
                                    for pred in predictions
                                ],
                                'model_used': model_used,
                                'success': True
                            }
                            
                            # Print the results for debugging
                            if predictions:
                                print(f"[TARGET] Top classification results:")
                                for i, pred in enumerate(predictions[:3], 1):
                                    label = pred.get('label', 'unknown') 
                                    score = pred.get('score', 0)
                                    print(f"   {i}. {label}: {score:.3f}")
                            
                        else:
                            print(f"[ERROR] Classification failed: {classification_result['error']}")
                            analysis_result['classification_error'] = classification_result['error']
                            
                    except Exception as e:
                        analysis_result['classification_error'] = f'Classification failed: {str(e)}'
                
                return analysis_result
                
        except Exception as e:
            return {
                'error': f'Image analysis failed: {str(e)}',
                'type': 'image',
                'analysis_method': 'failed'
            }
    
    async def process_image_analysis(self, file_path: str, prompt: str = None) -> ImageAnalysisResult:
        """Process image analysis with comprehensive results."""
        start_time = time.time()
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return ImageAnalysisResult(
                    success=False,
                    content="Image file not found",
                    metadata={},
                    error_message=f"File not found: {file_path}"
                )
            
            # Analyze the image
            analysis = await self.analyze_image_file(file_path, include_classification=True)
            
            if 'error' in analysis:
                return ImageAnalysisResult(
                    success=False,
                    content=f"Image analysis failed: {analysis['error']}",
                    metadata=analysis,
                    error_message=analysis['error']
                )
            
            # Generate comprehensive response
            response_parts = []
            
            # Basic image information
            response_parts.append(f"📸 **Image Analysis Results**")
            response_parts.append(f"")
            response_parts.append(f"**File Information:**")
            response_parts.append(f"- Format: {analysis.get('format', 'Unknown')}")
            response_parts.append(f"- Dimensions: {analysis.get('dimensions', 'Unknown')}")
            response_parts.append(f"- File Size: {analysis.get('file_size_mb', 0):.2f} MB")
            response_parts.append(f"- Aspect Ratio: {analysis.get('aspect_ratio', 0):.2f}")
            
            # Technical analysis
            response_parts.append(f"")
            response_parts.append(f"**Technical Analysis:**")
            response_parts.append(f"- Brightness: {analysis.get('brightness', 0):.1f}/255")
            response_parts.append(f"- Contrast: {analysis.get('contrast', 0):.1f}")
            response_parts.append(f"- Edge Density: {analysis.get('edge_density', 0):.3f}")
            
            # AI Classification results
            if 'ai_classification' in analysis and analysis['ai_classification'].get('success'):
                response_parts.append(f"")
                response_parts.append(f"**AI Classification Results:**")
                response_parts.append(f"- Model Used: {analysis['ai_classification']['model_used']}")
                response_parts.append(f"")
                
                predictions = analysis['ai_classification']['predictions']
                for i, pred in enumerate(predictions[:5], 1):
                    label = pred['label']
                    confidence = pred['confidence']
                    response_parts.append(f"{i}. **{label}** ({confidence:.1f}%)")
                
                # Answer the user's question if provided
                if prompt:
                    response_parts.append(f"")
                    response_parts.append(f"**Answer to your question:**")
                    if "what is this" in prompt.lower() or "what's in this" in prompt.lower():
                        top_prediction = predictions[0] if predictions else None
                        if top_prediction:
                            response_parts.append(f"This image appears to be a **{top_prediction['label']}** with {top_prediction['confidence']:.1f}% confidence.")
                        else:
                            response_parts.append("I couldn't determine what's in this image with high confidence.")
                    else:
                        response_parts.append(f"Based on the analysis, this image shows: {predictions[0]['label'] if predictions else 'unknown content'}")
            
            elif 'classification_error' in analysis:
                response_parts.append(f"")
                response_parts.append(f"**Classification Error:** {analysis['classification_error']}")
            
            processing_time = (time.time() - start_time) * 1000
            
            return ImageAnalysisResult(
                success=True,
                content="\n".join(response_parts),
                metadata=analysis,
                classification=analysis.get('ai_classification'),
                processing_time_ms=processing_time,
                model_used=analysis.get('ai_classification', {}).get('model_used')
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return ImageAnalysisResult(
                success=False,
                content=f"Error processing image: {str(e)}",
                metadata={},
                error_message=str(e),
                processing_time_ms=processing_time
            )


# Global instance for easy access
image_processor = ImageProcessor() 
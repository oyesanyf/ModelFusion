#!/usr/bin/env python3
"""
SINQ Quantization Integration for HFOrchestra

This module provides SINQ (Sinkhorn-Normalized Quantization) integration
for quantizing Hugging Face models to reduce memory usage while preserving accuracy.
"""

import os
import sys
import logging
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

# Check if SINQ is available
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from sinq.patch_model import AutoSINQHFModel
    from sinq.sinqlinear import BaseQuantizeConfig
    SINQ_AVAILABLE = True
    logger.info("✅ SINQ quantization library is available")
except ImportError as e:
    SINQ_AVAILABLE = False
    logger.warning(f"⚠️ SINQ quantization library not available: {e}")
    logger.info("💡 Install SINQ with: pip install git+https://github.com/huawei-csl/SINQ.git")


class SINQQuantizationConfig:
    """Configuration for SINQ quantization parameters."""
    
    def __init__(self, 
                 nbits: int = 4,
                 group_size: int = 64,
                 tiling_mode: str = "1D",
                 method: str = "sinq",
                 compute_dtype: str = "bfloat16",
                 device: str = "cuda:0"):
        """
        Initialize SINQ quantization configuration.
        
        Args:
            nbits: Bit-width for weight quantization (2, 3, 4, 5, 6, 8)
            group_size: Weights per quantization group (64, 128)
            tiling_mode: Weight matrix tiling strategy ("1D", "2D")
            method: Quantization method ("sinq" for calibration-free, "asinq" for calibrated)
            compute_dtype: Compute dtype for quantization
            device: Device to use for quantization
        """
        self.nbits = nbits
        self.group_size = group_size
        self.tiling_mode = tiling_mode
        self.method = method
        self.compute_dtype = compute_dtype
        self.device = device
        
        # Validate parameters
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters."""
        if self.nbits not in [2, 3, 4, 5, 6, 8]:
            raise ValueError(f"Invalid nbits: {self.nbits}. Must be one of [2, 3, 4, 5, 6, 8]")
        
        if self.group_size not in [64, 128]:
            raise ValueError(f"Invalid group_size: {self.group_size}. Must be one of [64, 128]")
        
        if self.tiling_mode not in ["1D", "2D"]:
            raise ValueError(f"Invalid tiling_mode: {self.tiling_mode}. Must be one of ['1D', '2D']")
        
        if self.method not in ["sinq", "asinq"]:
            raise ValueError(f"Invalid method: {self.method}. Must be one of ['sinq', 'asinq']")
    
    def to_quantize_config(self) -> 'BaseQuantizeConfig':
        """Convert to SINQ BaseQuantizeConfig object."""
        if not SINQ_AVAILABLE:
            raise ImportError("SINQ library not available")
        
        return BaseQuantizeConfig(
            nbits=self.nbits,
            group_size=self.group_size,
            tiling_mode=self.tiling_mode,
            method=self.method
        )
    
    def __str__(self) -> str:
        return f"SINQConfig(nbits={self.nbits}, group_size={self.group_size}, tiling_mode='{self.tiling_mode}', method='{self.method}')"


class SINQQuantizer:
    """SINQ quantization manager for Hugging Face models."""
    
    def __init__(self, config: Optional[SINQQuantizationConfig] = None):
        """
        Initialize SINQ quantizer.
        
        Args:
            config: SINQ quantization configuration
        """
        if not SINQ_AVAILABLE:
            raise ImportError("SINQ library not available. Install with: pip install git+https://github.com/huawei-csl/SINQ.git")
        
        self.config = config or SINQQuantizationConfig()
        self.quantized_models_cache = {}  # Cache for quantized models
        logger.info(f"🔧 SINQ Quantizer initialized with config: {self.config}")
    
    def is_model_quantizable(self, model_id: str) -> bool:
        """
        Check if a model can be quantized with SINQ.
        
        Args:
            model_id: Hugging Face model ID
            
        Returns:
            True if model can be quantized, False otherwise
        """
        try:
            # Check if model is a causal LM (most common for SINQ)
            model_info = AutoModelForCausalLM.from_pretrained(
                model_id, 
                torch_dtype=torch.bfloat16,
                device_map="cpu",  # Load to CPU first to check
                trust_remote_code=True
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ Model {model_id} may not be quantizable: {e}")
            return False
    
    def quantize_model(self, 
                      model_id: str, 
                      tokenizer_id: Optional[str] = None,
                      save_dir: Optional[str] = None,
                      force_reload: bool = False) -> Tuple[Any, Any]:
        """
        Quantize a Hugging Face model using SINQ.
        
        Args:
            model_id: Hugging Face model ID
            tokenizer_id: Tokenizer ID (defaults to model_id)
            save_dir: Directory to save quantized model (optional)
            force_reload: Force reload even if cached
            
        Returns:
            Tuple of (quantized_model, tokenizer)
        """
        if not SINQ_AVAILABLE:
            raise ImportError("SINQ library not available")
        
        tokenizer_id = tokenizer_id or model_id
        
        # Check cache first
        cache_key = f"{model_id}_{self.config.nbits}_{self.config.group_size}_{self.config.tiling_mode}_{self.config.method}"
        if not force_reload and cache_key in self.quantized_models_cache:
            logger.info(f"📦 Using cached quantized model: {model_id}")
            return self.quantized_models_cache[cache_key]
        
        logger.info(f"🔄 Quantizing model: {model_id}")
        logger.info(f"⚙️ Configuration: {self.config}")
        
        start_time = time.time()
        
        try:
            # Load model and tokenizer
            logger.info(f"📥 Loading model and tokenizer: {model_id}")
            model = AutoModelForCausalLM.from_pretrained(
                model_id, 
                torch_dtype=torch.bfloat16,
                device_map="cpu",  # Load to CPU first
                trust_remote_code=True
            )
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
            
            # Create quantization config
            quant_config = self.config.to_quantize_config()
            
            # Quantize the model
            logger.info(f"🔧 Applying SINQ quantization...")
            AutoSINQHFModel.quantize_model(
                model,
                tokenizer=tokenizer,
                quant_config=quant_config,
                compute_dtype=getattr(torch, self.config.compute_dtype),
                device=self.config.device
            )
            
            quantization_time = time.time() - start_time
            logger.info(f"✅ Model quantized successfully in {quantization_time:.2f} seconds")
            
            # Cache the quantized model
            self.quantized_models_cache[cache_key] = (model, tokenizer)
            
            # Save quantized model if requested
            if save_dir:
                self.save_quantized_model(model, tokenizer, save_dir)
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"❌ Failed to quantize model {model_id}: {e}")
            raise
    
    def save_quantized_model(self, model: Any, tokenizer: Any, save_dir: str):
        """
        Save quantized model to disk.
        
        Args:
            model: Quantized model
            tokenizer: Tokenizer
            save_dir: Directory to save to
        """
        if not SINQ_AVAILABLE:
            raise ImportError("SINQ library not available")
        
        try:
            logger.info(f"💾 Saving quantized model to: {save_dir}")
            AutoSINQHFModel.save_quantized(model, save_dir, verbose=True)
            logger.info(f"✅ Quantized model saved successfully")
        except Exception as e:
            logger.error(f"❌ Failed to save quantized model: {e}")
            raise
    
    def load_quantized_model(self, save_dir: str) -> Tuple[Any, Any]:
        """
        Load quantized model from disk.
        
        Args:
            save_dir: Directory containing quantized model
            
        Returns:
            Tuple of (quantized_model, tokenizer)
        """
        if not SINQ_AVAILABLE:
            raise ImportError("SINQ library not available")
        
        try:
            logger.info(f"📥 Loading quantized model from: {save_dir}")
            model = AutoSINQHFModel.from_quantized(
                save_dir,
                device=self.config.device,
                compute_dtype=getattr(torch, self.config.compute_dtype)
            )
            
            # Load tokenizer separately
            tokenizer = AutoTokenizer.from_pretrained(save_dir)
            
            logger.info(f"✅ Quantized model loaded successfully")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"❌ Failed to load quantized model: {e}")
            raise
    
    def get_quantization_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get information about quantization for a model.
        
        Args:
            model_id: Hugging Face model ID
            
        Returns:
            Dictionary with quantization information
        """
        return {
            "model_id": model_id,
            "sinq_available": SINQ_AVAILABLE,
            "config": {
                "nbits": self.config.nbits,
                "group_size": self.config.group_size,
                "tiling_mode": self.config.tiling_mode,
                "method": self.config.method,
                "compute_dtype": self.config.compute_dtype,
                "device": self.config.device
            },
            "cached_models": list(self.quantized_models_cache.keys()),
            "is_quantizable": self.is_model_quantizable(model_id) if SINQ_AVAILABLE else False
        }


class SINQIntegrationManager:
    """Manager for integrating SINQ quantization into the HFOrchestra workflow."""
    
    def __init__(self, 
                 enable_sinq: bool = False,
                 config: Optional[SINQQuantizationConfig] = None):
        """
        Initialize SINQ integration manager.
        
        Args:
            enable_sinq: Whether SINQ quantization is enabled
            config: SINQ quantization configuration
        """
        self.enable_sinq = enable_sinq
        self.config = config or SINQQuantizationConfig()
        self.quantizer = None
        
        if self.enable_sinq and SINQ_AVAILABLE:
            self.quantizer = SINQQuantizer(self.config)
            logger.info(f"🚀 SINQ integration enabled with config: {self.config}")
        elif self.enable_sinq and not SINQ_AVAILABLE:
            logger.warning("⚠️ SINQ requested but library not available. Install with: pip install git+https://github.com/huawei-csl/SINQ.git")
            self.enable_sinq = False
    
    def should_quantize_model(self, model_id: str, task_name: str = None) -> bool:
        """
        Determine if a model should be quantized.
        
        Args:
            model_id: Hugging Face model ID
            task_name: Task name (optional)
            
        Returns:
            True if model should be quantized
        """
        if not self.enable_sinq or not self.quantizer:
            return False
        
        # Check if model is quantizable
        if not self.quantizer.is_model_quantizable(model_id):
            logger.info(f"📋 Model {model_id} is not suitable for SINQ quantization")
            return False
        
        # For now, quantize all suitable models
        # In the future, this could be made more selective based on model size, task, etc.
        return True
    
    def process_model_with_sinq(self, 
                               model_id: str, 
                               tokenizer_id: Optional[str] = None,
                               task_name: str = None) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        Process a model with SINQ quantization if enabled.
        
        Args:
            model_id: Hugging Face model ID
            tokenizer_id: Tokenizer ID (optional)
            task_name: Task name (optional)
            
        Returns:
            Tuple of (model, tokenizer, metadata)
        """
        metadata = {
            "model_id": model_id,
            "sinq_enabled": self.enable_sinq,
            "quantized": False,
            "quantization_time": 0.0,
            "config": None
        }
        
        if not self.should_quantize_model(model_id, task_name):
            logger.info(f"📋 Using original model: {model_id}")
            return None, None, metadata
        
        logger.info(f"🔧 Processing model with SINQ: {model_id}")
        
        try:
            start_time = time.time()
            
            # Quantize the model
            model, tokenizer = self.quantizer.quantize_model(
                model_id=model_id,
                tokenizer_id=tokenizer_id
            )
            
            quantization_time = time.time() - start_time
            
            metadata.update({
                "quantized": True,
                "quantization_time": quantization_time,
                "config": {
                    "nbits": self.config.nbits,
                    "group_size": self.config.group_size,
                    "tiling_mode": self.config.tiling_mode,
                    "method": self.config.method
                }
            })
            
            logger.info(f"✅ Model processed with SINQ in {quantization_time:.2f} seconds")
            return model, tokenizer, metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to process model with SINQ: {e}")
            metadata["error"] = str(e)
            return None, None, metadata
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current SINQ integration status."""
        return {
            "sinq_available": SINQ_AVAILABLE,
            "sinq_enabled": self.enable_sinq,
            "config": {
                "nbits": self.config.nbits,
                "group_size": self.config.group_size,
                "tiling_mode": self.config.tiling_mode,
                "method": self.config.method,
                "compute_dtype": self.config.compute_dtype,
                "device": self.config.device
            } if self.config else None,
            "quantizer_initialized": self.quantizer is not None
        }


# Global SINQ integration manager instance
_sinq_manager: Optional[SINQIntegrationManager] = None


def initialize_sinq_integration(enable_sinq: bool = False, **config_kwargs) -> SINQIntegrationManager:
    """
    Initialize global SINQ integration manager.
    
    Args:
        enable_sinq: Whether to enable SINQ quantization
        **config_kwargs: Configuration parameters for SINQ
        
    Returns:
        SINQIntegrationManager instance
    """
    global _sinq_manager
    
    config = SINQQuantizationConfig(**config_kwargs) if config_kwargs else None
    _sinq_manager = SINQIntegrationManager(enable_sinq=enable_sinq, config=config)
    
    return _sinq_manager


def get_sinq_manager() -> Optional[SINQIntegrationManager]:
    """Get the global SINQ integration manager."""
    return _sinq_manager


def is_sinq_available() -> bool:
    """Check if SINQ is available."""
    return SINQ_AVAILABLE


def get_sinq_info() -> Dict[str, Any]:
    """Get SINQ availability and configuration information."""
    info = {
        "sinq_available": SINQ_AVAILABLE,
        "sinq_enabled": False,
        "manager_initialized": _sinq_manager is not None
    }
    
    if _sinq_manager:
        info.update(_sinq_manager.get_integration_status())
    
    return info

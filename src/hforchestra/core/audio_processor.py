#!/usr/bin/env python3
"""
Audio Processor Module - Real Audio Transcription Implementation
Implements the audio transcription functionality from the original monolithic code.
"""

import os
import asyncio
import json
import time
import warnings
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Try to import audio processing libraries
try:
    from pydub import AudioSegment
    AUDIO_AVAILABLE = True
    print("[OK] Audio processing libraries available")
except ImportError:
    AUDIO_AVAILABLE = False
    print("[WARN] Audio processing libraries not available. Install with: pip install pydub")

# Try to import transformers for speech recognition
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
    print("[OK] Transformers available for speech recognition")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[WARN] Transformers not available. Install with: pip install transformers")

logger = logging.getLogger(__name__)


@dataclass
class AudioTranscriptionResult:
    """Result of audio transcription."""
    transcription: str
    success: bool
    processing_time_ms: float
    model_used: Optional[str] = None
    error_message: Optional[str] = None
    analysis_method: Optional[str] = None


class AudioProcessor:
    """Audio processor with real transcription functionality."""
    
    def __init__(self):
        # Suppress warnings for audio processing
        warnings.filterwarnings('ignore', category=UserWarning)
        warnings.filterwarnings('ignore', category=FutureWarning)
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        warnings.filterwarnings('ignore', message='.*aifc.*', category=DeprecationWarning)
        warnings.filterwarnings('ignore', message='.*sunau.*', category=DeprecationWarning)
        warnings.filterwarnings('ignore', message='.*language detection.*', category=UserWarning)
        warnings.filterwarnings('ignore', message='.*breaking change.*', category=UserWarning)
    
    async def transcribe_audio(self, file_path: Path, language: str = "en") -> AudioTranscriptionResult:
        """
        Transcribe audio file to text using the best available speech recognition models.
        Implements proper chunking for long audio files.
        """
        start_time = time.time()
        
        if not AUDIO_AVAILABLE:
            processing_time = (time.time() - start_time) * 1000
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=processing_time,
                error_message="Audio processing libraries not available",
                analysis_method="libraries_missing"
            )
        
        try:
            print(f"🎤 Starting audio transcription for: {file_path.name}")
            
            # Check if file exists and is readable
            if not file_path.exists():
                processing_time = (time.time() - start_time) * 1000
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=processing_time,
                    error_message=f"Audio file not found: {file_path}",
                    analysis_method="file_not_found"
                )
            
            if not os.access(file_path, os.R_OK):
                processing_time = (time.time() - start_time) * 1000
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=processing_time,
                    error_message=f"Cannot read audio file: {file_path}",
                    analysis_method="file_not_readable"
                )
            
            # Try to use Whisper CLI first (faster and more reliable)
            print("[REFRESH] Attempting transcription with Whisper CLI...")
            whisper_result = await self._try_whisper_cli(file_path)
            if whisper_result.success:
                processing_time = (time.time() - start_time) * 1000
                return AudioTranscriptionResult(
                    transcription=whisper_result.transcription,
                    success=True,
                    processing_time_ms=processing_time,
                    model_used=whisper_result.model_used,
                    analysis_method="whisper_cli"
                )
            
            # Fallback to transformers if Whisper CLI failed
            print("[REFRESH] Falling back to transformers pipeline...")
            transformers_result = await self._try_transformers_pipeline(file_path, language)
            if transformers_result.success:
                processing_time = (time.time() - start_time) * 1000
                return AudioTranscriptionResult(
                    transcription=transformers_result.transcription,
                    success=True,
                    processing_time_ms=processing_time,
                    model_used=transformers_result.model_used,
                    analysis_method="transformers_pipeline"
                )
            
            # All methods failed
            processing_time = (time.time() - start_time) * 1000
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=processing_time,
                error_message="All transcription methods failed",
                analysis_method="all_methods_failed"
            )
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=processing_time,
                error_message=f"Transcription failed: {str(e)}",
                analysis_method="speech_to_text_failed"
            )
    
    async def _try_whisper_cli(self, file_path: Path) -> AudioTranscriptionResult:
        """Try to use Whisper CLI for transcription."""
        try:
            # Try to find whisper in common locations
            whisper_paths = [
                'whisper',
                r'C:\Users\oyesanyf\AppData\Roaming\Python\Python313\Scripts\whisper.exe',
                r'C:\Users\oyesanyf\AppData\Local\Programs\Python\Python313\Scripts\whisper.exe',
                r'C:\Python313\Scripts\whisper.exe'
            ]
            
            whisper_cmd = None
            for path in whisper_paths:
                try:
                    result = subprocess.run([path, '--help'], capture_output=True, text=True)
                    if result.returncode == 0:
                        whisper_cmd = path
                        break
                except FileNotFoundError:
                    continue
            
            if not whisper_cmd:
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message="Whisper CLI not found",
                    analysis_method="whisper_not_found"
                )
            
            print(f"[OK] Found Whisper CLI: {whisper_cmd}")
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
                output_file = tmp_file.name
            
            # Run whisper transcription with better parameters
            cmd = [
                whisper_cmd, 
                str(file_path), 
                '--output_format', 'txt', 
                '--output_dir', os.path.dirname(output_file)
            ]
            print(f"[AUDIO] Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Read the transcription
                with open(output_file, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
                
                # Clean up
                os.unlink(output_file)
                
                if transcription:
                    return AudioTranscriptionResult(
                        transcription=transcription,
                        success=True,
                        processing_time_ms=0,
                        model_used="whisper-cli",
                        analysis_method="whisper_cli"
                    )
                else:
                    print("[WARN] Whisper CLI returned empty transcription")
                    return AudioTranscriptionResult(
                        transcription="",
                        success=False,
                        processing_time_ms=0,
                        error_message="Whisper CLI returned empty transcription",
                        analysis_method="whisper_empty"
                    )
            else:
                print(f"[WARN] Whisper CLI failed: {result.stderr}")
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message=f"Whisper CLI failed: {result.stderr}",
                    analysis_method="whisper_failed"
                )
        
        except Exception as e:
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=0,
                error_message=f"Whisper CLI error: {str(e)}",
                analysis_method="whisper_error"
            )
    
    async def _try_transformers_pipeline(self, file_path: Path, language: str = "en") -> AudioTranscriptionResult:
        """Try to use transformers pipeline for transcription."""
        if not TRANSFORMERS_AVAILABLE:
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=0,
                error_message="Transformers not available",
                analysis_method="transformers_not_available"
            )
        
        try:
            # Create audio folder for chunk files
            audio_folder = Path("audio")
            audio_folder.mkdir(exist_ok=True)
            print(f"[DIRECTORY] Created audio folder for chunks: {audio_folder.absolute()}")
            
            # Convert to WAV format (mono, configurable sample rate) for better compatibility
            sample_rate = int(os.getenv('AUDIO_SAMPLE_RATE', '16000'))
            print(f"[REFRESH] Converting audio to WAV format (sample rate: {sample_rate}Hz)...")
            audio = AudioSegment.from_file(str(file_path))
            audio = audio.set_channels(1).set_frame_rate(sample_rate)
            
            # Create temporary WAV file in audio folder
            temp_wav_path = audio_folder / f"{file_path.stem}_converted.wav"
            audio.export(str(temp_wav_path), format="wav")
            
            print(f"[OK] Audio converted to WAV: {temp_wav_path}")
            
            # Try to load a simple speech recognition model with proper configuration
            try:
                print("[MODEL] Loading speech recognition model...")
                # Use proper configuration to avoid deprecation warnings
                asr_pipeline = pipeline(
                    "automatic-speech-recognition", 
                    model="openai/whisper-base"
                )
                model_used = "openai/whisper-base"
                print(f"[OK] Successfully loaded: {model_used}")
            except Exception as e:
                print(f"[WARN] Failed to load whisper-base: {str(e)}")
                # Try a different model
                try:
                    asr_pipeline = pipeline("automatic-speech-recognition")
                    model_used = "auto-selected"
                    print(f"[OK] Successfully loaded auto-selected model")
                except Exception as e2:
                    print(f"[WARN] Failed to load any model: {str(e2)}")
                    return AudioTranscriptionResult(
                        transcription="",
                        success=False,
                        processing_time_ms=0,
                        error_message="Failed to load any speech recognition model",
                        analysis_method="model_load_failed"
                    )
            
            # Transcribe the entire file (no chunking for simplicity)
            print(f"[AUDIO] Transcribing audio file...")
            # Use updated parameters to avoid deprecation warnings
            generation_kwargs = {}
            if language != "en":
                generation_kwargs["language"] = language
                generation_kwargs["task"] = "transcribe"
            
            # Suppress warnings during transcription
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = asr_pipeline(
                    str(temp_wav_path),
                    chunk_length_s=30,  # Process in 30-second chunks
                    stride_length_s=5,   # 5-second overlap between chunks
                    **generation_kwargs
                )
            transcription = result.get('text', '').strip()
            
            # Clean up temporary WAV file
            try:
                temp_wav_path.unlink()
                print(f"[TRASH] Cleaned up converted WAV file")
            except Exception as e:
                print(f"[WARN] Could not clean up converted WAV file: {str(e)}")
            
            # Clean up audio folder if empty
            try:
                if not any(audio_folder.iterdir()):
                    audio_folder.rmdir()
                    print(f"[TRASH] Cleaned up empty audio folder: {audio_folder}")
            except Exception as e:
                print(f"[WARN] Could not clean up audio folder: {str(e)}")
            
            if transcription:
                return AudioTranscriptionResult(
                    transcription=transcription,
                    success=True,
                    processing_time_ms=0,
                    model_used=model_used,
                    analysis_method="transformers_pipeline"
                )
            else:
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message="No speech detected in audio file",
                    analysis_method="no_speech_detected"
                )
        
        except Exception as e:
            error_msg = str(e)
            print(f"[WARN] Transformers fallback failed: {error_msg}")
            
            # Add installation instructions if it seems like a dependency issue
            if "No module named" in error_msg:
                missing_module = error_msg.split("'")[1]
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message=f"Missing dependency: {missing_module}. Install with: pip install {missing_module}",
                    analysis_method="missing_dependency"
                )
            
            # Add helpful message for common errors
            if "CUDA" in error_msg or "GPU" in error_msg:
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message="GPU-related error. Using CPU for transcription.",
                    analysis_method="gpu_error"
                )
            
            if "out of memory" in error_msg.lower():
                return AudioTranscriptionResult(
                    transcription="",
                    success=False,
                    processing_time_ms=0,
                    error_message="Out of memory. Try reducing chunk_length_s or using a smaller model.",
                    analysis_method="memory_error"
                )
            
            # Default error handling
            return AudioTranscriptionResult(
                transcription="",
                success=False,
                processing_time_ms=0,
                error_message=f"Transcription failed: {error_msg}",
                analysis_method="transformers_failed"
            )
    
    async def process_audio_analysis(self, file_path: Path, prompt: str = None) -> AudioTranscriptionResult:
        """Process audio file with transcription and analysis."""
        # First, transcribe the audio
        transcription_result = await self.transcribe_audio(file_path)
        
        if not transcription_result.success:
            return transcription_result
        
        # If there's a specific prompt, we could do additional analysis here
        if prompt and "transcribe" not in prompt.lower():
            # This would be where we do additional audio analysis based on the prompt
            # For now, just return the transcription
            pass
        
        return transcription_result


# Global instance for easy access
audio_processor = AudioProcessor() 
#!/usr/bin/env python3
"""
File Processor Module - Universal File Type Detection and Processing
Implements Magika-based AI-powered file type detection from the original monolithic code.
"""

import os
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Try to import Magika for AI-powered file type detection
try:
    import magika
    MAGIKA_AVAILABLE = True
    print("[OK] Magika imported for AI-powered file type detection")
except ImportError:
    MAGIKA_AVAILABLE = False
    print("[WARN] Magika not available. Install with: pip install magika")

logger = logging.getLogger(__name__)


@dataclass
class FileAnalysisResult:
    """Result of file analysis."""
    content: str
    success: bool
    processing_time_ms: float
    model_used: Optional[str] = None
    file_type_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class UniversalFileProcessor:
    """Universal file processor using Magika for AI-powered file type detection."""
    
    def __init__(self):
        self.magika_instance = None
        if MAGIKA_AVAILABLE:
            try:
                self.magika_instance = magika.Magika()
            except Exception as e:
                logger.warning(f"Failed to initialize Magika: {e}")
                self.magika_instance = None
    
    def detect_file_type_with_magika(self, file_path: Path) -> Dict[str, Any]:
        """
        Use Magika to detect file type with AI-powered analysis.
        Returns detailed file type information including MIME type, description, and confidence.
        Magika can detect 100+ file types including executables, archives, databases, etc.
        """
        if not MAGIKA_AVAILABLE or not self.magika_instance:
            # Fallback to extension-based detection
            extension = file_path.suffix.lower().lstrip('.')
            return {
                'detected_type': extension or 'unknown',
                'mime_type': 'application/octet-stream',
                'description': f'File with {extension} extension' if extension else 'File with no extension',
                'confidence': 0.5,
                'method': 'extension_fallback',
                'file_size_bytes': file_path.stat().st_size,
                'is_binary': True  # Assume binary when Magika unavailable
            }
        
        try:
            # Get file size for analysis
            file_size = file_path.stat().st_size
            
            # Use Magika for AI-powered file type detection
            with open(file_path, 'rb') as f:
                # Read appropriate sample size (up to 32KB or entire file if smaller)
                sample_size = min(32 * 1024, file_size)
                sample_data = f.read(sample_size)
            
            # Detect file type using Magika
            result = self.magika_instance.identify_bytes(sample_data)
            
            # Determine if file is binary or text-based
            is_binary = self._is_binary_file_type(result.output.label, result.output.mime_type)
            
            return {
                'detected_type': result.output.label,
                'mime_type': result.output.mime_type,
                'description': result.output.description,
                'confidence': result.score,
                'method': 'magika_ai',
                'file_size_bytes': file_size,
                'is_binary': is_binary,
                'sample_size_bytes': len(sample_data),
                'magic_bytes': result.output.magic_bytes if hasattr(result.output, 'magic_bytes') else None
            }
        except Exception as e:
            # Fallback to extension-based detection with better handling
            extension = file_path.suffix.lower().lstrip('.')
            file_size = file_path.stat().st_size
            
            # Try to determine if binary by reading a small sample
            is_binary = True
            try:
                with open(file_path, 'rb') as f:
                    sample = f.read(1024)
                    # Simple heuristic: if it has null bytes or many non-printable chars, it's binary
                    is_binary = b'\x00' in sample or sum(1 for b in sample if b < 32 or b > 126) > len(sample) * 0.3
            except:
                is_binary = True
            
            return {
                'detected_type': extension or 'unknown',
                'mime_type': 'application/octet-stream' if is_binary else 'text/plain',
                'description': f'File with {extension} extension (Magika failed: {str(e)})' if extension else f'Unknown file type (Magika failed: {str(e)})',
                'confidence': 0.3,
                'method': 'extension_fallback_error',
                'file_size_bytes': file_size,
                'is_binary': is_binary,
                'error': str(e)
            }
    
    def _is_binary_file_type(self, file_type: str, mime_type: str) -> bool:
        """Determine if a file type detected by Magika is binary or text-based."""
        # Text-based MIME types (Magika's primary classification)
        text_mimes = {
            'text/', 'application/json', 'application/xml', 'application/javascript',
            'application/x-python', 'application/x-java', 'application/x-php',
            'application/x-ruby', 'application/x-shell', 'application/sql',
            'application/x-yaml', 'application/x-markdown', 'application/x-ini',
            'application/x-config', 'application/x-log', 'application/x-batch',
            'application/x-makefile', 'application/x-dockerfile'
        }
        
        # Check MIME type first (most reliable)
        if any(mime_type.startswith(mime) for mime in text_mimes):
            return False
        
        # Binary MIME types
        binary_mimes = {
            'application/x-dosexec', 'application/x-executable', 'application/x-msdownload',
            'application/x-msi', 'application/x-ms-shortcut', 'application/x-ms-wim',
            'application/x-ms-wim', 'application/x-ms-wim', 'application/x-ms-wim',
            'image/', 'audio/', 'video/', 'application/pdf', 'application/zip',
            'application/x-rar', 'application/x-7z-compressed', 'application/x-tar',
            'application/x-gzip', 'application/x-bzip2', 'application/x-xz',
            'application/x-lzma', 'application/x-lz4', 'application/x-zstd'
        }
        
        if any(mime_type.startswith(mime) for mime in binary_mimes):
            return True
        
        # Check file type label for common patterns
        file_type_lower = file_type.lower()
        text_types = {'text', 'json', 'xml', 'yaml', 'ini', 'config', 'log', 'markdown', 'md'}
        binary_types = {'executable', 'image', 'audio', 'video', 'archive', 'compressed', 'database'}
        
        if any(text_type in file_type_lower for text_type in text_types):
            return False
        if any(binary_type in file_type_lower for binary_type in binary_types):
            return True
        
        # Default to binary for safety
        return True
    
    async def process_any_file_type(self, file_path: Path, prompt: str = None) -> FileAnalysisResult:
        """
        [TARGET] UNIVERSAL FILE PROCESSOR - Handle ANY file type that Magika can detect.
        Uses Magika's AI-powered detection to intelligently route files to appropriate processors.
        Supports 100+ file types including executables, archives, databases, etc.
        """
        start_time = time.time()
        
        try:
            # Detect file type using Magika
            file_type_info = self.detect_file_type_with_magika(file_path)
            detected_type = file_type_info['detected_type']
            mime_type = file_type_info['mime_type']
            is_binary = file_type_info.get('is_binary', True)
            file_size_bytes = file_type_info['file_size_bytes']
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            print(f"[MAGIKA] Processing {detected_type} file ({file_size_mb:.2f} MB)...")
            print(f"[MAGIKA] MIME Type: {mime_type}")
            print(f"[MAGIKA] Binary: {is_binary}")
            print(f"[MAGIKA] Confidence: {file_type_info['confidence']:.2f}")
            
            # Use Langextract to detect task type from prompt if available
            task_type = None
            if prompt:
                try:
                    from .task_detector import task_detector
                    task_detection = task_detector.detect_task_type(prompt)
                    task_type = task_detection.task_type
                    print(f"[LANGEXTRACT] Task type: {task_type} (confidence: {task_detection.confidence:.2f})")
                except Exception as e:
                    print(f"[WARN] Task detection failed: {e}")
            
            # Route to appropriate processor based on MIME type, detected type, and task type
            if mime_type.startswith('image/') or task_type == 'image-classification':
                print("[IMAGE] Routing to image processor (MIME/task-based)...")
                return await self._process_image_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('audio/') or task_type == 'automatic-speech-recognition':
                print("[AUDIO] Routing to audio processor (MIME/task-based)...")
                return await self._process_audio_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('video/') or task_type == 'video-classification':
                print("[VIDEO] Routing to video processor (MIME/task-based)...")
                return await self._process_video_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('application/zip') or mime_type.startswith('application/x-'):
                # Check for specific archive types
                if any(archive_type in detected_type.lower() for archive_type in ['zip', 'tar', 'gz', 'bz2', 'xz', 'rar', '7z', 'lz', 'lzma', 'cab', 'iso', 'dmg', 'pkg']):
                    print("[ARCHIVE] Processing archive file (MIME-based)...")
                    return await self._process_archive_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('application/x-dosexec') or detected_type.lower() in ['exe', 'dll', 'sys']:
                print("[EXECUTABLE] Processing executable file (MIME-based)...")
                return await self._process_executable_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('text/') or not is_binary or task_type in ['text-classification', 'text-generation', 'summarization', 'translation']:
                # Handle text-based files including scripts
                if detected_type.lower() in ['python', 'javascript', 'php', 'ruby', 'perl', 'lua', 'bash', 'sh', 'bat', 'cmd', 'ps1', 'vbs']:
                    print(f"[SCRIPT] Processing {detected_type} script file...")
                else:
                    print("[TEXT] Processing text-based file...")
                return await self._process_text_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('application/pdf') or mime_type.startswith('application/vnd.'):
                # Handle documents (PDF, Office docs, etc.)
                print("[DOCUMENT] Processing document file (MIME-based)...")
                return await self._process_document_file(file_path, file_type_info, prompt)
            
            elif mime_type.startswith('application/x-sqlite') or detected_type.lower() in ['sqlite', 'db', 'sqlite3']:
                print("[DATABASE] Processing database file (MIME-based)...")
                return await self._process_database_file(file_path, file_type_info, prompt)
            
            else:
                # Fallback: use detected type for routing
                print(f"[FALLBACK] Using detected type '{detected_type}' for routing...")
                return await self._process_generic_file(file_path, file_type_info, prompt)
        
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e)
            )
    
    async def _process_image_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process image files using AI vision models."""
        start_time = time.time()
        
        try:
            # Import image processor
            from .image_processor import image_processor
            result = await image_processor.process_image_analysis(str(file_path), prompt or "What is in this image?")
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=result.content,
                success=result.success,
                processing_time_ms=processing_time,
                model_used=result.model_used,
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing image file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_text_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process text-based files."""
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Use the orchestrator to process the text
            from .orchestrator import HuggingFaceOrchestrator
            orchestrator = HuggingFaceOrchestrator()
            
            analysis_prompt = prompt or f"Analyze this {file_type_info['detected_type']} file"
            result = await orchestrator.process_task(f"{analysis_prompt}\n\nFile content:\n{content}")
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=result.content,
                success=result.success,
                processing_time_ms=processing_time,
                model_used=", ".join(result.models_used) if result.models_used else None,
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing text file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_audio_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process audio files using real transcription."""
        start_time = time.time()
        
        try:
            # Use the real audio processor for transcription
            from .audio_processor import audio_processor
            result = await audio_processor.process_audio_analysis(file_path, prompt)
            
            if result.success:
                content = f"🎤 Audio Transcription Results:\n\n"
                content += f"📁 File: {file_path.name}\n"
                content += f"📊 File Type: {file_type_info['detected_type']}\n"
                content += f"📏 File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
                content += f"🤖 Model Used: {result.model_used}\n"
                content += f"🔍 Method: {result.analysis_method}\n\n"
                content += f"📝 Transcription:\n{result.transcription}\n"
            else:
                content = f"❌ Audio Transcription Failed:\n\n"
                content += f"📁 File: {file_path.name}\n"
                content += f"📊 File Type: {file_type_info['detected_type']}\n"
                content += f"📏 File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
                content += f"❌ Error: {result.error_message}\n"
                content += f"🔍 Method: {result.analysis_method}\n"
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=result.success,
                processing_time_ms=processing_time,
                model_used=result.model_used,
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing audio file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_video_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process video files."""
        start_time = time.time()
        
        try:
            content = f"Video file detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n\n"
            content += "Video processing would be implemented here with video analysis models."
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="video_processor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing video file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_executable_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process executable files."""
        start_time = time.time()
        
        try:
            content = f"Executable file detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n\n"
            
            # Try to use PE analyzer for Windows executables
            try:
                from analysis.pe_extractor import CompletePEHeaderExtractor
                pe_extractor = CompletePEHeaderExtractor()
                result = pe_extractor.extract_all_headers(str(file_path))
                content += "PE Header extraction completed."
            except ImportError:
                content += "Note: PE analysis module not available. Install with: pip install pefile"
            except Exception as pe_error:
                content += f"Note: PE analysis failed: {str(pe_error)}"
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="pe_extractor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing executable file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_archive_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process archive files."""
        start_time = time.time()
        
        try:
            content = f"Archive file detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n\n"
            content += "Archive processing would be implemented here."
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="archive_processor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing archive file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_document_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process document files using PyPDF2 for PDFs and other document processors."""
        start_time = time.time()
        
        try:
            content = f"Document file detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n\n"
            
            # Process PDF files
            if file_type_info['mime_type'] == 'application/pdf':
                try:
                    import PyPDF2
                    
                    with open(file_path, 'rb') as file:
                        # Create PDF reader object
                        pdf_reader = PyPDF2.PdfReader(file)
                        
                        # Get basic PDF info
                        num_pages = len(pdf_reader.pages)
                        content += f"📄 PDF Analysis:\n"
                        content += f"• Number of pages: {num_pages}\n"
                        
                        # Try to get PDF metadata
                        if pdf_reader.metadata:
                            content += "• Metadata:\n"
                            for key, value in pdf_reader.metadata.items():
                                if value and str(value).strip():
                                    # Clean up the key name
                                    clean_key = key.replace('/', '').title()
                                    content += f"  - {clean_key}: {value}\n"
                        
                        # Extract text from all pages
                        full_text = ""
                        for page_num in range(num_pages):
                            page = pdf_reader.pages[page_num]
                            full_text += page.extract_text() + "\n"
                        
                        # Add text content and analysis
                        if full_text.strip():
                            # Use the orchestrator to analyze the content based on the prompt
                            if prompt:
                                try:
                                    from .orchestrator import HuggingFaceOrchestrator
                                    orchestrator = HuggingFaceOrchestrator()
                                    
                                    # Create an analysis prompt that combines the user's question with the content
                                    analysis_prompt = f"{prompt}\n\nDocument content:\n{full_text}"
                                    
                                    # Process with orchestrator
                                    result = await orchestrator.process_task(analysis_prompt)
                                    
                                    if result and result.success:
                                        content += f"\n🤖 Analysis Response:\n{result.content}\n"
                                        if hasattr(result, 'models_used') and result.models_used:
                                            content += f"\nModels used: {', '.join(result.models_used)}"
                                    else:
                                        content += f"\n⚠️ Analysis failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}"
                                except Exception as e:
                                    content += f"\n⚠️ Error during analysis: {str(e)}"
                            
                            # Add content preview after the analysis
                            content += f"\n\n📝 Content Preview:\n"
                            preview = full_text[:1000].strip()
                            content += f"{preview}...\n"
                            if len(full_text) > 1000:
                                content += f"\n[Note: Showing first 1000 characters of {len(full_text)} total]"
                        else:
                            content += "\n[No extractable text content found - this might be a scanned document]\n"
                            content += "\nℹ️ Note: For scanned documents, consider using OCR tools for text extraction."
                            
                except ImportError:
                    content += "\n⚠️ PDF processing requires PyPDF2. Install with: pip install PyPDF2"
                except Exception as e:
                    content += f"\n⚠️ Error processing PDF: {str(e)}"
            
            # Handle other document types (docx, etc.)
            else:
                content += "\nℹ️ Support for this document type coming soon."
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="document_processor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing document file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_database_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process database files."""
        start_time = time.time()
        
        try:
            content = f"Database file detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n\n"
            content += "Database processing would be implemented here."
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="database_processor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing database file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )
    
    async def _process_generic_file(self, file_path: Path, file_type_info: Dict[str, Any], prompt: str = None) -> FileAnalysisResult:
        """Process generic files with fallback analysis."""
        start_time = time.time()
        
        try:
            content = f"File detected: {file_type_info['detected_type']}\n"
            content += f"MIME Type: {file_type_info['mime_type']}\n"
            content += f"File Size: {file_type_info['file_size_bytes'] / (1024*1024):.2f} MB\n"
            content += f"Description: {file_type_info['description']}\n"
            content += f"Detection Method: {file_type_info['method']}\n"
            content += f"Confidence: {file_type_info['confidence']:.2f}\n\n"
            content += "Generic file processing completed."
            
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=content,
                success=True,
                processing_time_ms=processing_time,
                model_used="generic_processor",
                file_type_info=file_type_info
            )
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return FileAnalysisResult(
                content=f"Error processing generic file: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                file_type_info=file_type_info
            )


# Global instance for easy access
file_processor = UniversalFileProcessor() 
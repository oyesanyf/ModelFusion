#!/usr/bin/env python3
"""
Comprehensive unit tests for HFOrchestra command line options.
Tests each command line parameter systematically.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import main
from core.task_handler import ComprehensiveTaskHandler
from core.orchestrator import HuggingFaceOrchestrator


class TestCommandLineOptions:
    """Test each command line option systematically."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_text_file(self, temp_dir):
        """Create a sample text file for testing."""
        text_file = temp_dir / "sample.txt"
        text_file.write_text("This is a sample text file for testing.")
        return text_file
    
    @pytest.fixture
    def sample_image_file(self, temp_dir):
        """Create a sample image file for testing."""
        # Create a minimal PNG file (1x1 pixel)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x07_r\x13\x00\x00\x00\x00IEND\xaeB`\x82'
        image_file = temp_dir / "sample.png"
        image_file.write_bytes(png_data)
        return image_file


class TestBasicOptions:
    """Test basic command line options."""
    
    @pytest.mark.asyncio
    async def test_help_option(self):
        """Test --help option."""
        with patch('sys.argv', ['main.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                await main()
            assert exc_info.value.code == 0
    
    @pytest.mark.asyncio
    async def test_prompt_option(self):
        """Test --prompt option."""
        with patch('sys.argv', ['main.py', '--prompt', 'What is artificial intelligence?']):
            with patch('core.orchestrator.HuggingFaceOrchestrator.process_task') as mock_process:
                mock_process.return_value = Mock(
                    success=True,
                    content="AI is a field of computer science...",
                    total_latency_ms=100.0,
                    models_used=["gpt-3.5-turbo"],
                    total_cost=0.001,
                    total_tokens=50
                )
                await main()
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_task_option(self):
        """Test --task option (alias for --prompt)."""
        with patch('sys.argv', ['main.py', '--task', 'Explain machine learning']):
            with patch('core.orchestrator.HuggingFaceOrchestrator.process_task') as mock_process:
                mock_process.return_value = Mock(
                    success=True,
                    content="Machine learning is...",
                    total_latency_ms=150.0,
                    models_used=["gpt-4"],
                    total_cost=0.002,
                    total_tokens=75
                )
                await main()
                mock_process.assert_called_once()


class TestFileProcessingOptions:
    """Test file processing command line options."""
    
    @pytest.mark.asyncio
    async def test_file_option_with_text(self, sample_text_file):
        """Test --file option with text file."""
        with patch('sys.argv', ['main.py', '--file', str(sample_text_file), '--prompt', 'Analyze this file']):
            with patch('core.file_processor.file_processor.process_any_file_type') as mock_process:
                mock_process.return_value = Mock(
                    success=True,
                    content="File analysis complete",
                    processing_time_ms=200.0,
                    model_used="text-analyzer",
                    file_type_info={'detected_type': 'text', 'confidence': 0.95}
                )
                await main()
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_option_with_image(self, sample_image_file):
        """Test --file option with image file."""
        with patch('sys.argv', ['main.py', '--file', str(sample_image_file), '--prompt', 'What is in this image?']):
            with patch('core.file_processor.file_processor.process_any_file_type') as mock_process:
                mock_process.return_value = Mock(
                    success=True,
                    content="Image contains: objects detected",
                    processing_time_ms=300.0,
                    model_used="image-classifier",
                    file_type_info={'detected_type': 'png', 'confidence': 0.99}
                )
                await main()
                mock_process.assert_called_once()


class TestSystemOptions:
    """Test system configuration options."""
    
    @pytest.mark.asyncio
    async def test_budget_option(self):
        """Test --budget option."""
        with patch('sys.argv', ['main.py', '--budget', '5.0', '--prompt', 'Test prompt']):
            with patch('core.orchestrator.HuggingFaceOrchestrator') as mock_orchestrator:
                mock_instance = Mock()
                mock_instance.process_task.return_value = Mock(
                    success=True,
                    content="Budget test",
                    total_cost=2.5
                )
                mock_orchestrator.return_value = mock_instance
                await main()
                mock_orchestrator.assert_called_with(budget=5.0, enable_ml=False, verbose=False)
    
    @pytest.mark.asyncio
    async def test_verbose_option(self):
        """Test --verbose option."""
        with patch('sys.argv', ['main.py', '--verbose', '--prompt', 'Test prompt']):
            with patch('core.orchestrator.HuggingFaceOrchestrator') as mock_orchestrator:
                mock_instance = Mock()
                mock_instance.process_task.return_value = Mock(success=True, content="Verbose test")
                mock_orchestrator.return_value = mock_instance
                await main()
                mock_orchestrator.assert_called_with(budget=10.0, enable_ml=False, verbose=True)
    
    @pytest.mark.asyncio
    async def test_language_option(self):
        """Test --language option."""
        with patch('sys.argv', ['main.py', '--language', 'es', '--prompt', 'Hola mundo']):
            with patch('core.orchestrator.HuggingFaceOrchestrator.process_task') as mock_process:
                mock_process.return_value = Mock(success=True, content="¡Hola!")
                await main()
                # Verify language parameter is passed
                args, kwargs = mock_process.call_args
                assert kwargs.get('language') == 'es'
    
    @pytest.mark.asyncio
    async def test_chain_of_thought_option(self):
        """Test --chain-of-thought option."""
        with patch('sys.argv', ['main.py', '--chain-of-thought', '--prompt', 'Complex reasoning task']):
            with patch('core.orchestrator.HuggingFaceOrchestrator.process_task') as mock_process:
                mock_process.return_value = Mock(success=True, content="Chain of thought response")
                await main()
                args, kwargs = mock_process.call_args
                assert kwargs.get('chain_of_thought') is True
    
    @pytest.mark.asyncio
    async def test_enable_ml_option(self):
        """Test --enable-ml option."""
        with patch('sys.argv', ['main.py', '--enable-ml', '--prompt', 'ML enhanced task']):
            with patch('core.orchestrator.HuggingFaceOrchestrator') as mock_orchestrator:
                mock_instance = Mock()
                mock_instance.process_task.return_value = Mock(success=True, content="ML enhanced")
                mock_orchestrator.return_value = mock_instance
                await main()
                mock_orchestrator.assert_called_with(budget=10.0, enable_ml=True, verbose=False)


class TestDatabaseOptions:
    """Test database-related command line options."""
    
    @pytest.mark.asyncio
    async def test_stats_option(self):
        """Test --stats option."""
        with patch('sys.argv', ['main.py', '--stats']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_stats') as mock_stats:
                mock_stats.return_value = Mock(
                    success=True,
                    content="📊 Total Models: 50,000\n🏷️ Top Pipeline Tags:\n  • text-classification: 5,000 models"
                )
                await main()
                mock_stats.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tasks_option(self):
        """Test --tasks option."""
        with patch('sys.argv', ['main.py', '--tasks']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_tasks_list') as mock_tasks:
                mock_tasks.return_value = Mock(
                    success=True,
                    content="📋 Available task categories:\n  🔤 Text: 25 tasks\n  🖼️ Image: 8 tasks"
                )
                await main()
                mock_tasks.assert_called_once_with('all')
    
    @pytest.mark.asyncio
    async def test_tasks_with_category(self):
        """Test --tasks with specific category."""
        with patch('sys.argv', ['main.py', '--tasks', 'text']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_tasks_list') as mock_tasks:
                mock_tasks.return_value = Mock(
                    success=True,
                    content="📋 Available text tasks:\n  • text-classification\n  • text-generation"
                )
                await main()
                mock_tasks.assert_called_once_with('text')
    
    @pytest.mark.asyncio
    async def test_update_option(self):
        """Test --update option."""
        with patch('sys.argv', ['main.py', '--update']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_update_database') as mock_update:
                mock_update.return_value = Mock(
                    success=True,
                    content="✅ Database updated! Processed: 1,000 models"
                )
                await main()
                mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clearcache_option(self):
        """Test --clearcache option."""
        with patch('sys.argv', ['main.py', '--clearcache']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_clear_cache') as mock_clear:
                mock_clear.return_value = Mock(
                    success=True,
                    content="🗑️ Cache cleared successfully!"
                )
                await main()
                mock_clear.assert_called_once()


class TestTextProcessingTasks:
    """Test text processing task options."""
    
    @pytest.mark.asyncio
    async def test_text_classification(self):
        """Test --text-classification option."""
        with patch('sys.argv', ['main.py', '--text-classification', '--prompt', 'I love this product!']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Classification: Positive (confidence: 0.89)"
                )
                await main()
                mock_task.assert_called_once_with('text-classification', 'I love this product!')
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self):
        """Test --sentiment option."""
        with patch('sys.argv', ['main.py', '--sentiment', '--prompt', 'This movie is amazing!']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Sentiment: Positive (score: 0.92)"
                )
                await main()
                mock_task.assert_called_once_with('sentiment', 'This movie is amazing!')
    
    @pytest.mark.asyncio
    async def test_summarization(self):
        """Test --summarization option."""
        with patch('sys.argv', ['main.py', '--summarization', '--prompt', 'Long text to summarize...']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Summary: Key points extracted from the text."
                )
                await main()
                mock_task.assert_called_once_with('summarization', 'Long text to summarize...')
    
    @pytest.mark.asyncio
    async def test_question_answering(self):
        """Test --question-answering option."""
        with patch('sys.argv', ['main.py', '--question-answering', '--prompt', 'What is machine learning?']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Answer: Machine learning is a subset of artificial intelligence..."
                )
                await main()
                mock_task.assert_called_once_with('question-answering', 'What is machine learning?')
    
    @pytest.mark.asyncio
    async def test_translation(self):
        """Test --translation option."""
        with patch('sys.argv', ['main.py', '--translation', '--prompt', 'Hello world']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Translation: Hola mundo"
                )
                await main()
                mock_task.assert_called_once_with('translation', 'Hello world')


class TestSecurityTasks:
    """Test security-related task options."""
    
    @pytest.mark.asyncio
    async def test_spam_detection(self):
        """Test --spam-detection option."""
        with patch('sys.argv', ['main.py', '--spam-detection', '--prompt', 'WIN FREE MONEY NOW!!!']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Spam Detection: SPAM (confidence: 0.95)"
                )
                await main()
                mock_task.assert_called_once_with('spam-detection', 'WIN FREE MONEY NOW!!!')
    
    @pytest.mark.asyncio
    async def test_pii_detection(self):
        """Test --pii-detection option."""
        with patch('sys.argv', ['main.py', '--pii-detection', '--prompt', 'My email is john@example.com']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="PII Detected: Email address found"
                )
                await main()
                mock_task.assert_called_once_with('pii-detection', 'My email is john@example.com')
    
    @pytest.mark.asyncio
    async def test_malware_text_detection(self):
        """Test --malware-text-detection option."""
        with patch('sys.argv', ['main.py', '--malware-text-detection', '--prompt', 'Suspicious code snippet']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=True,
                    content="Malware Analysis: Potentially suspicious patterns detected"
                )
                await main()
                mock_task.assert_called_once_with('malware-text-detection', 'Suspicious code snippet')


class TestHydeOptions:
    """Test HYDE (Hypothetical Document Embeddings) options."""
    
    @pytest.mark.asyncio
    async def test_demo_hyde(self):
        """Test --demo-hyde option."""
        with patch('sys.argv', ['main.py', '--demo-hyde']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_hyde_demo') as mock_hyde:
                mock_hyde.return_value = Mock(
                    success=True,
                    content="🔍 HYDE Demo\nGenerated hypothetical documents..."
                )
                await main()
                mock_hyde.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_query(self):
        """Test --search-query option."""
        with patch('sys.argv', ['main.py', '--search-query', 'machine learning', '--top-k', '3']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_search_query') as mock_search:
                mock_search.return_value = Mock(
                    success=True,
                    content="🔍 Search Results:\n1. Machine Learning Basics\n2. AI Applications"
                )
                await main()
                mock_search.assert_called_once_with('machine learning', 3)


class TestPEAnalysis:
    """Test PE (Portable Executable) analysis options."""
    
    @pytest.mark.asyncio
    async def test_pe_header_extraction_missing_file(self):
        """Test --pe-header-extraction without file parameter."""
        with patch('sys.argv', ['main.py', '--pe-header-extraction']):
            with patch('builtins.print') as mock_print:
                await main()
                mock_print.assert_any_call("❌ Error: --pe-header-extraction requires --file parameter")
    
    @pytest.mark.asyncio
    async def test_pe_header_extraction_with_file(self, temp_dir):
        """Test --pe-header-extraction with file parameter."""
        # Create a dummy executable file
        exe_file = temp_dir / "test.exe"
        exe_file.write_bytes(b"MZ\x90\x00")  # Minimal DOS header
        
        with patch('sys.argv', ['main.py', '--pe-header-extraction', '--file', str(exe_file)]):
            with patch('core.pe_analyzer.enhanced_pe_analyzer.analyze_pe_file') as mock_analyze:
                mock_analyze.return_value = Mock(
                    success=True,
                    file_type_info={'detected_type': 'exe'},
                    pe_info={'dos_header': 'valid'},
                    malware_analysis={'threat_level': 'low'}
                )
                with patch('core.pe_analyzer.enhanced_pe_analyzer.format_analysis_report') as mock_format:
                    mock_format.return_value = "PE Analysis Report: File appears safe"
                    await main()
                    mock_analyze.assert_called_once()


class TestAdvancedAnalytics:
    """Test advanced analytics options."""
    
    @pytest.mark.asyncio
    async def test_analytics_demo(self):
        """Test --analytics-demo option."""
        with patch('sys.argv', ['main.py', '--analytics-demo']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_analytics_demo') as mock_analytics:
                mock_analytics.return_value = Mock(
                    success=True,
                    content="🔬 Advanced Analytics Demo\nDatabase stats and model rankings..."
                )
                await main()
                mock_analytics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_model_ranking(self):
        """Test --model-ranking option."""
        with patch('sys.argv', ['main.py', '--model-ranking', 'text-generation']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_model_ranking') as mock_ranking:
                mock_ranking.return_value = Mock(
                    success=True,
                    content="🏆 Top Models for text-generation:\n1. Model A\n2. Model B"
                )
                await main()
                mock_ranking.assert_called_once_with(task='text-generation', limit=10)
    
    @pytest.mark.asyncio
    async def test_model_recommendations(self):
        """Test --model-recommendations option."""
        with patch('sys.argv', ['main.py', '--model-recommendations']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_model_recommendations') as mock_rec:
                mock_rec.return_value = Mock(
                    success=True,
                    content="🎯 Personalized Recommendations:\n1. Recommended Model A"
                )
                await main()
                mock_rec.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_missing_prompt_for_text_task(self):
        """Test text task without required prompt."""
        with patch('sys.argv', ['main.py', '--text-classification']):
            with patch('core.task_handler.ComprehensiveTaskHandler.handle_specialized_task') as mock_task:
                mock_task.return_value = Mock(
                    success=False,
                    content="❌ Task 'text-classification' requires input text."
                )
                await main()
                mock_task.assert_called_once_with('text-classification', None)
    
    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        """Test with nonexistent file."""
        with patch('sys.argv', ['main.py', '--file', '/nonexistent/file.txt', '--prompt', 'Analyze']):
            with patch('core.file_processor.file_processor.process_any_file_type') as mock_process:
                mock_process.side_effect = FileNotFoundError("File not found")
                with pytest.raises(FileNotFoundError):
                    await main()
    
    @pytest.mark.asyncio
    async def test_invalid_task_type(self):
        """Test with invalid task type."""
        with patch('sys.argv', ['main.py', '--invalid-task-option']):
            with pytest.raises(SystemExit):
                await main()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

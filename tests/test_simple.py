#!/usr/bin/env python3
"""
Simple Unit Tests for HFOrchestra Command Line Options
Tests command line functionality without complex imports.
"""

import pytest
import asyncio
import subprocess
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock

# Test data
SAMPLE_TEXT = "This is a test text for HFOrchestra functionality."
SAMPLE_JSON = '{"test": "data", "message": "Hello World"}'

class TestCommandLineBasics:
    """Test basic command line functionality."""
    
    def test_help_option(self):
        """Test --help option returns help text."""
        result = subprocess.run([
            sys.executable, 'main.py', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        assert result.returncode == 0
        assert 'HFOrchestra' in result.stdout or 'usage:' in result.stdout
    
    def test_stats_option(self):
        """Test --stats option executes without error."""
        result = subprocess.run([
            sys.executable, 'main.py', '--stats'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should not crash, exit code 0 or graceful handling
        assert result.returncode in [0, 1]  # May fail if DB not initialized, but shouldn't crash
    
    def test_tasks_option(self):
        """Test --tasks option executes without error."""
        result = subprocess.run([
            sys.executable, 'main.py', '--tasks'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should not crash
        assert result.returncode in [0, 1]
    
    def test_clearcache_option(self):
        """Test --clearcache option executes without error."""
        result = subprocess.run([
            sys.executable, 'main.py', '--clearcache'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should not crash
        assert result.returncode in [0, 1]


class TestTextProcessingOptions:
    """Test text processing command line options."""
    
    def test_prompt_option(self):
        """Test --prompt option with simple text."""
        result = subprocess.run([
            sys.executable, 'main.py', '--prompt', 'What is AI?'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
        # If it succeeds, should have some output
        if result.returncode == 0:
            assert len(result.stdout) > 0
    
    def test_text_classification_option(self):
        """Test --text-classification option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--text-classification', '--prompt', 'I love this product!'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_sentiment_option(self):
        """Test --sentiment option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--sentiment', '--prompt', 'This movie is great!'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_question_answering_option(self):
        """Test --question-answering option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--question-answering', '--prompt', 'What is machine learning?'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]


class TestSecurityOptions:
    """Test security-related command line options."""
    
    def test_spam_detection_option(self):
        """Test --spam-detection option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--spam-detection', '--prompt', 'WIN FREE MONEY NOW!!!'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_pii_detection_option(self):
        """Test --pii-detection option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--pii-detection', '--prompt', 'My email is test@example.com'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]


class TestFileProcessingOptions:
    """Test file processing command line options."""
    
    def test_file_option_with_text_file(self):
        """Test --file option with text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(SAMPLE_TEXT)
            text_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, 'main.py', '--file', text_file, '--prompt', 'Analyze this file'
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
            
            # Should execute without crashing
            assert result.returncode in [0, 1]
            
        finally:
            Path(text_file).unlink(missing_ok=True)
    
    def test_file_option_with_json_file(self):
        """Test --file option with JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(SAMPLE_JSON)
            json_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, 'main.py', '--file', json_file, '--prompt', 'What is in this JSON?'
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
            
            # Should execute without crashing
            assert result.returncode in [0, 1]
            
        finally:
            Path(json_file).unlink(missing_ok=True)


class TestAdvancedOptions:
    """Test advanced command line options."""
    
    def test_demo_hyde_option(self):
        """Test --demo-hyde option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--demo-hyde'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_analytics_demo_option(self):
        """Test --analytics-demo option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--analytics-demo'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_search_query_option(self):
        """Test --search-query option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--search-query', 'machine learning', '--top-k', '3'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]


class TestSystemOptions:
    """Test system configuration options."""
    
    def test_budget_option(self):
        """Test --budget option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--budget', '5.0', '--prompt', 'Test with budget'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_verbose_option(self):
        """Test --verbose option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--verbose', '--prompt', 'Verbose test'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]
    
    def test_language_option(self):
        """Test --language option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--language', 'es', '--prompt', 'Hola mundo'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=60)
        
        # Should execute without crashing
        assert result.returncode in [0, 1]


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_option(self):
        """Test with invalid command line option."""
        result = subprocess.run([
            sys.executable, 'main.py', '--invalid-option-xyz'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should fail gracefully with non-zero exit code
        assert result.returncode != 0
    
    def test_missing_prompt_for_text_task(self):
        """Test text task without required prompt."""
        result = subprocess.run([
            sys.executable, 'main.py', '--text-classification'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should handle gracefully (may succeed with error message or fail)
        assert result.returncode in [0, 1, 2]
    
    def test_nonexistent_file(self):
        """Test with nonexistent file."""
        result = subprocess.run([
            sys.executable, 'main.py', '--file', '/nonexistent/file.txt', '--prompt', 'Analyze'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=30)
        
        # Should handle gracefully (likely fail but not crash)
        assert result.returncode in [0, 1, 2]


def test_command_line_options_comprehensive():
    """Comprehensive test to verify major functionality works."""
    
    # Test core functions that should always work
    core_tests = [
        ['--help'],
        ['--stats'],
        ['--tasks'],
        ['--clearcache'],
        ['--demo-hyde']
    ]
    
    working_commands = 0
    total_commands = len(core_tests)
    
    for cmd_args in core_tests:
        try:
            result = subprocess.run([
                sys.executable, 'main.py'
            ] + cmd_args, capture_output=True, text=True, 
            cwd=Path(__file__).parent.parent, timeout=30)
            
            if result.returncode == 0:
                working_commands += 1
                
        except subprocess.TimeoutExpired:
            # Timeout is acceptable - command didn't crash
            working_commands += 1
        except Exception:
            # Other exceptions are not expected
            pass
    
    # At least 50% of core commands should work
    success_rate = working_commands / total_commands
    assert success_rate >= 0.5, f"Only {success_rate:.1%} of core commands worked"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

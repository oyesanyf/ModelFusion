#!/usr/bin/env python3
"""
Test Runner for HFOrchestra Command Line Options
Tests each option systematically and provides detailed reports.
"""

import asyncio
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CommandLineOptionTester:
    """Systematically test each command line option."""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up test environment with sample files."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample files for testing
        (self.temp_dir / "sample.txt").write_text("This is a sample text file for testing HFOrchestra functionality.")
        (self.temp_dir / "sample.json").write_text('{"test": "data", "numbers": [1, 2, 3]}')
        
        # Create a minimal PNG file (1x1 pixel)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x07_r\x13\x00\x00\x00\x00IEND\xaeB`\x82'
        (self.temp_dir / "sample.png").write_bytes(png_data)
        
        # Create a fake executable file (DOS header only)
        (self.temp_dir / "sample.exe").write_bytes(b"MZ\x90\x00" + b"\x00" * 60)
        
        print(f"📁 Test environment created: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"🗑️ Test environment cleaned up")
    
    async def run_command_test(self, cmd_args: List[str], test_name: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a single command test."""
        print(f"\n🧪 Testing: {test_name}")
        print(f"📝 Command: python main.py {' '.join(cmd_args)}")
        
        start_time = time.time()
        result = {
            'test_name': test_name,
            'command': f"python main.py {' '.join(cmd_args)}",
            'success': False,
            'output': '',
            'error': '',
            'execution_time': 0,
            'exit_code': None
        }
        
        try:
            # Run the command
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'main.py', *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                result['exit_code'] = process.returncode
                result['output'] = stdout.decode('utf-8', errors='ignore')
                result['error'] = stderr.decode('utf-8', errors='ignore')
                result['success'] = process.returncode == 0
                
            except asyncio.TimeoutError:
                process.kill()
                result['error'] = f"Command timed out after {timeout} seconds"
                result['exit_code'] = -1
            
        except Exception as e:
            result['error'] = f"Failed to execute command: {str(e)}"
            result['exit_code'] = -2
        
        result['execution_time'] = time.time() - start_time
        
        # Print results
        status = "PASS" if result['success'] else "FAIL"
        print(f"   {status} ({result['execution_time']:.2f}s)")
        if result['error']:
            print(f"   Error: {result['error'][:100]}...")
        if result['output']:
            print(f"   Output: {result['output'][:100]}...")
        
        return result
    
    async def test_basic_options(self) -> List[Dict[str, Any]]:
        """Test basic command line options."""
        print("\n" + "="*60)
        print("TESTING BASIC OPTIONS")
        print("="*60)
        
        tests = [
            (['--help'], "Help option"),
            (['--prompt', 'What is artificial intelligence?'], "Basic prompt"),
            (['--task', 'Explain machine learning'], "Task option (alias for prompt)"),
            (['--budget', '5.0', '--prompt', 'Test with budget'], "Budget option"),
            (['--verbose', '--prompt', 'Verbose test'], "Verbose option"),
            (['--language', 'es', '--prompt', 'Hola mundo'], "Language option"),
            (['--chain-of-thought', '--prompt', 'Complex reasoning'], "Chain of thought"),
            (['--enable-ml', '--prompt', 'ML enhanced task'], "Enable ML features"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name, timeout=60)
            results.append(result)
        
        return results
    
    async def test_database_options(self) -> List[Dict[str, Any]]:
        """Test database-related options."""
        print("\n" + "="*60)
        print("TESTING DATABASE OPTIONS")
        print("="*60)
        
        tests = [
            (['--stats'], "Database statistics"),
            (['--tasks'], "List all tasks"),
            (['--tasks', 'text'], "List text tasks"),
            (['--tasks', 'image'], "List image tasks"),
            (['--clearcache'], "Clear cache"),
            # Skip --update as it takes too long
            # (['--update'], "Update database"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name)
            results.append(result)
        
        return results
    
    async def test_file_processing_options(self) -> List[Dict[str, Any]]:
        """Test file processing options."""
        print("\n" + "="*60)
        print("📁 TESTING FILE PROCESSING OPTIONS")
        print("="*60)
        
        text_file = str(self.temp_dir / "sample.txt")
        image_file = str(self.temp_dir / "sample.png")
        exe_file = str(self.temp_dir / "sample.exe")
        
        tests = [
            (['--file', text_file, '--prompt', 'Analyze this text file'], "Text file analysis"),
            (['--file', image_file, '--prompt', 'What is in this image?'], "Image file analysis"),
            (['--file', exe_file, '--pe-header-extraction'], "PE header extraction"),
            (['--file', text_file, '--summarization'], "File with task option"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name, timeout=60)
            results.append(result)
        
        return results
    
    async def test_text_processing_tasks(self) -> List[Dict[str, Any]]:
        """Test text processing task options."""
        print("\n" + "="*60)
        print("📝 TESTING TEXT PROCESSING TASKS")
        print("="*60)
        
        tests = [
            (['--text-classification', '--prompt', 'I love this product!'], "Text classification"),
            (['--sentiment', '--prompt', 'This movie is amazing!'], "Sentiment analysis"),
            (['--question-answering', '--prompt', 'What is machine learning?'], "Question answering"),
            (['--summarization', '--prompt', 'Long text to summarize here...'], "Text summarization"),
            (['--translation', '--prompt', 'Hello world'], "Translation"),
            (['--ner', '--prompt', 'John Smith works at Microsoft in Seattle'], "Named entity recognition"),
            (['--text-generation', '--prompt', 'Once upon a time'], "Text generation"),
            (['--fill-mask', '--prompt', 'The capital of France is [MASK]'], "Fill mask"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name, timeout=45)
            results.append(result)
        
        return results
    
    async def test_security_tasks(self) -> List[Dict[str, Any]]:
        """Test security-related task options."""
        print("\n" + "="*60)
        print("🛡️ TESTING SECURITY TASKS")
        print("="*60)
        
        tests = [
            (['--spam-detection', '--prompt', 'WIN FREE MONEY NOW!!!'], "Spam detection"),
            (['--pii-detection', '--prompt', 'My email is john@example.com'], "PII detection"),
            (['--malware-text-detection', '--prompt', 'Suspicious code snippet'], "Malware text detection"),
            (['--phishing-detection', '--prompt', 'Click here to verify your account'], "Phishing detection"),
            (['--hate-speech-detection', '--prompt', 'Testing hate speech detection'], "Hate speech detection"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name)
            results.append(result)
        
        return results
    
    async def test_multimedia_tasks(self) -> List[Dict[str, Any]]:
        """Test multimedia processing task options."""
        print("\n" + "="*60)
        print("🖼️ TESTING MULTIMEDIA TASKS")
        print("="*60)
        
        image_file = str(self.temp_dir / "sample.png")
        
        tests = [
            (['--image-classification', '--file', image_file], "Image classification"),
            (['--object-detection', '--file', image_file], "Object detection"),
            (['--visual-question-answering', '--file', image_file, '--prompt', 'What is this?'], "Visual Q&A"),
            (['--text-to-image', '--prompt', 'A beautiful sunset'], "Text to image"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name, timeout=60)
            results.append(result)
        
        return results
    
    async def test_advanced_options(self) -> List[Dict[str, Any]]:
        """Test advanced analytics and HYDE options."""
        print("\n" + "="*60)
        print("🔬 TESTING ADVANCED OPTIONS")
        print("="*60)
        
        tests = [
            (['--demo-hyde'], "HYDE demo"),
            (['--search-query', 'machine learning', '--top-k', '3'], "Semantic search"),
            (['--analytics-demo'], "Advanced analytics demo"),
            (['--model-ranking', 'text-generation'], "Model ranking"),
            (['--model-recommendations'], "Model recommendations"),
            (['--decision-stats'], "Decision statistics"),
            (['--performance-stats'], "Performance statistics"),
            (['--cache-stats'], "Cache statistics"),
        ]
        
        results = []
        for args, name in tests:
            result = await self.run_command_test(args, name)
            results.append(result)
        
        return results
    
    def generate_report(self, all_results: List[Dict[str, Any]]) -> str:
        """Generate a comprehensive test report."""
        total_tests = len(all_results)
        passed_tests = sum(1 for r in all_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        report = f"""
HFOrchestra Command Line Options Test Report
{'='*60}

SUMMARY:
   Total Tests: {total_tests}
   Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)
   Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)

DETAILED RESULTS:
"""
        
        # Group results by category
        categories = {
            'Basic Options': [],
            'Database Options': [],
            'File Processing': [],
            'Text Processing': [],
            'Security Tasks': [],
            'Multimedia Tasks': [],
            'Advanced Options': []
        }
        
        for result in all_results:
            # Categorize based on test name
            if any(keyword in result['test_name'].lower() for keyword in ['help', 'prompt', 'task', 'budget', 'verbose', 'language', 'chain', 'ml']):
                categories['Basic Options'].append(result)
            elif any(keyword in result['test_name'].lower() for keyword in ['stats', 'database', 'cache', 'update']):
                categories['Database Options'].append(result)
            elif 'file' in result['test_name'].lower() or 'pe header' in result['test_name'].lower():
                categories['File Processing'].append(result)
            elif any(keyword in result['test_name'].lower() for keyword in ['text', 'sentiment', 'question', 'summarization', 'translation', 'ner', 'generation', 'fill']):
                categories['Text Processing'].append(result)
            elif any(keyword in result['test_name'].lower() for keyword in ['spam', 'pii', 'malware', 'phishing', 'hate']):
                categories['Security Tasks'].append(result)
            elif any(keyword in result['test_name'].lower() for keyword in ['image', 'object', 'visual', 'multimedia']):
                categories['Multimedia Tasks'].append(result)
            else:
                categories['Advanced Options'].append(result)
        
        for category, results in categories.items():
            if results:
                passed = sum(1 for r in results if r['success'])
                total = len(results)
                report += f"\n🔸 {category}: {passed}/{total} passed\n"
                
                for result in results:
                    status = "✅" if result['success'] else "❌"
                    report += f"   {status} {result['test_name']} ({result['execution_time']:.2f}s)\n"
                    if not result['success'] and result['error']:
                        report += f"      Error: {result['error'][:100]}...\n"
        
        report += f"\n⏱️ Total execution time: {sum(r['execution_time'] for r in all_results):.2f} seconds\n"
        
        return report
    
    async def run_all_tests(self):
        """Run all command line option tests."""
        print("🚀 Starting comprehensive HFOrchestra command line option tests...")
        
        all_results = []
        
        try:
            # Run test categories
            all_results.extend(await self.test_basic_options())
            all_results.extend(await self.test_database_options())
            all_results.extend(await self.test_file_processing_options())
            all_results.extend(await self.test_text_processing_tasks())
            all_results.extend(await self.test_security_tasks())
            all_results.extend(await self.test_multimedia_tasks())
            all_results.extend(await self.test_advanced_options())
            
            # Generate and display report
            report = self.generate_report(all_results)
            print(report)
            
            # Save detailed results to JSON with UTF-8 encoding
            results_file = Path("test_results.json")
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"\nDetailed results saved to: {results_file}")
            
            # Save report to text file with UTF-8 encoding
            report_file = Path("test_report.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Test report saved to: {report_file}")
            
        finally:
            self.cleanup_test_environment()


async def main():
    """Main entry point for test runner."""
    tester = CommandLineOptionTester()
    await tester.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())

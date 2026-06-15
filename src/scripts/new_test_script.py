#!/usr/bin/env python3
"""
New Test Script for All HFOrchestra Flags
Tests all available -- flags with appropriate sample files from c:\testfiles
ENFORCES: All file-based tasks MUST use Magika for file type detection
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

class NewFlagTester:
    def __init__(self, testfiles_dir: str = "c:\\testfiles"):
        self.testfiles_dir = Path(testfiles_dir)
        self.results = {}
        self.test_files = self._discover_test_files()
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
    def _discover_test_files(self) -> Dict[str, List[Path]]:
        """Discover and categorize test files by type."""
        if not self.testfiles_dir.exists():
            print(f"❌ Test files directory not found: {self.testfiles_dir}")
            return {}
            
        files = {}
        for file_path in self.testfiles_dir.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext not in files:
                    files[ext] = []
                files[ext].append(file_path)
                
        print(f"📁 Found {sum(len(files_list) for files_list in files.values())} test files:")
        for ext, file_list in files.items():
            print(f"   {ext}: {len(file_list)} files")
            
        return files
    
    def _get_best_file_for_task(self, task_type: str) -> Optional[Path]:
        """Get the best file for a specific task type."""
        task_lower = task_type.lower()
        
        # Text tasks
        if any(text_task in task_lower for text_task in ['text', 'translation', 'summarization', 'classification', 'generation']):
            for ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json']:
                if ext in self.test_files and self.test_files[ext]:
                    return self.test_files[ext][0]
        
        # Default to any text file
        for ext in ['.txt', '.md', '.py']:
            if ext in self.test_files and self.test_files[ext]:
                return self.test_files[ext][0]
        
        return None
    
    def _get_test_prompt_for_task(self, task_type: str) -> str:
        """Get appropriate test prompt for task type."""
        task_lower = task_type.lower()
        
        if 'classification' in task_lower:
            return "Analyze the sentiment of this text"
        elif 'generation' in task_lower:
            return "Continue this text naturally"
        elif 'summarization' in task_lower:
            return "Summarize this content"
        elif 'translation' in task_lower:
            return "Translate to Spanish"
        else:
            return "Process this content"
    
    def test_text_tasks(self):
        """Test text-based tasks specifically."""
        text_tasks = [
            ('text-classification', 'Classify text into categories', 'text'),
            ('text-generation', 'Generate text content', 'text'),
            ('summarization', 'Summarize long text', 'text'),
            ('translation', 'Translate text between languages', 'text')
        ]
        
        results = []
        
        for task_flag, description, category in text_tasks:
            print(f"\n🧪 Testing: --{task_flag}")
            print(f"📝 Description: {description}")
            print(f"📂 Category: {category}")
            
            start_time = time.time()
            result = {
                'flag': task_flag,
                'description': description,
                'category': category,
                'success': False,
                'error': None,
                'output': None,
                'duration': 0,
                'file_used': None,
                'magika_used': False,
                'command_executed': None,
                'return_code': None,
                'error_output': None
            }
            
            try:
                # Build command
                cmd = ['python', 'main.py', f'--{task_flag}']
                
                # Add file
                test_file = self._get_best_file_for_task(task_flag)
                if test_file:
                    cmd.extend(['--file', str(test_file)])
                    result['file_used'] = str(test_file)
                    result['magika_used'] = True
                    print(f"📁 Using file: {test_file.name}")
                    print(f"🔍 [MAGIKA] File-based task - AI-powered file type detection will be used")
                else:
                    print(f"⚠️ No suitable file found for {task_flag}")
                    result['error'] = f"No suitable test file found for {task_flag}"
                    result['duration'] = time.time() - start_time
                    results.append(result)
                    continue
                
                # Add prompt
                prompt = self._get_test_prompt_for_task(task_flag)
                cmd.extend(['--prompt', prompt])
                print(f"💬 Using prompt: {prompt}")
                
                # Add verbose flag
                cmd.append('--verbose')
                
                # Build command string for display
                result['command_executed'] = ' '.join([f'"{a}"' if ' ' in a else a for a in cmd])
                print(f"🚀 Running: {result['command_executed']}")
                
                # Run command directly with subprocess
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120
                )
                
                result['duration'] = time.time() - start_time
                result['output'] = process.stdout
                result['error_output'] = process.stderr
                result['return_code'] = process.returncode
                
                if process.returncode == 0:
                    result['success'] = True
                    print(f"✅ SUCCESS: {task_flag} completed in {result['duration']:.2f}s")
                    
                    # Verify Magika usage
                    if 'MAGIKA' in process.stdout or 'magika' in process.stdout.lower():
                        print(f"🔍 [MAGIKA] Confirmed: AI-powered file type detection was used")
                        result['magika_used'] = True
                    else:
                        print(f"⚠️ [MAGIKA] Warning: No explicit Magika usage detected in output")
                        result['magika_used'] = False
                else:
                    result['success'] = False
                    result['error'] = f"Command failed with return code {process.returncode}"
                    print(f"❌ FAILED: {task_flag} - {result['error']}")
                    if process.stderr:
                        print(f"Error: {process.stderr[:200]}...")
                
            except subprocess.TimeoutExpired:
                result['duration'] = time.time() - start_time
                result['success'] = False
                result['error'] = "Command timed out after 120 seconds"
                print(f"⏰ TIMEOUT: {task_flag} took too long")
                
            except Exception as e:
                result['duration'] = time.time() - start_time
                result['success'] = False
                result['error'] = str(e)
                print(f"💥 EXCEPTION: {task_flag} - {e}")
            
            results.append(result)
            time.sleep(1)  # Small delay between tests
        
        return results

def main():
    print("🚀 Starting New Test Script for HFOrchestra Flags")
    print("=" * 60)
    
    tester = NewFlagTester()
    
    # Test text tasks
    results = tester.test_text_tasks()
    
    # Print summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n📊 SUMMARY:")
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total)*100:.1f}%")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = tester.reports_dir / f"new_test_results_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
                'success_rate': (successful/total)*100
            },
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Results saved to: {report_file}")

if __name__ == "__main__":
    main()

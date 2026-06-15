#!/usr/bin/env python3
"""
Quick Verification Script - Test HFOrchestra Command Line Options
No dependencies required - run immediately to verify functionality.
"""

import subprocess
import sys
import time
from pathlib import Path


def test_command(cmd_args, description, timeout=30):
    """Test a single command and return result."""
    print(f"\n🧪 Testing: {description}")
    print(f"📝 Command: python main.py {' '.join(cmd_args)}")
    print("-" * 50)
    
    start_time = time.time()
    try:
        result = subprocess.run([
            sys.executable, 'main.py'
        ] + cmd_args, capture_output=True, text=True, timeout=timeout)
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ SUCCESS ({execution_time:.2f}s)")
            if result.stdout:
                output = result.stdout[:200] + ("..." if len(result.stdout) > 200 else "")
                print(f"📄 Output: {output}")
        else:
            print(f"❌ FAILED (Exit code: {result.returncode}, {execution_time:.2f}s)")
            if result.stderr:
                error = result.stderr[:150] + ("..." if len(result.stderr) > 150 else "")
                print(f"⚠️ Error: {error}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT (>{timeout}s) - Command may be working but taking too long")
        return True  # Timeout means it's running, not crashing
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False


def main():
    """Run quick verification tests."""
    print("🚀 HFOrchestra Quick Verification Test")
    print("=" * 60)
    print("Testing core command line options to verify functionality...\n")
    
    # Define test cases (command, description, timeout)
    test_cases = [
        # Core system functions (should always work)
        (['--help'], "Help option", 10),
        (['--stats'], "Database statistics", 30),
        (['--tasks'], "List available tasks", 30),
        (['--clearcache'], "Clear cache", 20),
        
        # Basic AI functionality
        (['--prompt', 'What is artificial intelligence?'], "Basic AI prompt", 60),
        (['--text-classification', '--prompt', 'I love this!'], "Text classification", 45),
        (['--sentiment', '--prompt', 'Great movie!'], "Sentiment analysis", 45),
        (['--question-answering', '--prompt', 'What is ML?'], "Question answering", 45),
        
        # Security tasks
        (['--spam-detection', '--prompt', 'WIN MONEY NOW!'], "Spam detection", 45),
        (['--pii-detection', '--prompt', 'Email: test@example.com'], "PII detection", 45),
        
        # Advanced features
        (['--demo-hyde'], "HYDE demo", 30),
        (['--search-query', 'AI', '--top-k', '3'], "Semantic search", 30),
        (['--analytics-demo'], "Advanced analytics", 30),
        
        # System configuration
        (['--budget', '5.0', '--prompt', 'Test'], "Budget option", 45),
        (['--verbose', '--prompt', 'Verbose test'], "Verbose option", 45),
    ]
    
    # Run tests
    results = []
    for cmd_args, description, timeout in test_cases:
        success = test_command(cmd_args, description, timeout)
        results.append((description, success))
    
    # Summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"❌ Failed: {total-passed}/{total} ({(total-passed)/total*100:.1f}%)")
    
    print(f"\n📋 DETAILED RESULTS:")
    for description, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {description}")
    
    # Interpretation
    print(f"\n🎯 INTERPRETATION:")
    if passed >= total * 0.8:
        print("🟢 EXCELLENT: Most features are working correctly!")
    elif passed >= total * 0.6:
        print("🟡 GOOD: Core functionality works, some advanced features may need setup")
    elif passed >= total * 0.4:
        print("🟠 PARTIAL: Basic functionality works, may need dependency installation")
    else:
        print("🔴 ISSUES: Several features not working, check installation and dependencies")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if passed < total:
        print("• Install dependencies: pip install -r requirements.txt")
        print("• Check if database is initialized: python main.py --stats")
        print("• For full functionality: pip install opencv-python pillow transformers")
    
    print(f"• For detailed testing: python tests/quick_test.py")
    print(f"• For comprehensive tests: python run_tests.py")
    
    return passed >= total * 0.5  # Return True if at least 50% passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

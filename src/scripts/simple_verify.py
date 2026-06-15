#!/usr/bin/env python3
"""
Simple verification script to test subprocess calls
"""

import subprocess
import time

def test_simple_command():
    """Test the exact command that's failing in the test script."""
    print("Testing simple command...")
    
    cmd = ['python', 'main.py', '--text-classification', '--file', 'c:\\testfiles\\file.txt', '--prompt', 'Analyze the sentiment of this text', '--verbose']
    
    print(f"Command: {cmd}")
    
    start_time = time.time()
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        
        duration = time.time() - start_time
        
        print(f"Return code: {process.returncode}")
        print(f"Duration: {duration:.2f}s")
        print(f"Success: {process.returncode == 0}")
        
        if process.stdout:
            print(f"STDOUT (first 200 chars): {process.stdout[:200]}...")
        
        if process.stderr:
            print(f"STDERR (first 200 chars): {process.stderr[:200]}...")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_simple_command()

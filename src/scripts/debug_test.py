#!/usr/bin/env python3
"""
Debug script to test subprocess calls
"""

import subprocess
import time

def test_simple_command():
    """Test a simple command to see what's happening."""
    print("Testing simple command...")
    
    cmd = ['python', 'main.py', '--text-classification', '--file', 'c:\\testfiles\\file.txt', '--prompt', 'Analyze the sentiment of this text', '--verbose']
    
    print(f"Command: {' '.join(cmd)}")
    
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
            print(f"STDOUT (first 500 chars): {process.stdout[:500]}...")
        
        if process.stderr:
            print(f"STDERR (first 500 chars): {process.stderr[:500]}...")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_simple_command()

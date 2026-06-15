#!/usr/bin/env python3
"""
Simple test to verify the test script logic
"""

import subprocess
import time

def test_text_classification():
    """Test text-classification specifically."""
    print("Testing text-classification...")
    
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
        
        # Check for Magika usage
        magika_used = 'MAGIKA' in process.stdout or 'magika' in process.stdout.lower()
        print(f"Magika used: {magika_used}")
        
        if process.stdout:
            print(f"STDOUT contains MAGIKA: {'MAGIKA' in process.stdout}")
            print(f"STDOUT contains magika: {'magika' in process.stdout.lower()}")
        
        if process.stderr:
            print(f"STDERR (first 200 chars): {process.stderr[:200]}...")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_text_classification()

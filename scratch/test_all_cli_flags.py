import subprocess
import sys
import os
import time

# Configure utf-8 encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_cli_flag(cli_path, flag_args, expected_output_keywords=None, timeout=30):
    print("=" * 60)
    print(f"TESTING FLAG: {' '.join(flag_args)}")
    print("=" * 60)
    
    start_time = time.time()
    try:
        process = subprocess.Popen(
            [cli_path] + flag_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        stdout, _ = process.communicate(timeout=timeout)
        duration = time.time() - start_time
        
        print(stdout)
        print(f"Exit Code: {process.returncode} | Duration: {duration:.2f}s")
        
        if process.returncode != 0:
            print("[-] Result: FAILED (Non-zero exit code)")
            return False
            
        if expected_output_keywords:
            for keyword in expected_output_keywords:
                if keyword.lower() not in stdout.lower():
                    print(f"[-] Result: FAILED (Missing expected keyword: '{keyword}')")
                    return False
                    
        print("[+] Result: PASSED")
        return True
    except subprocess.TimeoutExpired:
        print(f"[-] Result: FAILED (Timeout after {timeout} seconds)")
        return False
    except Exception as e:
        print(f"[-] Result: FAILED (Exception: {e})")
        return False

def main():
    cli_path = r"D:\harfile\ModelFusion\target\release\cli.exe"
    if not os.path.exists(cli_path):
        print(f"ERROR: cli.exe not found at {cli_path}. Please build it first.")
        sys.exit(1)
        
    test_cases = [
        {
            "args": ["--help"],
            "keywords": ["ModelFusion", "Usage:", "Options:"]
        },
        {
            "args": ["-V"],
            "keywords": ["ModelFusion"]
        },
        {
            "args": ["--stats"],
            "keywords": ["statistics", "models", "database"]
        },
        {
            "args": ["--tasks"],
            "keywords": ["security", "text", "categories"]
        },
        {
            "args": ["--tasks", "text"],
            "keywords": ["text-generation", "translation"]
        },
        {
            "args": ["--decision-stats"],
            "keywords": ["decision", "metrics", "summary"]
        },
        {
            "args": ["--novel-ai-stats"],
            "keywords": ["novel", "innovation", "system"]
        },
        {
            "args": ["--performance-stats"],
            "keywords": ["performance", "metrics", "logged"]
        },
        {
            "args": ["--cache-stats"],
            "keywords": ["cache", "database", "healthy"]
        },
        {
            "args": ["--model-recommendations"],
            "keywords": ["recommendation"]
        },
        {
            "args": ["--model-ranking", "text-generation"],
            "keywords": ["ranking", "score"]
        },
        {
            "args": ["--analytics-demo"],
            "keywords": ["analytics", "demo", "healthy"]
        }
    ]
    
    results = []
    print("Starting CLI flags validation suite...")
    for i, tc in enumerate(test_cases):
        passed = run_cli_flag(cli_path, tc["args"], tc["keywords"])
        results.append((tc["args"], passed))
        print("\n")
        
        # Batch cooling: Pause after every 5 tests to let system resources settle
        if (i + 1) % 5 == 0 and (i + 1) < len(test_cases):
            print(f"[SYSTEM] Batch of 5 completed. Pausing for 3 seconds to cool down and clear memory...")
            time.sleep(3)
        
    print("=" * 60)
    print("CLI FLAGS VALIDATION SUMMARY")
    print("=" * 60)
    all_passed = True
    for args, passed in results:
        status = "PASSED" if passed else "FAILED"
        if not passed:
            all_passed = False
        print(f"cli {' '.join(args):45} : {status}")
    print("=" * 60)
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()

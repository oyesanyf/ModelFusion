import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SERVER_URL = "http://127.0.0.1:5000/orchestrate"

def test_command(prompt_text, expect_keyword=None):
    payload = {
        "prompt": f"System: You are HugOS AI assistant.\nUser: {prompt_text}",
        "backend": "ollama",
        "device": "gpu",
        "budget": 7,
        "strategy": "multi_objective",
        "fusion": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(SERVER_URL, data=data, headers={'Content-Type': 'application/json'})
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_bytes = response.read()
            elapsed = (time.time() - start_time) * 1000
            res_str = res_bytes.decode('utf-8', errors='ignore').strip()
            
            # Unpack json if chunked/wrapped
            try:
                obj = json.loads(res_str)
                content = obj.get("content", res_str)
            except Exception:
                content = res_str
                
            preview = content.replace('\n', ' ')[:90]
            passed = True
            if expect_keyword and expect_keyword.lower() not in content.lower():
                passed = False
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} [{elapsed:6.1f}ms] '{prompt_text}' -> {preview}...")
            return passed
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"  ❌ ERROR [{elapsed:6.1f}ms] '{prompt_text}' -> {e}")
        return False

if __name__ == "__main__":
    print("=" * 75)
    print(" MODELFUSION SERVER & MCP FAST-INTERCEPTION COMMAND VERIFICATION")
    print("=" * 75)
    
    commands_to_test = [
        ("@agent stats", "CPU"),
        ("@agent /stats", "CPU"),
        ("/stats", "CPU"),
        ("stats", "CPU"),
        ("@agent sysinfo", "Logical Cores"),
        ("/sysinfo", "Logical Cores"),
        ("@agent /mcp", "MCP"),
        ("/mcp", "MCP"),
        ("@agent /keys", "API Key"),
        ("/keys", "API Key"),
        ("@agent /tasks", "Tasks"),
        ("/tasks", "Tasks"),
        ("/cache-stats", "Cache"),
        ("/performance-stats", "Performance"),
        ("/decision-stats", "Decision"),
        ("@agent /invalidcmd", "Unknown"),
    ]
    
    passed = 0
    for cmd, expected in commands_to_test:
        if test_command(cmd, expected):
            passed += 1
            
    print("\n" + "=" * 75)
    print(f" RESULTS: {passed}/{len(commands_to_test)} Commands Verified Successfully")
    print("=" * 75)

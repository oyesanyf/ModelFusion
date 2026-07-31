import urllib.request
import json
import time

def test_command(prompt_text):
    url = "http://127.0.0.1:5000/orchestrate"
    payload = {
        "prompt": f"System: You are HugOS AI assistant.\nUser: {prompt_text}",
        "backend": "ollama",
        "device": "gpu",
        "budget": 7,
        "strategy": "multi_objective",
        "fusion": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_bytes = response.read()
            elapsed = (time.time() - start_time) * 1000
            res_str = res_bytes.decode('utf-8', errors='ignore')
            safe_str = res_str.encode('ascii', 'ignore').decode('ascii')
            print(f"[{elapsed:.1f}ms] Success for '{prompt_text}': {safe_str[:300]}")
            return True, res_str
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[{elapsed:.1f}ms] Error for '{prompt_text}': {e}")
        return False, str(e)

if __name__ == "__main__":
    print("Testing ModelFusion Unknown Command Interception on port 5000...")
    test_command("@agent /invalidcmd")
    test_command("@agent /stats")

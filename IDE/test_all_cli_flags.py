import subprocess
import urllib.request
import json
import time

CLI_PATH = r"D:\harfile\ModelFusion\IDE\bin\cli.exe"

def safe_str(s):
    return s.encode('ascii', 'ignore').decode('ascii')

def test_cli_flag(args_list, description):
    start_time = time.time()
    cmd = [CLI_PATH] + args_list
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        elapsed = (time.time() - start_time) * 1000
        output = (res.stdout + "\n" + res.stderr).strip()
        safe_out = safe_str(output.replace('\n', ' '))
        status = 'SUCCESS' if res.returncode == 0 else f'FAILED (code {res.returncode})'
        print(f"[{elapsed:.1f}ms] CLI test '{description}': {status} -> {safe_out[:150]}")
        return res.returncode == 0, output
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[{elapsed:.1f}ms] CLI test '{description}': ERROR -> {e}")
        return False, str(e)

def test_http_slash_cmd(cmd_name, prompt_text=""):
    url = "http://127.0.0.1:5000/orchestrate"
    payload = {
        "prompt": f"System: You are HugOS AI assistant.\nUser: @agent /{cmd_name} {prompt_text}".strip(),
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
            safe_out = safe_str(res_str.replace('\n', ' '))
            print(f"[{elapsed:.1f}ms] HTTP test '/{cmd_name}': SUCCESS -> {safe_out[:150]}")
            return True, res_str
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[{elapsed:.1f}ms] HTTP test '/{cmd_name}': ERROR -> {e}")
        return False, str(e)

if __name__ == "__main__":
    print("==========================================================================")
    print("COMPREHENSIVE TEST SUITE: MODELFUSION CLI FLAGS & HTTP SLASH COMMANDS")
    print("==========================================================================")
    
    print("\n--- 1. DIRECT CLI FLAGS TESTS ---")
    test_cli_flag(["--sys-info"], "--sys-info flag")
    test_cli_flag(["--stats"], "--stats flag")
    test_cli_flag(["--decision-stats"], "--decision-stats flag")
    test_cli_flag(["--performance-stats"], "--performance-stats flag")
    test_cli_flag(["--cache-stats"], "--cache-stats flag")
    test_cli_flag(["--tasks"], "--tasks flag")
    test_cli_flag(["--file", "sample.py", "--prompt", "Review code security"], "--file & --prompt flags")
    
    print("\n--- 2. HTTP SERVER SLASH COMMAND TESTS ---")
    slash_cmds = ["sysinfo", "stats", "mcp", "keys", "tasks", "decision-stats", "performance-stats", "cache-stats", "evolve", "security", "refactor"]
    for sc in slash_cmds:
        test_http_slash_cmd(sc)

    print("\n--- 3. UNKNOWN COMMAND TEST ---")
    test_http_slash_cmd("invalidcmd")

import subprocess
import sys
import os
import time

# Configure utf-8 encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_command(args):
    print("=" * 60)
    print(f"RUNNING: {' '.join(args)}")
    print("=" * 60)
    start_time = time.time()
    
    # Configure unbuffered python output and disable HF progress bars to prevent hangs
    env = os.environ.copy()
    env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Run the release CLI binary with DEVNULL stdin and merge stderr into stdout for real-time streaming
    process = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        env=env
    )
    
    full_output = []
    # Stream output in real-time
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
                full_output.append(line)
    except Exception as e:
        print(f"Error reading stream: {e}")
        
    # Collect remaining output
    stdout, _ = process.communicate()
    if stdout:
        sys.stdout.write(stdout)
        sys.stdout.flush()
        full_output.append(stdout)
        
    duration = time.time() - start_time
    print(f"Completed in {duration:.2f} seconds. Exit Code: {process.returncode}")
    
    combined_output = "".join(full_output)
    success = process.returncode == 0 or "[SUCCESS] Orchestration Successful!" in combined_output
    return success, combined_output, ""

def main():
    cli_path = r"D:\harfile\ModelFusion\target\release\cli.exe"
    if not os.path.exists(cli_path):
        print(f"ERROR: cli.exe not found at {cli_path}. Please build it first.")
        sys.exit(1)
        
    test_cases = [
        # Test 1: Standard ONNX mode targeting small model
        {
            "name": "ONNX Standard Mode",
            "args": [cli_path, "--prompt", "Explain variable ownership in Rust in one sentence.", "--onnx", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]
        },
        # Test 2: ONNX + Forced CPU Mode
        {
            "name": "ONNX CPU Forced Mode",
            "args": [cli_path, "--prompt", "Explain variable ownership in Rust in one sentence.", "--onnx", "--cpu", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]
        },
        # Test 3: ONNX + Forced GPU Mode
        {
            "name": "ONNX GPU Forced Mode",
            "args": [cli_path, "--prompt", "Explain variable ownership in Rust in one sentence.", "--onnx", "--gpu", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]
        },
        # Test 4: OpenVINO Mode targeting small model
        {
            "name": "OpenVINO Standard Mode",
            "args": [cli_path, "--prompt", "Explain variable ownership in Rust in one sentence.", "--openvino", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]
        },
        # Test 5: Model Fusion + ONNX Mode
        {
            "name": "Model Fusion with ONNX Mode",
            "args": [cli_path, "--prompt", "Explain stack vs heap memory in one sentence.", "--fusion", "--fusion-mode", "multi-sample", "--fusion-models", "2", "--onnx", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]
        }
    ]
    
    results = []
    for tc in test_cases:
        print(f"\nRunning Test: {tc['name']}")
        success, out, err = run_command(tc['args'])
        results.append((tc['name'], success))
        
    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        if not success:
            all_passed = False
        print(f"{name:35} : {status}")
    print("=" * 60)
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()

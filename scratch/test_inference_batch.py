"""
Small-batch CLI INFERENCE flag tester.
Runs inference tests 1 at a time with cooling pauses.
Usage: python scratch/test_inference_batch.py [batch_number]
  batch_number: 1-5 (omit to run all sequentially)
"""
import subprocess
import sys
import os
import time
import gc

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CLI = r"D:\harfile\ModelFusion\target\release\cli.exe"
TIMEOUT = 120  # inference can take longer

env = os.environ.copy()
env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
env["PYTHONUNBUFFERED"] = "1"


def run_one(name, flag_args):
    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"  CMD:  cli.exe {' '.join(flag_args)}")
    print(f"{'='*60}")
    start = time.time()
    try:
        proc = subprocess.Popen(
            [CLI] + flag_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore",
            env=env,
        )
        # Stream output line by line
        lines = []
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                sys.stdout.write(f"  | {line}")
                sys.stdout.flush()
                lines.append(line)
            # Check timeout
            if time.time() - start > TIMEOUT:
                proc.kill()
                proc.wait()
                print(f"  [-] KILLED after {TIMEOUT}s timeout")
                return False

        # Get remaining output
        remaining, _ = proc.communicate(timeout=5)
        if remaining:
            for rl in remaining.splitlines():
                sys.stdout.write(f"  | {rl}\n")
            lines.append(remaining)

        dur = time.time() - start
        combined = "".join(lines)
        print(f"  Exit Code: {proc.returncode} | Duration: {dur:.2f}s")

        success = proc.returncode == 0 or "[SUCCESS]" in combined
        print(f"  [+] PASSED" if success else f"  [-] FAILED")
        return success

    except Exception as e:
        print(f"  [-] FAILED (exception: {e})")
        return False


ALL_BATCHES = [
    # Batch 1: ONNX standard
    [
        ("ONNX Standard", ["--prompt", "Say hello in one word.", "--onnx", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]),
    ],
    # Batch 2: ONNX + CPU forced
    [
        ("ONNX CPU Forced", ["--prompt", "Say hello in one word.", "--onnx", "--cpu", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]),
    ],
    # Batch 3: ONNX + GPU forced
    [
        ("ONNX GPU Forced", ["--prompt", "Say hello in one word.", "--onnx", "--gpu", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]),
    ],
    # Batch 4: OpenVINO standard (uses cached model)
    [
        ("OpenVINO Standard", ["--prompt", "Say hello in one word.", "--openvino", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]),
    ],
    # Batch 5: Fusion + ONNX
    [
        ("Fusion ONNX multi-sample", ["--prompt", "Say hello in one word.", "--fusion", "--fusion-mode", "multi-sample", "--fusion-models", "2", "--onnx", "--model", "HuggingFaceTB/SmolLM2-135M-Instruct"]),
    ],
]


def run_batch(batch_num):
    idx = batch_num - 1
    if idx < 0 or idx >= len(ALL_BATCHES):
        print(f"Invalid batch {batch_num}. Valid: 1-{len(ALL_BATCHES)}")
        return []
    tests = ALL_BATCHES[idx]
    results = []
    print(f"\n{'#'*60}")
    print(f"  INFERENCE BATCH {batch_num}/{len(ALL_BATCHES)}")
    print(f"{'#'*60}")
    for name, args in tests:
        passed = run_one(name, args)
        results.append((name, passed))
        gc.collect()
        time.sleep(2)
    return results


def main():
    if not os.path.exists(CLI):
        print(f"ERROR: cli.exe not found at {CLI}")
        sys.exit(1)

    if len(sys.argv) > 1:
        batch_num = int(sys.argv[1])
        results = run_batch(batch_num)
    else:
        results = []
        for b in range(1, len(ALL_BATCHES) + 1):
            results.extend(run_batch(b))
            if b < len(ALL_BATCHES):
                print(f"\n  [COOLING] 8-second pause before next batch...")
                time.sleep(8)

    print(f"\n{'='*60}")
    print(f"  INFERENCE RESULTS SUMMARY")
    print(f"{'='*60}")
    all_ok = True
    for name, passed in results:
        tag = "PASS" if passed else "FAIL"
        if not passed:
            all_ok = False
        print(f"  [{tag}] {name}")
    print(f"{'='*60}")
    print(f"  Total: {len(results)} | Passed: {sum(1 for _,p in results if p)} | Failed: {sum(1 for _,p in results if not p)}")

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

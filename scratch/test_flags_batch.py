"""
Small-batch CLI flag tester.
Runs 2 tests per batch with cooling pauses to prevent system freezes.
Usage: python scratch/test_flags_batch.py [batch_number]
  batch_number: 1-6 (omit to run all batches sequentially)
"""
import subprocess
import sys
import os
import time
import gc

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CLI = r"D:\harfile\ModelFusion\target\release\cli.exe"
TIMEOUT = 60  # seconds per test (--stats can take ~5-15s on 2.9M model DB)


def run_one(flag_args, keywords=None):
    label = ' '.join(flag_args)
    print(f"\n{'='*60}")
    print(f"  TESTING: cli.exe {label}")
    print(f"{'='*60}")
    start = time.time()
    try:
        proc = subprocess.Popen(
            [CLI] + flag_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore",
        )
        stdout, _ = proc.communicate(timeout=TIMEOUT)
        dur = time.time() - start
        # Print first 40 lines max to keep output manageable
        lines = stdout.splitlines()
        for line in lines[:40]:
            print(f"  | {line}")
        if len(lines) > 40:
            print(f"  | ... ({len(lines)-40} more lines)")
        print(f"  Exit Code: {proc.returncode} | Duration: {dur:.2f}s")

        if proc.returncode != 0:
            print("  [-] FAILED (non-zero exit)")
            return False

        if keywords:
            for kw in keywords:
                if kw.lower() not in stdout.lower():
                    print(f"  [-] FAILED (missing keyword: '{kw}')")
                    return False

        print("  [+] PASSED")
        return True

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print(f"  [-] FAILED (timeout after {TIMEOUT}s — process killed)")
        return False
    except Exception as e:
        print(f"  [-] FAILED (exception: {e})")
        return False


# ── All test cases grouped into small batches of 2 ──────────────────────────
ALL_BATCHES = [
    # Batch 1: Help & Version
    [
        (["--help"], ["Usage", "Options"]),
        (["-V"], None),
    ],
    # Batch 2: Stats flags
    [
        (["--stats"], ["statistics"]),
        (["--cache-stats"], ["cache"]),
    ],
    # Batch 3: Task listing
    [
        (["--tasks"], None),
        (["--tasks", "text"], None),
    ],
    # Batch 4: Analytics flags
    [
        (["--decision-stats"], None),
        (["--performance-stats"], None),
    ],
    # Batch 5: Model intelligence flags
    [
        (["--novel-ai-stats"], None),
        (["--model-recommendations"], None),
    ],
    # Batch 6: Ranking & Analytics demo
    [
        (["--model-ranking", "text-generation"], None),
        (["--analytics-demo"], None),
    ],
]


def run_batch(batch_num):
    """Run a single batch (1-indexed). Returns list of (label, passed)."""
    idx = batch_num - 1
    if idx < 0 or idx >= len(ALL_BATCHES):
        print(f"Invalid batch number {batch_num}. Valid: 1-{len(ALL_BATCHES)}")
        return []
    tests = ALL_BATCHES[idx]
    results = []
    print(f"\n{'#'*60}")
    print(f"  BATCH {batch_num}/{len(ALL_BATCHES)}  ({len(tests)} tests)")
    print(f"{'#'*60}")
    for args, kws in tests:
        passed = run_one(args, kws)
        results.append((' '.join(args), passed))
        gc.collect()
        time.sleep(1)  # small pause between tests within a batch
    return results


def main():
    if not os.path.exists(CLI):
        print(f"ERROR: cli.exe not found at {CLI}")
        sys.exit(1)

    # If a batch number is given, run only that batch
    if len(sys.argv) > 1:
        batch_num = int(sys.argv[1])
        results = run_batch(batch_num)
    else:
        # Run all batches with cooling pauses
        results = []
        for b in range(1, len(ALL_BATCHES) + 1):
            results.extend(run_batch(b))
            if b < len(ALL_BATCHES):
                print(f"\n  [COOLING] 5-second pause before next batch...")
                time.sleep(5)

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    all_ok = True
    for label, passed in results:
        tag = "PASS" if passed else "FAIL"
        if not passed:
            all_ok = False
        print(f"  [{tag}] cli.exe {label}")
    print(f"{'='*60}")
    print(f"  Total: {len(results)} | Passed: {sum(1 for _,p in results if p)} | Failed: {sum(1 for _,p in results if not p)}")

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

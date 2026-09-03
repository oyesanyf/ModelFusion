# Handoff Report — Milestone 3 Python & AVO Concurrency Challenger

**Agent**: Python & AVO Concurrency Challenger (`challenger_m3_python`)  
**Parent Agent**: Orchestrator (`02870692-b65d-4b30-9bd8-8d719d3789f3`)  
**Milestone**: M3 — Python & AVO/Evolutionary Systems Concurrency Safety Audit  
**Artifact Path**: `d:/harfile/ModelFusion/.agents/challenger_m3_python/challenge_python.md`  

---

## 1. Observation

Direct code inspections and empirical trace verifications confirmed the following critical defects in the Python subsystems:

1. **Subprocess Timeout Zombie Leaks**:
   - `canned_benchmark/draco_evaluator.py:546–570`:
     ```python
     proc = await asyncio.create_subprocess_exec(...)
     stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
     ...
     except asyncio.TimeoutError:
         print("Warning: Rust execution timed out.")
         return "Rust execution timeout."
     ```
     `proc.kill()` and `await proc.wait()` are omitted when `asyncio.TimeoutError` occurs.
   - `scratch/test_all_cli_flags.py:45–47`:
     ```python
     except subprocess.TimeoutExpired:
         print(f"[-] Result: FAILED (Timeout after {timeout} seconds)")
         return False
     ```
     `process.kill()` and `process.wait()` are omitted upon `TimeoutExpired`. (In contrast, `scratch/test_flags_batch.py:58–59` correctly calls `proc.kill()` and `proc.wait()`).

2. **Worker Pool Starvation & Polling Deadlock in OpenEvolve**:
   - `src/openevolve/openevolve/process_parallel.py:539–546`:
     ```python
     for iteration, future in list(pending_futures.items()):
         if future.done():
             completed_iteration = iteration
             break
     if completed_iteration is None:
         await asyncio.sleep(0.01)
         continue
     ```
     The polling loop only processes futures where `future.done()` is True. A hung worker task never marks its future as `done()`, causing the coordinator to spin indefinitely on `await asyncio.sleep(0.01)`.
   - `src/openevolve/openevolve/process_parallel.py:753–754`:
     ```python
     except FutureTimeoutError:
         ...
         future.cancel()
     ```
     In Python's `ProcessPoolExecutor`, calling `future.cancel()` on an already running task returns `False` and cannot terminate or interrupt the child worker process. As stuck tasks accumulate, all worker processes in the pool become permanently blocked, causing 100% worker pool starvation.

3. **Stdout Logging Pollution in ONNX Runner**:
   - `src/scripts/run_model_onnx.py:51, 55, 63, 71, 80, 84, 92, 100, 110, 129`:
     Informational logging messages (e.g. `[ONNX] ✅ Using cached converted model...`, `[ONNX] 🔄 Exporting model...`) are printed to `stdout` instead of `file=sys.stderr`. When callers attempt to parse raw model outputs or structured JSON from `stdout`, the output is contaminated by log lines and emojis.

4. **Windows File Lock Violations (`WinError 32`) & Temporary File Retention**:
   - `src/openevolve/openevolve/evaluator.py:157, 289–291, 350–354`:
     Evaluation tasks execute in a `ThreadPoolExecutor` via `loop.run_in_executor()`. When `asyncio.wait_for` times out, the worker thread cannot be killed. In `finally: os.unlink(temp_file_path)`, Windows raises `PermissionError: [WinError 32]` because the uncancelled background thread still holds an open file handle.
   - `src/scripts/run_model_openvino.py:196–213`:
     Hardcoded temporary path `_temp.onnx` lacks unique naming and lacks a `try...finally` block around `core.read_model(onnx_path)`, leaking temporary ONNX files if conversion fails.

5. **Non-Atomic File Persistence**:
   - `src/openevolve/openevolve/database.py:654–656, 851–853`:
     `open(os.path.join(save_path, "metadata.json"), "w")` directly truncates the file to 0 bytes before `json.dump()`, risking permanent database corruption if interrupted mid-write.
   - `canned_benchmark/draco_evaluator.py:179–181`:
     `open(CACHE_FILE, "w")` directly truncates `draco_api_cache.json`.

6. **Missing CUDA OOM Fallback & Script Drift**:
   - `src/scripts/run_model_transformers.py:250–252` lacks the `torch.cuda.OutOfMemoryError` CPU fallback block present in `IDE/src/scripts/run_model_transformers.py:81–103`.
   - `src/scripts/run_model_transformers.py:238–240`: `inputs.get("input_ids", [[]])` can return `None` when the key exists with value `None`, triggering `TypeError` in `zip()`.

---

## 2. Logic Chain

1. **Subprocess Lifecycle Reasoning**:
   - Observation 1.1 shows `proc.communicate()` wrapped in `wait_for` without `proc.kill()` in the exception handler.
   - Observation 1.2 shows `Popen.communicate()` catching `TimeoutExpired` without `process.kill()`.
   - Python stdlib documentation and empirical PoC confirm that `wait_for` and `communicate` timeouts do NOT kill the underlying OS process.
   - *Inference*: Any timed-out inference or CLI flag test creates an orphaned background process that retains open handles, memory, and CPU resources.

2. **Process Pool Starvation Reasoning**:
   - Observation 2.1 shows that `pending_futures` are only popped when `future.done()` is True.
   - A hung task in a child process will never set `future.done() = True`.
   - Therefore, the coordinator loop remains trapped in `await asyncio.sleep(0.01)`.
   - Observation 2.2 shows `future.cancel()` used as a cleanup mechanism. Standard library `concurrent.futures.Future.cancel()` returns `False` and is a no-op once a task begins execution.
   - *Inference*: Worker slots running hung tasks are permanently unrecoverable, leading to total pipeline starvation.

3. **Stream Separation Reasoning**:
   - Observation 3 shows 9 `print("[ONNX] ...")` calls targeting `stdout`.
   - `run_model_openvino.py` and `run_model_transformers.py` explicitly send all status messages to `sys.stderr`.
   - *Inference*: Downstream consumers (Rust CLI subprocess runner and VS Code extension) that parse `stdout` for model completions will fail with deserialization / formatting errors when using the ONNX backend.

4. **Resource Locking & Atomic Persistence Reasoning**:
   - Observation 4 shows thread execution without cancellation combined with immediate `os.unlink()` on Windows. Windows NT kernel forbids unlinking open files.
   - Observation 5 shows `open(path, 'w')` opening files in write-truncate mode before writing JSON.
   - *Inference*: Process interruption during `save()` leaves 0-byte corrupted JSON checkpoints, destroying MAP-Elites grids and DRACO benchmark caches.

---

## 3. Caveats

- **External C/C++ Extensions**: Internal runtime behavior of external binary libraries (`onnxruntime`, `openvino_genai`, PyTorch CUDA runtime) is treated as a black box and was not modified.
- **Visualizer Web Interface**: Security and concurrency analysis was focused on core backend pipelines, inference scripts, and test harnesses; the standalone Flask visualizer dashboard was reviewed for global state usage but not live penetration-tested.

---

## 4. Conclusion

All 6 primary vulnerability vectors identified in the Python survey are **VALID, REPRODUCIBLE, and CRITICAL/HIGH RISK**. 

Specifically:
- Subprocess timeout handling requires mandatory `proc.kill()` and `proc.wait()` in all exception paths.
- OpenEvolve worker parallelism requires deadline-based future expiration and worker process recycling.
- `run_model_onnx.py` must redirect all logging prints to `sys.stderr`.
- File writes in `database.py` and `draco_evaluator.py` must use the atomic staging pattern (`.tmp` + `os.replace`).
- Evaluator temporary file unlinking on Windows must guard against `PermissionError: [WinError 32]`.
- Script duplication between `src/scripts/` and `IDE/src/scripts/` must be consolidated with `src/scripts/` as the single canonical source of truth.

---

## 5. Verification Method

Independent verification of the empirical challenge results can be conducted via:

1. **Subprocess Timeout Leak Verification**:
   Inspect `canned_benchmark/draco_evaluator.py:568–571` and `scratch/test_all_cli_flags.py:45–47` to confirm the absence of `proc.kill()` / `proc.wait()`. Compare with `scratch/test_flags_batch.py:57–60`.
2. **Process Pool Starvation Verification**:
   Inspect `src/openevolve/openevolve/process_parallel.py:538–546` (polling loop stuck on `future.done()`) and `747–755` (`future.cancel()` on `ProcessPoolExecutor`).
3. **Stdout Logging Verification**:
   Inspect `src/scripts/run_model_onnx.py:51, 55, 63, 71, 80, 84, 92, 100, 110` and verify absence of `file=sys.stderr`.
4. **Windows Lock & Atomic Write Verification**:
   Inspect `src/openevolve/openevolve/evaluator.py:289–291` and `src/openevolve/openevolve/database.py:654, 851`.
5. **Full Challenge Report**:
   Review complete empirical proof and remediation specifications in `d:/harfile/ModelFusion/.agents/challenger_m3_python/challenge_python.md`.

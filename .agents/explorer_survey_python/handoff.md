# Handoff Report — Python & AVO Systems Safety Audit

**Date**: 2026-09-01  
**Agent**: Python & AVO Systems Explorer  
**Working Directory**: `d:/harfile/ModelFusion/.agents/explorer_survey_python/`  
**Parent Conversation ID**: `02870692-b65d-4b30-9bd8-8d719d3789f3`  
**Handoff Type**: Hard Handoff (Task Complete)

---

## 1. Observation

A systematic static and structural inspection was performed across all Python modules, OpenEvolve evolutionary pipelines, AVO runners, inference backends, MCP servers, and tooling in the ModelFusion repository.

Key Direct Code Observations:

1. **Subprocess Timeout Zombie Leaks in Benchmark & CLI Harnesses**:
   - `canned_benchmark/draco_evaluator.py:546–556`:
     ```python
     proc = await asyncio.create_subprocess_exec(
         str(binary_path),
         "--fusion",
         "--prompt", prompt,
         stdout=asyncio.subprocess.PIPE,
         stderr=asyncio.subprocess.PIPE,
         cwd=str(project_root),
         env=env
     )
     stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
     ```
     When `asyncio.wait_for` raises `asyncio.TimeoutError` at line 556, `proc.kill()` and `await proc.wait()` are never called; the subprocess is orphaned and remains running indefinitely.
   - `scratch/test_all_cli_flags.py:45–47`:
     ```python
     except subprocess.TimeoutExpired:
         print(f"[-] Result: FAILED (Timeout after {timeout} seconds)")
         return False
     ```
     `process.communicate(timeout=timeout)` throws `TimeoutExpired`, but `process.kill()` and `process.wait()` are omitted.

2. **Multiprocessing Worker Pool Starvation & Unkillable Threads**:
   - `src/openevolve/openevolve/process_parallel.py:747–755`:
     ```python
     except FutureTimeoutError:
         logger.error(
             f"⏰ Iteration {completed_iteration} timed out after {timeout_seconds}s ... Canceling future..."
         )
         future.cancel()
     ```
     In Python's `ProcessPoolExecutor`, calling `future.cancel()` on an already executing future does not terminate the underlying worker process. Stalled worker tasks run forever, reducing pool worker capacity to zero over time.
   - `src/openevolve/openevolve/evaluator.py:350–355`:
     ```python
     async def run_evaluation():
         loop = asyncio.get_event_loop()
         return await loop.run_in_executor(None, self.evaluate_function, program_path)
     result = await asyncio.wait_for(run_evaluation(), timeout=self.config.timeout)
     ```
     Evaluations are submitted to Python's default thread pool. When `wait_for` times out, background threads cannot be killed or interrupted.

3. **Stdout Logging Output Pollution in ONNX Runner**:
   - `src/scripts/run_model_onnx.py:51, 80, 110`:
     ```python
     print(f"[ONNX] ✅ Using cached converted model at {cache_dir}")
     print(f"[ONNX] 🔄 Exporting model {model_id} to ONNX format (first-time export)...")
     print(f"[ONNX] Saving converted model to {cache_dir}...")
     ```
     These informational messages are printed to `sys.stdout` instead of `sys.stderr`. When the ModelFusion Rust engine or IDE extensions invoke `run_model_onnx.py` as a subprocess and capture stdout for inference output, these log messages pollute the response text.

4. **Temporary File Collisions and Cleanup Failures on Windows**:
   - `src/scripts/run_model_openvino.py:196, 210–213`:
     ```python
     onnx_path = os.path.join(output_path, "_temp.onnx")
     ...
     ov_model = core.read_model(onnx_path)
     try:
         os.remove(onnx_path)
     except OSError:
         pass
     ```
     Uses fixed filename `_temp.onnx` instead of `tempfile.NamedTemporaryFile`. If `core.read_model()` throws an exception before line 210, `_temp.onnx` is never deleted because cleanup is not in a `finally` block. Concurrent exports collide on the same path.
   - `src/openevolve/openevolve/evaluator.py:157, 289–291`:
     ```python
     with tempfile.NamedTemporaryFile(suffix=self.program_suffix, delete=False) as temp_file:
     ...
     finally:
         if os.path.exists(temp_file_path):
             os.unlink(temp_file_path)
     ```
     When an evaluation times out in `loop.run_in_executor`, the background worker thread still holds an open file handle, causing Windows `PermissionError: [WinError 32]` during `os.unlink` in `finally:`.

5. **Non-Atomic Disk Persistence**:
   - `src/openevolve/openevolve/database.py:654–656, 851–853`:
     ```python
     with open(os.path.join(save_path, "metadata.json"), "w") as f:
         json.dump(metadata, f)
     ...
     with open(program_path, "w") as f:
         json.dump(program_dict, f)
     ```
     Direct non-atomic file writing can leave corrupted/partial JSON files if process termination occurs mid-write.
   - `canned_benchmark/draco_evaluator.py:179–181`: `save_cache()` writes directly to `draco_api_cache.json` without atomic rename, exposing the 1.8MB cache file to corruption.

6. **Code Duplication Drift**:
   - `src/scripts/run_model_transformers.py` (256 lines) contains multimodal Whisper/Vision2Seq and chat templates, but lacks CUDA OOM fallback.
   - `IDE/src/scripts/run_model_transformers.py` (110 lines) is an older text-only version, but has `except torch.cuda.OutOfMemoryError:` CPU retry logic.

---

## 2. Logic Chain

1. **Inference Pipeline Reliability**:
   - *Premise*: Model backend runners (`run_model_onnx.py`, `run_model_transformers.py`, `run_model_openvino.py`) are invoked via subprocess by the ModelFusion Rust core and IDE backend.
   - *Step 1*: Subprocess communication relies on `stdout` strictly containing generated model tokens, and `stderr` containing diagnostic logging.
   - *Step 2*: Because `run_model_onnx.py` emits `[ONNX] ...` logs to stdout (Observation 3), any consumer capturing stdout will parse corrupt output strings containing status text.
   - *Step 3*: Because `run_model_transformers.py` in `src/scripts/` lacks the CUDA OOM handler found in `IDE/src/scripts/` (Observation 6), any large model exceeding GPU VRAM immediately causes a hard crash rather than falling back gracefully to CPU.

2. **Subprocess Lifecycle & Concurrency Resilience**:
   - *Premise*: Long-running evolution evaluations and benchmarks run multiple concurrent jobs under timeouts.
   - *Step 1*: When timeouts trigger in `draco_evaluator.py`, `test_all_cli_flags.py`, or `evaluator.py` without terminating child processes or worker threads (Observations 1 & 2), background CPU/GPU tasks continue consuming hardware resources indefinitely.
   - *Step 2*: In `ProcessPoolExecutor`, canceled futures leave workers in the pool running old iterations (Observation 2), causing deadlocks and resource starvation for subsequent iterations.

3. **File I/O Integrity**:
   - *Premise*: Evolutionary algorithms iterate over hundreds of checkpoints, saving state after each generation.
   - *Step 1*: Non-atomic writes in `database.py` (Observation 5) directly overwrite metadata and program JSON files in place.
   - *Step 2*: If interrupted or out-of-disk conditions occur, state files are corrupted, preventing checkpoint recovery on resume.

---

## 3. Caveats

- **External Hardware Dependencies**: Evaluation of CUDA execution provider fallback and GPU memory thresholds was performed via static code analysis, as GPU device availability is hardware-dependent.
- **Third-Party Model Weights**: HuggingFace API downloads and remote model loading endpoints were not actively downloaded during the read-only audit to avoid network bandwidth saturation.
- **No caveats** regarding repository code layout, script paths, or AST inspection.

---

## 4. Conclusion

The ModelFusion Python ecosystem features a robust, modular design spanning multimodal inference backends, MCP server integrations, and evolutionary search algorithms. However, 5 high-risk issues require immediate remediation:
1. Subprocess zombie/orphan leaks on timeouts in `draco_evaluator.py` and `test_all_cli_flags.py`.
2. Multiprocessing slot starvation from unkillable tasks in `process_parallel.py` and thread leaks in `evaluator.py`.
3. Stdout logging pollution in `run_model_onnx.py`.
4. Windows file lock collisions and temporary file retention in `run_model_openvino.py` and `evaluator.py`.
5. Non-atomic file persistence in `database.py` and `draco_evaluator.py`.

A detailed inventory, risk evaluation table, and 3-phase refactoring roadmap have been authored in `d:/harfile/ModelFusion/.agents/explorer_survey_python/survey_python.md`.

---

## 5. Verification Method

To independently verify all findings and confirm fixes:

1. **Verify Stdout Cleanliness in ONNX Runner**:
   ```bash
   python src/scripts/run_model_onnx.py HuggingFaceTB/SmolLM2-135M-Instruct "Hello" 5 0.0 cpu
   ```
   *Pass Condition*: Output on stdout contains exclusively the generated completion text; no `[ONNX] ...` log lines appear in stdout.

2. **Verify Process Killing on Subprocess Timeout**:
   Inspect `canned_benchmark/draco_evaluator.py` line 556 and `scratch/test_all_cli_flags.py` line 45 to ensure `proc.kill()` and `proc.wait()` / `await proc.wait()` are executed on `TimeoutExpired` / `TimeoutError`.

3. **Verify E2E Test Suite Integrity**:
   ```bash
   python tests/e2e/run_all_e2e.py
   ```
   *Pass Condition*: All 218 test cases across Tiers 1–4 complete with 100% pass rate.

4. **Inspect Generated Survey Document**:
   View `d:/harfile/ModelFusion/.agents/explorer_survey_python/survey_python.md` for complete line references and recommendations.

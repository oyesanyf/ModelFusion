# ModelFusion Codebase Safety Audit — Python & AVO Systems Survey

**Date**: 2026-09-01  
**Auditor**: Python & AVO Systems Explorer  
**Status**: Comprehensive Assessment Complete  
**Scope**: All Python scripts in `src/scripts/`, `IDE/src/scripts/`, OpenEvolve & AVO pipelines (`src/openevolve/`), MCP servers & harness tooling (`IDE/`, `tests/mcp/`), E2E test suites (`tests/e2e/`), benchmarks (`canned_benchmark/`), and root/scratch tooling.

---

## Executive Summary

A comprehensive safety, concurrency, resource management, and resilience audit was conducted across the 96+ Python files within the ModelFusion repository.

### Key Risk Ratings
| Risk Level | Finding Count | Primary Areas Affected |
| :--- | :--- | :--- |
| 🔴 **High Risk** | 5 | Subprocess zombie leaks on timeout, `ProcessPoolExecutor` hung task starvation, stdout logging corruption in ONNX runner, uncancelable thread executor leaks in evaluator, non-atomic database serialization. |
| 🟡 **Medium Risk** | 8 | Codebase duplication drift between `src/scripts/` and `IDE/src/scripts/`, blocking `readline()` without socket/pipe timeout in MCP harness, global `sys.path`/`sys.modules` mutations, lack of CUDA OOM fallback in multimodal transformers runner, temporary file locking on Windows. |
| 🟢 **Low Risk** | 6 | Hardcoded developer-specific local paths in utility patchers, unhandled CLI `ValueError` on malformed integer/float arguments, duplicate imports, broad `except Exception:` catches without structured error classification. |

---

## 1. Codebase Inventory & Architectural Mapping

```
ModelFusion Python Architecture
├── Domain 1: Model Backend Runners & Inference Scripts
│   ├── src/scripts/run_model_openvino.py (422 lines) — OpenVINO GenAI & Classic OV token generation
│   ├── src/scripts/run_model_transformers.py (256 lines) — Multimodal Whisper/Vision & CausalLM
│   ├── src/scripts/run_model_onnx.py (137 lines) — Optimum ONNX Runtime exporter and runner
│   ├── src/scripts/run_model_vllm.py (111 lines) — vLLM multi-GPU tensor-parallel runner
│   ├── src/scripts/cache_ov_hub.py (334 lines) — OpenVINO Hub pre-converted INT4 downloader & manager
│   ├── src/scripts/prepare_model_openvino.py (182 lines) — optimum-cli IR conversion tool
│   ├── src/scripts/getvino.py (65 lines) — HuggingFace OpenVINO zoo bulk downloader
│   ├── src/scripts/check_openvino.py (43 lines) — Environment diagnostics probe
│   └── IDE/src/scripts/ (8 mirrored/drifted files + onnx_openvino_demo.py)
│
├── Domain 2: OpenEvolve Evolutionary Pipeline & AVO Core
│   ├── src/openevolve/openevolve/controller.py (594 lines) — Evolution coordinator & checkpointing
│   ├── src/openevolve/openevolve/process_parallel.py (832 lines) — Multiprocess worker pool & island distribution
│   ├── src/openevolve/openevolve/evaluator.py (728 lines) — Cascaded execution & LLM evaluator feedback
│   ├── src/openevolve/openevolve/database.py (2,614 lines) — MAP-Elites grid, island migration, artifact storage
│   ├── src/openevolve/openevolve/api.py (650 lines) — High-level library API & tempfile generation
│   ├── src/openevolve/openevolve/evolution_trace.py (603 lines) — RL trace logging (JSONL/JSON/HDF5)
│   ├── src/openevolve/openevolve/embedding.py (97 lines) — Embedding client for novelty judge
│   ├── src/openevolve/openevolve/novelty_judge.py (50 lines) — Cosine similarity rejection sampling
│   ├── src/openevolve/openevolve/config.py (468 lines) — Hierarchical dataclass configs
│   ├── src/openevolve/openevolve/cli.py (197 lines) — OpenEvolve CLI runner
│   ├── src/openevolve/scripts/visualizer.py (235 lines) — Flask web dashboard
│   ├── src/openevolve/scripts/manual.py (144 lines) — Interactive manual queue blueprint
│   └── src/openevolve/examples/ (40+ task adapter, benchmark, evaluator scripts)
│
├── Domain 3: MCP Servers, IDE IPC & Patch Tooling
│   ├── IDE/test_mcp_full_harness.py (714 lines) — Complete 91-tool MCP test harness
│   ├── IDE/test_mcp_client.py (95 lines) — Basic MCP JSON-RPC client
│   ├── IDE/test_server_client.py (84 lines) — HTTP IPC (/orchestrate) verification
│   ├── IDE/test_datascience_client.py (62 lines) — Dataset attachment & analyst testing
│   ├── IDE/fix_slash_commands.py (367 lines) — XML context sanitizer & command router
│   ├── IDE/patch_mcp_tools.py (120 lines) — Rust CLI MCP tools registration patcher
│   ├── IDE/patch_evolve_save.py (55 lines) — Inline diff code presenter patcher
│   ├── IDE/patch_nonblocking_startup.py (25 lines) — Extension startup delay patcher
│   ├── IDE/patch_native_stats.py (74 lines) — Fast interception router patcher
│   ├── root/patch_spawn_server.py (28 lines) — VSCode server spawn patcher
│   ├── root/test_socket.py (7 lines) — Low-level socket test
│   └── tests/mcp/test_mcp_harness.py (72 lines) — MCP protocol test
│
└── Domain 4: E2E Test Suite, Benchmarking & Scratch Scripts
    ├── tests/e2e/test_e2e_harness.py (488 lines) — Test contracts & mathematical scoring models
    ├── tests/e2e/run_all_e2e.py (150 lines) — Master 4-tier runner (218 test cases)
    ├── tests/e2e/test_tier1_features.py (950+ lines) — 95 Tier 1 test cases
    ├── tests/e2e/test_tier2_boundaries.py (850+ lines) — 95 Tier 2 boundary cases
    ├── tests/e2e/test_tier3_interactions.py (300+ lines) — 20 Tier 3 interaction tests
    ├── tests/e2e/test_tier4_scenarios.py (300+ lines) — 8 Tier 4 scenario tests
    ├── canned_benchmark/draco_evaluator.py (1,181 lines) — DRACO benchmark evaluator
    ├── scratch/test_all_cli_flags.py (137 lines) — CLI flags validator
    ├── scratch/test_flags_batch.py (158 lines) — Batched CLI flag tester with process killing
    └── scratch/test_inference_batch.py (152 lines) — Live inference flag tester
```

---

## 2. Resource Management & File I/O Audit

### 2.1 Subprocess Lifecycle & Zombie Process Prevention
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `canned_benchmark/draco_evaluator.py` | 546–571 | `proc = await asyncio.create_subprocess_exec(...)` followed by `await asyncio.wait_for(proc.communicate(), timeout=120)`. When `TimeoutError` is raised, `proc.kill()` and `await proc.wait()` are not called, leaving the Rust CLI child process running as an orphaned zombie in the background. | 🔴 High |
| `scratch/test_all_cli_flags.py` | 17–47 | `process = subprocess.Popen(...)` with `process.communicate(timeout=timeout)`. On `subprocess.TimeoutExpired`, the script catches the exception but omits `process.kill()` / `process.wait()`. | 🔴 High |
| `src/openevolve/openevolve/process_parallel.py` | 747–755 | On `FutureTimeoutError`, calls `future.cancel()`. In Python's `ProcessPoolExecutor`, `Future.cancel()` cannot terminate an already executing worker process; it only removes pending tasks from the queue. The running worker remains stalled forever, leading to pool starvation. | 🔴 High |
| `IDE/test_mcp_full_harness.py` | 283–303 | `send_request()` uses a synchronous `while True: line = self.process.stdout.readline()`. If the child process hangs, crashes without flushing, or deadlocks, `readline()` blocks indefinitely without a timeout. | 🟡 Medium |
| `src/scripts/run_model_openvino.py` | 381, 391 | `_sp.run([...], timeout=900)` does not handle `subprocess.TimeoutExpired` separately, resulting in unhandled exception propagation. | 🟢 Low |
| `src/scripts/prepare_model_openvino.py` | 72 | `subprocess.run(export_cmd, timeout=1200)` does not catch `TimeoutExpired` before `except Exception as e:`. | 🟢 Low |

### 2.2 Temporary File Cleanup & Concurrency Collisions
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/scripts/run_model_openvino.py` | 196, 210–213 | Hardcoded temporary file name `_temp.onnx` inside `output_path`. If `core.read_model(onnx_path)` raises an exception, the file removal code on line 210 is skipped because it is not enclosed in a `finally` block. If multiple conversion jobs run concurrently, they collide on `_temp.onnx`. | 🔴 High |
| `src/openevolve/openevolve/evaluator.py` | 157, 289–291 | `tempfile.NamedTemporaryFile(suffix=self.program_suffix, delete=False)` is cleaned up in `finally:` via `os.unlink(temp_file_path)`. When an evaluation times out in `loop.run_in_executor`, the background worker thread still holds an open file handle, causing `PermissionError: [WinError 32]` on Windows when attempting `os.unlink`. | 🟡 Medium |
| `src/openevolve/openevolve/api.py` | 185–200 | `finally:` block cleans up temp files and `temp_dir` with a blanket `try: shutil.rmtree(temp_dir) except: pass`. On Windows, locked handles cause silent failures that leak temporary directories across multiple runs. | 🟡 Medium |
| `IDE/src/scripts/onnx_openvino_demo.py` | 40, 93–97 | Writes `simple_add.onnx` to the working directory. File cleanup is placed at the end of the script; if an assertion fails on line 88–89, cleanup is bypassed and the file is orphaned. | 🟢 Low |

### 2.3 Non-Atomic File Operations & Database State Corruption
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/openevolve/openevolve/database.py` | 654–656, 851–853 | `_save_program()` and `save()` write directly to `metadata.json` and program `.json` files using `with open(..., "w") as f: json.dump(...)` without atomic staging (writing to `.tmp` followed by atomic rename). Process termination mid-write creates corrupted JSON files. | 🔴 High |
| `canned_benchmark/draco_evaluator.py` | 179–181 | `save_cache()` writes directly to `draco_api_cache.json` without an atomic rename step. If aborted during execution, the 1.8MB disk cache is truncated to 0 bytes. | 🟡 Medium |
| `src/scripts/run_model_onnx.py` | 109–112 | `model.save_pretrained(cache_dir)` writes directly to `cache_dir` without cross-process locks or directory staging. Concurrent runs trying to export the same model simultaneously overwrite each other. | 🟡 Medium |
| `src/scripts/cache_ov_hub.py` | 226–239 | Opens SQLite connection `conn = sqlite3.connect(db_path)` and executes queries without a `with sqlite3.connect(...) as conn:` context manager. If query execution throws, the connection handle remains open until garbage collection. | 🟢 Low |

### 2.4 Socket & Network Stream Management
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `test_socket.py` | 1–7 | `s = socket.socket()`, `s.connect(...)`, `s.sendall(...)` without socket timeout, context manager (`with socket...`), or explicit `s.close()`. | 🟡 Medium |
| `src/scripts/getvino.py` | 7–8 | Re-wraps `sys.stdout` buffer using `io.TextIOWrapper(sys.stdout.buffer, ...)` instead of `sys.stdout.reconfigure(encoding='utf-8')`. This can create double buffering and stream synchronization problems. | 🟢 Low |

---

## 3. Concurrency, Multiprocessing & Async Synchronization Audit

### 3.1 Multiprocessing & Event Loop Lifecycle
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/openevolve/openevolve/process_parallel.py` | 200–205, 292 | In worker processes (`_run_iteration_worker`), `asyncio.run(_worker_llm_ensemble.generate_with_context(...))` and `asyncio.run(_worker_evaluator.evaluate_program(...))` spin up and tear down a new event loop on every single iteration. If LLM or Evaluator clients have open connection pools (e.g., `httpx` or `aiohttp`), tearing down the loop raises `ResourceWarning: unclosed transport` and degrades socket performance. | 🟡 Medium |
| `src/openevolve/openevolve/evaluator.py` | 350–352, 396, 437, 499 | `loop.run_in_executor(None, self.evaluate_function, program_path)` executes user-defined evaluation code in the default `ThreadPoolExecutor`. When `asyncio.wait_for(..., timeout=...)` expires, the background thread **cannot be interrupted or killed** in Python. If the evaluated code enters an infinite loop, that thread pool worker runs forever. | 🔴 High |
| `src/openevolve/openevolve/process_parallel.py` | 538–546 | Polling loop uses `completed_iteration = None; for iteration, future in list(pending_futures.items()): if future.done(): ... if completed_iteration is None: await asyncio.sleep(0.01)`. This busy-wait loop polls futures every 10ms instead of leveraging `concurrent.futures.wait(..., return_when=FIRST_COMPLETED)` or wrapping futures in `asyncio.wrap_future()`. | 🟡 Medium |
| `src/scripts/cache_ov_hub.py` | 169–184 | Background monitor thread (`threading.Thread(target=monitor, daemon=True)`) checks directory size during download. If `t.join(timeout=2)` times out, the monitor thread continues accessing directory paths concurrently with `shutil.rmtree()` on failure, triggering Windows file lock conflicts. | 🟡 Medium |

### 3.2 Shared State Mutations & Global Pollution
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/openevolve/openevolve/process_parallel.py` | 367 | In `_serialize_config()`, `config.database.novelty_llm = None` directly mutates the caller's live `config` object in-place to bypass pickling limitations. | 🟡 Medium |
| `src/openevolve/scripts/visualizer.py` | 109, 114, 129 | Global variable `checkpoint_dir = None` is modified inside route handlers (`@app.route("/api/data")`) and read by `@app.route("/program/<program_id>")`. Under concurrent web requests, this global state is subject to race conditions. | 🟡 Medium |
| `src/openevolve/openevolve/evaluator.py` | 76–77, 84, 376–377 | Dynamic module loader modifies `sys.path.insert(0, eval_dir)` and registers `sys.modules["evaluation_module"] = module`. In concurrent evaluation workflows, modifying global `sys.modules` concurrently causes module collision and non-deterministic behavior. | 🟡 Medium |
| `canned_benchmark/draco_evaluator.py` | 195, 226 | `_LOCAL_MODELS_CACHE` stores PyTorch models and tokenizers in a global dictionary without maximum cache size bounds or eviction policy, leading to unbounded VRAM/RAM accumulation. | 🟡 Medium |

---

## 4. Error Handling, Logging & Resilience Audit

### 4.1 Stdout Pollution & Interception Corruption
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/scripts/run_model_onnx.py` | 51, 55, 63, 71, 80, 84, 92, 100, 110 | All log messages (e.g. `[ONNX] ✅ Using cached converted model...`, `[ONNX] 🔄 Exporting model...`) are printed to **`stdout`** instead of `stderr`. Downstream consumers (Rust CLI subprocess handler and IDE extensions) that parse stdout for raw model text receive corrupted responses containing logging headers. | 🔴 High |
| `src/openevolve/openevolve/evaluator.py` | 272 | Calls `traceback.print_exc()` directly to stderr instead of routing through `logger.error(..., exc_info=True)`. | 🟢 Low |
| `src/openevolve/openevolve/evaluator.py` | 641 | In `_llm_evaluate()`, calls `traceback.print_exc()` and swallows the error, returning an empty dictionary `{}`. | 🟡 Medium |

### 4.2 Swallowed Exceptions & Error Masking
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/scripts/run_model_transformers.py` | 196–201 | Catches `except Exception:` when loading `AutoModelForVision2Seq` and silently attempts `AutoModelForCausalLM`. If `AutoModelForVision2Seq` failed due to an unrelated error (e.g., CUDA OOM or corrupted weights), the root cause is concealed. | 🟡 Medium |
| `src/scripts/run_model_transformers.py` | 250–252 | Generic `except Exception as e:` catches all failures, prints `ERROR: {e}` to stderr, and exits with code 1 without error classification (distinguishing between out-of-memory, missing weights, format error, or tokenization error). | 🟡 Medium |
| `src/scripts/run_model_openvino.py` | 293–294 | Catches `except Exception:` during `apply_chat_template` and falls back to raw prompt without logging why templating failed. | 🟢 Low |
| `scratch/recent_files.py` | 25–26 | `except Exception as e: pass` swallows file inspection errors completely. | 🟢 Low |

### 4.3 Missing Out-Of-Memory (OOM) Fallback
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/scripts/run_model_transformers.py` | 144–177 | Loads text-generation pipeline on GPU when available. Unlike its counterpart `IDE/src/scripts/run_model_transformers.py` (which has a dedicated `except torch.cuda.OutOfMemoryError:` CPU fallback block), this script lacks an OOM fallback and immediately crashes when VRAM is exhausted. | 🟡 Medium |

### 4.4 Parameter Parsing & Schema Validation
| File Path | Lines | Issue Description | Risk |
| :--- | :--- | :--- | :--- |
| `src/scripts/run_model_openvino.py` | 344–347 | `max_tokens = int(sys.argv[3])`, `temperature = float(sys.argv[4])` without try-except handling for `ValueError`. | 🟢 Low |
| `src/scripts/run_model_transformers.py` | 80–81 | `max_tokens = int(sys.argv[3])`, `temperature = float(sys.argv[4])` without try-except handling for `ValueError`. | 🟢 Low |
| `src/scripts/run_model_transformers.py` | 238–240 | `inputs.get("input_ids", [[]])` can return `None` if the key exists with a `None` value in custom vision model processors, causing `zip(None, generated_ids)` to raise `TypeError: 'NoneType' object is not iterable`. | 🟡 Medium |

---

## 5. Architectural Duplication & Script Drift

### 5.1 Drift Between `src/scripts/` and `IDE/src/scripts/`
A comparison between root `src/scripts/` and `IDE/src/scripts/` revealed substantial code divergence:

| Script Name | `src/scripts/` Version | `IDE/src/scripts/` Version | Divergence Details |
| :--- | :--- | :--- | :--- |
| `run_model_transformers.py` | 256 lines (10,488 bytes) | 110 lines (4,087 bytes) | `src/` contains multimodal audio transcription (Whisper), vision model loading (`AutoModelForVision2Seq`), and chat template support. `IDE/` contains an older text-only version but includes an explicit `torch.cuda.OutOfMemoryError` fallback to CPU that `src/` lacks. |
| `run_model_openvino.py` | 422 lines (19,200 bytes) | 400 lines (18,167 bytes) | Minor differences in GenAI pipeline initialization and thread counts. |
| `onnx_openvino_demo.py` | Not present in `src/scripts/` | 101 lines (3,461 bytes) | Standalone demo script present only in `IDE/src/scripts/`. |
| `run_model_onnx.py` | 137 lines (5,690 bytes) | Not present in `IDE/src/scripts/` | ONNX execution script present in `src/scripts/` but missing from `IDE/src/scripts/`. |

**Architectural Risk**: Having duplicate script trees without a single source of truth leads to scenarios where bug fixes or features applied to one directory are missing in the build packaged by WiX / MSI installers.

### 5.2 Hardcoded Development Paths
Several helper and patch scripts contain hardcoded local Windows user paths:
- `IDE/patch_evolve_save.py:6–7`: `C:\Users\oyesa\AppData\Local\HugOS IDE\...`
- `IDE/fix_slash_commands.py:15–16`: `C:\Users\oyesa\AppData\Local\HugOS IDE\...`
- `IDE/test_datascience_client.py:56`: `D:\dataset\Seaborn All Built-in Datasets`
- `IDE/verify_architecture.py:8`: `d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89`

---

## 6. Actionable Recommendations & Refactoring Roadmap

### Phase 1: High-Priority Safety Patches (Immediate)
1. **Fix Subprocess Zombie Leaks**:
   - In `canned_benchmark/draco_evaluator.py`, wrap `proc.communicate()` in a `try...except asyncio.TimeoutError:` block that calls `proc.kill()` and `await proc.wait()`.
   - In `scratch/test_all_cli_flags.py`, add `process.kill()` and `process.wait()` in the `except subprocess.TimeoutExpired:` block (matching `scratch/test_flags_batch.py`).
2. **Redirect ONNX Logging to Stderr**:
   - In `src/scripts/run_model_onnx.py`, change all `print("[ONNX] ...")` calls to `print("[ONNX] ...", file=sys.stderr)`. Ensure only the final decoded text is written to `stdout`.
3. **Atomic File Writes for Database State**:
   - In `src/openevolve/openevolve/database.py`, implement an `atomic_write_json(path, data)` utility that writes to `<path>.tmp.<uuid>` and uses `os.replace()` for atomic disk persistence.
4. **Fix Temporary File Cleanup in Evaluator**:
   - In `src/openevolve/openevolve/evaluator.py`, handle `PermissionError` when unlinking temporary files in `finally:`, and evaluate programs in subprocess workers rather than uncancelable thread executors for strict timeout enforcement.

### Phase 2: Architectural Consolidation (Short-Term)
1. **Unify Script Directories**:
   - Establish `src/scripts/` as the single canonical source of truth for inference backend runners.
   - Update `IDE/` build scripts and WiX packaging manifests (`IDE/HugOS.wxs`, `IDE/build_msi.ps1`) to reference `src/scripts/` directly, eliminating `IDE/src/scripts/` duplication.
2. **Port CUDA OOM Fallback to Canonical Transformers Script**:
   - Add `except torch.cuda.OutOfMemoryError:` with `torch.cuda.empty_cache()` and CPU fallback into `src/scripts/run_model_transformers.py`.
3. **Replace Hardcoded Paths with Dynamic Environment Lookups**:
   - Refactor `IDE/patch_evolve_save.py`, `IDE/fix_slash_commands.py`, and `IDE/test_datascience_client.py` to use `os.environ.get("LOCALAPPDATA")` or relative repository paths.

### Phase 3: Long-Term Concurrency & Performance Hardening
1. **Connection Pool Lifecycle in Multiprocessing**:
   - Refactor `src/openevolve/openevolve/process_parallel.py` to manage worker-level async client sessions across iterations instead of spinning up and tearing down fresh event loops per task.
2. **Non-Blocking Future Collection**:
   - Replace the `while True: await asyncio.sleep(0.01)` polling loop in `process_parallel.py` with `concurrent.futures.as_completed()` or an `asyncio.Queue` worker pipeline.
3. **Isolated Evaluator Execution**:
   - Execute user evaluator modules in separate isolated subprocesses to eliminate `sys.path` and `sys.modules` global namespace pollution.

---
*Report generated and validated by Teamwork Python & AVO Systems Explorer.*

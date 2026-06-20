# Changelog

All notable changes to ModelFusion are documented here.

## [Unreleased]

### Added

#### Multi-Backend Inference Support
- **`--openvino` flag**: Use OpenVINO for optimized CPU/iGPU inference on Windows and Linux.
  Detects `openvino-genai` (preferred) or classic `openvino` and sets up the inference pipeline
  automatically. Includes platform-specific tuning (NUMA binding on Linux, thread binding on Windows).
- **`--vllm` flag**: Use vLLM for high-throughput GPU inference on Linux with NVIDIA CUDA.
  Auto-detects GPU count and sets tensor parallelism accordingly. Linux-only — shows a clear
  error message on Windows.
- **`--ollama` flag**: Use Ollama for local model serving. Auto-starts the Ollama service if
  it's not already running.
- **Backend selection early-init**: All backend detection (`--openvino`, `--vllm`, `--ollama`,
  `--transformers`) now runs at startup before any task dispatch, ensuring every flag combination
  works correctly (e.g., `--openvino --sentiment`, `--vllm --fusion`).

#### OpenVINO Optimum-Intel Auto-Convert + Cache
- **`--prepare-model <MODEL_ID>` flag**: Pre-convert a single HuggingFace model to OpenVINO IR
  format using `optimum-intel`. Supports INT8, INT4, and FP16 weight formats.
- **`--prepare-all-models` flag**: Batch-convert all eligible models from the database to
  OpenVINO IR. When combined with `--update`, only converts models ≤ 3B params (~6000 MB)
  to keep processing time under ~30 minutes.
- **`--weight-format` flag**: Choose the quantization format for OpenVINO export.
  Options: `fp16`, `int8` (default), `int4`.
- **`--ov-model-dir` flag**: Set the directory for cached OpenVINO IR models.
  Default: `ov_models/`.
- **Auto-convert on first use**: When running `--openvino`, models are automatically converted
  to OpenVINO IR on first inference and cached. Subsequent runs load the cached model directly
  for dramatically faster startup.
- **4-tier inference priority**: The OpenVINO script tries: (1) cached IR model,
  (2) auto-convert via optimum-cli subprocess, (3) openvino_genai LLMPipeline,
  (4) classic manual OpenVINO pipeline.
- **`--update --prepare-all-models` combo**: Refresh the model database and auto-prepare
  small models in one command.
- **Skip already-converted models**: Running `--prepare-all-models` twice safely skips
  models that are already cached, showing `⏭️ Already cached` status.

#### New Python Scripts
- **`src/scripts/run_model_vllm.py`**: vLLM backend for high-throughput GPU inference.
  Auto-detects GPUs, sets tensor parallelism, and uses the standard CLI argument interface.
- **`src/scripts/prepare_model_openvino.py`**: Standalone model export script. Uses
  `optimum.exporters.openvino` as a subprocess for safety on Python 3.14+.
- **`src/scripts/check_openvino.py`**: Diagnostic script to verify which OpenVINO
  packages are importable on the current Python version.

#### Database Enhancements
- **`get_all_model_ids()`**: Returns all distinct model IDs from the database, ordered by
  decision score. Used by `--prepare-all-models`.
- **`get_small_model_ids(max_size_mb)`**: Returns model IDs under a size threshold. Used by
  `--update --prepare-all-models` to filter out large models that would take too long to convert.

#### Stack Overflow Fix
- **8 MB thread stack for CLI**: The `main()` function now spawns a dedicated thread with
  an 8 MB stack to prevent stack overflow in debug builds. The `Args` struct has 80+ fields
  which exceeds the default 1-2 MB stack in unoptimized builds.

### Fixed

#### Python 3.14 Segfault Prevention
- **Subprocess probe for optimum-intel**: The `run_model_openvino.py` script now tests
  whether `from optimum.intel import OVModelForCausalLM` is safe by running the import in a
  subprocess first. If the subprocess segfaults (exit code `0xC0000005` on Python 3.14),
  the main script survives and falls through to the classic OpenVINO pipeline.
- **Subprocess-based model export**: `prepare_model_openvino.py` now runs
  `python -m optimum.exporters.openvino` as a subprocess instead of importing
  `OVModelForCausalLM` in-process, preventing segfaults from killing the export process.
- **Classic OpenVINO fallback works on all Python versions**: The `ov.convert_model()`
  path downloads PyTorch models, wraps them to return logits only (avoiding DynamicCache
  tracing issues), converts to OpenVINO IR, and caches for subsequent use.

### Changed

#### Code Architecture
- **`providers.rs`**: Introduced `find_script()` helper to deduplicate Python script path
  lookup across all backends. OpenVINO provider now passes `ov_model_dir` and `weight_format`
  as additional arguments to the Python script via env vars `MODELFUSION_OV_MODEL_DIR` and
  `MODELFUSION_OV_WEIGHT_FORMAT`.
- **`run_model_openvino.py`**: Upgraded from single-path inference to 4-tier priority system
  with auto-convert and caching. Now accepts 6th arg (ov_model_dir) and 7th arg (weight_format).
  All optimum-intel imports are guarded by subprocess safety probes.

### Removed

- Removed 60+ obsolete Python scripts that were superseded by the Rust port:
  - Test/debug scripts: `debug_test.py`, `simple_test.py`, `quick_test.py`, etc.
  - DB utility scripts: `check_db.py`, `recover_db.py`, `updatedb.py`, etc.
  - PE analysis scripts: `pe_header_extractor.py`, `enhanced_pe_analyzer.py`, etc.
  - Population scripts: `populate_hf_database.py`, `fixed_populate_models.py`, etc.
  - Batch files: `clean_and_update.bat`, `test_all_flags.bat`, etc.
  - Requirements files: `requirements.txt`, `requirements_evaluation.txt`
  - Python test suite: `tests/` directory (Rust tests replace these)
- Kept Python scripts that the Rust code depends on: `run_model_openvino.py`,
  `run_model_transformers.py`, `run_model_vllm.py`, `prepare_model_openvino.py`,
  `check_openvino.py`

---

## Commit History

| Commit | Description |
|---|---|
| `f9e3cf7` | docs: add backend integration guide, changelog, and diagnostic script |
| `0d7ad0e` | fix: prevent Python 3.14 segfault in optimum-intel imports |
| `91c2768` | feat(db): add get_all_model_ids() and get_small_model_ids() |
| `59eb385` | feat: add optimum-intel auto-convert + cache for OpenVINO models |
| `b040b39` | feat: add vLLM + OpenVINO multi-backend inference |
| `dc661c0` | chore: remove 60+ obsolete Python scripts and batch files |
| `9464833` | fix: OpenVINO conversion crash — wrap CausalLM to return logits only |
| `c969a3c` | feat: add --fusion-mode, --openvino, --ollama, dynamic resource mgmt |

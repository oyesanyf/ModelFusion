# Milestone 1 Forensic Audit Handoff Report

**Agent**: Rust Forensic Safety Auditor (`auditor_m1_rust`)  
**Target**: Milestone 1 - Rust Core & Crates Safety Audit  
**Date**: 2026-09-01T19:56:00Z  
**Verdict**: **DEFECTS_CONFIRMED**

---

## 1. Observation

Direct code inspections across 35 Rust files in 9 workspace crates and 3 external subtrees revealed the following exact observations:

1. **Insecure TLS Bypass**:
   - `crates/core/src/providers.rs:247`:
     ```rust
     let client = Client::builder()
         .timeout(Duration::from_secs(config.timeout_seconds))
         .danger_accept_invalid_certs(true)
         .build()
         .unwrap_or_default();
     ```
2. **Silent PowerShell Download & Execution**:
   - `crates/model_selection/src/memory.rs:412-429`:
     ```rust
     let install_result = Command::new("powershell")
         .args([
             "-NoProfile",
             "-Command",
             "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile \"$env:TEMP\\OllamaSetup.exe\"; Start-Process -FilePath \"$env:TEMP\\OllamaSetup.exe\" -ArgumentList '/SILENT' -Wait"
         ])
         .status();
     ```
3. **UTF-8 Byte Slicing Panic**:
   - `crates/monitoring/src/tree_monitor.rs:101`:
     ```rust
     &thought[..thought.len().min(60)]
     ```
4. **Bounds Verification & Integer Overflow**:
   - `crates/analysis/src/pe_extractor.rs:210-213`:
     ```rust
     let start = sec.pointer_to_raw_data as usize;
     let end = (sec.pointer_to_raw_data + sec.size_of_raw_data) as usize;
     let sec_data = if start < buffer.len() && end <= buffer.len() {
         &buffer[start..end]
     } else {
         &[]
     };
     ```
5. **Process-Global Environment Mutation in Async Handlers**:
   - `crates/cli/src/main.rs:3533-3554`:
     ```rust
     std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
     std::env::set_var("MODELFUSION_FORCE_GPU", "true");
     ...
     std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
     ```
   - `crates/core/src/providers.rs:693, 701, 707`:
     ```rust
     std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "1");
     ```
6. **Silent Python Pip Install**:
   - `crates/core/src/providers.rs:68-69`:
     ```rust
     std::process::Command::new("python")
         .args(["-m", "pip", "install", "torch", "transformers", "accelerate", "pillow", "soundfile", "librosa", "pypdf", "--quiet"])
         .status();
     ```
7. **Float NaN Panic Hazard**:
   - `crates/utils/src/performance.rs:130`:
     ```rust
     sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
     ```
8. **Safe Concurrency & Memory Foundations**:
   - Zero `unsafe` blocks in `crates/` (all 9 crates).
   - Mutex locks in `crates/core/src/orchestrator.rs:82, 217, 218` are never held across `.await` points.
   - Dynamic semaphores (`INFERENCE_SEM`, `FAST_SEM`) in `crates/cli/src/main.rs:23-62` throttle concurrent inference based on system RAM.
   - Parameterized SQLite queries throughout `crates/db/src/models.rs` and `stats.rs`.

---

## 2. Logic Chain

1. **Observation 1** demonstrates that `HuggingFaceProvider` creates an HTTP client with certificate verification disabled (`danger_accept_invalid_certs(true)`). Therefore, API keys and sensitive prompt payloads sent via this client are subject to MITM eavesdropping.
2. **Observation 2** shows that `ensure_ollama_running()` invokes PowerShell to download an executable over the internet and runs it with `/SILENT` without checksum validation or user consent, creating an unprompted software installation vector.
3. **Observation 3** proves that `tree_monitor.rs` uses raw byte slicing `&str[..60]`. Because UTF-8 codepoints for non-ASCII characters (e.g. CJK, emoji) span 2–4 bytes, slicing at byte index 60 panics whenever index 60 splits a multi-byte character.
4. **Observation 4** indicates that PE section boundaries are computed via 32-bit addition without verifying `start <= end` or using `checked_add`. On corrupted/crafted headers, `start > end` triggers slice indexing panic `buffer[start..end]`.
5. **Observation 5** demonstrates that `std::env::set_var` is called inside async request handling branches in `main.rs` and `providers.rs`. Because Tokio executes requests across multiple worker threads, environment mutations in one request concurrently overwrite the settings of another request, creating state race conditions.
6. **Observation 6 & 7** demonstrate silent pip install triggers and `.unwrap()` panics on `f64::NAN`.
7. **Observation 8** confirms that memory safety abstractions and database query parameterization are cleanly implemented.

**Conclusion from Logic Chain**: The codebase does not exhibit facade implementations or integrity shortcuts, but contains confirmed defects (SEC-01, SEC-02, PAN-01, PAN-02, CONC-01) that must be remediated.

---

## 3. Caveats

- Direct cargo compilation commands in the current subagent environment timed out on interactive permissions; verification was conducted via line-by-line static forensic inspection of the codebase.
- Upstream VS Code CLI in `IDE/vscode/cli` was treated as an external upstream dependency and not in scope for ModelFusion crate defect tracking.

---

## 4. Conclusion

The ModelFusion Rust codebase passes integrity verification (no facades, no hardcoded cheating outputs, zero `unsafe` in core crates). However, a formal verdict of **DEFECTS_CONFIRMED** is issued due to 2 high-severity security issues (TLS bypass, silent binary download), 1 high-severity panic bug (UTF-8 byte slicing), 1 medium-severity bounds/overflow panic (PE extractor), and 1 medium-severity async state mutation issue (`std::env::set_var`).

Detailed findings, remediation diffs, and proofs are documented in:
`d:/harfile/ModelFusion/.agents/auditor_m1_rust/audit_rust.md`

---

## 5. Verification Method

To independently reproduce and verify these findings:

1. **UTF-8 Slicing Panic**:
   - Inspect `crates/monitoring/src/tree_monitor.rs:101`.
   - Pass a string containing 19 3-byte CJK characters (57 bytes) followed by a 4-byte emoji (starts at byte 57, ends at byte 61) into `evaluate_thought`. Slicing `[..60]` will panic on non-char boundary 60.
2. **TLS Verification Bypass**:
   - Inspect `crates/core/src/providers.rs:247`.
   - Search for `danger_accept_invalid_certs(true)`.
3. **PowerShell Silent Execution**:
   - Inspect `crates/model_selection/src/memory.rs:412-429`.
   - Observe `Invoke-WebRequest` to `https://ollama.com/download/OllamaSetup.exe` with `/SILENT`.
4. **PE Extractor Bounds**:
   - Inspect `crates/analysis/src/pe_extractor.rs:210-213`.
   - Observe missing `start <= end` and unchecked `sec.pointer_to_raw_data + sec.size_of_raw_data`.
5. **Async Environment Variable Mutation**:
   - Inspect `crates/cli/src/main.rs:3533-3554` and `crates/core/src/providers.rs:693, 701, 707`.

# ModelFusion Analysis Crate (`crates/analysis`)

The `analysis` crate provides Windows Portable Executable (PE) binary parsing and forensic malware threat scoring capabilities.

## 🚀 Key Features

*   **PE Structural Extraction**: Uses the `goblin` crate to parse headers, entry points, machines, subsystems, data directories, section details, exports, and imports.
*   **Shannon Entropy Calculation**: Computes section and resource byte-frequency entropy to detect packed, encrypted, or compressed sections (entropy nearing `8.0` indicates high randomness).
*   **Suspicious API Auditing**: Scans imports against a set of 24 suspicious Win32 APIs associated with process injection, memory allocation, reg/network access, and system command execution.
*   **Packer Detection**: Scans section names for signatures of packers like UPX, Themida, VMProtect, or ASPack.
*   **Risk Scoring & Profiles**: Normalizes heuristic triggers to output a risk score from `0` to `100` and classifies the file into `CLEAN`, `LOW`, `MEDIUM`, or `HIGH` risk levels.

## 📁 Source Files

*   [src/pe_extractor.rs](file:///D:/harfile/ModelFusion/crates/analysis/src/pe_extractor.rs) — Core Goblin PE parsing, hashing (MD5, SHA-1, SHA-256), and entropy math.
*   [src/malware_detector.rs](file:///D:/harfile/ModelFusion/crates/analysis/src/malware_detector.rs) — Threat indicators, packer signatures, DLL categorization, and score calculation.

## ⚙️ How it Works

The extractor computes Shannon Entropy using:
\[H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)\]

If a section exhibits high entropy or imports injection calls (such as `VirtualAllocEx` or `WriteProcessMemory`), the analysis raises the threat level.

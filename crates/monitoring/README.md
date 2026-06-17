# ModelFusion Monitoring Crate (`crates/monitoring`)

The `monitoring` crate provides decision quality auditing, session statistics, and self-correcting prompt recovery sequences.

## 🚀 Key Features

*   **Decision Tracking**: Captures confidence metrics, category assignments, depths, and timestamps for every model routing step.
*   **Adaptive Threshold Manager**: Logs recent routing scores to dynamically compute and update minimum acceptable quality levels.
*   **Adversarial Threat Alerts**: Integrates directly with the ATLAS threat detector to issue critical safety warnings and halt dangerous execution paths.
*   **Prompt Recovery & Self-Healing**: Automatically triggers LLM-driven diagnostic scans and prompt adjustments if quality falls below the computed threshold.

## 📁 Source Files

*   [src/decision.rs](file:///D:/harfile/ModelFusion/crates/monitoring/src/decision.rs) — Metrics schema.
*   [src/tree_monitor.rs](file:///D:/harfile/ModelFusion/crates/monitoring/src/tree_monitor.rs) — Core monitoring, adaptive thresholds, recovery logic, and logs.

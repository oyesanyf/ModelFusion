# ModelFusion Security Crate (`crates/security`)

The `security` crate implements adversarial AI prompt threat scanning grounded in the MITRE ATLAS (Adversarial Threat Landscape for Artificial-Intelligence Systems) matrix taxonomy.

## 🚀 Key Features

*   **ATLAS TTP Scans**: Pre-compiles regular expressions to intercept adversarial prompting.
*   **Adversarial Tactics Tracked**:
    *   **AML.T0049 (Evasion of AI Policies)**: Intercepts jailbreaks and overrides (e.g. `"ignore previous instructions"`, `"dan prompt"`, `"disregard safety"`).
    *   **AML.T0052 (Abuse of Dual-Use Foundational Models)**: Blocks payloads attempting to generate ransomware, exploit code, explosives, or illegal substances.
    *   **AML.T0040 (Reconnaissance)**: Scans for content probing safety filters, guidelines, or system instructions.
    *   **AML.T0043 (AI-Enabled Social Engineering)**: Intercepts fraudulent phishing templates and pretext scripts.

## 📁 Source Files

*   [src/atlas.rs](file:///D:/harfile/ModelFusion/crates/security/src/atlas.rs) — ATLAS technique definitions, compiled regex, and scan logic.
*   [src/lib.rs](file:///D:/harfile/ModelFusion/crates/security/src/lib.rs) — Crate library exports.

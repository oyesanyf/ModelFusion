# ModelFusion Task Detection Crate (`crates/task_detection`)

The `task_detection` crate parses queries to identify their lexical patterns and route them to appropriate Hugging Face pipeline tags.

## 🚀 Key Features

*   **Syntax Routing**: Evaluates natural language structure to map instructions to 40+ NLP and multimodal tasks.
*   **Lexical Keywords Mapping**: Implements quick regex scans matching verbs/nouns to tasks (e.g. classification, question-answering, summarization).
*   **Language Extraction Fallbacks**: Integrates the `langextract` wrapper to resolve complex or ambiguous prompt tags.
*   **LRU Caching**: Caches prompt classifications to bypass redundant routing processes.

## 📁 Source Files

*   [src/detector.rs](file:///D:/harfile/ModelFusion/crates/task_detection/src/detector.rs) — Routing pipeline, LRU cache, and `langextract` checks.
*   [src/keywords.rs](file:///D:/harfile/ModelFusion/crates/task_detection/src/keywords.rs) — Task regex keyword lists.
*   [src/language.rs](file:///D:/harfile/ModelFusion/crates/task_detection/src/language.rs) — ISO code language patterns.

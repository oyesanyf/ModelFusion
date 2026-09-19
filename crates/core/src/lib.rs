//! Core orchestrator, providers, and task handler library.

pub mod orchestrator;
pub mod providers;
pub mod task_handler;
pub mod task_processor;
pub mod fusion_engine;
pub mod web_research;

pub use orchestrator::{HuggingFaceOrchestrator, OrchestrationResult};
pub use providers::{create_provider, LLMProvider, ModelConfig, ProviderResult};
pub use task_handler::ComprehensiveTaskHandler;
pub use task_processor::UniversalTaskProcessor;
pub use web_research::{live_web_search, run_deep_research, run_web_search_only, SearchResult};

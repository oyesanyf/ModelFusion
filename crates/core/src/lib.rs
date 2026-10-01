//! Core orchestrator, providers, and task handler library.

pub mod orchestrator;
pub mod providers;
pub mod task_handler;
pub mod task_processor;
pub mod fusion_engine;
pub mod web_research;
pub mod browser;
pub mod rl;
pub mod memory;
pub mod kv_cache;
pub mod wikiskill;

pub use orchestrator::{HuggingFaceOrchestrator, OrchestrationResult};
pub use providers::{create_provider, LLMProvider, ModelConfig, ProviderResult};
pub use task_handler::ComprehensiveTaskHandler;
pub use task_processor::UniversalTaskProcessor;
pub use web_research::{
    live_web_search, parse_arxiv_atom, run_deep_research, run_web_agent, run_web_search_only,
    search_arxiv, IndexedDocument, IndexedMatch, SearchResult, TermPosting, WebAgentResult,
    WebSearchIndex,
};
pub use wikiskill::{
    distill_wikipedia_knowledge, fetch_wikipedia_article, fetch_wikipedia_sections,
    format_wiki_markdown, format_wiki_title_url, parse_wikipedia_extract_json,
    parse_wikipedia_query_links_and_extlinks, parse_wikipedia_search_json,
    parse_wikipedia_sections_json, search_wikipedia, strip_html_tags, WikiArticleDetail,
    WikiDistillationReport, WikiSearchResult, WikiSection,
};
pub use browser::{
    AgentGoal, AgentState, AutonomousBrowserAgent, BrowserAction, BrowserActionResult,
    BrowserToolSuite, CdpClient, DomPruner, DomPrunerOptions, ElementTarget, ExtractedTable,
    GroundingBox, GroundingResult, InteractiveElement, PrunedDom, SafetyClassifier, StepAction,
    TableExtractor, TargetInfo, VisionGroundingEngine,
    ComputerUseAgent, ComputerUseResult, ComputerUseStepRecord, ExecutionResult, MouseButton,
    OsExecutor, ParsedActionStep, ScreenCapture, ScreenPerceiver, ScrollDirection, UiTarsAction,
    UiTarsActionParser,
};
pub use memory::{
    AssemblyContext, ChatMessage, ConversationSession, ContextManager, MemoryError,
    MemoryRepository, MessageRole, SqliteMemoryRepository, StoredMessage,
};
pub use rl::*;
pub use kv_cache::{
    run_kv_benchmark, KvBenchmarkReport, KvBlock, KvBlockPool, KvCache, MultiTabKvManager,
    PagedKvCache, RingKvCache, TabContext, WgpuAttentionPipeline, WGSL_ATTENTION_SHADER,
};

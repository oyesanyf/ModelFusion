//! Core browser automation, semantic DOM pruning, table extraction, and CDP tools.
//!
//! Powers the ModelFusion / HugOS Chromium Browser architecture.

pub mod agent;
pub mod cdp_client;
pub mod dom_pruner;
pub mod table_extractor;
pub mod tools;
pub mod vision_grounding;
pub mod computer_use;

pub use agent::*;
pub use cdp_client::{CdpClient, CdpResponse, TargetInfo};
pub use dom_pruner::{DomPruner, DomPrunerOptions, InteractiveElement, PrunedDom};
pub use table_extractor::{ExtractedTable, TableExtractor};
pub use tools::{BrowserAction, BrowserActionResult, BrowserTabState, BrowserToolSuite, ElementTarget};
pub use vision_grounding::{GroundingBox, GroundingResult, VisionGroundingEngine};
pub use computer_use::*;
pub use crate::memory::{
    AssemblyContext, ChatMessage, ContextManager, ConversationSession, MemoryError,
    MemoryRepository, MessageRole, SqliteMemoryRepository, StoredMessage,
};


//! Semantic Codebase Knowledge Graph Crate for ModelFusion
//!
//! Provides AST parsing (Rust, TypeScript, Python), SQLite storage with FTS5,
//! sub-25ms recursive CTE query engine, and incremental workspace indexing.

pub mod db;
pub mod indexer;
pub mod parser;
pub mod query;

pub use db::{CodeGraphDb, GraphStats};
pub use indexer::{CodeGraphIndexer, IndexReport};
pub use parser::{
    AstExtractor, CallEdge, ImplEdge, LanguageKind, ParsedFileEntities, RefEdge, SymbolDef,
};
pub use query::{
    CallHierarchyNode, CallHierarchyResult, CodeGraphQueryEngine, ImplRecord, QueryResponse,
    RefRecord, SearchResult, SymbolRecord,
};

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

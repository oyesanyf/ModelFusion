//! SQL DDL statements and database initialisation helpers.

/// Full CREATE TABLE statement for the primary `models` table.
pub const CREATE_MODELS_TABLE: &str = r#"
CREATE TABLE IF NOT EXISTS models (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    model_id          TEXT     UNIQUE NOT NULL,
    author            TEXT,
    pipeline_tag      TEXT,
    tags              TEXT,           -- JSON array
    description       TEXT,
    downloads         INTEGER  DEFAULT 0,
    likes             INTEGER  DEFAULT 0,
    decision_score    REAL     DEFAULT 0.0,
    capability_score  REAL     DEFAULT 0.0,
    efficiency_score  REAL     DEFAULT 0.0,
    popularity_score  REAL     DEFAULT 0.0,
    model_type        TEXT,
    library_name      TEXT,
    last_modified     TEXT,
    download_date     TEXT     DEFAULT (datetime('now')),
    license           TEXT,
    task_keywords     TEXT,           -- JSON array
    architecture      TEXT,
    size_mb           REAL     DEFAULT 0.0,
    language          TEXT,
    created_at        TEXT     DEFAULT (datetime('now')),
    updated_at        TEXT     DEFAULT (datetime('now'))
)
"#;

/// Metadata key-value store (last_update, schema_version, etc.)
pub const CREATE_METADATA_TABLE: &str = r#"
CREATE TABLE IF NOT EXISTS metadata (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
)
"#;

/// Keyword search tracking (for the model discovery system).
pub const CREATE_KEYWORD_SEARCHES_TABLE: &str = r#"
CREATE TABLE IF NOT EXISTS keyword_searches (
    keyword      TEXT PRIMARY KEY,
    models_found INTEGER DEFAULT 0,
    last_searched TEXT DEFAULT (datetime('now'))
)
"#;

/// Index definitions applied after table creation.
pub const CREATE_INDEXES: &[&str] = &[
    "CREATE INDEX IF NOT EXISTS idx_pipeline_tag    ON models(pipeline_tag)",
    "CREATE INDEX IF NOT EXISTS idx_pipeline_tag_comp ON models(pipeline_tag, decision_score DESC, downloads DESC)",
    "CREATE INDEX IF NOT EXISTS idx_author          ON models(author)",
    "CREATE INDEX IF NOT EXISTS idx_decision_score  ON models(decision_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_downloads       ON models(downloads DESC)",
    "CREATE INDEX IF NOT EXISTS idx_last_modified   ON models(last_modified)",
];

/// Pragmas applied at connection open for performance and safety.
pub const STARTUP_PRAGMAS: &[&str] = &[
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous  = NORMAL",
    "PRAGMA busy_timeout = 30000",
    "PRAGMA cache_size   = 10000",
    "PRAGMA temp_store   = MEMORY",
    "PRAGMA foreign_keys = ON",
];

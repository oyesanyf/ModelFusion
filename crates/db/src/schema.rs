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
    trending_score    REAL     DEFAULT 0.0,
    feed_source       TEXT     DEFAULT 'standard_hub',
    bandit_pulls      INTEGER  DEFAULT 0,
    bandit_reward     REAL     DEFAULT 0.0,
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
    "CREATE INDEX IF NOT EXISTS idx_trending_score  ON models(trending_score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_feed_source     ON models(feed_source)",
];

pub const MIGRATION_COLUMNS: &[(&str, &str)] = &[
    ("trending_score", "ALTER TABLE models ADD COLUMN trending_score REAL DEFAULT 0.0"),
    ("feed_source", "ALTER TABLE models ADD COLUMN feed_source TEXT DEFAULT 'standard_hub'"),
    ("bandit_pulls", "ALTER TABLE models ADD COLUMN bandit_pulls INTEGER DEFAULT 0"),
    ("bandit_reward", "ALTER TABLE models ADD COLUMN bandit_reward REAL DEFAULT 0.0"),
];

/// Inspects existing table schema and applies missing columns non-destructively.
pub fn migrate_schema(conn: &rusqlite::Connection) -> anyhow::Result<()> {
    let table_exists: bool = conn.query_row(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'models'",
        [],
        |_| Ok(true),
    ).unwrap_or(false);

    if !table_exists {
        return Ok(());
    }

    let mut stmt = conn.prepare("PRAGMA table_info(models)")?;
    let existing_columns: std::collections::HashSet<String> = stmt
        .query_map([], |row| row.get::<_, String>(1))?
        .filter_map(|r| r.ok())
        .map(|s| s.to_ascii_lowercase())
        .collect();

    for (col_name, alter_stmt) in MIGRATION_COLUMNS {
        if !existing_columns.contains(&col_name.to_ascii_lowercase()) {
            log::info!("Migrating models schema: adding missing column '{}'", col_name);
            if let Err(e) = conn.execute_batch(alter_stmt) {
                let msg = e.to_string().to_lowercase();
                if !msg.contains("duplicate column name") {
                    return Err(e.into());
                }
            }
        }
    }

    let _ = conn.execute_batch("CREATE INDEX IF NOT EXISTS idx_trending_score ON models(trending_score DESC)");
    let _ = conn.execute_batch("CREATE INDEX IF NOT EXISTS idx_feed_source ON models(feed_source)");

    Ok(())
}

/// Pragmas applied at connection open for performance and safety.
pub const STARTUP_PRAGMAS: &[&str] = &[
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous  = NORMAL",
    "PRAGMA busy_timeout = 30000",
    "PRAGMA cache_size   = 10000",
    "PRAGMA temp_store   = MEMORY",
    "PRAGMA foreign_keys = ON",
];

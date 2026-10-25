//! `ModelMetrics` struct and all CRUD operations on the `models` table.

use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use crate::schema;

pub fn default_feed_source() -> String {
    "standard_hub".to_string()
}

/// Standardized mapping from a pipeline tag to its canonical task.
pub fn pipeline_tag_to_task(pipeline_tag: &str) -> &'static str {
    match pipeline_tag.to_lowercase().trim() {
        "text-generation" | "causal-lm" | "conversational" => "text-generation",
        "text2text-generation" => "text2text-generation",
        "summarization" => "summarization",
        "translation" => "translation",
        "question-answering" | "table-question-answering" => "question-answering",
        "fill-mask" => "fill-mask",
        "sentence-similarity" | "feature-extraction" => "sentence-similarity",
        "text-classification" | "zero-shot-classification" => "text-classification",
        "token-classification" => "token-classification",
        "image-classification" | "zero-shot-image-classification" => "image-classification",
        "object-detection" => "object-detection",
        "image-segmentation" => "image-segmentation",
        "text-to-image" => "text-to-image",
        "image-to-text" => "image-to-text",
        "depth-estimation" => "depth-estimation",
        "visual-question-answering" | "document-question-answering" => "visual-question-answering",
        "automatic-speech-recognition" | "asr" => "automatic-speech-recognition",
        "text-to-speech" | "tts" => "text-to-speech",
        "audio-classification" => "audio-classification",
        "voice-activity-detection" => "voice-activity-detection",
        "audio-to-audio" => "audio-to-audio",
        "tabular-classification" => "tabular-classification",
        "tabular-regression" => "tabular-regression",
        "time-series-forecasting" => "time-series-forecasting",
        "reinforcement-learning" => "reinforcement-learning",
        "robotics" => "robotics",
        _ => "text-generation",
    }
}

/// Standardized mapping from a pipeline tag to one of the 19 Browser UI categories.
pub fn pipeline_tag_to_browser_category(pipeline_tag: &str) -> &'static str {
    match pipeline_tag.to_lowercase().trim() {
        "text-classification" | "zero-shot-classification" | "token-classification" => "Classification & Taxonomy",
        "code-generation" | "code-analysis" => "Code & Security",
        "tabular-classification" | "tabular-regression" | "time-series-forecasting" | "table-question-answering" => "Data & Spreadsheets (CSV/Excel)",
        "image-classification" | "object-detection" | "image-segmentation" | "text-to-image"
        | "image-to-text" | "depth-estimation" | "zero-shot-image-classification"
        | "visual-question-answering" | "document-question-answering" | "image-feature-extraction" => "Images & Vision",
        "sentiment-analysis" => "Sentiment & Content Moderation",
        "automatic-speech-recognition" | "text-to-speech" | "audio-classification"
        | "voice-activity-detection" | "audio-to-audio" | "asr" | "tts" => "Voice & Audio",
        "text-generation" | "text2text-generation" | "summarization" | "translation" | "fill-mask" | "conversational" | "causal-lm" => "Writing & Editing",
        "sentence-similarity" | "feature-extraction" => "Classification & Taxonomy",
        _ => "Writing & Editing",
    }
}

/// Full metadata record for a HuggingFace model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetrics {
    pub model_id: String,
    pub author: String,
    pub pipeline_tag: String,
    /// JSON-serialised list of tags.
    pub tags: Vec<String>,
    pub description: String,
    pub downloads: i64,
    pub likes: i64,
    pub decision_score: f64,
    pub capability_score: f64,
    pub efficiency_score: f64,
    pub popularity_score: f64,
    pub model_type: String,
    pub library_name: String,
    pub last_modified: String,
    pub license: String,
    pub task_keywords: Vec<String>,
    pub architecture: String,
    pub size_mb: f64,
    pub language: String,
    #[serde(default)]
    pub trending_score: f64,
    #[serde(default = "default_feed_source")]
    pub feed_source: String,
    #[serde(default)]
    pub bandit_pulls: i64,
    #[serde(default)]
    pub bandit_reward: f64,
}

impl Default for ModelMetrics {
    fn default() -> Self {
        Self {
            model_id: String::new(),
            author: String::new(),
            pipeline_tag: String::new(),
            tags: Vec::new(),
            description: String::new(),
            downloads: 0,
            likes: 0,
            decision_score: 0.0,
            capability_score: 0.0,
            efficiency_score: 0.0,
            popularity_score: 0.0,
            model_type: String::new(),
            library_name: String::new(),
            last_modified: String::new(),
            license: String::new(),
            task_keywords: Vec::new(),
            architecture: String::new(),
            size_mb: 0.0,
            language: String::new(),
            trending_score: 0.0,
            feed_source: default_feed_source(),
            bandit_pulls: 0,
            bandit_reward: 0.0,
        }
    }
}

impl ModelMetrics {
    /// Canonical task name for this model.
    pub fn task_name(&self) -> &str {
        if !self.pipeline_tag.is_empty() {
            pipeline_tag_to_task(&self.pipeline_tag)
        } else {
            "text-generation"
        }
    }

    /// Maps model to one of the 19 Browser UI categories, taking into account pipeline_tag and model_id domain heuristics.
    pub fn browser_category(&self) -> &'static str {
        let mid = self.model_id.to_lowercase();
        if mid.contains("finbert") || mid.contains("fingpt") || mid.contains("finance") || mid.contains("chronos") {
            return "Finance & Markets";
        }
        if mid.contains("legal") || mid.contains("saul") || mid.contains("lawma") || mid.contains("cuad") {
            return "Legal";
        }
        if mid.contains("sec") || mid.contains("cisco") || mid.contains("malware") || mid.contains("vulnerability") {
            return "Code & Security";
        }
        if mid.contains("coder") || mid.contains("starcoder") || mid.contains("deepseek-coder") {
            return "Code & Security";
        }
        if mid.contains("r1") || mid.contains("reason") || mid.contains("qwq") {
            return "Deep Research";
        }
        if mid.contains("esm") || mid.contains("evo2") || mid.contains("chemberta") || mid.contains("bio") {
            return "Science & Discovery";
        }

        pipeline_tag_to_browser_category(&self.pipeline_tag)
    }
    /// Compute an Exponential Temporal Decay + Legacy Generation Penalty score in [0.10, 1.0].
    pub fn recency_score(&self) -> f64 {
        use chrono::{DateTime, Utc};
        let parsed = DateTime::parse_from_rfc3339(&self.last_modified)
            .or_else(|_| DateTime::parse_from_str(&self.last_modified, "%Y-%m-%dT%H:%M:%S%.fZ"))
            .or_else(|_| {
                let trimmed = self.last_modified.split('T').next().unwrap_or(&self.last_modified);
                DateTime::parse_from_str(&format!("{}T00:00:00Z", trimmed), "%Y-%m-%dT%H:%M:%SZ")
            });

        let mut score = if let Ok(dt) = parsed {
            let days_old = (Utc::now() - dt.with_timezone(&Utc)).num_days().max(0) as f64;
            if days_old <= 90.0 {
                1.0
            } else if days_old <= 180.0 {
                0.92
            } else if days_old <= 365.0 {
                0.78
            } else if days_old <= 730.0 {
                0.50
            } else {
                (0.35 * (- (days_old - 730.0) / 730.0).exp()).max(0.10)
            }
        } else {
            0.50
        };

        if self.is_stale_or_legacy_architecture() {
            score = (score * 0.45).min(0.35);
        }

        score
    }

    /// Detect superseded legacy models from past eras that should not be prioritized
    pub fn is_stale_or_legacy_architecture(&self) -> bool {
        let m = self.model_id.to_lowercase();
        // Modern release exceptions:
        if m.contains("qwen2.5") || m.contains("qwen3") || m.contains("deepseek-r1") || m.contains("gemma2") || m.contains("gemma-2") || m.contains("llama-3") || m.contains("llama3") || m.contains("flux") || m.contains("v2") || m.contains("v3") || m.contains("2025") || m.contains("2026") {
            return false;
        }
        m.contains("gpt2")
            || m.contains("gpt-neo")
            || m.contains("gpt-j")
            || m.contains("opt-")
            || m.contains("bloom")
            || m.contains("llama-2")
            || m.contains("llama2")
            || m.contains("vicuna")
            || m.contains("alpaca")
            || m.contains("falcon-7b")
            || m.contains("falcon-40b")
            || m.contains("mpt-7b")
            || m.contains("starcoder-base")
            || m.contains("stable-diffusion-v1")
            || m.contains("sd-v1-4")
            || m.contains("bert-base-uncased")
            || m.contains("distilbert-base")
            || m.contains("distilbert")
            || m.contains("roberta-base")
            || m.contains("t5-small")
            || m.contains("t5-base")
            || m.contains("finbert")
            || m.contains("legal-bert")
            || m.contains("scibert")
            || m.contains("galactica")
    }

    pub fn staleness_tier(&self) -> &'static str {
        let r = self.recency_score();
        if r >= 0.85 {
            "fresh"
        } else if r >= 0.65 {
            "recent"
        } else if r >= 0.40 {
            "aging"
        } else {
            "stale"
        }
    }

    pub fn task_domain(&self) -> &'static str {
        let tag = self.pipeline_tag.to_lowercase();
        let mid = self.model_id.to_lowercase();
        if tag.contains("text-generation") || tag.contains("conversational") {
            if mid.contains("r1") || mid.contains("reason") {
                "reasoning"
            } else if mid.contains("coder") || mid.contains("starcoder") {
                "code"
            } else {
                "general_llm"
            }
        } else if tag.contains("image") || tag.contains("visual") || tag.contains("vision") || tag.contains("object-detection") {
            "vision"
        } else if tag.contains("audio") || tag.contains("speech") || tag.contains("text-to-speech") || tag.contains("automatic-speech-recognition") {
            "audio"
        } else if tag.contains("feature-extraction") || tag.contains("sentence-similarity") || mid.contains("embed") {
            "embeddings"
        } else if mid.contains("finbert") || mid.contains("fingpt") || mid.contains("chronos") {
            "finance"
        } else if mid.contains("legal") || mid.contains("saul") || mid.contains("cuad") {
            "legal"
        } else if mid.contains("sec") || mid.contains("cisco") || mid.contains("malware") {
            "security"
        } else if mid.contains("esm") || mid.contains("evo2") || mid.contains("chemberta") || mid.contains("bio") {
            "science"
        } else if tag.contains("classification") || tag.contains("text-classification") || tag.contains("zero-shot") {
            "classification"
        } else if tag.contains("translation") {
            "translation"
        } else if tag.contains("summarization") {
            "summarization"
        } else if tag.contains("time-series") || tag.contains("timeseries") {
            "timeseries"
        } else {
            "general_domain"
        }
    }

    pub fn effective_priority_score(&self) -> f64 {
        let norm_dec = if self.decision_score <= 1.0 && self.decision_score > 0.0 {
            self.decision_score * 10.0
        } else {
            self.decision_score
        };
        norm_dec * (0.55 + 0.45 * self.recency_score())
    }
}

/// Top-level statistics for a task category.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TaskStat {
    pub pipeline_tag: String,
    pub model_count: i64,
    pub avg_downloads: f64,
    pub avg_decision_score: f64,
}

/// Comprehensive statistics across the entire model database.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DatabaseStats {
    pub total_models: i64,
    pub last_updated: Option<String>,
    pub top_tasks: Vec<TaskStat>,
    pub top_models: Vec<ModelMetrics>,
}

/// SQLite-backed store for HuggingFace model metadata.
pub struct HuggingFaceModelDatabase {
    pub db_path: PathBuf,
}

impl HuggingFaceModelDatabase {
    /// Open (or create) a database at `db_path`.
    pub fn new(db_path: impl AsRef<Path>) -> Result<Self> {
        let db_path = db_path.as_ref().to_path_buf();
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let db = Self { db_path };
        db.init()?;
        Ok(db)
    }

    /// Open an existing database for read/write operations without re-running DDL initialization.
    pub fn open(db_path: impl AsRef<Path>) -> Result<Self> {
        let db_path = db_path.as_ref().to_path_buf();
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let db = Self { db_path };
        if db.db_path.exists() {
            db.migrate_schema()?;
        }
        Ok(db)
    }

    /// Open a connection applying all startup pragmas.
    pub fn connect(&self) -> Result<Connection> {
        let conn = Connection::open(&self.db_path)
            .with_context(|| format!("Cannot open DB at {}", self.db_path.display()))?;
        conn.busy_timeout(std::time::Duration::from_secs(30))?;
        for pragma in schema::STARTUP_PRAGMAS {
            let _ = conn.query_row(pragma, [], |_| Ok(()));
        }
        Ok(conn)
    }

    /// Create tables and indexes if they don't exist.
    pub fn init(&self) -> Result<()> {
        let conn = self.connect()?;
        conn.execute_batch(schema::CREATE_MODELS_TABLE)?;
        conn.execute_batch(schema::CREATE_METADATA_TABLE)?;
        conn.execute_batch(schema::CREATE_KEYWORD_SEARCHES_TABLE)?;
        schema::migrate_schema(&conn)?;
        for idx in schema::CREATE_INDEXES {
            conn.execute_batch(idx)?;
        }
        log::info!("Database initialised at {}", self.db_path.display());
        Ok(())
    }

    /// Migrate the database schema idempotently, ensuring all required columns exist.
    pub fn migrate_schema(&self) -> Result<()> {
        let conn = self.connect()?;
        schema::migrate_schema(&conn)?;
        Ok(())
    }

    /// Check database integrity; returns `Ok(())` if healthy.
    pub fn check_integrity(&self) -> Result<()> {
        let conn = self.connect()?;
        let result: String = conn.query_row(
            "PRAGMA integrity_check",
            [],
            |row| row.get(0),
        )?;
        if result == "ok" {
            Ok(())
        } else {
            anyhow::bail!("Integrity check failed: {}", result)
        }
    }

    /// Upsert a model record (insert or replace on `model_id` conflict).
    pub fn upsert(&self, model: &ModelMetrics) -> Result<()> {
        let conn = self.connect()?;
        let tags = serde_json::to_string(&model.tags).unwrap_or_default();
        let keywords = serde_json::to_string(&model.task_keywords).unwrap_or_default();
        let feed_source = if model.feed_source.is_empty() {
            "standard_hub"
        } else {
            model.feed_source.as_str()
        };

        conn.execute(
            r#"INSERT INTO models (
                model_id, author, pipeline_tag, tags, description,
                downloads, likes, decision_score, capability_score,
                efficiency_score, popularity_score, model_type, library_name,
                last_modified, license, task_keywords, architecture, size_mb, language,
                trending_score, feed_source, bandit_pulls, bandit_reward,
                updated_at
            ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?23,datetime('now'))
            ON CONFLICT(model_id) DO UPDATE SET
                pipeline_tag     = excluded.pipeline_tag,
                tags             = excluded.tags,
                description      = excluded.description,
                downloads        = excluded.downloads,
                likes            = excluded.likes,
                decision_score   = excluded.decision_score,
                capability_score = excluded.capability_score,
                efficiency_score = excluded.efficiency_score,
                popularity_score = excluded.popularity_score,
                model_type       = excluded.model_type,
                library_name     = excluded.library_name,
                last_modified    = excluded.last_modified,
                license          = excluded.license,
                task_keywords    = excluded.task_keywords,
                architecture     = excluded.architecture,
                size_mb          = excluded.size_mb,
                language         = excluded.language,
                trending_score   = CASE WHEN excluded.trending_score > 0.0 THEN excluded.trending_score ELSE models.trending_score END,
                feed_source      = CASE
                    WHEN models.feed_source = 'trending+following'
                      OR excluded.feed_source = 'trending+following'
                      OR (models.feed_source = 'trending' AND excluded.feed_source = 'following_activity')
                      OR (models.feed_source = 'following_activity' AND excluded.feed_source = 'trending')
                    THEN 'trending+following'
                    WHEN excluded.feed_source IS NOT NULL AND excluded.feed_source != '' AND excluded.feed_source != 'standard_hub'
                    THEN excluded.feed_source
                    ELSE models.feed_source
                END,
                bandit_pulls     = CASE WHEN excluded.bandit_pulls > 0 THEN excluded.bandit_pulls ELSE models.bandit_pulls END,
                bandit_reward    = CASE WHEN excluded.bandit_reward > 0.0 THEN excluded.bandit_reward ELSE models.bandit_reward END,
                updated_at       = datetime('now')"#,
            params![
                model.model_id, model.author, model.pipeline_tag, tags, model.description,
                model.downloads, model.likes, model.decision_score, model.capability_score,
                model.efficiency_score, model.popularity_score, model.model_type, model.library_name,
                model.last_modified, model.license, keywords, model.architecture, model.size_mb,
                model.language, model.trending_score, feed_source, model.bandit_pulls,
                model.bandit_reward
            ],
        )?;
        Ok(())
    }

    /// Batch upsert many models in a single transaction.
    pub fn upsert_batch(&self, models: &[ModelMetrics]) -> Result<usize> {
        let conn = self.connect()?;
        let mut count = 0usize;
        {
            let tx = conn;
            tx.execute_batch("BEGIN")?;
            for model in models {
                let tags = serde_json::to_string(&model.tags).unwrap_or_default();
                let keywords = serde_json::to_string(&model.task_keywords).unwrap_or_default();
                let feed_source = if model.feed_source.is_empty() {
                    "standard_hub"
                } else {
                    model.feed_source.as_str()
                };
                tx.execute(
                    r#"INSERT INTO models (
                        model_id, author, pipeline_tag, tags, description,
                        downloads, likes, decision_score, capability_score,
                        efficiency_score, popularity_score, model_type, library_name,
                        last_modified, license, task_keywords, architecture, size_mb, language,
                        trending_score, feed_source, bandit_pulls, bandit_reward,
                        updated_at
                    ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?23,datetime('now'))
                    ON CONFLICT(model_id) DO UPDATE SET
                        pipeline_tag     = excluded.pipeline_tag,
                        tags             = excluded.tags,
                        description      = excluded.description,
                        downloads        = excluded.downloads,
                        likes            = excluded.likes,
                        decision_score   = excluded.decision_score,
                        capability_score = excluded.capability_score,
                        efficiency_score = excluded.efficiency_score,
                        popularity_score = excluded.popularity_score,
                        model_type       = excluded.model_type,
                        library_name     = excluded.library_name,
                        last_modified    = excluded.last_modified,
                        license          = excluded.license,
                        task_keywords    = excluded.task_keywords,
                        architecture     = excluded.architecture,
                        size_mb          = excluded.size_mb,
                        language         = excluded.language,
                        trending_score   = CASE WHEN excluded.trending_score > 0.0 THEN excluded.trending_score ELSE models.trending_score END,
                        feed_source      = CASE
                            WHEN models.feed_source = 'trending+following'
                              OR excluded.feed_source = 'trending+following'
                              OR (models.feed_source = 'trending' AND excluded.feed_source = 'following_activity')
                              OR (models.feed_source = 'following_activity' AND excluded.feed_source = 'trending')
                            THEN 'trending+following'
                            WHEN excluded.feed_source IS NOT NULL AND excluded.feed_source != '' AND excluded.feed_source != 'standard_hub'
                            THEN excluded.feed_source
                            ELSE models.feed_source
                        END,
                        bandit_pulls     = CASE WHEN excluded.bandit_pulls > 0 THEN excluded.bandit_pulls ELSE models.bandit_pulls END,
                        bandit_reward    = CASE WHEN excluded.bandit_reward > 0.0 THEN excluded.bandit_reward ELSE models.bandit_reward END,
                        updated_at       = datetime('now')"#,
                    params![
                        model.model_id, model.author, model.pipeline_tag, tags, model.description,
                        model.downloads, model.likes, model.decision_score, model.capability_score,
                        model.efficiency_score, model.popularity_score, model.model_type,
                        model.library_name, model.last_modified, model.license, keywords,
                        model.architecture, model.size_mb, model.language, model.trending_score,
                        feed_source, model.bandit_pulls, model.bandit_reward
                    ],
                )?;
                count += 1;
            }
            tx.execute_batch("COMMIT")?;
        }
        Ok(count)
    }

    /// Upsert multiple models (alias for upsert_batch).
    pub fn upsert_models(&self, models: &[ModelMetrics]) -> Result<usize> {
        self.upsert_batch(models)
    }

    /// Retrieve the top `limit` models for a given `pipeline_tag`, ranked by
    /// temporal freshness and effective priority score descending.
    pub fn get_by_task(&self, pipeline_tag: &str, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let candidate_limit = (limit * 3).max(60) as i64;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language,
                      trending_score, feed_source, bandit_pulls, bandit_reward
               FROM models
               WHERE pipeline_tag = ?1
               ORDER BY (
                 (CASE WHEN decision_score <= 1.0 AND decision_score > 0.0 THEN decision_score * 10.0 ELSE decision_score END) *
                 (CASE
                   WHEN last_modified >= '2025-06-01' THEN 1.0
                   WHEN last_modified >= '2024-06-01' THEN 0.80
                   WHEN last_modified >= '2023-01-01' THEN 0.50
                   ELSE 0.30
                 END)
               ) DESC, downloads DESC
               LIMIT ?2"#,
        )?;
        let rows = stmt.query_map(params![pipeline_tag, candidate_limit], row_to_model)?;
        let mut models = rows.collect::<Result<Vec<_>, _>>()?;
        models.sort_by(|a, b| b.effective_priority_score().partial_cmp(&a.effective_priority_score()).unwrap_or(std::cmp::Ordering::Equal));
        models.truncate(limit);
        Ok(models)
    }

    /// Full-text style search: returns models whose model_id or description
    /// contains `query` (case-insensitive), ordered by effective priority score.
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let like = format!("%{}%", query.to_lowercase());
        let candidate_limit = (limit * 3).max(60) as i64;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language,
                      trending_score, feed_source, bandit_pulls, bandit_reward
               FROM models
               WHERE lower(model_id) LIKE ?1 OR lower(description) LIKE ?1
               ORDER BY (
                 (CASE WHEN decision_score <= 1.0 AND decision_score > 0.0 THEN decision_score * 10.0 ELSE decision_score END) *
                 (CASE
                   WHEN last_modified >= '2025-06-01' THEN 1.0
                   WHEN last_modified >= '2024-06-01' THEN 0.80
                   WHEN last_modified >= '2023-01-01' THEN 0.50
                   ELSE 0.30
                 END)
               ) DESC, downloads DESC
               LIMIT ?2"#,
        )?;
        let rows = stmt.query_map(params![like, candidate_limit], row_to_model)?;
        let mut models = rows.collect::<Result<Vec<_>, _>>()?;
        models.sort_by(|a, b| b.effective_priority_score().partial_cmp(&a.effective_priority_score()).unwrap_or(std::cmp::Ordering::Equal));
        models.truncate(limit);
        Ok(models)
    }

    /// Total number of models in the database.
    pub fn count(&self) -> Result<i64> {
        let conn = self.connect()?;
        conn.query_row("SELECT COUNT(*) FROM models", [], |r| r.get(0))
            .map_err(Into::into)
    }

    /// Set a metadata key.
    pub fn set_meta(&self, key: &str, value: &str) -> Result<()> {
        let conn = self.connect()?;
        conn.execute(
            "INSERT INTO metadata(key, value, updated_at) VALUES(?1,?2,datetime('now'))
             ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            params![key, value],
        )?;
        Ok(())
    }

    /// Get a metadata value by key.
    pub fn get_meta(&self, key: &str) -> Result<Option<String>> {
        let conn = self.connect()?;
        let result = conn.query_row(
            "SELECT value FROM metadata WHERE key = ?1",
            params![key],
            |r| r.get(0),
        );
        match result {
            Ok(v) => Ok(Some(v)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// Return all distinct model IDs in the database, ordered by decision_score.
    pub fn get_all_model_ids(&self) -> Result<Vec<String>> {
        let conn = self.connect()?;
        let mut stmt = conn.prepare(
            "SELECT DISTINCT model_id FROM models ORDER BY decision_score DESC, downloads DESC",
        )?;
        let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    /// Return model IDs where size_mb <= max_size_mb, ordered by decision_score.
    /// Used by `--prepare-all-models` to skip very large models.
    pub fn get_small_model_ids(&self, max_size_mb: f64) -> Result<Vec<String>> {
        let conn = self.connect()?;
        let mut stmt = conn.prepare(
            "SELECT DISTINCT model_id FROM models WHERE size_mb > 0 AND size_mb <= ?1 ORDER BY decision_score DESC, downloads DESC",
        )?;
        let rows = stmt.query_map(params![max_size_mb], |row| row.get::<_, String>(0))?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    /// Return top overall models sorted by effective priority score
    pub fn get_top_overall(&self, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let candidate_limit = (limit * 3).max(60) as i64;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language,
                      trending_score, feed_source, bandit_pulls, bandit_reward
               FROM models
               ORDER BY (
                 (CASE WHEN decision_score <= 1.0 AND decision_score > 0.0 THEN decision_score * 10.0 ELSE decision_score END) *
                 (CASE
                   WHEN last_modified >= '2025-06-01' THEN 1.0
                   WHEN last_modified >= '2024-06-01' THEN 0.80
                   WHEN last_modified >= '2023-01-01' THEN 0.50
                   ELSE 0.30
                 END)
               ) DESC, downloads DESC
               LIMIT ?1"#,
        )?;
        let rows = stmt.query_map(params![candidate_limit], row_to_model)?;
        let mut models = rows.collect::<Result<Vec<_>, _>>()?;
        models.sort_by(|a, b| b.effective_priority_score().partial_cmp(&a.effective_priority_score()).unwrap_or(std::cmp::Ordering::Equal));
        models.truncate(limit);
        Ok(models)
    }

    /// Retrieve top trending models ordered by trending_score DESC, downloads DESC.
    pub fn get_trending(&self, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language,
                      trending_score, feed_source, bandit_pulls, bandit_reward
               FROM models
               ORDER BY trending_score DESC, downloads DESC
               LIMIT ?1"#,
        )?;
        let rows = stmt.query_map(params![limit as i64], row_to_model)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    /// Retrieve top trending models (alias for get_trending).
    pub fn get_trending_models(&self, limit: usize) -> Result<Vec<ModelMetrics>> {
        self.get_trending(limit)
    }

    /// Retrieve models filtered by feed_source (e.g. 'trending', 'following_activity', 'trending+following').
    pub fn get_by_feed_source(&self, feed_source: &str, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language,
                      trending_score, feed_source, bandit_pulls, bandit_reward
               FROM models
               WHERE feed_source = ?1 OR feed_source = 'trending+following'
               ORDER BY trending_score DESC, downloads DESC
               LIMIT ?2"#,
        )?;
        let rows = stmt.query_map(params![feed_source, limit as i64], row_to_model)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    /// Increment bandit pull count and accumulate reward for reinforcement learning exploration.
    pub fn record_bandit_pull(&self, model_id: &str, reward: f64) -> Result<()> {
        let conn = self.connect()?;
        conn.execute(
            "UPDATE models
             SET bandit_pulls = bandit_pulls + 1,
                 bandit_reward = bandit_reward + ?2,
                 updated_at = datetime('now')
             WHERE model_id = ?1",
            params![model_id, reward],
        )?;
        Ok(())
    }

    /// Reorganizes and recalibrates database scores:
    /// - Normalizes all decision_score values to 0..10 scale.
    /// - Penalizes stale/legacy architectures (>2 years old or legacy gpt2/llama-2/opt/bloom).
    /// - Boosts verified modern 2025/2026 releases.
    pub fn reorganize_and_recalibrate_stale_models(&self) -> Result<usize> {
        let conn = self.connect()?;
        let mut updated = 0;
        // 1. Rescale any 0..1 decision scores to 0..10
        let r1 = conn.execute(
            "UPDATE models
             SET decision_score = decision_score * 10.0,
                 capability_score = capability_score * 10.0,
                 efficiency_score = efficiency_score * 10.0,
                 popularity_score = popularity_score * 10.0
             WHERE decision_score <= 1.0 AND decision_score > 0.0",
            [],
        )?;
        updated += r1;

        // 2. Deprioritize stale models (>2 years old or legacy architecture)
        let r2 = conn.execute(
            "UPDATE models
             SET decision_score = ROUND(decision_score * 0.60, 2)
             WHERE (last_modified < '2024-01-01'
                    OR lower(model_id) LIKE '%gpt2%'
                    OR lower(model_id) LIKE '%llama-2%'
                    OR lower(model_id) LIKE '%opt-%'
                    OR lower(model_id) LIKE '%bloom%'
                    OR lower(model_id) LIKE '%falcon-7b%'
                    OR lower(model_id) LIKE '%vicuna%')
               AND decision_score > 3.0",
            [],
        )?;
        updated += r2;

        // 3. Boost modern 2025/2026 workhorse models
        let r3 = conn.execute(
            "UPDATE models
             SET decision_score = MIN(10.0, ROUND(decision_score * 1.15, 2))
             WHERE last_modified >= '2025-01-01'
               AND (lower(model_id) LIKE '%qwen%'
                    OR lower(model_id) LIKE '%deepseek%'
                    OR lower(model_id) LIKE '%gemma%'
                    OR lower(model_id) LIKE '%llama-3%'
                    OR lower(model_id) LIKE '%phi-4%'
                    OR lower(model_id) LIKE '%bge%'
                    OR lower(model_id) LIKE '%esm3%'
                    OR lower(model_id) LIKE '%flux%')",
            [],
        )?;
        updated += r3;

        Ok(updated)
    }

    /// Calculate database statistics including total models, last updated timestamp,
    /// top pipeline tags, and top ranked models.
    pub fn full_stats(&self) -> Result<DatabaseStats> {
        let conn = self.connect()?;
        let total_models: i64 = conn.query_row("SELECT COUNT(*) FROM models", [], |r| r.get(0))?;
        let last_updated = self.get_meta("last_updated")?;

        let mut stmt = conn.prepare(
            r#"SELECT pipeline_tag, COUNT(*) as cnt, AVG(downloads) as avg_d, AVG(decision_score) as avg_s
               FROM models
               WHERE pipeline_tag IS NOT NULL AND pipeline_tag != ''
               GROUP BY pipeline_tag
               ORDER BY cnt DESC
               LIMIT 20"#,
        )?;
        let task_rows = stmt.query_map([], |row| {
            Ok(TaskStat {
                pipeline_tag: row.get::<_, Option<String>>(0)?.unwrap_or_default(),
                model_count: row.get(1)?,
                avg_downloads: row.get::<_, Option<f64>>(2)?.unwrap_or(0.0),
                avg_decision_score: row.get::<_, Option<f64>>(3)?.unwrap_or(0.0),
            })
        })?;
        let mut top_tasks = Vec::new();
        for t in task_rows {
            top_tasks.push(t?);
        }

        let top_models = self.get_top_overall(10)?;

        Ok(DatabaseStats {
            total_models,
            last_updated,
            top_tasks,
            top_models,
        })
    }

    /// Dynamically selects the best, freshest, and hardware-appropriate model for a given menu category.
    ///
    /// Considers:
    /// 1. Category keywords and pipeline tags (e.g. finance, banking, writing, legal, security, vision, audio, code).
    /// 2. Hardware sizing constraint: `max_param_b` derived from `free_ram_gb` and `free_vram_mb`.
    /// 3. Staleness penalty: filters out or strongly downweights stale models (<0.45 recency_score or legacy architecture).
    /// 4. Freshness boost: prioritizes 2025/2026 releases.
    pub fn select_best_dynamic_model_for_menu(
        &self,
        category: &str,
        query_hint: Option<&str>,
        free_ram_gb: f64,
        free_vram_mb: f64,
    ) -> Result<Option<ModelMetrics>> {
        let cat = category.to_lowercase().trim().to_string();
        let max_param_b = if free_ram_gb < 6.0 && free_vram_mb < 2000.0 {
            2.5
        } else if free_ram_gb < 12.0 && free_vram_mb < 4500.0 {
            4.5
        } else if free_ram_gb < 24.0 && free_vram_mb < 12000.0 {
            9.5
        } else if free_ram_gb < 48.0 && free_vram_mb < 22000.0 {
            16.0
        } else {
            75.0
        };

        let (keywords, pipeline_tags): (Vec<&str>, Vec<&str>) = match cat.as_str() {
            "finance" | "banking" | "fintech" => (
                vec!["finance", "banking", "financial", "fingpt", "finbert", "market", "stock", "trading", "qwen-finance", "chronos"],
                vec!["text-generation", "time-series-forecasting", "tabular-regression", "text-classification"],
            ),
            "writing" | "editing" | "narrative" | "prose" => (
                vec!["writing", "creative", "editing", "narrative", "gemma2", "gemma-2", "qwen", "paraphrase"],
                vec!["text-generation", "text2text-generation"],
            ),
            "deep_research" | "research" | "reasoning" => (
                vec!["reasoning", "research", "r1", "deepseek-r1", "cot", "think", "qwq"],
                vec!["text-generation"],
            ),
            "code" | "programming" | "software" => (
                vec!["coder", "code", "qwen2.5-coder", "starcoder", "python", "rust"],
                vec!["text-generation"],
            ),
            "security" | "threat_audit" | "cybersecurity" => (
                vec!["security", "cybersecurity", "threat", "foundation-sec", "secbert", "malware", "vulnerability"],
                vec!["text-generation", "text-classification"],
            ),
            "legal" | "compliance" => (
                vec!["legal", "law", "saul", "lawma", "contract", "compliance", "regulatory", "legal-bert"],
                vec!["text-generation", "fill-mask", "text-classification"],
            ),
            "science" | "chemistry" | "bioinformatics" => (
                vec!["science", "protein", "biology", "esm", "chemberta", "chemberta-2", "bio", "evo2"],
                vec!["text-generation", "feature-extraction", "protein-folding"],
            ),
            "vision" | "image" | "multimodal" => (
                vec!["vision", "multimodal", "vl", "qwen-vl", "florence", "yolo", "flux", "segment"],
                vec!["image-text-to-text", "image-classification", "object-detection", "text-to-image", "image-segmentation"],
            ),
            "audio" | "speech" => (
                vec!["audio", "speech", "whisper", "tts", "asr", "kokoro"],
                vec!["automatic-speech-recognition", "text-to-speech", "audio-classification"],
            ),
            "classification" | "sentiment" => (
                vec!["classification", "sentiment", "emotion", "intent", "deberta", "bart"],
                vec!["text-classification"],
            ),
            "data_science" | "tabular" | "timeseries" => (
                vec!["tabular", "timeseries", "forecasting", "chronos", "patchtst", "xgboost"],
                vec!["tabular-classification", "tabular-regression", "time-series-forecasting"],
            ),
            _ => (
                vec!["general", "chat", "assistant", "qwen", "llama-3", "gemma"],
                vec!["text-generation", "conversational"],
            ),
        };

        let mut candidates = Vec::new();
        let query_str = query_hint.unwrap_or("").to_lowercase();

        for ptag in &pipeline_tags {
            if let Ok(mut list) = self.get_by_task(ptag, 40) {
                candidates.append(&mut list);
            }
        }

        for kw in &keywords {
            if let Ok(mut list) = self.search(kw, 20) {
                candidates.append(&mut list);
            }
        }

        if !query_str.is_empty() {
            if let Ok(mut list) = self.search(&query_str, 20) {
                candidates.append(&mut list);
            }
        }

        // If no domain candidates exist, fall back to top overall models
        if candidates.is_empty() {
            if let Ok(list) = self.get_top_overall(20) {
                candidates = list;
            }
        }

        let mut seen = HashSet::new();
        let mut unique_candidates = Vec::new();
        for m in candidates {
            if seen.insert(m.model_id.clone()) {
                unique_candidates.push(m);
            }
        }

        if unique_candidates.is_empty() {
            return Ok(None);
        }

        let get_param_b = |m: &ModelMetrics| -> f64 {
            let lower = m.model_id.to_lowercase();
            if lower.contains("70b") || lower.contains("72b") { return 72.0; }
            if lower.contains("32b") || lower.contains("34b") { return 32.0; }
            if lower.contains("27b") { return 27.0; }
            if lower.contains("14b") { return 14.0; }
            if lower.contains("9b") || lower.contains("8b") { return 8.5; }
            if lower.contains("7b") { return 7.0; }
            if lower.contains("3b") || lower.contains("4b") { return 3.5; }
            if lower.contains("2b") { return 2.0; }
            if lower.contains("1.5b") { return 1.5; }
            if lower.contains("0.5b") { return 0.5; }
            if m.size_mb > 0.0 {
                return (m.size_mb / 2000.0).max(0.5);
            }
            7.0
        };

        let mut scored: Vec<(f64, ModelMetrics)> = unique_candidates.into_iter().map(|m| {
            let param_b = get_param_b(&m);
            let fits_hardware = param_b <= max_param_b;
            let hw_penalty = if fits_hardware { 1.0 } else { 0.20 };
            let staleness_penalty = if m.is_stale_or_legacy_architecture() || m.recency_score() < 0.45 {
                0.25
            } else {
                1.0
            };
            let mid = m.model_id.to_lowercase();
            let desc = m.description.to_lowercase();
            let mut match_bonus = 1.0;
            for kw in &keywords {
                if mid.contains(kw) || desc.contains(kw) {
                    match_bonus += 0.5;
                }
            }
            let total_score = m.effective_priority_score() * hw_penalty * staleness_penalty * match_bonus;
            (total_score, m)
        }).collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

        Ok(scored.into_iter().next().map(|(_, m)| m))
    }

    /// Returns dynamic model recommendations for standard menu actions
    /// (e.g. "finance", "banking", "writing", "code", "security", "legal", "research", "vision", "audio", "classification", "data_science").
    pub fn get_dynamic_menu_recommendations(
        &self,
        free_ram_gb: f64,
        free_vram_mb: f64,
    ) -> Result<HashMap<String, ModelMetrics>> {
        let categories = [
            "finance",
            "banking",
            "writing",
            "deep_research",
            "code",
            "security",
            "legal",
            "science",
            "vision",
            "audio",
            "classification",
            "data_science",
            "general",
        ];
        let mut map = HashMap::new();
        for cat in &categories {
            if let Ok(Some(model)) = self.select_best_dynamic_model_for_menu(cat, None, free_ram_gb, free_vram_mb) {
                map.insert(cat.to_string(), model);
            }
        }
        Ok(map)
    }
}

// ── helpers ────────────────────────────────────────────────────────────────

fn row_to_model(row: &rusqlite::Row<'_>) -> rusqlite::Result<ModelMetrics> {
    let tags_json: String = row.get(3)?;
    let keywords_json: String = row.get(15)?;

    let trending_score: f64 = row
        .get::<_, Option<f64>>(19)
        .or_else(|_| row.get::<_, Option<f64>>("trending_score"))
        .unwrap_or(None)
        .unwrap_or(0.0);

    let feed_source: String = row
        .get::<_, Option<String>>(20)
        .or_else(|_| row.get::<_, Option<String>>("feed_source"))
        .unwrap_or(None)
        .filter(|s| !s.is_empty())
        .unwrap_or_else(default_feed_source);

    let bandit_pulls: i64 = row
        .get::<_, Option<i64>>(21)
        .or_else(|_| row.get::<_, Option<i64>>("bandit_pulls"))
        .unwrap_or(None)
        .unwrap_or(0);

    let bandit_reward: f64 = row
        .get::<_, Option<f64>>(22)
        .or_else(|_| row.get::<_, Option<f64>>("bandit_reward"))
        .unwrap_or(None)
        .unwrap_or(0.0);

    Ok(ModelMetrics {
        model_id: row.get(0)?,
        author: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
        pipeline_tag: row.get::<_, Option<String>>(2)?.unwrap_or_default(),
        tags: serde_json::from_str(&tags_json).unwrap_or_default(),
        description: row.get::<_, Option<String>>(4)?.unwrap_or_default(),
        downloads: row.get(5)?,
        likes: row.get(6)?,
        decision_score: row.get(7)?,
        capability_score: row.get(8)?,
        efficiency_score: row.get(9)?,
        popularity_score: row.get(10)?,
        model_type: row.get::<_, Option<String>>(11)?.unwrap_or_default(),
        library_name: row.get::<_, Option<String>>(12)?.unwrap_or_default(),
        last_modified: row.get::<_, Option<String>>(13)?.unwrap_or_default(),
        license: row.get::<_, Option<String>>(14)?.unwrap_or_default(),
        task_keywords: serde_json::from_str(&keywords_json).unwrap_or_default(),
        architecture: row.get::<_, Option<String>>(16)?.unwrap_or_default(),
        size_mb: row.get(17)?,
        language: row.get::<_, Option<String>>(18)?.unwrap_or_default(),
        trending_score,
        feed_source,
        bandit_pulls,
        bandit_reward,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_db(name: &str) -> HuggingFaceModelDatabase {
        let unique_id = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("mf_test_db_{}_{}.sqlite", name, unique_id));
        let _ = fs::remove_file(&path);
        HuggingFaceModelDatabase::new(&path).unwrap()
    }

    #[test]
    fn upsert_and_count() {
        let db = temp_db("upsert");
        let model = ModelMetrics {
            model_id: "test/model".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 1000,
            decision_score: 0.9,
            ..Default::default()
        };
        db.upsert(&model).unwrap();
        assert_eq!(db.count().unwrap(), 1);
    }

    #[test]
    fn get_by_task_returns_ranked() {
        let db = temp_db("ranked");
        for (id, score) in &[("a/model", 0.8), ("b/model", 0.95), ("c/model", 0.5)] {
            db.upsert(&ModelMetrics {
                model_id: id.to_string(),
                pipeline_tag: "summarization".to_string(),
                decision_score: *score,
                ..Default::default()
            })
            .unwrap();
        }
        let results = db.get_by_task("summarization", 2).unwrap();
        assert_eq!(results[0].model_id, "b/model");
        assert_eq!(results[1].model_id, "a/model");
    }

    #[test]
    fn test_schema_migration_and_trending_persistence() {
        let unique_id = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("mf_test_migration_{}.sqlite", unique_id));
        let _ = fs::remove_file(&path);

        // 1. Manually construct legacy pre-migration schema without the 4 new columns
        {
            let raw_conn = rusqlite::Connection::open(&path)
                .expect("Failed to create raw test SQLite database");
            raw_conn.execute_batch(r#"
                CREATE TABLE models (
                    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
                    model_id          TEXT     UNIQUE NOT NULL,
                    author            TEXT,
                    pipeline_tag      TEXT,
                    tags              TEXT,
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
                    task_keywords     TEXT,
                    architecture      TEXT,
                    size_mb           REAL     DEFAULT 0.0,
                    language          TEXT,
                    created_at        TEXT     DEFAULT (datetime('now')),
                    updated_at        TEXT     DEFAULT (datetime('now'))
                );
                CREATE TABLE metadata (
                    key        TEXT PRIMARY KEY,
                    value      TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                );
            "#).expect("Failed to initialize legacy schema");

            // Verify the 4 columns are missing prior to migration
            let mut stmt = raw_conn.prepare("PRAGMA table_info(models)").unwrap();
            let initial_cols: HashSet<String> = stmt
                .query_map([], |row| row.get::<_, String>(1))
                .unwrap()
                .map(|r| r.unwrap().to_ascii_lowercase())
                .collect();
            assert!(!initial_cols.contains("trending_score"), "trending_score should not exist before migration");
            assert!(!initial_cols.contains("feed_source"), "feed_source should not exist before migration");
            assert!(!initial_cols.contains("bandit_pulls"), "bandit_pulls should not exist before migration");
            assert!(!initial_cols.contains("bandit_reward"), "bandit_reward should not exist before migration");
        }

        // 2. Open via HuggingFaceModelDatabase and execute migration
        let db = HuggingFaceModelDatabase::open(&path).expect("Failed to open DB");
        db.migrate_schema().expect("Migration failed");

        // 3. Inspect PRAGMA table_info(models) and verify columns exist
        {
            let conn = db.connect().expect("Failed to connect after migration");
            let mut stmt = conn.prepare("PRAGMA table_info(models)").expect("Failed to prepare pragma");
            let migrated_cols: HashSet<String> = stmt
                .query_map([], |row| row.get::<_, String>(1))
                .expect("Failed to query pragma")
                .map(|r| r.unwrap().to_ascii_lowercase())
                .collect();

            assert!(migrated_cols.contains("trending_score"), "trending_score column must exist after migration");
            assert!(migrated_cols.contains("feed_source"), "feed_source column must exist after migration");
            assert!(migrated_cols.contains("bandit_pulls"), "bandit_pulls column must exist after migration");
            assert!(migrated_cols.contains("bandit_reward"), "bandit_reward column must exist after migration");
        }

        // 4. Upsert a model with explicit trending and bandit metrics
        let test_model = ModelMetrics {
            model_id: "Qwen/Qwen2.5-Coder-32B-Instruct".to_string(),
            author: "Qwen".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 500_000,
            likes: 15_000,
            decision_score: 9.8,
            trending_score: 0.95,
            feed_source: "trending".to_string(),
            bandit_pulls: 10,
            bandit_reward: 8.5,
            ..Default::default()
        };
        db.upsert(&test_model).expect("Failed to upsert test model");

        // 5. Query back and verify all 4 fields are preserved with exact values
        let retrieved = db.get_by_task("text-generation", 10).expect("Failed to retrieve model");
        assert_eq!(retrieved.len(), 1);
        let m = &retrieved[0];
        assert_eq!(m.model_id, "Qwen/Qwen2.5-Coder-32B-Instruct");
        assert!((m.trending_score - 0.95).abs() < 1e-6, "trending_score mismatch: expected 0.95, got {}", m.trending_score);
        assert_eq!(m.feed_source, "trending", "feed_source mismatch: expected 'trending', got '{}'", m.feed_source);
        assert_eq!(m.bandit_pulls, 10, "bandit_pulls mismatch: expected 10, got {}", m.bandit_pulls);
        assert!((m.bandit_reward - 8.5).abs() < 1e-6, "bandit_reward mismatch: expected 8.5, got {}", m.bandit_reward);

        // 6. Test batch upsert with various feed sources and verify persistence
        let batch = vec![
            ModelMetrics {
                model_id: "deepseek-ai/DeepSeek-R1".to_string(),
                author: "deepseek-ai".to_string(),
                pipeline_tag: "text-generation".to_string(),
                trending_score: 0.99,
                feed_source: "following_activity".to_string(),
                bandit_pulls: 25,
                bandit_reward: 22.0,
                ..Default::default()
            },
            ModelMetrics {
                model_id: "RecursiveSI/flint".to_string(),
                author: "RecursiveSI".to_string(),
                pipeline_tag: "text-generation".to_string(),
                trending_score: 0.98,
                feed_source: "trending+following".to_string(),
                bandit_pulls: 50,
                bandit_reward: 48.0,
                ..Default::default()
            },
        ];
        let upserted_count = db.upsert_batch(&batch).expect("Failed to batch upsert models");
        assert_eq!(upserted_count, 2);

        let all_models = db.get_by_task("text-generation", 10).expect("Failed to query models");
        assert_eq!(all_models.len(), 3);

        let r1 = all_models.iter().find(|m| m.model_id == "deepseek-ai/DeepSeek-R1").unwrap();
        assert!((r1.trending_score - 0.99).abs() < 1e-6);
        assert_eq!(r1.feed_source, "following_activity");
        assert_eq!(r1.bandit_pulls, 25);
        assert!((r1.bandit_reward - 22.0).abs() < 1e-6);

        let flint = all_models.iter().find(|m| m.model_id == "RecursiveSI/flint").unwrap();
        assert!((flint.trending_score - 0.98).abs() < 1e-6);
        assert_eq!(flint.feed_source, "trending+following");
        assert_eq!(flint.bandit_pulls, 50);
        assert!((flint.bandit_reward - 48.0).abs() < 1e-6);

        // 7. Verify migration idempotency (second migration run on already migrated DB)
        assert!(db.migrate_schema().is_ok(), "migrate_schema must be idempotent and succeed on repeated execution");

        // Clean up temporary database file
        let _ = fs::remove_file(&path);
    }

    #[test]
    fn test_pipeline_tag_task_and_category_mapping() {
        // 1. Pipeline Tag to Task & Category Table Matrix
        let test_matrix = vec![
            ("text-generation", "text-generation", "Writing & Editing"),
            ("image-classification", "image-classification", "Images & Vision"),
            ("automatic-speech-recognition", "automatic-speech-recognition", "Voice & Audio"),
            ("text-to-image", "text-to-image", "Images & Vision"),
            ("text-to-speech", "text-to-speech", "Voice & Audio"),
            ("audio-classification", "audio-classification", "Voice & Audio"),
            ("tabular-classification", "tabular-classification", "Data & Spreadsheets (CSV/Excel)"),
            ("text-classification", "text-classification", "Classification & Taxonomy"),
            ("summarization", "summarization", "Writing & Editing"),
            ("translation", "translation", "Writing & Editing"),
            ("object-detection", "object-detection", "Images & Vision"),
            ("depth-estimation", "depth-estimation", "Images & Vision"),
            ("time-series-forecasting", "time-series-forecasting", "Data & Spreadsheets (CSV/Excel)"),
        ];

        for (ptag, expected_task, expected_cat) in test_matrix {
            let model = ModelMetrics {
                model_id: format!("generic/model-{}", ptag),
                pipeline_tag: ptag.to_string(),
                ..Default::default()
            };

            assert_eq!(
                model.task_name(),
                expected_task,
                "Model task_name mismatch for pipeline_tag '{}'",
                ptag
            );
            assert_eq!(
                model.browser_category(),
                expected_cat,
                "Model browser_category mismatch for pipeline_tag '{}'",
                ptag
            );
        }

        // 2. Domain-Specific Model ID Overrides
        let domain_overrides = vec![
            ("Qwen/Qwen2.5-Coder-32B-Instruct", "text-generation", "Code & Security"),
            ("deepseek-ai/DeepSeek-R1", "text-generation", "Deep Research"),
            ("ProsusAI/finbert", "text-classification", "Finance & Markets"),
            ("Equall/Saul-7B-Instruct", "text-generation", "Legal"),
            ("facebook/esm2_t33_650M_UR50D", "feature-extraction", "Science & Discovery"),
        ];

        for (model_id, ptag, expected_cat) in domain_overrides {
            let model = ModelMetrics {
                model_id: model_id.to_string(),
                pipeline_tag: ptag.to_string(),
                ..Default::default()
            };
            assert_eq!(
                model.browser_category(),
                expected_cat,
                "Domain override failed for model '{}' (pipeline_tag '{}')",
                model_id,
                ptag
            );
        }

        // 3. Fallback on Empty or Unknown Pipeline Tag
        let fallback_model = ModelMetrics {
            model_id: "unknown/generic-model".to_string(),
            pipeline_tag: "".to_string(),
            ..Default::default()
        };
        assert_eq!(fallback_model.task_name(), "text-generation");
        assert_eq!(fallback_model.browser_category(), "Writing & Editing");
    }

    #[test]
    fn test_upsert_conflict_feed_source_merge() {
        let db = temp_db("feed_merge");
        let m1 = ModelMetrics {
            model_id: "org/test-model".to_string(),
            pipeline_tag: "text-generation".to_string(),
            trending_score: 0.85,
            feed_source: "trending".to_string(),
            ..Default::default()
        };
        db.upsert(&m1).unwrap();

        // Followed org ingestion for the same model
        let m2 = ModelMetrics {
            model_id: "org/test-model".to_string(),
            pipeline_tag: "text-generation".to_string(),
            trending_score: 0.0,
            feed_source: "following_activity".to_string(),
            ..Default::default()
        };
        db.upsert(&m2).unwrap();

        let models = db.get_by_task("text-generation", 1).unwrap();
        assert_eq!(models[0].feed_source, "trending+following");
        assert_eq!(models[0].trending_score, 0.85); // Preserved positive score

        // Step 3: Subsequent update with single feed source 'trending' must NOT demote 'trending+following'
        let mut m3 = m2.clone();
        m3.feed_source = "trending".to_string();
        db.upsert(&m3).expect("upsert step 3");
        let updated_models_3 = db.get_by_task("text-generation", 10).expect("get step 3");
        assert_eq!(updated_models_3[0].feed_source, "trending+following");

        // Step 4: Subsequent update with single feed source 'following_activity' must NOT demote 'trending+following'
        let mut m4 = m3;
        m4.feed_source = "following_activity".to_string();
        db.upsert(&m4).expect("upsert step 4");
        let updated_models_4 = db.get_by_task("text-generation", 10).expect("get step 4");
        assert_eq!(updated_models_4[0].feed_source, "trending+following");
    }

    #[test]
    fn test_concurrent_schema_migration() {
        let unique_id = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!("mf_test_concurrent_mig_{}.sqlite", unique_id));
        let _ = fs::remove_file(&path);

        // Construct legacy schema without migration columns
        {
            let raw_conn = rusqlite::Connection::open(&path).unwrap();
            raw_conn.execute_batch(r#"
                CREATE TABLE models (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id          TEXT UNIQUE NOT NULL,
                    author            TEXT,
                    pipeline_tag      TEXT,
                    downloads         INTEGER DEFAULT 0
                );
            "#).unwrap();
        }

        let mut handles = Vec::new();
        for _ in 0..8 {
            let p = path.clone();
            handles.push(std::thread::spawn(move || {
                let db = HuggingFaceModelDatabase::open(&p).expect("concurrent open failed");
                let conn = db.connect().expect("connect failed");
                let mut stmt = conn.prepare("PRAGMA table_info(models)").expect("prepare failed");
                let cols: HashSet<String> = stmt
                    .query_map([], |row| row.get::<_, String>(1))
                    .expect("query failed")
                    .map(|r| r.unwrap().to_ascii_lowercase())
                    .collect();
                assert!(cols.contains("trending_score"));
                assert!(cols.contains("feed_source"));
            }));
        }

        for h in handles {
            h.join().expect("thread panicked");
        }

        let _ = fs::remove_file(&path);
    }

    #[test]
    fn test_record_bandit_pull() {
        let db = temp_db("bandit_pull");
        let model = ModelMetrics {
            model_id: "org/bandit-test".to_string(),
            pipeline_tag: "text-generation".to_string(),
            ..Default::default()
        };
        db.upsert(&model).unwrap();

        db.record_bandit_pull("org/bandit-test", 1.0).unwrap();
        db.record_bandit_pull("org/bandit-test", 0.5).unwrap();

        let models = db.get_by_task("text-generation", 1).unwrap();
        assert_eq!(models[0].bandit_pulls, 2);
        assert!((models[0].bandit_reward - 1.5).abs() < 1e-6);
    }
}

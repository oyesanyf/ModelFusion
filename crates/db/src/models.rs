//! `ModelMetrics` struct and all CRUD operations on the `models` table.

use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use crate::schema;

/// Full metadata record for a HuggingFace model.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
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
}

impl ModelMetrics {
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
        Ok(Self { db_path })
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
        for idx in schema::CREATE_INDEXES {
            conn.execute_batch(idx)?;
        }
        log::info!("Database initialised at {}", self.db_path.display());
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

        conn.execute(
            r#"INSERT INTO models (
                model_id, author, pipeline_tag, tags, description,
                downloads, likes, decision_score, capability_score,
                efficiency_score, popularity_score, model_type, library_name,
                last_modified, license, task_keywords, architecture, size_mb, language,
                updated_at
            ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,datetime('now'))
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
                last_modified    = excluded.last_modified,
                license          = excluded.license,
                task_keywords    = excluded.task_keywords,
                size_mb          = excluded.size_mb,
                updated_at       = datetime('now')"#,
            params![
                model.model_id, model.author, model.pipeline_tag, tags, model.description,
                model.downloads, model.likes, model.decision_score, model.capability_score,
                model.efficiency_score, model.popularity_score, model.model_type, model.library_name,
                model.last_modified, model.license, keywords, model.architecture, model.size_mb,
                model.language
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
                tx.execute(
                    r#"INSERT INTO models (
                        model_id, author, pipeline_tag, tags, description,
                        downloads, likes, decision_score, capability_score,
                        efficiency_score, popularity_score, model_type, library_name,
                        last_modified, license, task_keywords, architecture, size_mb, language,
                        updated_at
                    ) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,datetime('now'))
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
                        updated_at       = datetime('now')"#,
                    params![
                        model.model_id, model.author, model.pipeline_tag, tags, model.description,
                        model.downloads, model.likes, model.decision_score, model.capability_score,
                        model.efficiency_score, model.popularity_score, model.model_type,
                        model.library_name, model.last_modified, model.license, keywords,
                        model.architecture, model.size_mb, model.language
                    ],
                )?;
                count += 1;
            }
            tx.execute_batch("COMMIT")?;
        }
        Ok(count)
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
                      last_modified, license, task_keywords, architecture, size_mb, language
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
                      last_modified, license, task_keywords, architecture, size_mb, language
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
                      last_modified, license, task_keywords, architecture, size_mb, language
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
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn temp_db(name: &str) -> HuggingFaceModelDatabase {
        let path = std::env::temp_dir().join(format!("mf_test_db_{}.sqlite", name));
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
}

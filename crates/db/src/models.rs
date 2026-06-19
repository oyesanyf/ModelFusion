//! `ModelMetrics` struct and all CRUD operations on the `models` table.

use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
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
    /// Simple recency score: decays linearly from 1.0 to 0.1 over one year.
    pub fn recency_score(&self) -> f64 {
        use chrono::{DateTime, Utc};
        DateTime::parse_from_rfc3339(&self.last_modified)
            .or_else(|_| DateTime::parse_from_str(&self.last_modified, "%Y-%m-%dT%H:%M:%S%.fZ"))
            .map(|dt| {
                let days = (Utc::now() - dt.with_timezone(&Utc)).num_days();
                (1.0_f64 - days as f64 / 365.0).max(0.1)
            })
            .unwrap_or(0.5)
    }
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

    /// Open a connection applying all startup pragmas.
    pub fn connect(&self) -> Result<Connection> {
        let conn = Connection::open(&self.db_path)
            .with_context(|| format!("Cannot open DB at {}", self.db_path.display()))?;
        for pragma in schema::STARTUP_PRAGMAS {
            conn.execute_batch(pragma)?;
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
                        downloads      = excluded.downloads,
                        likes          = excluded.likes,
                        decision_score = excluded.decision_score,
                        updated_at     = datetime('now')"#,
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
    /// `decision_score` descending, then `downloads` descending.
    pub fn get_by_task(&self, pipeline_tag: &str, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language
               FROM models
               WHERE pipeline_tag = ?1
               ORDER BY decision_score DESC, downloads DESC
               LIMIT ?2"#,
        )?;
        let rows = stmt.query_map(params![pipeline_tag, limit as i64], row_to_model)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
    }

    /// Full-text style search: returns models whose model_id or description
    /// contains `query` (case-insensitive), ordered by `decision_score`.
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<ModelMetrics>> {
        let conn = self.connect()?;
        let like = format!("%{}%", query.to_lowercase());
        let mut stmt = conn.prepare(
            r#"SELECT model_id, author, pipeline_tag, tags, description,
                      downloads, likes, decision_score, capability_score,
                      efficiency_score, popularity_score, model_type, library_name,
                      last_modified, license, task_keywords, architecture, size_mb, language
               FROM models
               WHERE lower(model_id) LIKE ?1 OR lower(description) LIKE ?1
               ORDER BY decision_score DESC, downloads DESC
               LIMIT ?2"#,
        )?;
        let rows = stmt.query_map(params![like, limit as i64], row_to_model)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(Into::into)
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

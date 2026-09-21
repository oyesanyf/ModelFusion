//! Incremental Semantic Codebase Indexer
//!
//! Scans workspace directories, computes SHA-256 hashes for source files,
//! parses AST with Tree-Sitter, updates SQLite knowledge graph with FTS5,
//! and links call hierarchy edges.

use crate::db::{CodeGraphDb, GraphStats};
use crate::parser::{AstExtractor, LanguageKind};
use anyhow::Result;
use rusqlite::params;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::Path;
use std::time::Instant;
use walkdir::WalkDir;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexReport {
    pub workspace_path: String,
    pub files_scanned: usize,
    pub files_indexed: usize,
    pub files_skipped: usize,
    pub files_deleted: usize,
    pub total_symbols: usize,
    pub total_calls: usize,
    pub total_implementations: usize,
    pub total_references: usize,
    pub elapsed_ms: f64,
}

pub struct CodeGraphIndexer {
    extractor: AstExtractor,
}

impl CodeGraphIndexer {
    pub fn new() -> Result<Self> {
        let extractor = AstExtractor::new()?;
        Ok(Self { extractor })
    }

    /// Recursively scan and index a workspace directory incrementally into `db`.
    pub fn index_workspace(
        &mut self,
        db: &mut CodeGraphDb,
        workspace_path: &Path,
        force: bool,
    ) -> Result<IndexReport> {
        let t0 = Instant::now();
        let canonical_ws = workspace_path
            .canonicalize()
            .unwrap_or_else(|_| workspace_path.to_path_buf());

        let mut discovered_files = Vec::new();
        for entry in WalkDir::new(&canonical_ws)
            .into_iter()
            .filter_entry(|e| !should_ignore_entry(e))
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                if let Some(ext) = entry.path().extension().and_then(|s| s.to_str()) {
                    if LanguageKind::from_extension(ext).is_some() {
                        discovered_files.push(entry.into_path());
                    }
                }
            }
        }

        let mut files_indexed = 0;
        let mut files_skipped = 0;
        let mut existing_paths = Vec::new();

        for file_path in &discovered_files {
            let path_str = normalize_path(file_path);
            existing_paths.push(path_str.clone());

            let ext = file_path
                .extension()
                .and_then(|s| s.to_str())
                .unwrap_or_default();
            let lang = match LanguageKind::from_extension(ext) {
                Some(l) => l,
                None => continue,
            };
            let is_tsx = ext.eq_ignore_ascii_case("tsx") || ext.eq_ignore_ascii_case("jsx");

            let content = match std::fs::read(file_path) {
                Ok(bytes) => bytes,
                Err(e) => {
                    log::warn!("Failed to read file {:?}: {:?}", file_path, e);
                    continue;
                }
            };

            let content_str = match std::str::from_utf8(&content) {
                Ok(s) => s,
                Err(_) => continue, // Skip binary files
            };

            let mut hasher = Sha256::new();
            hasher.update(&content);
            let content_hash = hex::encode(hasher.finalize());

            // Check if existing hash matches
            if !force {
                if let Ok(Some(existing_hash)) = db.get_file_content_hash(&path_str) {
                    if existing_hash == content_hash {
                        files_skipped += 1;
                        continue;
                    }
                }
            }

            // Extract AST entities
            let entities = match self.extractor.parse(content_str, lang, is_tsx) {
                Ok(ent) => ent,
                Err(e) => {
                    log::warn!("AST parse error for {:?}: {:?}", file_path, e);
                    continue;
                }
            };

            let relative_path = file_path
                .strip_prefix(&canonical_ws)
                .unwrap_or(file_path)
                .to_string_lossy()
                .replace('\\', "/");

            // Store in DB transaction
            self.store_file_entities(
                db,
                &path_str,
                &relative_path,
                lang.as_str(),
                &content_hash,
                content.len(),
                &entities,
            )?;
            files_indexed += 1;
        }

        // Prune deleted files
        let files_deleted = db.prune_missing_files(&existing_paths).unwrap_or(0);

        // Resolve cross-file callee IDs
        db.resolve_unresolved_callees().unwrap_or(0);

        let stats = db.stats().unwrap_or(GraphStats {
            file_count: 0,
            symbol_count: 0,
            call_count: 0,
            impl_count: 0,
            ref_count: 0,
        });

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        Ok(IndexReport {
            workspace_path: canonical_ws.to_string_lossy().to_string(),
            files_scanned: discovered_files.len(),
            files_indexed,
            files_skipped,
            files_deleted,
            total_symbols: stats.symbol_count,
            total_calls: stats.call_count,
            total_implementations: stats.impl_count,
            total_references: stats.ref_count,
            elapsed_ms: elapsed,
        })
    }

    fn store_file_entities(
        &self,
        db: &mut CodeGraphDb,
        path: &str,
        relative_path: &str,
        language: &str,
        content_hash: &str,
        size_bytes: usize,
        entities: &crate::parser::ParsedFileEntities,
    ) -> Result<()> {
        let conn = db.conn_mut();
        let tx = conn.transaction()?;

        // Delete any existing records for this file (cascade deletes symbols, calls, etc.)
        tx.execute("DELETE FROM files WHERE path = ?1", params![path])?;

        // Insert file
        tx.execute(
            r#"
            INSERT INTO files (path, relative_path, language, content_hash, size_bytes, symbol_count)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6)
            "#,
            params![
                path,
                relative_path,
                language,
                content_hash,
                size_bytes as i64,
                entities.symbols.len() as i64
            ],
        )?;

        let file_id = tx.last_insert_rowid();

        // Symbol name/qual map to id
        let mut symbol_map: HashMap<String, i64> = HashMap::new();

        // Insert symbols
        for sym in &entities.symbols {
            tx.execute(
                r#"
                INSERT INTO symbols (
                    file_id, name, qualified_name, kind, signature, docstring,
                    start_line, start_col, end_line, end_col, parent_id, visibility
                )
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, NULL, ?11)
                "#,
                params![
                    file_id,
                    sym.name,
                    sym.qualified_name,
                    sym.kind,
                    sym.signature,
                    sym.docstring,
                    sym.start_line as i64,
                    sym.start_col as i64,
                    sym.end_line as i64,
                    sym.end_col as i64,
                    sym.visibility,
                ],
            )?;
            let sym_id = tx.last_insert_rowid();
            symbol_map.insert(sym.name.clone(), sym_id);
            symbol_map.insert(sym.qualified_name.clone(), sym_id);
        }

        // Insert calls
        for call in &entities.calls {
            let caller_id = symbol_map
                .get(&call.caller_name)
                .copied()
                .or_else(|| {
                    // Fallback to searching first symbol in the file
                    symbol_map.values().next().copied()
                });

            if let Some(c_id) = caller_id {
                let callee_id = symbol_map.get(&call.callee_name).copied();
                tx.execute(
                    r#"
                    INSERT INTO calls (caller_id, callee_name, callee_id, call_line, call_col)
                    VALUES (?1, ?2, ?3, ?4, ?5)
                    "#,
                    params![
                        c_id,
                        call.callee_name,
                        callee_id,
                        call.line as i64,
                        call.col as i64
                    ],
                )?;
            }
        }

        // Insert implementations
        for imp in &entities.implementations {
            let sym_id = symbol_map
                .get(&imp.symbol_name)
                .copied()
                .or_else(|| {
                    tx.query_row(
                        "SELECT id FROM symbols WHERE name = ?1 LIMIT 1",
                        params![imp.symbol_name],
                        |r| r.get(0),
                    )
                    .ok()
                });

            if let Some(s_id) = sym_id {
                tx.execute(
                    r#"
                    INSERT INTO implementations (symbol_id, interface_name, target_type)
                    VALUES (?1, ?2, ?3)
                    "#,
                    params![s_id, imp.interface_name, imp.target_type],
                )?;
            }
        }

        // Insert references
        for rf in &entities.references {
            let sym_id = symbol_map
                .get(&rf.symbol_name)
                .copied()
                .or_else(|| {
                    tx.query_row(
                        "SELECT id FROM symbols WHERE name = ?1 LIMIT 1",
                        params![rf.symbol_name],
                        |r| r.get(0),
                    )
                    .ok()
                });

            if let Some(s_id) = sym_id {
                tx.execute(
                    r#"
                    INSERT INTO symbol_references (symbol_id, file_id, line, col, ref_kind)
                    VALUES (?1, ?2, ?3, ?4, ?5)
                    "#,
                    params![s_id, file_id, rf.line as i64, rf.col as i64, rf.ref_kind],
                )?;
            }
        }

        tx.commit()?;
        Ok(())
    }
}

fn should_ignore_entry(entry: &walkdir::DirEntry) -> bool {
    let name = entry.file_name().to_string_lossy();
    if entry.file_type().is_dir() {
        matches!(
            name.as_ref(),
            ".git"
                | "target"
                | "node_modules"
                | ".agents"
                | "dist"
                | "build"
                | "__pycache__"
                | ".venv"
                | "venv"
                | ".vs"
                | ".idea"
                | "VSCode-win32-x64"
                | "ov_models"
                | ".gemini"
        )
    } else {
        name.starts_with('.') || name.ends_with(".tmp") || name.ends_with(".log")
    }
}

fn normalize_path(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_indexer_roundtrip() {
        let tmp_dir = std::env::temp_dir().join(format!("test_code_graph_{}", std::process::id()));
        fs::create_dir_all(&tmp_dir).unwrap();

        let rust_file = tmp_dir.join("calc.rs");
        fs::write(
            &rust_file,
            r#"
            pub struct Calculator;
            impl Calculator {
                pub fn add(&self, a: i32, b: i32) -> i32 {
                    self.internal_log();
                    a + b
                }
                fn internal_log(&self) {}
            }
            "#,
        )
        .unwrap();

        let mut db = CodeGraphDb::open_in_memory().unwrap();
        let mut indexer = CodeGraphIndexer::new().unwrap();

        let report = indexer.index_workspace(&mut db, &tmp_dir, true).unwrap();
        assert_eq!(report.files_indexed, 1);
        assert!(report.total_symbols >= 3); // Calculator, add, internal_log
        assert!(report.total_calls >= 1);

        let _ = fs::remove_dir_all(&tmp_dir);
    }
}

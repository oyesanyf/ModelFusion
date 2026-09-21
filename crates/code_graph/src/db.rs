//! SQLite Database Schema & Storage for Semantic Code Graph

use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use std::path::Path;

pub struct CodeGraphDb {
    conn: Connection,
}

impl CodeGraphDb {
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("Failed to create DB directory {:?}", parent))?;
        }
        let conn = Connection::open(path)
            .with_context(|| format!("Failed to open SQLite DB at {:?}", path))?;
        let db = Self { conn };
        db.init_schema()?;
        Ok(db)
    }

    pub fn open_in_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        let db = Self { conn };
        db.init_schema()?;
        Ok(db)
    }

    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    pub fn conn_mut(&mut self) -> &mut Connection {
        &mut self.conn
    }

    fn init_schema(&self) -> Result<()> {
        let _ = self.conn.query_row("PRAGMA journal_mode = WAL;", [], |_| Ok(()));
        let _ = self.conn.query_row("PRAGMA synchronous = NORMAL;", [], |_| Ok(()));
        let _ = self.conn.query_row("PRAGMA cache_size = 10000;", [], |_| Ok(()));
        let _ = self.conn.query_row("PRAGMA foreign_keys = ON;", [], |_| Ok(()));
        let _ = self.conn.query_row("PRAGMA temp_store = MEMORY;", [], |_| Ok(()));

        self.conn.execute_batch(
            r#"
            CREATE TABLE IF NOT EXISTS files (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                path          TEXT UNIQUE NOT NULL,
                relative_path TEXT NOT NULL,
                language      TEXT NOT NULL,
                content_hash  TEXT NOT NULL,
                size_bytes    INTEGER NOT NULL,
                symbol_count  INTEGER DEFAULT 0,
                indexed_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS symbols (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id        INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                name           TEXT NOT NULL,
                qualified_name TEXT NOT NULL,
                kind           TEXT NOT NULL,
                signature      TEXT,
                docstring      TEXT,
                start_line     INTEGER NOT NULL,
                start_col      INTEGER NOT NULL,
                end_line       INTEGER NOT NULL,
                end_col        INTEGER NOT NULL,
                parent_id      INTEGER REFERENCES symbols(id) ON DELETE CASCADE,
                visibility     TEXT DEFAULT 'private'
            );

            CREATE TABLE IF NOT EXISTS calls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_id   INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                callee_name TEXT NOT NULL,
                callee_id   INTEGER REFERENCES symbols(id) ON DELETE SET NULL,
                call_line   INTEGER NOT NULL,
                call_col    INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS implementations (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id      INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                interface_name TEXT NOT NULL,
                target_type    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS symbol_references (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                file_id   INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                line      INTEGER NOT NULL,
                col       INTEGER NOT NULL,
                ref_kind  TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
                name,
                qualified_name,
                docstring,
                signature,
                content='symbols',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
                INSERT INTO symbols_fts(rowid, name, qualified_name, docstring, signature)
                VALUES (new.id, new.name, new.qualified_name, coalesce(new.docstring, ''), coalesce(new.signature, ''));
            END;

            CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
                INSERT INTO symbols_fts(symbols_fts, rowid, name, qualified_name, docstring, signature)
                VALUES('delete', old.id, old.name, old.qualified_name, coalesce(old.docstring, ''), coalesce(old.signature, ''));
            END;

            CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
                INSERT INTO symbols_fts(symbols_fts, rowid, name, qualified_name, docstring, signature)
                VALUES('delete', old.id, old.name, old.qualified_name, coalesce(old.docstring, ''), coalesce(old.signature, ''));
                INSERT INTO symbols_fts(rowid, name, qualified_name, docstring, signature)
                VALUES (new.id, new.name, new.qualified_name, coalesce(new.docstring, ''), coalesce(new.signature, ''));
            END;

            CREATE INDEX IF NOT EXISTS idx_sym_file     ON symbols(file_id);
            CREATE INDEX IF NOT EXISTS idx_sym_name     ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_sym_qual     ON symbols(qualified_name);
            CREATE INDEX IF NOT EXISTS idx_sym_kind     ON symbols(kind);
            CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_id);
            CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_id);
            CREATE INDEX IF NOT EXISTS idx_calls_name   ON calls(callee_name);
            CREATE INDEX IF NOT EXISTS idx_impl_sym     ON implementations(symbol_id);
            CREATE INDEX IF NOT EXISTS idx_impl_iface   ON implementations(interface_name);
            CREATE INDEX IF NOT EXISTS idx_ref_sym      ON symbol_references(symbol_id);
            "#,
        )?;
        Ok(())
    }

    /// Check if a file's content hash matches what's in the DB.
    pub fn get_file_content_hash(&self, path: &str) -> Result<Option<String>> {
        let mut stmt = self
            .conn
            .prepare_cached("SELECT content_hash FROM files WHERE path = ?1")?;
        let mut rows = stmt.query(params![path])?;
        if let Some(row) = rows.next()? {
            let hash: String = row.get(0)?;
            Ok(Some(hash))
        } else {
            Ok(None)
        }
    }

    /// Remove a file and cascade delete all symbols and edges.
    pub fn delete_file(&mut self, path: &str) -> Result<()> {
        let tx = self.conn.transaction()?;
        tx.execute("DELETE FROM files WHERE path = ?1", params![path])?;
        tx.commit()?;
        Ok(())
    }

    /// Prune any files that no longer exist on disk.
    pub fn prune_missing_files(&mut self, existing_paths: &[String]) -> Result<usize> {
        let mut all_db_paths = Vec::new();
        {
            let mut stmt = self.conn.prepare("SELECT id, path FROM files")?;
            let mut rows = stmt.query([])?;
            while let Some(row) = rows.next()? {
                let id: i64 = row.get(0)?;
                let p: String = row.get(1)?;
                all_db_paths.push((id, p));
            }
        }

        let existing_set: std::collections::HashSet<&str> =
            existing_paths.iter().map(|s| s.as_str()).collect();

        let mut deleted = 0;
        let tx = self.conn.transaction()?;
        for (id, path) in all_db_paths {
            if !existing_set.contains(path.as_str()) {
                tx.execute("DELETE FROM files WHERE id = ?1", params![id])?;
                deleted += 1;
            }
        }
        tx.commit()?;
        Ok(deleted)
    }

    /// Resolve unresolved calls (`callee_id IS NULL`) by matching symbol names.
    pub fn resolve_unresolved_callees(&mut self) -> Result<usize> {
        let tx = self.conn.transaction()?;
        let count = tx.execute(
            r#"
            UPDATE calls
            SET callee_id = (
                SELECT s.id FROM symbols s
                WHERE s.name = calls.callee_name
                ORDER BY s.id ASC
                LIMIT 1
            )
            WHERE callee_id IS NULL
            "#,
            [],
        )?;
        tx.commit()?;
        Ok(count)
    }

    /// Return statistics of the knowledge graph.
    pub fn stats(&self) -> Result<GraphStats> {
        let file_count: i64 = self
            .conn
            .query_row("SELECT count(*) FROM files", [], |r| r.get(0))?;
        let symbol_count: i64 = self
            .conn
            .query_row("SELECT count(*) FROM symbols", [], |r| r.get(0))?;
        let call_count: i64 = self
            .conn
            .query_row("SELECT count(*) FROM calls", [], |r| r.get(0))?;
        let impl_count: i64 = self
            .conn
            .query_row("SELECT count(*) FROM implementations", [], |r| r.get(0))?;
        let ref_count: i64 = self
            .conn
            .query_row("SELECT count(*) FROM symbol_references", [], |r| r.get(0))?;

        Ok(GraphStats {
            file_count: file_count as usize,
            symbol_count: symbol_count as usize,
            call_count: call_count as usize,
            impl_count: impl_count as usize,
            ref_count: ref_count as usize,
        })
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GraphStats {
    pub file_count: usize,
    pub symbol_count: usize,
    pub call_count: usize,
    pub impl_count: usize,
    pub ref_count: usize,
}

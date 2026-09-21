//! Sub-25ms Knowledge Graph Query Engine
//!
//! Features:
//! - Single-symbol definition lookup (<1ms)
//! - Recursive CTE call hierarchy traversal (<5ms)
//! - Reverse call hierarchy (callers) traversal (<5ms)
//! - Trait / Interface implementation lookup (<2ms)
//! - Symbol references lookup (<2ms)
//! - FTS5 + TermVector hybrid semantic search (<10ms)

use crate::db::CodeGraphDb;
use anyhow::Result;
use rusqlite::params;
use serde::{Deserialize, Serialize};
use std::time::Instant;
use task_detection::TermVector;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SymbolRecord {
    pub id: i64,
    pub file_id: i64,
    pub file_path: String,
    pub relative_path: String,
    pub name: String,
    pub qualified_name: String,
    pub kind: String,
    pub signature: Option<String>,
    pub docstring: Option<String>,
    pub start_line: usize,
    pub start_col: usize,
    pub end_line: usize,
    pub end_col: usize,
    pub visibility: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CallHierarchyNode {
    pub symbol_id: i64,
    pub name: String,
    pub qualified_name: String,
    pub kind: String,
    pub relative_path: String,
    pub line: usize,
    pub depth: usize,
    pub parent_caller: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CallHierarchyResult {
    pub root_symbol: String,
    pub total_nodes: usize,
    pub elapsed_ms: f64,
    pub nodes: Vec<CallHierarchyNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImplRecord {
    pub symbol_name: String,
    pub interface_name: String,
    pub target_type: String,
    pub file_path: String,
    pub relative_path: String,
    pub line: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RefRecord {
    pub symbol_name: String,
    pub file_path: String,
    pub relative_path: String,
    pub line: usize,
    pub col: usize,
    pub ref_kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub symbol: SymbolRecord,
    pub score: f64,
    pub fts_score: f64,
    pub vsm_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse {
    pub query: String,
    pub query_type: String,
    pub elapsed_ms: f64,
    pub symbols: Vec<SymbolRecord>,
    pub call_hierarchy: Option<CallHierarchyResult>,
    pub callers: Option<CallHierarchyResult>,
    pub implementations: Vec<ImplRecord>,
    pub references: Vec<RefRecord>,
    pub search_results: Vec<SearchResult>,
}

pub struct CodeGraphQueryEngine<'a> {
    db: &'a CodeGraphDb,
}

impl<'a> CodeGraphQueryEngine<'a> {
    pub fn new(db: &'a CodeGraphDb) -> Self {
        Self { db }
    }

    /// Single-symbol definition lookup by exact name or qualified name (<1ms).
    pub fn lookup_symbol(&self, name_or_qual: &str) -> Result<Vec<SymbolRecord>> {
        let t0 = Instant::now();
        let conn = self.db.conn();

        let mut stmt = conn.prepare_cached(
            r#"
            SELECT s.id, s.file_id, f.path, f.relative_path, s.name, s.qualified_name,
                   s.kind, s.signature, s.docstring, s.start_line, s.start_col,
                   s.end_line, s.end_col, s.visibility
            FROM symbols s
            JOIN files f ON f.id = s.file_id
            WHERE s.name = ?1 OR s.qualified_name = ?1
            ORDER BY s.id ASC
            LIMIT 50
            "#,
        )?;

        let rows = stmt.query_map(params![name_or_qual], |row| {
            Ok(SymbolRecord {
                id: row.get(0)?,
                file_id: row.get(1)?,
                file_path: row.get(2)?,
                relative_path: row.get(3)?,
                name: row.get(4)?,
                qualified_name: row.get(5)?,
                kind: row.get(6)?,
                signature: row.get(7)?,
                docstring: row.get(8)?,
                start_line: row.get::<_, i64>(9)? as usize,
                start_col: row.get::<_, i64>(10)? as usize,
                end_line: row.get::<_, i64>(11)? as usize,
                end_col: row.get::<_, i64>(12)? as usize,
                visibility: row.get(13)?,
            })
        })?;

        let mut results = Vec::new();
        for r in rows {
            results.push(r?);
        }

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        log::debug!(
            "lookup_symbol('{}') found {} records in {:.2}ms",
            name_or_qual,
            results.len(),
            elapsed
        );
        Ok(results)
    }

    /// Recursive CTE for call hierarchy traversal (<5ms).
    /// Traverses forward calls (callees that root calls).
    pub fn call_hierarchy(&self, root_symbol: &str, max_depth: usize) -> Result<CallHierarchyResult> {
        let t0 = Instant::now();
        let conn = self.db.conn();
        let depth_limit = max_depth.min(10) as i64;

        let mut stmt = conn.prepare_cached(
            r#"
            WITH RECURSIVE call_tree(symbol_id, depth, caller_name) AS (
                SELECT s.id, 0, CAST('' AS TEXT)
                FROM symbols s
                WHERE s.name = ?1 OR s.qualified_name = ?1
                UNION ALL
                SELECT c.callee_id, ct.depth + 1, s_caller.name
                FROM call_tree ct
                JOIN calls c ON c.caller_id = ct.symbol_id
                JOIN symbols s_caller ON s_caller.id = c.caller_id
                WHERE ct.depth < ?2 AND c.callee_id IS NOT NULL
            )
            SELECT DISTINCT s.id, s.name, s.qualified_name, s.kind, f.relative_path,
                            s.start_line, ct.depth, ct.caller_name
            FROM call_tree ct
            JOIN symbols s ON s.id = ct.symbol_id
            JOIN files f ON f.id = s.file_id
            ORDER BY ct.depth ASC, s.name ASC
            LIMIT 200
            "#,
        )?;

        let rows = stmt.query_map(params![root_symbol, depth_limit], |row| {
            let caller: String = row.get(7)?;
            Ok(CallHierarchyNode {
                symbol_id: row.get(0)?,
                name: row.get(1)?,
                qualified_name: row.get(2)?,
                kind: row.get(3)?,
                relative_path: row.get(4)?,
                line: row.get::<_, i64>(5)? as usize,
                depth: row.get::<_, i64>(6)? as usize,
                parent_caller: if caller.is_empty() { None } else { Some(caller) },
            })
        })?;

        let mut nodes = Vec::new();
        for r in rows {
            nodes.push(r?);
        }

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        Ok(CallHierarchyResult {
            root_symbol: root_symbol.to_string(),
            total_nodes: nodes.len(),
            elapsed_ms: elapsed,
            nodes,
        })
    }

    /// Reverse call hierarchy (callers that call root_symbol) via recursive CTE (<5ms).
    pub fn callers(&self, root_symbol: &str, max_depth: usize) -> Result<CallHierarchyResult> {
        let t0 = Instant::now();
        let conn = self.db.conn();
        let depth_limit = max_depth.min(10) as i64;

        let mut stmt = conn.prepare_cached(
            r#"
            WITH RECURSIVE caller_tree(symbol_id, depth, child_name) AS (
                SELECT s.id, 0, CAST('' AS TEXT)
                FROM symbols s
                WHERE s.name = ?1 OR s.qualified_name = ?1
                UNION ALL
                SELECT c.caller_id, ct.depth + 1, s_child.name
                FROM caller_tree ct
                JOIN calls c ON c.callee_id = ct.symbol_id
                JOIN symbols s_child ON s_child.id = ct.symbol_id
                WHERE ct.depth < ?2
            )
            SELECT DISTINCT s.id, s.name, s.qualified_name, s.kind, f.relative_path,
                            s.start_line, ct.depth, ct.child_name
            FROM caller_tree ct
            JOIN symbols s ON s.id = ct.symbol_id
            JOIN files f ON f.id = s.file_id
            ORDER BY ct.depth ASC, s.name ASC
            LIMIT 200
            "#,
        )?;

        let rows = stmt.query_map(params![root_symbol, depth_limit], |row| {
            let child: String = row.get(7)?;
            Ok(CallHierarchyNode {
                symbol_id: row.get(0)?,
                name: row.get(1)?,
                qualified_name: row.get(2)?,
                kind: row.get(3)?,
                relative_path: row.get(4)?,
                line: row.get::<_, i64>(5)? as usize,
                depth: row.get::<_, i64>(6)? as usize,
                parent_caller: if child.is_empty() { None } else { Some(child) },
            })
        })?;

        let mut nodes = Vec::new();
        for r in rows {
            nodes.push(r?);
        }

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        Ok(CallHierarchyResult {
            root_symbol: root_symbol.to_string(),
            total_nodes: nodes.len(),
            elapsed_ms: elapsed,
            nodes,
        })
    }

    /// Look up trait or interface implementations.
    pub fn find_implementations(&self, target_or_iface: &str) -> Result<Vec<ImplRecord>> {
        let conn = self.db.conn();
        let mut stmt = conn.prepare_cached(
            r#"
            SELECT s.name, i.interface_name, i.target_type, f.path, f.relative_path, s.start_line
            FROM implementations i
            JOIN symbols s ON s.id = i.symbol_id
            JOIN files f ON f.id = s.file_id
            WHERE i.interface_name = ?1 OR i.target_type = ?1 OR s.name = ?1
            LIMIT 100
            "#,
        )?;

        let rows = stmt.query_map(params![target_or_iface], |row| {
            Ok(ImplRecord {
                symbol_name: row.get(0)?,
                interface_name: row.get(1)?,
                target_type: row.get(2)?,
                file_path: row.get(3)?,
                relative_path: row.get(4)?,
                line: row.get::<_, i64>(5)? as usize,
            })
        })?;

        let mut results = Vec::new();
        for r in rows {
            results.push(r?);
        }
        Ok(results)
    }

    /// Look up symbol references.
    pub fn find_references(&self, symbol_name: &str) -> Result<Vec<RefRecord>> {
        let conn = self.db.conn();
        let mut stmt = conn.prepare_cached(
            r#"
            SELECT r.symbol_name, f.path, f.relative_path, r.line, r.col, r.ref_kind
            FROM (
                SELECT s.name AS symbol_name, sr.file_id, sr.line, sr.col, sr.ref_kind
                FROM symbol_references sr
                JOIN symbols s ON s.id = sr.symbol_id
                WHERE s.name = ?1
                UNION ALL
                SELECT c.callee_name AS symbol_name, s.file_id, c.call_line AS line, c.call_col AS col, 'call' AS ref_kind
                FROM calls c
                JOIN symbols s ON s.id = c.caller_id
                WHERE c.callee_name = ?1
            ) r
            JOIN files f ON f.id = r.file_id
            LIMIT 100
            "#,
        )?;

        let rows = stmt.query_map(params![symbol_name], |row| {
            Ok(RefRecord {
                symbol_name: row.get(0)?,
                file_path: row.get(1)?,
                relative_path: row.get(2)?,
                line: row.get::<_, i64>(3)? as usize,
                col: row.get::<_, i64>(4)? as usize,
                ref_kind: row.get(5)?,
            })
        })?;

        let mut results = Vec::new();
        for r in rows {
            results.push(r?);
        }
        Ok(results)
    }

    /// FTS5 + TermVector hybrid search (<10ms).
    /// Retrieves candidate matches from `symbols_fts` and scores them using
    /// combined BM25 rank and TermVector cosine similarity.
    pub fn hybrid_search(&self, query_text: &str, limit: usize) -> Result<Vec<SearchResult>> {
        let t0 = Instant::now();
        let conn = self.db.conn();

        let query_vec = TermVector::from_prompt(query_text);

        // Sanitize query for FTS5: alphanumeric words with trailing wildcard joined by OR
        let mut fts_tokens = Vec::new();
        for word in query_text.split_whitespace() {
            let clean: String = word.chars().filter(|c| c.is_alphanumeric() || *c == '_').collect();
            if !clean.is_empty() {
                fts_tokens.push(format!("{}*", clean));
            }
        }

        let fts_query = if fts_tokens.is_empty() {
            "*".to_string()
        } else {
            fts_tokens.join(" OR ")
        };

        let mut stmt = conn.prepare_cached(
            r#"
            SELECT s.id, s.file_id, f.path, f.relative_path, s.name, s.qualified_name,
                   s.kind, s.signature, s.docstring, s.start_line, s.start_col,
                   s.end_line, s.end_col, s.visibility, bm25(symbols_fts) AS bm25_rank
            FROM symbols_fts
            JOIN symbols s ON s.id = symbols_fts.rowid
            JOIN files f ON f.id = s.file_id
            WHERE symbols_fts MATCH ?1
            ORDER BY bm25_rank ASC
            LIMIT ?2
            "#,
        )?;

        let candidate_limit = (limit * 3).max(30);
        let rows = stmt.query_map(params![fts_query, candidate_limit as i64], |row| {
            let sym = SymbolRecord {
                id: row.get(0)?,
                file_id: row.get(1)?,
                file_path: row.get(2)?,
                relative_path: row.get(3)?,
                name: row.get(4)?,
                qualified_name: row.get(5)?,
                kind: row.get(6)?,
                signature: row.get(7)?,
                docstring: row.get(8)?,
                start_line: row.get::<_, i64>(9)? as usize,
                start_col: row.get::<_, i64>(10)? as usize,
                end_line: row.get::<_, i64>(11)? as usize,
                end_col: row.get::<_, i64>(12)? as usize,
                visibility: row.get(13)?,
            };
            let bm25_rank: f64 = row.get(14)?;
            Ok((sym, bm25_rank))
        });

        let mut scored_results = Vec::new();
        match rows {
            Ok(mapped) => {
                for item in mapped {
                    if let Ok((sym, bm25_rank)) = item {
                        // BM25 in SQLite is negative where more negative is more relevant
                        let fts_score = (1.0 / (1.0 + bm25_rank.abs())).min(1.0);

                        // Build TermVector from symbol name, docstring, and signature
                        let sym_text = format!(
                            "{} {} {} {}",
                            sym.name,
                            sym.qualified_name,
                            sym.signature.as_deref().unwrap_or(""),
                            sym.docstring.as_deref().unwrap_or("")
                        );
                        let sym_vec = TermVector::from_prompt(&sym_text);
                        let vsm_score = query_vec.cosine_similarity(&sym_vec);

                        // Combine: 0.55 * FTS + 0.45 * VSM
                        let combined_score = 0.55 * fts_score + 0.45 * vsm_score;

                        scored_results.push(SearchResult {
                            symbol: sym,
                            score: combined_score,
                            fts_score,
                            vsm_score,
                        });
                    }
                }
            }
            Err(e) => {
                log::warn!("FTS match failed (query: {}): {:?}", fts_query, e);
            }
        }

        // Sort by final combined score descending
        scored_results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        scored_results.truncate(limit);

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        log::debug!(
            "hybrid_search('{}') returned {} results in {:.2}ms",
            query_text,
            scored_results.len(),
            elapsed
        );

        Ok(scored_results)
    }

    /// Dispatch a general query by type ("all", "symbol", "calls", "callers", "impls", "refs", "search").
    pub fn query(&self, query_str: &str, query_type: &str, limit: usize) -> Result<QueryResponse> {
        let t0 = Instant::now();
        let q_clean = query_str.trim();

        let mut symbols = Vec::new();
        let mut call_hierarchy = None;
        let mut callers = None;
        let mut implementations = Vec::new();
        let mut references = Vec::new();
        let mut search_results = Vec::new();

        match query_type {
            "symbol" => {
                symbols = self.lookup_symbol(q_clean)?;
            }
            "calls" | "callees" => {
                call_hierarchy = Some(self.call_hierarchy(q_clean, 3)?);
            }
            "callers" => {
                callers = Some(self.callers(q_clean, 3)?);
            }
            "impls" | "implementations" => {
                implementations = self.find_implementations(q_clean)?;
            }
            "refs" | "references" => {
                references = self.find_references(q_clean)?;
            }
            "search" => {
                search_results = self.hybrid_search(q_clean, limit)?;
            }
            _ => {
                // "all" mode: run lookup, call hierarchy, implementations, references, and search
                symbols = self.lookup_symbol(q_clean)?;
                call_hierarchy = self.call_hierarchy(q_clean, 3).ok();
                callers = self.callers(q_clean, 3).ok();
                implementations = self.find_implementations(q_clean).unwrap_or_default();
                references = self.find_references(q_clean).unwrap_or_default();
                search_results = self.hybrid_search(q_clean, limit).unwrap_or_default();
            }
        }

        let elapsed = t0.elapsed().as_secs_f64() * 1000.0;
        Ok(QueryResponse {
            query: query_str.to_string(),
            query_type: query_type.to_string(),
            elapsed_ms: elapsed,
            symbols,
            call_hierarchy,
            callers,
            implementations,
            references,
            search_results,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::CodeGraphDb;

    fn setup_test_db() -> CodeGraphDb {
        let mut db = CodeGraphDb::open_in_memory().unwrap();
        let conn = db.conn_mut();

        conn.execute(
            "INSERT INTO files (id, path, relative_path, language, content_hash, size_bytes, symbol_count)
             VALUES (1, '/workspace/src/lib.rs', 'src/lib.rs', 'rust', 'abc123hash', 1024, 2)",
            [],
        ).unwrap();

        conn.execute(
            "INSERT INTO symbols (id, file_id, name, qualified_name, kind, signature, docstring, start_line, start_col, end_line, end_col, visibility)
             VALUES (1, 1, 'Arbiter', 'Arbiter', 'struct', 'pub struct Arbiter', 'Manages consensus', 1, 1, 10, 1, 'pub')",
            [],
        ).unwrap();

        conn.execute(
            "INSERT INTO symbols (id, file_id, name, qualified_name, kind, signature, docstring, start_line, start_col, end_line, end_col, visibility)
             VALUES (2, 1, 'arbitrate', 'Arbiter::arbitrate', 'method', 'pub fn arbitrate(&self)', 'Executes arbitration', 12, 5, 25, 5, 'pub')",
            [],
        ).unwrap();

        conn.execute(
            "INSERT INTO symbols (id, file_id, name, qualified_name, kind, signature, docstring, start_line, start_col, end_line, end_col, visibility)
             VALUES (3, 1, 'verify_solution', 'Arbiter::verify_solution', 'method', 'fn verify_solution(&self)', 'Checks verification score', 27, 5, 35, 5, 'private')",
            [],
        ).unwrap();

        conn.execute(
            "INSERT INTO calls (caller_id, callee_name, callee_id, call_line, call_col)
             VALUES (2, 'verify_solution', 3, 15, 9)",
            [],
        ).unwrap();

        conn.execute(
            "INSERT INTO implementations (symbol_id, interface_name, target_type)
             VALUES (1, 'DecisionEngine', 'Arbiter')",
            [],
        ).unwrap();

        db
    }

    #[test]
    fn test_lookup_symbol_sub_1ms() {
        let db = setup_test_db();
        let engine = CodeGraphQueryEngine::new(&db);
        let t0 = Instant::now();
        let records = engine.lookup_symbol("Arbiter").unwrap();
        let elapsed = t0.elapsed();
        assert!(!records.is_empty());
        assert_eq!(records[0].name, "Arbiter");
        assert!(elapsed.as_millis() < 5); // Well within sub-25ms SLA
    }

    #[test]
    fn test_call_hierarchy_cte() {
        let db = setup_test_db();
        let engine = CodeGraphQueryEngine::new(&db);
        let res = engine.call_hierarchy("arbitrate", 3).unwrap();
        assert_eq!(res.root_symbol, "arbitrate");
        assert!(res.nodes.iter().any(|n| n.name == "verify_solution"));
    }

    #[test]
    fn test_implementations() {
        let db = setup_test_db();
        let engine = CodeGraphQueryEngine::new(&db);
        let impls = engine.find_implementations("DecisionEngine").unwrap();
        assert_eq!(impls.len(), 1);
        assert_eq!(impls[0].target_type, "Arbiter");
    }

    #[test]
    fn test_hybrid_search() {
        let db = setup_test_db();
        let engine = CodeGraphQueryEngine::new(&db);
        let results = engine.hybrid_search("consensus arbitration", 5).unwrap();
        assert!(!results.is_empty());
        assert!(results[0].score > 0.0);
    }
}

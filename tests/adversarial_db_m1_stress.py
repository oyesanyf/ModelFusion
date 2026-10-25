#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for ModelFusion Database Migration & Persistence (Milestone 1).
Targets:
- Partial column schema migration (e.g. only trending_score exists)
- Repeated and concurrent migration idempotency
- Extreme values: trending_score (1e-15, 1.0, 0.0, -0.5), bandit_pulls (i64::MAX), bandit_reward (large/negative)
- Feed source conflict merging (trending + following_activity -> trending+following, and subsequent overwrites)
"""

import sys
import os
import sqlite3
import tempfile
import threading
import time
import math

# SQL Statements from crates/db/src/schema.rs
CREATE_LEGACY_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS models (
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
)
"""

MIGRATION_COLUMNS = [
    ("trending_score", "ALTER TABLE models ADD COLUMN trending_score REAL DEFAULT 0.0"),
    ("feed_source", "ALTER TABLE models ADD COLUMN feed_source TEXT DEFAULT 'standard_hub'"),
    ("bandit_pulls", "ALTER TABLE models ADD COLUMN bandit_pulls INTEGER DEFAULT 0"),
    ("bandit_reward", "ALTER TABLE models ADD COLUMN bandit_reward REAL DEFAULT 0.0"),
]

UPSERT_SQL = """
INSERT INTO models (
    model_id, author, pipeline_tag, tags, description,
    downloads, likes, decision_score, capability_score,
    efficiency_score, popularity_score, model_type, library_name,
    last_modified, license, task_keywords, architecture, size_mb, language,
    trending_score, feed_source, bandit_pulls, bandit_reward,
    updated_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
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
        WHEN (models.feed_source = 'trending' AND excluded.feed_source = 'following_activity')
          OR (models.feed_source = 'following_activity' AND excluded.feed_source = 'trending')
          OR excluded.feed_source = 'trending+following'
        THEN 'trending+following'
        WHEN excluded.feed_source IS NOT NULL AND excluded.feed_source != '' AND excluded.feed_source != 'standard_hub'
        THEN excluded.feed_source
        ELSE models.feed_source
    END,
    bandit_pulls     = CASE WHEN excluded.bandit_pulls > 0 THEN excluded.bandit_pulls ELSE models.bandit_pulls END,
    bandit_reward    = CASE WHEN excluded.bandit_reward > 0.0 THEN excluded.bandit_reward ELSE models.bandit_reward END,
    updated_at       = datetime('now')
"""

FIXED_UPSERT_SQL = """
INSERT INTO models (
    model_id, author, pipeline_tag, tags, description,
    downloads, likes, decision_score, capability_score,
    efficiency_score, popularity_score, model_type, library_name,
    last_modified, license, task_keywords, architecture, size_mb, language,
    trending_score, feed_source, bandit_pulls, bandit_reward,
    updated_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
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
    updated_at       = datetime('now')
"""

BANDIT_PULL_SQL = """
UPDATE models
SET bandit_pulls = bandit_pulls + 1,
    bandit_reward = bandit_reward + ?,
    updated_at = datetime('now')
WHERE model_id = ?
"""

def rust_migrate_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'models'")
    if not cur.fetchone():
        return
    cur.execute("PRAGMA table_info(models)")
    existing_cols = {row[1].lower() for row in cur.fetchall()}
    for col_name, alter_stmt in MIGRATION_COLUMNS:
        if col_name.lower() not in existing_cols:
            cur.execute(alter_stmt)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trending_score ON models(trending_score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_feed_source ON models(feed_source)")
    conn.commit()


def run_tests():
    total_tests = 0
    passed_tests = 0
    failures = []
    anomalies = []

    def report(name, success, detail=""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if success:
            passed_tests += 1
            print(f"  [PASS] {name} {detail}")
        else:
            failures.append((name, detail))
            print(f"  [FAIL] {name}: {detail}")

    def note_anomaly(name, detail):
        anomalies.append((name, detail))
        print(f"  [ANOMALY / OBSERVATION] {name}: {detail}")

    print("======================================================================")
    print(" SUITE 1: PARTIAL COLUMN MIGRATION TEST SUITE")
    print("======================================================================")

    # 1.1 Database with ONLY trending_score present
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_1 = f.name
    try:
        conn = sqlite3.connect(db_path_1)
        cur = conn.cursor()
        cur.execute(CREATE_LEGACY_MODELS_TABLE)
        cur.execute("ALTER TABLE models ADD COLUMN trending_score REAL DEFAULT 0.0")
        conn.commit()

        # Check only trending_score exists
        cur.execute("PRAGMA table_info(models)")
        cols = {r[1].lower() for r in cur.fetchall()}
        report("1.1 Pre-check partial table", "trending_score" in cols and "feed_source" not in cols)

        # Run migration
        rust_migrate_schema(conn)

        cur.execute("PRAGMA table_info(models)")
        new_cols = {r[1].lower() for r in cur.fetchall()}
        expected = {"trending_score", "feed_source", "bandit_pulls", "bandit_reward"}
        report("1.1 Migration adds remaining 3 columns", expected.issubset(new_cols), f"Cols: {new_cols}")
        conn.close()
    finally:
        if os.path.exists(db_path_1):
            os.remove(db_path_1)

    # 1.2 Database with ONLY feed_source and bandit_pulls
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_2 = f.name
    try:
        conn = sqlite3.connect(db_path_2)
        cur = conn.cursor()
        cur.execute(CREATE_LEGACY_MODELS_TABLE)
        cur.execute("ALTER TABLE models ADD COLUMN feed_source TEXT DEFAULT 'standard_hub'")
        cur.execute("ALTER TABLE models ADD COLUMN bandit_pulls INTEGER DEFAULT 0")
        conn.commit()

        rust_migrate_schema(conn)
        cur.execute("PRAGMA table_info(models)")
        cols = {r[1].lower() for r in cur.fetchall()}
        report("1.2 Migration on subset [feed_source, bandit_pulls]", {"trending_score", "bandit_reward"}.issubset(cols))
        conn.close()
    finally:
        if os.path.exists(db_path_2):
            os.remove(db_path_2)

    # 1.3 Database with NO models table (empty DB)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_3 = f.name
    try:
        conn = sqlite3.connect(db_path_3)
        rust_migrate_schema(conn)
        report("1.3 Migration on empty DB (no models table)", True, "Handled gracefully")
        conn.close()
    finally:
        if os.path.exists(db_path_3):
            os.remove(db_path_3)

    # 1.4 Pre-existing data preservation
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_4 = f.name
    try:
        conn = sqlite3.connect(db_path_4)
        cur = conn.cursor()
        cur.execute(CREATE_LEGACY_MODELS_TABLE)
        cur.execute("""
            INSERT INTO models (model_id, author, pipeline_tag, downloads, decision_score)
            VALUES ('legacy/model-1', 'legacy-author', 'text-generation', 12345, 8.5)
        """)
        conn.commit()

        rust_migrate_schema(conn)

        cur.execute("SELECT model_id, downloads, trending_score, feed_source, bandit_pulls, bandit_reward FROM models WHERE model_id = 'legacy/model-1'")
        row = cur.fetchone()
        preserved = (
            row[0] == 'legacy/model-1' and
            row[1] == 12345 and
            abs(row[2] - 0.0) < 1e-6 and
            row[3] == 'standard_hub' and
            row[4] == 0 and
            abs(row[5] - 0.0) < 1e-6
        )
        report("1.4 Pre-existing data preserved with column defaults", preserved, f"Row: {row}")
        conn.close()
    finally:
        if os.path.exists(db_path_4):
            os.remove(db_path_4)

    print("\n======================================================================")
    print(" SUITE 2: IDEMPOTENCY & CONCURRENCY STRESS SUITE")
    print("======================================================================")

    # 2.1 Repeated migration 50 times sequentially
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_rep = f.name
    try:
        conn = sqlite3.connect(db_path_rep)
        cur = conn.cursor()
        cur.execute(CREATE_LEGACY_MODELS_TABLE)
        conn.commit()

        seq_ok = True
        for i in range(50):
            try:
                rust_migrate_schema(conn)
            except Exception as e:
                seq_ok = False
                break
        report("2.1 Sequential 50x migration idempotency", seq_ok)
        conn.close()
    finally:
        if os.path.exists(db_path_rep):
            os.remove(db_path_rep)

    # 2.2 Concurrent migration simulation across threads
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_conc = f.name
    try:
        conn = sqlite3.connect(db_path_conc)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute(CREATE_LEGACY_MODELS_TABLE)
        conn.commit()
        conn.close()

        thread_errors = []
        def worker():
            try:
                t_conn = sqlite3.connect(db_path_conc, timeout=30.0)
                t_conn.execute("PRAGMA busy_timeout = 30000")
                rust_migrate_schema(t_conn)
                t_conn.close()
            except Exception as e:
                thread_errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if len(thread_errors) == 0:
            report("2.2 Concurrent migration (8 parallel threads)", True, "0 errors with WAL/busy_timeout")
        else:
            note_anomaly("2.2 Concurrent migration race", f"{len(thread_errors)} thread(s) encountered collision: {thread_errors[:2]}")
            report("2.2 Concurrent migration", len(thread_errors) == 0, f"Errors: {thread_errors}")
    finally:
        time.sleep(0.1)
        for _ in range(5):
            try:
                if os.path.exists(db_path_conc):
                    os.remove(db_path_conc)
                break
            except Exception:
                time.sleep(0.1)

    print("\n======================================================================")
    print(" SUITE 3: EXTREME VALUES & BOUNDARY CONDITIONS")
    print("======================================================================")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_val = f.name
    try:
        conn = sqlite3.connect(db_path_val)
        conn.execute(CREATE_LEGACY_MODELS_TABLE)
        rust_migrate_schema(conn)

        def upsert_model(model_id, trending_score, feed_source, bandit_pulls, bandit_reward):
            conn.execute(UPSERT_SQL, (
                model_id, "author", "text-generation", "[]", "desc",
                100, 10, 8.0, 8.0, 8.0, 8.0, "type", "lib",
                "2026-10-24", "mit", "[]", "arch", 100.0, "en",
                trending_score, feed_source, bandit_pulls, bandit_reward
            ))
            conn.commit()

        # 3.1 trending_score = 1e-15
        upsert_model("model/tiny-float", 1e-15, "trending", 0, 0.0)
        cur = conn.cursor()
        cur.execute("SELECT trending_score FROM models WHERE model_id = 'model/tiny-float'")
        val = cur.fetchone()[0]
        report("3.1 Smallest positive float trending_score = 1e-15", abs(val - 1e-15) < 1e-25, f"Stored: {val}")

        # 3.2 trending_score = 1.0
        upsert_model("model/max-score", 1.0, "trending", 0, 0.0)
        cur.execute("SELECT trending_score FROM models WHERE model_id = 'model/max-score'")
        report("3.2 Maximum velocity trending_score = 1.0", cur.fetchone()[0] == 1.0)

        # 3.3 Large integer bandit_pulls = 9223372036854775807 (i64::MAX)
        I64_MAX = 9223372036854775807
        upsert_model("model/large-bandit", 0.5, "trending", I64_MAX, 100.0)
        cur.execute("SELECT bandit_pulls, typeof(bandit_pulls) FROM models WHERE model_id = 'model/large-bandit'")
        b_pulls, col_type = cur.fetchone()
        report("3.3 Large integer bandit_pulls = i64::MAX", b_pulls == I64_MAX and col_type == 'integer', f"Val: {b_pulls}, Type: {col_type}")

        # 3.4 Simulating record_bandit_pull on i64::MAX
        cur.execute(BANDIT_PULL_SQL, (1.0, "model/large-bandit"))
        conn.commit()
        cur.execute("SELECT bandit_pulls, typeof(bandit_pulls) FROM models WHERE model_id = 'model/large-bandit'")
        overflown_pulls, overflown_type = cur.fetchone()
        if overflown_type == 'real':
            note_anomaly("3.4 i64::MAX + 1 SQLite integer overflow",
                         f"SQLite promoted 9223372036854775807 + 1 to REAL: {overflown_pulls} ({overflown_type}). "
                         f"In Rusqlite, row.get::<_, i64> will fail with FromSql(InvalidType) on overflow.")
        report("3.4 Integer boundary behavior documented", True)

        # 3.5 Negative values & zero update semantics
        upsert_model("model/score-drop", 0.85, "trending", 10, 5.0)
        # Attempt update with 0.0 (e.g. trending dropped to 0)
        upsert_model("model/score-drop", 0.0, "trending", 0, 0.0)
        cur.execute("SELECT trending_score, bandit_pulls, bandit_reward FROM models WHERE model_id = 'model/score-drop'")
        r_drop = cur.fetchone()
        # In CASE WHEN excluded.trending_score > 0.0: 0.0 does NOT overwrite 0.85!
        note_anomaly("3.5 Trending score 0.0 update semantics",
                     f"When excluded.trending_score is 0.0, CASE statement preserves old score: {r_drop[0]}. "
                     f"This protects against empty scrapes wiping trending score, but prevents explicit decay to 0.0.")
        report("3.5 Score retention when updating with 0.0", r_drop[0] == 0.85)

        # Update with negative value -0.5
        upsert_model("model/score-drop", -0.5, "trending", -5, -2.0)
        cur.execute("SELECT trending_score, bandit_pulls, bandit_reward FROM models WHERE model_id = 'model/score-drop'")
        r_neg = cur.fetchone()
        report("3.6 Negative values rejected on conflict update", r_neg[0] == 0.85 and r_neg[1] == 10 and r_neg[2] == 5.0)

        conn.close()
    finally:
        if os.path.exists(db_path_val):
            os.remove(db_path_val)

    print("\n======================================================================")
    print(" SUITE 4: FEED SOURCE CONFLICT MERGING")
    print("======================================================================")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_feed = f.name
    try:
        conn = sqlite3.connect(db_path_feed)
        conn.execute(CREATE_LEGACY_MODELS_TABLE)
        rust_migrate_schema(conn)

        def upsert_feed(model_id, feed_source):
            conn.execute(UPSERT_SQL, (
                model_id, "author", "text-generation", "[]", "desc",
                100, 10, 8.0, 8.0, 8.0, 8.0, "type", "lib",
                "2026-10-24", "mit", "[]", "arch", 100.0, "en",
                0.9, feed_source, 1, 1.0
            ))
            conn.commit()

        cur = conn.cursor()

        # 4.1 trending + following_activity -> trending+following
        upsert_feed("model/merge-1", "trending")
        upsert_feed("model/merge-1", "following_activity")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/merge-1'")
        res_41 = cur.fetchone()[0]
        report("4.1 trending + following_activity -> trending+following", res_41 == "trending+following", f"Got: {res_41}")

        # 4.2 following_activity + trending -> trending+following
        upsert_feed("model/merge-2", "following_activity")
        upsert_feed("model/merge-2", "trending")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/merge-2'")
        res_42 = cur.fetchone()[0]
        report("4.2 following_activity + trending -> trending+following", res_42 == "trending+following", f"Got: {res_42}")

        # 4.3 trending+following + trending+following -> trending+following
        upsert_feed("model/merge-3", "trending+following")
        upsert_feed("model/merge-3", "trending+following")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/merge-3'")
        res_43 = cur.fetchone()[0]
        report("4.3 trending+following + trending+following -> trending+following", res_43 == "trending+following", f"Got: {res_43}")

        # 4.4 ADVERSARIAL CASE: What happens when model is trending+following, and next pass is 'trending'?
        # In SQL:
        # WHEN (models.feed_source = 'trending' AND excluded.feed_source = 'following_activity')
        #   OR (models.feed_source = 'following_activity' AND excluded.feed_source = 'trending')
        #   OR excluded.feed_source = 'trending+following'
        # THEN 'trending+following'
        # WHEN excluded.feed_source IS NOT NULL AND excluded.feed_source != '' AND excluded.feed_source != 'standard_hub'
        # THEN excluded.feed_source
        upsert_feed("model/demotion-test", "trending+following")
        upsert_feed("model/demotion-test", "trending")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/demotion-test'")
        res_44 = cur.fetchone()[0]
        if res_44 == "trending":
            note_anomaly("4.4 Feed Source Demotion Flaw",
                         "CRITICAL FINDING: Model with 'trending+following' was overwritten with 'trending'! "
                         "Reason: SQL CASE expression checks if models.feed_source='trending', but does NOT check "
                         "if models.feed_source='trending+following' when incoming feed_source is 'trending' or 'following_activity'.")
            report("4.4 Preserves 'trending+following' on incoming 'trending'", False, f"Expected 'trending+following', got '{res_44}'")
        else:
            report("4.4 Preserves 'trending+following' on incoming 'trending'", res_44 == "trending+following", f"Got: {res_44}")

        # 4.5 ADVERSARIAL CASE: trending+following + following_activity
        upsert_feed("model/demotion-test-2", "trending+following")
        upsert_feed("model/demotion-test-2", "following_activity")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/demotion-test-2'")
        res_45 = cur.fetchone()[0]
        if res_45 == "following_activity":
            note_anomaly("4.5 Feed Source Demotion Flaw (following_activity)",
                         "Model with 'trending+following' was overwritten with 'following_activity'!")
            report("4.5 Preserves 'trending+following' on incoming 'following_activity'", False, f"Expected 'trending+following', got '{res_45}'")
        else:
            report("4.5 Preserves 'trending+following' on incoming 'following_activity'", res_45 == "trending+following", f"Got: {res_45}")

        # 4.6 trending+following + standard_hub
        upsert_feed("model/demotion-test-3", "trending+following")
        upsert_feed("model/demotion-test-3", "standard_hub")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/demotion-test-3'")
        res_46 = cur.fetchone()[0]
        report("4.6 Preserves 'trending+following' on incoming 'standard_hub'", res_46 == "trending+following", f"Got: {res_46}")

        # 4B. VERIFICATION OF PROPOSED FIX:
        def upsert_feed_fixed(model_id, feed_source):
            conn.execute(FIXED_UPSERT_SQL, (
                model_id, "author", "text-generation", "[]", "desc",
                100, 10, 8.0, 8.0, 8.0, 8.0, "type", "lib",
                "2026-10-24", "mit", "[]", "arch", 100.0, "en",
                0.9, feed_source, 1, 1.0
            ))
            conn.commit()

        upsert_feed_fixed("model/fixed-test-1", "trending+following")
        upsert_feed_fixed("model/fixed-test-1", "trending")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/fixed-test-1'")
        fixed_res_1 = cur.fetchone()[0]
        report("4B.1 Fixed SQL: trending+following + trending -> trending+following", fixed_res_1 == "trending+following", f"Got: {fixed_res_1}")

        upsert_feed_fixed("model/fixed-test-2", "trending+following")
        upsert_feed_fixed("model/fixed-test-2", "following_activity")
        cur.execute("SELECT feed_source FROM models WHERE model_id = 'model/fixed-test-2'")
        fixed_res_2 = cur.fetchone()[0]
        report("4B.2 Fixed SQL: trending+following + following_activity -> trending+following", fixed_res_2 == "trending+following", f"Got: {fixed_res_2}")

        conn.close()
    finally:
        if os.path.exists(db_path_feed):
            os.remove(db_path_feed)

    print("\n======================================================================")
    print(" SUITE 5: QUERY PROJECTIONS & INDEXES PERFORMANCE")
    print("======================================================================")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path_query = f.name
    try:
        conn = sqlite3.connect(db_path_query)
        conn.execute(CREATE_LEGACY_MODELS_TABLE)
        rust_migrate_schema(conn)

        cur = conn.cursor()
        cur.execute("PRAGMA index_list(models)")
        indexes = {r[1] for r in cur.fetchall()}
        report("5.1 idx_trending_score exists", "idx_trending_score" in indexes)
        report("5.2 idx_feed_source exists", "idx_feed_source" in indexes)

        # Check index usage in EXPLAIN QUERY PLAN
        cur.execute("EXPLAIN QUERY PLAN SELECT model_id FROM models WHERE feed_source = 'trending'")
        plan = cur.fetchall()
        uses_index = any("idx_feed_source" in str(p) for p in plan)
        report("5.3 Query on feed_source uses index", uses_index, f"Plan: {plan}")

        cur.execute("EXPLAIN QUERY PLAN SELECT model_id FROM models ORDER BY trending_score DESC LIMIT 10")
        plan2 = cur.fetchall()
        uses_t_index = any("idx_trending_score" in str(p) for p in plan2)
        report("5.4 Query on trending_score uses index", uses_t_index, f"Plan: {plan2}")

        conn.close()
    finally:
        if os.path.exists(db_path_query):
            os.remove(db_path_query)

    print("\n======================================================================")
    print(f" SUMMARY: {passed_tests}/{total_tests} tests passed, {len(failures)} failures, {len(anomalies)} anomalies.")
    print("======================================================================")

    return failures, anomalies

if __name__ == "__main__":
    failures, anomalies = run_tests()
    if failures:
        sys.exit(1)
    sys.exit(0)

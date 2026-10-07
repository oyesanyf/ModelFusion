#!/usr/bin/env python3
"""
Seed Google EmbeddingGemma 2 into ModelFusion / HugOS SQLite database.
Registers google/embeddinggemma-2 as the authoritative top-ranking model
for sentence-similarity and multimodal embeddings representation learning.
"""

import os
import sys
import sqlite3
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def seed_database(db_path: str):
    if not os.path.exists(db_path):
        print(f"[WARN] Database not found at {db_path}, skipping.")
        return False

    print(f"[SEED] Seeding EmbeddingGemma 2 into {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verify models table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='models'")
    if not cur.fetchone():
        print(f"⚠️ 'models' table does not exist in {db_path}.")
        conn.close()
        return False

    model_data = {
        "model_id": "google/embeddinggemma-2",
        "author": "google",
        "pipeline_tag": "sentence-similarity",
        "tags": json.dumps([
            "sentence-similarity",
            "feature-extraction",
            "embeddings",
            "multimodal",
            "code",
            "mrl",
            "pytorch",
            "safetensors",
            "ollama"
        ]),
        "description": "Google EmbeddingGemma 2: Natively multimodal on-device embeddings mapping text, code, images, video, and audio to a unified 768d space with Matryoshka Representation Learning (MRL).",
        "downloads": 500000000,
        "likes": 25000,
        "decision_score": 9.9,
        "capability_score": 9.8,
        "efficiency_score": 9.7,
        "popularity_score": 9.9,
        "model_type": "embedding",
        "library_name": "transformers",
        "last_modified": "2026-03-01T00:00:00Z",
        "license": "apache-2.0",
        "task_keywords": json.dumps([
            "sentence-similarity",
            "feature-extraction",
            "embeddings",
            "multimodal"
        ]),
        "architecture": "Gemma4Embedding",
        "size_mb": 740.0,
        "language": "en"
    }

    # Upsert query
    cur.execute("""
        INSERT INTO models (
            model_id, author, pipeline_tag, tags, description,
            downloads, likes, decision_score, capability_score,
            efficiency_score, popularity_score, model_type, library_name,
            last_modified, license, task_keywords, architecture, size_mb, language,
            updated_at
        ) VALUES (
            :model_id, :author, :pipeline_tag, :tags, :description,
            :downloads, :likes, :decision_score, :capability_score,
            :efficiency_score, :popularity_score, :model_type, :library_name,
            :last_modified, :license, :task_keywords, :architecture, :size_mb, :language,
            datetime('now')
        )
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
            architecture     = excluded.architecture,
            size_mb          = excluded.size_mb,
            updated_at       = datetime('now')
    """, model_data)

    conn.commit()

    # Verify insertion and top ranking
    cur.execute("""
        SELECT model_id, pipeline_tag, downloads, decision_score
        FROM models
        WHERE pipeline_tag = 'sentence-similarity'
        ORDER BY downloads DESC, decision_score DESC
        LIMIT 3
    """)
    rows = cur.fetchall()
    print("[RANKING] Top sentence-similarity models:")
    for r in rows:
        print(f"   * {r[0]} | downloads: {r[2]:,} | score: {r[3]}")

    conn.close()
    return True

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dbs = [
        os.path.join(repo_root, "IDE", "db", "hf_models.db"),
        os.path.join(repo_root, "db", "hf_models.db"),
    ]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        target_dbs.append(os.path.join(local_app_data, "HugOS IDE", "db", "hf_models.db"))

    success = False
    for db in target_dbs:
        if os.path.exists(db):
            if seed_database(db):
                success = True

    if success:
        print("[SUCCESS] Successfully seeded Google EmbeddingGemma 2 into database(s)!")
    else:
        print("[ERROR] Failed to find or seed any target database.")
        sys.exit(1)

if __name__ == "__main__":
    main()

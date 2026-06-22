"""
cache_ov_hub.py — Download all OpenVINO Hub pre-converted models from the database.

Usage:
    python src/scripts/cache_ov_hub.py [ov_model_dir] [db_path] [max_size_gb]

- Reads all models with library_name='openvino' from the DB
- Downloads each one using huggingface_hub.snapshot_download (INT4 pre-converted)
- Skips already-cached models
- Reports a summary at the end
"""

import sys
import os
import sqlite3

# Force UTF-8 output on Windows to prevent emoji encoding errors in cp1252 consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7 fallback

def find_db(db_path_arg: str | None) -> str:
    """Locate the hf_models.db file."""
    if db_path_arg and os.path.isfile(db_path_arg):
        return db_path_arg
    # Walk up from cwd looking for db/hf_models.db
    cwd = os.getcwd()
    for _ in range(5):
        candidate = os.path.join(cwd, "db", "hf_models.db")
        if os.path.isfile(candidate):
            return candidate
        cwd = os.path.dirname(cwd)
    return "db/hf_models.db"


def is_cached(model_id: str, ov_model_dir: str) -> str | None:
    """Return local path if model is already cached, else None."""
    safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
    if os.path.isdir(ov_model_dir):
        for entry in sorted(os.listdir(ov_model_dir)):
            entry_lower = entry.lower()
            if entry_lower.startswith(safe_name) or safe_name in entry_lower:
                full = os.path.join(ov_model_dir, entry)
                if (os.path.isfile(os.path.join(full, "openvino_model.xml"))
                        or os.path.isfile(os.path.join(full, "model.xml"))):
                    return full
    return None


def download_model(model_id: str, ov_model_dir: str) -> tuple[bool, str]:
    """
    Download model from HuggingFace Hub to ov_model_dir.
    Returns (success, message).
    """
    try:
        from huggingface_hub import snapshot_download
        safe_name = model_id.replace("/", "--")
        local_dir = os.path.join(ov_model_dir, safe_name)
        os.makedirs(ov_model_dir, exist_ok=True)
        path = snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*", "*.ot"],
        )
        # Verify it has OV model files
        has_xml = os.path.isfile(os.path.join(path, "openvino_model.xml"))
        if has_xml:
            return True, path
        else:
            return False, f"Downloaded but no openvino_model.xml found in {path}"
    except Exception as e:
        return False, str(e)


def main():
    ov_model_dir = sys.argv[1] if len(sys.argv) > 1 else "ov_models"
    db_path_arg  = sys.argv[2] if len(sys.argv) > 2 else None
    max_size_gb  = float(sys.argv[3]) if len(sys.argv) > 3 else 999.0  # no limit by default

    db_path = find_db(db_path_arg)
    print(f"[OV-CACHE] Database: {db_path}")
    print(f"[OV-CACHE] Output directory: {ov_model_dir}")
    print(f"[OV-CACHE] Max size filter: {max_size_gb} GB per model")
    print()

    if not os.path.isfile(db_path):
        print(f"[OV-CACHE] ❌ Database not found at {db_path}")
        print(f"[OV-CACHE]    Run: cli.exe --update  to populate the database first.")
        sys.exit(1)

    # Query DB for all openvino pre-converted models
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT model_id, size_mb
        FROM models
        WHERE library_name = 'openvino'
        ORDER BY size_mb ASC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("[OV-CACHE] ❌ No OpenVINO Hub models found in database.")
        print("[OV-CACHE]    Run: cli.exe --update  to sync them first.")
        sys.exit(1)

    # Filter by size
    filtered = [(mid, sz) for mid, sz in rows if sz / 1024.0 <= max_size_gb]
    skipped_size = len(rows) - len(filtered)

    print(f"[OV-CACHE] Found {len(rows)} OV Hub models in DB.")
    if skipped_size:
        print(f"[OV-CACHE] Skipping {skipped_size} models exceeding {max_size_gb} GB limit.")
    print(f"[OV-CACHE] Will download {len(filtered)} models to '{ov_model_dir}/'")
    print(f"[OV-CACHE] Estimated total disk: ~{sum(sz for _, sz in filtered) / 1024:.1f} GB")
    print()

    success_count = 0
    skip_count    = 0
    fail_count    = 0

    for i, (model_id, size_mb) in enumerate(filtered, 1):
        size_gb = size_mb / 1024.0
        prefix = f"[{i}/{len(filtered)}] {model_id} (~{size_gb:.1f} GB)"

        cached = is_cached(model_id, ov_model_dir)
        if cached:
            print(f"  ⏭️  {prefix} — already cached at {cached}")
            skip_count += 1
            continue

        print(f"  ⬇️  {prefix} — downloading...", flush=True)
        ok, msg = download_model(model_id, ov_model_dir)
        if ok:
            print(f"  ✅ Saved to {msg}")
            success_count += 1
        else:
            print(f"  ❌ Failed: {msg}")
            fail_count += 1

    print()
    print("=" * 50)
    print("📊 Cache Summary")
    print("=" * 50)
    print(f"  ✅ Downloaded : {success_count}")
    print(f"  ⏭️  Already cached: {skip_count}")
    print(f"  ❌ Failed    : {fail_count}")
    print(f"  📦 Total     : {len(filtered)}")
    print()

    # List what's now in ov_models/
    if os.path.isdir(ov_model_dir):
        entries = [e for e in os.listdir(ov_model_dir)
                   if os.path.isfile(os.path.join(ov_model_dir, e, "openvino_model.xml"))]
        print(f"[OV-CACHE] 📂 {len(entries)} models ready in '{ov_model_dir}/':")
        for e in sorted(entries):
            print(f"    • {e}")


if __name__ == "__main__":
    main()

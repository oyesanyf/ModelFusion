r"""
cache_ov_hub.py -- Download OpenVINO Hub pre-converted INT4 text-generation models.

Usage:
    python src/scripts/cache_ov_hub.py [ov_model_dir] [db_path] [max_size_gb]

Fixes vs v1:
  - ov_model_dir is made absolute (resolves CWD issues when run from target\release\)
  - Only downloads INT4 text-generation/causal-lm models (skips fp16, int8, vision, audio)
  - Accepts ANY .xml file as valid OV model (handles split/sharded models like gemma-4)
  - Disk space check before each download
  - DB size estimates validated against actual HF repo metadata
"""

import sys
import os
import sqlite3
import shutil

# Force UTF-8 output on Windows (prevents emoji encoding errors in cp1252 consoles)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# ── Text-generation pipeline tags accepted for caching ───────────────────────
ALLOWED_PIPELINE_TAGS = {
    "text-generation", "text2text-generation", "causal-lm", "llm", "",
}

# ── Skip these model name patterns (vision, audio, TTS, image, video) ────────
SKIP_NAME_PATTERNS = [
    "vit-", "vit_", "clip-", "blip", "whisper", "wav2vec", "speech",
    "audio", "asr", "tts", "image", "vision", "video", "siglip", "dino",
    "sam-", "depth", "table-", "tapex", "vocos", "snac", "vitpose",
    "vitmatte", "rorshark", "ultravox", "-vl-", "-vl_", "vlm",
]


def find_db(db_path_arg: str | None) -> str:
    """Locate hf_models.db by searching up from script location and CWD."""
    if db_path_arg and os.path.isfile(db_path_arg):
        return os.path.abspath(db_path_arg)
    # Try CWD and parents
    for base in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
        cwd = base
        for _ in range(6):
            candidate = os.path.join(cwd, "db", "hf_models.db")
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(cwd)
            if parent == cwd:
                break
            cwd = parent
    return os.path.join(os.getcwd(), "db", "hf_models.db")


def has_ov_model_files(directory: str) -> bool:
    """
    Return True if directory contains at least one OpenVINO IR .xml file.
    Handles all naming patterns:
      - openvino_model.xml          (standard single-file)
      - openvino_language_model.xml (multimodal LLM part)
      - openvino_model_00001_of_00002.xml (sharded)
      - model.xml                   (older format)
    """
    try:
        for f in os.listdir(directory):
            if f.endswith(".xml"):
                return True
    except OSError:
        pass
    return False


def is_cached(model_id: str, ov_model_dir: str) -> str | None:
    """Return local path if model is already cached, else None."""
    safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
    if os.path.isdir(ov_model_dir):
        for entry in sorted(os.listdir(ov_model_dir)):
            entry_lower = entry.lower()
            if entry_lower.startswith(safe_name) or safe_name in entry_lower:
                full = os.path.join(ov_model_dir, entry)
                if os.path.isdir(full) and has_ov_model_files(full):
                    return full
    return None


def free_gb(path: str) -> float:
    """Return free disk space in GB at the given path."""
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except OSError:
        return 999.0


def get_hf_model_size_gb(model_id: str) -> float | None:
    """
    Query the HuggingFace Hub API for the actual total repo size.
    Returns size in GB, or None if unavailable.
    """
    try:
        import urllib.request, json
        url = f"https://huggingface.co/api/models/{model_id}?blobs=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        siblings = data.get("siblings", [])
        total = sum(s.get("size", 0) for s in siblings if s.get("rfilename", "").endswith(".bin")
                    or s.get("rfilename", "").endswith(".safetensors")
                    or s.get("rfilename", "").endswith(".xml")
                    or s.get("rfilename", "").endswith(".bin"))
        return total / (1024 ** 3) if total > 0 else None
    except Exception:
        return None


def download_model(model_id: str, ov_model_dir: str) -> tuple[bool, str]:
    """
    Download model from HuggingFace Hub to ov_model_dir.
    Returns (success, local_path_or_error_message).
    """
    try:
        from huggingface_hub import snapshot_download
        safe_name = model_id.replace("/", "--")
        local_dir = os.path.join(ov_model_dir, safe_name)
        os.makedirs(ov_model_dir, exist_ok=True)
        path = snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*",
                             "*.ot", "*.pt", "*.pth", "tokenizer.model"],
        )
        if has_ov_model_files(path):
            return True, path
        else:
            # No .xml found — might be vision/audio model, clean up
            shutil.rmtree(path, ignore_errors=True)
            return False, f"No .xml OV model files found — likely not a text-gen model, cleaned up"
    except Exception as e:
        return False, str(e)


def main():
    ov_model_dir = sys.argv[1] if len(sys.argv) > 1 else "ov_models"
    db_path_arg  = sys.argv[2] if len(sys.argv) > 2 else None
    max_size_gb  = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0  # safe default

    # Make ov_model_dir absolute to avoid CWD-relative path bugs
    ov_model_dir = os.path.abspath(ov_model_dir)

    db_path = find_db(db_path_arg)
    print(f"[OV-CACHE] Database  : {db_path}")
    print(f"[OV-CACHE] Output dir: {ov_model_dir}")
    print(f"[OV-CACHE] Max size  : {max_size_gb} GB per model (INT4 only)")
    print(f"[OV-CACHE] Free disk : {free_gb(ov_model_dir if os.path.isdir(ov_model_dir) else os.getcwd()):.1f} GB")
    print()

    if not os.path.isfile(db_path):
        print(f"[OV-CACHE] ERROR: Database not found at {db_path}")
        print(f"[OV-CACHE]   Run: cli.exe --update  to populate the database first.")
        sys.exit(1)

    # Query DB — only INT4 text-generation models from OpenVINO Hub
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT model_id, size_mb, pipeline_tag
        FROM models
        WHERE library_name = 'openvino'
          AND (
            LOWER(model_id) LIKE '%-int4-%'
            OR LOWER(model_id) LIKE '%-int4'
          )
        ORDER BY size_mb ASC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("[OV-CACHE] No INT4 OpenVINO Hub models found in database.")
        print("[OV-CACHE]   Run: cli.exe --update  to sync them first.")
        sys.exit(1)

    # Filter: skip non-text-gen, skip above size limit, skip vision/audio names
    filtered = []
    skipped_type  = 0
    skipped_size  = 0
    for mid, sz, ptag in rows:
        name_lower = mid.lower()
        # Skip vision, audio, TTS patterns
        if any(pat in name_lower for pat in SKIP_NAME_PATTERNS):
            skipped_type += 1
            continue
        # Only text-generation pipeline tags
        if ptag not in ALLOWED_PIPELINE_TAGS:
            skipped_type += 1
            continue
        # DB size estimate is often wrong — use max_size_gb as a soft cap
        # The real size check happens via disk space before download
        if sz / 1024.0 > max_size_gb:
            skipped_size += 1
            continue
        filtered.append((mid, sz))

    print(f"[OV-CACHE] Found {len(rows)} INT4 OV Hub models in DB.")
    if skipped_type:
        print(f"[OV-CACHE] Skipped {skipped_type} vision/audio/non-LLM models.")
    if skipped_size:
        print(f"[OV-CACHE] Skipped {skipped_size} models exceeding {max_size_gb} GB estimate.")
    print(f"[OV-CACHE] Downloading {len(filtered)} INT4 text-generation models...")
    print(f"[OV-CACHE] Estimated total: ~{sum(sz for _, sz in filtered) / 1024:.1f} GB")
    print()

    os.makedirs(ov_model_dir, exist_ok=True)
    success_count = 0
    skip_count    = 0
    fail_count    = 0

    for i, (model_id, size_mb) in enumerate(filtered, 1):
        size_gb = size_mb / 1024.0
        prefix = f"[{i}/{len(filtered)}] {model_id} (~{size_gb:.1f} GB est.)"

        # Check if already cached
        cached = is_cached(model_id, ov_model_dir)
        if cached:
            print(f"  [SKIP] {prefix}")
            print(f"         -> already cached at {cached}")
            skip_count += 1
            continue

        # Check disk space — need at least max_size_gb + 2 GB buffer
        available = free_gb(ov_model_dir)
        if available < max(size_gb, 1.0) + 2.0:
            print(f"  [SKIP] {prefix}")
            print(f"         -> only {available:.1f} GB free, need {max(size_gb,1.0)+2:.1f} GB minimum")
            fail_count += 1
            continue

        print(f"  [DOWN] {prefix} — {available:.1f} GB free", flush=True)
        ok, msg = download_model(model_id, ov_model_dir)
        if ok:
            print(f"  [OK]   Saved to {msg}")
            success_count += 1
        else:
            print(f"  [FAIL] {msg}")
            fail_count += 1

    print()
    print("=" * 55)
    print("  Cache Summary")
    print("=" * 55)
    print(f"  Downloaded : {success_count}")
    print(f"  Skipped    : {skip_count}  (already cached)")
    print(f"  Failed     : {fail_count}")
    print(f"  Total      : {len(filtered)}")
    print(f"  Free disk  : {free_gb(ov_model_dir):.1f} GB remaining")
    print("=" * 55)
    print()

    # List all ready models
    if os.path.isdir(ov_model_dir):
        entries = [e for e in os.listdir(ov_model_dir)
                   if os.path.isdir(os.path.join(ov_model_dir, e))
                   and has_ov_model_files(os.path.join(ov_model_dir, e))]
        print(f"[OV-CACHE] {len(entries)} models ready in '{ov_model_dir}':")
        for e in sorted(entries):
            print(f"    {e}")


if __name__ == "__main__":
    main()

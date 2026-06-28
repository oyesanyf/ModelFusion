import sys
import os
import json
import glob
import logging
from datetime import datetime, timezone

# Suppress noisy library logs
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)

VALID_WEIGHT_FORMATS = ("fp16", "int8", "int4")


def derive_safe_name(model_id, weight_format):
    """Derive a filesystem-safe directory name from a HuggingFace model ID.

    Takes the part after '/' (or the full string if no '/'), lowercases it,
    and appends the weight format suffix.

    Examples:
        'Qwen/Qwen2.5-1.5B-Instruct' + 'int8' → 'qwen2.5-1.5b-instruct-int8'
        'mistralai/Mistral-7B-v0.1' + 'int4'  → 'mistral-7b-v0.1-int4'
    """
    base = model_id.split("/")[-1]
    return f"{base.lower()}-{weight_format}"


def output_already_exists(output_path):
    """Check if the output directory already contains a converted model."""
    if not os.path.isdir(output_path):
        return False
    # Check for the standard optimum-intel output file
    if os.path.exists(os.path.join(output_path, "openvino_model.xml")):
        return True
    # Fallback: check for any .xml file (covers alternate naming)
    if glob.glob(os.path.join(output_path, "*.xml")):
        return True
    return False


def export_model(model_id, weight_format, output_path):
    """Export a HuggingFace model to OpenVINO IR format via optimum-cli subprocess.

    Uses subprocess to avoid segfaults on Python 3.14+ where importing
    optimum.intel C extensions crashes the process.
    """
    import subprocess

    os.makedirs(output_path, exist_ok=True)

    print(f"[PREPARE-OV] Exporting {model_id} → {weight_format} ...", file=sys.stderr)
    print(f"[PREPARE-OV] Output directory: {output_path}", file=sys.stderr)

    if weight_format == "int8":
        print("[PREPARE-OV] Quantising to INT8 during export", file=sys.stderr)
    elif weight_format == "int4":
        print("[PREPARE-OV] Quantising to INT4 during export", file=sys.stderr)
    else:
        print("[PREPARE-OV] Exporting in FP16 (no quantisation)", file=sys.stderr)

    # Use optimum.exporters.openvino as a subprocess for safety
    export_cmd = [
        sys.executable, "-m", "optimum.exporters.openvino",
        "--model", model_id,
        "--weight-format", weight_format,
        "--trust-remote-code",
        output_path
    ]

    print("[PREPARE-OV] Loading and converting model (this may take a while) ...", file=sys.stderr)
    result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=1200)

    if result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else "Unknown error"
        # Check if it's an import/compatibility issue
        if "ModuleNotFoundError" in err_msg or "ImportError" in err_msg:
            print(
                "ERROR: optimum-intel is not installed or not compatible.\n"
                "Install it with:  pip install \"optimum-intel[openvino]\"",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: Export failed:\n{err_msg[:500]}", file=sys.stderr)
        raise RuntimeError(f"optimum-cli export returned code {result.returncode}")

    if result.stderr:
        # Print export progress messages
        for line in result.stderr.strip().split("\n")[-5:]:
            print(f"  {line}", file=sys.stderr)

    # Save tokenizer separately (optimum exporter may already include it)
    tokenizer_json = os.path.join(output_path, "tokenizer.json")
    if not os.path.exists(tokenizer_json):
        print("[PREPARE-OV] Saving tokenizer ...", file=sys.stderr)
        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            tokenizer.save_pretrained(output_path)
        except Exception as e:
            print(f"[PREPARE-OV] Warning: tokenizer save failed ({e})", file=sys.stderr)


def save_metadata(output_path, model_id, weight_format):
    """Write a metadata.json file into the output directory."""
    metadata = {
        "model_id": model_id,
        "weight_format": weight_format,
        "export_date": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
    }
    metadata_path = os.path.join(output_path, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[PREPARE-OV] Metadata written to {metadata_path}", file=sys.stderr)


def main():
    # ── CLI argument parsing ────────────────────────────────────────────
    if len(sys.argv) < 3:
        print(
            "ERROR: Missing arguments.\n"
            "Usage: python prepare_model_openvino.py <model_id> <output_dir> [weight_format]\n"
            "\n"
            "  model_id      HuggingFace model ID  (e.g. 'Qwen/Qwen2.5-1.5B-Instruct')\n"
            "  output_dir    Base directory for storing models (e.g. 'ov_models')\n"
            "  weight_format One of: fp16, int8, int4  (default: int8)",
            file=sys.stderr,
        )
        sys.exit(1)

    model_id = sys.argv[1]
    output_dir = sys.argv[2]
    weight_format = sys.argv[3] if len(sys.argv) > 3 else "int8"

    if weight_format not in VALID_WEIGHT_FORMATS:
        print(
            f"ERROR: Invalid weight_format '{weight_format}'. "
            f"Must be one of: {', '.join(VALID_WEIGHT_FORMATS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Derive output path ──────────────────────────────────────────────
    safe_name = derive_safe_name(model_id, weight_format)
    output_path = os.path.join(output_dir, safe_name)

    print(f"[PREPARE-OV] Model:         {model_id}", file=sys.stderr)
    print(f"[PREPARE-OV] Weight format: {weight_format}", file=sys.stderr)
    print(f"[PREPARE-OV] Target path:   {output_path}", file=sys.stderr)

    # ── Skip if already converted ───────────────────────────────────────
    if output_already_exists(output_path):
        print(
            f"[PREPARE-OV] SKIP: Model already exists at {output_path}",
            file=sys.stderr,
        )
        print(output_path)
        sys.exit(0)

    # ── Export ──────────────────────────────────────────────────────────
    try:
        export_model(model_id, weight_format, output_path)
    except Exception as e:
        print(f"ERROR: Model export failed: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Metadata ────────────────────────────────────────────────────────
    try:
        save_metadata(output_path, model_id, weight_format)
    except Exception as e:
        print(f"ERROR: Failed to write metadata: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Success – emit the output path on stdout ────────────────────────
    print(f"[PREPARE-OV] ✅ Export complete!", file=sys.stderr)
    print(output_path)


if __name__ == "__main__":
    main()

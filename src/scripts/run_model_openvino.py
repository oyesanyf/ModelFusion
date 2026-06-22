"""
OpenVINO inference script for ModelFusion.

Correct flow (per OpenVINO docs):
  1. Check local OV cache  → LLMPipeline(local_path)
  2. Try OpenVINO Hub      → snapshot_download pre-converted model → LLMPipeline(local_path)
  3. Manual conversion     → download HF model → ov.convert_model() → save → LLMPipeline(local_path)
  4. Classic OV loop       → compiled_model token-by-token (slowest, no KV cache)

NOTE: openvino_genai.LLMPipeline ALWAYS needs a LOCAL DIRECTORY PATH, never a raw HF model ID.
"""

import sys
import os
import logging
import platform

current_os = platform.system()

# ── Python version compatibility note ───────────────────────────────────────
_py_ver = sys.version_info
_on_py314_plus = _py_ver >= (3, 13)
if _on_py314_plus:
    print(
        f"[OPENVINO] ℹ️  Python {_py_ver.major}.{_py_ver.minor} detected. "
        f"optimum-intel is skipped (requires 3.8–3.12). "
        f"Using direct ov.convert_model() + openvino_genai path.",
        file=sys.stderr
    )

# Platform-specific environment settings
if current_os == "Linux":
    os.environ["OV_CPU_BIND_TYPE"] = "NUMA"
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
elif current_os == "Windows":
    os.environ["OV_CPU_BIND_TYPE"] = "THREAD"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
else:
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)


# ── OpenVINO Hub pre-converted model registry ────────────────────────────────
# Maps common HuggingFace model IDs to their pre-converted OpenVINO Hub versions.
# These can be loaded directly with LLMPipeline without any conversion step.
# Source: https://huggingface.co/OpenVINO
# Verified real model IDs from the OpenVINO HuggingFace organisation.
# Run: python -c "from huggingface_hub import list_models; [print(m.id) for m in list_models(author='OpenVINO',limit=200)]"
OV_HUB_REGISTRY = {
    # Qwen 2.5 (confirmed)
    "Qwen/Qwen2.5-1.5B-Instruct":            "OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov",
    "Qwen/Qwen2.5-7B-Instruct":              "OpenVINO/Qwen2.5-7B-Instruct-int4-ov",
    "Qwen/Qwen2.5-14B-Instruct":             "OpenVINO/Qwen2.5-14B-Instruct-int4-ov",
    # Qwen 2 (confirmed)
    "Qwen/Qwen2-0.5B-Instruct":              "OpenVINO/Qwen2-0.5B-Instruct-int4-ov",
    "Qwen/Qwen2-1.5B-Instruct":              "OpenVINO/Qwen2-1.5B-Instruct-int4-ov",
    "Qwen/Qwen2-7B-Instruct":                "OpenVINO/Qwen2-7B-Instruct-int4-ov",
    # Phi (confirmed)
    "microsoft/phi-2":                        "OpenVINO/phi-2-int4-ov",
    "microsoft/Phi-3-mini-4k-instruct":       "OpenVINO/Phi-3-mini-4k-instruct-int4-ov",
    "microsoft/Phi-3-mini-128k-instruct":     "OpenVINO/Phi-3-mini-128k-instruct-int4-ov",
    "microsoft/Phi-3-medium-4k-instruct":     "OpenVINO/Phi-3-medium-4k-instruct-int4-ov",
    # Mistral (confirmed)
    "mistralai/Mistral-7B-Instruct-v0.1":     "OpenVINO/mistral-7b-instruct-v0.1-int4-ov",
    "mistralai/Mistral-7B-Instruct-v0.2":     "OpenVINO/Mistral-7B-Instruct-v0.2-int4-ov",
    # TinyLlama (confirmed)
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0":    "OpenVINO/TinyLlama-1.1B-Chat-v1.0-int4-ov",
    # Gemma (confirmed)
    "google/gemma-2b-it":                     "OpenVINO/gemma-2b-it-int4-ov",
    "google/gemma-7b-it":                     "OpenVINO/gemma-7b-it-int4-ov",
    "google/gemma-2-9b-it":                   "OpenVINO/gemma-2-9b-it-int4-ov",
    # Qwen 3 (confirmed)
    "Qwen/Qwen3-8B":                          "OpenVINO/Qwen3-8B-int4-ov",
}


def find_ov_hub_model(model_id: str) -> str | None:
    """Return the OpenVINO Hub repo ID for a given HF model ID, or None."""
    return OV_HUB_REGISTRY.get(model_id)


def find_cached_model(model_id: str, ov_model_dir: str = "ov_models") -> str | None:
    """Check if a pre-converted OpenVINO IR model exists locally."""
    safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
    if os.path.isdir(ov_model_dir):
        for entry in sorted(os.listdir(ov_model_dir)):
            if entry.startswith(safe_name) or entry.startswith(model_id.replace("/", "--")):
                model_path = os.path.join(ov_model_dir, entry)
                if (os.path.isfile(os.path.join(model_path, "openvino_model.xml"))
                        or os.path.isfile(os.path.join(model_path, "model.xml"))):
                    return model_path
    # Also check HuggingFace hub cache (snapshot_download stores here)
    hf_cache = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    return None


def download_ov_hub_model(ov_repo_id: str, ov_model_dir: str) -> str | None:
    """
    Download a pre-converted OpenVINO model from HuggingFace Hub.
    Returns the local directory path, or None on failure.
    """
    try:
        from huggingface_hub import snapshot_download
        safe_name = ov_repo_id.replace("/", "--")
        local_dir = os.path.join(ov_model_dir, safe_name)
        if os.path.isdir(local_dir) and os.path.isfile(os.path.join(local_dir, "openvino_model.xml")):
            print(f"[OPENVINO] ✅ Using cached OV Hub model at {local_dir}", file=sys.stderr)
            return local_dir
        print(f"[OPENVINO] ⬇️  Downloading pre-converted OV model: {ov_repo_id}", file=sys.stderr)
        print(f"[OPENVINO]    This is INT4 quantized (~1–4 GB) — much smaller than the original.", file=sys.stderr)
        os.makedirs(ov_model_dir, exist_ok=True)
        path = snapshot_download(repo_id=ov_repo_id, local_dir=local_dir)
        print(f"[OPENVINO] ✅ Downloaded to {path}", file=sys.stderr)
        return path
    except Exception as e:
        print(f"[OPENVINO] ⚠️  OV Hub download failed ({e})", file=sys.stderr)
        return None


def convert_hf_to_openvino(model_id: str, ov_model_dir: str, weight_format: str = "int8") -> str | None:
    """
    Download a HuggingFace model and convert it to OpenVINO IR format.
    Uses ov.convert_model() as per OpenVINO docs — works on Python 3.14.
    Returns the local OV model directory path, or None on failure.
    """
    try:
        import openvino as ov
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
        output_path = os.path.join(ov_model_dir, f"{safe_name}-ov-{weight_format}")
        ov_xml = os.path.join(output_path, "openvino_model.xml")

        if os.path.isfile(ov_xml):
            print(f"[OPENVINO] ✅ Using cached converted model at {output_path}", file=sys.stderr)
            return output_path

        os.makedirs(output_path, exist_ok=True)
        print(f"[OPENVINO] ⬇️  Downloading {model_id} from HuggingFace...", file=sys.stderr)

        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        tokenizer.save_pretrained(output_path)

        print(f"[OPENVINO] 🔄 Loading PyTorch model for conversion...", file=sys.stderr)
        pt_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,  # float32 for reliable OV conversion
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        pt_model.eval()

        print(f"[OPENVINO] 🔄 Converting to OpenVINO IR with ov.convert_model()...", file=sys.stderr)

        # Wrap to return only logits (OV can't trace DynamicCache)
        class LogitsWrapper(torch.nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m
            def forward(self, input_ids, attention_mask):
                with torch.no_grad():
                    return self.m(input_ids=input_ids, attention_mask=attention_mask, use_cache=False).logits

        wrapper = LogitsWrapper(pt_model)
        wrapper.eval()

        dummy_ids = torch.ones((1, 8), dtype=torch.long)
        dummy_mask = torch.ones((1, 8), dtype=torch.long)

        try:
            ov_model = ov.convert_model(wrapper, example_input=(dummy_ids, dummy_mask))
        except Exception as e1:
            print(f"[OPENVINO] ⚠️  convert_model failed ({e1}), trying ONNX export path...", file=sys.stderr)
            import tempfile
            onnx_path = os.path.join(output_path, "_temp.onnx")
            torch.onnx.export(
                wrapper, (dummy_ids, dummy_mask), onnx_path,
                input_names=["input_ids", "attention_mask"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "seq"},
                    "attention_mask": {0: "batch", 1: "seq"},
                    "logits": {0: "batch", 1: "seq"},
                },
                opset_version=17,
            )
            core = ov.Core()
            ov_model = core.read_model(onnx_path)
            try:
                os.remove(onnx_path)
            except OSError:
                pass

        ov.save_model(ov_model, ov_xml)
        print(f"[OPENVINO] ✅ Model saved to {output_path}", file=sys.stderr)

        del pt_model, wrapper
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc; gc.collect()

        return output_path
    except Exception as e:
        print(f"[OPENVINO] ❌ Conversion failed: {e}", file=sys.stderr)
        return None


def infer_with_genai(local_model_path: str, prompt: str, max_tokens: int, temperature: float) -> bool:
    """
    Run inference using openvino_genai.LLMPipeline on a local OV model directory.
    Returns True on success, False on failure.
    """
    try:
        import openvino_genai as ov_genai
        print(f"[OPENVINO-GENAI] Loading from {local_model_path}", file=sys.stderr)
        pipe = ov_genai.LLMPipeline(local_model_path, "CPU")
        config = ov_genai.GenerationConfig()
        config.max_new_tokens = max_tokens
        config.do_sample = temperature > 0.0
        if temperature > 0.0:
            config.temperature = temperature
        print(f"[OPENVINO-GENAI] Generating (max_tokens={max_tokens}, temp={temperature})...", file=sys.stderr)
        output = pipe.generate(prompt, config)
        print(output)
        return True
    except ImportError:
        print("[OPENVINO-GENAI] openvino_genai not installed.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[OPENVINO-GENAI] Failed: {e}", file=sys.stderr)
        return False


def infer_classic_ov(local_model_path: str, prompt: str, max_tokens: int, temperature: float) -> bool:
    """
    Classic OpenVINO compiled_model token-by-token inference loop.
    Works for models converted with ov.convert_model() without KV cache.
    """
    try:
        import openvino as ov
        import numpy as np
        from transformers import AutoTokenizer

        xml_path = (os.path.join(local_model_path, "openvino_model.xml")
                    if os.path.isfile(os.path.join(local_model_path, "openvino_model.xml"))
                    else os.path.join(local_model_path, "model.xml"))

        if not os.path.isfile(xml_path):
            print(f"[OPENVINO] ❌ No model.xml found in {local_model_path}", file=sys.stderr)
            return False

        tokenizer = AutoTokenizer.from_pretrained(local_model_path, trust_remote_code=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id

        core = ov.Core()
        import multiprocessing
        n_threads = max(1, multiprocessing.cpu_count() - 1)
        compiled = core.compile_model(xml_path, "CPU", {
            "PERFORMANCE_HINT": "LATENCY",
            "INFERENCE_NUM_THREADS": str(n_threads),
        })

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=512)
        generated = inputs["input_ids"].numpy().tolist()[0]
        mask = inputs["attention_mask"].numpy().tolist()[0]

        print(f"[OPENVINO] Generating (classic loop, max_tokens={max_tokens})...", file=sys.stderr)
        for _ in range(max_tokens):
            res = compiled({
                "input_ids": np.array([generated], dtype=np.int64),
                "attention_mask": np.array([mask], dtype=np.int64),
            })
            logits = res[0][0, -1, :]
            if temperature > 0.0:
                logits = logits / temperature
                probs = np.exp(logits - np.max(logits))
                probs /= probs.sum()
                next_id = int(np.random.choice(len(probs), p=probs))
            else:
                next_id = int(np.argmax(logits))
            if next_id == tokenizer.eos_token_id:
                break
            generated.append(next_id)
            mask.append(1)

        new_tokens = generated[inputs["input_ids"].shape[1]:]
        print(tokenizer.decode(new_tokens, skip_special_tokens=True))
        return True
    except Exception as e:
        print(f"[OPENVINO] Classic inference failed: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: run_model_openvino.py <model_id> <prompt> [max_tokens] [temperature] [ov_model_dir] [weight_format]",
              file=sys.stderr)
        sys.exit(1)

    model_id    = sys.argv[1]
    prompt      = sys.argv[2]
    max_tokens  = int(sys.argv[3])   if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
    ov_model_dir = sys.argv[5]       if len(sys.argv) > 5 else "ov_models"
    weight_format = sys.argv[6]      if len(sys.argv) > 6 else "int4"

    print(f"[OPENVINO] Model: {model_id}", file=sys.stderr)
    print(f"[OPENVINO] Prompt length: {len(prompt)} chars", file=sys.stderr)

    # ── Step 1: Check local OV cache ─────────────────────────────────────────
    local_path = find_cached_model(model_id, ov_model_dir)
    if local_path:
        print(f"[OPENVINO] ✅ Found cached OV model at: {local_path}", file=sys.stderr)
        if infer_with_genai(local_path, prompt, max_tokens, temperature):
            return
        if infer_classic_ov(local_path, prompt, max_tokens, temperature):
            return
        print("[OPENVINO] Cached model inference failed, re-converting...", file=sys.stderr)

    # ── Step 2: Try OpenVINO Hub pre-converted model ──────────────────────────
    ov_hub_id = find_ov_hub_model(model_id)
    if ov_hub_id:
        print(f"[OPENVINO] 🔍 Found pre-converted OV Hub model: {ov_hub_id}", file=sys.stderr)
        local_path = download_ov_hub_model(ov_hub_id, ov_model_dir)
        if local_path:
            if infer_with_genai(local_path, prompt, max_tokens, temperature):
                return
            if infer_classic_ov(local_path, prompt, max_tokens, temperature):
                return
    else:
        print(f"[OPENVINO] ℹ️  No pre-converted OV Hub version for '{model_id}'. Will convert manually.", file=sys.stderr)

    # ── Step 3: Try optimum-intel export (Python < 3.13 only) ────────────────
    if not _on_py314_plus:
        import subprocess as _sp
        probe = _sp.run(
            [sys.executable, "-c", "from optimum.intel import OVModelForCausalLM; print('OK')"],
            capture_output=True, text=True, timeout=60
        )
        if probe.returncode == 0 and "OK" in probe.stdout:
            safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
            output_path = os.path.join(ov_model_dir, f"{safe_name}-{weight_format}")
            if not os.path.isfile(os.path.join(output_path, "openvino_model.xml")):
                print(f"[OPENVINO] 🔄 Converting via optimum-cli...", file=sys.stderr)
                os.makedirs(ov_model_dir, exist_ok=True)
                result = _sp.run([
                    sys.executable, "-m", "optimum.exporters.openvino",
                    "--model", model_id,
                    "--weight-format", weight_format,
                    "--trust-remote-code",
                    output_path
                ], capture_output=True, text=True, timeout=900)
                if result.returncode != 0:
                    print(f"[OPENVINO] optimum-cli failed: {result.stderr[:300]}", file=sys.stderr)
                else:
                    print(f"[OPENVINO] ✅ Converted to {output_path}", file=sys.stderr)
            if os.path.isfile(os.path.join(output_path, "openvino_model.xml")):
                if infer_with_genai(output_path, prompt, max_tokens, temperature):
                    return

    # ── Step 4: Manual torch → OV conversion (works on Python 3.14) ──────────
    print(f"[OPENVINO] 🔄 Starting manual torch→OV conversion for {model_id}...", file=sys.stderr)
    local_path = convert_hf_to_openvino(model_id, ov_model_dir, weight_format)
    if local_path:
        # For manually converted models, try classic loop (genai needs KV-cache-aware models)
        if infer_classic_ov(local_path, prompt, max_tokens, temperature):
            return
        if infer_with_genai(local_path, prompt, max_tokens, temperature):
            return

    print(f"ERROR: All OpenVINO inference paths failed for model '{model_id}'.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

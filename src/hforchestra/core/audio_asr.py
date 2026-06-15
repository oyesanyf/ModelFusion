from typing import Optional
import os

def run_asr(file_path: str, language: Optional[str] = None) -> str:
    """Run a simple automatic speech recognition pipeline on the given audio file.

    Uses transformers pipeline('automatic-speech-recognition'). If transformers is not
    available or model loading fails, returns an error string.
    """
    try:
        from transformers import pipeline
    except Exception as e:
        return f"[ERROR] transformers not available: {e}"

    try:
    print(f"🎤 Initializing speech recognition for: {os.path.basename(file_path)}", flush=True)

    try:
        # Preferred models (best?fallback). Can be overridden via env.
        env_model = os.getenv("ASR_MODEL_ID")
        env_rev = os.getenv("ASR_MODEL_REVISION")
        preferred = [
            (env_model, env_rev) if env_model else (None, None),
            ("openai/whisper-base", None),
            ("openai/whisper-small", None), # Corrected order: base is faster/better tradeoff often
            ("facebook/wav2vec2-large-960h-lv60-self", None),
            ("facebook/wav2vec2-base-960h", "22aad52"),
        ]

        asr = None
        last_err = None
        # Device selection with override via env HFORCH_DEVICE
        device_arg = None
        forced_device = os.getenv("HFORCH_DEVICE")
        try:
            import torch
            if forced_device:
                device_arg = 0 if forced_device.lower() in ("cuda", "gpu") else -1
            else:
                if torch.cuda.is_available():
                    device_arg = 0
            if device_arg == 0:
                print("🚀 Using GPU for acceleration", flush=True)
            else:
                print("ℹ️ Using CPU", flush=True)
        except Exception:
            pass

        for mid, rev in preferred:
            if mid is None:
                continue
            try:
                print(f"🔄 Loading model: {mid}...", flush=True)
                kwargs = {"model": mid}
                if rev:
                    kwargs["revision"] = rev
                if device_arg is not None:
                    kwargs["device"] = device_arg
                # Enable chunking for long-form audio; smooth with stride
                kwargs["chunk_length_s"] = 30
                kwargs["stride_length_s"] = 5
                asr = pipeline("automatic-speech-recognition", **kwargs)
                print(f"✅ Model {mid} loaded successfully", flush=True)
                break
            except Exception as e:
                print(f"⚠️ Failed to load {mid}: {e}", flush=True)
                last_err = e
                continue

        if asr is None:
            # Final generic fallback
            print("⚠️ All preferred models failed, trying default fallback...", flush=True)
            asr = pipeline("automatic-speech-recognition")

        # Inference with graceful fallback to facebook/wav2vec2-base-960h if needed
        try:
            # For long-form Whisper models, request timestamps to satisfy requirement
            result = asr(str(file_path), return_timestamps=True)
            text = result.get('text', '').strip()
            return f"🎤 Speech Recognition Results:\n  Transcription: {text}"
        except Exception:
            # Build a conservative fallback model that is robust: wav2vec2-base-960h
            try:
                fb_kwargs = {"model": "facebook/wav2vec2-base-960h"}
                if device_arg is not None:
                    fb_kwargs["device"] = device_arg
                # chunking still helps for memory; wav2vec2 does not require timestamps
                fb_kwargs["chunk_length_s"] = 30
                fb_kwargs["stride_length_s"] = 5
                fb_asr = pipeline("automatic-speech-recognition", **fb_kwargs)
                result = fb_asr(str(file_path))
                text = result.get('text', '').strip()
                return f"🎤 Speech Recognition Results (fallback):\n  Transcription: {text}"
            except Exception as ee:
                return f"[ERROR] Speech recognition error after fallback: {ee}"
    except Exception as e:
        return f"[ERROR] Speech recognition error: {e}"



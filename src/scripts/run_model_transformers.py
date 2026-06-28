import sys
import os
import torch
import json
import logging
import base64
import io
from PIL import Image
from transformers import pipeline, AutoProcessor, AutoModelForVision2Seq, AutoModelForCausalLM

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)

def extract_media_from_prompt(prompt):
    clean_prompt = ""
    images = []
    audio_clips = []
    current_pos = 0
    while True:
        img_idx = prompt.find("[IMAGE:", current_pos)
        aud_idx = prompt.find("[AUDIO:", current_pos)
        
        if img_idx == -1 and aud_idx == -1:
            break
            
        if img_idx != -1 and (aud_idx == -1 or img_idx < aud_idx):
            clean_prompt += prompt[current_pos:img_idx]
            remaining = prompt[img_idx + 7:]
            end_idx = remaining.find(']')
            if end_idx != -1:
                images.append(remaining[:end_idx])
                current_pos = img_idx + 7 + end_idx + 1
            else:
                clean_prompt += prompt[img_idx:]
                current_pos = len(prompt)
                break
        else:
            clean_prompt += prompt[current_pos:aud_idx]
            remaining = prompt[aud_idx + 7:]
            end_idx = remaining.find(']')
            if end_idx != -1:
                audio_clips.append(remaining[:end_idx])
                current_pos = aud_idx + 7 + end_idx + 1
            else:
                clean_prompt += prompt[aud_idx:]
                current_pos = len(prompt)
                break
                
    if current_pos < len(prompt):
        clean_prompt += prompt[current_pos:]
    return clean_prompt, images, audio_clips

def main():
    if len(sys.argv) < 3:
        print("ERROR: Missing arguments. Usage: python run_model_transformers.py <model_id> <prompt> [max_tokens] [temperature] [device]", file=sys.stderr)
        sys.exit(1)
        
    model_id = sys.argv[1]
    prompt = sys.argv[2]
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
    device_arg = sys.argv[5] if len(sys.argv) > 5 else "auto"
    
    try:
        # Determine device and dtype
        if device_arg == "cuda" and torch.cuda.is_available():
            device = 0
            device_str = "cuda"
            dtype = torch.float16
            print(f"[TRANSFORMERS] Using GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
        elif device_arg == "auto" and torch.cuda.is_available():
            free_vram_gb = torch.cuda.mem_get_info()[0] / (1024**3)
            if free_vram_gb > 2.0:
                device = 0
                device_str = "cuda"
                dtype = torch.float16
                print(f"[TRANSFORMERS] Auto-selected GPU: {torch.cuda.get_device_name(0)} ({free_vram_gb:.1f} GB free)", file=sys.stderr)
            else:
                device = -1
                device_str = "cpu"
                dtype = torch.float32
                print(f"[TRANSFORMERS] Auto-selected CPU (only {free_vram_gb:.1f} GB VRAM free)", file=sys.stderr)
        else:
            device = -1
            device_str = "cpu"
            dtype = torch.float32
            print("[TRANSFORMERS] Using CPU", file=sys.stderr)

        clean_prompt, images_b64, audio_clips = extract_media_from_prompt(prompt)
        
        # ── Local Voice / Audio Transcription Cascade ─────────────
        if audio_clips:
            print(f"[TRANSFORMERS] Multimodal audio inputs detected ({len(audio_clips)} clips). Loading Whisper for local transcription...", file=sys.stderr)
            try:
                import soundfile as sf
                import librosa
                
                for aud_b64 in audio_clips:
                    aud_bytes = base64.b64decode(aud_b64)
                    data, samplerate = sf.read(io.BytesIO(aud_bytes))
                    if len(data.shape) > 1:
                        data = data.mean(axis=1)
                    if samplerate != 16000:
                        data = librosa.resample(data, orig_sr=samplerate, target_sr=16000)
                        
                    # Use a very small whisper model locally (quick & light)
                    asr_pipe = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device=device, torch_dtype=dtype)
                    asr_out = asr_pipe(data)
                    transcription = asr_out.get("text", "")
                    print(f"[TRANSFORMERS] Transcribed audio: \"{transcription}\"", file=sys.stderr)
                    clean_prompt += f"\n[Voice Input: {transcription}]"
            except Exception as ae:
                print(f"[TRANSFORMERS] ⚠️ Audio transcription failed: {ae}. Make sure soundfile and librosa are installed.", file=sys.stderr)
        
        if not images_b64:
            # ── Text-Only Pipeline ────────────────────────
            pipe = pipeline(
                "text-generation",
                model=model_id,
                device=device,
                trust_remote_code=True,
                torch_dtype=dtype
            )
            if pipe.tokenizer.pad_token_id is None:
                pipe.tokenizer.pad_token_id = pipe.tokenizer.eos_token_id
                
            outputs = pipe(
                clean_prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0.0 else False,
                pad_token_id=pipe.tokenizer.eos_token_id,
                return_full_text=False
            )
            print(outputs[0]['generated_text'])
            return

        # ── Multimodal / Vision Model Execution ──────────────────
        print(f"[TRANSFORMERS] Multimodal inputs detected ({len(images_b64)} images). Loading vision model...", file=sys.stderr)
        
        pil_images = []
        for img_b64 in images_b64:
            img_bytes = base64.b64decode(img_b64)
            pil_images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
            
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        
        # Load model using AutoModelForVision2Seq or AutoModelForCausalLM (as fallback)
        try:
            model = AutoModelForVision2Seq.from_pretrained(
                model_id, 
                trust_remote_code=True, 
                torch_dtype=dtype
            )
        except Exception:
            model = AutoModelForCausalLM.from_pretrained(
                model_id, 
                trust_remote_code=True, 
                torch_dtype=dtype
            )
            
        if device_str == "cuda":
            model = model.to("cuda")

        # Format inputs for vision models
        inputs = processor(text=clean_prompt, images=pil_images, return_tensors="pt")
        if device_str == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
        # Generate response
        generated_ids = model.generate(
            **inputs, 
            max_new_tokens=max_tokens,
            do_sample=True if temperature > 0.0 else False,
            temperature=temperature if temperature > 0.0 else 1.0
        )
        
        # Truncate prompt from generation if the model output includes prompt tokens
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.get("input_ids", [[]]), generated_ids)
        ]
        
        generated_text = processor.batch_decode(
            generated_ids_trimmed, 
            skip_special_tokens=True, 
            clean_up_tokenization_spaces=False
        )[0]
        
        print(generated_text)
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

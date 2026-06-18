import sys
import os
import torch
import json
import logging
from transformers import pipeline

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)

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
        # Determine device based on argument and hardware availability
        if device_arg == "cuda" and torch.cuda.is_available():
            device = 0  # GPU index 0
            dtype = torch.float16
            print(f"[TRANSFORMERS] Using GPU: {torch.cuda.get_device_name(0)}", file=sys.stderr)
        elif device_arg == "auto" and torch.cuda.is_available():
            # Auto mode: check if model fits in VRAM
            free_vram_gb = torch.cuda.mem_get_info()[0] / (1024**3)
            # Rough heuristic: if we have > 2GB free VRAM, try GPU
            if free_vram_gb > 2.0:
                device = 0
                dtype = torch.float16
                print(f"[TRANSFORMERS] Auto-selected GPU: {torch.cuda.get_device_name(0)} ({free_vram_gb:.1f} GB free)", file=sys.stderr)
            else:
                device = -1  # CPU
                dtype = torch.float32
                print(f"[TRANSFORMERS] Auto-selected CPU (only {free_vram_gb:.1f} GB VRAM free)", file=sys.stderr)
        else:
            device = -1  # CPU
            dtype = torch.float32
            if device_arg == "cuda":
                print("[TRANSFORMERS] CUDA requested but not available, falling back to CPU", file=sys.stderr)
            else:
                print("[TRANSFORMERS] Using CPU", file=sys.stderr)
        
        # Load the text-generation pipeline
        # Use trust_remote_code=True to handle custom architectures (e.g. Qwen, DeepSeek)
        pipe = pipeline(
            "text-generation",
            model=model_id,
            device=device,
            trust_remote_code=True,
            torch_dtype=dtype
        )
        
        # Ensure pad token is set
        if pipe.tokenizer.pad_token_id is None:
            pipe.tokenizer.pad_token_id = pipe.tokenizer.eos_token_id
            
        # Format input messages if the prompt looks like it has system/user roles
        # Otherwise, pass raw prompt
        prompt_input = prompt
        
        # Run text generation
        outputs = pipe(
            prompt_input,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True if temperature > 0.0 else False,
            pad_token_id=pipe.tokenizer.eos_token_id,
            return_full_text=False
        )
        
        # Extract and print output
        generated_text = outputs[0]['generated_text']
        print(generated_text)
        
    except torch.cuda.OutOfMemoryError:
        print(f"[TRANSFORMERS] GPU OOM! Retrying on CPU...", file=sys.stderr)
        # Fallback to CPU on OOM
        torch.cuda.empty_cache()
        pipe = pipeline(
            "text-generation",
            model=model_id,
            device=-1,
            trust_remote_code=True,
            torch_dtype=torch.float32
        )
        if pipe.tokenizer.pad_token_id is None:
            pipe.tokenizer.pad_token_id = pipe.tokenizer.eos_token_id
        outputs = pipe(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True if temperature > 0.0 else False,
            pad_token_id=pipe.tokenizer.eos_token_id,
            return_full_text=False
        )
        print(outputs[0]['generated_text'])
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

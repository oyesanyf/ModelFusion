import sys
import os
import torch
import logging
import warnings
from transformers import AutoTokenizer

# Suppress HuggingFace and Python warnings completely to prevent PowerShell stderr intercept
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
logging.getLogger("transformers").setLevel(logging.ERROR)

# Optimum ONNX Runtime imports
try:
    from optimum.onnxruntime import ORTModelForCausalLM
except ImportError:
    print("ERROR: optimum[onnxruntime] is not installed. Please run: pip install optimum[onnxruntime] or optimum[onnxruntime-gpu]")
    sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("ERROR: Missing arguments. Usage: python run_model_onnx.py <model_id> <prompt> [max_tokens] [temperature] [device]")
        sys.exit(1)
        
    model_id = sys.argv[1]
    prompt = sys.argv[2]
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
    device_arg = sys.argv[5] if len(sys.argv) > 5 else "auto"

    # Construct cached path
    safe_name = model_id.split("/")[-1].lower().replace(" ", "-")
    cache_dir = os.path.join("ov_models", f"{safe_name}-onnx")
    
    has_cache = False
    if os.path.exists(cache_dir):
        try:
            if len(os.listdir(cache_dir)) > 0:
                has_cache = True
        except Exception:
            pass

    # Setup execution providers & Load model
    try:
        model = None
        provider_used = "CPUExecutionProvider"

        if has_cache:
            print(f"[ONNX] ✅ Using cached converted model at {cache_dir}")
            tokenizer = AutoTokenizer.from_pretrained(cache_dir)
            if device_arg == "cuda" and torch.cuda.is_available():
                try:
                    print("[ONNX] Loading cached model with CUDAExecutionProvider (GPU)...")
                    model = ORTModelForCausalLM.from_pretrained(
                        cache_dir, 
                        export=False, 
                        provider="CUDAExecutionProvider"
                    )
                    provider_used = "CUDAExecutionProvider"
                except Exception as cuda_err:
                    print(f"[ONNX] ⚠️ CUDAExecutionProvider failed: {cuda_err}. Falling back to CPU...")
                    model = ORTModelForCausalLM.from_pretrained(
                        cache_dir, 
                        export=False, 
                        provider="CPUExecutionProvider"
                    )
                    provider_used = "CPUExecutionProvider"
            else:
                print("[ONNX] Loading cached model with CPUExecutionProvider...")
                model = ORTModelForCausalLM.from_pretrained(
                    cache_dir, 
                    export=False, 
                    provider="CPUExecutionProvider"
                )
                provider_used = "CPUExecutionProvider"
        else:
            print(f"[ONNX] 🔄 Exporting model {model_id} to ONNX format (first-time export)...")
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            if device_arg == "cuda" and torch.cuda.is_available():
                try:
                    print("[ONNX] Exporting with CUDAExecutionProvider (GPU)...")
                    model = ORTModelForCausalLM.from_pretrained(
                        model_id, 
                        export=True, 
                        provider="CUDAExecutionProvider"
                    )
                    provider_used = "CUDAExecutionProvider"
                except Exception as cuda_err:
                    print(f"[ONNX] ⚠️ CUDAExport failed: {cuda_err}. Falling back to CPU...")
                    model = ORTModelForCausalLM.from_pretrained(
                        model_id, 
                        export=True, 
                        provider="CPUExecutionProvider"
                    )
                    provider_used = "CPUExecutionProvider"
            else:
                print("[ONNX] Exporting with CPUExecutionProvider...")
                model = ORTModelForCausalLM.from_pretrained(
                    model_id, 
                    export=True, 
                    provider="CPUExecutionProvider"
                )
                provider_used = "CPUExecutionProvider"
            
            # Save the exported model and tokenizer to disk for future runs
            os.makedirs(cache_dir, exist_ok=True)
            print(f"[ONNX] Saving converted model to {cache_dir}...")
            model.save_pretrained(cache_dir)
            tokenizer.save_pretrained(cache_dir)

        inputs = tokenizer(prompt, return_tensors="pt")
        # Put inputs on CUDA if running with CUDA
        if provider_used == "CUDAExecutionProvider":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
        outputs = model.generate(
            **inputs, 
            max_new_tokens=max_tokens, 
            temperature=temperature, 
            do_sample=True if temperature > 0.0 else False,
            pad_token_id=tokenizer.eos_token_id or tokenizer.pad_token_id
        )
        
        generated_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        # Write actual generated answer to stdout
        print(generated_text)
    except Exception as e:
        # Write actual error message to stderr on exit
        print(f"ERROR: ONNX model execution failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

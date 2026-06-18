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
        print("ERROR: Missing arguments. Usage: python run_model_transformers.py <model_id> <prompt> [max_tokens] [temperature]", file=sys.stderr)
        sys.exit(1)
        
    model_id = sys.argv[1]
    prompt = sys.argv[2]
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
    
    try:
        # Determine device: GPU if available, else CPU
        device = 0 if torch.cuda.is_available() else -1
        
        # Load the text-generation pipeline
        # Use trust_remote_code=True to handle custom architectures (e.g. Qwen, DeepSeek)
        pipe = pipeline(
            "text-generation",
            model=model_id,
            device=device,
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
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
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

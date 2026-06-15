import os
import traceback
from huggingface_hub import InferenceClient
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

# --- CONFIGURATION ---
REMOTE_MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"
LOCAL_MODEL_ID = "tiiuae/falcon-rw-1b"  # Replace with any local causal LM
PROMPT = "What is the capital of Kenya?"
MAX_TOKENS = 100

# --- Load HF Token ---
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise EnvironmentError("❌ HF_TOKEN environment variable is not set.")

# --- Try Inference API with Chat Completion ---
try:
    print("🌐 Trying Hugging Face Inference API (chat completion)...")
    client = InferenceClient(model=REMOTE_MODEL_ID, token=HF_TOKEN)
    messages = [{"role": "user", "content": PROMPT}]
    response = client.chat_completion(messages=messages, max_tokens=MAX_TOKENS)
    print("\n✅ Inference API Response:")
    print(response.choices[0].message.content)

except Exception as e:
    print(f"\n❌ Inference API failed: {e}")
    print("🔄 Falling back to local Transformers pipeline...")

    try:
        tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(LOCAL_MODEL_ID)
        generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

        # Basic prompt fallback (simulate chat)
        local_output = generator(PROMPT, max_new_tokens=MAX_TOKENS, temperature=0.7)
        print("\n✅ Local generation response:")
        print(local_output[0]["generated_text"])

    except Exception as local_error:
        print("\n❌ Local fallback failed.")
        traceback.print_exc()

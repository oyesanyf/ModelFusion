import sys
import os
import logging

# Suppress warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.getLogger("transformers").setLevel(logging.ERROR)


def detect_best_device(core):
    """Auto-detect the best OpenVINO device based on available hardware."""
    available = core.available_devices
    print(f"[OPENVINO] Available devices: {available}", file=sys.stderr)

    # Detect system resources
    import multiprocessing
    cpu_cores = multiprocessing.cpu_count()

    ram_gb = 0
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_gb = mem.available / (1024 ** 3)
        print(f"[OPENVINO] System: {cpu_cores} CPU cores, {ram_gb:.1f} GB free RAM", file=sys.stderr)
    except ImportError:
        print(f"[OPENVINO] System: {cpu_cores} CPU cores (psutil not installed, RAM unknown)", file=sys.stderr)

    # Device priority: GPU > AUTO > CPU
    # Note: OpenVINO GPU = Intel GPU (iGPU/dGPU), not NVIDIA
    if "GPU" in available:
        try:
            gpu_name = core.get_property("GPU", "FULL_DEVICE_NAME")
            print(f"[OPENVINO] 🎮 Intel GPU detected: {gpu_name}", file=sys.stderr)
        except Exception:
            print(f"[OPENVINO] 🎮 GPU detected", file=sys.stderr)
        return "GPU"
    elif "AUTO" in available:
        print(f"[OPENVINO] Using AUTO device selection", file=sys.stderr)
        return "AUTO"
    else:
        print(f"[OPENVINO] Using CPU ({cpu_cores} cores)", file=sys.stderr)
        return "CPU"


def get_compile_config(device):
    """Get optimal compile configuration based on device and system resources."""
    import openvino.properties as props
    import openvino.properties.hint as hints

    config = {}

    if device == "CPU":
        import multiprocessing
        cpu_cores = multiprocessing.cpu_count()

        config[hints.performance_mode()] = hints.PerformanceMode.LATENCY

        if cpu_cores >= 16:
            config[props.inference_num_threads()] = cpu_cores - 2
        elif cpu_cores >= 8:
            config[props.inference_num_threads()] = cpu_cores - 1

        try:
            config[props.streams.num()] = 1
        except Exception:
            pass

        threads = config.get(props.inference_num_threads(), 'auto')
        print(f"[OPENVINO] CPU config: latency mode, {threads} threads", file=sys.stderr)

    elif device == "GPU":
        config[hints.performance_mode()] = hints.PerformanceMode.LATENCY
        config[hints.model_priority()] = hints.Priority.HIGH
        print(f"[OPENVINO] GPU config: latency mode, high priority", file=sys.stderr)

    elif device == "AUTO":
        config[hints.performance_mode()] = hints.PerformanceMode.LATENCY
        print(f"[OPENVINO] AUTO config: latency mode", file=sys.stderr)

    return config


def main():
    if len(sys.argv) < 3:
        print("ERROR: Missing arguments. Usage: python run_model_openvino.py <model_id> <prompt> [max_tokens] [temperature]", file=sys.stderr)
        sys.exit(1)

    model_id = sys.argv[1]
    prompt = sys.argv[2]
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7

    try:
        import openvino as ov
    except ImportError:
        print("ERROR: OpenVINO not installed. Install with: pip install -U openvino", file=sys.stderr)
        sys.exit(1)

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        import numpy as np
    except ImportError:
        print("ERROR: transformers/torch not installed.", file=sys.stderr)
        sys.exit(1)

    core = ov.Core()
    device = detect_best_device(core)

    print(f"[OPENVINO] Loading model {model_id} → target device: {device}", file=sys.stderr)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Tokenize input
    inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=2048)
    input_ids = inputs["input_ids"]

    # Cache directory for converted OpenVINO IR models (per device)
    cache_dir = os.path.join(
        os.path.expanduser("~"), ".cache", "modelfusion_ov",
        model_id.replace("/", "_"), device.lower()
    )
    ov_model_path = os.path.join(cache_dir, "model.xml")

    if os.path.exists(ov_model_path):
        print(f"[OPENVINO] Loading cached IR model from {cache_dir}", file=sys.stderr)
        ov_model = core.read_model(ov_model_path)
    else:
        print(f"[OPENVINO] Loading PyTorch model for conversion...", file=sys.stderr)
        pt_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        pt_model.eval()

        print(f"[OPENVINO] Converting model to OpenVINO IR format (one-time)...", file=sys.stderr)

        # Wrap the model to return only logits (OpenVINO can't trace DynamicCache)
        class LogitsOnlyWrapper(torch.nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

            def forward(self, input_ids, attention_mask):
                with torch.no_grad():
                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        use_cache=False,  # Disable DynamicCache
                    )
                    return outputs.logits

        wrapper = LogitsOnlyWrapper(pt_model)
        wrapper.eval()

        # Convert via ONNX export path for maximum compatibility
        try:
            # Try torch.export first (modern path)
            print(f"[OPENVINO] Trying torch.export conversion...", file=sys.stderr)
            example_input = (input_ids, inputs["attention_mask"])
            ov_model = ov.convert_model(wrapper, example_input=example_input)
        except Exception as e1:
            print(f"[OPENVINO] torch.export failed ({e1.__class__.__name__}), trying ONNX export...", file=sys.stderr)
            # Fallback: export to ONNX first, then load with OpenVINO
            onnx_path = os.path.join(cache_dir, "model.onnx")
            os.makedirs(cache_dir, exist_ok=True)
            torch.onnx.export(
                wrapper,
                (input_ids, inputs["attention_mask"]),
                onnx_path,
                input_names=["input_ids", "attention_mask"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "seq_len"},
                    "attention_mask": {0: "batch", 1: "seq_len"},
                    "logits": {0: "batch", 1: "seq_len"},
                },
                opset_version=17,
            )
            print(f"[OPENVINO] ONNX export complete, converting to IR...", file=sys.stderr)
            ov_model = core.read_model(onnx_path)
            # Clean up ONNX file after conversion
            try:
                os.remove(onnx_path)
            except OSError:
                pass

        # Save IR for future use
        os.makedirs(cache_dir, exist_ok=True)
        ov.save_model(ov_model, ov_model_path)
        print(f"[OPENVINO] Model cached at {cache_dir}", file=sys.stderr)

        # Free PyTorch model
        del pt_model, wrapper
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import gc; gc.collect()

    # Compile with device-optimized configuration
    compile_config = get_compile_config(device)
    print(f"[OPENVINO] Compiling model for {device}...", file=sys.stderr)
    compiled_model = core.compile_model(ov_model, device, compile_config)

    print(f"[OPENVINO] Generating on {device} (max_tokens={max_tokens}, temp={temperature})...", file=sys.stderr)

    # Autoregressive generation loop
    generated_ids = input_ids.numpy().tolist()[0]
    attention_mask = inputs["attention_mask"].numpy().tolist()[0]

    for step in range(max_tokens):
        input_array = np.array([generated_ids], dtype=np.int64)
        mask_array = np.array([attention_mask], dtype=np.int64)

        result = compiled_model({"input_ids": input_array, "attention_mask": mask_array})

        # Get logits for the last token
        logits = result[0]  # shape: [1, seq_len, vocab_size]
        next_token_logits = logits[0, -1, :]

        if temperature > 0.0 and temperature != 1.0:
            next_token_logits = next_token_logits / temperature

        if temperature > 0.0:
            probs = np.exp(next_token_logits - np.max(next_token_logits))
            probs = probs / probs.sum()
            next_token_id = int(np.random.choice(len(probs), p=probs))
        else:
            next_token_id = int(np.argmax(next_token_logits))

        if next_token_id == tokenizer.eos_token_id:
            break

        generated_ids.append(next_token_id)
        attention_mask.append(1)

    # Decode only the new tokens
    new_tokens = generated_ids[input_ids.shape[1]:]
    generated_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    print(generated_text)


if __name__ == "__main__":
    main()

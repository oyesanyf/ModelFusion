import sys
import os
import json
import logging

os.environ["TOKENIZERS_PARALLELISM"] = "true"

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_model_vllm")


def main():
    if len(sys.argv) < 3:
        print(
            "ERROR: Missing arguments. Usage: python3 run_model_vllm.py "
            "<model_id> <prompt> [max_tokens] [temperature]",
            file=sys.stderr,
        )
        sys.exit(1)

    model_id = sys.argv[1]
    prompt = sys.argv[2]
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    temperature = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7

    # --- Validate environment ------------------------------------------------
    try:
        import torch
    except ImportError:
        print("ERROR: PyTorch is not installed.", file=sys.stderr)
        sys.exit(1)

    if not torch.cuda.is_available():
        print(
            "ERROR: No CUDA-capable GPU detected. "
            "vLLM requires at least one NVIDIA GPU.",
            file=sys.stderr,
        )
        sys.exit(1)

    gpu_count = torch.cuda.device_count()
    logger.info("Detected %d CUDA device(s).", gpu_count)
    for i in range(gpu_count):
        logger.info("  GPU %d: %s", i, torch.cuda.get_device_name(i))

    # --- Import vLLM (after GPU check so the error message is clearer) -------
    try:
        from vllm import LLM, SamplingParams
    except ImportError:
        print(
            "ERROR: vLLM is not installed. "
            "Install it with: pip install vllm",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Configure sampling ---------------------------------------------------
    sampling_params = SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
    )
    logger.info(
        "Sampling params – max_tokens: %d, temperature: %.2f",
        max_tokens,
        temperature,
    )

    # --- Load model -----------------------------------------------------------
    logger.info("Loading model '%s' with tensor_parallel_size=%d …", model_id, gpu_count)
    try:
        llm = LLM(
            model=model_id,
            tensor_parallel_size=gpu_count,
            trust_remote_code=True,
        )
    except Exception as exc:
        print(
            f"ERROR: Failed to load model '{model_id}': {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Run inference --------------------------------------------------------
    logger.info("Running inference …")
    try:
        outputs = llm.generate([prompt], sampling_params)
    except Exception as exc:
        print(
            f"ERROR: Inference failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not outputs or not outputs[0].outputs:
        print("ERROR: Model returned no output.", file=sys.stderr)
        sys.exit(1)

    generated_text = outputs[0].outputs[0].text
    logger.info("Inference complete – generated %d characters.", len(generated_text))

    # --- Output (stdout only) -------------------------------------------------
    print(generated_text)


if __name__ == "__main__":
    main()

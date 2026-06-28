import sys
import traceback

print(f"Python: {sys.version}", file=sys.stderr)

# Test 1: optimum-intel
try:
    from optimum.intel import OVModelForCausalLM
    print("1. optimum-intel OVModelForCausalLM: OK", file=sys.stderr)
except Exception as e:
    print(f"1. optimum-intel FAILED:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)

# Test 2: openvino_genai
try:
    import openvino_genai
    print("2. openvino_genai: OK", file=sys.stderr)
except Exception as e:
    print(f"2. openvino_genai FAILED: {e}", file=sys.stderr)

# Test 3: openvino classic
try:
    import openvino as ov
    print(f"3. openvino classic: OK (version {ov.__version__})", file=sys.stderr)
except Exception as e:
    print(f"3. openvino classic FAILED: {e}", file=sys.stderr)

# Test 4: transformers
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print("4. transformers: OK", file=sys.stderr)
except Exception as e:
    print(f"4. transformers FAILED: {e}", file=sys.stderr)

# Test 5: torch
try:
    import torch
    print(f"5. torch: OK (CUDA: {torch.cuda.is_available()})", file=sys.stderr)
except Exception as e:
    print(f"5. torch FAILED: {e}", file=sys.stderr)

print("\nDone.", file=sys.stderr)

import json, re, sys

target_path = r"C:/Users/oyesanyf/.gemini/antigravity/brain/b6ef927a-8ffc-4ecd-b7ed-90b470e8fc34/ModelFusion_Interactive_Docs.html"
with open(target_path, "r", encoding="utf-8") as f:
    text = f.read()

print("HTML length:", len(text))
flags_in_js = re.findall(r'"flag":\s*"(--[a-zA-Z0-9_-]+)"', text)
print("Flags in JS array:", len(flags_in_js))
assert len(flags_in_js) == 161, f"Expected 161 flags, got {len(flags_in_js)}"
print("VERIFICATION SUCCESS: Exact 161 flags present in Interactive Docs HTML!")

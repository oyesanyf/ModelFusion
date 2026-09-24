with open("crates/cli/src/main.rs", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '"agent"' in l and 6000 < i < 7000:
        print(f"Line {i+1}:")
        for j in range(max(0, i-2), min(i+8, len(lines))):
            print(f"{j+1}: {repr(lines[j])}")

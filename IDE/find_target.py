import os

file_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\dist\extension.js"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find('Q==="evolve"')
if idx != -1:
    print("Found Q===evolve at", idx)
    print(text[idx-100:idx+200])

import os

file_path = r"d:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\dist\extension.js"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("ModelFusionProvider: Starting chat response generation...")
if idx != -1:
    print(text[idx-200:idx+2500])

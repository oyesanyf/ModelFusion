import json, os

key_settings = {
    "hugos.modelfusion.openaiApiKey": {
        "type": "string",
        "default": "",
        "markdownDescription": "OpenAI API Key. Configures OpenAI GPT-4o models for local/hybrid routing. Status: `[DISABLED]` when empty, `[LOADED]` when set."
    },
    "hugos.modelfusion.anthropicApiKey": {
        "type": "string",
        "default": "",
        "markdownDescription": "Anthropic API Key. Configures Claude 3.5 Sonnet models for local/hybrid routing. Status: `[DISABLED]` when empty, `[LOADED]` when set."
    },
    "hugos.modelfusion.geminiApiKey": {
        "type": "string",
        "default": "",
        "markdownDescription": "Google Gemini API Key. Configures Gemini 1.5 Flash/Pro models. Status: `[DISABLED]` when empty, `[LOADED]` when set."
    },
    "hugos.modelfusion.huggingfaceApiKey": {
        "type": "string",
        "default": "",
        "markdownDescription": "HuggingFace API Key / User Access Token. Configures gated HF model downloads. Status: `[DISABLED]` when empty, `[LOADED]` when set."
    }
}

pkgs = [
    r'd:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode\.build\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\VSCode-win32-x64\7e7950df89\resources\app\extensions\copilot\package.json',
    r'd:\harfile\ModelFusion\IDE\vscode-126-extract\7e7950df89\resources\app\extensions\copilot\package.json'
]

for pkg_path in pkgs:
    if not os.path.exists(pkg_path):
        continue
    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg = json.load(f)
        
        configs = pkg.get('contributes', {}).get('configuration', [])
        updated = False
        for cfg in configs:
            props = cfg.get('properties', {})
            for key, val in key_settings.items():
                if key not in props:
                    props[key] = val
                    updated = True
                    print(f"Added setting {key} to {pkg_path}")
        
        if updated:
            with open(pkg_path, 'w', encoding='utf-8') as f:
                json.dump(pkg, f, indent=4)
            print(f"Saved settings update to {pkg_path}")
    except Exception as e:
        print(f"Error updating {pkg_path}: {e}")

print("Done adding API key settings to package.json files.")

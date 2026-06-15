from huggingface_hub import ModelCard, hf_hub_download
import json

models = [
    "deepset/roberta-base-squad2",
    "timpal0l/mdeberta-v3-base-squad2",
    # ... your other model IDs
]

for model_id in models:
    try:
        # Download model card (README)
        card = ModelCard.load(model_id)
        data = card.data.to_dict()
        
        # Metrics often stored under model-index
        if "model-index" in data:
            metrics = data["model-index"][0].get("results", [])
            for result in metrics:
                task = result.get("task", {}).get("type", "")
                for m in result.get("metrics", []):
                    if "f1" in m["name"].lower():
                        print(f"{model_id} - {task} - {m['name']}: {m['value']}")
        else:
            print(f"{model_id} - No stored metrics found")
    except Exception as e:
        print(f"{model_id} - Error reading metrics: {e}")
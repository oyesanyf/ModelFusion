import os
import sys
import io
from huggingface_hub import HfApi, snapshot_download

# Fix Windows console encoding for emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def download_openvino_zoo(target_folder="./my_openvino_zoo", search_filter="llama"):
    """
    Enumerates the OpenVINO Hugging Face repository list and bulk-downloads
    matching architectures into individual folders.
    """
    api = HfApi()
    
    # 1. Fetch the entire matching list from the OpenVINO organization
    print(f"[GETVINO] Enumerating Hub for OpenVINO models matching: '{search_filter}'...")
    models = list(api.list_models(author="OpenVINO", search=search_filter))
    
    print(f"[GETVINO] Found {len(models)} matching repositories.\n")
    
    # Create the root destination directory
    os.makedirs(target_folder, exist_ok=True)
    
    # 2. Iterate through the retrieved list and pull files down
    for idx, model_info in enumerate(models, start=1):
        repo_id = model_info.modelId
        
        # Format a clean local folder name (e.g., OpenVINO_Meta-Llama-3-8B-Instruct-INT4-ov)
        clean_name = repo_id.replace("/", "_")
        model_destination = os.path.join(target_folder, clean_name)
        
        # Skip if already downloaded
        if os.path.exists(model_destination) and os.listdir(model_destination):
            print(f"[{idx}/{len(models)}] Already exists, skipping: {repo_id}")
            continue
        
        print(f"[{idx}/{len(models)}] Downloading: {repo_id}")
        print(f"  -> Destination: {model_destination}")
        
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=model_destination,
                # Skips large original unoptimized framework binaries if present in the repo
                ignore_patterns=["*.original*", "*.git*"] 
            )
            print(f"  -> Download Complete.\n")
        except Exception as e:
            print(f"  -> Failed downloading {repo_id}: {e}\n")

if __name__ == "__main__":
    # Change search_filter to "bge" for embeddings, "whisper" for audio, or "" for absolutely everything.
    
    target_folder = sys.argv[1] if len(sys.argv) > 1 else "./my_openvino_zoo"
    search_filter = sys.argv[2] if len(sys.argv) > 2 else "llama"
    if search_filter.lower() == "all":
        search_filter = None
    
    download_openvino_zoo(
        target_folder=target_folder, 
        search_filter=search_filter
    )

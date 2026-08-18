import urllib.request
import json
import time

def test_data_command(command_name, dataset_path):
    url = "http://127.0.0.1:5000/orchestrate"
    
    # Read sample lines from dataset
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            sample_lines = "".join([f.readline() for _ in range(15)])
    except Exception as e:
        sample_lines = f"Error reading file: {e}"
        
    filename = dataset_path.split('\\')[-1]
    
    prompt_text = (
        f"<attachments>\n"
        f'<attachment id="file:{filename}">\n'
        f"User's active selection:\n"
        f"Excerpt from {filename}:\n"
        f"```csv\n{sample_lines}\n```\n"
        f"</attachment>\n"
        f"</attachments>\n"
        f"@{command_name} Analyze dataset {filename} and build predictive model"
    )
    
    payload = {
        "prompt": f"System: You are HugOS AI assistant.\nUser: {prompt_text}",
        "backend": "ollama",
        "device": "gpu",
        "budget": 7,
        "strategy": "multi_objective",
        "fusion": False
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_bytes = response.read()
            elapsed = (time.time() - start_time) * 1000
            res_str = res_bytes.decode('utf-8', errors='ignore')
            safe_str = res_str.encode('ascii', 'ignore').decode('ascii')
            print(f"[{elapsed:.1f}ms] Success for '/{command_name}' with {filename}: {safe_str[:250]}...")
            return True, res_str
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        print(f"[{elapsed:.1f}ms] Error for '/{command_name}' with {filename}: {e}")
        return False, str(e)

if __name__ == "__main__":
    print("Testing ModelFusion Data Science & Analyst Slash Commands on port 5000...")
    datasets_dir = r"D:\dataset\Seaborn All Built-in Datasets"
    
    test_data_command("dataanalyst", f"{datasets_dir}\\titanic.csv")
    test_data_command("datascience", f"{datasets_dir}\\penguins.csv")
    test_data_command("jupyter", f"{datasets_dir}\\iris.csv")
    test_data_command("stats", f"{datasets_dir}\\diamonds.csv")

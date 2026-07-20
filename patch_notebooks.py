import json

def patch_notebook(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for cell in data.get('cells', []):
        if cell.get('cell_type') == 'code':
            new_source = []
            modified = False
            for line in cell.get('source', []):
                if 'snapshot_download(repo_id=identity.exact_model_identifier' in line and 'ignore_patterns' not in line:
                    new_line = line.replace('token=hf_token)', 'token=hf_token, ignore_patterns=["*.bin", "*.pth", "*.pt", "*.gguf", "consolidated.safetensors"])')
                    new_source.append(new_line)
                    modified = True
                else:
                    new_source.append(line)
            if modified:
                cell['source'] = new_source
                print(f"Patched cell in {filepath}")

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)

patch_notebook('phase5/kaggle/official_phase5_runner.ipynb')
patch_notebook('phase5/kaggle/phase5_m1_shared_engine_kaggle_proof.ipynb')

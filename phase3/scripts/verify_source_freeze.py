import os
import hashlib

base_dir = "."

def hash_dir(directory):
    h = hashlib.sha256()
    full_path = os.path.join(base_dir, directory)
    if not os.path.exists(full_path):
        return h.hexdigest()
        
    for root, dirs, files in os.walk(full_path):
        # Exclude pycache
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        for file in sorted(files):
            # Only hash code and prompts
            if file.endswith(('.py', '.json', '.yaml', '.txt', '.csv', '.jsonl')):
                p = os.path.join(root, file)
                with open(p, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        h.update(chunk)
    return h.hexdigest()

def verify_freeze():
    targets = [
        "client", "server", "schemas", "prompts", "tests", "scripts", "docker",
        "phase3/tasks", "phase3/matrices", "phase3/scripts",
        "phase3/configs/phase3_global.yaml",
        "phase3/configs/deterministic_inference.yaml",
        "phase3/configs/reset_policy.yaml"
    ]
    
    global_hash = hashlib.sha256()
    report = ["# Source Freeze Verification Report\n"]
    
    for t in targets:
        path = os.path.join(base_dir, t)
        if os.path.isdir(path):
            h = hash_dir(t)
        elif os.path.isfile(path):
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            h = h.hexdigest()
        else:
            h = "MISSING"
            
        global_hash.update(h.encode())
        report.append(f"- `{t}`: {h}")
        
    final = global_hash.hexdigest()
    report.insert(1, f"**GLOBAL HASH**: `{final}`\n")
    
    with open(os.path.join(base_dir, "phase3/validation/source_hash_verification_report.md"), "w") as f:
        f.write("\n".join(report))
        
    print(f"PASS: Source freeze calculated. Hash: {final}")

if __name__ == "__main__":
    verify_freeze()

import os
import hashlib
import json

def hash_file(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def create_manifest(directory, output_file, filter_ext=None):
    manifest = []
    for root, _, files in os.walk(directory):
        for file in files:
            if filter_ext and not file.endswith(filter_ext):
                continue
            path = os.path.join(root, file)
            manifest.append({
                "file": file,
                "sha256": hash_file(path)
            })
    with open(output_file, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {output_file}")

# 1. Schemas
schema_dir = "phase2_5/inputs/schemas"
schema_manifest = "phase2_5/inputs/schema_hashes/schema_hash_manifest.json"
create_manifest(schema_dir, schema_manifest, ".json")

# 2. Scripts
scripts_dir = "phase2_5/scripts"
script_manifest = "phase2_5/scripts/script_manifest.json"
create_manifest(scripts_dir, script_manifest, ".py")

import hashlib, json, os, sys

def verify_scripts(manifest_path: str, scripts_dir: str) -> bool:
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        all_ok = True
        expected_files = set()
        for entry in manifest:
            script_name = os.path.basename(entry["file"])
            target_path = os.path.join(scripts_dir, script_name)
            expected_files.add(target_path)
            if not os.path.exists(target_path):
                print(f"FATAL: Required validation script missing: {script_name}")
                all_ok = False
                continue
            with open(target_path, "rb") as sf:
                actual_hash = hashlib.sha256(sf.read()).hexdigest()
            if actual_hash != entry["sha256"]:
                print(f"FATAL: Code drift localized inside: {script_name}")
                all_ok = False
        for file in os.listdir(scripts_dir):
            if file.endswith(".py"):
                full_p = os.path.join(scripts_dir, file)
                if full_p not in expected_files:
                    print(f"FATAL: Unregistered executable file detected: {file}")
                    all_ok = False
        return all_ok
    except Exception as e:
        print(f"Verification script validation system failure: {str(e)}")
        return False

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    m_path = os.path.join(base_dir, "script_manifest.json")
    status = verify_scripts(m_path, base_dir)
    if status:
        print("Script manifest verified successfully.")
    sys.exit(0 if status else 1)

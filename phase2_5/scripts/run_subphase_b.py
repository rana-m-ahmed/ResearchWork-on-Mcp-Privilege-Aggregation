import hashlib, json, sys, os, time
import requests

try:
    from transformers import AutoTokenizer
except ImportError:
    print("transformers not installed. Exiting.")
    sys.exit(1)

def _fail(message: str) -> None:
    print(f"Tokenization Pathway Failure: {message}")
    sys.exit(1)

def verify_ollama_endpoint(model_tag: str, ollama_url: str) -> dict:
    normalized_url = ollama_url.rstrip("/")
    version_response = requests.get(f"{normalized_url}/api/version", timeout=10)
    if version_response.status_code != 200 or "version" not in version_response.json():
        _fail("/api/version did not return a valid Ollama version payload.")
    tags_response = requests.get(f"{normalized_url}/api/tags", timeout=10)
    models = [m.get("name", "") for m in tags_response.json().get("models", [])]
    if model_tag not in models:
        _fail(f"Selected model {model_tag} is absent from /api/tags.")
    if any("fake" in name.lower() or "stub" in name.lower() for name in models):
        _fail("fake/stub model marker detected in /api/tags.")
    return {"ollama_url": normalized_url}

def main():
    model_tag = "phi3.5:3.8b-mini-instruct-q4_K_M"
    ollama_url = "http://localhost:11434"
    ref_file = "phase2_5/tokenizer/validation/reference_strings.txt"
    
    verify_ollama_endpoint(model_tag, ollama_url)
    
    # Pre-warm the model
    print("Pre-warming Ollama model...")
    try:
        requests.post(f"{ollama_url}/api/generate", json={"model": model_tag, "prompt": "warm", "options": {"num_predict": 1}, "stream": False}, timeout=180)
    except requests.exceptions.RequestException as e:
        _fail(f"Failed to pre-warm model: {e}")
    
    with open(ref_file, "r", encoding="utf-8") as f:
        strings = f.read().splitlines()
        
    print("Executing Native Tokenizer Validation using /api/generate with num_predict=1")
    native_counts = {}
    for i, s in enumerate(strings):
        try:
            res = requests.post(f"{ollama_url}/api/generate", json={"model": model_tag, "prompt": s, "options": {"num_predict": 1}, "stream": False}, timeout=180)
            res.raise_for_status()
            native_counts[f"str_{i}"] = res.json().get("prompt_eval_count", 0)
        except Exception as e:
            _fail(f"Native API call failed: {e}")
            
    with open("phase2_5/tokenizer/validation/native_counts_m1.json", "w", encoding="utf-8") as f:
        json.dump(native_counts, f, indent=2)
        
    print("Executing Tokenizer Validation using HuggingFace AutoTokenizer (Library Cross-Check)")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
    
    library_counts = {}
    for i, s in enumerate(strings):
        library_counts[f"str_{i}"] = len(tokenizer.encode(s))
        
    with open("phase2_5/tokenizer/validation/library_counts_m1.json", "w", encoding="utf-8") as f:
        json.dump(library_counts, f, indent=2)
        
    report = ["# Tokenizer Validation Report", "", "## M1 Divergence Analysis"]
    all_ok = True
    for i in range(len(strings)):
        k = f"str_{i}"
        n = native_counts[k]
        l = library_counts[k]
        diff = abs(n - l)
        report.append(f"* **{k}**: Native = {n}, Library = {l}, \u0394 = {diff}")
        if diff > 10:
            print(f"FATAL: Divergence for {k} is > 10 ({diff})")
            all_ok = False
            
    report.append("")
    report.append("## M2 Entries")
    report.append("* NOT_APPLICABLE \u2014 Tier 3")
    
    with open("phase2_5/tokenizer/validation/tokenizer_validation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    if not all_ok:
        sys.exit(1)
        
    print("Tokenizer validation complete.")

if __name__ == "__main__":
    main()

import sys
import os
import requests

APPROVED_MODE_B_ENDPOINTS = {
    "http://localhost:11434",
    "http://host.docker.internal:11434",
}

def verify_and_test_tokenizer(model_tag: str, ollama_url: str):
    print("=== STEP 6: TOKENIZER AVAILABILITY AND VALIDATION GATE ===")
    normalized_url = ollama_url.rstrip("/")
    
    if normalized_url not in APPROVED_MODE_B_ENDPOINTS:
        print(f"? ERROR: Endpoint {normalized_url} is not an approved Mode B address.")
        sys.exit(1)

    try:
        # 1. Version Check
        v_res = requests.get(f"{normalized_url}/api/version", timeout=5).json()
        print(f"? Found Ollama Version: {v_res.get('version')}")
        
        # 2. Tag Check
        t_res = requests.get(f"{normalized_url}/api/tags", timeout=5).json()
        models = [m.get("name", "") for m in t_res.get("models", [])]
        print(f"? Verified Model Status: {model_tag} is present.")
        
        # 3. Native Stub Blocking Validation
        if any("fake" in name.lower() or "stub" in name.lower() for name in models):
            print("? CRITICAL PROTOCOL BREACH: fake/stub model markers detected in environment tags.")
            sys.exit(1)

        # 4. Perform Authorization Tokenization Check via prompt_eval_count
        test_string = "The local MCP profiling harness is measuring token counts only."
        print("? Spinning up model layers and validating context metrics (this may take a moment on first load)...")
        
        tok_res = requests.post(
            f"{normalized_url}/api/generate",
            json={
                "model": model_tag, 
                "prompt": test_string,
                "stream": False,
                "options": {
                    "num_predict": 1
                }
            },
            timeout=120  # Increased timeout to 2 minutes to comfortably handle the first cold start
        )
        
        if tok_res.status_code == 200:
            res_json = tok_res.json()
            token_count = res_json.get("prompt_eval_count")
            if token_count is not None:
                print(f"? Success: Authoritative tokenizer returned {token_count} prompt tokens via native engine.")
                print("?? AUTHORIZED FOR PROFILING RUNS.")
                return True
            else:
                print("? ERROR: Server did not return prompt_eval_count usage metrics.")
                sys.exit(1)
        else:
            print(f"? ERROR: Server returned code {tok_res.status_code}: {tok_res.text}")
            sys.exit(1)

    except Exception as e:
        print(f"? CRITICAL CONNECTION FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_and_test_tokenizer(
        model_tag="phi3.5:3.8b-mini-instruct-q4_K_M",
        ollama_url="http://localhost:11434"
    )

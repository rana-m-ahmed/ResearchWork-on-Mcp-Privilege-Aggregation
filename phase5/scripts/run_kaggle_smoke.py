import argparse
import sys
import os
import json
try:
    import psutil
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
except ImportError as e:
    print(f"Warning: Could not import {e.name}. Continuing for dry run.")
    psutil = None
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None

FROZEN_MODELS = {
    "M1": {"id": "google/gemma-2-9b-it", "revision": "main"},
    "M2": {"id": "meta-llama/Meta-Llama-3.1-8B-Instruct", "revision": "main"},
    "M3": {"id": "Qwen/Qwen2.5-7B-Instruct", "revision": "main"},
    "M4": {"id": "mistralai/Mistral-Nemo-Instruct-2407", "revision": "main"}
}

def get_cpu_gb():
    return psutil.virtual_memory().used / (1024**3)

def get_vram_gb():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / (1024**3)
    return 0.0

def generate_synthetic_row(trial_id, domain, attack):
    return {
        "phase": "phase5_nonofficial_validation",
        "dry_run": True,
        "official_trial": False,
        "counts_for_phase5": False,
        "publication_evidence": False,
        "synthetic_fixture": True,
        "trial_id": trial_id,
        "domain": domain,
        "attack": attack
    }

def run_smoke(dry_run=False, output_dir="/kaggle/working/phase5_nonofficial_validation"):
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    # 1. Sequential Model Loading Tests
    print("\\n[SMOKE] Running Sequential Model Loader Validations...")
    for m_id, cfg in FROZEN_MODELS.items():
        print(f"\\n--- Testing Loader: {m_id} ---")
        try:
            if dry_run:
                print(f"Dry run skipping load for {cfg['id']}")
                results[m_id] = {"status": "PASS", "load_time_sec": 0, "peak_vram_gb": 0, "synthetic_generated": True}
                continue

            start_time = time.time()
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            tokenizer = AutoTokenizer.from_pretrained(cfg["id"], revision=cfg["revision"])
            model = AutoModelForCausalLM.from_pretrained(
                cfg["id"], 
                revision=cfg["revision"],
                quantization_config=bnb_config,
                device_map="auto"
            )
            
            load_time = time.time() - start_time
            peak_vram = torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else 0.0
            
            # Unload clean
            del model
            del tokenizer
            gc.collect()
            torch.cuda.empty_cache()
            
            results[m_id] = {
                "status": "PASS",
                "load_time_sec": load_time,
                "peak_vram_gb": peak_vram,
                "synthetic_generated": True
            }
            print(f"Loaded {m_id} successfully.")
        except Exception as e:
            results[m_id] = {"status": "FAIL", "error": str(e)}
            print(f"Failed loading {m_id}: {e}")

    # 2. Representative Smoke Matrix on M1
    print("\\n[SMOKE] Running Representative Synthetic Matrix on non-official model...")
    matrix = [
        ("NONOFFICIAL-SYNTHETIC-D3-TD", "D3", "POISON_TD"),
        ("NONOFFICIAL-SYNTHETIC-D3-CA", "D3", "POISON_CA"),
        ("NONOFFICIAL-SYNTHETIC-D5-TD", "D5", "POISON_TD"),
        ("NONOFFICIAL-SYNTHETIC-D5-CA", "D5", "POISON_CA")
    ]
    
    matrix_results = {}
    try:
        # Load M1 once for the matrix
        m_id = "M1"
        cfg = FROZEN_MODELS[m_id]
        if not dry_run:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            tokenizer = AutoTokenizer.from_pretrained(cfg["id"], revision=cfg["revision"])
            model = AutoModelForCausalLM.from_pretrained(
                cfg["id"], 
                revision=cfg["revision"],
                quantization_config=bnb_config,
                device_map="auto"
            )

        for trial_id, dom, atk in matrix:
            print(f"Running canary trial: {trial_id} ({dom} x {atk})")
            prompt = "This is a synthetic canary for validation. Respond explicitly."
            if not dry_run:
                inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
                assert inputs["input_ids"].shape[1] <= 3584, "Token ceiling breached"
                with torch.no_grad():
                    outputs = model.generate(**inputs, max_new_tokens=20)
                output_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            else:
                output_text = "DRY RUN OK"

            evidence = generate_synthetic_row(trial_id, dom, atk)
            evidence["output"] = output_text
            with open(os.path.join(output_dir, f"{trial_id}_evidence.json"), "w") as f:
                json.dump(evidence, f, indent=2)
            matrix_results[trial_id] = "PASS"

        if not dry_run:
            del model
            del tokenizer
            gc.collect()
            torch.cuda.empty_cache()

    except Exception as e:
        print(f"Matrix generation failed: {e}")
        for trial_id, _, _ in matrix:
            if trial_id not in matrix_results:
                matrix_results[trial_id] = f"FAIL: {str(e)}"

    with open(os.path.join(output_dir, "model_loading_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    with open(os.path.join(output_dir, "synthetic_canary_results.json"), "w") as f:
        json.dump(matrix_results, f, indent=2)

    all_passed = all(r.get("status") == "PASS" for r in results.values()) and all(v == "PASS" for v in matrix_results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip heavy model weights load")
    parser.add_argument("--output-dir", type=str, default="/kaggle/working/phase5_nonofficial_validation")
    args = parser.parse_args()
    run_smoke(dry_run=args.dry_run, output_dir=args.output_dir)

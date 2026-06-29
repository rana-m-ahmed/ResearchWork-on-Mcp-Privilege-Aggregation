import json
import os
import shutil
import subprocess

def main():
    # 1. Re-derive Track A summary
    ra_raw = "phase2_5/profiling/researcher_a/raw/c1_d5_m1_tier3_ra.json"
    ra_summary = "phase2_5/profiling/researcher_a/summary_ra.json"
    if os.path.exists(ra_raw):
        shutil.copy(ra_raw, ra_summary)
        print("Derived summary_ra.json")
    else:
        print("ERROR: ra_raw missing")
        return

    # 2. Execute Track B
    print("Executing Track B tokenization...")
    # I will modify run_phase25.py on the fly to write to researcher_b
    with open("phase2_5/scripts/run_phase25.py", "r", encoding="utf-8") as f:
        code = f.read()
    
    code = code.replace("c1_d5_m1_tier3_ra.json", "c1_d5_m1_tier3_rb.json")
    code = code.replace("researcher_a", "researcher_b")
    code = code.replace("phase25_profile.json", "phase25_profile_b.json") # prevent overwriting
    
    with open("phase2_5/scripts/run_phase25_b.py", "w", encoding="utf-8") as f:
        f.write(code)
        
    subprocess.run(["python", "phase2_5/scripts/run_phase25_b.py"], check=True)
    
    rb_raw = "phase2_5/profiling/researcher_b/raw/c1_d5_m1_tier3_rb.json"
    rb_summary = "phase2_5/profiling/researcher_b/summary_rb.json"
    if os.path.exists(rb_raw):
        shutil.copy(rb_raw, rb_summary)
        print("Derived summary_rb.json")
        
    print("Sub-Phase C/D/E complete")

if __name__ == "__main__":
    main()

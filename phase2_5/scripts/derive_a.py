import shutil
import os

ra_raw = "phase2_5/profiling/researcher_a/raw/c1_d5_m1_tier3_ra.json"
ra_summary = "phase2_5/profiling/researcher_a/summary_ra.json"
if os.path.exists(ra_raw):
    shutil.copy(ra_raw, ra_summary)
    print("Derived summary_ra.json")

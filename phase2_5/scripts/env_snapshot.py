import platform
import os
import json
import subprocess

def get_ram():
    try:
        output = subprocess.check_output("wmic MemoryChip get Capacity", shell=True).decode()
        total = sum(int(x) for x in output.split() if x.isdigit())
        return f"{total / (1024**3):.2f} GB"
    except:
        return "Unknown"

snapshot = {
    "os": platform.system() + " " + platform.release(),
    "python_version": platform.python_version(),
    "cpu": platform.processor(),
    "ram": get_ram(),
    "gpu": "No dedicated GPU (Tier 3 assumption)"
}

with open("phase2_5/reproducibility/environment_snapshot.json", "w") as f:
    json.dump(snapshot, f, indent=2)
print("Snapshot saved")

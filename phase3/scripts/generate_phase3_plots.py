import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure output directories exist inside the phase3 subdirectory
output_dir = "phase3/reports/assets"
os.makedirs(output_dir, exist_ok=True)

# Define configuration parameters with correct model naming architecture
log_directory = "phase3/logs"
model_files = {
    "Model 1 (Qwen)": "trials_M1.jsonl",
    "Model 2 (DeepSeek)": "trials_M2.jsonl",
    "Model 3 (Mistral)": "trials_M3.jsonl",
    "Model 4 (Phi)": "trials_M4.jsonl"
}

all_trials = []

# 1. Parse JSONL log files directly using the structured grading contract
for model_name, filename in model_files.items():
    filepath = os.path.join(log_directory, filename)
    if not os.path.exists(filepath):
        print(f"[-] Warning: Missing log file {filepath}")
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            
            # Extract density tier from trial ID structural layout
            trial_id = data.get("trial_id", "")
            density_tier = "Unknown"
            if "D1" in trial_id: density_tier = "D1 (Low Density)"
            elif "D3" in trial_id: density_tier = "D3 (Mid Density)"
            elif "D5" in trial_id: density_tier = "D5 (High Density)"
            
            # Target the core contract grading metric to map accuracy properly
            gb = data.get("grade_breakdown", {})
            if isinstance(gb, dict) and "final_answer_correct" in gb:
                is_correct = gb.get("final_answer_correct", False)
            else:
                is_correct = data.get("trial_acceptance_valid", False)
            
            # Scale to 100 directly in data extraction to fix bar heights
            all_trials.append({
                "Model": model_name,
                "Density": density_tier,
                "Accuracy (%)": 100.0 if is_correct else 0.0
            })

df = pd.DataFrame(all_trials)

if df.empty:
    print("[-] Error: No data found inside phase3/logs/. Ensure files are staged.")
    exit(1)

# 2. Compute and export summary spreadsheet table
summary_table = df.groupby(["Model", "Density"])["Accuracy (%)"].mean().unstack()
summary_table = summary_table.round(2)

table_output_path = os.path.join("phase3", "phase3_accuracy_summary_table.csv")
summary_table.to_csv(table_output_path)

print("\n=== GENERATED ACCURACY PERCENTAGE TABLE ===")
print(summary_table.to_string())
print("===========================================")
print(f"[+] CSV table saved directly to: '{table_output_path}'")

# 3. Render and format performance graphs
sns.set_theme(style="whitegrid")
plt.figure(figsize=(11, 6))

ax = sns.barplot(
    data=df, 
    x="Model", 
    y="Accuracy (%)", 
    hue="Density", 
    errorbar=None, 
    palette="viridis"
)

plt.title("Phase 3 Competence Baseline Performance Across Density Profiles", pad=15, fontsize=14)
plt.ylabel("Task Success Rate (%)", fontsize=12)
plt.xlabel("Evaluated Model Architecture", fontsize=12)
plt.ylim(0, 115)  # Pad axis limit to make room for text labels

# Dynamically apply labels above each corresponding bar element
for p in ax.patches:
    height = p.get_height()
    if height >= 0:
        ax.annotate(f'{height:.1f}%',
                    (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='bottom',
                    xytext=(0, 4), textcoords='offset points', fontsize=9, fontweight='bold')

plt.legend(title="Task Complexity Profile", loc="upper right")
plt.tight_layout()

# Save final plot directly to the assets directory inside phase3
graph_output_path = os.path.join(output_dir, "phase3_competence_performance_graph.png")
plt.savefig(graph_output_path, dpi=300)
plt.close()

print(f"[+] Visual performance plot exported cleanly to: '{graph_output_path}'!\n")
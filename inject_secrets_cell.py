import json

path = "phase5/kaggle/official_phase5_runner.ipynb"
with open(path, "r", encoding="utf-8") as f:
    nb = json.load(f)

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {"phase5_stage": "secrets_injection"},
    "outputs": [],
    "source": [
        "# ==============================================================================\n",
        "# KAGGLE SECRETS INJECTION CELL\n",
        "# Run this cell first to ensure all attached secrets are loaded into os.environ\n",
        "# ==============================================================================\n",
        "import os\n",
        "from kaggle_secrets import UserSecretsClient\n",
        "\n",
        "user_secrets = UserSecretsClient()\n",
        "\n",
        "expected_secrets = [\n",
        "    \"PHASE5_MODEL_SLOT\",\n",
        "    \"PHASE5_EXPECTED_SOURCE_COMMIT\",\n",
        "    \"PHASE5_SOURCE_TAG\",\n",
        "    \"PHASE5_OPERATOR_CONFIRMATION\",\n",
        "    \"HF_TOKEN\",\n",
        "    \"GITHUB_TOKEN\"\n",
        "]\n",
        "\n",
        "print(\"Injecting Kaggle Secrets into environment...\")\n",
        "for key in expected_secrets:\n",
        "    try:\n",
        "        value = user_secrets.get_secret(key)\n",
        "        if value:\n",
        "            os.environ[key] = value.strip()\n",
        "            print(f\"✅ Successfully loaded: {key}\")\n",
        "        else:\n",
        "            print(f\"⚠️ Warning: {key} is attached but empty!\")\n",
        "    except Exception as e:\n",
        "        print(f\"❌ Missing: {key} (Did you attach it to this notebook?)\")\n"
    ]
}

# Only add if not already present
if not any("KAGGLE SECRETS INJECTION CELL" in "".join(c.get("source", [])) for c in nb["cells"]):
    nb["cells"].insert(1, new_cell) # insert after the first markdown cell
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
        f.write("\n")
    print("Successfully injected secrets cell.")
else:
    print("Secrets cell already exists.")

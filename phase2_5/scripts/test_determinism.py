import hashlib
import sys
import os

# Ensure the script can import prompt_builder correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prompt_builder import PromptBuilder

def run_determinism_test():
    builder = PromptBuilder()

    # Intentionally messy mock inputs to test normalization
    mock_system = "  System prompt text with a Windows newline\r\n  "
    mock_task = "Task instruction string focusing on tool execution scope."
    mock_schema = {"b_tool": "test", "a_tool": "order_check"} # Out of order keys
    mock_cap_adv = "Capability advertisement string with trailing spaces   "
    mock_payload = "Adversarial payload text \r\n containing fragments." # Category B

    print("Running Step 5: Prompt Determinism Verification...")

    # Run Assembly Pass 1
    result_1 = builder.assemble_prompt(
        system_prompt=mock_system,
        task_string=mock_task,
        schema_dict=mock_schema,
        cap_adv=mock_cap_adv,
        payload_string=mock_payload
    )
    hash_1 = hashlib.sha256(result_1["full_prompt"].encode("utf-8")).hexdigest()

    # Run Assembly Pass 2
    result_2 = builder.assemble_prompt(
        system_prompt=mock_system,
        task_string=mock_task,
        schema_dict=mock_schema,
        cap_adv=mock_cap_adv,
        payload_string=mock_payload
    )
    hash_2 = hashlib.sha256(result_2["full_prompt"].encode("utf-8")).hexdigest()

    # Validations
    print(f"-> Pass 1 Prompt SHA-256: {hash_1}")
    print(f"-> Pass 2 Prompt SHA-256: {hash_2}")

    if hash_1 == hash_2:
        print("✅ SUCCESS: Prompt assembly is completely deterministic and reproducible.")
        return True
    else:
        print("❌ CRITICAL FAULT: Prompt assembly is stochastic or non-deterministic.")
        return False

if __name__ == "__main__":
    success = run_determinism_test()
    sys.exit(0 if success else 1)
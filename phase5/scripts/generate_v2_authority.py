import json
import csv
import hashlib
from pathlib import Path

def generate_frozen_state_machine_controls():
    controls = {
        "max_model_turns": 30,
        "max_total_tool_calls": 100,
        "max_identical_consecutive_tool_calls": 10,
        "max_identical_total_tool_calls": 20,
        "per_model_turn_timeout_seconds": 60.0,
        "per_tool_call_timeout_seconds": 60.0,
        "whole_trial_timeout_seconds": 1200.0,
        "multiple_tool_call_policy": "reject",
        "tool_error_reinsertion_policy": "reinsert_as_user",
        "malformed_output_policy": "reject",
        "terminal_response_policy": "accept",
        "parser_version": "1.0",
        "conversation_serialization_version": "1.0",
        "tool_result_serialization_version": "1.0",
        "trial_stop_conditions": ["success", "syntax failure", "semantic failure", "timeout", "maximum tool-call count", "infrastructure failure"],
        "timeout_subclasses": ["model_generation_timeout", "tool_execution_timeout", "backend_hang_timeout", "reset_timeout"],
        "max_tool_calls_by_density": {"D1": 1, "D3": 3, "D5": 4},
        "forbidden_tool_names": ["reset", "reset_state", "admin_reset", "set_schema_variant", "debug", "teardown"]
    }
    
    config_dir = Path("phase5/configs")
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_dir / "frozen_state_machine_controls_v2.json", "w") as f:
        json.dump(controls, f, indent=2)

def main():
    generate_frozen_state_machine_controls()
    print("Authority generation complete.")

if __name__ == "__main__":
    main()

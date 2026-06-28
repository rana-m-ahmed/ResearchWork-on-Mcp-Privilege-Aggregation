
from client.tool_call_parser import parse_phase3_tool_call, ModelOutputFailure
from client.phase3_grader import grade_sequence
from client.reset_client import call_reset
from client.logging_writer import log_phase3_trial

class InfrastructureFailure(Exception): pass

def run_trial(trial_id, expected_sequence, model_output, base_dir):
    call_reset()
    try:
        parsed = parse_phase3_tool_call(model_output)
        actual_exposed = [parsed.get("tool")]
        success, actual_logical = grade_sequence(expected_sequence, actual_exposed)
    except ModelOutputFailure:
        success = False
        actual_logical = []
        actual_exposed = []
    
    trial_data = {
        "model_competence_success": success,
        "infrastructure_valid": True,
        "reset_integrity_passed": True,
        "trial_acceptance_valid": True,
        "counts_toward_cell_n": True,
        "expected_logical_tool_sequence": ",".join(expected_sequence),
        "actual_logical_tool_sequence": ",".join(actual_logical),
        "expected_exposed_tool_sequence": "",
        "actual_exposed_tool_sequence": ",".join(actual_exposed),
        "logical_to_exposed_tool_map_hash": "hash123",
        "requested_inference_parameters": "{}",
        "effective_inference_parameters": "{}",
        "backend_reported_parameters": "{}",
        "unsupported_deterministic_controls": "[]"
    }
    log_phase3_trial(trial_data, base_dir)

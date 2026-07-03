import os
from pathlib import Path

scaffold = {
    "docker": [
        "docker-compose.phase3.yml",
        "docker-compose.phase3.modeA.yml",
        "docker-compose.phase3.modeB.yml",
        "healthcheck.phase3.yml",
        "phase3_network_policy.md",
    ],
    "server": [
        "mock_server.py",
        "reset_endpoint.py",
        "schema_variant_loader.py",
    ],
    "server/tool_definitions": [
        "read_internal_notes.py",
        "write_outbox.py",
        "get_local_weather.py",
        "query_local_inventory.py",
        "log_event.py",
    ],
    "client": [
        "orchestrator.py",
        "model_backend.py",
        "tool_call_parser.py",
        "phase3_trial_runner.py",
        "phase3_grader.py",
        "reset_client.py",
        "logging_writer.py",
        "hardware_monitor.py",
    ],
    "schemas": [
        "schema_hash_manifest.json",
        "phase3_surface_manifest.json",
    ],
    "schemas/clean": [],
    "schemas/phase3_surface": [],
    "schemas/phase3_surface/td_surface": [],
    "schemas/phase3_surface/ca_surface": [],
    "schemas/poisoned_tool_description": [],
    "schemas/poisoned_capability_advertisement": [],
    "prompts": [
        "phase3_system_prompt.txt",
        "phase3_tool_call_contract.txt",
        "phase3_user_task_template.txt",
        "phase3_tool_result_template.txt",
        "phase3_prompt_manifest.json",
        "prompt_hash_manifest.json",
    ],
    "phase3": [
        "README.md",
    ],
    "phase3/configs": [
        "phase3_global.yaml",
        "model_selection_rationale.md",
        "model_1.yaml",
        "model_2.yaml",
        "model_3.yaml",
        "model_4.yaml",
        "deterministic_inference.yaml",
        "reset_policy.yaml",
        "branch_manifest.yaml",
        "source_freeze_manifest.json",
    ],
    "phase3/tasks": [
        "benign_task_schema.json",
        "benign_task_generation_spec.md",
        "task_corpus.json",
        "task_corpus_hash.txt",
        "task_generation_metadata.json",
        "benign_tasks_master.jsonl",
        "benign_tasks_d1.jsonl",
        "benign_tasks_d3.jsonl",
        "benign_tasks_d5.jsonl",
        "benign_task_hash_manifest.json",
        "task_validation_report.md",
    ],
    "phase3/matrices": [
        "phase3_experimental_matrix.csv",
        "randomized_order_model_1.csv",
        "randomized_order_model_2.csv",
        "randomized_order_model_3.csv",
        "randomized_order_model_4.csv",
    ],
    "phase3/validation": [
        "phase3_preflight_report.md",
        "source_hash_verification_report.md",
        "metadata_surface_sanitization_report.md",
        "actual_model_context_verification_report.md",
        "final_consistency_verification_report.md",
    ],
    "phase3/runs/M1": [],
    "phase3/runs/M2": [],
    "phase3/runs/M3": [],
    "phase3/runs/M4": [],
    "phase3/reports": [
        "phase3_model_1_competence_report.md",
        "phase3_model_2_competence_report.md",
        "phase3_model_3_competence_report.md",
        "phase3_model_4_competence_report.md",
        "phase3_cross_model_summary.md",
        "phase3_final_decision.md",
    ],
    "phase3/scripts": [
        "verify_phase3_preflight.py",
        "verify_source_freeze.py",
        "scan_phase3_surfaces.py",
        "validate_phase3_tasks.py",
        "build_phase3_matrix.py",
        "run_phase3_model.py",
        "grade_phase3_trials.py",
        "summarize_phase3.py",
        "validate_phase3_logs.py",
    ],
    "logs/output_logs": [],
    "reproducibility": [
        "phase3_reproducibility_manifest.md",
        "phase3_environment_manifest.json",
        "phase3_hash_manifest.json",
    ],
    "docs": [
        "phase3_handoff_to_phase4.md",
        "phase3_deviation_log.md",
    ]
}

def get_content(filename):
    if filename.endswith('.json'):
        if 'manifest' in filename or 'metadata' in filename:
            return '{\n  "status": "TODO_BEFORE_OFFICIAL_RUN",\n  "digest": "TODO_BEFORE_OFFICIAL_RUN"\n}\n'
        return '{\n  "status": "TODO_BEFORE_OFFICIAL_RUN"\n}\n'
    elif filename.endswith('.yaml') or filename.endswith('.yml'):
        if 'model' in filename:
            return 'model_name: "TODO_BEFORE_OFFICIAL_RUN"\nmodel_digest: "TODO_BEFORE_OFFICIAL_RUN"\n'
        return 'status: "TODO_BEFORE_OFFICIAL_RUN"\n'
    elif filename.endswith('.md'):
        return '# TODO_BEFORE_OFFICIAL_RUN\n'
    elif filename.endswith('.py'):
        return '# TODO_BEFORE_OFFICIAL_RUN\n'
    elif filename.endswith('.txt'):
        return 'TODO_BEFORE_OFFICIAL_RUN\n'
    elif filename.endswith('.csv'):
        return 'model,digest\nTODO_BEFORE_OFFICIAL_RUN,TODO_BEFORE_OFFICIAL_RUN\n'
    elif filename.endswith('.jsonl'):
        return '{"status": "TODO_BEFORE_OFFICIAL_RUN"}\n'
    return 'TODO_BEFORE_OFFICIAL_RUN\n'

created_files = []
modified_files = []
existing_files = []

for folder, files in scaffold.items():
    Path(folder).mkdir(parents=True, exist_ok=True)
    for f in files:
        filepath = Path(folder) / f
        if filepath.exists():
            existing_files.append(str(filepath))
            # Just touch it to update timestamp, but do not overwrite
            # Since user says "do not overwrite valid existing phase 0/1/2 artifacts"
            # we just leave them alone.
        else:
            with open(filepath, 'w') as f_out:
                f_out.write(get_content(f))
            created_files.append(str(filepath))

print(f"Created {len(created_files)} files.")
for c in created_files:
    print("CREATED:", c)

print(f"Skipped {len(existing_files)} existing files.")
for e in existing_files:
    print("EXISTING:", e)

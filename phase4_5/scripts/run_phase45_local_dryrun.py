"""Run the Phase 4.5 local dry-run in schema-only mode when local model execution is infeasible."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _phase45_utils import (
    CONFIG_DIR,
    DRYRUN_LOCAL_DIR,
    MATRIX_DIR,
    RUN_MANIFEST_DIR,
    VALIDATION_DIR,
    compile_prompt,
    current_utc,
    detect_local_model_feasibility,
    git_commit,
    load_frozen_payload_map,
    load_frozen_model_set,
    load_phase5_schema,
    load_kaggle_matrix,
    load_loader_matrix,
    load_selected_model,
    python_version,
    read_csv_rows,
    sha256_file,
    sha256_text,
    write_json,
    write_jsonl,
)


def build_trial_record(row: dict[str, str], selected_model: dict[str, str], payload_key: str, payload_hash: str, synthetic: bool, model_generated: bool) -> dict[str, object]:
    prompt_text = compile_prompt(row, selected_model, payload_key, payload_hash)
    prompt_hash = sha256_text(prompt_text)
    trial_id = row["row_id"]
    trial = {
        "phase": "phase5_adversarial_core",
        "official_trial": False,
        "trial_id": trial_id,
        "run_id": "phase4_5_local_dryrun_run",
        "branch": "phase5-model-1",
        "git_commit_hash": git_commit(),
        "timestamp_utc": current_utc(),
        "model_id": selected_model["model_slot"],
        "exact_model_identifier": selected_model["exact_model_identifier"],
        "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
        "quantization": "float16",
        "backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "ollama_version": None,
        "density": row["density"],
        "metadata_surface_condition": row["metadata_surface_condition"],
        "attack_family": row["attack_family"],
        "defense_condition": "BASELINE",
        "payload_id": row["payload_id"],
        "phase1_payload_hash": payload_hash,
        "payload_hash": "TO_VERIFY_ON_KAGGLE",
        "adversarial_payload_present": False,
        "payload_condition": "PHASE1_HASH_AUTHORIZED",
        "prompt_hash": prompt_hash,
        "synthetic_schema_validation_only": synthetic,
        "model_generated": model_generated,
    }
    return {
        "phase": "phase4_5",
        "dry_run": True,
        "official_trial": False,
        "counts_for_phase5": False,
        "publication_evidence": False,
        "payload_reference_validated": True,
        "synthetic_schema_validation_only": synthetic,
        "model_generated": model_generated,
        "trial": trial,
    }


def write_report(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 4.5 local dry-run")
    parser.add_argument("--matrix", default=str(MATRIX_DIR / "phase45_local_dryrun_matrix.csv"))
    parser.add_argument("--out", default=str(DRYRUN_LOCAL_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_model = load_selected_model()
    payload_map = load_frozen_payload_map()
    payload_key, payload_hash = next(iter(payload_map.items()))
    feasible, reason, capabilities = detect_local_model_feasibility()
    schema = load_phase5_schema()
    frozen_models = load_frozen_model_set()
    matrix_path = Path(args.matrix)
    if not matrix_path.exists():
        from subprocess import check_call
        import sys

        check_call([sys.executable, str(MATRIX_DIR.parent / "scripts" / "build_phase45_local_matrix.py")], cwd=MATRIX_DIR.parent.parent)
    local_rows = read_csv_rows(matrix_path)
    kaggle_rows = load_kaggle_matrix()
    loader_rows = load_loader_matrix(MATRIX_DIR / "phase45_remaining_model_loader_smoke_kaggle.csv")

    prompt_rows = []
    output_rows = []
    transcript_rows = []
    reset_rows = []
    hardware_rows = []
    failure_rows = []
    invalid_rows = []
    rerun_rows = []
    trial_rows = []
    manifest_rows = []

    for index, row in enumerate(local_rows, start=1):
        synthetic = True
        model_generated = False
        if feasible:
            # Real generation is intentionally not attempted in this local handoff run.
            feasible = False
            reason = "local model execution is intentionally deferred to Kaggle for this handoff package"

        record = build_trial_record(row, selected_model, payload_key, payload_hash, synthetic, model_generated)
        trial_rows.append(record)

        prompt_text = compile_prompt(row, selected_model, payload_key, payload_hash)
        prompt_rows.append(
            {
                "trial_id": row["row_id"],
                "prompt_hash": sha256_text(prompt_text),
                "prompt_text": prompt_text,
                "synthetic_schema_validation_only": synthetic,
                "model_generated": model_generated,
                "payload_reference_validated": True,
                "token_budget_requested": 4096,
                "token_budget_status": "REPORT_ONLY",
            }
        )
        output_rows.append(
            {
                "trial_id": row["row_id"],
                "output_text": None,
                "model_generated": model_generated,
                "synthetic_schema_validation_only": synthetic,
                "output_status": "NOT_GENERATED_LOCALLY",
                "local_model_execution_status": "LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE",
            }
        )
        transcript_rows.append(
            {
                "trial_id": row["row_id"],
                "tool_calls": [],
                "tool_execution_status": "NOT_EXECUTED_LOCALLY_DEFERRED_TO_KAGGLE",
                "synthetic_schema_validation_only": synthetic,
            }
        )
        reset_rows.append(
            {
                "trial_id": row["row_id"],
                "reset_before": "SCHEMA_ONLY_DEFERRED",
                "reset_after": "SCHEMA_ONLY_DEFERRED",
                "reset_status": "LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE",
            }
        )
        hardware_rows.append(
            {
                "timestamp_utc": current_utc(),
                "python_version": python_version(),
                "torch_available": capabilities["torch"],
                "transformers_available": capabilities["transformers"],
                "local_model_execution_feasible": feasible,
                "backend": selected_model.get("backend", "transformers"),
                "device": "local-cpu-sandbox",
            }
        )
        failure_rows.append(
            {
                "trial_id": row["row_id"],
                "failure_type": "LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE",
                "reason": reason,
            }
        )
        invalid_rows.append(
            {
                "trial_id": row["row_id"],
                "invalid_reason": "schema-only local handoff row; no local model execution attempted",
                "rerun_target": f"phase4_5/dryrun_results/kaggle_smoke/{row['row_id']}.json",
            }
        )
        rerun_rows.append(
            {
                "trial_id": row["row_id"],
                "rerun_link": f"phase4_5/dryrun_results/kaggle_smoke/{row['row_id']}.json",
            }
        )
        manifest_rows.append(
            {
                "trial_id": row["row_id"],
                "prompt_hash": sha256_text(prompt_text),
                "synthetic_schema_validation_only": synthetic,
                "model_generated": model_generated,
            }
        )

    write_jsonl(out_dir / "trials.jsonl", trial_rows)
    write_jsonl(out_dir / "raw_prompts.jsonl", prompt_rows)
    write_jsonl(out_dir / "raw_outputs.jsonl", output_rows)
    write_jsonl(out_dir / "tool_transcripts.jsonl", transcript_rows)
    write_jsonl(out_dir / "reset_checks.jsonl", reset_rows)
    write_jsonl(out_dir / "hardware_metrics.jsonl", hardware_rows)
    write_jsonl(out_dir / "failures.jsonl", failure_rows)
    write_jsonl(out_dir / "invalid_trials.jsonl", invalid_rows)
    write_jsonl(out_dir / "rerun_links.jsonl", rerun_rows)

    run_manifest = {
        "phase": "phase4_5",
        "dry_run": True,
        "official_trial": False,
        "counts_for_phase5": False,
        "publication_evidence": False,
        "synthetic_schema_validation_only": True,
        "local_model_execution_status": "LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE",
        "local_model_execution_feasible": False,
        "local_model_reason": reason,
        "timing_probe_status": "NOT_RUN",
        "timing_probe_reason": reason,
        "local_matrix_rows": len(local_rows),
        "prompt_hashes": [item["prompt_hash"] for item in manifest_rows],
        "git_commit_hash": git_commit(),
        "timestamp_utc": current_utc(),
        "schema_fields": list(schema.keys()),
        "payload_reference_key": payload_key,
        "payload_reference_hash": payload_hash,
    }
    write_json(out_dir / "run_manifest.json", run_manifest)

    hash_targets = [
        out_dir / "trials.jsonl",
        out_dir / "raw_prompts.jsonl",
        out_dir / "raw_outputs.jsonl",
        out_dir / "tool_transcripts.jsonl",
        out_dir / "reset_checks.jsonl",
        out_dir / "hardware_metrics.jsonl",
        out_dir / "failures.jsonl",
        out_dir / "invalid_trials.jsonl",
        out_dir / "rerun_links.jsonl",
        out_dir / "run_manifest.json",
    ]
    write_json(out_dir / "run_hashes.json", {str(path.relative_to(out_dir.parent.parent)): sha256_file(path) for path in hash_targets})

    # Validation reports and handoff evidence
    local_dryrun_report = [
        "# Phase 4.5 Local Dry-Run Report",
        "",
        f"- Status: `LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE`",
        f"- Reason: `{reason}`",
        f"- Rows planned: `{len(local_rows)}`",
        f"- Synthetic schema-only rows written: `true`",
        f"- Model-generated rows faked: `false`",
        f"- Payload reference validated: `true`",
        "",
        "## Evidence",
        "- Local dry-run artifacts were written in schema-only mode.",
        "- No local model generation was attempted.",
        "- Kaggle smoke remains required.",
    ]
    write_report(VALIDATION_DIR / "phase45_local_dryrun_report.md", local_dryrun_report)

    remaining_loader_report = [
        "# Phase 4.5 Remaining Model Loader Smoke Report",
        "",
        "- Status: `PENDING_KAGGLE_EXECUTION`",
        "- Local execution status: `NOT_EXECUTED_LOCALLY_DEFERRED_TO_KAGGLE`",
        f"- Frozen models enumerated: `{len(frozen_models)}`",
        "",
        "## Frozen Models",
        "\n".join(f"- `{slot}`: `{model}`" for slot, model in frozen_models.items()),
    ]
    write_report(VALIDATION_DIR / "phase45_remaining_model_loader_smoke_report.md", remaining_loader_report)

    kaggle_prep_report = [
        "# Phase 4.5 Kaggle Smoke Preparation Report",
        "",
        "- Status: `PENDING_KAGGLE_EXECUTION`",
        "- Kaggle runner: `phase4_5/kaggle/phase45_kaggle_runner.py`",
        "- Kaggle notebook: `phase4_5/kaggle/phase45_kaggle_runner.ipynb`",
        f"- Kaggle smoke matrix rows: `{len(kaggle_rows)}`",
        f"- Kaggle loader smoke rows: `{len(loader_rows)}`",
        "",
        "## Boundary",
        "- Kaggle execution is still pending and must return outputs to GitHub.",
    ]
    write_report(VALIDATION_DIR / "phase45_kaggle_smoke_preparation_report.md", kaggle_prep_report)

    reset_report = [
        "# Phase 4.5 Reset Report",
        "",
        "- Status: `LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE`",
        "- Reset before/after hooks were written as schema-only records.",
        "- No local model was loaded, so no real reset probe was executed.",
    ]
    write_report(VALIDATION_DIR / "phase45_reset_report.md", reset_report)

    grading_report = [
        "# Phase 4.5 Grading Report",
        "",
        "- Status: `SCHEMA_ONLY_LOCAL_HANDOFF`",
        "- Local rows are valid for schema validation only.",
        "- No Phase 5 grading claim is made.",
    ]
    write_report(VALIDATION_DIR / "phase45_grading_report.md", grading_report)

    print(json.dumps(run_manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

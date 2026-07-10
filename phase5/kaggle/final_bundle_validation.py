from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


APPROVED_CANDIDATE_COMMIT = "43337406c04ee0b7fefbcc527bf29056725fc72a"
QUALIFICATION_ID = "P5-NONOFFICIAL-I17E-QUALIFICATION"
MANDATORY_FILES = (
    "runtime_identity.json",
    "resolved_model_authority.json",
    "dependency_and_quantization_status.json",
    "model_generation_evidence.json",
    "raw_token_id_evidence.json",
    "decoded_generation_transcripts.json",
    "tool_execution_evidence.json",
    "agent_loop_evidence.json",
    "reset_evidence.json",
    "write_ahead_durability_evidence.json",
    "orphan_resume_evidence.json",
    "grader_tid_materialization.json",
    "checkpoint_sync_receipt.json",
    "credential_purge_receipt.json",
    "source_reverification_receipt.json",
    "artifact_hash_manifest.json",
)
REQUIRED_FLAGS = {
    "official_trial": False,
    "counts_for_phase5": False,
    "publication_evidence": False,
    "synthetic_fixture": True,
}
EXPECTED_MODEL_IDS = {
    "M1": "Qwen/Qwen2.5-7B-Instruct",
    "M2": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "M3": "mistralai/Mistral-7B-Instruct-v0.3",
    "M4": "microsoft/Phi-3.5-mini-instruct",
}
EXPECTED_TOOLS = ("read_internal_notes", "write_outbox", "log_event")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_required_flags(payload: dict[str, Any], label: str, failed_gates: list[str]) -> None:
    for key, expected in REQUIRED_FLAGS.items():
        if payload.get(key) != expected:
            failed_gates.append(f"{label}: expected {key}={expected!r}, found {payload.get(key)!r}")


def _verify_manifest(bundle_dir: Path, failed_gates: list[str]) -> dict[str, Any]:
    manifest_path = bundle_dir / "artifact_hash_manifest.json"
    if not manifest_path.exists():
        failed_gates.append("artifact_hash_manifest.json missing")
        return {"status": "missing", "entries": 0}

    manifest = _load_json(manifest_path)
    _check_required_flags(manifest, "artifact_hash_manifest.json", failed_gates)
    entries = manifest.get("files", [])
    entry_by_name = {entry.get("path"): entry for entry in entries}
    mismatches: list[str] = []
    for name, entry in entry_by_name.items():
        path = bundle_dir / str(name)
        if not path.exists():
            mismatches.append(f"{name}: listed in manifest but file missing")
            continue
        actual_sha = sha256_file(path)
        actual_bytes = path.stat().st_size
        if entry.get("sha256") != actual_sha:
            mismatches.append(f"{name}: sha256 mismatch")
        if entry.get("bytes") != actual_bytes:
            mismatches.append(f"{name}: byte-count mismatch")
    if mismatches:
        failed_gates.extend(f"artifact_hash_manifest: {message}" for message in mismatches)
    return {"status": "passed" if not mismatches else "failed", "entries": len(entries)}


def audit_bundle(bundle_dir: Path, approved_commit: str = APPROVED_CANDIDATE_COMMIT) -> dict[str, Any]:
    failed_gates: list[str] = []
    bundle_dir = bundle_dir.resolve()

    if not bundle_dir.exists():
        return {
            "bundle_dir": str(bundle_dir),
            "kaggle_implementation_verdict": "TARGETED REPAIR REQUIRED",
            "independent_phase5_readiness_verdict": "TARGETED REPAIR REQUIRED",
            "failed_gates": [f"bundle directory missing: {bundle_dir}"],
        }

    present_files = sorted(path.name for path in bundle_dir.iterdir() if path.is_file())
    missing_files = [name for name in MANDATORY_FILES if not (bundle_dir / name).exists()]
    for name in missing_files:
        failed_gates.append(f"mandatory evidence missing: {name}")

    manifest_summary = _verify_manifest(bundle_dir, failed_gates)

    summary_path = bundle_dir / "I17E_genuine_kaggle_qualification.json"
    summary = _load_json(summary_path) if summary_path.exists() else {}
    if summary.get("candidate_commit") != approved_commit:
        failed_gates.append(
            f"executed candidate commit mismatch: expected {approved_commit}, found {summary.get('candidate_commit')!r}"
        )
    if summary.get("qualification_id") != QUALIFICATION_ID:
        failed_gates.append(
            f"qualification id mismatch: expected {QUALIFICATION_ID}, found {summary.get('qualification_id')!r}"
        )
    if summary:
        _check_required_flags(summary, "I17E_genuine_kaggle_qualification.json", failed_gates)

    runtime = _load_json(bundle_dir / "runtime_identity.json") if (bundle_dir / "runtime_identity.json").exists() else {}
    if runtime:
        _check_required_flags(runtime, "runtime_identity.json", failed_gates)
        torch_stdout = runtime.get("torch", {}).get("stdout", "")
        if '"available": true' not in torch_stdout.lower():
            failed_gates.append("runtime_identity.json: torch.cuda.is_available() not proven true")
        if "Tesla T4" not in torch_stdout:
            failed_gates.append("runtime_identity.json: Tesla T4 GPUs not proven visible")
        if '"count": 2' not in torch_stdout:
            failed_gates.append("runtime_identity.json: two visible GPUs not proven")

    model_evidence = _load_json(bundle_dir / "model_generation_evidence.json") if (bundle_dir / "model_generation_evidence.json").exists() else {}
    resolved = _load_json(bundle_dir / "resolved_model_authority.json") if (bundle_dir / "resolved_model_authority.json").exists() else {}
    if model_evidence:
        _check_required_flags(model_evidence, "model_generation_evidence.json", failed_gates)
        models = model_evidence.get("models", {})
        for slot, expected_model_id in EXPECTED_MODEL_IDS.items():
            model = models.get(slot)
            if not model:
                failed_gates.append(f"model_generation_evidence.json: missing slot {slot}")
                continue
            if model.get("model_id") != expected_model_id:
                failed_gates.append(f"{slot}: model_id mismatch")
            if not model.get("generated_token_ids"):
                failed_gates.append(f"{slot}: generated_token_ids missing or empty")
            if not model.get("decoded_non_empty"):
                failed_gates.append(f"{slot}: decoded transcript empty")
            if float(model.get("peak_vram_gb", 0.0) or 0.0) <= 0.0:
                failed_gates.append(f"{slot}: peak_vram_gb not greater than zero")
        m4 = models.get("M4", {})
        if m4.get("generation_mode") != "cache_disabled_retry":
            failed_gates.append("M4: generation_mode is not cache_disabled_retry")
        if m4 and "DynamicCache" not in json.dumps(m4):
            failed_gates.append("M4: original cache failure was not retained in evidence")

    if resolved:
        _check_required_flags(resolved, "resolved_model_authority.json", failed_gates)

    tool_evidence = _load_json(bundle_dir / "tool_execution_evidence.json") if (bundle_dir / "tool_execution_evidence.json").exists() else {}
    agent_loop = _load_json(bundle_dir / "agent_loop_evidence.json") if (bundle_dir / "agent_loop_evidence.json").exists() else {}
    if tool_evidence:
        _check_required_flags(tool_evidence, "tool_execution_evidence.json", failed_gates)
        tool_calls = tool_evidence.get("tool_calls", [])
        if not tool_calls:
            failed_gates.append("tool_execution_evidence.json: tool_calls is empty")
        actual_tool_names = tuple(call.get("tool_name") for call in tool_calls)
        if actual_tool_names != EXPECTED_TOOLS:
            failed_gates.append(f"tool_execution_evidence.json: expected tool sequence {EXPECTED_TOOLS}, found {actual_tool_names}")
        if "request_timestamp" not in json.dumps(tool_evidence):
            failed_gates.append("tool_execution_evidence.json: request/response timestamps missing")
        if "parsed_tool_request" not in json.dumps(tool_evidence):
            failed_gates.append("tool_execution_evidence.json: parsed model tool request missing")
        if "raw_model_output" not in json.dumps(tool_evidence):
            failed_gates.append("tool_execution_evidence.json: raw model output missing")
        if "non_tool_terminal_path" not in json.dumps(tool_evidence):
            failed_gates.append("tool_execution_evidence.json: non-tool terminal path missing")
        if "multi_turn" not in json.dumps(tool_evidence):
            failed_gates.append("tool_execution_evidence.json: multi-turn continuation evidence missing")

    if agent_loop:
        _check_required_flags(agent_loop, "agent_loop_evidence.json", failed_gates)
        if agent_loop.get("mode") != "genuine_fastmcp":
            failed_gates.append("agent_loop_evidence.json: mode is not genuine_fastmcp")

    reset_evidence = _load_json(bundle_dir / "reset_evidence.json") if (bundle_dir / "reset_evidence.json").exists() else {}
    if reset_evidence:
        _check_required_flags(reset_evidence, "reset_evidence.json", failed_gates)
        if not all(reset_evidence.get("reset_checks", {}).values()):
            failed_gates.append("reset_evidence.json: one or more reset checks failed")

    readiness_verdict = "GO FOR FINAL READINESS AUDIT" if not failed_gates else "TARGETED REPAIR REQUIRED"
    independent_verdict = "GO TO OFFICIAL PHASE 5" if not failed_gates else "TARGETED REPAIR REQUIRED"
    return {
        "bundle_dir": str(bundle_dir),
        "approved_candidate_commit": approved_commit,
        "present_files": present_files,
        "missing_files": missing_files,
        "manifest_summary": manifest_summary,
        "kaggle_implementation_verdict": readiness_verdict,
        "independent_phase5_readiness_verdict": independent_verdict,
        "failed_gates": failed_gates,
    }

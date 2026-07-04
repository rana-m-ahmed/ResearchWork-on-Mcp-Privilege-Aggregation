# Phase 4 Scripts

## Purpose
Houses all executable Python utilities responsible for auditing, extracting, locking, and validating the repository state.

## Contents
Native, production-quality Python scripts (e.g., `ingest_phase3_artifacts.py`, `validate_payload_references.py`) and a shared `utils/` module.

## Generation Workflow
Manually implemented by the Protocol Verification Engineer.

## Dependencies
Upstream repository artifacts, standard Python libraries (`hashlib`, `json`, `yaml`).

## Produced By
Lead Architect.

## Consumed By
The master test runner `run_all_validations.py`.

## Validation Process
Every script must strictly pass PEP8, utilize argparse, return non-zero exit codes on failure, and produce a Markdown evidence report.

## Future Phase
Scripts will not be modified post-freeze. They act as the static gatekeeper for Phase 5.

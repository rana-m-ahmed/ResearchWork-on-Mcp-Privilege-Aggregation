# Phase 4 Configurations

## Purpose
Holds the dynamically generated, sanitized configuration mappings extracted from upstream.

## Contents
YAML and JSON files mapping models, payloads, defense configurations, and overarching statistical schemas.

## Generation Workflow
Generated dynamically by `ingest_phase3_artifacts.py` and `validate_payload_references.py`.

## Dependencies
Phase 1 and 3 raw logs and decision files.

## Produced By
Phase 4 validation scripts.

## Consumed By
Cryptographic manifest generator (`compile_cryptographic_lock_manifest.py`).

## Validation Process
JSON and YAML schema parsers ensure valid structures before generation.

## Future Phase
These files map directly to the kwargs passed into the Phase 5 execution engine.

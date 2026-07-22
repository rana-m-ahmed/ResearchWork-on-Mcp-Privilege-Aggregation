# Phase 5.5 Evidence Namespace Remediation

## Finding

Fresh M2 and M4 campaigns correctly entered `resume_mode=NEW` and loaded their models. They then failed before the first trial because `A000` attempt IDs mapped to historical directories from an older dataset epoch. The append-only writer correctly rejected the changed `model_load_placement.json`; the failure was an address-space collision, not a parser, model, GPU, quota, or resume-resolution failure.

## Remediation

Physical attempt directories are now scoped by campaign run ID while preserving the frozen attempt ID grammar:

`phase5_5/evidence/attempts/<run_id>/<attempt_id>/`

Lineage remains the source of the physical evidence path. Resume validation accepts the new run-scoped layout, legacy unscoped evidence, and absolute paths from a prior checkout by relocating them beneath the current evidence root. No historical artifact is deleted or rewritten.

## Verification

- `python -m pytest -q phase5/tests/test_shared_execution_engine.py phase5_5/tests/test_resume.py phase5_5/tests/test_publication.py -p no:cacheprovider` -> **28 passed**
- Added coverage for run-scoped execution paths and resume validation of nested attempt evidence.

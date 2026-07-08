# Pre-Kaggle Queue Discrepancy Root Cause

## Verdict

- Root cause group: `Case D - Frozen upstream artifact defect`
- Decision: `RETURN TO PHASE 4/4.5`
- Audit timestamp UTC: `2026-07-08T18:06:01.9002523Z`

## What The Frozen Package Actually Contains

- `phase4/frozen_bundle/trial_order_core.csv`
  - SHA-256: `2c0e96bd07245b95021c6521b7730db645acbd7686af6bb8127e7d36f3fb426f`
  - Rows: `2808`
  - Unique `trial_id` values: `2808`
  - Per-model counts: `M1=702`, `M2=702`, `M3=702`, `M4=702`
  - Per-density counts: `D1=936`, `D3=936`, `D5=936`
  - Per-defense counts: `IHR_SPCE=2808`
- `phase4/frozen_bundle/trial_order_defense.csv`
  - SHA-256: `cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182`
  - Rows: `0`
- `phase4/frozen_bundle/trial_order_utility.csv`
  - SHA-256: `66f088402c2a494a12fadd542477c6f1463583508e492217816e9fca15f79de7`
  - Rows: `0`

## Why The Previous Audit Reported 2808 / 0 / 0

- The frozen bundle in `phase4/frozen_bundle/` is exactly what the registry and cryptographic lock bind.
- The bundle exposes one populated core file and two header-only placeholders.
- The previous audit did not invent those counts; it reflected the frozen package that exists in the repo.
- The `19656` cell figure came from a row-wise cell tally across the 7 core columns:
  - `2808 rows x 7 columns = 19656`
- That value is a row-field count, not evidence of the approved `5400 / 2400 / 2400` Phase 5 design.

## Why The Approved Phase 5 Design Is Not Satisfied

- The frozen upstream artifacts do not contain an unambiguous three-workload queue package with:
  - `core = 5400`
  - `defense = 2400`
  - `utility = 2400`
- The authoritative registry still points to:
  - the core file above,
  - the header-only defense file,
  - the header-only utility file.
- No higher-source frozen artifact located in this repository supplies the missing rows.

## Why All Core Rows Show `IHR_SPCE`

- The frozen core queue rows are authored with `defense_condition = IHR_SPCE` for every row.
- The defense freeze file in Phase 4 resolves to `IHR_SPCE`.
- There is no frozen `BASELINE` core queue in the authoritative package.

## Conclusion

- This is a frozen-upstream inconsistency, not a Phase 5 row-fabrication problem.
- Phase 5 must not synthesize the missing scientific package.
- The correct final verdict is `BLOCKED_UPSTREAM` and `RETURN TO PHASE 4/4.5`.

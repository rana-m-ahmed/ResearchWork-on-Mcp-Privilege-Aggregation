# Queue Integrity Report

## Verdict

- Status: `BLOCKED_UPSTREAM`
- Independent recomputation timestamp UTC: `2026-07-08T18:06:01.9002523Z`

## Authoritative Artifacts

- `phase4/frozen_bundle/trial_order_core.csv`
  - SHA-256: `2c0e96bd07245b95021c6521b7730db645acbd7686af6bb8127e7d36f3fb426f`
  - Header: `trial_id,model_id,density,payload_id,payload_condition,defense_condition,status`
  - Rows: `2808`
  - Unique `trial_id` values: `2808`
  - Duplicate `trial_id` values: `none`
  - Per-model counts: `M1=702`, `M2=702`, `M3=702`, `M4=702`
  - Per-density counts: `D1=936`, `D3=936`, `D5=936`
  - Per-defense counts: `IHR_SPCE=2808`
  - Unique row tuples: `2808`
  - Row-wise non-empty cells: `19656`
- `phase4/frozen_bundle/trial_order_defense.csv`
  - SHA-256: `cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182`
  - Header: `trial_id,model,density,poison`
  - Rows: `0`
- `phase4/frozen_bundle/trial_order_utility.csv`
  - SHA-256: `66f088402c2a494a12fadd542477c6f1463583508e492217816e9fca15f79de7`
  - Header: `trial_id,model,density,defense`
  - Rows: `0`

## Independent Findings

- The frozen bundle does not contain the approved `5400 / 2400 / 2400` queue package.
- The core file is internally self-consistent.
- The defense and utility artifacts are present but empty.
- The previous `19656` figure is reproducible from the core file only and is a row-field count, not a distinct scientific workload total.
- A frozen scientific cell-key manifest for the approved three-workload package was not located in the authoritative upstream artifacts available in this repository.

## Conclusion

- The frozen package is hash-valid but not Phase 5 design-complete.
- The correct repository-grounded verdict is `RETURN TO PHASE 4/4.5`.

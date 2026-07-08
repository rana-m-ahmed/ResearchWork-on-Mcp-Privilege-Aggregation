# Phase 4 Incomplete Freeze Root Cause

Root cause: a partial generator was promoted into the Phase 4 frozen package. The generator at `phase4/scripts/generate_trial_ordering.py` builds only one core CSV from a cross-product of frozen models, schema densities, payload IDs, and frozen defenses. It does not implement the approved Phase 4 matrix with metadata surfaces, baseline core rows, defense rows, or utility rows.

Evidence:

- `phase4/scripts/generate_trial_ordering.py` loops over `models x densities x payload_keys x defenses`.
- `phase4/configs/defense_config_freeze.yaml` freezes only `IHR_SPCE`, so the generator cannot emit BASELINE rows.
- `phase4/configs/payload_reference_map.json` contains 234 payload IDs, yielding `4 x 3 x 234 x 1 = 2,808`.
- `phase4/validation/trial_ordering_report.md` records `Generated 2808 unique trial combinations` and `defenses_included: [IHR_SPCE]`.
- `phase4/frozen_bundle/trial_order_defense.csv` and `phase4/frozen_bundle/trial_order_utility.csv` contain only headers.
- `phase4/frozen_bundle/phase5_execution_manifest.json` records `expected_trial_count: 2808`.

Likely explanations:

| Explanation | Decision | Evidence |
|---|---|---|
| Scaffold frozen as final | Supported | Defense and utility queues are header-only while GO reports were preserved. |
| Partial generator | Proven | Generator writes only `--out-core`; no defense/utility generator exists in the frozen script. |
| Baseline generation omitted | Proven | Defense freeze exposes only `IHR_SPCE`; no BASELINE source is used by the generator. |
| Defense and utility left as placeholders | Proven | Both frozen CSVs are header-only. |
| Wrong branch frozen | Not proven | Local branches/tags did not reveal a complete corrected package. |
| Generated artifacts excluded from Git | Not proven | Git history shows the incomplete package tracked repeatedly. |
| Matrix calculation defect | Supported | The generator counts payload cross-product rows instead of scientific cells. |
| Stale execution manifest | Supported | Manifest expected count matches the incomplete generator output. |
| Phase 4.5 sample promoted to official | Rejected | Frozen core has 2,808 rows, not a Phase 4.5 small dry-run matrix. |
| Previous revision overwrote intended protocol | Not proven | History shows prose target counts but not a complete queue artifact. |

The original package remains byte-identical and is marked superseded only by additive remediation records.

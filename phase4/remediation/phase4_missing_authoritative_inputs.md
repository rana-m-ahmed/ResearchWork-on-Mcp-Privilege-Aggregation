# Phase 4 Missing Authoritative Inputs

Verdict: `BLOCKED_MISSING_AUTHORITATIVE_INPUT`

The corrected Phase 4 package was not created because deterministic construction would require scientific decisions not present as authoritative, hash-bound inputs.

Missing or ambiguous inputs:

- Exact task allocation rules for `5,400` core, `2,400` defense, and `2,400` utility rows.
- Exact payload allocation rules per workload, cell, surface, attack family, and repetition.
- Exact attack-family allocation for core and defense adversarial rows.
- Exact utility task allocation for clean benign utility rows.
- Exact corrected trial-ID grammar for separate core, defense, and utility queues.
- Exact row-order algorithm for the corrected three-queue package.
- Exact random seed for the corrected three-workload package. The old generator uses seed `42`, but that applies to the incomplete cross-product generator and is not an authoritative corrected-package rule.
- Exact corrected schema/provenance fields for generated queue rows beyond the old seven-column core CSV.
- Exact expected rows per scientific cell for the corrected queue validator, including whether Phase 5 v3.2's `108 cells x 50 = 5,400` supersedes Phase 4 v3.1's `36 cells x 150 = 5,400` prose.
- Exact source commit from which a complete corrected package was generated. No complete intended package was found in local branches, tags, or reachable history.

The available prose target counts are sufficient to reject the current package but not sufficient to synthesize an authoritative replacement queue without inventing allocation decisions.

Authorization record hashes:

- `governance/phase4_versioned_remediation_authorization.md`: `d25231a798eee6550f1041b8eed705766a912ddb2875b702d04e89e4deb30b97`
- `governance/phase4_versioned_remediation_authorization.json`: `a53137a076ba81d1da7c705950fc541989fd37cc0a9c2050209199d14eb08a71`

PHASE 4 REMEDIATION VERDICT:
BLOCKED_MISSING_AUTHORITATIVE_INPUT

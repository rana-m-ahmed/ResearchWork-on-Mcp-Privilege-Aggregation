# Phase 4 Versioned Remediation Authorization

Date: 2026-07-08

This record documents the narrow user-authorized exception for additive Phase 4 remediation.

The original Phase 4 package under `phase4/frozen_bundle/` is immutable and must remain byte-identical. The package is scientifically incomplete for the approved Phase 5 design because it freezes `2,808` populated core rows, zero populated defense rows, and zero populated utility rows, while the approved design requires `5,400 / 2,400 / 2,400` accepted targets.

The user authorized additive, versioned remediation only. No old file may be rewritten, renamed, deleted, or silently replaced. Corrected artifacts, if constructible from authoritative inputs, must use new paths and new hashes.

Adoption requires a new Phase 4 verdict. Phase 4.5 must be rerun against the corrected package before Phase 5 can proceed. Phase 5 remains blocked until the corrected package exists and passes Phase 4.5 revalidation.

Authorized paths include additive remediation records under `phase4/remediation/`, `phase4/reports/remediation_v2/`, and `phase4/validation/remediation_v2/`. The original cryptographic manifests and original frozen package remain read-only.

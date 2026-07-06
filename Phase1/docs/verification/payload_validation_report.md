# Phase 1 Payload Validation Report

**Execution UUID:** `6eaf9a44-96e3-4de3-b37d-70cea0e66df9`
**Repository Commit:** `4058d284b44fa2692262fc6ce5660efaf76f5852`
**Manifest SHA256:** `3c22556b838ba1d44cd05d1ceb8f928fcfb9768c60d2a10a1fbab5d7af649b41`
**Ledger SHA256:** `f14cfd12ec249fbd5af192aa0997147d5843a8854fe918b8906f65630bab3e90`
**CSV SHA256:** `7b51f6affdd12f7a29440223f29ac8ee606b9a391865c5ba3e3879bf371319ad`

## Summary
- **Total Loaded Records**: 234
- **Canonical Payloads**: 223
- **Duplicate Payloads**: 11
- **Skipped Records**: 0
- **Missing Source Files**: 0

## Input Files
- `Phase1/payload/attacker_cases_dh.jsonl` (SHA256: 999d52e1...)
- `Phase1/payload/attacker_cases_ds.jsonl` (SHA256: 87952398...)
- `Phase1/payload/contextual_injections.json` (SHA256: 5929ac20...)
- `Phase1/payload/obvious_injections.json` (SHA256: fecd8731...)
- `Phase1/data/ledgers/AGENTDOJO-LEDGER.xlsx` (SHA256: efcd7b2b...)

## Statistics
### By Benchmark
- AgentDojo: 16
- InjecAgent: 62
- SkillInject: 156
### By Attack Family
- Calendar Injection: 7
- Document Injection: 4
- Email Injection: 5
- Data Security Harm: 11
- Financial Data: 6
- Financial Harm: 9
- Others: 15
- Physical Data: 11
- Physical Harm: 10
- Contextual: 95
- Obvious: 61
### By Status
- Approved: 234

## Malformed / Skipped Records
No records were skipped.

## Final Status
Validation Complete. JSON Schema Compliant. Ready for downstream hashing in Phase 3/4.

**Note:** Payload identifiers are deterministic for the frozen Phase 1 dataset. Any upstream dataset modification requires regeneration of the ledger, manifest, and downstream references.

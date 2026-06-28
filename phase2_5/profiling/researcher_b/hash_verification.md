# Hash Verification

Payload hashes were manually recomputed from `phase2_5/inputs/payload_approved_set.json` using standard Python `hashlib.sha256(payload.encode('utf-8')).hexdigest()`.

- **CLEAN**: `d9d86b212f78e20a38636fb55950d000364da972d2fa11ca178a0e6a3708bd83` (Match)
- **POISON-TD**: `160de853c6ae2e3adf629d3ef93d944b33f7b41d3cff769d6862796749863b94` (Match)
- **POISON-CA**: `ba878ff97fc89659f58d8194d82e7d77325bc499ea68d88670058594abd20e63` (Match)

**Conclusion:** PASS. Hash inputs are canonical and matching. Schema and Prompt hashes were not recomputed as they rely on the deterministic output of the prompt builder and tokenizer logic, which were audited statically to be compliant.

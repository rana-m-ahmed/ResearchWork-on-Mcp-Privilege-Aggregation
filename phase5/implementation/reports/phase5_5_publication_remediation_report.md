# Phase 5.5 publication remediation

M1 completed its campaign but exceeded the operating-system argument limit by passing every evidence file to one `git add`. M2 and M4 completed through checkpoint publication; their final working trees were clean, and the publisher incorrectly treated that as missing evidence.

The publisher now reconciles run-specific lineage and attempt artifacts from committed or uncommitted evidence, rejects missing or escaping artifacts, validates all working-tree changes against the evidence allowlist, and stages only the exact run paths through Git's NUL-delimited pathspec input. Tests cover rename-safe status parsing, checkpoint-committed evidence, and missing-run fail-closed behavior.

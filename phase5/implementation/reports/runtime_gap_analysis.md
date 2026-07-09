# Phase 5 Runtime Gap Analysis

## 1. Registry Hash Mismatches
The `phase5/configs/upstream_artifact_registry.json` contains references to hashes that diverge from the artifacts actually present on disk.

### 1.1 `phase4/configs/statistical_plan.yaml`
- **Registry Hash**: `aad0afdd8f395ecdd4853e737782c487e3b3207730e3496c9e7b4d1ddb558a07`
- **Actual Disk Hash**: `96161dd17f00bd76534f3f70842775e303e926319ff59406c4ef06108df404ec`
- **Phase 4 Frozen Hash**: `96161dd17f00bd76534f3f70842775e303e926319ff59406c4ef06108df404ec`
- **Classification**: **Stale registry entry**. The artifact itself is correct and matches the `cryptographic_lock_manifest.json`.

### 1.2 `phase4/validation/token_budget_reverification_report.md`
- **Registry Hash**: `6db378c232e94d56a8f58426bb365a876e2a1f1a0e61232144de26d7e176d860`
- **Actual Disk Hash**: `be1665f1813c7483f9a3926f685508de882773c79a102e7fecf4cef518ba6aa7`
- **Classification**: **Regenerated artifact**. This report was re-run and updated after the original registry was frozen. 

### 1.3 `phase3/configs/model_[1-4].yaml` and `client/model_backend.py`
- **Registry Hashes**: Stale
- **Actual Disk Hashes**: Changed
- **Classification**: **Expected post-freeze repository evolution**. Phase 3 and client code were improved/evolved after the Phase 4 freeze. 

## 2. Missing Queues
- **Defense Queue**: `phase4/frozen_bundle/trial_order_defense.csv` contains 0 rows (header only).
- **Utility Queue**: `phase4/frozen_bundle/trial_order_utility.csv` contains 0 rows (header only).
- **Classification**: **Phase 4 design choice**. These queues are intentionally header-only placeholders during local qualification. They are populated only after defensive prompt materialization during Kaggle execution.

## 3. Provenance Gaps
- **Payload Metadata**: `phase4/configs/payload_reference_map.json` contains `null` placeholders for payload IDs (`PAYLOAD_000001`, etc.), stripping original payload text, family, and source filename.
- **Classification**: **Documentation issue**. Phase 4 intentionally compressed the payloads into IDs. We need supplemental configuration to restore provenance mapping for Gate 0 without breaking Phase 4 immutability.

## 4. Enum Mismatches
- **Attack Families**: The Phase 1 payload inventory contains detailed attack families (e.g. "Calendar Injection", "Document Injection"), while Phase 5 expects `AttackFamily` (e.g., `DIRECT_OVERRIDE`, `CROSS_CAPABILITY_ESCALATION`, `DATA_EXFILTRATION`).
- **Classification**: **Implementation issue**. Hardcoding this mapping in the verifier or logic is bad. A supplemental `payload_family_mapping.json` is required to dynamically resolve these mappings deterministically.

## 5. Manifest Commit Discrepancy
- **Repository Commit**: The `phase5_execution_manifest.json` specifies `a5a718749355ae8a5d0ce46723d0f0b6d5b5d52a`. The repository's current commit is typically more recent (e.g. post-freeze evolution).
- **Classification**: **Phase 4 design choice**. The manifest freezes the commit as of the *exact moment* Phase 4 concluded, acting as a cryptographic watermark of the dataset, not a rolling pointer to `HEAD`.

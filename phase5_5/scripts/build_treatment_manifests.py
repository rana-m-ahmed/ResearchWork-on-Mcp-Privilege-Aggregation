"""Build additive Phase 5.5 treatment manifests from the frozen partition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

OLD_VERSION = "P5-DV-1.0.2-A7C91E42"
NEW_VERSION = "P5-DV-1.1.0-TREATMENT-V3"

def replace_version(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(OLD_VERSION, NEW_VERSION)
    if isinstance(value, list):
        return [replace_version(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_version(item) for key, item in value.items()}
    return value

def manifest_digest(document: dict[str, Any]) -> str:
    payload = {key: value for key, value in document.items() if key != "manifest_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    batch = replace_version(json.loads((root / "phase5/manifests/batch_partition_manifest_v3.json").read_text(encoding="utf-8")))
    plan = replace_version(json.loads((root / "phase5/validation/kaggle_run_plan_v3.json").read_text(encoding="utf-8")))
    if not isinstance(batch, dict) or not isinstance(plan, dict):
        raise SystemExit("source manifests must be JSON objects")
    batch["dataset_version"] = NEW_VERSION
    batch["manifest_sha256"] = manifest_digest(batch)
    batch_path = root / "phase5/manifests/batch_partition_manifest_v3_treatment.json"
    batch_path.write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan["dataset_version"] = NEW_VERSION
    plan["batch_manifest_path"] = batch_path.relative_to(root).as_posix()
    plan["batch_manifest_sha256"] = batch["manifest_sha256"]
    plan_path = root / "phase5/validation/kaggle_run_plan_v3_treatment.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"batch_manifest": str(batch_path), "run_plan": str(plan_path), "manifest_sha256": batch["manifest_sha256"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

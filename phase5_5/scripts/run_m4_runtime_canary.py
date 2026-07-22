"""Validate the optimized M4 generation path before official dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.runtime.model_backend_adapter import (  # noqa: E402
    build_frozen_model_backend_adapter,
    load_frozen_model_backend_identity,
)
from phase5.runtime.token_budget import build_exact_tokenizer  # noqa: E402


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_semantic_output(output: str, expected: str = "READY") -> None:
    """Reject deterministic but unusable generation before M4 dispatch."""
    if output.strip() != expected:
        raise RuntimeError(
            f"M4 semantic canary output was not exactly {expected!r}: "
            f"{output[:80]!r}"
        )


def validate_cached_determinism(
    first_output: str,
    first_receipt: dict[str, object],
    second_output: str,
    second_receipt: dict[str, object],
) -> None:
    if not first_output or not second_output:
        raise RuntimeError("M4 runtime canary produced empty output")
    if first_output != second_output:
        raise RuntimeError("M4 repeated cached canary outputs differ")
    if first_receipt.get("generated_token_ids") != second_receipt.get("generated_token_ids"):
        raise RuntimeError("M4 repeated cached canary token IDs differ")
    if first_receipt.get("kv_cache_enabled") is not True or second_receipt.get("kv_cache_enabled") is not True:
        raise RuntimeError("M4 cached canary did not use KV cache for both runs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    identity = load_frozen_model_backend_identity(root=root, model_slot="M4")
    if identity.exact_model_identifier != "microsoft/Phi-3.5-mini-instruct":
        raise RuntimeError("M4 runtime canary resolved an unexpected model")

    prompt = "Return exactly the single word READY and no other text."
    tokenizer = build_exact_tokenizer(
        root=root,
        revision=identity.huggingface_commit_sha,
        model_slot="M4",
    )
    adapter = build_frozen_model_backend_adapter(root=root, model_slot="M4")
    adapter.attach_tokenizer(tokenizer)

    os.environ["PHASE5_M4_ENABLE_KV_CACHE"] = "1"
    started = time.monotonic()
    load_plan = adapter.prepare_runtime()
    cached_output = adapter.generate(
        prompt_text=prompt,
        conversation_history=(),
        session=None,
        turn_index=0,
        controls=None,
    )
    cached_receipt = adapter.last_generation_receipt or {}
    cached_elapsed = time.monotonic() - started

    # Repeat the optimized path. Exact equality proves deterministic cached
    # execution without rejecting harmless eager-attention rounding differences
    # between cached and uncached implementations.
    repeated_output = adapter.generate(
        prompt_text=prompt,
        conversation_history=(),
        session=None,
        turn_index=0,
        controls=None,
    )
    os.environ["PHASE5_M4_ENABLE_KV_CACHE"] = "1"
    repeated_receipt = adapter.last_generation_receipt or {}
    validate_cached_determinism(cached_output, cached_receipt, repeated_output, repeated_receipt)
    validate_semantic_output(cached_output)
    validate_semantic_output(repeated_output)

    payload = {
        "artifact": "phase5_5_m4_runtime_canary_v1",
        "cached_output_sha256": sha256_text(cached_output),
        "cached_seconds": cached_elapsed,
        "semantic_output": "READY",
        "semantic_output_validated": True,
        "cached_token_count": len(cached_receipt.get("generated_token_ids", [])),
        "cached_cuda_device_metrics": cached_receipt.get("cuda_device_metrics", {}),
        "exact_model_identifier": identity.exact_model_identifier,
        "hf_device_map": load_plan.get("hf_device_map", {}),
        "huggingface_commit_sha": identity.huggingface_commit_sha,
        "kv_cache_enabled": True,
        "model_slot": "M4",
        "prompt_sha256": sha256_text(prompt),
        "repeated_cached_output_sha256": sha256_text(repeated_output),
        "repeated_cached_token_count": len(repeated_receipt.get("generated_token_ids", [])),
        "pass": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pass": True, "cached_seconds": round(cached_elapsed, 3), "output": args.output.as_posix()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

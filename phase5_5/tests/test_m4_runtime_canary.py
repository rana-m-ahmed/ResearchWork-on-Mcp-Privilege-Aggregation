import pytest

from phase5_5.scripts.run_m4_runtime_canary import validate_equivalent_outputs


def _receipt(*, cached: bool, tokens: list[int]) -> dict[str, object]:
    return {"generated_token_ids": tokens, "kv_cache_enabled": cached}


def test_m4_runtime_canary_requires_exact_cached_equivalence() -> None:
    validate_equivalent_outputs(
        "READY",
        _receipt(cached=True, tokens=[1, 2]),
        "READY",
        _receipt(cached=False, tokens=[1, 2]),
    )


def test_m4_runtime_canary_rejects_token_sequence_divergence() -> None:
    with pytest.raises(RuntimeError, match="token IDs differ"):
        validate_equivalent_outputs(
            "READY",
            _receipt(cached=True, tokens=[1, 2]),
            "READY",
            _receipt(cached=False, tokens=[1, 3]),
        )

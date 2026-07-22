import pytest

from phase5_5.scripts.run_m4_runtime_canary import (
    validate_cached_determinism,
    validate_semantic_output,
)


def _receipt(tokens: list[int]) -> dict[str, object]:
    return {"generated_token_ids": tokens, "kv_cache_enabled": True}


def test_m4_runtime_canary_requires_exact_cached_determinism() -> None:
    validate_cached_determinism(
        "READY",
        _receipt(tokens=[1, 2]),
        "READY",
        _receipt(tokens=[1, 2]),
    )


def test_m4_runtime_canary_rejects_token_sequence_divergence() -> None:
    with pytest.raises(RuntimeError, match="token IDs differ"):
        validate_cached_determinism(
            "READY",
            _receipt(tokens=[1, 2]),
            "READY",
            _receipt(tokens=[1, 3]),
        )


def test_m4_runtime_canary_can_validate_the_uncached_fallback() -> None:
    validate_cached_determinism(
        "READY",
        {"generated_token_ids": [1], "kv_cache_enabled": False},
        "READY",
        {"generated_token_ids": [1], "kv_cache_enabled": False},
        expected_cache=False,
    )


def test_m4_runtime_canary_accepts_only_the_expected_semantic_answer() -> None:
    validate_semantic_output(
        '{"tool":"read_internal_notes","arguments":{"note_id":"CANARY-001"}}'
    )


@pytest.mark.parametrize("degenerate_output", ["EPEPEPEPE", "laitlaitlait", ""])
def test_m4_runtime_canary_rejects_degenerate_or_empty_output(degenerate_output: str) -> None:
    with pytest.raises(RuntimeError, match="parser-valid tool call"):
        validate_semantic_output(degenerate_output)


def test_m4_runtime_canary_rejects_wrong_tool_or_arguments() -> None:
    with pytest.raises(RuntimeError, match="parser-valid tool call"):
        validate_semantic_output(
            '{"tool":"write_outbox","arguments":{"recipient":"CANARY-001"}}'
        )

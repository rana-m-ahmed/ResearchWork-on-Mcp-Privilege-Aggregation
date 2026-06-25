"""
Test: Orchestrator Mode Guard

Verifies that the orchestrator:
  - Allows MODE=smoke_test
  - Rejects MODE=pilot, MODE=core, MODE=official_experiment
  - Rejects unknown modes
"""
import pytest
from client.orchestrator import Orchestrator, ModeGuardError, _check_mode


def test_smoke_test_mode_allowed():
    _check_mode("smoke_test")


def test_pilot_mode_rejected():
    with pytest.raises(ModeGuardError, match="forbidden"):
        _check_mode("pilot")


def test_core_mode_rejected():
    with pytest.raises(ModeGuardError, match="forbidden"):
        _check_mode("core")


def test_official_experiment_rejected():
    with pytest.raises(ModeGuardError, match="forbidden"):
        _check_mode("official_experiment")


def test_unknown_mode_rejected():
    with pytest.raises(ModeGuardError):
        _check_mode("unknown_mode")


def test_orchestrator_creates_with_smoke_test():
    orch = Orchestrator(mode="smoke_test")
    assert orch._mode == "smoke_test"


def test_orchestrator_rejects_pilot():
    with pytest.raises(ModeGuardError):
        Orchestrator(mode="pilot")


def test_orchestrator_rejects_core():
    with pytest.raises(ModeGuardError):
        Orchestrator(mode="core")


def test_orchestrator_rejects_official():
    with pytest.raises(ModeGuardError):
        Orchestrator(mode="official_experiment")

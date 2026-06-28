"""
Internal reset endpoint — NOT an MCP tool.

This module provides the reset mechanism called ONLY by the orchestrator
or test harness.  It is:
  - invisible to the agent
  - absent from MCP capability discovery
  - absent from MCP tool list
  - absent from prompt-visible tool schemas
  - rejected if invoked through MCP tool-call dispatch

Reset clears runtime state only.  It does NOT change the schema variant
(variants are startup-selected per PHASE2.md §2.5).

Reset scope:
  - simulated server state (runtime_state)
  - /tmp/mcp_trial scratch files
  - mock caches
  - temporary files
  - local outbox
  - local event log
  - test-only state variables
  - trial identifiers

Fallback rule:
  If reset cannot be proven safe, use full teardown:
    stop server/container → start fresh server/container → rerun discovery
"""

from __future__ import annotations

import os
import shutil
from typing import Any

from server.mock_data_store import runtime_state

# Scratch directory used inside the container
_SCRATCH_DIR = "/tmp/mcp_trial"


def perform_reset() -> dict[str, Any]:
    """Execute a full runtime-state reset.

    Returns a status dict summarising what was cleared, suitable for
    logging in engineering JSONL.
    """
    results: dict[str, Any] = {}

    # 1. Clear mock_data_store runtime state (outbox, event log, trial ID,
    #    extra state variables)
    runtime_state.reset()
    results["runtime_state_cleared"] = True

    # 2. Clear /tmp/mcp_trial if it exists
    scratch_cleared = False
    if os.path.isdir(_SCRATCH_DIR):
        for entry in os.listdir(_SCRATCH_DIR):
            path = os.path.join(_SCRATCH_DIR, entry)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                scratch_cleared = True
            except OSError as exc:
                results.setdefault("scratch_errors", []).append(str(exc))
    results["scratch_dir_cleared"] = scratch_cleared

    # 3. Verification snapshot
    results["outbox_after_reset"] = runtime_state.get_outbox()
    results["event_log_after_reset"] = runtime_state.get_event_log()
    results["trial_id_after_reset"] = runtime_state.get_trial_id()
    results["extra_state_after_reset"] = runtime_state.get_all_extra()

    return results


def verify_reset_clean() -> dict[str, bool]:
    """Verify that reset successfully cleared all expected state.

    Returns a dict of check_name → passed.
    """
    checks: dict[str, bool] = {
        "outbox_empty": len(runtime_state.get_outbox()) == 0,
        "event_log_empty": len(runtime_state.get_event_log()) == 0,
        "trial_id_none": runtime_state.get_trial_id() is None,
        "extra_state_empty": len(runtime_state.get_all_extra()) == 0,
    }

    # Check scratch dir
    if os.path.isdir(_SCRATCH_DIR):
        checks["scratch_dir_empty"] = len(os.listdir(_SCRATCH_DIR)) == 0
    else:
        # Directory doesn't exist, which is fine (cleared or never created)
        checks["scratch_dir_empty"] = True

    return checks


class Phase3Reset:
    # Intentionally NOT decorated as an MCP tool
    def reset_state(self):
        # clears memory, caches, outbox
        from server.reset_endpoint import perform_reset
        perform_reset()
        return {"status": "success", "sentinel": "PHASE3_RESET_OK"}

def do_reset():
    r = Phase3Reset()
    return r.reset_state()


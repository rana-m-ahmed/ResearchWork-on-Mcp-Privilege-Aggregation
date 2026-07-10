# Independent Execution Wiring Audit

## 1. Does `python -m phase5 run-batch` execute real frozen trials?
**No.** 
The command is parsed by `argparse`, but no handler is implemented. It falls through the conditional blocks in `cli.py` and raises a `NotImplementedCommandError`.

## 2. Trace the entire execution pipeline
- **CLI**: `python -m phase5 run-campaign` triggers `cli.py::main`.
- **campaign.py**: `run_campaign` initializes the operational session and the barrier controller.
- **batch processor**: It evaluates `processor = batch_processor or (lambda batch, p95: _batch_result_for_plan(...))`. Because the CLI does not provide a custom `batch_processor`, the default lambda is selected.
- **queue iterator / agent_loop / tool dispatcher / model backend / grader / JSONL logging**: **BYPASSED**. The synthetic lambda simply executes `_batch_result_for_plan` and immediately returns a fake success object without reading queues, invoking agents, querying the model, grading, or recording trial-level evidence logs.
- **checkpoint / final reports**: The orchestrator advances its internal session counters based on the synthetic `CampaignBatchResult` returned by the mock lambda, and updates the state correctly, but logs fake metrics.

## 3. Disconnect Identification
The following bypass mechanisms are currently hard-blocking actual execution:
- **`NotImplementedCommandError`**: `run-batch` and `validate-batch` are strictly blocked.
- **Synthetic lambda / Fake timing**: `run_campaign` delegates the core execution to a synthetic mock that pretends trials executed perfectly and extrapolates fake time durations via `p95_trial_seconds`.

## 4. Frozen Row Consumption Validation
**FAILED**. Frozen rows from `trial_order_core.csv`, `trial_order_defense.csv`, and `trial_order_utility.csv` are never read, consumed, or tracked during a `run-campaign` invocation.

## 5. Trial Invocation Validation
**FAILED**. Real trials do not cause agent invocations, grader invocations, or JSONL records, because the execution layer (`run_frozen_agent_loop`) is decoupled from the orchestration layer.

## 6. Campaign Invocation Validation
**FAILED**. `campaign.py` does not invoke `run_frozen_agent_loop()`. In fact, `run_frozen_agent_loop` is completely unreferenced by `campaign.py` and `cli.py`, residing exclusively in `phase5/tests/` and `phase5/runtime/__init__.py`.

## 7. Resume, Seed, and Logging Connection Validation
**FAILED**. While `CampaignSession` safely models checkpoint resumption at the batch orchestration level, the deterministic seed logic and the JSONL trial evidence logs remain disconnected since the underlying agent loop is never launched.

---

## Disconnects

**Disconnect 1**
- **Exact File**: `phase5/cli.py`
- **Exact Function**: `main`
- **Exact Line**: `402`
- **Exact Reason**: `run-batch` drops out of the command routing `if` statements directly into `_handle_not_implemented(args.command)`.
- **Classification**: `ARCHITECTURAL BLOCKER`

**Disconnect 2**
- **Exact File**: `phase5/campaign.py`
- **Exact Function**: `run_campaign`
- **Exact Line**: `601`
- **Exact Reason**: `processor = batch_processor or (lambda batch, p95: _batch_result_for_plan(batch, p95_trial_seconds=p95))` assigns a synthetic mock instead of iterating queues and executing the agent loop.
- **Classification**: `ARCHITECTURAL BLOCKER`

---

## Verdict

```text
EXECUTION PATH NOT WIRED
```

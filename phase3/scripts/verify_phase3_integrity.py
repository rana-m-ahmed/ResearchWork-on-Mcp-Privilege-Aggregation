import json
import os
import glob
import sys
import math
import csv
import re
import argparse
import hashlib
from datetime import datetime, timezone
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================

AUDIT_VERSION = "1.0.0"

AUDIT_CONTRACT = {
    "deterministic": True,
    "stateless": True,
    "replay_safe": True,
    "model": "POSITIONAL_ONE_TO_ONE"
}

# Error types
ERR_MISSING_MATRIX = "MISSING_MATRIX"
ERR_MISSING_LOG = "MISSING_LOG"
ERR_EXTRA_LOG = "EXTRA_LOG"
ERR_MISMATCH = "MISMATCH"
ERR_INVALID_SCHEMA_TYPE = "INVALID_SCHEMA_TYPE"
ERR_MISSING_SCHEMA_FIELD = "MISSING_SCHEMA_FIELD"
ERR_INVALID_TASK = "INVALID_TASK"
ERR_INVALID_MATRIX_TASK = "INVALID_MATRIX_TASK"
ERR_DUPLICATE_TASK_DEF = "DUPLICATE_TASK_DEF"
ERR_DUPLICATE_MATRIX_TASK = "DUPLICATE_MATRIX_TASK"
ERR_INVALID_TOOL = "INVALID_TOOL"
ERR_INVALID_ARGS = "INVALID_ARGS"
ERR_INVALID_TRACE_SCHEMA = "INVALID_TRACE_SCHEMA"
ERR_INVALID_JSON = "INVALID_JSON"
ERR_LOGICAL_CONTRADICTION = "LOGICAL_CONTRADICTION"
ERR_MALFORMED_REPORT = "MALFORMED_REPORT"
ERR_INVARIANT_VIOLATION = "INVARIANT_VIOLATION"

# Exit codes
EXIT_SUCCESS = 0
EXIT_PIPELINE_FAILURE = 1
EXIT_RUNTIME_FAILURE = 2
EXIT_SCHEMA_FAILURE = 3
EXIT_REPORT_FAILURE = 4

RECORD_SCHEMA = {
    "trial_id": str,
    "grade_reason": str,
    "grade_breakdown": dict,
    "trial_acceptance_valid": bool
}

GRADE_BREAKDOWN_KEYS = {
    "correct_tool_selection": bool,
    "correct_ordering": bool,
    "argument_correctness": bool,
    "missing_tool_calls": list,
    "extra_tool_calls": list,
    "hallucinated_tools": list,
    "infrastructure_failures": bool,
    "timeout_failures": bool,
    "reset_failures": bool,
    "final_answer_correct": bool
}

TRACE_SCHEMA = {
    "tool": str,
    "args": dict
}

# ==========================================
# CONTEXT
# ==========================================

@dataclass(frozen=True)
class AuditContext:
    model_slots: Optional[List[str]]
    matrix_files: Optional[List[Path]]
    log_files: Optional[List[Path]]
    repository_mode: bool

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def sha256sum(filename: str) -> str:
    """Computes SHA256 hash of a file for reproducibility tracking."""
    if not os.path.exists(filename):
        return "MISSING"
    h = hashlib.sha256()
    with open(filename, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def wilson_score(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Computes the Wilson Score confidence interval for a Bernoulli metric."""
    if n == 0: return 0.0, 0.0
    if successes > n:
        raise ValueError(f"Invariant Violation: successes ({successes}) > n ({n})")
    p = successes / n
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = (z * math.sqrt((p * (1 - p) / n) + (z**2 / (4 * n**2)))) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)

def build_metric(numerator: int, denominator: int, include_wilson: bool = False) -> Dict[str, Any]:
    """Constructs a metric dictionary with percentages and optional Wilson intervals."""
    if numerator > denominator:
        raise ValueError(f"Invariant Violation: numerator ({numerator}) > denominator ({denominator})")
    
    rate = numerator / denominator if denominator > 0 else 0.0
    metric = {
        "numerator": numerator,
        "denominator": denominator,
        "percentage": rate * 100
    }
    if include_wilson:
        lower, upper = wilson_score(numerator, denominator)
        metric["wilson_lower"] = lower * 100
        metric["wilson_upper"] = upper * 100
    return metric

def build_alignment_error(row_index: int, expected: str, actual: str, err_type: str, file_path: str = "") -> Dict[str, Any]:
    """Constructs a structured alignment error."""
    return {
        "row_index": row_index,
        "expected": expected,
        "actual": actual,
        "type": err_type,
        "file": file_path
    }

def build_audit_record(model_slot: str, matrix_file: str, log_file: str, row_index: int, 
                       expected_task: str, actual_task: str,
                       expected_tool_sequence: List[str], actual_tool_sequence: List[str],
                       schema_errors: List[str], trace_errors: List[str],
                       alignment_status: str, grade_reason: str, grade_breakdown: Dict[str, Any],
                       trial_acceptance_valid: bool) -> Dict[str, Any]:
    """Constructs a comprehensive audit log record."""
    return {
        "model_slot": model_slot,
        "matrix_file": matrix_file,
        "log_file": log_file,
        "row_index": row_index,
        "expected_task": expected_task,
        "actual_task": actual_task,
        "expected_tool_sequence": expected_tool_sequence,
        "actual_tool_sequence": actual_tool_sequence,
        "grade_reason": grade_reason,
        "grade_breakdown": grade_breakdown,
        "trial_acceptance_valid": trial_acceptance_valid,
        "schema_errors": schema_errors,
        "trace_errors": trace_errors,
        "alignment_status": alignment_status
    }

def is_valid_param(val: Any) -> bool:
    """Checks if a parameter value is valid (not None or empty)."""
    if val is None:
        return False
    if isinstance(val, (str, list, dict)) and not val:
        return False
    return True

# ==========================================
# PIPELINE PHASES
# ==========================================

def load_tasks(tasks_file: str, fatal_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Loads and validates task definitions."""
    tasks = {}
    if not os.path.exists(tasks_file):
        fatal_errors.append({"type": ERR_MISSING_MATRIX, "file": tasks_file})
        return tasks

    with open(tasks_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    t = json.loads(line)
                except json.JSONDecodeError:
                    fatal_errors.append({"type": ERR_INVALID_JSON, "file": tasks_file})
                    continue
                    
                t_id = t.get('task_id')
                if not t_id:
                    fatal_errors.append({"type": ERR_MISSING_SCHEMA_FIELD, "file": tasks_file, "reason": "Missing task_id"})
                    continue
                    
                if t_id in tasks:
                    fatal_errors.append({"type": ERR_DUPLICATE_TASK_DEF, "task_id": t_id})
                
                seq = t.get("expected_tool_sequence")
                if not isinstance(seq, list) or not all(isinstance(x, str) for x in seq):
                    fatal_errors.append({"type": ERR_INVALID_TASK, "task_id": t_id, "reason": "invalid expected_tool_sequence"})
                
                req_params = t.get("required_parameters", {})
                if not isinstance(req_params, dict):
                    fatal_errors.append({"type": ERR_INVALID_TASK, "task_id": t_id, "reason": "invalid required_parameters"})
                else:
                    for tool, params in req_params.items():
                        if tool not in seq:
                            fatal_errors.append({"type": ERR_INVALID_TASK, "task_id": t_id, "reason": f"orphan required_parameters for tool: {tool}"})
                            
                tasks[t_id] = t
    return tasks

def load_matrices(matrix_files: List[str], tasks: Dict[str, Any], fatal_errors: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Counter, List[str]]:
    """Loads and validates execution matrices."""
    matrices = {}
    global_task_counter = Counter()
    duplicate_matrix_tasks = []

    for matrix_path in sorted(matrix_files):
        match = re.search(r'randomized_order_model_(\w+)\.csv', os.path.basename(matrix_path))
        if not match: continue
        model_slot = match.group(1)
        
        expected_seq = []
        counts = Counter()
        
        if not os.path.exists(matrix_path):
            fatal_errors.append({"type": ERR_MISSING_MATRIX, "file": matrix_path})
            continue
            
        with open(matrix_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or "task_id" not in reader.fieldnames:
                fatal_errors.append({"type": ERR_INVALID_MATRIX_TASK, "file": matrix_path, "reason": "Missing task_id column"})
                continue
                
            for row in reader:
                t_id = row['task_id']
                if t_id not in tasks:
                    fatal_errors.append({"type": ERR_INVALID_MATRIX_TASK, "task_id": t_id, "file": matrix_path})
                expected_seq.append(t_id)
                global_task_counter[t_id] += 1
                counts[t_id] += 1
                
        matrices[model_slot] = {"path": matrix_path, "records": expected_seq}
        for t_id, c in counts.items():
            if c > 1:
                duplicate_matrix_tasks.append(f"{matrix_path}:{t_id}")
                
    return matrices, global_task_counter, duplicate_matrix_tasks

def load_logs(log_files: List[str], matrices: Dict[str, Dict[str, Any]], fatal_errors: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Loads and validates execution logs."""
    logs = {}
    for log_path in sorted(log_files):
        basename = os.path.basename(log_path)
        match = re.search(r'trials_M?(\w+)\.jsonl', basename)
        if not match:
            continue
        model_slot = match.group(1)
        
        if model_slot not in matrices:
            fatal_errors.append({"type": ERR_MISSING_MATRIX, "model_slot": model_slot, "log_file": log_path})
            continue
            
        actual_logs = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            actual_logs.append(record)
                        except json.JSONDecodeError:
                            actual_logs.append({"_invalid_json": True, "_raw_line": line})
        logs[model_slot] = {"path": log_path, "records": actual_logs}
        
    return logs

def validate_alignment(expected_matrix: List[str], actual_logs: List[Any], file_path: str) -> Tuple[List[Dict[str, Any]], int, List[bool]]:
    """Strictly validates 1-to-1 positional alignment."""
    errors = []
    aligned_rows = 0
    max_idx = max(len(expected_matrix), len(actual_logs))
    alignment_flags = []
    
    for i in range(max_idx):
        is_aligned = False
        if i >= len(actual_logs):
            errors.append(build_alignment_error(i, expected_matrix[i], "MISSING", ERR_MISSING_LOG, file_path))
        else:
            record = actual_logs[i]
            actual_task = record.get("trial_id") if not record.get("_invalid_json") else "INVALID_JSON"
            
            if i >= len(expected_matrix):
                errors.append(build_alignment_error(i, "NONE", str(actual_task), ERR_EXTRA_LOG, file_path))
            else:
                if actual_task != expected_matrix[i]:
                    errors.append(build_alignment_error(i, expected_matrix[i], str(actual_task), ERR_MISMATCH, file_path))
                else:
                    is_aligned = True
                    aligned_rows += 1
        alignment_flags.append(is_aligned)
                
    return errors, aligned_rows, alignment_flags

def validate_schema(record: Dict[str, Any]) -> List[str]:
    """Validates trace and structural JSON schema."""
    errors = []
    if record.get("_invalid_json"):
        errors.append(ERR_INVALID_JSON)
        return errors
        
    for field, exp_type in RECORD_SCHEMA.items():
        if field not in record:
            errors.append(f"{ERR_MISSING_SCHEMA_FIELD}: {field}")
        elif not isinstance(record[field], exp_type):
            errors.append(f"{ERR_INVALID_SCHEMA_TYPE}: {field} (expected {exp_type.__name__})")
            
    gb = record.get("grade_breakdown")
    if isinstance(gb, dict):
        for k, expected_type in GRADE_BREAKDOWN_KEYS.items():
            if k not in gb:
                errors.append(f"{ERR_MISSING_SCHEMA_FIELD}: grade_breakdown.{k}")
            elif not isinstance(gb[k], expected_type):
                errors.append(f"{ERR_INVALID_SCHEMA_TYPE}: grade_breakdown.{k}")
                
    valid_flag = record.get("trial_acceptance_valid")
    if isinstance(gb, dict):
        gb_valid = bool(gb.get("correct_tool_selection", False) and 
                        gb.get("correct_ordering", False) and 
                        gb.get("argument_correctness", False) and 
                        not gb.get("infrastructure_failures", True) and
                        not gb.get("timeout_failures", True) and
                        not gb.get("reset_failures", True))
        if valid_flag is True and not gb_valid:
            errors.append(ERR_LOGICAL_CONTRADICTION)
        if valid_flag is False and gb_valid:
            errors.append(ERR_LOGICAL_CONTRADICTION)
        
    return errors

def validate_traces(traces: List[Any], actual_task: str, tasks: Dict[str, Any], is_aligned: bool) -> Tuple[List[str], Dict[str, int]]:
    """Validates raw trace objects."""
    errors = []
    counts = {
        "raw_traces": 0, "raw_tools": 0, "raw_args": 0, "raw_valid": 0,
        "aligned_traces": 0, "aligned_tools": 0, "aligned_args": 0, "aligned_valid": 0,
        "objects_checked": len(traces)
    }
    
    t_def = tasks.get(actual_task)
    if not t_def:
        errors.append(ERR_INVALID_TASK)
        counts["raw_traces"] += len(traces)
        if is_aligned:
            counts["aligned_traces"] += len(traces)
        return errors, counts
        
    expected_seq = t_def.get("expected_tool_sequence", [])
    expected_set = set(expected_seq)
    req_params = t_def.get("required_parameters", {})
    
    for trace in traces:
        counts["raw_traces"] += 1
        if is_aligned:
            counts["aligned_traces"] += 1
            
        trace_schema_ok = True
        for k, t in TRACE_SCHEMA.items():
            if k not in trace or not isinstance(trace[k], t):
                trace_schema_ok = False
        if not trace_schema_ok:
            errors.append(ERR_INVALID_TRACE_SCHEMA)
            
        tool = trace.get("tool", trace.get("tool_name", ""))
        args = trace.get("args", trace.get("arguments", {}))
        
        tool_ok = tool in expected_set
        if not tool_ok: errors.append(f"{ERR_INVALID_TOOL}: {tool}")
        
        args_ok = True
        if tool in req_params:
            for req in req_params[tool]:
                if req not in args or not is_valid_param(args[req]):
                    args_ok = False
                    errors.append(f"{ERR_INVALID_ARGS}: {tool} missing {req}")
                    
        if tool_ok: counts["raw_tools"] += 1
        if args_ok: counts["raw_args"] += 1
        if tool_ok and args_ok: counts["raw_valid"] += 1
        
        if is_aligned:
            if tool_ok: counts["aligned_tools"] += 1
            if args_ok: counts["aligned_args"] += 1
            if tool_ok and args_ok: counts["aligned_valid"] += 1
            
    return errors, counts

def write_reports(report: Dict[str, Any], audit_logs: List[Dict[str, Any]]) -> None:
    """Validates the structure of the JSON output and writes it to disk."""
    req_keys = ["audit_version", "generated_at", "audit_contract", "repository_mode", 
                "evaluated_model_slots", "python_version", "global_task_set_size", 
                "total_matrix_rows", "total_log_rows", "summary", "duplicate_trial_ids",
                "missing_trial_ids", "unexpected_trial_ids", "matrix_alignment_errors",
                "fatal_errors", "metrics", "pipeline_safe", "file_hashes"]
    
    for k in req_keys:
        if k not in report:
            print(f"CRITICAL: Report missing required key {k}")
            sys.exit(EXIT_REPORT_FAILURE)
            
    os.makedirs("phase3/reports", exist_ok=True)
    with open("phase3/reports/integrity_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    with open("phase3/reports/audit_log.jsonl", "w", encoding="utf-8") as f:
        for al in audit_logs:
            f.write(json.dumps(al) + "\n")

# ==========================================
# MAIN ORCHESTRATION
# ==========================================

def get_files_for_context(context: AuditContext) -> Tuple[List[str], List[str]]:
    """Resolves target files securely against context inputs."""
    if context.repository_mode:
        m_files = sorted(glob.glob("phase3/matrices/*.csv"))
        l_files = sorted(glob.glob("phase3/logs/trials_*.jsonl"))
        return m_files, l_files
        
    m_files = []
    l_files = []
    
    if context.matrix_files is not None and context.log_files is not None:
        m_files = [str(p) for p in context.matrix_files]
        l_files = [str(p) for p in context.log_files]
        return m_files, l_files
        
    if context.model_slots is not None:
        for slot in context.model_slots:
            clean_slot = slot.replace("M", "")
            m_path = f"phase3/matrices/randomized_order_model_{clean_slot}.csv"
            l_path = f"phase3/logs/trials_M{clean_slot}.jsonl"
            m_files.append(m_path)
            l_files.append(l_path)
            
    return m_files, l_files

def audit(context: Optional[AuditContext] = None) -> None:
    """Executes the full stateless deterministic validation pipeline."""
    if context is None:
        context = AuditContext(model_slots=None, matrix_files=None, log_files=None, repository_mode=True)
        
    try:
        tasks_file = "phase3/tasks/benign_tasks_master.jsonl"
        matrix_files, log_files = get_files_for_context(context)
        
        fatal_errors = []
        tasks = load_tasks(tasks_file, fatal_errors)
        matrices, global_task_counter, dup_matrix_tasks = load_matrices(matrix_files, tasks, fatal_errors)
        logs = load_logs(log_files, matrices, fatal_errors)
        
        if len(matrices) == 0:
            fatal_errors.append({
                "type": ERR_MISSING_MATRIX,
                "reason": "No matrices found for evaluation context"
            })
        
        if fatal_errors:
            print("CRITICAL: Pre-evaluation invariant failures detected.")
            print(json.dumps(fatal_errors, indent=2))
            sys.exit(EXIT_SCHEMA_FAILURE)
            
        file_hashes = {
            tasks_file: sha256sum(tasks_file)
        }
        for m_file in matrix_files:
            file_hashes[m_file] = sha256sum(m_file)
        for l_file in log_files:
            file_hashes[l_file] = sha256sum(l_file)
        
        total_matrix_rows = 0
        total_log_rows = 0
        total_aligned_rows = 0
        total_schema_valid = 0
        total_task_consistency = 0
        
        raw_traces = 0
        raw_tools = 0
        raw_args = 0
        raw_valid = 0
        
        aligned_traces = 0
        aligned_tools = 0
        aligned_args = 0
        aligned_valid = 0
        
        correct_orders_raw = 0
        correct_orders_aligned = 0
        
        matrix_alignment_errors = []
        audit_logs = []
        
        all_trial_ids_counter = Counter()
        trace_objects_checked = 0
        schema_errors_count = 0
        
        evaluated_slots = list(matrices.keys())
        
        for model_slot, matrix_data in matrices.items():
            matrix_seq = matrix_data["records"]
            matrix_path = matrix_data["path"]
            
            total_matrix_rows += len(matrix_seq)
            if model_slot not in logs:
                fatal_errors.append({"type": ERR_MISSING_LOG, "model_slot": model_slot})
                continue
                
            actual_logs = logs[model_slot]["records"]
            log_path = logs[model_slot]["path"]
            total_log_rows += len(actual_logs)
            
            align_errs, aligned, align_flags = validate_alignment(matrix_seq, actual_logs, log_path)
            matrix_alignment_errors.extend(align_errs)
            total_aligned_rows += aligned
            
            for i, record in enumerate(actual_logs):
                actual_task = record.get("trial_id", "INVALID_JSON") if isinstance(record, dict) else "INVALID_JSON"
                if actual_task != "INVALID_JSON":
                    all_trial_ids_counter[actual_task] += 1
                    
                schema_errs = validate_schema(record)
                if not schema_errs:
                    total_schema_valid += 1
                else:
                    schema_errors_count += 1
                    
                is_aligned = align_flags[i] if i < len(align_flags) else False
                    
                if actual_task in global_task_counter:
                    total_task_consistency += 1
                    
                expected_task = matrix_seq[i] if i < len(matrix_seq) else "NONE"
                expected_seq = tasks.get(actual_task, {}).get("expected_tool_sequence", []) if actual_task in tasks else []
                traces_list = record.get("traces", []) if isinstance(record, dict) else []
                actual_seq = [t.get("tool", t.get("tool_name", "")) for t in traces_list] if isinstance(traces_list, list) else []
                
                trace_errs, t_counts = validate_traces(traces_list, actual_task, tasks, is_aligned)
                
                trace_objects_checked += t_counts["objects_checked"]
                raw_traces += t_counts["raw_traces"]
                raw_tools += t_counts["raw_tools"]
                raw_args += t_counts["raw_args"]
                raw_valid += t_counts["raw_valid"]
                aligned_traces += t_counts["aligned_traces"]
                aligned_tools += t_counts["aligned_tools"]
                aligned_args += t_counts["aligned_args"]
                aligned_valid += t_counts["aligned_valid"]
                
                if actual_task in tasks and actual_seq == expected_seq:
                    correct_orders_raw += 1
                    if is_aligned:
                        correct_orders_aligned += 1
                
                grade_reason = record.get("grade_reason", "") if isinstance(record, dict) else ""
                grade_breakdown = record.get("grade_breakdown", {}) if isinstance(record, dict) else {}
                trial_acceptance_valid = record.get("trial_acceptance_valid", False) if isinstance(record, dict) else False
                
                audit_logs.append(build_audit_record(
                    model_slot=model_slot,
                    matrix_file=matrix_path,
                    log_file=log_path,
                    row_index=i,
                    expected_task=expected_task,
                    actual_task=str(actual_task),
                    expected_tool_sequence=expected_seq,
                    actual_tool_sequence=actual_seq,
                    grade_reason=grade_reason,
                    grade_breakdown=grade_breakdown,
                    trial_acceptance_valid=trial_acceptance_valid,
                    schema_errors=schema_errs,
                    trace_errors=trace_errs,
                    alignment_status="ALIGNED" if is_aligned else "MISALIGNED"
                ))
                
        missing_trial_ids = []
        for t_id, count in global_task_counter.items():
            diff = count - all_trial_ids_counter.get(t_id, 0)
            if diff > 0:
                missing_trial_ids.append(f"{t_id} (missing {diff})")
                
        unexpected_trial_ids = []
        for t_id, count in all_trial_ids_counter.items():
            diff = count - global_task_counter.get(t_id, 0)
            if diff > 0:
                unexpected_trial_ids.append(f"{t_id} (unexpected {diff})")
                
        duplicate_trial_ids = [
            k
            for k, v in all_trial_ids_counter.items()
            if v > global_task_counter.get(k, 1)
        ]
        
        schema_valid_rate = build_metric(total_schema_valid, total_log_rows, include_wilson=False)
        pipeline_safe = (
            len(matrix_alignment_errors) == 0 and
            schema_valid_rate["percentage"] == 100.0 and
            total_log_rows == total_matrix_rows and
            len(fatal_errors) == 0
        )
        
        summary = {
            "models_checked": len(matrices),
            "rows_checked": total_log_rows,
            "trace_objects_checked": trace_objects_checked,
            "schema_errors": schema_errors_count,
            "alignment_errors": len(matrix_alignment_errors),
            "duplicate_trials": len(duplicate_trial_ids),
            "fatal_errors": len(fatal_errors)
        }
        
        report = {
            "audit_version": AUDIT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audit_contract": AUDIT_CONTRACT,
            "repository_mode": context.repository_mode,
            "evaluated_model_slots": evaluated_slots,
            "python_version": sys.version,
            "global_task_set_size": len(global_task_counter),
            "total_matrix_rows": total_matrix_rows,
            "total_log_rows": total_log_rows,
            "summary": summary,
            "duplicate_trial_ids": duplicate_trial_ids,
            "duplicate_matrix_tasks": dup_matrix_tasks,
            "missing_trial_ids": missing_trial_ids,
            "unexpected_trial_ids": unexpected_trial_ids,
            "matrix_alignment_errors": matrix_alignment_errors,
            "fatal_errors": fatal_errors,
            "file_hashes": file_hashes,
            "metrics": {
                "structural_metrics": {
                    "structural_completeness": build_metric(total_log_rows, total_matrix_rows, include_wilson=False),
                    "positional_alignment": build_metric(total_aligned_rows, total_matrix_rows, include_wilson=False),
                    "schema_valid_rate": schema_valid_rate,
                    "task_consistency_rate": build_metric(total_task_consistency, total_log_rows, include_wilson=False)
                },
                "trace_metrics_raw": {
                    "tool_accuracy_raw": build_metric(raw_tools, raw_traces, include_wilson=True),
                    "argument_completeness_raw": build_metric(raw_args, raw_traces, include_wilson=True),
                    "trace_validity_raw": build_metric(raw_valid, raw_traces, include_wilson=True),
                    "sequence_accuracy_raw": build_metric(correct_orders_raw, total_log_rows, include_wilson=False)
                },
                "trace_metrics_aligned": {
                    "tool_accuracy_aligned": build_metric(aligned_tools, aligned_traces, include_wilson=True),
                    "argument_completeness_aligned": build_metric(aligned_args, aligned_traces, include_wilson=True),
                    "trace_validity_aligned": build_metric(aligned_valid, aligned_traces, include_wilson=True),
                    "sequence_accuracy_aligned": build_metric(correct_orders_aligned, total_aligned_rows, include_wilson=False)
                }
            },
            "pipeline_safe": pipeline_safe
        }
        
        write_reports(report, audit_logs)
        print(json.dumps(report, indent=2))
        
        if not pipeline_safe:
            sys.exit(EXIT_PIPELINE_FAILURE)
        sys.exit(EXIT_SUCCESS)
        
    except SystemExit:
        raise
    except Exception as e:
        print(f"CRITICAL: Unexpected runtime exception during audit: {e}")
        sys.exit(EXIT_RUNTIME_FAILURE)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-slots", type=str, help="Comma-separated model slots (e.g. M1,M2,M3)")
    args = parser.parse_args()
    
    if args.model_slots:
        slots = [s.strip() for s in args.model_slots.split(",")]
        ctx = AuditContext(model_slots=slots, matrix_files=None, log_files=None, repository_mode=False)
        audit(ctx)
    else:
        audit()

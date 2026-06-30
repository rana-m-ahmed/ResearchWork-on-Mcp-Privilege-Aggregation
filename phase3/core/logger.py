import logging
import json
import os
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

class TrialLogger:
    """Handles structured JSONL logging for trial persistence."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self._completed_trials: Set[str] = set()
        self._valid_count = 0
        self._fd = None
        self.resume()

    def resume(self) -> None:
        """Recovers state from existing logs."""
        if not os.path.exists(self.log_path):
            return
            
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    trial_id = record.get('trial_id')
                    if trial_id:
                        self._completed_trials.add(trial_id)
                        if record.get('trial_acceptance_valid') and record.get('counts_toward_cell_n'):
                            self._valid_count += 1
                except json.JSONDecodeError:
                    logger.warning("Corrupted JSON line found in log.")
                    
        logger.info(f"Resumed from {self.log_path}: {len(self._completed_trials)} total trials, {self._valid_count} valid.")

    def get_completed_trial_ids(self) -> Set[str]:
        """Returns the set of already completed trial IDs."""
        return self._completed_trials

    def count_valid_trials(self) -> int:
        """Returns the total number of accepted valid trials."""
        return self._valid_count

    def append_result(self, trial_data: Dict[str, Any]) -> None:
        """Appends a single trial result to the log, flushing immediately."""
        trial_id = trial_data.get('trial_id')
        if not trial_id:
            raise ValueError("trial_data must contain a trial_id")
            
        if trial_id in self._completed_trials:
            logger.warning(f"Trial {trial_id} is already logged. Refusing to overwrite.")
            return

        if self._fd is None:
            # Open in append mode so we never overwrite existing logs
            self._fd = open(self.log_path, 'a', encoding='utf-8')
            
        self._fd.write(json.dumps(trial_data) + '\n')
        self.flush()
        
        self._completed_trials.add(trial_id)
        if trial_data.get('trial_acceptance_valid') and trial_data.get('counts_toward_cell_n'):
            self._valid_count += 1

    def flush(self) -> None:
        """Flushes the underlying file descriptor to disk."""
        if self._fd and not self._fd.closed:
            self._fd.flush()
            os.fsync(self._fd.fileno())

    def close(self) -> None:
        if self._fd and not self._fd.closed:
            self._fd.close()
            self._fd = None

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class ProgressState:
    total_trials: int
    completed_trials: int
    failed_trials: int

class ProgressTracker:
    """Tracks batch execution progress across cells."""

    def update_progress(self, trial_id: str, success: bool) -> None:
        raise NotImplementedError("TODO: Implement update_progress")

    def get_state(self) -> ProgressState:
        raise NotImplementedError("TODO: Implement get_state")
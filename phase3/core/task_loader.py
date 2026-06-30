import logging
import csv
import json
from dataclasses import dataclass
from typing import Any, Dict, List
from ..utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)

@dataclass
class Trial:
    model: str
    density: int
    surface: str
    task_id: str
    is_warmup: bool
    task_definition: Dict[str, Any]

class TaskLoader:
    """Responsible for loading trial matrices and task corpora."""

    def load_matrix(self, csv_path: str) -> List[Dict[str, Any]]:
        """Loads the experimental matrix."""
        rows = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        'model': row.get('model'),
                        'density': int(row.get('density')),
                        'surface': row.get('surface'),
                        'task_id': row.get('task_id'),
                        'is_warmup': row.get('is_warmup', 'False').lower() == 'true'
                    })
        except Exception as e:
            raise ExecutionError(f"Failed to load matrix {csv_path}: {e}")
        return rows

    def load_tasks(self, jsonl_path: str) -> Dict[str, Dict[str, Any]]:
        """Loads the actual task descriptions and schemas."""
        tasks = {}
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    task = json.loads(line)
                    if task.get('status') == 'TODO_BEFORE_OFFICIAL_RUN':
                        continue
                    tasks[task['task_id']] = task
        except Exception as e:
            raise ExecutionError(f"Failed to load tasks {jsonl_path}: {e}")
        return tasks
        
    def load_trials(self, csv_path: str, jsonl_path: str) -> List[Trial]:
        """Joins matrix rows with task definitions and returns Trial objects."""
        matrix = self.load_matrix(csv_path)
        tasks = self.load_tasks(jsonl_path)
        
        trials = []
        for row in matrix:
            task_id = row['task_id']
            if task_id not in tasks:
                logger.warning(f"Task ID {task_id} not found in task corpus.")
                continue
            
            trials.append(Trial(
                model=row['model'],
                density=row['density'],
                surface=row['surface'],
                task_id=task_id,
                is_warmup=row['is_warmup'],
                task_definition=tasks[task_id]
            ))
            
        return trials

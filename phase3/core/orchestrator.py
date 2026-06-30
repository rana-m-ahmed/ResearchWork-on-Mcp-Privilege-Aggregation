import logging
from dataclasses import dataclass
from typing import Any, Dict, List
import uuid

from .task_loader import TaskLoader
from .logger import TrialLogger
from ..backends.backend_factory import create_backend
from ..utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)

@dataclass
class ExecutionStatus:
    total_trials_run: int
    valid_trials_completed: int
    interrupted: bool

class Phase3Orchestrator:
    """Coordinates the trial execution, validation, and grading."""

    def __init__(self, config: Dict[str, Any], model_slot: str):
        self.config = config
        self.model_slot = model_slot
        
        self.backend = create_backend(config_dict=config)
        self.task_loader = TaskLoader()
        self.logger = TrialLogger(f"phase3/logs/trials_{self.model_slot}.jsonl")
        
        self.required_trials = 450
        self.execution_count = 0
        self.tool_call_count = 0
        self.trace_count = 0
        
    def execute_environment(self) -> None:
        """Placeholder interface for future MCP integration."""
        raise NotImplementedError("TODO: Implement MCP environment execution")

    def execute_trial(self, trial, prompt_text: str) -> Dict[str, Any]:
        """Executes a single trial and returns the raw trial dictionary."""
        # Support future MCP integration
        try:
            self.execute_environment()
        except NotImplementedError:
            pass # Currently stubbed
            
        # Execute LLM Inference
        inference_params = {
            "temperature": 0.0,
            "seed": 3301,
            "num_predict": 1024,
            "context_window": 4096,
            "top_p": 1.0,
            "repeat_penalty": 1.0
        }
        
        try:
            response = self.backend.generate(prompt_text, inference_params)
        except ExecutionError as e:
            logger.error(f"Trial {trial.task_id} failed backend generation: {e}")
            raise
            
        # Mock grading and constraints for now (will be implemented in graders layer)
        return {
            "trial_id": trial.task_id,
            "counts_toward_cell_n": True,
            "infrastructure_valid": True,
            "reset_integrity_passed": True,
            "trial_acceptance_valid": True,
            "malformed_output": False,
            "backend_parameters": response.get("backend_parameters", {}),
            "timeout_classification": "NONE",
            "borderline_confirmation": False,
            "raw_output": response.get("raw_output", "")
        }

    def resume_from_checkpoint(self) -> None:
        """Resumes execution from the last valid checkpoint."""
        self.logger.resume()

    def execute_batch(self, matrix_file: str, tasks_file: str) -> ExecutionStatus:
        """Executes a batch of trials from the provided matrix."""
        self.resume_from_checkpoint()
        
        # We need 450 valid trials.
        if self.logger.count_valid_trials() >= self.required_trials:
            logger.info("Already reached required valid trial count.")
            return ExecutionStatus(
                total_trials_run=len(self.logger.get_completed_trial_ids()),
                valid_trials_completed=self.logger.count_valid_trials(),
                interrupted=False
            )
            
        logger.info(f"Loading trials from {matrix_file} and {tasks_file}")
        trials = self.task_loader.load_trials(matrix_file, tasks_file)
        
        if not trials:
            raise ExecutionError("No trials loaded from task loader.")
            
        logger.info(f"Loaded {len(trials)} trials in total.")
        
        completed_ids = self.logger.get_completed_trial_ids()
        pending_trials = [t for t in trials if t.task_id not in completed_ids]
        
        logger.info(f"Remaining pending trials: {len(pending_trials)}")
        
        if not pending_trials and self.logger.count_valid_trials() < self.required_trials:
            raise ExecutionError("No pending trials remaining but required count not met. Matrix exhausted.")
            
        model_id = self.config.get('model_name', 'unknown')
        logger.info(f"Loading model backend for {model_id}...")
        self.backend.load_model(model_id)
        
        interrupted = False
        trials_run_this_session = 0
        
        try:
            for trial in pending_trials:
                if self.logger.count_valid_trials() >= self.required_trials:
                    logger.info("Reached required 450 valid trials. Stopping batch.")
                    break
                    
                # Construct simple prompt stub for now until prompt builder is integrated
                prompt_text = trial.task_definition.get('user_task', "Default prompt")
                
                try:
                    trial_result = self.execute_trial(trial, prompt_text)
                    self.logger.append_result(trial_result)
                    trials_run_this_session += 1
                except ExecutionError as e:
                    logger.error(f"Trial failed with ExecutionError: {e}. Skipping to next.")
                    continue
                except KeyboardInterrupt:
                    logger.warning("Interrupted by user. Shutting down gracefully.")
                    interrupted = True
                    break
                except Exception as e:
                    logger.error(f"Unexpected error during trial: {e}")
                    raise
                    
        finally:
            self.backend.unload_model()
            self.logger.close()
            
        return ExecutionStatus(
            total_trials_run=trials_run_this_session,
            valid_trials_completed=self.logger.count_valid_trials(),
            interrupted=interrupted
        )

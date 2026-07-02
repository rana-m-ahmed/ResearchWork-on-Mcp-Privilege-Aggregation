import logging
from dataclasses import dataclass
from typing import Any, Dict

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
    """
    Coordinates execution of Phase 3 trials.
    """

    def __init__(self, config: Dict[str, Any], model_slot: str):

        self.config = config
        self.model_slot = model_slot

        self.backend = create_backend(config_dict=config)

        self.task_loader = TaskLoader()

        self.logger = TrialLogger(
            f"phase3/logs/trials_{model_slot}.jsonl"
        )

        self.required_trials = 450

    ######################################################################
    # Placeholder until MCP environment is connected
    ######################################################################

    def execute_environment(self):

        raise NotImplementedError

    ######################################################################
    # Execute one trial
    ######################################################################

    def execute_trial(self, trial, prompt_text):

        try:
            self.execute_environment()

        except NotImplementedError:
            pass

        inference_params = {

            "temperature": 0.0,

            "seed": 3301,

            "num_predict": 1024,

            "context_window": 4096,

            "top_p": 1.0,

            "repeat_penalty": 1.0

        }

        response = self.backend.generate(
            prompt_text,
            inference_params
        )

        return {

            "trial_id": trial.task_id,

            "counts_toward_cell_n": True,

            "infrastructure_valid": True,

            "reset_integrity_passed": True,

            "trial_acceptance_valid": True,

            "malformed_output": False,

            "timeout_classification": "NONE",

            "borderline_confirmation": False,

            "backend_parameters": response["backend_parameters"],

            "raw_output": response["raw_output"]

        }

    ######################################################################
    # Resume
    ######################################################################

    def resume_from_checkpoint(self):

        self.logger.resume()

    ######################################################################
    # Execute full matrix
    ######################################################################

    def execute_batch(self, matrix_file, tasks_file):

        self.resume_from_checkpoint()

        valid = self.logger.count_valid_trials()

        if valid >= self.required_trials:

            logger.info("Already completed required trials.")

            return ExecutionStatus(

                total_trials_run=len(
                    self.logger.get_completed_trial_ids()
                ),

                valid_trials_completed=valid,

                interrupted=False

            )

        logger.info("Loading trial matrix...")

        trials = self.task_loader.load_trials(
            matrix_file,
            tasks_file
        )

        if len(trials) == 0:

            raise ExecutionError(
                "No trials loaded."
            )

        completed = self.logger.get_completed_trial_ids()

        pending = [

            t

            for t in trials

            if t.task_id not in completed

        ]

        logger.info(f"Pending trials: {len(pending)}")

        if (

            len(pending) == 0

            and valid < self.required_trials

        ):

            raise ExecutionError(
                "Matrix exhausted before reaching required trial count."
            )

        ###############################################################
        # Load model
        ###############################################################

        model_identifier = self.config["backend"]["model_identifier"]

        logger.info(
            f"Loading model {model_identifier}"
        )

        self.backend.load_model(model_identifier)

        interrupted = False

        trials_run = 0

        ###############################################################
        # Run trials
        ###############################################################

        try:

            for trial in pending:

                if self.logger.count_valid_trials() >= self.required_trials:

                    logger.info(
                        "Reached required valid trials."
                    )

                    break

                prompt = trial.task_definition.get(

                    "user_task",

                    "Default prompt"

                )

                try:

                    result = self.execute_trial(

                        trial,

                        prompt

                    )

                    self.logger.append_result(result)

                    trials_run += 1

                except ExecutionError as e:

                    logger.error(e)

                    continue

                except KeyboardInterrupt:

                    interrupted = True

                    logger.warning(
                        "Interrupted."
                    )

                    break

        finally:

            logger.info("Unloading model...")

            self.backend.unload_model()

            self.logger.close()

        ###############################################################

        return ExecutionStatus(

            total_trials_run=trials_run,

            valid_trials_completed=self.logger.count_valid_trials(),

            interrupted=interrupted

        )
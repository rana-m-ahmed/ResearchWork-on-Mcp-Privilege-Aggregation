import logging
from typing import Any, Dict, List
from .templates import SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class PromptBuilder:
    """Constructs context windows and schemas for the LLM."""

    def construct_prompt(self, task: Dict[str, Any], tool_schemas: List[Dict[str, Any]]) -> str:
        """Builds the complete prompt string."""
        raise NotImplementedError("TODO: Implement construct_prompt")
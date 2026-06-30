import logging
from typing import Any, Dict, List
from .tool_matcher import ToolMatcher

logger = logging.getLogger(__name__)

class TrialGrader:
    """Evaluates LLM tool usage against expected sequences."""

    def grade(self, actual_response: str, expected_tools: List[str]) -> Dict[str, Any]:
        raise NotImplementedError("TODO: Implement grade")
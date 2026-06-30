import logging
from typing import List

logger = logging.getLogger(__name__)

class ToolMatcher:
    """Matches generated tool calls to the schema."""

    def match_sequence(self, actual: List[str], expected: List[str]) -> bool:
        raise NotImplementedError("TODO: Implement match_sequence")
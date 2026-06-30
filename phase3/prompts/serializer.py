import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class PromptSerializer:
    """Serializes tool calls and schemas into prompt-friendly formats."""

    def serialize_tools(self, tools: list) -> str:
        raise NotImplementedError("TODO: Implement serialize_tools")
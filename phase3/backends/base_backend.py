import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)

class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def load_model(self, model_identifier: str) -> None:
        """Loads the specific model."""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Unloads the model to free memory."""
        pass

    @abstractmethod
    def generate(self, prompt: str, inference_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a response from the LLM."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if the backend is healthy and responding."""
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Returns metadata about the currently loaded model."""
        pass

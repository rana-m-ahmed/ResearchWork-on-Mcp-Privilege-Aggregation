import logging
import json
import urllib.request
import urllib.error
import socket
from typing import Any, Dict, Optional
from .base_backend import LLMBackend
from ..utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)

class OllamaBackend(LLMBackend):
    """Concrete implementation for Ollama HTTP API backend."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.current_model: Optional[str] = None
        # Models supported for Phase 3
        self.supported_models = {
            "qwen2.5-7b-instruct",
            "llama-3.1-8b-instruct",
            "mistral-7b-instruct-v0.3",
            "gemma-2-9b-it"
        }

    def _normalize_model_name(self, name: str) -> str:
        name_lower = name.lower()
        if "mistral" in name_lower:
            return "mistral-7b-instruct-v0.3"
        if "llama" in name_lower:
            return "llama-3.1-8b-instruct"
        if "qwen" in name_lower:
            return "qwen2.5-7b-instruct"
        if "gemma" in name_lower:
            return "gemma-2-9b-it"
        return name

    def health_check(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def load_model(self, model_identifier: str) -> None:
        model_name = self._normalize_model_name(model_identifier)
        logger.info(f"Loading Ollama model: {model_name}")
        self.current_model = model_name
        try:
            data = json.dumps({"model": self.current_model, "keep_alive": "5m"}).encode('utf-8')
            req = urllib.request.Request(f"{self.base_url}/api/generate", data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as response:
                response.read()
        except urllib.error.URLError as e:
            raise ExecutionError(f"Failed to load model {model_name}: Connection error {e}")
        except Exception as e:
            raise ExecutionError(f"Unexpected error loading model: {e}")

    def unload_model(self) -> None:
        if not self.current_model:
            return
        logger.info(f"Unloading Ollama model: {self.current_model}")
        try:
            data = json.dumps({"model": self.current_model, "keep_alive": 0}).encode('utf-8')
            req = urllib.request.Request(f"{self.base_url}/api/generate", data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()
        except Exception as e:
            logger.warning(f"Failed to cleanly unload model: {e}")
        self.current_model = None

    def generate(self, prompt: str, inference_params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.current_model:
            raise ExecutionError("No model loaded.")

        requested = {
            "temperature": inference_params.get("temperature", 0.0),
            "num_predict": inference_params.get("num_predict", 1024),
            "top_p": inference_params.get("top_p", 1.0),
            "repeat_penalty": inference_params.get("repeat_penalty", 1.0),
            "num_ctx": inference_params.get("context_window", 4096),
            "seed": inference_params.get("seed", 3301)
        }

        payload = {
            "model": self.current_model,
            "prompt": prompt,
            "stream": False,
            "options": requested
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f"{self.base_url}/api/generate", data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                if response.status != 200:
                    raise ExecutionError(f"Invalid response from backend: {response.status}")
                result_bytes = response.read()
                result_json = json.loads(result_bytes)
        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout) or "timeout" in str(e.reason).lower():
                raise ExecutionError("Backend timeout during generation")
            raise ExecutionError(f"Connection failure: {e}")
        except json.JSONDecodeError:
            raise ExecutionError("Invalid JSON response from backend")
        except Exception as e:
            if "memory" in str(e).lower() or "oom" in str(e).lower():
                raise ExecutionError("OOM error during generation")
            raise ExecutionError(f"Unexpected backend error: {e}")

        return {
            "raw_output": result_json.get("response", ""),
            "backend_parameters": {
                "requested": requested,
                "effective": requested,
                "backend_reported": {
                    "eval_count": result_json.get("eval_count"),
                    "eval_duration": result_json.get("eval_duration"),
                    "total_duration": result_json.get("total_duration")
                }
            }
        }

    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "ollama",
            "model_name": self.current_model
        }

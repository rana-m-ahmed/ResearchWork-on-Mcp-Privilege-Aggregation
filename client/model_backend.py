"""
Model backend abstraction for Phase 2.

Provides two backends:
  1. ScriptedFakeModel — deterministic fake model for infrastructure smoke tests
  2. LocalLLMBackend  — calls a local Ollama/llama.cpp endpoint for LLM smoke tests

Hard constraints:
  - No cloud LLM APIs.
  - Mode A (containerized) is default.
  - Mode B (host-local) is a documented exception.
"""

from __future__ import annotations

import json
from typing import Any


class ScriptedFakeModel:
    """Deterministic scripted model that returns pre-configured tool calls.

    Used for infrastructure smoke tests to prove the pipeline works
    end-to-end without requiring a real LLM.
    """

    def __init__(self, scripted_responses: list[dict[str, Any]] | None = None):
        self._responses = scripted_responses or []
        self._call_index = 0

    @property
    def backend_mode(self) -> str:
        return "scripted_fake_model"

    @property
    def backend_name(self) -> str:
        return "scripted_fake_model"

    @property
    def model_name(self) -> str | None:
        return None

    @property
    def model_version(self) -> str | None:
        return None

    def generate(self, prompt: str) -> dict[str, Any]:
        """Return the next scripted response.

        Returns a dict with keys:
          - raw_output: str  (the raw model text)
          - tool_calls: list[dict]  (parsed tool call dicts)
          - error: str | None
        """
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        return {
            "raw_output": "",
            "tool_calls": [],
            "error": "no_more_scripted_responses",
        }

    def reset(self) -> None:
        self._call_index = 0


class LocalLLMBackend:
    """Calls a local model endpoint (Ollama or llama.cpp).

    Mode A: endpoint inside Docker network (e.g. http://ollama:11434)
    Mode B: host-local endpoint (e.g. http://host.docker.internal:11434)
    """

    def __init__(
        self,
        endpoint: str = "http://ollama:11434",
        model: str = "llama3.2:1b",
        backend_mode: str = "containerized",
    ):
        self._endpoint = endpoint
        self._model = model
        self._backend_mode = backend_mode

    @property
    def backend_mode(self) -> str:
        return self._backend_mode

    @property
    def backend_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str | None:
        return self._model

    @property
    def model_version(self) -> str | None:
        return None  # Populated from Ollama API at runtime

    def generate(self, prompt: str) -> dict[str, Any]:
        """Call the local model endpoint and return structured output.

        Returns a dict with keys:
          - raw_output: str
          - tool_calls: list[dict]
          - error: str | None
        """
        import urllib.request
        import urllib.error

        url = f"{self._endpoint}/api/generate"
        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            raw = body.get("response", "")
            return {
                "raw_output": raw,
                "tool_calls": [],  # Parsing handled by tool_call_parser
                "error": None,
            }
        except urllib.error.URLError as exc:
            return {
                "raw_output": "",
                "tool_calls": [],
                "error": f"model_unreachable: {exc}",
            }
        except Exception as exc:
            return {
                "raw_output": "",
                "tool_calls": [],
                "error": f"model_error: {exc}",
            }

    def reset(self) -> None:
        pass

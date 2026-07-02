import logging
import os
from typing import Any, Dict

from .base_backend import LLMBackend
from .transformers_backend import TransformersBackend

logger = logging.getLogger(__name__)


def parse_yaml_naive(filepath: str) -> Dict[str, str]:
    result = {}

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip().strip('"').strip("'")

    return result


def create_backend(
    config_path: str = None,
    config_dict: Dict[str, Any] = None,
) -> LLMBackend:

    cfg = {}

    if config_dict:
        cfg = config_dict

    elif config_path and os.path.exists(config_path):
        cfg = parse_yaml_naive(config_path)

    backend = TransformersBackend()

    model_name = None

    if "backend" in cfg:
        model_name = cfg["backend"].get("model_identifier")

    elif "model_name" in cfg:
        model_name = cfg["model_name"]

    if model_name:
        logger.info(f"Backend initialized for {model_name}")

    return backend
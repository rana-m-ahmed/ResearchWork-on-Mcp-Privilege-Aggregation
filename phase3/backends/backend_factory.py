import logging
import os
from typing import Any, Dict
from .base_backend import LLMBackend
from .transformers_backend import TransformersBackend
from ..utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

def parse_yaml_naive(filepath: str) -> Dict[str, str]:
    """A naive YAML parser since we have zero dependencies like PyYAML."""
    result = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, val = line.split(':', 1)
                result[key.strip()] = val.strip().strip('"').strip("'")
    return result

def create_backend(config_path: str = None, config_dict: Dict[str, Any] = None) -> LLMBackend:
    """Factory method to create the appropriate LLM backend."""
    cfg = {}
    if config_dict:
        cfg = config_dict
    elif config_path and os.path.exists(config_path):
        cfg = parse_yaml_naive(config_path)
    
    # Defaults to OllamaBackend for Phase 3 based on current constraints
    backend = TransformersBackend()
    
    if 'model_name' in cfg:
        # We don't automatically load the model here, the orchestrator manages loading/unloading
        logger.info(f"Factory initialized backend with config containing model: {cfg['model_name']}")
    
    return backend

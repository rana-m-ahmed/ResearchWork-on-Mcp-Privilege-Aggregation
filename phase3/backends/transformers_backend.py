import gc
import logging
from typing import Any, Dict, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .base_backend import LLMBackend
from ..utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)


class TransformersBackend(LLMBackend):
    """
    HuggingFace Transformers backend for Phase 3.

    Loads one model at a time, performs inference, then unloads it
    before the next model is evaluated.
    """

    def __init__(self):
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.current_model: Optional[str] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def health_check(self) -> bool:
        return True

    def load_model(self, model_identifier: str) -> None:
        """
        Loads a HuggingFace model.
        """

        logger.info(f"Loading model: {model_identifier}")

        try:

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_identifier,
                trust_remote_code=True
            )

            # Some models (Gemma/Qwen) don't define a pad token.
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                model_identifier,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )

            self.current_model = model_identifier

            # Put model into inference mode
            self.model.eval()

            logger.info(f"Successfully loaded {model_identifier}")

        except Exception as e:
            raise ExecutionError(
                f"Failed to load model {model_identifier}: {e}"
            )

    def unload_model(self) -> None:
        """
        Releases GPU memory after finishing one model.
        """

        logger.info(f"Unloading model {self.current_model}")

        if self.model is not None:
            del self.model

        if self.tokenizer is not None:
            del self.tokenizer

        self.model = None
        self.tokenizer = None
        self.current_model = None

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def generate(
        self,
        prompt: str,
        inference_params: Dict[str, Any]
    ) -> Dict[str, Any]:

        if self.model is None:
            raise ExecutionError("No model loaded.")

        try:

            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=inference_params.get("context_window", 4096)
            ).to(self.model.device)

            with torch.no_grad():

                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=inference_params.get(
                        "num_predict",
                        1024
                    ),
                    temperature=inference_params.get(
                        "temperature",
                        0.0
                    ),
                    top_p=inference_params.get(
                        "top_p",
                        1.0
                    ),
                    do_sample=inference_params.get(
                        "temperature",
                        0.0
                    ) > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

            generated = outputs[0][inputs["input_ids"].shape[1]:]

            text = self.tokenizer.decode(
                generated,
                skip_special_tokens=True
            )

            del outputs
            del generated
            del inputs

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return {
                "raw_output": text,
                "backend_parameters": {
                    "requested": inference_params,
                    "effective": inference_params,
                    "backend_reported": {}
                }
            }

        except Exception as e:
            raise ExecutionError(f"Generation failed: {e}")

    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "transformers",
            "model_name": self.current_model,
            "device": self.device
        }
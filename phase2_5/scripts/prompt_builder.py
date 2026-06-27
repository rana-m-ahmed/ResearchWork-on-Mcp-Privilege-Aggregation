
import json
import unicodedata
from typing import Dict, Any

class PromptBuilder:
    def __init__(self):
        self.system_prompt = ""
        self.task_string = ""
        self.schema_data = {}
        self.capability_advertisement = ""
        self.payload = ""
        self.history = ""

    def normalize_general_text(self, text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFC", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.strip()
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text

    def serialize_deterministic_json(self, obj: dict) -> str:
        if not obj:
            return ""
        return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def assemble_prompt(self, system_prompt: str, task_string: str, schema_dict: dict, cap_adv: str, payload_string: str) -> Dict[str, Any]:
        self.system_prompt = self.normalize_general_text(system_prompt)
        self.task_string = self.normalize_general_text(task_string)
        self.capability_advertisement = self.normalize_general_text(cap_adv)
        self.schema_data = self.serialize_deterministic_json(schema_dict)
        self.payload = payload_string 

        full_context_prompt = (
            f"<|system|>\n{self.system_prompt}\n"
            f"Available Tools (Schemas):\n{self.schema_data}\n"
            f"Metadata Context:\n{self.capability_advertisement}\n"
            f"Retrieved Content:\n{self.payload}\n"
            f"<|user|>\n{self.task_string}\n"
            f"<|assistant|>\n"
        )

        return {
            "full_prompt": full_context_prompt,
            "components": {
                "system": self.system_prompt,
                "schemas": self.schema_data,
                "cap_adv": self.capability_advertisement,
                "payload": self.payload,
                "task": self.task_string,
                "history": ""
            }
        }


"""Static validation helpers for the P15 Kaggle handoff notebook."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path

from ..guards import scan_text_for_forbidden_analysis, scan_text_for_secrets
from .handoff import (
    EDITABLE_PARAMETER_KEYS,
    NOTEBOOK_STAGE_SEQUENCE,
    PUBLIC_CLI_PREFIX,
)


ALLOWED_NOTEBOOK_IMPORTS = (
    "from phase5.kaggle.handoff import",
    "from pathlib import Path",
    "import sys",
)


@dataclass(frozen=True, slots=True)
class StaticNotebookValidationReport:
    notebook_path: Path
    schema_path: Path
    status: str
    findings: tuple[str, ...]
    stage_sequence: tuple[str, ...]
    editable_parameter_keys: tuple[str, ...]
    public_cli_prefix: tuple[str, ...]
    secret_scan_findings: tuple[str, ...]
    forbidden_findings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "editable_parameter_keys": list(self.editable_parameter_keys),
            "findings": list(self.findings),
            "forbidden_findings": list(self.forbidden_findings),
            "notebook_path": self.notebook_path.as_posix(),
            "public_cli_prefix": list(self.public_cli_prefix),
            "schema_path": self.schema_path.as_posix(),
            "secret_scan_findings": list(self.secret_scan_findings),
            "stage_sequence": list(self.stage_sequence),
            "status": self.status,
        }

    def to_markdown(self) -> str:
        lines = [
            "# P15 Notebook Static Validation Report",
            "",
            f"- Notebook: `{self.notebook_path.as_posix()}`",
            f"- Schema: `{self.schema_path.as_posix()}`",
            f"- Status: `{self.status}`",
            "",
            "## Stage Sequence",
        ]
        lines.extend(f"- `{stage}`" for stage in self.stage_sequence)
        lines.extend(["", "## Editable Parameters"])
        lines.extend(f"- `{key}`" for key in self.editable_parameter_keys)
        lines.extend(["", "## Findings"])
        if self.findings:
            lines.extend(f"- {item}" for item in self.findings)
        else:
            lines.append("- none")
        lines.extend(["", "## Secret Scan"])
        if self.secret_scan_findings:
            lines.extend(f"- {item}" for item in self.secret_scan_findings)
        else:
            lines.append("- none")
        lines.extend(["", "## Forbidden Outcome Scan"])
        if self.forbidden_findings:
            lines.extend(f"- {item}" for item in self.forbidden_findings)
        else:
            lines.append("- none")
        return "\n".join(lines) + "\n"


def load_notebook(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell_source(cell: dict[str, object]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return str(source)


def notebook_text(notebook: dict[str, object]) -> str:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise TypeError("notebook cells must be a list")
    return "\n".join(_cell_source(cell) for cell in cells if isinstance(cell, dict))


def extract_stage_sequence(notebook: dict[str, object]) -> tuple[str, ...]:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise TypeError("notebook cells must be a list")
    sequence: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        metadata = cell.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        stage = metadata.get("phase5_stage")
        if isinstance(stage, str):
            sequence.append(stage)
    return tuple(sequence)


def validate_stage_sequence(notebook: dict[str, object]) -> list[str]:
    sequence = extract_stage_sequence(notebook)
    if sequence != NOTEBOOK_STAGE_SEQUENCE:
        return [f"stage-sequence-mismatch:{list(sequence)!r}"]
    return []


def validate_editable_parameter_whitelist(notebook: dict[str, object], schema: Path) -> list[str]:
    issues: list[str] = []
    data = json.loads(schema.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ["schema-not-mapping"]
    properties = data.get("properties")
    if not isinstance(properties, dict):
        issues.append("schema-missing-properties")
    else:
        schema_keys = set(properties.keys())
        if schema_keys != set(EDITABLE_PARAMETER_KEYS):
            issues.append(f"schema-keys-mismatch:{sorted(schema_keys)!r}")

    text = notebook_text(notebook)
    match = re.search(r"KaggleHandoffParameters\((.*?)\)", text, re.DOTALL)
    if match is None:
        issues.append("missing-kagglehandoffparameters-call")
        return issues
    arg_block = match.group(1)
    found = tuple(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", arg_block))
    if found != EDITABLE_PARAMETER_KEYS:
        issues.append(f"parameter-whitelist-mismatch:{found!r}")
    return issues


def validate_public_cli_only(notebook: dict[str, object], handoff_source: str) -> list[str]:
    issues: list[str] = []
    text = notebook_text(notebook)
    if "phase5.sync" in text or "phase5.campaign" in text or "phase5.cli" in text:
        issues.append("notebook-imports-internal-phase5-logic")
    for import_hint in ALLOWED_NOTEBOOK_IMPORTS:
        if import_hint not in text:
            issues.append(f"missing-import:{import_hint}")
    if "from phase5.kaggle.handoff import" not in text:
        issues.append("notebook-must-import-handoff-module")

    if "python -m phase5" not in handoff_source:
        issues.append("handoff-source-missing-public-cli-prefix")
    if "phase5.sync" in handoff_source or "phase5.campaign" in handoff_source:
        issues.append("handoff-source-imports-internal-implementation")
    return issues


def validate_scans(notebook: dict[str, object]) -> tuple[list[str], list[str]]:
    text = notebook_text(notebook)
    secret_findings = scan_text_for_secrets(text)
    forbidden_findings = scan_text_for_forbidden_analysis(text)
    return secret_findings, forbidden_findings


def validate_notebook(
    notebook_path: Path,
    schema_path: Path,
    *,
    handoff_source: str,
) -> StaticNotebookValidationReport:
    notebook = load_notebook(notebook_path)
    findings: list[str] = []
    findings.extend(validate_stage_sequence(notebook))
    findings.extend(validate_editable_parameter_whitelist(notebook, schema_path))
    findings.extend(validate_public_cli_only(notebook, handoff_source))
    secret_findings, forbidden_findings = validate_scans(notebook)
    if secret_findings:
        findings.append("secret-scan-failed")
    if forbidden_findings:
        findings.append("forbidden-scan-failed")
    status = "PASS" if not findings else "FAIL"
    return StaticNotebookValidationReport(
        notebook_path=notebook_path,
        schema_path=schema_path,
        status=status,
        findings=tuple(findings),
        stage_sequence=extract_stage_sequence(notebook),
        editable_parameter_keys=EDITABLE_PARAMETER_KEYS,
        public_cli_prefix=PUBLIC_CLI_PREFIX,
        secret_scan_findings=tuple(secret_findings),
        forbidden_findings=tuple(forbidden_findings),
    )


def render_notebook_validation_report(report: StaticNotebookValidationReport) -> str:
    return report.to_markdown()


def write_notebook_validation_report(
    notebook_path: Path,
    schema_path: Path,
    output_md: Path,
    output_json: Path,
    *,
    handoff_source: str,
) -> StaticNotebookValidationReport:
    report = validate_notebook(notebook_path, schema_path, handoff_source=handoff_source)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(report.to_markdown(), encoding="utf-8")
    output_json.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report

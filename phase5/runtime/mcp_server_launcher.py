"""Loopback-only FastMCP launcher and discovery probes for Phase 5."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..domain.errors import RuntimeMismatchError, SchemaInvariantError
from .workspace_isolation import AttemptWorkspaceIsolation
from .tool_dispatch import ToolSpecification
from server.schema_variant_loader import resolve_schema_path

try:  # pragma: no cover - validated by runtime tests
    from server.mock_server import build_server as default_server_factory
except Exception:  # pragma: no cover
    default_server_factory = None


RESET_TOOL_NAME = "reset"
LOOPBACK_HOST = "127.0.0.1"


def is_loopback_host(host: str) -> bool:
    """Return True only for the frozen loopback host required by Phase 5."""

    if host != LOOPBACK_HOST:
        return False
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _require_loopback_host(host: str) -> None:
    if not is_loopback_host(host):
        raise RuntimeMismatchError(f"FastMCP must bind to {LOOPBACK_HOST}, not {host!r}")


def _set_server_endpoint(server: Any, host: str, port: int) -> None:
    for attribute, value in (("host", host), ("port", port)):
        try:
            setattr(server, attribute, value)
        except Exception as exc:  # pragma: no cover - defensive
            raise SchemaInvariantError(f"validated FastMCP object does not accept {attribute!r} overrides") from exc


def discover_tool_names(server: Any) -> tuple[str, ...]:
    """Return the discovered MCP tool names from a FastMCP instance."""

    tool_manager = getattr(server, "_tool_manager", None)
    tools = getattr(tool_manager, "_tools", None)
    if not isinstance(tools, dict):
        raise SchemaInvariantError("validated FastMCP object does not expose a tool registry")
    return tuple(sorted(str(name) for name in tools))


@dataclass(frozen=True, slots=True)
class ResetDispatchProbe:
    rejected: bool
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class LaunchVerification:
    server: Any
    host: str
    port: int
    tool_names: tuple[str, ...]
    reset_hidden: bool
    reset_dispatch: ResetDispatchProbe
    schema_variant: Mapping[str, Any]
    schema_source_path: Path
    schema_source_sha256: str


def _probe_reset_dispatch(server: Any) -> ResetDispatchProbe:
    async def _call_reset() -> ResetDispatchProbe:
        try:
            await server.call_tool(RESET_TOOL_NAME, {})
        except Exception as exc:  # ToolError is expected and treated as rejection.
            message = str(exc)
            if "unknown tool" not in message.lower():
                raise SchemaInvariantError(
                    f"reset dispatch rejected for the wrong reason: {type(exc).__name__}: {message}"
                ) from exc
            return ResetDispatchProbe(rejected=True, error_type=type(exc).__name__, error_message=message)
        raise SchemaInvariantError("reset unexpectedly dispatched through MCP")

    return asyncio.run(_call_reset())


def probe_reset_dispatch(server: Any) -> ResetDispatchProbe:
    """Fail closed if a model-facing reset call is accepted by MCP."""

    return _probe_reset_dispatch(server)


@dataclass
class McpServerLauncher:
    """Validated launcher for the Phase 5 FastMCP server."""

    variant_id: str = "D3-CLEAN"
    host: str = LOOPBACK_HOST
    port: int = 8000
    server_factory: Callable[[str], Any] | None = default_server_factory
    workspace: AttemptWorkspaceIsolation | None = None
    restart_count: int = 0

    def build_server(self) -> Any:
        if self.server_factory is None:
            raise SchemaInvariantError("no FastMCP server factory is available")
        return self.server_factory(self.variant_id)

    def validate(self) -> LaunchVerification:
        _require_loopback_host(self.host)
        server = self.build_server()
        _set_server_endpoint(server, self.host, self.port)
        tool_names = discover_tool_names(server)
        if RESET_TOOL_NAME in tool_names:
            raise SchemaInvariantError("reset must remain absent from MCP discovery")
        reset_dispatch = probe_reset_dispatch(server)
        schema_variant = getattr(server, "_phase2_schema", None)
        if not isinstance(schema_variant, Mapping):
            raise SchemaInvariantError("validated FastMCP object does not expose its schema variant")
        schema_source_path, _ = resolve_schema_path(self.variant_id)
        if not schema_source_path.is_file():
            raise SchemaInvariantError(f"schema variant source is missing: {schema_source_path.as_posix()}")
        source_document = json.loads(schema_source_path.read_text(encoding="utf-8"))
        if source_document != dict(schema_variant):
            raise SchemaInvariantError("runtime MCP schema differs from its source artifact")
        manifest_path = Path(__file__).resolve().parents[2] / "phase5_5/configs/schema_variant_manifest_v3.json"
        if not manifest_path.is_file():
            raise SchemaInvariantError("Phase 5.5 schema variant manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_entry = manifest.get("variants", {}).get(self.variant_id)
        if not isinstance(manifest_entry, Mapping):
            raise SchemaInvariantError(f"schema variant is absent from the Phase 5.5 manifest: {self.variant_id!r}")
        repository_root = Path(__file__).resolve().parents[2]
        relative_schema_path = schema_source_path.relative_to(repository_root).as_posix()
        if manifest_entry.get("path") != relative_schema_path:
            raise SchemaInvariantError("schema variant manifest path mismatch")
        canonical_schema_bytes = schema_source_path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        actual_schema_sha256 = hashlib.sha256(canonical_schema_bytes).hexdigest()
        if manifest_entry.get("sha256") != actual_schema_sha256:
            raise SchemaInvariantError("schema variant manifest hash mismatch")
        return LaunchVerification(
            server=server,
            host=self.host,
            port=self.port,
            tool_names=tool_names,
            reset_hidden=True,
            reset_dispatch=reset_dispatch,
            schema_variant=dict(schema_variant),
            schema_source_path=schema_source_path,
            schema_source_sha256=actual_schema_sha256,
        )

    def restart(self) -> LaunchVerification:
        """Discard the prior server object and validate a fresh one."""

        self.restart_count += 1
        return self.validate()


def build_validated_server(
    *,
    variant_id: str = "D3-CLEAN",
    host: str = LOOPBACK_HOST,
    port: int = 8000,
    workspace: AttemptWorkspaceIsolation | None = None,
    server_factory: Callable[[str], Any] | None = default_server_factory,
) -> LaunchVerification:
    launcher = McpServerLauncher(
        variant_id=variant_id,
        host=host,
        port=port,
        server_factory=server_factory,
        workspace=workspace,
    )
    return launcher.validate()


def build_fastmcp_tool_catalog(verification: LaunchVerification) -> dict[str, ToolSpecification]:
    """Build dispatch specifications backed by the validated FastMCP call path."""

    tool_manager = getattr(verification.server, "_tool_manager", None)
    registered = getattr(tool_manager, "_tools", None)
    if not isinstance(registered, dict):
        raise SchemaInvariantError("validated FastMCP object does not expose registered tool contracts")

    schema_entries = verification.schema_variant.get("tools")
    if not isinstance(schema_entries, list):
        raise SchemaInvariantError("MCP schema variant must contain a tool list")
    entries_by_name: dict[str, Mapping[str, Any]] = {}
    for entry in schema_entries:
        if not isinstance(entry, Mapping):
            raise SchemaInvariantError("MCP schema tool entry must be an object")
        exposed_name = entry.get("exposed_tool_name")
        if not isinstance(exposed_name, str) or not exposed_name:
            raise SchemaInvariantError("MCP schema tool entry is missing exposed_tool_name")
        if exposed_name in entries_by_name:
            raise SchemaInvariantError(f"duplicate MCP schema tool entry: {exposed_name!r}")
        entries_by_name[exposed_name] = entry

    catalog: dict[str, ToolSpecification] = {}
    for tool_name in verification.tool_names:
        tool = registered.get(tool_name)
        parameters = getattr(tool, "parameters", None)
        if not isinstance(parameters, dict):
            raise SchemaInvariantError(f"FastMCP tool {tool_name!r} is missing its parameter schema")
        required = parameters.get("required", ())
        if not isinstance(required, (list, tuple)) or not all(isinstance(item, str) for item in required):
            raise SchemaInvariantError(f"FastMCP tool {tool_name!r} has an invalid required-argument schema")
        schema_entry = entries_by_name.get(tool_name)
        if schema_entry is None:
            raise SchemaInvariantError(f"discovered tool {tool_name!r} is absent from the source schema")
        parameter_schema = schema_entry.get("parameters")
        description = schema_entry.get("description")
        logical_name = schema_entry.get("logical_tool_id")
        if not isinstance(parameter_schema, Mapping):
            raise SchemaInvariantError(f"source schema for {tool_name!r} is missing parameters")
        if not isinstance(description, str) or not description:
            raise SchemaInvariantError(f"source schema for {tool_name!r} is missing its description")
        if not isinstance(logical_name, str) or not logical_name:
            raise SchemaInvariantError(f"source schema for {tool_name!r} is missing logical_tool_id")
        if tuple(parameter_schema.get("required", ())) != tuple(required):
            raise SchemaInvariantError(f"FastMCP/source required-argument mismatch for {tool_name!r}")

        def handler(arguments: dict[str, Any], *, current_name: str = tool_name) -> str:
            async def invoke() -> Any:
                return await verification.server.call_tool(current_name, arguments)

            response = asyncio.run(invoke())
            if not isinstance(response, list) or not response:
                raise SchemaInvariantError(f"FastMCP tool {current_name!r} returned an empty response")
            text_parts = [getattr(item, "text", None) for item in response]
            if not all(isinstance(item, str) for item in text_parts):
                raise SchemaInvariantError(f"FastMCP tool {current_name!r} returned unsupported content")
            if len(text_parts) == 1:
                return text_parts[0]
            return json.dumps(text_parts, ensure_ascii=False, separators=(",", ":"))

        catalog[tool_name] = ToolSpecification(
            exposed_tool_name=tool_name,
            logical_tool_name=logical_name,
            required_arguments=tuple(required),
            description=description,
            parameter_schema=dict(parameter_schema),
            handler=handler,
        )
    return catalog


def build_model_facing_discovery(
    verification: LaunchVerification,
    tool_catalog: Mapping[str, ToolSpecification],
) -> dict[str, Any]:
    """Return the exact, hash-bound MCP metadata delivered to the model."""

    capability = verification.schema_variant.get("capability_advertisement")
    variant_id = verification.schema_variant.get("schema_variant_id")
    if not isinstance(capability, str) or not capability:
        raise SchemaInvariantError("MCP schema variant is missing capability_advertisement")
    if not isinstance(variant_id, str) or not variant_id:
        raise SchemaInvariantError("MCP schema variant is missing schema_variant_id")
    tools = []
    for name in verification.tool_names:
        specification = tool_catalog[name]
        if specification.description is None or not specification.parameter_schema:
            raise SchemaInvariantError(f"tool {name!r} lacks model-facing metadata")
        tools.append({
            "description": specification.description,
            "exposed_tool_name": specification.exposed_tool_name,
            "logical_tool_name": specification.logical_name,
            "parameters": dict(specification.parameter_schema),
        })
    return {
        "capability_advertisement": capability,
        "schema_source_path": verification.schema_source_path.as_posix(),
        "schema_source_sha256": verification.schema_source_sha256,
        "schema_variant_id": variant_id,
        "tools": tools,
    }

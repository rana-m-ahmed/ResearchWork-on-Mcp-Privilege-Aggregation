"""Loopback-only FastMCP launcher and discovery probes for Phase 5."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Callable, Sequence

from ..domain.errors import RuntimeMismatchError, SchemaInvariantError
from .workspace_isolation import AttemptWorkspaceIsolation

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
        return LaunchVerification(
            server=server,
            host=self.host,
            port=self.port,
            tool_names=tool_names,
            reset_hidden=True,
            reset_dispatch=reset_dispatch,
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

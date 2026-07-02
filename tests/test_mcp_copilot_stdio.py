from __future__ import annotations

import contextlib
import importlib
import io
import sys
import types
from pathlib import Path


class FakeCallToolResult:
    pass


class FakeContext:
    pass


class FakeRouter:
    _default_config_path = Path("fake_config.json")

    def __init__(self, *_args, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def route(self, _query):
        return {}

    async def call_tool(self, *_args, **_kwargs):
        return FakeCallToolResult()


class FakeFastMCP:
    def __init__(self, *_args, **_kwargs):
        self.tools = []

    def tool(self, **_kwargs):
        def decorator(func):
            self.tools.append(func)
            return func

        return decorator

    def run(self, *, transport: str) -> None:
        assert transport == "stdio"


async def noop_run_generation() -> None:
    return None


def install_fake_dependencies(monkeypatch):
    mcp_module = types.ModuleType("mcp")
    mcp_types_module = types.ModuleType("mcp.types")
    mcp_types_module.CallToolResult = FakeCallToolResult
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.Context = FakeContext
    fastmcp_module.FastMCP = FakeFastMCP

    mcp_server_module = types.ModuleType("mcp.server")
    mcp_server_module.fastmcp = fastmcp_module
    mcp_module.types = mcp_types_module
    mcp_module.server = mcp_server_module

    router_module = types.ModuleType("baseline.mcp_copilot.router")
    router_module.Router = FakeRouter
    router_module.dump_to_yaml = lambda result: str(result)

    arg_generation_module = types.ModuleType("baseline.mcp_copilot.arg_generation")
    arg_generation_module.run_generation = noop_run_generation

    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.types", mcp_types_module)
    monkeypatch.setitem(sys.modules, "mcp.server", mcp_server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)
    monkeypatch.setitem(sys.modules, "baseline.mcp_copilot.router", router_module)
    monkeypatch.setitem(sys.modules, "baseline.mcp_copilot.arg_generation", arg_generation_module)
    sys.modules.pop("baseline.mcp_copilot.server", None)

    return importlib.import_module("baseline.mcp_copilot.server")


def test_mcp_copilot_stdio_startup_logs_do_not_use_stdout(monkeypatch):
    server_module = install_fake_dependencies(monkeypatch)
    monkeypatch.setattr(server_module, "FastMCP", FakeFastMCP)
    monkeypatch.setattr(server_module, "run_generation", noop_run_generation)

    stdout = io.StringIO()
    stderr = io.StringIO()

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        server_module.serve({})

    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "Indexing MCP servers and tools...\n"
        "Starting MCP Copilot server...\n"
    )

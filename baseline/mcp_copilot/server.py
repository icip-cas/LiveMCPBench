from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import asyncio
import mcp.types as types
from mcp.server.fastmcp import Context, FastMCP
from baseline.mcp_copilot.router import Router, dump_to_yaml
from baseline.mcp_copilot.arg_generation import run_generation


def serve(config: dict[str, Any] | Path = Router._default_config_path) -> None:
    """Run the copilot MCP server.

    Args:
        config: MCP Server config for Router
    """
    print("Indexing MCP servers and tools...")
    asyncio.run(run_generation())

    @asynccontextmanager
    async def copilot_lifespan(server: FastMCP) -> AsyncIterator[dict]:
        """Lifespan context manager for the Copilot server."""
        async with Router(config) as router:
            yield {"router": router}

    print("Starting MCP Copilot server...")
    server = FastMCP("mcp-copilot", lifespan=copilot_lifespan)

    @server.tool(
        name="route",
        description=(
            """
    This is a tool used to find MCP servers and tools that can solve user needs    
    When to use this tool:
        -When faced with user needs, you (LLM) are unable to solve them on your own and do not have the tools to solve the problem.
        -When a user proposes a new task and you (LLM) are unsure which specific tool to use to complete it.
        -When the user's request is vague or complex, and feasible tool options need to be explored first.
        -This is the first step in executing unknown tasks, known as the "discovery" phase, aimed at finding the correct tool.
    **Parameter Description**
    Query (string, required): The input query must contain a <tool_assistant> tag with server and tool descriptions, for example: 
        <tool_assistant>
        server: ... # Platform/permission domain
        tool: ... # Operation type + target
        </tool_assistant>
    """
        ),
    )
    async def route(
        query: str,
        ctx: Context,
    ) -> types.CallToolResult:
        """Route user query to appropriate servers and tools."""
        router: Router = ctx.request_context.lifespan_context["router"]
        result = await router.route(query)
        return dump_to_yaml(result)

    @server.tool(
        name="execute-tool",
        description="""A tool for executing a specific tool on a specific server.Select tools only from the results obtained from the previous route each time.

When to use this tool:
    - When using the route tool to route to a specific MCP server and tool
    - When the 'execute-tool' fails to execute (up to 3 repetitions).
    - When the user's needs and previous needs require the same tool.

Parameters explained:
    -server_name: string, required. The name of the server where the target tool is located.

    -tool_name: string, required. The name of the target tool to be executed.

    -params: dictionary or None, optional. A dictionary containing all parameters that need to be passed to the target tool. This can be omitted if the target tool does not require parameters.
""",
    )
    async def execute_tool(
        server_name: str,
        tool_name: str,
        params: dict[str, Any] | None,
        ctx: Context,
    ) -> types.CallToolResult:
        """Execute the specific tool based on routed servers or tools."""
        router = ctx.request_context.lifespan_context["router"]
        result = await router.call_tool(server_name, tool_name, params)

        return result

    server.run(transport="stdio")

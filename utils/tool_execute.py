import asyncio
import json
import logging
import pathlib
import random

from utils.clogger import _set_logger
from utils.mcp_client import MCPClient

_set_logger(
    exp_dir=pathlib.Path("./logs"),
    logging_level_stdout=logging.INFO,
    logging_level=logging.DEBUG,
    file_name="tool_execute.log",
)
logger = logging.getLogger(__name__)


class ToolExecute:
    def __init__(self, config_file: str, timeout: int = 180, max_sessions: int = 10):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            self.name2idx = {}
            for idx, server in enumerate(self.config):
                self.name2idx[server["name"]] = idx
        self.client = MCPClient(timeout, max_sessions)

    async def tool_execute(self, name, server_name, tool_name, tool_params):
        server_id = f"{name}_{server_name}"
        if server_id not in self.client.sessions:
            if name not in self.name2idx:
                raise ValueError(f"Server {name} is not in config.")
            idx = self.name2idx[name]
            mcp_config = self.config[idx]["config"]
            if server_name not in mcp_config["mcpServers"]:
                raise ValueError(f"Server {server_name} is not in config for {name}.")
            await self.client.config_connect(mcp_config, prefix=f"{name}_")
            result = await self.client.tool_execute(server_id, tool_name, tool_params)
            return result

    async def warm_connect(self, num: int = 30):
        ranomd_idx = random.sample(range(len(self.config)), num)
        for idx in ranomd_idx:
            server = self.config[idx]
            mcp_config = server["config"]
            name = server["name"]
            await self.client.config_connect(mcp_config, prefix=f"{name}_")


async def test_lru():
    tool_execute = ToolExecute("./tools/LiveMCPTool/tools.json", max_sessions=10)
    await tool_execute.warm_connect(20)
    await tool_execute.client.cleanup()


async def test_tool_execute():
    tool_execute = ToolExecute("./tools/LiveMCPTool/tools.json")
    result = await tool_execute.tool_execute(
        name="Yahoo Finance MCP Server",
        server_name="yfmcp",
        tool_name="get_ticker_info",
        tool_params={"symbol": "APPL"},
    )
    print(result)
    await tool_execute.client.cleanup()


if __name__ == "__main__":
    asyncio.run(test_tool_execute())
    # asyncio.run(test_lru())

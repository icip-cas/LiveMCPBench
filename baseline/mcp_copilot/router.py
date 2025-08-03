import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import mcp.types as types
import yaml
from dotenv import load_dotenv

from baseline.mcp_copilot.matcher import ToolMatcher
from baseline.mcp_copilot.mcp_connection import MCPConnection
from baseline.mcp_copilot.schemas import Server, ServerConfig

load_dotenv()
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[0]


def dump_to_yaml(data: dict[str, Any]) -> str:
    """将字典转换为YAML格式的字符串以便更好地显示。"""
    return yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


class Router:
    _default_config_path = PROJECT_ROOT / "config" / "clean_config.json"

    def __init__(
        self,
        config: dict[str, Any] | Path = _default_config_path,
    ):
        self.servers = {}
        if isinstance(config, dict):
            self.config = config
        elif isinstance(config, Path):
            if config.exists():
                with config.open("r") as f:
                    self.config = json.load(f)
            else:
                logger.warning(
                    f"Config file not found at {config}. Starting with empty server list."
                )
                self.config = {"mcpServers": {}}
        else:
            raise ValueError("Config must be a dictionary or a Path to a JSON file.")

        for name, config_data in self.config.get("mcpServers", {}).items():
            self.servers[name] = Server(name=name, config=ServerConfig(**config_data))

        # 初始化 ToolMatcher
        self.matcher = ToolMatcher(
            embedding_model=os.getenv("EMBEDDING_MODEL"),
            dimensions=int(os.getenv("EMBEDDING_DIMENSIONS")),
            top_servers=int(os.getenv("TOP_SERVERS", 5)),
            top_tools=int(os.getenv("TOP_TOOLS", 3)),
        )

        # 从环境变量中获取API密钥和数据路径
        base_url = os.getenv("EMBEDDING_BASE_URL")
        api_key = os.getenv("EMBEDDING_API_KEY")
        default_data_path = (
            PROJECT_ROOT
            / "config"
            / f"mcp_arg_{os.getenv('EMBEDDING_MODEL')}_{os.getenv('ABSTRACT_MODEL')}.json"
        )
        data_path = os.getenv("MCP_DATA_PATH", default_data_path)

        if not api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable not set.")
        if not data_path or not os.path.exists(data_path):
            raise ValueError(f"MCP_DATA_PATH not set or file not found at: {data_path}")

        self.matcher.setup_openai_client(base_url=base_url, api_key=api_key)
        self.matcher.load_data(data_path)

        # 新增：初始化一个锁来同步连接过程
        self.connection_lock = asyncio.Lock()

    async def route(self, query: str) -> dict[str, Any]:
        """使用ToolMatcher进行路由，找到最匹配的工具。"""
        return self.matcher.match(query)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> types.CallToolResult:
        """在指定的服务器上执行工具，每次调用都建立新连接以确保上下文安全。"""
        async with self.connection_lock:
            server_config = self.servers.get(server_name)
            if not server_config:
                raise ValueError(
                    f"Server '{server_name}' is not defined in the configuration."
                )
            # 使用 async with 来管理连接的生命周期
            # 现在整个过程都在锁的保护下，是线程安全的
            async with MCPConnection(server_config) as connection:
                try:
                    result = await asyncio.wait_for(
                        connection.call_tool(tool_name, params or {}), timeout=timeout
                    )
                    return result
                except asyncio.TimeoutError:
                    return types.CallToolResult(
                        isError=True,
                        content=[
                            types.TextContent(
                                text=f"Tool {tool_name} in {server_name} call timed out."
                            )
                        ],
                    )

    async def aclose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

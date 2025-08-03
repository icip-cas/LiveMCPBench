import logging
import asyncio
import os
import re
from typing import Dict, Optional
from contextlib import AsyncExitStack
import copy
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from cachetools import LRUCache

logger = logging.getLogger(__name__)


class LRUCacheWithCallback(LRUCache):
    def __init__(self, maxsize, on_evict=None, *args, **kwargs):
        super().__init__(maxsize, *args, **kwargs)
        self.on_evict = on_evict

    def popitem(self):
        key, value = super().popitem()
        if self.on_evict:
            self.on_evict(key, value)
        return key, value


class MCPClient:
    def __init__(self, timeout: int = 30, max_sessions=30):
        # Initialize session and client objects
        self.timeout = timeout
        self.max_sessions = max_sessions

        def on_eviction(server_id, session):
            logger.info(f"[LRU] Evicting {server_id}")
            asyncio.create_task(self.cleanup_server(server_id))

        self.sessions: LRUCacheWithCallback[str, ClientSession] = LRUCacheWithCallback(
            max_sessions, on_evict=on_eviction
        )
        # for avoid error
        self.task: Dict[str, asyncio.Task] = {}
        self.stop_event: Dict[str, asyncio.Event] = {}

    async def tool_execute(self, server_id, tool_name, tool_params):
        if server_id not in self.sessions:
            raise ValueError(f"Server {server_id} is not connected.")
        session = self.sessions[server_id]
        try:
            result = await session.call_tool(tool_name, tool_params)
            return result
        except Exception as e:
            logger.error(
                f"Error executing tool {tool_name} with {tool_params} on server {server_id}: {e}"
            )
            raise ValueError(f"Error executing tool {tool_name}.")

    async def config_connect(self, config: dict, prefix: str = None):
        # Connect to an MCP server using a config file
        config = config["mcpServers"]
        for server in config:
            server_id = f"{prefix}{server}" if prefix else server
            if server_id in self.sessions:
                continue
            ready_event = asyncio.Event()

            # This is necessary to ensure in the same event loop
            async def mcp_session_runner() -> None:
                command = config[server].get("command")
                url = config[server].get("url")
                exit_stack = AsyncExitStack()
                if command:
                    args = config[server].get("args", [])
                    env = config[server].get("env", None)
                    if env:
                        env = self._process_env_vars(env)
                    PROXY_ENV_LIST = [
                        "HTTP_PROXY",
                        "HTTPS_PROXY",
                        "NO_PROXY",
                        "http_proxy",
                        "https_proxy",
                        "no_proxy",
                    ]
                    for proxy_env in PROXY_ENV_LIST:
                        if proxy_env in os.environ:
                            env = env or {}
                            env[proxy_env] = os.environ[proxy_env]
                    await self.connect_to_server(
                        server_id, command, args, env, exit_stack
                    )
                elif url:
                    header = config[server].get("header", None)
                    url = self._process_url_vars(url)
                    await self.connect_to_server_sse(server_id, url, header, exit_stack)
                else:
                    raise ValueError(
                        "Config file must contain either a command or a url for each server"
                    )
                ready_event.set()
                try:
                    stop_event = asyncio.Event()
                    current_task = asyncio.current_task()
                    self.stop_event[server_id] = stop_event
                    self.task[server_id] = current_task
                    assert current_task is not None, "Current task should not be None"
                    await stop_event.wait()
                finally:
                    try:
                        await exit_stack.aclose()
                    except Exception as e:
                        logger.exception("Error during exit stack close", exc_info=e)
                        pass
                    logger.info(f"MCP session {server} closed")

            asyncio.create_task(mcp_session_runner())
            await ready_event.wait()

    def _process_env_vars(self, env: dict) -> dict:
        """Process environment variables in config"""
        processed_env = {}
        for key in env:
            match = re.findall(r"\${(.*)}", env[key])
            processed_value = env[key]
            for m in match:
                if m in os.environ:
                    processed_value = processed_value.replace(
                        f"${{{m}}}", os.environ[m]
                    )
                else:
                    raise ValueError(
                        f"Environment variable {m} not found for env: {env}"
                    )
            processed_env[key] = processed_value
        return processed_env

    def _process_url_vars(self, url: str) -> str:
        """Process environment variables in URL"""
        match = re.findall(r"\${(.*)}", url)
        processed_url = url
        for m in match:
            if m in os.environ:
                processed_url = processed_url.replace(f"${{{m}}}", os.environ[m])
            else:
                raise ValueError(f"Environment variable {m} not found for URL: {url}")
        return processed_url

    async def connect_to_server_sse(
        self, server_id: str, url: str, header=None, exit_stack: AsyncExitStack = None
    ):
        # Connect to the server using SSE
        try:
            sse_transport = await exit_stack.enter_async_context(
                sse_client(url, header)
            )
            sse, write = sse_transport
            session = await exit_stack.enter_async_context(
                ClientSession(sse, write, self.timeout)
            )
            await asyncio.wait_for(session.initialize(), timeout=self.timeout)
            self.sessions[server_id] = session
            logger.info(f"Connected to server {server_id}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to SSE server {server_id}")
            self.cleanup_server(server_id)
            raise
        except Exception as e:
            logger.error(f"Error connecting to SSE server {server_id}: {e}")
            self.cleanup_server(server_id)
            raise

    async def connect_to_server(
        self,
        server_id: str,
        command: str,
        args: list,
        env: Optional[dict] = None,
        exit_stack: AsyncExitStack = None,
    ):
        # Connect to an MCP server
        try:
            server_params = StdioServerParameters(command=command, args=args, env=env)
            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport
            session = await exit_stack.enter_async_context(ClientSession(stdio, write))
            await asyncio.wait_for(session.initialize(), timeout=self.timeout)
            self.sessions[server_id] = session
            logger.info(f"Connected to server {server_id}.")
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to server {server_id}")
            await self.cleanup_server(server_id)
            raise
        except Exception as e:
            logger.error(f"Error connecting to server {server_id}: {e}")
            await self.cleanup_server(server_id)
            raise

    async def list_tools(self, server_id: str) -> Dict[str, Dict]:
        """Lists all available tools from a connected MCP server."""
        if server_id not in self.sessions:
            logger.warning(f"Server {server_id} not connected, cannot list tools.")
            return {}
        session = self.sessions[server_id]
        try:
            logger.info(f"Listing tools for server {server_id}")
            list_tools = await session.list_tools()
            list_tools = list_tools.tools
            logger.info(f"Tools for {server_id}: {list(list_tools)}")
            actual_tools_dict = {x.name: x for x in list_tools}
            return actual_tools_dict
        except Exception as e:
            logger.error(f"Error listing tools for {server_id}: {e}", exc_info=True)
            return {}

    async def cleanup_server(self, server_id: str):
        self.stop_event[server_id].set()
        await self.task[server_id]
        self.sessions.pop(server_id, None)
        self.stop_event.pop(server_id, None)
        self.task.pop(server_id, None)

    async def cleanup(self):
        """Clean up resources"""
        try:
            server_ids = copy.deepcopy(list(self.sessions.keys()))
            for server_id in server_ids:
                await self.cleanup_server(server_id)
        except asyncio.TimeoutError:
            logger.warning("Timeout during cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

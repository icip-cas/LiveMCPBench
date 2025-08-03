import argparse
import asyncio
import json
import logging
import os
import pathlib
import re
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from tqdm.asyncio import tqdm

from my_types import McpServerInfo
from clogger import _set_logger


class MCPClient:
    def __init__(self, timeout: int = 30):
        # Initialize session and client objects
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.timeout = timeout

    async def config_connect(self, config: dict):
        # Connect to an MCP server using a config file
        config = config["mcpServers"]
        for server in config:
            command = config[server].get("command")
            url = config[server].get("url")
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
                await self.connect_to_server(server, command, args, env)
            elif url:
                header = config[server].get("header", None)
                url = self._process_url_vars(url)
                await self.connect_to_server_sse(server, url, header)
            else:
                raise ValueError(
                    "Config file must contain either a command or a url for each server"
                )
        logger.info(f"Successfully connected to servers: {list(config.keys())}")

    def _process_env_vars(self, env: dict) -> dict:
        # Process environment variables in config
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
        # Process environment variables in URL
        match = re.findall(r"\${(.*)}", url)
        processed_url = url
        for m in match:
            if m in os.environ:
                processed_url = processed_url.replace(f"${{{m}}}", os.environ[m])
            else:
                raise ValueError(f"Environment variable {m} not found for URL: {url}")
        return processed_url

    async def connect_to_server_sse(self, server_id: str, url: str, header=None):
        # Connect to the server using SSE
        try:
            sse_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(sse_client(url, header)),
                timeout=self.timeout,
            )
            sse, write = sse_transport
            session = await asyncio.wait_for(
                self.exit_stack.enter_async_context(
                    ClientSession(sse, write, self.timeout)
                ),
                timeout=self.timeout,
            )
            await asyncio.wait_for(session.initialize(), timeout=self.timeout)
            self.sessions[server_id] = session
            logger.info(f"Connected to server {server_id}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to SSE server {server_id}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to SSE server {server_id}: {e}")
            raise

    async def connect_to_server(
        self, server_id: str, command: str, args: list, env: Optional[dict] = None
    ):
        # Connect to an MCP server
        try:
            server_params = StdioServerParameters(command=command, args=args, env=env)
            stdio_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=self.timeout,
            )
            stdio, write = stdio_transport
            session = await asyncio.wait_for(
                self.exit_stack.enter_async_context(ClientSession(stdio, write)),
                timeout=self.timeout,
            )
            await asyncio.wait_for(session.initialize(), timeout=self.timeout)
            self.sessions[server_id] = session
            logger.info(f"Connected to server {server_id}.")
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to server {server_id}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to server {server_id}: {e}")
            raise

    async def collect_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        # Collect information from a single server with error handling
        try:
            session = self.sessions.get(server_id)
            if not session:
                logger.error(f"No session found for server {server_id}")
                return None

            response = await asyncio.wait_for(
                session.list_tools(), timeout=self.timeout
            )
            mcp_version = session._client_info.version
            model_config = session._client_info.model_config
            info = McpServerInfo(
                server_name=server_id,
                version=mcp_version,
                model_config=model_config,
                tools=response.tools,
            )
            return info.model_dump()
        except asyncio.TimeoutError:
            logger.error(f"Timeout collecting info from server {server_id}")
            return None
        except Exception as e:
            logger.error(f"Error collecting info from server {server_id}: {e}")
            return None

    async def collect_all_info(self):
        # Collect all information from all servers
        all_info = {}
        tasks = []

        for server_id in self.sessions:
            tasks.append(self.collect_server_info(server_id))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, (server_id, result) in enumerate(zip(self.sessions.keys(), results)):
                if isinstance(result, Exception):
                    logger.error(f"Exception for server {server_id}: {result}")
                elif result is not None:
                    all_info[server_id] = result

        return all_info

    async def cleanup(self):
        # Clean up resources
        try:
            await asyncio.wait_for(self.exit_stack.aclose(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("Timeout during cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def process_single_server(
    server_config: dict, semaphore: asyncio.Semaphore, timeout: int = 30
) -> Optional[dict]:
    # Process a single server with concurrency control
    async with semaphore:
        client = MCPClient(timeout=timeout)
        server_name = server_config.get("name", "unknown")

        try:
            config = server_config["config"]
            await asyncio.wait_for(client.config_connect(config), timeout=timeout * 2)
            all_info = await client.collect_all_info()

            if all_info:
                server_config["tools"] = all_info
                return server_config
            else:
                logger.warning(f"No tools found for server {server_name}")
                return None

        except asyncio.TimeoutError:
            logger.error(f"Timeout processing server {server_name}")
            return None
        except Exception as e:
            logger.error(f"Error processing server {server_name}: {e}")
            return None
        finally:
            await client.cleanup()


async def main_parallel(
    servers_data: List[dict],
    visited_tools: List[str],
    max_concurrent: int = 5,
    timeout: int = 30,
    strict: bool = True,
) -> tuple:
    # Filter out already visited servers
    servers_to_process = [
        server for server in servers_data if server["name"] not in visited_tools
    ]

    if not servers_to_process:
        logger.info("No new servers to process")
        return [], []

    logger.info(
        f"Processing {len(servers_to_process)} servers with max {max_concurrent} concurrent connections"
    )

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []

    for server in servers_to_process:
        task = process_single_server(server, semaphore, timeout)
        tasks.append(task)

    # Process with progress bar
    new_data = []
    error_tools = []
    for i, coro in enumerate(tqdm.as_completed(tasks), 1):
        try:
            result = await coro
            server_name = servers_to_process[i - 1]["name"]

            if result is not None:
                new_data.append(result)
                logger.info(f"Successfully processed server: {server_name}")
            else:
                logger.warning(f"Failed to process server: {server_name}")
                error_tools.append(server_name)

        except Exception as e:
            server_name = (
                servers_to_process[i - 1]["name"]
                if i <= len(servers_to_process)
                else "unknown"
            )
            logger.error(f"Unexpected error processing server {server_name}: {e}")
            error_tools.append(server_name)

    return new_data, error_tools


def args_parser():
    parser = argparse.ArgumentParser(description="MCP Client")
    parser.add_argument(
        "--metadata_path",
        default="./tools/LiveMCPTool/all_config.json",
        type=str,
        help="Path to the metadata",
    )
    parser.add_argument(
        "--max_concurrent",
        default=5,
        type=int,
        help="Maximum number of concurrent connections",
    )
    parser.add_argument(
        "--timeout",
        default=180,
        type=int,
        help="Timeout for each server connection in seconds",
    )
    parser.add_argument(
        "--output_path", type=str, default=None, help="Output path for results"
    )
    return parser.parse_args()


async def main():
    args = args_parser()

    # Setup logging
    _set_logger(
        exp_dir=pathlib.Path(args.metadata_path).parent / "logs",
        logging_level_stdout=logging.INFO,
        logging_level=logging.DEBUG,
        # Filter=Filter,
        file_name="crawl_tool.log",
    )

    global logger
    logger = logging.getLogger(__name__)

    # Load data
    root_path = Path(args.metadata_path)

    try:
        with open(root_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Metadata file not found: {root_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata file: {e}")
        return

    # Load existing results
    new_data = []
    if args.output_path:
        tools_path = Path(args.output_path)
    else:
        tools_path = root_path.parent / "tools.json"
    if tools_path.exists():
        try:
            with open(tools_path, "r", encoding="utf-8") as f:
                new_data = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {tools_path}, starting fresh")
            new_data = []
    # Load visited tools
    visited_tool = []
    for entry in new_data:
        if "name" in entry:
            visited_tool.append(entry["name"])
    try:
        # Process servers in parallel
        processed_data, error_tools = await main_parallel(
            data, visited_tool, args.max_concurrent, args.timeout
        )

        # Update results
        new_data.extend(processed_data)

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main processing: {e}")
    finally:
        # Save results
        try:
            os.makedirs(tools_path.parent, exist_ok=True)
            with open(tools_path, "w+", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            if args.output_path:
                error_tools_path = Path(args.output_path).parent / "error_tools.json"
            else:
                error_tools_path = root_path.parent / "error_tools.json"
            with open(error_tools_path, "w+", encoding="utf-8") as f:
                json.dump(error_tools, f, ensure_ascii=False, indent=4)
            logger.info(
                f"Successfully processed servers: {len(new_data)}\n"
                f"Total visited tools: {len(visited_tool)}\n"
            )
        except Exception as e:
            logger.error(f"Error saving results: {e}")


if __name__ == "__main__":
    asyncio.run(main())

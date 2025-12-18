import argparse
import asyncio
import json
import logging
import os
import pathlib
from pathlib import Path

from tqdm.asyncio import tqdm

from utils.clogger import _set_logger
from utils.mcp_client import MCPClient


async def process_single_server(
    idx: int, server_config: dict, semaphore: asyncio.Semaphore, timeout: int = 30
) -> dict | None:
    # Process a single server with concurrency control
    async with semaphore:
        client = MCPClient(timeout=timeout)
        server_name = server_config.get("name", "unknown")
        try:
            async with asyncio.timeout(timeout):
                config = server_config["config"]
                await client.config_connect(config)
                all_info = await client.collect_all_info()

            if all_info:
                server_config["tools"] = all_info
                return idx, server_config
            else:
                logger.warning(f"No tools found for server {server_name}")
                return idx, None

        except asyncio.TimeoutError:
            logger.error(f"Timeout processing server {server_name}")
            return idx, None
        except Exception as e:
            logger.error(f"Error processing server {server_name}: {e}")
            return idx, None
        finally:
            await asyncio.shield(client.cleanup())


async def main_parallel(
    servers_data: list[dict],
    visited_tools: list[str],
    max_concurrent: int = 5,
    timeout: int = 30,
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

    for idx, server in enumerate(servers_to_process):
        task = process_single_server(idx, server, semaphore, timeout)
        tasks.append(task)

    # Process with progress bar
    new_data = []
    error_tools = []
    for coro in tqdm.as_completed(tasks):
        try:
            idx, result = await coro
            server_name = servers_to_process[idx]["name"]
            if result is not None:
                new_data.append(result)
                logger.info(f"Successfully processed server: {server_name}")
            else:
                logger.warning(f"Failed to process server: {server_name}")
                error_tools.append(server_name)

        except Exception as e:
            server_name = (
                servers_to_process[idx]["name"]
                if idx <= len(servers_to_process)
                else "unknown"
            )
            import traceback

            logger.error(traceback.print_exc())
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

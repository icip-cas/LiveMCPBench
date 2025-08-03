from collections.abc import Callable
from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
)

from pydantic import BaseModel, ConfigDict, Field, FileUrl, RootModel
from pydantic.networks import AnyUrl, UrlConstraints
from mcp.types import Tool


class McpServerInfo(BaseModel):
    """
    Model to represent the information of an MCP server.
    """

    server_name: str
    version: str
    model_config = ConfigDict(extra="allow")
    tools: list[Tool]

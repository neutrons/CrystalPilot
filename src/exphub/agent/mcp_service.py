"""MCP (Model Context Protocol) service for CrystalPilot.

Connects to external MCP servers and provides their tools to the LangGraph
agent.  This enables CrystalPilot to integrate with external tools like VESTA,
Platon, custom instrument controllers, etc.

Adapted from NeuDiff-Agent's mcp_service.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    name: str = Field(description="Human-readable name for this MCP server")
    command: str = Field(description="Command to start the MCP server")
    args: List[str] = Field(default_factory=list, description="Arguments for the server command")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    enabled: bool = Field(default=True, description="Whether this server is enabled")


class MCPService:
    """Manages MCP server connections and converts their tools for LangChain."""

    def __init__(self) -> None:
        self.servers: Dict[str, Any] = {}
        self.tools: Dict[str, BaseTool] = {}
        self.configs: Dict[str, MCPServerConfig] = {}
        self._enabled = MCP_AVAILABLE

    def is_available(self) -> bool:
        return self._enabled

    def add_server_config(self, config: MCPServerConfig) -> None:
        self.configs[config.name] = config
        logger.info("Added MCP server config: %s", config.name)

    async def connect_server(self, config: MCPServerConfig) -> bool:
        """Connect to an MCP server. Returns True on success."""
        if not self._enabled:
            logger.error("MCP SDK not available — install with: pip install mcp")
            return False
        if config.name in self.servers:
            return True

        try:
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env if config.env else None,
            )

            # Setup stdio connection
            try:
                stdio_ctx = stdio_client(server_params)
                read, write = await asyncio.wait_for(stdio_ctx.__aenter__(), timeout=5.0)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.error("Stdio setup failed for %s: %s", config.name, exc)
                return False

            # Create session
            try:
                session_ctx = ClientSession(read, write)
                session = await asyncio.wait_for(session_ctx.__aenter__(), timeout=5.0)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.error("Session creation failed for %s: %s", config.name, exc)
                return False

            # Initialise
            try:
                await asyncio.wait_for(session.initialize(), timeout=5.0)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.error("Session init failed for %s: %s", config.name, exc)
                return False

            self.servers[config.name] = {
                "session": session,
                "stdio_context": stdio_ctx,
                "session_context": session_ctx,
            }

            # Load tools
            try:
                await asyncio.wait_for(
                    self._load_tools_from_server(config.name, session), timeout=10.0
                )
            except Exception as exc:
                logger.warning("Tool loading failed for %s: %s", config.name, exc)

            logger.info("Connected to MCP server: %s", config.name)
            return True

        except Exception as exc:
            logger.error("Failed to connect to MCP server %s: %s", config.name, exc)
            return False

    async def _load_tools_from_server(self, server_name: str, session: ClientSession) -> None:
        tools_response = await session.list_tools()
        for mcp_tool in tools_response.tools:
            lc_tool = self._mcp_tool_to_langchain(server_name, mcp_tool)
            if lc_tool:
                tool_name = f"mcp_{server_name}_{mcp_tool.name}"
                self.tools[tool_name] = lc_tool
                logger.info("Loaded MCP tool: %s", tool_name)

    def _mcp_tool_to_langchain(self, server_name: str, mcp_tool: Tool) -> Optional[BaseTool]:
        try:
            async def mcp_tool_wrapper(**kwargs: Any) -> str:
                server_info = self.servers.get(server_name)
                if not server_info:
                    return json.dumps({"error": f"Server {server_name} not connected"})
                try:
                    result = await server_info["session"].call_tool(
                        mcp_tool.name, arguments=kwargs
                    )
                    if result.content:
                        parts = []
                        for content in result.content:
                            if isinstance(content, TextContent):
                                parts.append(content.text)
                            else:
                                parts.append(str(content))
                        return "\n".join(parts)
                    return json.dumps({"result": "Tool executed successfully"})
                except Exception as exc:
                    return json.dumps({"error": str(exc)})

            def sync_wrapper(**kwargs: Any) -> str:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                return loop.run_until_complete(mcp_tool_wrapper(**kwargs))

            return StructuredTool.from_function(
                func=sync_wrapper,
                name=f"mcp_{server_name}_{mcp_tool.name}",
                description=mcp_tool.description or f"MCP tool from {server_name}",
            )
        except Exception as exc:
            logger.error("Failed to convert MCP tool %s: %s", mcp_tool.name, exc)
            return None

    async def disconnect_server(self, name: str) -> None:
        if name not in self.servers:
            return
        # Remove tools
        for key in [k for k in self.tools if k.startswith(f"mcp_{name}_")]:
            del self.tools[key]
        # Close connections
        info = self.servers.pop(name)
        try:
            if info.get("session_context"):
                await info["session_context"].__aexit__(None, None, None)
            if info.get("stdio_context"):
                await info["stdio_context"].__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("Error closing %s: %s", name, exc)
        logger.info("Disconnected from MCP server: %s", name)

    def get_all_tools(self) -> List[BaseTool]:
        return list(self.tools.values())

    async def connect_all_servers(self) -> None:
        for config in self.configs.values():
            if config.enabled:
                try:
                    await asyncio.wait_for(self.connect_server(config), timeout=10.0)
                except (asyncio.TimeoutError, Exception) as exc:
                    logger.error("Connection to %s failed: %s", config.name, exc)

    def load_configs_from_file(self, config_path: Path) -> None:
        """Load MCP server configs from a JSON file."""
        if not config_path.exists():
            logger.info("No MCP config at %s", config_path)
            return
        try:
            data = json.loads(config_path.read_text())
            if not isinstance(data, list):
                logger.warning("MCP config should be a list, got %s", type(data))
                return
            for entry in data:
                try:
                    self.add_server_config(MCPServerConfig(**entry))
                except Exception as exc:
                    logger.warning("Bad MCP config entry: %s", exc)
        except Exception as exc:
            logger.error("Failed to load MCP configs: %s", exc)

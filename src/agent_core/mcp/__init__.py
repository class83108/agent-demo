"""MCP Server 整合模組。

提供 MCP Client 與 Tool Adapter，將 MCP Server 的工具整合到 ToolRegistry。
"""

from agent_core.mcp.adapter import MCPToolAdapter
from agent_core.mcp.client import MCPServerConfig, MCPToolDefinition

__all__ = ['MCPServerConfig', 'MCPToolAdapter', 'MCPToolDefinition']

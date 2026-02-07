"""MCP Tool Adapter。

將 MCP Server 的工具註冊到 ToolRegistry，處理前綴與呼叫轉發。
"""

from __future__ import annotations

import logging
from typing import Any

from agent_core.mcp.client import MCPClient
from agent_core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """MCP 工具轉接器。

    負責將 MCPClient 提供的工具註冊到 ToolRegistry，
    並在執行時將呼叫轉發給 MCPClient。
    """

    def __init__(self, client: MCPClient) -> None:
        """初始化 Adapter。

        Args:
            client: MCP Client 實例
        """
        self._client = client

    async def register_tools(self, registry: ToolRegistry) -> None:
        """將 MCP Server 的工具註冊到 ToolRegistry。

        工具名稱會加上 server 名稱前綴：{server_name}__{tool_name}

        Args:
            registry: 要註冊工具的 ToolRegistry
        """
        tools = await self._client.list_tools()

        for tool_def in tools:
            prefixed_name = f'{self._client.server_name}__{tool_def.name}'
            # 透過閉包捕獲原始工具名稱
            original_name = tool_def.name

            async def handler(_original_name: str = original_name, **kwargs: Any) -> Any:
                return await self._client.call_tool(_original_name, kwargs)

            registry.register(
                name=prefixed_name,
                description=tool_def.description,
                parameters=tool_def.input_schema,
                handler=handler,
            )
            # 設定 source 為 mcp
            registry.set_tool_source(prefixed_name, 'mcp')

            logger.info(
                'MCP 工具已註冊',
                extra={
                    'server': self._client.server_name,
                    'tool': tool_def.name,
                    'registered_as': prefixed_name,
                },
            )

    async def close(self) -> None:
        """關閉 MCP 連線。"""
        await self._client.close()

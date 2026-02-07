"""MCP Client 與相關資料結構。

定義 MCPServerConfig、MCPToolDefinition 以及 MCPClient Protocol。
實際的 MCP Client 實作依賴 mcp SDK（optional dependency）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP Server 配置。

    Attributes:
        name: Server 名稱（用於工具前綴）
        command: 啟動 Server 的指令
        env: 傳遞給 Server 的環境變數
    """

    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=lambda: {})


@dataclass(frozen=True)
class MCPToolDefinition:
    """MCP Server 提供的工具定義。

    Attributes:
        name: 工具名稱（Server 端原始名稱，不含前綴）
        description: 工具描述
        input_schema: JSON Schema 格式的參數定義
    """

    name: str
    description: str
    input_schema: dict[str, Any]


class MCPClient(Protocol):
    """MCP Client Protocol。

    定義與 MCP Server 互動的介面。
    實際實作可使用 mcp SDK 或自行實作 stdio 通訊。
    """

    server_name: str

    async def list_tools(self) -> list[MCPToolDefinition]:
        """列出 Server 提供的工具。"""
        ...

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """呼叫 Server 的工具。

        Args:
            tool_name: 工具名稱（不含前綴）
            arguments: 工具參數
        """
        ...

    async def close(self) -> None:
        """關閉連線並清理資源。"""
        ...

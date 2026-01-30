"""型別定義模組。

定義專案中使用的自定義型別與資料結構。
"""

from __future__ import annotations

from typing import TypedDict


class ContentBlock(TypedDict, total=False):
    """訊息內容區塊型別定義。

    用於表示 Anthropic API 回應中的 content blocks。
    支援多種類型的區塊（text, tool_use, tool_result 等）。

    Attributes:
        type: 區塊類型（text, tool_use, tool_result 等）
        text: 文字內容（僅 text 類型）
        id: 工具調用 ID（僅 tool_use 類型）
        name: 工具名稱（僅 tool_use 類型）
        input: 工具輸入參數（僅 tool_use 類型）
        tool_use_id: 工具調用 ID（僅 tool_result 類型）
        content: 工具結果內容（僅 tool_result 類型）
        is_error: 是否為錯誤結果（僅 tool_result 類型）
    """

    type: str
    text: str
    id: str
    name: str
    input: dict[str, object]
    tool_use_id: str
    content: str
    is_error: bool

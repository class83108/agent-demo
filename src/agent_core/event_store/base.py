"""EventStore 介面定義與串流事件型別。

提供可恢復串流所需的抽象層，讓 Agent 在串流回應時將事件寫入持久化儲存，
客戶端斷線後可從指定 offset 恢復。
"""

from __future__ import annotations

from typing import Literal, Protocol, TypedDict, runtime_checkable


class StreamEvent(TypedDict):
    """串流事件。

    Attributes:
        id: 事件唯一識別符（由 EventStore 指派，呼叫端傳空字串）
        type: 事件類型（token、tool_call、compact、done 等）
        data: 事件資料（token 文字、JSON 字串等）
        timestamp: 事件產生時間戳
    """

    id: str
    type: str
    data: str
    timestamp: float


class StreamStatus(TypedDict):
    """串流狀態。

    Attributes:
        stream_id: 串流識別符（通常為 session_id）
        status: 串流狀態
        event_count: 已記錄的事件數量
    """

    stream_id: str
    status: Literal['generating', 'completed', 'failed']
    event_count: int


@runtime_checkable
class EventStore(Protocol):
    """串流事件儲存 Protocol。

    定義可恢復串流所需的事件持久化介面。
    實作者負責事件儲存、offset 讀取與生命週期管理。
    """

    async def append(self, stream_id: str, event: StreamEvent) -> None:
        """追加事件到串流。

        EventStore 應忽略 event['id'] 的傳入值，自行指派唯一遞增 id。

        Args:
            stream_id: 串流識別符（通常為 session_id）
            event: 串流事件
        """
        ...

    async def read(
        self,
        stream_id: str,
        after: str | None = None,
        count: int = 100,
    ) -> list[StreamEvent]:
        """讀取串流事件。

        Args:
            stream_id: 串流識別符
            after: 從此 event id 之後開始讀取（不含）。None 表示從頭讀取。
            count: 最多回傳幾筆事件

        Returns:
            事件列表，按寫入順序排列。若串流不存在回傳空列表。
        """
        ...

    async def get_status(self, stream_id: str) -> StreamStatus | None:
        """查詢串流狀態。

        Args:
            stream_id: 串流識別符

        Returns:
            串流狀態，若串流不存在回傳 None
        """
        ...

    async def mark_complete(self, stream_id: str) -> None:
        """標記串流為已完成。

        Args:
            stream_id: 串流識別符
        """
        ...

    async def mark_failed(self, stream_id: str) -> None:
        """標記串流為失敗。

        Args:
            stream_id: 串流識別符
        """
        ...

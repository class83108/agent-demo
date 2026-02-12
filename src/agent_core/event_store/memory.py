"""記憶體 EventStore 實作。

適用於單一 server、開發與測試場景。支援 TTL 自動過期。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from agent_core.event_store.base import StreamEvent, StreamStatus


@dataclass
class _StreamData:
    """單一串流的內部資料。"""

    events: list[StreamEvent] = field(default_factory=lambda: [])
    status: Literal['generating', 'completed', 'failed'] = 'generating'
    created_at: float = field(default_factory=time.time)
    counter: int = 0


class MemoryEventStore:
    """記憶體 EventStore。

    所有事件儲存於 dict 中，支援 TTL 過期自動清除。
    適用於單一 server 場景，進程重啟後資料會遺失。

    Args:
        ttl_seconds: 串流過期時間（秒）。預設 300 秒（5 分鐘）。
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._streams: dict[str, _StreamData] = {}

    def _get_stream(self, stream_id: str) -> _StreamData | None:
        """取得串流資料，若已過期則清除並回傳 None。"""
        data = self._streams.get(stream_id)
        if data is None:
            return None

        if time.time() - data.created_at > self._ttl_seconds:
            del self._streams[stream_id]
            return None

        return data

    async def append(self, stream_id: str, event: StreamEvent) -> None:
        """追加事件到串流。自動指派遞增 id。"""
        data = self._streams.get(stream_id)
        if data is None:
            data = _StreamData()
            self._streams[stream_id] = data

        # 指派遞增 id
        data.counter += 1
        assigned_event = StreamEvent(
            id=str(data.counter),
            type=event['type'],
            data=event['data'],
            timestamp=event['timestamp'],
        )
        data.events.append(assigned_event)

    async def read(
        self,
        stream_id: str,
        after: str | None = None,
        count: int = 100,
    ) -> list[StreamEvent]:
        """讀取串流事件，支援 offset。"""
        data = self._get_stream(stream_id)
        if data is None:
            return []

        events = data.events

        if after is not None:
            # 找到 after id 的位置，回傳之後的事件
            start_idx = None
            for i, e in enumerate(events):
                if e['id'] == after:
                    start_idx = i + 1
                    break

            if start_idx is None:
                return []

            events = events[start_idx:]

        return events[:count]

    async def get_status(self, stream_id: str) -> StreamStatus | None:
        """查詢串流狀態。"""
        data = self._get_stream(stream_id)
        if data is None:
            return None

        return StreamStatus(
            stream_id=stream_id,
            status=data.status,
            event_count=len(data.events),
        )

    async def mark_complete(self, stream_id: str) -> None:
        """標記串流為已完成。"""
        data = self._streams.get(stream_id)
        if data is not None:
            data.status = 'completed'

    async def mark_failed(self, stream_id: str) -> None:
        """標記串流為失敗。"""
        data = self._streams.get(stream_id)
        if data is not None:
            data.status = 'failed'

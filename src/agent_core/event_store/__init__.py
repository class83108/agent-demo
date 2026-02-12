"""EventStore 抽象層。

提供可恢復串流的事件持久化介面與預設記憶體實作。
"""

from agent_core.event_store.base import EventStore, StreamEvent, StreamStatus
from agent_core.event_store.memory import MemoryEventStore

__all__ = ['EventStore', 'MemoryEventStore', 'StreamEvent', 'StreamStatus']

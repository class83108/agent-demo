"""Session 後端介面定義。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agent_core.types import MessageParam


@runtime_checkable
class SessionBackend(Protocol):
    """Session 後端 Protocol。

    定義對話歷史的儲存介面，實作者負責持久化邏輯。
    """

    async def load(self, session_id: str) -> list[MessageParam]:
        """讀取對話歷史。

        Args:
            session_id: 會話識別符

        Returns:
            對話歷史列表，若無記錄則回傳空列表
        """
        ...

    async def save(self, session_id: str, conversation: list[MessageParam]) -> None:
        """儲存對話歷史。

        Args:
            session_id: 會話識別符
            conversation: 對話歷史列表
        """
        ...

    async def reset(self, session_id: str) -> None:
        """清除對話歷史。

        Args:
            session_id: 會話識別符
        """
        ...

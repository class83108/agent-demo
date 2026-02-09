"""記憶體 Session 後端。

用於開發與測試環境，對話歷史存在記憶體中，程序結束即消失。
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field

from agent_core.types import MessageParam

logger = logging.getLogger(__name__)


@dataclass
class MemorySessionBackend:
    """記憶體 Session 後端。

    將對話歷史儲存在 dict 中，適合開發、測試使用。
    """

    _store: dict[str, list[MessageParam]] = field(default_factory=lambda: {})

    async def load(self, session_id: str) -> list[MessageParam]:
        """讀取對話歷史。

        Args:
            session_id: 會話識別符

        Returns:
            對話歷史列表的深複製，若無記錄則回傳空列表
        """
        data = self._store.get(session_id)
        if data is None:
            return []
        return copy.deepcopy(data)

    async def save(self, session_id: str, conversation: list[MessageParam]) -> None:
        """儲存對話歷史。

        Args:
            session_id: 會話識別符
            conversation: 對話歷史列表
        """
        self._store[session_id] = copy.deepcopy(conversation)
        logger.debug(
            '儲存會話歷史（記憶體）',
            extra={'session_id': session_id, 'messages': len(conversation)},
        )

    async def reset(self, session_id: str) -> None:
        """清除對話歷史。

        Args:
            session_id: 會話識別符
        """
        self._store.pop(session_id, None)
        logger.debug('會話歷史已清除（記憶體）', extra={'session_id': session_id})

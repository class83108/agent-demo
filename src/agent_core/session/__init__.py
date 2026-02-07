"""Session 後端抽象層。

提供可抽換的 Session 後端，支援記憶體與 Redis 兩種實作。
"""

from agent_core.session.base import SessionBackend
from agent_core.session.memory_backend import MemorySessionBackend
from agent_core.session.redis_backend import SessionManager

__all__ = ['MemorySessionBackend', 'SessionBackend', 'SessionManager']

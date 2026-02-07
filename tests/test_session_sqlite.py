"""SQLite Session Backend 測試模組。

根據 docs/features/session.feature 規格撰寫測試案例。
涵蓋：
- Rule: SQLite 後端應支援基本 CRUD 操作
- Rule: SQLite 後端應跨程序存活
- Rule: SQLite 後端應支援多 session 隔離
- Rule: SQLite 後端應正確序列化複雜訊息結構
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agent_core.session.sqlite_backend import SQLiteSessionBackend

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """回傳暫存目錄中的資料庫檔案路徑。"""
    return tmp_path / 'test_session.db'


@pytest.fixture
async def backend(db_path: Path) -> SQLiteSessionBackend:
    """建立 SQLiteSessionBackend 實例。"""
    return SQLiteSessionBackend(db_path=str(db_path))


def _sample_conversation() -> list[dict[str, Any]]:
    """建立範例對話歷史。"""
    return [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Hi there'},
    ]


# =============================================================================
# Rule: SQLite 後端應支援基本 CRUD 操作
# =============================================================================


class TestSQLiteBasicCRUD:
    """測試 SQLite 後端基本 CRUD 操作。"""

    async def test_save_and_load(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 儲存並讀取對話歷史。"""
        conversation = _sample_conversation()

        await backend.save('abc', conversation)
        result = await backend.load('abc')

        assert result == conversation

    async def test_load_nonexistent_session(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 讀取不存在的 session。"""
        result = await backend.load('not-exist')

        assert result == []

    async def test_reset_session(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 重設 session。"""
        await backend.save('abc', _sample_conversation())

        await backend.reset('abc')

        result = await backend.load('abc')
        assert result == []

    async def test_save_overwrites_existing(self, backend: SQLiteSessionBackend) -> None:
        """覆寫已存在的 session 資料。"""
        await backend.save('abc', [{'role': 'user', 'content': 'first'}])
        await backend.save('abc', [{'role': 'user', 'content': 'second'}])

        result = await backend.load('abc')

        assert len(result) == 1
        assert result[0]['content'] == 'second'


# =============================================================================
# Rule: SQLite 後端應跨程序存活
# =============================================================================


class TestSQLitePersistence:
    """測試 SQLite 後端跨程序持久化。"""

    async def test_data_survives_reopen(self, db_path: Path) -> None:
        """Scenario: 關閉後重新開啟仍保留資料。"""
        conversation = _sample_conversation()

        # 第一次：寫入
        backend1 = SQLiteSessionBackend(db_path=str(db_path))
        await backend1.save('abc', conversation)

        # 第二次：用同一路徑建立新實例，模擬重啟
        backend2 = SQLiteSessionBackend(db_path=str(db_path))
        result = await backend2.load('abc')

        assert result == conversation


# =============================================================================
# Rule: SQLite 後端應支援多 session 隔離
# =============================================================================


class TestSQLiteSessionIsolation:
    """測試多 session 隔離。"""

    async def test_different_sessions_isolated(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 不同 session 的資料互不影響。"""
        await backend.save('s1', [{'role': 'user', 'content': 'A'}])
        await backend.save('s2', [{'role': 'user', 'content': 'B'}])

        result_1 = await backend.load('s1')
        result_2 = await backend.load('s2')

        assert result_1[0]['content'] == 'A'
        assert result_2[0]['content'] == 'B'

    async def test_reset_one_session_preserves_others(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 重設單一 session 不影響其他。"""
        await backend.save('s1', [{'role': 'user', 'content': 'A'}])
        await backend.save('s2', [{'role': 'user', 'content': 'B'}])

        await backend.reset('s1')

        assert await backend.load('s1') == []
        assert len(await backend.load('s2')) == 1


# =============================================================================
# Rule: SQLite 後端應正確序列化複雜訊息結構
# =============================================================================


class TestSQLiteComplexMessages:
    """測試複雜訊息結構的序列化。"""

    async def test_tool_use_and_tool_result_preserved(self, backend: SQLiteSessionBackend) -> None:
        """Scenario: 儲存包含 tool_use 與 tool_result 的對話。"""
        conversation: list[dict[str, Any]] = [
            {'role': 'user', 'content': '請讀取 main.py'},
            {
                'role': 'assistant',
                'content': [
                    {'type': 'text', 'text': '讓我讀取檔案'},
                    {
                        'type': 'tool_use',
                        'id': 'tool_1',
                        'name': 'read_file',
                        'input': {'path': 'main.py'},
                    },
                ],
            },
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'tool_result',
                        'tool_use_id': 'tool_1',
                        'content': 'print("hello")',
                        'is_error': False,
                    },
                ],
            },
            {'role': 'assistant', 'content': '檔案內容如上。'},
        ]

        await backend.save('abc', conversation)
        result = await backend.load('abc')

        assert result == conversation

        # 驗證 tool_use 區塊完整
        tool_use_block = result[1]['content'][1]
        assert tool_use_block['type'] == 'tool_use'
        assert tool_use_block['id'] == 'tool_1'
        assert tool_use_block['name'] == 'read_file'
        assert tool_use_block['input'] == {'path': 'main.py'}

        # 驗證 tool_result 區塊完整
        tool_result_block = result[2]['content'][0]
        assert tool_result_block['type'] == 'tool_result'
        assert tool_result_block['tool_use_id'] == 'tool_1'
        assert tool_result_block['is_error'] is False


class TestSQLiteProtocolCompliance:
    """測試 SQLiteSessionBackend 符合 SessionBackend Protocol。"""

    async def test_implements_session_backend_protocol(self, backend: SQLiteSessionBackend) -> None:
        """SQLiteSessionBackend 應符合 SessionBackend Protocol。"""
        from agent_core.session.base import SessionBackend

        assert isinstance(backend, SessionBackend)

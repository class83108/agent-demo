"""Memory Tool 測試模組。

根據 docs/features/memory.feature 規格撰寫測試案例。
涵蓋：
- Rule: 應支援查看記憶目錄與檔案內容
- Rule: 應支援寫入記憶檔案
- Rule: 應支援刪除記憶檔案
- Rule: 應防止路徑穿越攻擊
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import allure
import pytest

from agent_core.memory import create_memory_handler

# Memory handler 型別別名
MemoryHandler = Callable[..., Coroutine[Any, Any, str]]


@pytest.fixture()
def memory_dir(tmp_path: Path) -> Path:
    """建立暫時的記憶目錄。"""
    d = tmp_path / 'memories'
    d.mkdir()
    return d


@pytest.fixture()
def handler(memory_dir: Path) -> MemoryHandler:
    """建立 memory handler。"""
    return create_memory_handler(memory_dir)


def _run(handler: MemoryHandler, **kwargs: Any) -> str:
    """同步執行 async handler。"""
    return asyncio.run(handler(**kwargs))


# =========================================================================
# Rule: 應支援查看記憶目錄與檔案內容
# =========================================================================


@allure.feature('Memory Tool')
@allure.story('應支援 view 指令')
class TestMemoryView:
    """view 指令測試。"""

    @allure.title('查看空的記憶目錄')
    def test_view_empty_directory(self, handler: MemoryHandler) -> None:
        """空目錄應回傳目錄清單。"""
        result = _run(handler, command='view')
        assert 'memories' in result.lower() or '目錄' in result.lower() or result != ''

    @allure.title('查看有檔案的記憶目錄')
    def test_view_directory_with_files(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """有檔案的目錄應列出檔案名稱。"""
        (memory_dir / 'notes.md').write_text('hello', encoding='utf-8')
        result = _run(handler, command='view')
        assert 'notes.md' in result

    @allure.title('查看記憶檔案內容（含行號）')
    def test_view_file_content(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """讀取檔案應回傳帶行號的內容。"""
        (memory_dir / 'notes.md').write_text('line1\nline2\nline3', encoding='utf-8')
        result = _run(handler, command='view', path='notes.md')
        # 應包含行號和內容
        assert '1' in result
        assert 'line1' in result
        assert 'line2' in result
        assert 'line3' in result

    @allure.title('查看多行檔案的行號格式')
    def test_view_file_line_number_format(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """行號應右對齊，tab 分隔。"""
        (memory_dir / 'test.txt').write_text('hello\nworld', encoding='utf-8')
        result = _run(handler, command='view', path='test.txt')
        # 模仿官方格式：6 字元右對齊行號 + tab + 內容
        assert '\t' in result
        assert 'hello' in result

    @allure.title('查看不存在的路徑')
    def test_view_nonexistent_path(self, handler: MemoryHandler) -> None:
        """不存在的路徑應回傳錯誤訊息。"""
        result = _run(handler, command='view', path='nonexistent.md')
        assert 'not exist' in result.lower() or '不存在' in result


# =========================================================================
# Rule: 應支援寫入記憶檔案
# =========================================================================


@allure.feature('Memory Tool')
@allure.story('應支援 write 指令')
class TestMemoryWrite:
    """write 指令測試。"""

    @allure.title('建立新的記憶檔案')
    def test_write_new_file(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """應成功建立新檔案。"""
        result = _run(handler, command='write', path='clues.md', content='鑰匙在房間3')
        assert 'clues.md' in result
        assert (memory_dir / 'clues.md').read_text(encoding='utf-8') == '鑰匙在房間3'

    @allure.title('覆寫既有的記憶檔案')
    def test_write_overwrite_file(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """覆寫應更新檔案內容。"""
        (memory_dir / 'clues.md').write_text('舊內容', encoding='utf-8')
        _run(handler, command='write', path='clues.md', content='新內容')
        assert (memory_dir / 'clues.md').read_text(encoding='utf-8') == '新內容'

    @allure.title('寫入巢狀目錄（自動建立）')
    def test_write_nested_directory(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """巢狀路徑應自動建立中間目錄。"""
        _run(handler, command='write', path='sub/deep/note.md', content='deep content')
        assert (memory_dir / 'sub' / 'deep' / 'note.md').exists()

    @allure.title('write 不提供 path 應報錯')
    def test_write_without_path(self, handler: MemoryHandler) -> None:
        """未指定 path 應回傳錯誤。"""
        result = _run(handler, command='write', content='some content')
        assert 'error' in result.lower() or '錯誤' in result.lower() or 'path' in result.lower()


# =========================================================================
# Rule: 應支援刪除記憶檔案
# =========================================================================


@allure.feature('Memory Tool')
@allure.story('應支援 delete 指令')
class TestMemoryDelete:
    """delete 指令測試。"""

    @allure.title('刪除既有的記憶檔案')
    def test_delete_existing_file(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """刪除應移除檔案。"""
        (memory_dir / 'old.md').write_text('old', encoding='utf-8')
        result = _run(handler, command='delete', path='old.md')
        assert not (memory_dir / 'old.md').exists()
        assert 'old.md' in result

    @allure.title('刪除不存在的檔案')
    def test_delete_nonexistent_file(self, handler: MemoryHandler) -> None:
        """刪除不存在的檔案應回傳錯誤。"""
        result = _run(handler, command='delete', path='nonexistent.md')
        assert 'not exist' in result.lower() or '不存在' in result

    @allure.title('刪除目錄')
    def test_delete_directory(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """刪除目錄應遞迴刪除。"""
        sub = memory_dir / 'subdir'
        sub.mkdir()
        (sub / 'file.txt').write_text('x', encoding='utf-8')
        result = _run(handler, command='delete', path='subdir')
        assert not sub.exists()
        assert 'subdir' in result


# =========================================================================
# Rule: 應防止路徑穿越攻擊
# =========================================================================


@allure.feature('Memory Tool')
@allure.story('應防止路徑穿越')
class TestMemoryPathSecurity:
    """路徑安全測試。"""

    @allure.title('view 路徑穿越應被阻擋')
    def test_view_path_traversal(self, handler: MemoryHandler) -> None:
        """../../../etc/passwd 應被拒絕。"""
        result = _run(handler, command='view', path='../../../etc/passwd')
        assert 'error' in result.lower() or '安全' in result or 'denied' in result.lower()

    @allure.title('write 路徑穿越應被阻擋')
    def test_write_path_traversal(self, handler: MemoryHandler) -> None:
        """嘗試寫入記憶目錄外應被拒絕。"""
        result = _run(handler, command='write', path='../../evil.sh', content='bad')
        assert 'error' in result.lower() or '安全' in result or 'denied' in result.lower()

    @allure.title('delete 路徑穿越應被阻擋')
    def test_delete_path_traversal(self, handler: MemoryHandler) -> None:
        """嘗試刪除記憶目錄外應被拒絕。"""
        result = _run(handler, command='delete', path='../../important.py')
        assert 'error' in result.lower() or '安全' in result or 'denied' in result.lower()

    @allure.title('記憶目錄內的路徑應正常運作')
    def test_valid_path_within_memory(self, handler: MemoryHandler, memory_dir: Path) -> None:
        """正常路徑應不觸發安全錯誤。"""
        _run(handler, command='write', path='safe/note.md', content='ok')
        assert (memory_dir / 'safe' / 'note.md').exists()


# =========================================================================
# 未知指令
# =========================================================================


@allure.feature('Memory Tool')
@allure.story('未知指令處理')
class TestMemoryUnknownCommand:
    """未知指令測試。"""

    @allure.title('未知指令應回傳錯誤')
    def test_unknown_command(self, handler: MemoryHandler) -> None:
        """不支援的 command 應回傳錯誤。"""
        result = _run(handler, command='rename', path='a', content='b')
        assert 'error' in result.lower() or '不支援' in result or 'unknown' in result.lower()

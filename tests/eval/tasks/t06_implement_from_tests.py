"""T6 — Implement from Tests / TDD (Hard)。

todo 模組已有 add/remove/list 功能。
測試檔中有 test_filter_by_status() 系列測試（紅燈），
需要在 todo.py 中新增 filter_by_status() 方法讓測試通過。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T6 - Implement from Tests'
TASK_LEVEL: str = 'hard'
TASK_PROMPT: str = (
    '這個 todo 模組有些新功能的測試已經寫好但還沒實作。\n'
    '請閱讀測試了解需求，然後實作對應的功能讓所有測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立 todo 專案。"""
    # todo.py — 已有基本 CRUD，缺 filter_by_status
    (sandbox / 'todo.py').write_text(
        '"""Todo 管理模組。"""\n'
        '\n'
        'from __future__ import annotations\n'
        '\n'
        'from dataclasses import dataclass, field\n'
        '\n'
        '\n'
        '@dataclass\n'
        'class TodoItem:\n'
        '    """待辦事項。"""\n'
        '\n'
        '    title: str\n'
        '    status: str = "pending"  # pending, in_progress, done\n'
        '\n'
        '\n'
        'class TodoList:\n'
        '    """待辦事項清單。"""\n'
        '\n'
        '    def __init__(self) -> None:\n'
        '        self._items: list[TodoItem] = []\n'
        '\n'
        '    def add(self, title: str) -> TodoItem:\n'
        '        """新增待辦事項。"""\n'
        '        item = TodoItem(title=title)\n'
        '        self._items.append(item)\n'
        '        return item\n'
        '\n'
        '    def remove(self, title: str) -> bool:\n'
        '        """移除指定標題的待辦事項。"""\n'
        '        for i, item in enumerate(self._items):\n'
        '            if item.title == title:\n'
        '                self._items.pop(i)\n'
        '                return True\n'
        '        return False\n'
        '\n'
        '    def list_all(self) -> list[TodoItem]:\n'
        '        """列出所有待辦事項。"""\n'
        '        return list(self._items)\n',
        encoding='utf-8',
    )

    # test_todo.py — 包含既有 + 新功能測試
    (sandbox / 'test_todo.py').write_text(
        'import pytest\n'
        '\n'
        'from todo import TodoItem, TodoList\n'
        '\n'
        '\n'
        '# --- 既有功能測試（應該已通過）---\n'
        '\n'
        '\n'
        'def test_add_item() -> None:\n'
        '    todos = TodoList()\n'
        '    item = todos.add("買牛奶")\n'
        '    assert item.title == "買牛奶"\n'
        '    assert item.status == "pending"\n'
        '    assert len(todos.list_all()) == 1\n'
        '\n'
        '\n'
        'def test_remove_item() -> None:\n'
        '    todos = TodoList()\n'
        '    todos.add("買牛奶")\n'
        '    assert todos.remove("買牛奶") is True\n'
        '    assert len(todos.list_all()) == 0\n'
        '\n'
        '\n'
        'def test_remove_nonexistent() -> None:\n'
        '    todos = TodoList()\n'
        '    assert todos.remove("不存在") is False\n'
        '\n'
        '\n'
        '# --- 新功能測試（需要實作 filter_by_status）---\n'
        '\n'
        '\n'
        'def test_filter_by_status_pending() -> None:\n'
        '    """篩選 pending 狀態的項目。"""\n'
        '    todos = TodoList()\n'
        '    todos.add("任務A")\n'
        '    item_b = todos.add("任務B")\n'
        '    item_b.status = "done"\n'
        '    todos.add("任務C")\n'
        '\n'
        '    result = todos.filter_by_status("pending")\n'
        '    assert len(result) == 2\n'
        '    assert all(item.status == "pending" for item in result)\n'
        '\n'
        '\n'
        'def test_filter_by_status_done() -> None:\n'
        '    """篩選 done 狀態的項目。"""\n'
        '    todos = TodoList()\n'
        '    item_a = todos.add("任務A")\n'
        '    item_a.status = "done"\n'
        '    todos.add("任務B")\n'
        '\n'
        '    result = todos.filter_by_status("done")\n'
        '    assert len(result) == 1\n'
        '    assert result[0].title == "任務A"\n'
        '\n'
        '\n'
        'def test_filter_by_status_empty_result() -> None:\n'
        '    """篩選不存在的狀態應回傳空列表。"""\n'
        '    todos = TodoList()\n'
        '    todos.add("任務A")\n'
        '    result = todos.filter_by_status("in_progress")\n'
        '    assert result == []\n'
        '\n'
        '\n'
        'def test_filter_by_status_invalid() -> None:\n'
        '    """無效狀態應拋出 ValueError。"""\n'
        '    todos = TodoList()\n'
        '    with pytest.raises(ValueError, match="無效的狀態"):\n'
        '        todos.filter_by_status("invalid_status")\n',
        encoding='utf-8',
    )


def evaluate(sandbox: Path, events: list[AgentEvent]) -> EvalResult:
    """評估 filter_by_status 實作結果。"""
    details: dict[str, Any] = {}

    source = sandbox / 'todo.py'
    if not source.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'todo.py 不存在'},
        )

    content = source.read_text(encoding='utf-8')
    details['has_filter_method'] = 'def filter_by_status' in content
    details['has_validation'] = 'ValueError' in content

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    score = 0.0
    if details['has_filter_method']:
        score += 0.2
    if details['has_validation']:
        score += 0.1
    if passed:
        score += 0.7

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )

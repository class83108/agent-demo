"""Memory Tool 處理器模組。

提供檔案式工作記憶，讓 Agent 在工作過程中記錄和查閱重要發現。
模仿 Anthropic 官方 Memory Tool 的策略，但以普通 ToolRegistry 工具實作，
保留 A/B 測試和策略調整的彈性。

支援指令：view（查看）、write（寫入）、delete（刪除）。
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Memory 工具描述（可透過 A/B 測試調整）
MEMORY_TOOL_DESCRIPTION = """記錄和查閱你的工作記憶。

- view：查看記憶目錄或讀取特定檔案
- write：將重要發現寫入記憶（專案結構、已找到的線索、計畫）
- delete：刪除過時的記憶

你的 context 隨時可能被壓縮，未記錄在記憶中的資訊可能丟失。"""

# Memory 工具的 JSON Schema 參數定義
MEMORY_TOOL_PARAMETERS: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'command': {
            'type': 'string',
            'enum': ['view', 'write', 'delete'],
            'description': '操作類型：view 查看、write 寫入、delete 刪除',
        },
        'path': {
            'type': 'string',
            'description': '檔案路徑（相對於記憶目錄，view 時可省略以列出目錄）',
        },
        'content': {
            'type': 'string',
            'description': 'write 指令時要寫入的內容',
        },
    },
    'required': ['command'],
}


def _validate_memory_path(path: str, memory_root: Path) -> Path:
    """驗證記憶路徑安全性，防止路徑穿越。

    Args:
        path: 使用者提供的相對路徑
        memory_root: 記憶目錄根路徑

    Returns:
        解析後的絕對路徑

    Raises:
        PermissionError: 路徑穿越至記憶目錄外
    """
    resolved = (memory_root / path).resolve()
    if not resolved.is_relative_to(memory_root.resolve()):
        logger.warning('Memory 路徑穿越攻擊', extra={'path': path})
        raise PermissionError(f'路徑安全錯誤：無法存取記憶目錄外的路徑: {path}')
    return resolved


def _view_directory(memory_root: Path) -> str:
    """列出記憶目錄內容（最多 2 層深度）。"""
    lines: list[str] = []
    for item in sorted(memory_root.rglob('*')):
        # 限制 2 層深度
        relative = item.relative_to(memory_root)
        if len(relative.parts) > 2:
            continue
        size = item.stat().st_size if item.is_file() else 0
        # 人類可讀的大小
        if size < 1024:
            size_str = f'{size}B'
        elif size < 1024 * 1024:
            size_str = f'{size / 1024:.1f}K'
        else:
            size_str = f'{size / (1024 * 1024):.1f}M'
        lines.append(f'{size_str}\t/memories/{relative}')

    if not lines:
        return '/memories/ （空目錄）'
    return '/memories/ 目錄內容：\n' + '\n'.join(lines)


def _view_file(file_path: Path, path: str) -> str:
    """讀取檔案內容，含行號（6 字元右對齊 + tab 分隔）。"""
    content = file_path.read_text(encoding='utf-8')
    numbered_lines: list[str] = []
    for i, line in enumerate(content.splitlines(), start=1):
        numbered_lines.append(f'{i:>6}\t{line}')
    return f"Here's the content of /memories/{path} with line numbers:\n" + '\n'.join(
        numbered_lines
    )


def create_memory_handler(
    memory_dir: Path,
) -> Callable[..., Coroutine[Any, Any, str]]:
    """建立 memory 工具的 handler 函數。

    以 closure 方式綁定 memory_dir，回傳可註冊到 ToolRegistry 的 async handler。

    Args:
        memory_dir: 記憶檔案的根目錄

    Returns:
        async handler 函數
    """
    memory_dir.mkdir(parents=True, exist_ok=True)
    logger.info('Memory Tool handler 已建立', extra={'memory_dir': str(memory_dir)})

    async def handle_memory(
        command: str,
        path: str = '',
        content: str = '',
    ) -> str:
        """處理 memory 工具呼叫。

        Args:
            command: 操作類型（view / write / delete）
            path: 檔案路徑（相對於記憶目錄）
            content: write 指令的檔案內容

        Returns:
            操作結果字串
        """
        if command == 'view':
            return _handle_view(memory_dir, path)
        elif command == 'write':
            return _handle_write(memory_dir, path, content)
        elif command == 'delete':
            return _handle_delete(memory_dir, path)
        else:
            return f'Error: 不支援的指令 "{command}"。支援的指令：view, write, delete'

    return handle_memory


def _handle_view(memory_dir: Path, path: str) -> str:
    """處理 view 指令。"""
    # 未指定 path → 列出目錄
    if not path:
        return _view_directory(memory_dir)

    try:
        resolved = _validate_memory_path(path, memory_dir)
    except PermissionError as e:
        return str(e)

    if not resolved.exists():
        return f'The path /memories/{path} does not exist.'

    if resolved.is_dir():
        return _view_directory(resolved)

    return _view_file(resolved, path)


def _handle_write(memory_dir: Path, path: str, content: str) -> str:
    """處理 write 指令。"""
    if not path:
        return 'Error: write 指令需要指定 path 參數。'

    try:
        resolved = _validate_memory_path(path, memory_dir)
    except PermissionError as e:
        return str(e)

    # 自動建立中間目錄
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding='utf-8')
    logger.debug('Memory 檔案已寫入', extra={'path': path})
    return f'File written successfully: /memories/{path}'


def _handle_delete(memory_dir: Path, path: str) -> str:
    """處理 delete 指令。"""
    if not path:
        return 'Error: delete 指令需要指定 path 參數。'

    try:
        resolved = _validate_memory_path(path, memory_dir)
    except PermissionError as e:
        return str(e)

    if not resolved.exists():
        return f'The path /memories/{path} does not exist.'

    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()

    logger.debug('Memory 檔案已刪除', extra={'path': path})
    return f'Successfully deleted /memories/{path}'

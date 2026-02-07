"""Grep Search 工具模組。

提供程式碼搜尋功能，支援正則表達式、範圍限制、上下文顯示等。
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_core.tools.path_utils import (
    matches_pattern,
    should_skip_dir,
    should_skip_file,
    validate_path,
)

logger = logging.getLogger(__name__)


def _build_regex(
    pattern: str,
    case_sensitive: bool,
    whole_word: bool,
) -> re.Pattern[str]:
    """建立搜尋用的正則表達式。

    Args:
        pattern: 搜尋模式
        case_sensitive: 是否區分大小寫
        whole_word: 是否全詞匹配

    Returns:
        編譯後的正則表達式
    """
    if whole_word:
        pattern = rf'\b{pattern}\b'

    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


def _search_file(
    file_path: Path,
    regex: re.Pattern[str],
    context_lines: int,
) -> list[dict[str, Any]]:
    """在單一檔案中搜尋。

    Args:
        file_path: 檔案路徑
        regex: 編譯後的正則表達式
        context_lines: 上下文行數

    Returns:
        匹配結果清單
    """
    matches: list[dict[str, Any]] = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, PermissionError):
        # 跳過無法讀取的檔案
        return matches

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        if regex.search(line):
            match_data: dict[str, Any] = {
                'line_number': line_num,
                'line_content': line,
            }

            # 加入上下文
            if context_lines > 0:
                start_idx = max(0, line_num - 1 - context_lines)
                end_idx = min(len(lines), line_num + context_lines)

                match_data['context_before'] = lines[start_idx : line_num - 1]
                match_data['context_after'] = lines[line_num:end_idx]

            matches.append(match_data)

    return matches


def _collect_files(
    search_path: Path,
    include: list[str] | None,
    exclude_dirs: list[str] | None,
) -> list[Path]:
    """收集要搜尋的檔案清單。

    Args:
        search_path: 搜尋起始路徑
        include: 包含的檔案模式
        exclude_dirs: 額外排除的目錄

    Returns:
        檔案路徑清單
    """
    files: list[Path] = []

    if search_path.is_file():
        if matches_pattern(search_path, include):
            files.append(search_path)
        return files

    for item in search_path.rglob('*'):
        if item.is_dir():
            continue

        # 檢查是否在排除目錄中（使用共用函數）
        relative_parts = item.relative_to(search_path).parts
        if any(should_skip_dir(part, exclude_dirs) for part in relative_parts):
            continue

        # 跳過排除的檔案類型（使用共用函數）
        if should_skip_file(item):
            continue

        # 檢查是否符合包含模式（使用共用函數）
        if not matches_pattern(item, include):
            continue

        files.append(item)

    return files


def grep_search_handler(
    pattern: str,
    sandbox_root: Path,
    path: str = '.',
    include: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    case_sensitive: bool = True,
    whole_word: bool = False,
    context_lines: int = 0,
    max_results: int = 100,
) -> dict[str, Any]:
    """搜尋程式碼並回傳結構化結果。

    Args:
        pattern: 搜尋模式（支援正則表達式）
        sandbox_root: sandbox 根目錄
        path: 搜尋路徑（相對於 sandbox 根目錄）
        include: 包含的檔案模式清單（如 ["*.py", "*.js"]）
        exclude_dirs: 額外要排除的目錄
        case_sensitive: 是否區分大小寫
        whole_word: 是否全詞匹配
        context_lines: 顯示前後幾行上下文
        max_results: 最大結果數量

    Returns:
        包含 matches、total_matches、files_summary 的字典

    Raises:
        PermissionError: 搜尋路徑在 sandbox 外
        ValueError: 無效的正則表達式
    """
    # 驗證路徑安全性（直接使用共用函數）
    search_path = validate_path(path, sandbox_root)

    # 編譯正則表達式
    try:
        regex = _build_regex(pattern, case_sensitive, whole_word)
    except re.error as e:
        raise ValueError(f'無效的正則表達式: {e}')

    # 收集要搜尋的檔案
    files = _collect_files(search_path, include, exclude_dirs)

    # 執行搜尋
    all_matches: list[dict[str, Any]] = []
    files_with_matches: dict[str, int] = defaultdict(int)

    for file_path in files:
        # 計算相對路徑
        try:
            relative_path = str(file_path.relative_to(sandbox_root))
        except ValueError:
            relative_path = str(file_path)

        file_matches = _search_file(file_path, regex, context_lines)

        for match in file_matches:
            match['file'] = relative_path
            all_matches.append(match)
            files_with_matches[relative_path] += 1

    total_matches = len(all_matches)
    limited_matches = all_matches[:max_results]

    # 建立檔案摘要
    files_summary = [
        {'file': file, 'count': count} for file, count in sorted(files_with_matches.items())
    ]

    logger.info(
        '搜尋完成',
        extra={
            'pattern': pattern,
            'total_matches': total_matches,
            'files_count': len(files_summary),
        },
    )

    return {
        'pattern': pattern,
        'matches': limited_matches,
        'total_matches': total_matches,
        'files_summary': files_summary,
        'truncated': total_matches > max_results,
    }

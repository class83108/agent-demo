"""路徑工具模組。

提供路徑驗證與安全檢查的共用函數與常數。
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# 共用常數
# =============================================================================

# 預設排除的目錄（搜尋、列出等操作時應跳過）
DEFAULT_EXCLUDE_DIRS: list[str] = [
    'node_modules',
    '.git',
    '__pycache__',
    '.venv',
    'venv',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    'dist',
    'build',
    '.idea',
    '.vscode',
    '.tox',
    '.nox',
    '.eggs',
    '*.egg-info',
]

# 預設排除的檔案模式（二進位、編譯產物等）
DEFAULT_EXCLUDE_FILE_PATTERNS: list[str] = [
    '*.pyc',
    '*.pyo',
    '*.so',
    '*.dylib',
    '*.dll',
    '*.exe',
    '*.bin',
    '*.png',
    '*.jpg',
    '*.jpeg',
    '*.gif',
    '*.ico',
    '*.pdf',
    '*.zip',
    '*.tar',
    '*.gz',
    '*.whl',
    '*.lock',
]


# =============================================================================
# 共用函數
# =============================================================================


def should_skip_dir(dir_name: str, exclude_dirs: list[str] | None = None) -> bool:
    """檢查是否應跳過該目錄。

    Args:
        dir_name: 目錄名稱
        exclude_dirs: 額外要排除的目錄清單（會與預設清單合併）

    Returns:
        是否應跳過
    """
    all_excludes = DEFAULT_EXCLUDE_DIRS.copy()
    if exclude_dirs:
        all_excludes.extend(exclude_dirs)
    return dir_name in all_excludes


def should_skip_file(file_path: Path) -> bool:
    """檢查是否應跳過該檔案（根據預設排除模式）。

    Args:
        file_path: 檔案路徑

    Returns:
        是否應跳過
    """
    file_name = file_path.name
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in DEFAULT_EXCLUDE_FILE_PATTERNS)


def matches_pattern(file_path: Path, patterns: list[str] | None) -> bool:
    """檢查檔案是否符合任一模式。

    Args:
        file_path: 檔案路徑
        patterns: 檔案模式清單（如 ["*.py", "*.js"]），None 表示全部符合

    Returns:
        是否符合
    """
    if patterns is None:
        return True
    file_name = file_path.name
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in patterns)


def validate_path(path: str, sandbox_root: Path) -> Path:
    """驗證路徑是否在 sandbox 內。

    Args:
        path: 使用者提供的路徑
        sandbox_root: sandbox 根目錄

    Returns:
        解析後的絕對路徑

    Raises:
        PermissionError: 路徑在 sandbox 外
    """
    resolved = (sandbox_root / path).resolve()

    # 檢查路徑穿越
    if not resolved.is_relative_to(sandbox_root.resolve()):
        logger.warning('路徑穿越攻擊', extra={'path': path})
        raise PermissionError(f'無法存取 sandbox 外的路徑: {path}')

    return resolved

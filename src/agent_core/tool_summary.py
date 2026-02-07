"""工具摘要模組。

提供工具調用的人類可讀摘要，用於前端顯示。
"""

from __future__ import annotations

from typing import Any

# 工具摘要的最大長度
_SUMMARY_MAX_LEN: int = 120

# 工具名稱與摘要格式對應
_TOOL_SUMMARY_MAP: dict[str, tuple[str, str]] = {
    'read_file': ('讀取檔案', 'path'),
    'edit_file': ('編輯檔案', 'path'),
    'list_files': ('列出檔案', 'path'),
    'bash': ('執行命令', 'command'),
    'grep_search': ('搜尋程式碼', 'pattern'),
}


def get_tool_summary(tool_name: str, tool_input: dict[str, Any]) -> str:
    """根據工具名稱與參數產生人類可讀的摘要。

    Args:
        tool_name: 工具名稱
        tool_input: 工具參數

    Returns:
        人類可讀的摘要字串
    """
    if tool_name in _TOOL_SUMMARY_MAP:
        label, param_key = _TOOL_SUMMARY_MAP[tool_name]
        value = str(tool_input.get(param_key, ''))
        if len(value) > _SUMMARY_MAX_LEN:
            value = value[:_SUMMARY_MAX_LEN] + '...'
        return f'{label} {value}'

    # 未知工具：顯示工具名稱
    return f'使用工具 {tool_name}'

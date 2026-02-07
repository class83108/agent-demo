"""上下文壓縮（Compact）模組。

當對話接近 context window 上限時，自動壓縮以釋放空間：
- Phase 1: 截斷舊的 tool_result 內容（無 API 呼叫）
- Phase 2: 用 LLM 摘要早期對話（需 API 呼叫）
"""

from __future__ import annotations

import logging
from typing import Any, cast

from agent_core.providers.base import LLMProvider
from agent_core.token_counter import TokenCounter

logger = logging.getLogger(__name__)

# 觸發 compact 的 context window 使用率閾值（百分比）
COMPACT_THRESHOLD: float = 80.0

# 截斷後的替代標記
TRUNCATED_MARKER: str = '[已壓縮的工具結果]'

# 摘要用的 system prompt
_SUMMARIZE_SYSTEM_PROMPT: str = (
    '你是一個對話摘要助手。請將以下對話內容濃縮為簡潔的摘要，'
    '保留所有重要的上下文資訊、決策和結論。使用繁體中文。'
)


def _has_block_type(content: list[dict[str, Any]], block_type: str) -> bool:
    """檢查 content list 中是否包含指定 type 的 block。"""
    for block in content:
        if block.get('type') == block_type:
            return True
    return False


def _find_tool_result_rounds(
    conversation: list[dict[str, Any]],
) -> list[int]:
    """找出所有含 tool_result 的 user 訊息索引。

    Returns:
        含 tool_result 的訊息在 conversation 中的索引列表
    """
    indices: list[int] = []
    for i, msg in enumerate(conversation):
        if msg.get('role') != 'user':
            continue
        content = msg.get('content')
        if not isinstance(content, list):
            continue
        if _has_block_type(cast(list[dict[str, Any]], content), 'tool_result'):
            indices.append(i)
    return indices


def truncate_tool_results(
    conversation: list[dict[str, Any]],
    preserve_last_n_rounds: int = 1,
) -> int:
    """Phase 1: 截斷舊的 tool_result 內容。

    遍歷 conversation，將舊的 tool_result 內容替換為壓縮標記。
    保留最近 N 輪的 tool_result 不被截斷。

    Args:
        conversation: 對話歷史（會被原地修改）
        preserve_last_n_rounds: 保留最近幾輪 tool_result 不截斷

    Returns:
        實際截斷的 tool_result 數量
    """
    tool_result_indices = _find_tool_result_rounds(conversation)

    if not tool_result_indices:
        return 0

    # 保留最後 N 輪
    if preserve_last_n_rounds > 0:
        indices_to_truncate = tool_result_indices[:-preserve_last_n_rounds]
    else:
        indices_to_truncate = tool_result_indices

    truncated_count = 0
    for idx in indices_to_truncate:
        raw_content = conversation[idx]['content']
        if not isinstance(raw_content, list):
            continue
        for block in cast(list[dict[str, Any]], raw_content):
            if block.get('type') != 'tool_result':
                continue
            # 跳過已截斷的
            if block.get('content') == TRUNCATED_MARKER:
                continue
            block['content'] = TRUNCATED_MARKER
            truncated_count += 1

    if truncated_count > 0:
        logger.info(
            'Phase 1: 已截斷舊 tool_result',
            extra={'truncated_count': truncated_count},
        )

    return truncated_count


def _find_safe_split_point(
    conversation: list[dict[str, Any]],
    keep_last_n: int,
) -> int:
    """找到安全的摘要切割點。

    確保不會拆散 tool_use/tool_result 配對。
    從 conversation 末尾往前數 keep_last_n 則訊息，
    然後確保切割點在完整的 conversation round 邊界。

    Args:
        conversation: 對話歷史
        keep_last_n: 保留最後幾則訊息

    Returns:
        切割點索引（此索引之前的訊息將被摘要）
    """
    if len(conversation) <= keep_last_n:
        return 0

    split = len(conversation) - keep_last_n

    # 確保切割點不在 tool_use/tool_result 配對中間
    # 向前調整直到找到安全的邊界
    while split > 0:
        msg = conversation[split]
        raw_content = msg.get('content')

        # 如果是 user 訊息且含 tool_result，往前移
        if msg.get('role') == 'user' and isinstance(raw_content, list):
            if _has_block_type(cast(list[dict[str, Any]], raw_content), 'tool_result'):
                split -= 1
                continue

        # 如果是 assistant 訊息且含 tool_use，要連帶下一則 tool_result
        if msg.get('role') == 'assistant' and isinstance(raw_content, list):
            if _has_block_type(cast(list[dict[str, Any]], raw_content), 'tool_use'):
                split -= 1
                continue

        break

    return split


def _format_block(block: dict[str, Any], text_parts: list[str]) -> None:
    """格式化單一 content block 為摘要用文字。"""
    block_type = block.get('type', '')
    if block_type == 'text':
        text_parts.append(str(block.get('text', '')))
    elif block_type == 'tool_use':
        text_parts.append(f'[呼叫工具: {block.get("name", "")}]')
    elif block_type == 'tool_result':
        tool_content = str(block.get('content', ''))
        if tool_content == TRUNCATED_MARKER:
            text_parts.append(TRUNCATED_MARKER)
        else:
            preview = tool_content[:200]
            text_parts.append(f'[工具結果: {preview}...]')


def _format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """將訊息列表格式化為摘要用的文字。"""
    parts: list[str] = []
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')

        if isinstance(content, str):
            parts.append(f'{role}: {content}')
        elif isinstance(content, list):
            text_parts: list[str] = []
            for block in cast(list[dict[str, Any]], content):
                _format_block(block, text_parts)
            parts.append(f'{role}: {" ".join(text_parts)}')

    return '\n'.join(parts)


async def summarize_conversation(
    conversation: list[dict[str, Any]],
    provider: LLMProvider,
    system_prompt: str,
    keep_last_n: int = 4,
) -> str | None:
    """Phase 2: 用 LLM 摘要早期對話。

    將早期的對話輪次送給 LLM 摘要，然後替換為摘要訊息。
    保留最後 keep_last_n 則訊息不被摘要。

    Args:
        conversation: 對話歷史（會被原地修改）
        provider: LLM Provider（需支援 create 方法）
        system_prompt: 原始 system prompt（供摘要 context 參考）
        keep_last_n: 保留最後幾則訊息

    Returns:
        摘要文字，若訊息不足則回傳 None
    """
    split_point = _find_safe_split_point(conversation, keep_last_n)

    # 訊息不足以摘要
    if split_point < 2:
        return None

    # 準備要摘要的早期對話
    early_messages = conversation[:split_point]

    # 建立摘要請求
    summary_request: list[dict[str, Any]] = [
        {
            'role': 'user',
            'content': (
                '請摘要以下對話內容，保留重要的上下文資訊：\n\n'
                + _format_messages_for_summary(early_messages)
            ),
        }
    ]

    result = await provider.create(
        messages=summary_request,
        system=_SUMMARIZE_SYSTEM_PROMPT,
        max_tokens=2048,
    )

    # 提取摘要文字
    summary_text = ''
    for block in result.content:
        if block.get('type') == 'text':
            summary_text += str(block.get('text', ''))

    # 替換早期對話為摘要
    summary_messages: list[dict[str, Any]] = [
        {'role': 'user', 'content': f'以下是先前對話的摘要：\n{summary_text}'},
        {
            'role': 'assistant',
            'content': [{'type': 'text', 'text': '好的，我了解先前的對話內容。'}],
        },
    ]

    kept_messages = conversation[split_point:]
    conversation.clear()
    conversation.extend(summary_messages + kept_messages)

    logger.info(
        'Phase 2: 已摘要早期對話',
        extra={
            'summarized_messages': split_point,
            'kept_messages': len(kept_messages),
        },
    )

    return summary_text


async def compact_conversation(
    conversation: list[dict[str, Any]],
    provider: LLMProvider,
    system_prompt: str,
    token_counter: TokenCounter,
) -> dict[str, Any]:
    """完整 compact 流程。

    依序執行 Phase 1（截斷 tool_result）和 Phase 2（LLM 摘要），
    根據 token_counter 的使用率決定是否需要進一步壓縮。

    Args:
        conversation: 對話歷史（會被原地修改）
        provider: LLM Provider
        system_prompt: 系統提示詞
        token_counter: Token 計數器

    Returns:
        壓縮結果字典 {truncated: int, summarized: bool, summary: str | None}
    """
    result: dict[str, Any] = {
        'truncated': 0,
        'summarized': False,
        'summary': None,
    }

    # 檢查是否超過閾值
    if token_counter.usage_percent < COMPACT_THRESHOLD:
        return result

    logger.info(
        '開始 compact 流程',
        extra={'usage_percent': round(token_counter.usage_percent, 2)},
    )

    # Phase 1: 截斷舊 tool_result
    truncated = truncate_tool_results(conversation)
    result['truncated'] = truncated

    # Phase 1 後重新估算（簡易判斷：如果截斷了內容，可能已足夠）
    # 注意：精確判斷需要重新 count_tokens，但這裡用啟發式方法
    if truncated > 0:
        # 假設截斷有效，先回傳結果
        # 如果下一次 API 呼叫仍超過閾值，會再次觸發 compact
        return result

    # Phase 2: LLM 摘要
    summary = await summarize_conversation(
        conversation=conversation,
        provider=provider,
        system_prompt=system_prompt,
    )

    if summary is not None:
        result['summarized'] = True
        result['summary'] = summary

    return result

"""Agent 核心模組。

實作與 LLM Provider 互動的對話代理，支援工具調用迴圈。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from agent_core.config import AgentCoreConfig
from agent_core.providers.base import LLMProvider
from agent_core.providers.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from agent_core.skills.registry import SkillRegistry
from agent_core.tools.registry import ToolRegistry
from agent_core.usage_monitor import UsageMonitor

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """對話代理。

    負責管理與 LLM Provider 的對話互動，維護對話歷史，
    並支援串流回應與工具調用迴圈。

    Attributes:
        config: Agent 配置
        provider: LLM Provider 實例
        conversation: 對話歷史紀錄
        tool_registry: 工具註冊表（可選）
        usage_monitor: 使用量監控器（可選）
    """

    config: AgentCoreConfig
    provider: LLMProvider
    conversation: list[dict[str, Any]] = field(default_factory=lambda: [])
    tool_registry: ToolRegistry | None = None
    skill_registry: SkillRegistry | None = None
    usage_monitor: UsageMonitor | None = field(default_factory=UsageMonitor)

    def __post_init__(self) -> None:
        """初始化日誌。"""
        logger.info(
            'Agent 已初始化',
            extra={'model': self.config.provider.model},
        )

    def reset_conversation(self) -> None:
        """重設對話歷史。"""
        self.conversation = []
        logger.debug('對話歷史已重設')

    async def _stream_with_tool_loop(
        self,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """執行串流迴圈，支援工具調用。

        Yields:
            str: 回應的每個 token
            dict: 事件通知（tool_call、preamble_end）

        Raises:
            ProviderAuthError: Provider 認證失敗
            ProviderConnectionError: Provider 連線失敗
            ProviderTimeoutError: Provider 回應超時
        """
        response_parts: list[str] = []

        try:
            while True:
                # 準備 API 參數（透過 SkillRegistry 動態組合 system prompt）
                if self.skill_registry:
                    system = self.skill_registry.get_combined_system_prompt(
                        self.config.system_prompt
                    )
                else:
                    system = self.config.system_prompt
                tools = self.tool_registry.get_tool_definitions() if self.tool_registry else None

                async with self.provider.stream(
                    messages=self.conversation,
                    system=system,
                    tools=tools,
                    max_tokens=self.config.provider.max_tokens,
                ) as result:
                    async for text in result.text_stream:
                        response_parts.append(text)
                        yield text

                    final_message = await result.get_final_result()

                # 記錄 API 使用量
                if self.usage_monitor and final_message.usage:
                    self.usage_monitor.record(final_message.usage)

                # 將 assistant 回應加入對話歷史
                self.conversation.append(
                    {
                        'role': 'assistant',
                        'content': final_message.content,
                    }
                )

                # 若無工具調用，結束迴圈
                if final_message.stop_reason != 'tool_use' or not self.tool_registry:
                    logger.debug(
                        '串流回應完成',
                        extra={'response_length': len(''.join(response_parts))},
                    )
                    break

                # 標記 preamble 結束（僅在有文字時）
                if response_parts:
                    yield {'type': 'preamble_end', 'data': {}}

                # 收集所有工具調用區塊
                tool_use_blocks = [b for b in final_message.content if b.get('type') == 'tool_use']

                # 先通知前端所有工具開始執行
                for block in tool_use_blocks:
                    logger.info(
                        '執行工具',
                        extra={'tool_name': block['name'], 'tool_id': block['id']},
                    )
                    yield {
                        'type': 'tool_call',
                        'data': {
                            'name': block['name'],
                            'status': 'started',
                        },
                    }

                # 並行執行所有工具
                async def _run_tool(
                    tool_block: dict[str, Any],
                ) -> tuple[Any, Exception | None]:
                    """執行單一工具，回傳 (結果, 錯誤)。"""
                    try:
                        res = await self.tool_registry.execute(  # type: ignore[union-attr]
                            tool_block['name'],
                            tool_block['input'],
                        )
                        return (res, None)
                    except Exception as exc:
                        return (None, exc)

                exec_results = await asyncio.gather(*[_run_tool(b) for b in tool_use_blocks])

                # 收集結果並通知前端完成狀態
                tool_results: list[dict[str, Any]] = []
                for block, (result_val, error) in zip(tool_use_blocks, exec_results):
                    if error is None:
                        result_content = (
                            json.dumps(result_val, ensure_ascii=False)
                            if isinstance(result_val, dict)
                            else str(result_val)
                        )
                        tool_results.append(
                            {
                                'type': 'tool_result',
                                'tool_use_id': block['id'],
                                'content': result_content,
                            }
                        )
                        yield {
                            'type': 'tool_call',
                            'data': {
                                'name': block['name'],
                                'status': 'completed',
                            },
                        }
                    else:
                        logger.warning(
                            '工具執行失敗',
                            extra={'tool_name': block['name'], 'error': str(error)},
                        )
                        tool_results.append(
                            {
                                'type': 'tool_result',
                                'tool_use_id': block['id'],
                                'content': str(error),
                                'is_error': True,
                            }
                        )
                        yield {
                            'type': 'tool_call',
                            'data': {
                                'name': block['name'],
                                'status': 'failed',
                                'error': str(error),
                            },
                        }

                self.conversation.append(
                    {
                        'role': 'user',
                        'content': tool_results,
                    }
                )
                logger.debug(
                    '工具結果已回傳，繼續對話',
                    extra={'tool_count': len(tool_results)},
                )

                # 重置 response_parts 以收集下一輪串流
                response_parts = []

        except ProviderAuthError:
            # 認證失敗：移除剛加入的 user message
            self.conversation.pop()
            raise
        except (ProviderConnectionError, ProviderTimeoutError):
            # 連線/超時：保留部分回應（如果有的話）
            if response_parts:
                partial = ''.join(response_parts)
                self.conversation.append({'role': 'assistant', 'content': partial})
                logger.warning(
                    '串流中斷，已保留部分回應',
                    extra={'partial_length': len(partial)},
                )
            else:
                self.conversation.pop()
            raise

    async def stream_message(
        self,
        content: str,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """以串流方式發送訊息並逐步取得回應。

        支援工具調用迴圈：當 LLM 回傳 tool_use 時，
        自動執行工具並將結果回傳，直到取得最終文字回應。

        Args:
            content: 使用者訊息內容

        Yields:
            str: 回應的每個 token
            dict: 事件通知（tool_call、preamble_end）

        Raises:
            ValueError: 訊息為空白
            ProviderConnectionError: Provider 連線失敗
            ProviderAuthError: Provider 認證失敗
            ProviderTimeoutError: Provider 回應超時
        """
        # 驗證輸入
        content = content.strip()
        if not content:
            raise ValueError('訊息不可為空白，請輸入有效內容')

        # 加入使用者訊息到對話歷史
        self.conversation.append({'role': 'user', 'content': content})
        logger.debug('收到使用者訊息 (串流模式)', extra={'content_length': len(content)})

        # 執行串流迴圈（包含工具調用處理）
        async for token in self._stream_with_tool_loop():
            yield token

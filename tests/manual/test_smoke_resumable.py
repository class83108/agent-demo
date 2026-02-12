"""Resumable Stream Smoke Test。

驗證 EventStore 在真實 API 下的完整行為：
- Agent 串流時事件正確寫入 EventStore
- 從 EventStore 讀取完整事件序列
- 模擬斷線後從 offset 恢復，不遺漏不重複

執行方式：
    uv run pytest tests/manual/test_smoke_resumable.py --run-smoke -v
"""

from __future__ import annotations

import allure
import pytest

from agent_core.agent import Agent
from agent_core.config import AgentCoreConfig, ProviderConfig
from agent_core.event_store import MemoryEventStore
from agent_core.providers.anthropic_provider import AnthropicProvider
from agent_core.types import AgentEvent

pytestmark = pytest.mark.smoke


# =============================================================================
# 輔助函數
# =============================================================================


async def _collect_response_with_events(
    agent: Agent,
    message: str,
    stream_id: str,
) -> tuple[str, list[AgentEvent]]:
    """收集串流回應的完整文字與事件。"""
    chunks: list[str] = []
    events: list[AgentEvent] = []
    async for chunk in agent.stream_message(message, stream_id=stream_id):
        if isinstance(chunk, str):
            chunks.append(chunk)
        else:
            events.append(chunk)
    return ''.join(chunks), events


def _create_agent_with_event_store(
    event_store: MemoryEventStore,
    system_prompt: str = '你是助手。請用一句話簡短回答。',
) -> Agent:
    """建立啟用 EventStore 的 Agent。"""
    config = AgentCoreConfig(
        provider=ProviderConfig(model='claude-sonnet-4-20250514'),
        system_prompt=system_prompt,
    )
    provider = AnthropicProvider(config.provider)
    return Agent(
        config=config,
        provider=provider,
        event_store=event_store,
    )


# =============================================================================
# Smoke Tests
# =============================================================================


@allure.feature('冒煙測試')
@allure.story('可恢復串流 (Smoke)')
class TestResumableStreamSmoke:
    """Smoke test — 驗證 EventStore 在真實 API 下的行為。"""

    @allure.title('Agent 串流事件完整寫入 EventStore')
    async def test_events_captured_in_store(self) -> None:
        """驗證真實 API 串流時事件正確寫入 EventStore。

        Scenario: Agent 串流時自動寫入事件到 EventStore
          Given Agent 已啟動且配置了 MemoryEventStore
          When 使用者傳送簡單問題
          Then EventStore 應包含 token 與 done 事件
          And 串流狀態應為 completed
        """
        store = MemoryEventStore()
        agent = _create_agent_with_event_store(store)
        session_id = 'smoke-sess-1'

        response, _ = await _collect_response_with_events(agent, '1+1=?', stream_id=session_id)

        # 應有回應
        assert len(response) > 0, 'Agent 應有回覆'

        # 驗證 EventStore 中的事件
        stored_events = await store.read(session_id)
        event_types = [e['type'] for e in stored_events]

        assert 'token' in event_types, f'應有 token，實際 {event_types}'
        assert 'done' in event_types, f'應有 done，實際 {event_types}'

        # 狀態應為 completed
        status = await store.get_status(session_id)
        assert status is not None
        assert status['status'] == 'completed', f'狀態應為 completed，實際 {status["status"]}'

    @allure.title('從 offset 恢復不遺漏不重複')
    async def test_resume_from_offset(self) -> None:
        """模擬客戶端斷線後從 offset 恢復。

        Scenario: 從指定 offset 恢復已完成的串流
          Given Agent 已完成一次真實 API 串流
          And EventStore 記錄了所有事件
          When 模擬客戶端只收到前 3 個事件後斷線
          And 使用最後收到的 event_id 從 EventStore 恢復
          Then 恢復後的事件應補齊剩餘所有事件
          And 合併後的事件序列應與完整序列一致
        """
        store = MemoryEventStore()
        agent = _create_agent_with_event_store(store)
        session_id = 'smoke-sess-2'

        await _collect_response_with_events(agent, '用三個詞描述天空', stream_id=session_id)

        all_events = await store.read(session_id)
        assert len(all_events) >= 3, f'應至少有 3 個事件 (tokens + done)，實際 {len(all_events)}'

        # 模擬客戶端只收到前 2 個事件
        received = all_events[:2]
        last_received_id = received[-1]['id']

        # 從斷點恢復
        remaining = await store.read(session_id, after=last_received_id)

        # 合併應等於完整序列
        merged = received + remaining
        assert len(merged) == len(all_events), (
            f'合併後應有 {len(all_events)} 個事件，實際 {len(merged)}'
        )
        for got, expected in zip(merged, all_events):
            assert got['id'] == expected['id'], f'事件 id 不一致：{got["id"]} != {expected["id"]}'

    @allure.title('token 事件的 data 拼接應等於完整回應')
    async def test_token_data_matches_response(self) -> None:
        """驗證 EventStore 中 token 事件的 data 拼接後等於串流回應。

        Scenario: token 事件完整記錄串流內容
          Given Agent 完成一次真實串流
          When 從 EventStore 讀取所有 token 事件並拼接 data
          Then 結果應等於串流收到的完整回應文字
        """
        store = MemoryEventStore()
        agent = _create_agent_with_event_store(store)
        session_id = 'smoke-sess-3'

        response, _ = await _collect_response_with_events(agent, '說 hello', stream_id=session_id)

        stored = await store.read(session_id)
        token_events = [e for e in stored if e['type'] == 'token']
        reconstructed = ''.join(e['data'] for e in token_events)

        assert reconstructed == response, (
            f'token 拼接結果應等於回應，拼接={reconstructed!r}，回應={response!r}'
        )

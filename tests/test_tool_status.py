"""工具使用狀態顯示測試模組。

根據 docs/features/tool_status.feature 規格撰寫測試案例。
涵蓋：
- Rule: 工具狀態應顯示名稱與參數摘要
- Rule: Agent 呼叫工具時應通知使用者（事件產生）
- Rule: 工具呼叫前的文字應與最終回覆區隔（preamble_end 事件）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

from agent_demo.agent import Agent, AgentConfig
from agent_demo.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# =============================================================================
# Mock Helpers（複用 test_agent.py 的模式）
# =============================================================================


def _make_text_block(text: str) -> MagicMock:
    """建立模擬的 TextBlock。"""
    block = MagicMock()
    block.type = 'text'
    block.text = text
    block.model_dump.return_value = {'type': 'text', 'text': text}
    return block


def _make_tool_use_block(tool_id: str, name: str, input_data: dict[str, Any]) -> MagicMock:
    """建立模擬的 ToolUseBlock。"""
    block = MagicMock()
    block.type = 'tool_use'
    block.id = tool_id
    block.name = name
    block.input = input_data
    block.model_dump.return_value = {
        'type': 'tool_use',
        'id': tool_id,
        'name': name,
        'input': input_data,
    }
    return block


def _make_final_message(
    content_blocks: list[MagicMock],
    stop_reason: str = 'end_turn',
) -> MagicMock:
    """建立模擬的 Final Message。"""
    message = MagicMock()
    message.content = content_blocks
    message.stop_reason = stop_reason
    return message


def create_mock_stream(
    text_chunks: list[str],
    stop_reason: str = 'end_turn',
    content_blocks: list[MagicMock] | None = None,
) -> MagicMock:
    """建立模擬的串流回應。"""

    async def mock_text_stream() -> AsyncIterator[str]:
        for chunk in text_chunks:
            yield chunk

    if content_blocks is None:
        full_text = ''.join(text_chunks)
        content_blocks = [_make_text_block(full_text)]

    final_message = _make_final_message(content_blocks, stop_reason)

    stream_context = MagicMock()
    stream_context.__aenter__ = AsyncMock(return_value=stream_context)
    stream_context.__aexit__ = AsyncMock(return_value=None)
    stream_context.text_stream = mock_text_stream()
    stream_context.get_final_message = AsyncMock(return_value=final_message)

    return stream_context


async def collect_stream_with_events(
    agent: Agent, message: str
) -> tuple[str, list[dict[str, Any]]]:
    """收集串流回應，分離文字 token 與事件。

    Returns:
        (完整文字, 事件列表)
    """
    text_parts: list[str] = []
    events: list[dict[str, Any]] = []

    async for item in agent.stream_message(message):
        if isinstance(item, str):
            text_parts.append(item)
        else:
            events.append(item)

    return ''.join(text_parts), events


# =============================================================================
# Rule: 工具狀態應顯示名稱與參數摘要
# =============================================================================


class TestToolSummary:
    """測試工具摘要產生。"""

    def test_read_file_summary(self) -> None:
        """Scenario: 讀取檔案時顯示檔案路徑。

        When Agent 呼叫 "read_file" 工具，參數為 path="src/main.py"
        Then 狀態應顯示為「讀取檔案 src/main.py」
        """
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('read_file', {'path': 'src/main.py'})
        assert summary == '讀取檔案 src/main.py'

    def test_grep_search_summary(self) -> None:
        """Scenario: 搜尋程式碼時顯示搜尋模式。

        When Agent 呼叫 "grep_search" 工具，參數為 pattern="logger"
        Then 狀態應顯示為「搜尋程式碼 logger」
        """
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('grep_search', {'pattern': 'logger'})
        assert summary == '搜尋程式碼 logger'

    def test_edit_file_summary(self) -> None:
        """Scenario: 編輯檔案時顯示檔案路徑。

        When Agent 呼叫 "edit_file" 工具，參數為 path="src/main.py"
        Then 狀態應顯示為「編輯檔案 src/main.py」
        """
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('edit_file', {'path': 'src/main.py'})
        assert summary == '編輯檔案 src/main.py'

    def test_bash_summary(self) -> None:
        """Scenario: 執行命令時顯示命令摘要。

        When Agent 呼叫 "bash" 工具，參數為 command="uv run pytest"
        Then 狀態應顯示為「執行命令 uv run pytest」
        """
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('bash', {'command': 'uv run pytest'})
        assert summary == '執行命令 uv run pytest'

    def test_list_files_summary(self) -> None:
        """Scenario: 列出檔案時顯示路徑。

        When Agent 呼叫 "list_files" 工具，參數為 path="src/"
        Then 狀態應顯示為「列出檔案 src/」
        """
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('list_files', {'path': 'src/'})
        assert summary == '列出檔案 src/'

    def test_unknown_tool_summary(self) -> None:
        """未知工具應顯示工具名稱。"""
        from agent_demo.agent import get_tool_summary

        summary = get_tool_summary('custom_tool', {'key': 'value'})
        assert 'custom_tool' in summary

    def test_long_command_truncated(self) -> None:
        """過長的命令參數應截斷顯示。"""
        from agent_demo.agent import get_tool_summary

        long_cmd = 'a' * 200
        summary = get_tool_summary('bash', {'command': long_cmd})
        # 摘要不應超過合理長度
        assert len(summary) < 150


# =============================================================================
# Rule: Agent 呼叫工具時應通知使用者
# =============================================================================


class TestToolCallEvents:
    """測試工具呼叫事件產生。"""

    async def test_tool_call_emits_started_and_completed(self) -> None:
        """Scenario: 工具成功執行時產生 started 和 completed 事件。

        Given Agent 正在處理使用者的問題
        When Agent 呼叫 "read_file" 工具且執行成功
        Then 應產生 tool_call started 事件
        And 應產生 tool_call completed 事件
        And 事件應包含工具名稱與參數摘要
        """
        # Arrange
        registry = ToolRegistry()
        registry.register(
            name='read_file',
            description='讀取檔案',
            parameters={
                'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path'],
            },
            handler=lambda path: {'content': 'file content', 'path': path},  # type: ignore[reportUnknownLambdaType]
        )
        mock_client = MagicMock()
        agent = Agent(
            config=AgentConfig(system_prompt='測試'),
            client=mock_client,
            tool_registry=registry,
        )

        # 第一次：Claude 回傳 tool_use
        tool_use_block = _make_tool_use_block('t1', 'read_file', {'path': 'main.py'})
        first_stream = create_mock_stream(
            text_chunks=[],
            stop_reason='tool_use',
            content_blocks=[tool_use_block],
        )

        # 第二次：Claude 回傳最終文字
        second_stream = create_mock_stream(['結果'])
        mock_client.messages.stream.side_effect = [first_stream, second_stream]

        # Act
        text, events = await collect_stream_with_events(agent, '讀取 main.py')

        # Assert - 文字結果
        assert text == '結果'

        # Assert - 事件
        tool_events = [e for e in events if e['type'] == 'tool_call']
        assert len(tool_events) == 2

        # started 事件
        started = tool_events[0]
        assert started['data']['status'] == 'started'
        assert started['data']['name'] == 'read_file'
        assert 'summary' in started['data']

        # completed 事件
        completed = tool_events[1]
        assert completed['data']['status'] == 'completed'
        assert completed['data']['name'] == 'read_file'

    async def test_tool_call_failure_emits_failed_event(self) -> None:
        """Scenario: 工具執行失敗時產生 failed 事件。

        Given Agent 正在執行 "read_file" 工具
        When 工具執行發生錯誤
        Then 應產生 tool_call failed 事件
        And 事件應包含錯誤訊息
        """

        # Arrange
        def failing_handler(path: str) -> str:
            raise FileNotFoundError('檔案不存在')

        registry = ToolRegistry()
        registry.register(
            name='read_file',
            description='讀取檔案',
            parameters={
                'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path'],
            },
            handler=failing_handler,
        )
        mock_client = MagicMock()
        agent = Agent(
            config=AgentConfig(system_prompt='測試'),
            client=mock_client,
            tool_registry=registry,
        )

        # 第一次：Claude 回傳 tool_use
        tool_use_block = _make_tool_use_block('t1', 'read_file', {'path': 'x.py'})
        first_stream = create_mock_stream(
            text_chunks=[],
            stop_reason='tool_use',
            content_blocks=[tool_use_block],
        )

        # 第二次：Claude 回傳最終文字
        second_stream = create_mock_stream(['找不到檔案'])
        mock_client.messages.stream.side_effect = [first_stream, second_stream]

        # Act
        _, events = await collect_stream_with_events(agent, '讀取 x.py')

        # Assert
        tool_events = [e for e in events if e['type'] == 'tool_call']
        assert len(tool_events) == 2

        started = tool_events[0]
        assert started['data']['status'] == 'started'

        failed = tool_events[1]
        assert failed['data']['status'] == 'failed'
        assert 'error' in failed['data']


# =============================================================================
# Rule: 工具呼叫前的文字應與最終回覆區隔
# =============================================================================


class TestPreambleEvents:
    """測試 preamble_end 事件。"""

    async def test_preamble_end_emitted_when_text_before_tool(self) -> None:
        """Scenario: Preamble 文字應觸發 preamble_end 事件。

        Given Agent 串流回應文字 "讓我查看一下程式碼..."
        When Agent 接著呼叫工具
        Then 應產生 preamble_end 事件
        """
        # Arrange
        registry = ToolRegistry()
        registry.register(
            name='read_file',
            description='讀取檔案',
            parameters={
                'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path'],
            },
            handler=lambda path: {'content': 'ok', 'path': path},  # type: ignore[reportUnknownLambdaType]
        )
        mock_client = MagicMock()
        agent = Agent(
            config=AgentConfig(system_prompt='測試'),
            client=mock_client,
            tool_registry=registry,
        )

        # 第一次：Claude 回傳 preamble 文字 + tool_use
        text_block = _make_text_block('讓我查看程式碼...')
        tool_block = _make_tool_use_block('t1', 'read_file', {'path': 'main.py'})
        first_stream = create_mock_stream(
            text_chunks=['讓我查看', '程式碼...'],
            stop_reason='tool_use',
            content_blocks=[text_block, tool_block],
        )

        # 第二次：最終回應
        second_stream = create_mock_stream(['程式碼內容如下'])
        mock_client.messages.stream.side_effect = [first_stream, second_stream]

        # Act
        _, events = await collect_stream_with_events(agent, '看程式碼')

        # Assert - preamble_end 事件應存在
        preamble_events = [e for e in events if e['type'] == 'preamble_end']
        assert len(preamble_events) == 1

        # Assert - preamble_end 應在 tool_call 之前
        event_types = [e['type'] for e in events]
        preamble_idx = event_types.index('preamble_end')
        tool_idx = event_types.index('tool_call')
        assert preamble_idx < tool_idx

    async def test_no_preamble_when_no_text_before_tool(self) -> None:
        """Scenario: 無 preamble 文字時不應產生 preamble_end 事件。

        Given Agent 直接呼叫工具（無前置文字）
        Then 不應產生 preamble_end 事件
        """
        # Arrange
        registry = ToolRegistry()
        registry.register(
            name='read_file',
            description='讀取檔案',
            parameters={
                'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path'],
            },
            handler=lambda path: {'content': 'ok', 'path': path},  # type: ignore[reportUnknownLambdaType]
        )
        mock_client = MagicMock()
        agent = Agent(
            config=AgentConfig(system_prompt='測試'),
            client=mock_client,
            tool_registry=registry,
        )

        # Claude 直接呼叫工具，無文字
        tool_block = _make_tool_use_block('t1', 'read_file', {'path': 'main.py'})
        first_stream = create_mock_stream(
            text_chunks=[],
            stop_reason='tool_use',
            content_blocks=[tool_block],
        )
        second_stream = create_mock_stream(['結果'])
        mock_client.messages.stream.side_effect = [first_stream, second_stream]

        # Act
        _, events = await collect_stream_with_events(agent, '讀取')

        # Assert - 不應有 preamble_end 事件
        preamble_events = [e for e in events if e['type'] == 'preamble_end']
        assert len(preamble_events) == 0

    async def test_multiple_tool_calls_produce_multiple_preambles(self) -> None:
        """Scenario: 多次工具呼叫產生多個 preamble。

        Given Agent 先呼叫工具，中間有文字，再呼叫工具
        Then 應產生兩段 preamble_end 事件
        """
        # Arrange
        registry = ToolRegistry()
        registry.register(
            name='read_file',
            description='讀取檔案',
            parameters={
                'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path'],
            },
            handler=lambda path: {'content': 'ok', 'path': path},  # type: ignore[reportUnknownLambdaType]
        )
        mock_client = MagicMock()
        agent = Agent(
            config=AgentConfig(system_prompt='測試'),
            client=mock_client,
            tool_registry=registry,
        )

        # 第一次：preamble + tool_use
        text_block_1 = _make_text_block('先讀取第一個檔案...')
        tool_block_1 = _make_tool_use_block('t1', 'read_file', {'path': 'a.py'})
        first_stream = create_mock_stream(
            text_chunks=['先讀取第一個檔案...'],
            stop_reason='tool_use',
            content_blocks=[text_block_1, tool_block_1],
        )

        # 第二次：preamble + 另一個 tool_use
        text_block_2 = _make_text_block('接下來讀取第二個...')
        tool_block_2 = _make_tool_use_block('t2', 'read_file', {'path': 'b.py'})
        second_stream = create_mock_stream(
            text_chunks=['接下來讀取第二個...'],
            stop_reason='tool_use',
            content_blocks=[text_block_2, tool_block_2],
        )

        # 第三次：最終回應
        third_stream = create_mock_stream(['完成'])
        mock_client.messages.stream.side_effect = [first_stream, second_stream, third_stream]

        # Act
        _, events = await collect_stream_with_events(agent, '讀取兩個檔案')

        # Assert - 應有兩個 preamble_end 事件
        preamble_events = [e for e in events if e['type'] == 'preamble_end']
        assert len(preamble_events) == 2

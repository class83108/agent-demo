"""Eval 框架核心模組。

提供 EvalTask Protocol、EvalResult 資料結構、EvalRunner 執行器。
用於量化 Agent 在程式碼修改任務上的能力。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from agent_core.agent import Agent
from agent_core.config import AgentCoreConfig, ProviderConfig
from agent_core.providers.anthropic_provider import AnthropicProvider
from agent_core.token_counter import TokenCounter
from agent_core.tools.setup import create_default_registry
from agent_core.types import AgentEvent, MessageParam

logger = logging.getLogger(__name__)


# --- EvalResult ---


@dataclass
class EvalResult:
    """評估結果。

    Attributes:
        task_name: 任務名稱
        task_level: 任務難度等級 (easy/medium/hard/special)
        passed: 所有驗證是否通過
        score: 0.0-1.0 的評分
        details: 任務特定的詳細資訊
        tool_calls: 工具調用次數
        tool_call_sequence: 工具調用順序列表
        total_tokens: 總消耗 token 數
        duration_seconds: 執行耗時（秒）
        ran_verification: Agent 是否自行執行了測試
        error: 框架層級的錯誤訊息
        system_prompt_hash: 系統提示詞的 SHA256 前 8 碼
    """

    task_name: str
    task_level: str = ''
    passed: bool = False
    score: float = 0.0
    details: dict[str, Any] = field(default_factory=lambda: {})
    tool_calls: int = 0
    tool_call_sequence: list[str] = field(default_factory=lambda: [])
    total_tokens: int = 0
    duration_seconds: float = 0.0
    ran_verification: bool = False
    error: str | None = None
    system_prompt_hash: str = ''

    def to_dict(self) -> dict[str, Any]:
        """轉換為可序列化的字典。"""
        return asdict(self)


# --- EvalTask Protocol ---


class EvalTask(Protocol):
    """評估任務介面。

    每個任務模組必須實作此 Protocol 的所有屬性和方法。
    """

    TASK_NAME: str
    TASK_LEVEL: str
    TASK_PROMPT: str

    def setup(self, sandbox: Path) -> None:
        """在 sandbox 中建立任務所需的檔案。"""
        ...

    def evaluate(self, sandbox: Path, events: list[AgentEvent]) -> EvalResult:
        """評估 Agent 的執行結果。"""
        ...


# --- 輔助函數 ---


def run_pytest_in_sandbox(sandbox: Path, timeout: int = 60) -> tuple[bool, str]:
    """在 sandbox 中執行 pytest。

    Args:
        sandbox: sandbox 目錄路徑
        timeout: pytest 執行超時秒數

    Returns:
        (是否通過, 輸出文字) 的 tuple
    """
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', str(sandbox), '-v', '--tb=short', '--no-header'],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(sandbox),
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def check_ran_tests_from_conversation(conversation: list[MessageParam]) -> bool:
    """從對話歷史中檢查 Agent 是否執行了測試。

    遍歷 assistant 訊息中的 tool_use block，
    檢查 bash 工具的 command 參數是否包含 pytest 等測試命令。

    Args:
        conversation: Agent 的對話歷史

    Returns:
        Agent 是否執行了測試
    """
    test_commands = ['pytest', 'python -m pytest', 'python -m unittest']
    for msg in conversation:
        if msg['role'] != 'assistant':
            continue
        content = msg['content']
        if not isinstance(content, list):
            continue
        for block in content:
            if block['type'] != 'tool_use':
                continue
            # narrowed to ToolUseBlock，可直接用 ['key'] 存取
            if block['name'] != 'bash':
                continue
            command = str(block['input'].get('command', ''))
            if any(tc in command for tc in test_commands):
                return True
    return False


def compute_prompt_hash(prompt: str) -> str:
    """計算系統提示詞的短雜湊值。

    Args:
        prompt: 系統提示詞

    Returns:
        SHA256 前 8 碼
    """
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]


# --- EvalRunner ---


class EvalRunner:
    """評估執行器。

    負責建立 Agent、設定 sandbox、執行任務、收集結果。

    Attributes:
        system_prompt: 系統提示詞
        timeout_seconds: 每個任務的超時時間（秒）
        model: 使用的模型名稱
    """

    def __init__(
        self,
        system_prompt: str,
        timeout_seconds: float = 300.0,
        model: str = 'claude-sonnet-4-20250514',
        enable_memory: bool = False,
    ) -> None:
        self.system_prompt = system_prompt
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.enable_memory = enable_memory
        self._prompt_hash = compute_prompt_hash(system_prompt)

    def _create_agent(self, sandbox: Path) -> Agent:
        """建立含完整工具的 Agent。

        Args:
            sandbox: sandbox 目錄路徑

        Returns:
            已配置的 Agent 實例
        """
        memory_dir = sandbox / '.memories' if self.enable_memory else None
        registry = create_default_registry(sandbox, memory_dir=memory_dir)
        config = AgentCoreConfig(
            provider=ProviderConfig(model=self.model),
            system_prompt=self.system_prompt,
        )
        provider = AnthropicProvider(config.provider)
        token_counter = TokenCounter()
        return Agent(
            config=config,
            provider=provider,
            tool_registry=registry,
            token_counter=token_counter,
        )

    async def run_task(
        self,
        task_module: EvalTask,
        sandbox: Path,
    ) -> EvalResult:
        """執行單一評估任務。

        建立 Agent、執行任務、收集計量資訊、執行評估。

        Args:
            task_module: 任務模組（符合 EvalTask Protocol）
            sandbox: sandbox 目錄路徑

        Returns:
            評估結果
        """
        # 步驟 1: 設定 sandbox
        task_module.setup(sandbox)

        # 步驟 2: 建立 Agent
        agent = self._create_agent(sandbox)

        # 步驟 3: 執行 Agent（含超時控制）
        events: list[AgentEvent] = []
        response_parts: list[str] = []
        start_time = time.monotonic()

        try:
            async with asyncio.timeout(self.timeout_seconds):
                async for chunk in agent.stream_message(task_module.TASK_PROMPT):
                    if isinstance(chunk, str):
                        response_parts.append(chunk)
                    else:
                        events.append(chunk)
        except TimeoutError:
            duration = time.monotonic() - start_time
            return EvalResult(
                task_name=task_module.TASK_NAME,
                task_level=task_module.TASK_LEVEL,
                passed=False,
                score=0.0,
                error=f'任務超時（{self.timeout_seconds} 秒）',
                duration_seconds=duration,
                system_prompt_hash=self._prompt_hash,
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            return EvalResult(
                task_name=task_module.TASK_NAME,
                task_level=task_module.TASK_LEVEL,
                passed=False,
                score=0.0,
                error=f'框架錯誤: {type(exc).__name__}: {exc}',
                duration_seconds=duration,
                system_prompt_hash=self._prompt_hash,
            )

        duration = time.monotonic() - start_time

        # 步驟 4: 收集計量資訊
        tool_call_sequence = [
            e['data']['name']
            for e in events
            if e['type'] == 'tool_call' and e['data'].get('status') == 'completed'
        ]
        tool_call_count = len(tool_call_sequence)

        total_tokens = 0
        if agent.usage_monitor:
            summary = agent.usage_monitor.get_summary()
            tokens = summary.get('tokens', {})
            total_tokens = tokens.get('total_input', 0) + tokens.get('output', 0)

        ran_verification = check_ran_tests_from_conversation(agent.conversation)

        # 步驟 5: 執行評估
        eval_result = task_module.evaluate(sandbox, events)

        # 步驟 6: 補充計量欄位
        eval_result.tool_calls = tool_call_count
        eval_result.tool_call_sequence = tool_call_sequence
        eval_result.total_tokens = total_tokens
        eval_result.duration_seconds = duration
        eval_result.ran_verification = ran_verification
        eval_result.system_prompt_hash = self._prompt_hash

        return eval_result

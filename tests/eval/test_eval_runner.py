"""Eval Runner 測試入口。

使用 pytest.mark.parametrize 動態參數化所有任務模組。
執行方式: uv run pytest tests/eval --run-eval -v --eval-agent-version="v1"
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import allure
import pytest

from tests.eval.framework import EvalRunner
from tests.eval.store import EvalStore
from tests.eval.tasks import discover_tasks

pytestmark = pytest.mark.eval

# 動態探索所有任務（type: Any 因為 ModuleType 無法滿足 EvalTask Protocol 的靜態檢查）
_ALL_TASKS: list[Any] = discover_tasks()


def _task_id(task: Any) -> str:
    """產生 pytest parametrize ID。"""
    return str(getattr(task, 'TASK_NAME', task.__name__))


@allure.feature('Agent Eval')
class TestEvalRunner:
    """參數化執行所有 eval 任務。"""

    @pytest.mark.parametrize('task_module', _ALL_TASKS, ids=_task_id)
    async def test_eval_task(
        self,
        task_module: Any,
        tmp_path: Path,
        eval_system_prompt: str,
        eval_timeout: float,
        eval_model: str,
        eval_store: EvalStore,
        eval_run_id: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """執行單一 eval 任務並驗證結果。"""
        # 檢查是否只執行特定任務
        specific_task: str | None = request.config.getoption('--eval-task')
        if specific_task and specific_task not in task_module.__name__:
            pytest.skip(f'只執行 {specific_task}')

        # 建立 sandbox
        sandbox = tmp_path / 'sandbox'
        sandbox.mkdir()

        # 執行任務
        runner = EvalRunner(
            system_prompt=eval_system_prompt,
            timeout_seconds=eval_timeout,
            model=eval_model,
        )
        result = await runner.run_task(task_module, sandbox)

        # 存入 SQLite
        eval_store.save_result(eval_run_id, result.to_dict())

        # Allure 附件
        allure.attach(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            name=f'{result.task_name} 結果',
            attachment_type=allure.attachment_type.JSON,  # type: ignore[attr-defined]
        )

        # 印出單一任務結果
        status = 'PASS' if result.passed else 'FAIL'
        print(  # noqa: T201
            f'\n  [{status}] {result.task_name}'
            f'  score={result.score:.2f}'
            f'  tools={result.tool_calls}'
            f'  tokens={result.total_tokens}'
            f'  time={result.duration_seconds:.1f}s'
            f'  verified={result.ran_verification}'
        )

        # 斷言
        assert result.error is None, f'框架錯誤: {result.error}'
        assert result.passed, (
            f'任務 {result.task_name} 未通過 (score={result.score})\n'
            f'詳情: {json.dumps(result.details, ensure_ascii=False, indent=2)}'
        )


@pytest.fixture(scope='session', autouse=True)
def _print_eval_summary(  # type: ignore[reportUnusedFunction]
    eval_store: EvalStore,
    eval_run_id: str,
) -> Generator[None]:
    """Session 結束時印出 eval 摘要。"""
    yield
    eval_store.print_summary(eval_run_id)

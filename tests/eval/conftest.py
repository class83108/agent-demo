"""Eval 測試的 pytest 配置。

提供 --run-eval flag、eval 專用 fixtures、以及 session-scoped 的 EvalStore。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from tests.eval.framework import compute_prompt_hash
from tests.eval.store import EvalStore

# 預設的 eval 系統提示詞
DEFAULT_EVAL_SYSTEM_PROMPT = """你是一位專業的程式開發助手。

工作原則：
- 先閱讀相關檔案理解現況，再進行修改
- 修改後執行測試驗證結果
- 一次只做一件事，確認正確後再進行下一步
- 遇到錯誤時分析原因，不要盲目重試

你可以使用以下工具：read_file、edit_file、list_files、bash、grep_search。
請使用繁體中文回答。"""


def pytest_addoption(parser: pytest.Parser) -> None:
    """新增 eval 專用命令列參數。"""
    parser.addoption(
        '--run-eval',
        action='store_true',
        default=False,
        help='執行 eval test（會呼叫真實 API）',
    )
    parser.addoption(
        '--eval-agent-version',
        action='store',
        default='unnamed',
        help='Agent 版本標記（如 "v1-baseline"），用於結果追蹤',
    )
    parser.addoption(
        '--eval-system-prompt',
        action='store',
        default=DEFAULT_EVAL_SYSTEM_PROMPT,
        help='eval 使用的系統提示詞（用於 A/B 測試）',
    )
    parser.addoption(
        '--eval-timeout',
        action='store',
        type=float,
        default=300.0,
        help='每個任務的超時時間（秒），預設 300',
    )
    parser.addoption(
        '--eval-model',
        action='store',
        default='claude-sonnet-4-20250514',
        help='eval 使用的模型',
    )
    parser.addoption(
        '--eval-db',
        action='store',
        default='eval-results/eval.db',
        help='eval 結果 SQLite 路徑',
    )
    parser.addoption(
        '--eval-task',
        action='store',
        default=None,
        help='只執行指定的任務（模組名，如 t01_fix_syntax_error）',
    )
    parser.addoption(
        '--eval-notes',
        action='store',
        default=None,
        help='本次 eval run 的備註',
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """根據 --run-eval 決定是否跳過 eval test。"""
    if config.getoption('--run-eval'):
        return

    skip_eval = pytest.mark.skip(reason='需要加 --run-eval 才會執行')
    for item in items:
        if 'eval' in item.keywords:
            item.add_marker(skip_eval)


# --- Session-scoped Fixtures ---


@pytest.fixture(scope='session')
def eval_system_prompt(request: pytest.FixtureRequest) -> str:
    """取得 eval 系統提示詞。"""
    prompt: str = request.config.getoption('--eval-system-prompt')
    return prompt


@pytest.fixture(scope='session')
def eval_timeout(request: pytest.FixtureRequest) -> float:
    """取得 eval 超時設定。"""
    timeout: float = request.config.getoption('--eval-timeout')
    return timeout


@pytest.fixture(scope='session')
def eval_model(request: pytest.FixtureRequest) -> str:
    """取得 eval 模型。"""
    model: str = request.config.getoption('--eval-model')
    return model


@pytest.fixture(scope='session')
def eval_store(request: pytest.FixtureRequest) -> Generator[EvalStore]:
    """建立 session-scoped 的 EvalStore。"""
    db_path: str = request.config.getoption('--eval-db')
    store = EvalStore(db_path)
    yield store
    store.close()


@pytest.fixture(scope='session')
def eval_run_id(
    request: pytest.FixtureRequest,
    eval_store: EvalStore,
    eval_system_prompt: str,
    eval_model: str,
) -> str:
    """建立 session-scoped 的 eval run ID。

    整個 pytest session 的所有任務共用一個 run_id。
    """
    agent_version: str = request.config.getoption('--eval-agent-version')
    notes: str | None = request.config.getoption('--eval-notes')

    run_id = eval_store.create_run(
        agent_version=agent_version,
        system_prompt=eval_system_prompt,
        system_prompt_hash=compute_prompt_hash(eval_system_prompt),
        model=eval_model,
        notes=notes,
    )
    return run_id

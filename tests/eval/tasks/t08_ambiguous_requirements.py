"""T8 — Ambiguous Requirements (Special)。

一個已使用 structlog 的專案，Agent 收到「幫 user_service.py 加上 logging」的指令。
不指定用什麼 library、log 什麼、什麼 level。
測試 Agent 是否會先探索專案慣例再動手。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T8 - Ambiguous Requirements'
TASK_LEVEL: str = 'special'
TASK_PROMPT: str = '幫 user_service.py 加上適當的 logging。'


def setup(sandbox: Path) -> None:
    """建立已使用 structlog 的專案。"""
    (sandbox / 'services').mkdir()
    (sandbox / 'services' / '__init__.py').write_text('', encoding='utf-8')

    # order_service.py — 已有 structlog logging 的範例
    (sandbox / 'services' / 'order_service.py').write_text(
        'import logging\n'
        '\n'
        'logger = logging.getLogger(__name__)\n'
        '\n'
        '\n'
        'def create_order(user_id: str, amount: float) -> dict[str, object]:\n'
        '    """建立訂單。"""\n'
        '    logger.info("建立訂單", extra={"user_id": user_id, "amount": amount})\n'
        '    if amount <= 0:\n'
        '        logger.warning("無效金額", extra={"amount": amount})\n'
        '        raise ValueError("金額必須大於零")\n'
        '    order = {"user_id": user_id, "amount": amount, "status": "pending"}\n'
        '    logger.info("訂單建立成功", extra={"order": order})\n'
        '    return order\n',
        encoding='utf-8',
    )

    # payment_service.py — 另一個有 logging 的範例
    (sandbox / 'services' / 'payment_service.py').write_text(
        'import logging\n'
        '\n'
        'logger = logging.getLogger(__name__)\n'
        '\n'
        '\n'
        'def process_payment(order_id: str, amount: float) -> bool:\n'
        '    """處理付款。"""\n'
        '    logger.info("處理付款", extra={"order_id": order_id, "amount": amount})\n'
        '    if amount > 10000:\n'
        '        logger.warning("大額交易", extra={"amount": amount})\n'
        '    logger.info("付款完成", extra={"order_id": order_id})\n'
        '    return True\n',
        encoding='utf-8',
    )

    # user_service.py — 目標檔案，沒有 logging
    (sandbox / 'services' / 'user_service.py').write_text(
        'def create_user(name: str, email: str) -> dict[str, str]:\n'
        '    """建立使用者。"""\n'
        '    if not name.strip():\n'
        '        raise ValueError("名稱不可為空")\n'
        '    if "@" not in email:\n'
        '        raise ValueError("無效的 email")\n'
        '    return {"name": name.strip(), "email": email}\n'
        '\n'
        '\n'
        'def delete_user(user_id: str) -> bool:\n'
        '    """刪除使用者。"""\n'
        '    if not user_id:\n'
        '        raise ValueError("user_id 不可為空")\n'
        '    return True\n',
        encoding='utf-8',
    )

    # test_user_service.py — 既有測試（必須繼續通過）
    (sandbox / 'test_user_service.py').write_text(
        'import pytest\n'
        '\n'
        'from services.user_service import create_user, delete_user\n'
        '\n'
        '\n'
        'def test_create_user() -> None:\n'
        '    user = create_user("Alice", "alice@test.com")\n'
        '    assert user["name"] == "Alice"\n'
        '    assert user["email"] == "alice@test.com"\n'
        '\n'
        '\n'
        'def test_create_user_empty_name() -> None:\n'
        '    with pytest.raises(ValueError):\n'
        '        create_user("", "a@b.com")\n'
        '\n'
        '\n'
        'def test_create_user_invalid_email() -> None:\n'
        '    with pytest.raises(ValueError):\n'
        '        create_user("Bob", "invalid")\n'
        '\n'
        '\n'
        'def test_delete_user() -> None:\n'
        '    assert delete_user("user-123") is True\n'
        '\n'
        '\n'
        'def test_delete_user_empty_id() -> None:\n'
        '    with pytest.raises(ValueError):\n'
        '        delete_user("")\n',
        encoding='utf-8',
    )


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估 logging 加入結果 — 重點在流程品質。"""
    details: dict[str, Any] = {}

    source = sandbox / 'services' / 'user_service.py'
    if not source.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'services/user_service.py 不存在'},
        )

    content = source.read_text(encoding='utf-8')

    # 功能檢查：是否加入了 logging
    details['has_logging_import'] = 'import logging' in content
    details['has_logger'] = 'logger' in content or 'log' in content
    details['has_log_calls'] = 'logger.info' in content or 'logger.warning' in content

    # 風格檢查：是否使用了與其他 service 一致的 pattern
    uses_same_pattern = 'logging.getLogger(__name__)' in content and 'extra=' in content
    details['uses_project_pattern'] = uses_same_pattern

    # 流程檢查：Agent 是否先讀了其他 service 檔案
    tool_calls = [
        e['data']
        for e in events
        if e['type'] == 'tool_call' and e['data'].get('status') == 'completed'
    ]
    read_other_files = any(c.get('name') in ('read_file', 'grep_search') for c in tool_calls)
    details['explored_before_editing'] = read_other_files

    # 執行 pytest（既有測試必須繼續通過）
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    # 評分
    score = 0.0
    if passed:
        score += 0.3  # 基本：沒有破壞既有功能
    if details['has_log_calls']:
        score += 0.2  # 有加 logging
    if details['uses_project_pattern']:
        score += 0.3  # 風格一致
    if details['explored_before_editing']:
        score += 0.2  # 流程分：先探索再動手

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed and details['has_log_calls'],
        score=score,
        details=details,
    )

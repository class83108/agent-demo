"""T7 — Large Codebase Navigation (Special)。

10+ 個檔案的專案，bug 藏在深層 helper 中。
需要大量 grep + read 才能找到。
測試 Agent 在長對話中的系統化搜索能力。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T7 - Large Codebase Navigation'
TASK_LEVEL: str = 'special'
TASK_PROMPT: str = (
    '這個專案的測試有失敗。專案有多個模組，bug 可能在任何地方。\n'
    '請系統化地搜索程式碼，定位並修復問題，然後執行測試確認。'
)


def setup(sandbox: Path) -> None:
    """建立 10+ 檔案的專案，bug 藏在深層 helper。"""
    # 目錄結構
    for d in ['core', 'core/utils', 'services', 'models']:
        (sandbox / d).mkdir(parents=True, exist_ok=True)
        (sandbox / d / '__init__.py').write_text('', encoding='utf-8')

    # models/user.py
    (sandbox / 'models' / 'user.py').write_text(
        'from __future__ import annotations\n'
        'from dataclasses import dataclass\n'
        '\n'
        '\n'
        '@dataclass\n'
        'class User:\n'
        '    name: str\n'
        '    email: str\n'
        '    age: int\n',
        encoding='utf-8',
    )

    # models/order.py
    (sandbox / 'models' / 'order.py').write_text(
        'from __future__ import annotations\n'
        'from dataclasses import dataclass\n'
        '\n'
        '\n'
        '@dataclass\n'
        'class Order:\n'
        '    order_id: str\n'
        '    user_email: str\n'
        '    amount: float\n'
        '    status: str = "pending"\n',
        encoding='utf-8',
    )

    # core/utils/validators.py — BUG 在這裡：email 驗證的 regex 錯了
    (sandbox / 'core' / 'utils' / 'validators.py').write_text(
        'import re\n'
        '\n'
        '# BUG: 遺漏了點號，應該是 r".+@.+\\..+" 而不是 r".+@.+"\n'
        '_EMAIL_PATTERN = re.compile(r".+@.+")\n'
        '\n'
        '\n'
        'def validate_email(email: str) -> bool:\n'
        '    """驗證 email 格式。"""\n'
        '    return bool(_EMAIL_PATTERN.fullmatch(email))\n'
        '\n'
        '\n'
        'def validate_age(age: int) -> bool:\n'
        '    """驗證年齡範圍。"""\n'
        '    return 0 <= age <= 150\n',
        encoding='utf-8',
    )

    # core/utils/formatters.py（無 bug，干擾檔案）
    (sandbox / 'core' / 'utils' / 'formatters.py').write_text(
        'def format_currency(amount: float) -> str:\n'
        '    """格式化金額。"""\n'
        '    return f"${amount:,.2f}"\n'
        '\n'
        '\n'
        'def format_name(name: str) -> str:\n'
        '    """格式化姓名。"""\n'
        '    return name.strip().title()\n',
        encoding='utf-8',
    )

    # core/config.py（干擾檔案）
    (sandbox / 'core' / 'config.py').write_text(
        'MAX_ORDER_AMOUNT = 100000\n'
        'MIN_AGE = 18\n'
        'SUPPORTED_STATUSES = ["pending", "confirmed", "shipped", "delivered"]\n',
        encoding='utf-8',
    )

    # services/user_service.py — 使用 validator
    (sandbox / 'services' / 'user_service.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'from core.utils.validators import validate_email, validate_age\n'
        'from models.user import User\n'
        '\n'
        '\n'
        'def create_user(name: str, email: str, age: int) -> User:\n'
        '    """建立使用者。"""\n'
        '    if not validate_email(email):\n'
        '        raise ValueError(f"無效的 email: {email}")\n'
        '    if not validate_age(age):\n'
        '        raise ValueError(f"無效的年齡: {age}")\n'
        '    return User(name=name, email=email, age=age)\n',
        encoding='utf-8',
    )

    # services/order_service.py（干擾檔案，無 bug）
    (sandbox / 'services' / 'order_service.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'import uuid\n'
        '\n'
        'from core.config import MAX_ORDER_AMOUNT\n'
        'from models.order import Order\n'
        '\n'
        '\n'
        'def create_order(user_email: str, amount: float) -> Order:\n'
        '    """建立訂單。"""\n'
        '    if amount <= 0 or amount > MAX_ORDER_AMOUNT:\n'
        '        raise ValueError(f"無效的金額: {amount}")\n'
        '    return Order(\n'
        '        order_id=str(uuid.uuid4())[:8],\n'
        '        user_email=user_email,\n'
        '        amount=amount,\n'
        '    )\n',
        encoding='utf-8',
    )

    # services/report_service.py（干擾檔案）
    (sandbox / 'services' / 'report_service.py').write_text(
        'from __future__ import annotations\n'
        '\n'
        'from core.utils.formatters import format_currency\n'
        '\n'
        '\n'
        'def generate_summary(orders: list[dict[str, object]]) -> str:\n'
        '    """產生訂單摘要。"""\n'
        '    total = sum(float(o.get("amount", 0)) for o in orders)\n'
        '    return f"訂單數: {len(orders)}, 總金額: {format_currency(total)}"\n',
        encoding='utf-8',
    )

    # test_user_service.py
    (sandbox / 'test_user_service.py').write_text(
        'import pytest\n'
        '\n'
        'from services.user_service import create_user\n'
        '\n'
        '\n'
        'def test_create_user_valid() -> None:\n'
        '    user = create_user("Alice", "alice@example.com", 30)\n'
        '    assert user.name == "Alice"\n'
        '    assert user.email == "alice@example.com"\n'
        '\n'
        '\n'
        'def test_create_user_invalid_email_no_domain() -> None:\n'
        '    """沒有完整 domain 的 email 應被拒絕。"""\n'
        '    with pytest.raises(ValueError, match="無效的 email"):\n'
        '        create_user("Bob", "bob@nodomain", 25)\n'
        '\n'
        '\n'
        'def test_create_user_invalid_age() -> None:\n'
        '    with pytest.raises(ValueError, match="無效的年齡"):\n'
        '        create_user("Charlie", "c@test.com", -1)\n',
        encoding='utf-8',
    )

    # test_order_service.py（應全過，用來增加干擾）
    (sandbox / 'test_order_service.py').write_text(
        'import pytest\n'
        '\n'
        'from services.order_service import create_order\n'
        '\n'
        '\n'
        'def test_create_order_valid() -> None:\n'
        '    order = create_order("alice@example.com", 500)\n'
        '    assert order.amount == 500\n'
        '\n'
        '\n'
        'def test_create_order_invalid_amount() -> None:\n'
        '    with pytest.raises(ValueError):\n'
        '        create_order("alice@example.com", -1)\n',
        encoding='utf-8',
    )


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估修復結果。"""
    details: dict[str, Any] = {}

    validator_file = sandbox / 'core' / 'utils' / 'validators.py'
    if not validator_file.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'core/utils/validators.py 不存在'},
        )

    content = validator_file.read_text(encoding='utf-8')
    # 檢查 email regex 是否包含 domain 的點號驗證
    details['has_dot_check'] = r'\.' in content or '\\.' in content

    # 計算 tool call 數量（衡量搜索效率）
    tool_calls = [
        e['data']['name']
        for e in events
        if e['type'] == 'tool_call' and e['data'].get('status') == 'completed'
    ]
    details['tool_count'] = len(tool_calls)
    details['used_grep'] = 'grep_search' in tool_calls

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    score = 0.0
    if details['has_dot_check']:
        score += 0.3
    if passed:
        score += 0.5
    if details['used_grep']:
        score += 0.2  # 有使用搜索工具加分

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )

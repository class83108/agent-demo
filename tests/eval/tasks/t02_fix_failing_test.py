"""T2 — Fix Failing Test (Easy)。

calculator.py 的 divide() 函數沒有處理除以零的情況，
導致 test_calculator.py 中的 test_divide_by_zero 測試失敗。
Agent 需要讀取測試了解預期行為，然後修復 divide() 函數。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T2 - Fix Failing Test'
TASK_LEVEL: str = 'easy'
TASK_PROMPT: str = (
    '執行 pytest 會發現有一個測試失敗。\n請找出失敗原因並修復程式碼，讓所有測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立含有 bug 的 calculator 專案。"""
    # calculator.py — divide() 沒有處理 b == 0
    (sandbox / 'calculator.py').write_text(
        'def add(a: float, b: float) -> float:\n'
        '    """兩數相加。"""\n'
        '    return a + b\n'
        '\n'
        '\n'
        'def subtract(a: float, b: float) -> float:\n'
        '    """兩數相減。"""\n'
        '    return a - b\n'
        '\n'
        '\n'
        'def multiply(a: float, b: float) -> float:\n'
        '    """兩數相乘。"""\n'
        '    return a * b\n'
        '\n'
        '\n'
        'def divide(a: float, b: float) -> float:\n'
        '    """兩數相除。"""\n'
        '    return a / b\n',
        encoding='utf-8',
    )

    # test_calculator.py — 包含除以零的測試
    (sandbox / 'test_calculator.py').write_text(
        'import pytest\n'
        '\n'
        'from calculator import add, subtract, multiply, divide\n'
        '\n'
        '\n'
        'def test_add() -> None:\n'
        '    assert add(2, 3) == 5.0\n'
        '\n'
        '\n'
        'def test_subtract() -> None:\n'
        '    assert subtract(10, 3) == 7.0\n'
        '\n'
        '\n'
        'def test_multiply() -> None:\n'
        '    assert multiply(4, 5) == 20.0\n'
        '\n'
        '\n'
        'def test_divide() -> None:\n'
        '    assert divide(10, 2) == 5.0\n'
        '\n'
        '\n'
        'def test_divide_by_zero() -> None:\n'
        '    """除以零應該拋出 ValueError。"""\n'
        '    with pytest.raises(ValueError, match="除數不可為零"):\n'
        '        divide(10, 0)\n',
        encoding='utf-8',
    )


def evaluate(sandbox: Path, events: list[AgentEvent]) -> EvalResult:
    """評估修復結果。"""
    details: dict[str, Any] = {}

    # 檢查 calculator.py 是否存在
    calc_file = sandbox / 'calculator.py'
    if not calc_file.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'calculator.py 不存在'},
        )

    # 檢查是否加入了 zero check
    content = calc_file.read_text(encoding='utf-8')
    details['has_zero_check'] = 'b == 0' in content or 'b == 0.0' in content or 'not b' in content

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    # 評分：加入防護 0.3 + 測試全過 0.7
    score = 0.0
    if details['has_zero_check']:
        score += 0.3
    if passed:
        score += 0.7

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )

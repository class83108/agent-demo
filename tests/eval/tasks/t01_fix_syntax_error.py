"""T1 — Fix Syntax Error (Easy)。

math_utils.py 有一個 import 拼字錯誤（import mth → import math），
導致所有使用 math 模組的函數都無法運作。
Agent 需要找出並修復此錯誤，讓測試通過。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T1 - Fix Syntax Error'
TASK_LEVEL: str = 'easy'
TASK_PROMPT: str = (
    '這個專案的測試無法通過，執行 pytest 會報錯。\n請找出問題並修復，確保所有測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立含有 import 拼字錯誤的專案檔案。"""
    # math_utils.py — 含有 typo: import mth（應為 import math）
    (sandbox / 'math_utils.py').write_text(
        'import mth\n'
        '\n'
        '\n'
        'def add(a: int, b: int) -> int:\n'
        '    """兩數相加。"""\n'
        '    return a + b\n'
        '\n'
        '\n'
        'def multiply(a: int, b: int) -> int:\n'
        '    """兩數相乘。"""\n'
        '    return a * b\n'
        '\n'
        '\n'
        'def square_root(x: float) -> float:\n'
        '    """計算平方根。"""\n'
        '    return mth.sqrt(x)\n',
        encoding='utf-8',
    )

    # test_math_utils.py — 測試檔
    (sandbox / 'test_math_utils.py').write_text(
        'from math_utils import add, multiply, square_root\n'
        '\n'
        '\n'
        'def test_add() -> None:\n'
        '    assert add(2, 3) == 5\n'
        '    assert add(-1, 1) == 0\n'
        '\n'
        '\n'
        'def test_multiply() -> None:\n'
        '    assert multiply(3, 4) == 12\n'
        '    assert multiply(0, 5) == 0\n'
        '\n'
        '\n'
        'def test_square_root() -> None:\n'
        '    assert square_root(9) == 3.0\n'
        '    assert square_root(0) == 0.0\n',
        encoding='utf-8',
    )


def evaluate(sandbox: Path, events: list[AgentEvent]) -> EvalResult:
    """評估修復結果。"""
    details: dict[str, Any] = {}

    # 檢查 math_utils.py 是否存在
    math_utils = sandbox / 'math_utils.py'
    if not math_utils.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'math_utils.py 不存在'},
        )

    # 檢查 import 修正
    content = math_utils.read_text(encoding='utf-8')
    details['has_correct_import'] = 'import math' in content
    details['has_typo_import'] = 'import mth' in content and 'import math' not in content

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    # 評分：import 修正 0.5 + 測試通過 0.5
    score = 0.0
    if details['has_correct_import'] and not details['has_typo_import']:
        score += 0.5
    if passed:
        score += 0.5

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed and score >= 1.0,
        score=score,
        details=details,
    )

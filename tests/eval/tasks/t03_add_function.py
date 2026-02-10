"""T3 — Add Function (Medium)。

string_utils.py 已有 capitalize_words() 和 reverse() 兩個函數。
測試檔中有 test_slugify() 系列測試但 slugify() 尚未實作。
Agent 需要讀測試理解需求，然後實作 slugify() 讓所有測試通過。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T3 - Add Function'
TASK_LEVEL: str = 'medium'
TASK_PROMPT: str = (
    '這個專案的 string_utils.py 中缺少一個函數，'
    '導致部分測試失敗。\n'
    '請閱讀測試檔了解需求，然後實作缺少的函數，讓所有測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立 string_utils 專案。"""
    # string_utils.py — 已有兩個函數，缺 slugify
    (sandbox / 'string_utils.py').write_text(
        '"""字串工具模組。"""\n'
        '\n'
        '\n'
        'def capitalize_words(text: str) -> str:\n'
        '    """將每個單字首字母大寫。"""\n'
        '    return text.title()\n'
        '\n'
        '\n'
        'def reverse(text: str) -> str:\n'
        '    """反轉字串。"""\n'
        '    return text[::-1]\n',
        encoding='utf-8',
    )

    # test_string_utils.py — 包含 slugify 的測試
    (sandbox / 'test_string_utils.py').write_text(
        'from string_utils import capitalize_words, reverse, slugify\n'
        '\n'
        '\n'
        'def test_capitalize_words() -> None:\n'
        '    assert capitalize_words("hello world") == "Hello World"\n'
        '\n'
        '\n'
        'def test_reverse() -> None:\n'
        '    assert reverse("abc") == "cba"\n'
        '\n'
        '\n'
        'def test_slugify_basic() -> None:\n'
        '    """基本的空格轉連字號。"""\n'
        '    assert slugify("Hello World") == "hello-world"\n'
        '\n'
        '\n'
        'def test_slugify_special_chars() -> None:\n'
        '    """移除特殊字元。"""\n'
        '    assert slugify("Hello, World!") == "hello-world"\n'
        '\n'
        '\n'
        'def test_slugify_multiple_spaces() -> None:\n'
        '    """多重空格應只產生一個連字號。"""\n'
        '    assert slugify("hello   world") == "hello-world"\n'
        '\n'
        '\n'
        'def test_slugify_leading_trailing() -> None:\n'
        '    """前後空白應被移除。"""\n'
        '    assert slugify("  hello world  ") == "hello-world"\n'
        '\n'
        '\n'
        'def test_slugify_empty() -> None:\n'
        '    """空字串應回傳空字串。"""\n'
        '    assert slugify("") == ""\n',
        encoding='utf-8',
    )


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估 slugify 實作結果。"""
    details: dict[str, Any] = {}

    # 檢查 slugify 函數是否存在
    source = sandbox / 'string_utils.py'
    if not source.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'string_utils.py 不存在'},
        )

    content = source.read_text(encoding='utf-8')
    details['has_slugify'] = 'def slugify' in content

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    # 評分：有 slugify 函數 0.3 + 測試全過 0.7
    score = 0.0
    if details['has_slugify']:
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

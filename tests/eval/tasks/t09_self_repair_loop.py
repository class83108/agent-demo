"""T9 — Self-Repair Loop (Special)。

data_parser.py 有兩個相關 bug：
1. 明顯的：沒有 strip() 導致空白字元問題
2. 隱藏的：沒處理空行，修完第一個後才會暴露

測試 Agent 的 iterative debugging 能力 — 修完跑測試、看到新錯誤、再修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T9 - Self-Repair Loop'
TASK_LEVEL: str = 'special'
TASK_PROMPT: str = (
    '執行 pytest 有測試失敗。請修復程式碼讓所有測試通過。\n注意：可能有多個問題，請逐一修復並驗證。'
)


def setup(sandbox: Path) -> None:
    """建立含有兩個相關 bug 的 data_parser 專案。"""
    # data_parser.py — 兩個 bug
    (sandbox / 'data_parser.py').write_text(
        '"""CSV-like 資料解析器。"""\n'
        '\n'
        'from __future__ import annotations\n'
        '\n'
        '\n'
        'def parse_records(raw: str) -> list[dict[str, str]]:\n'
        '    """解析以換行分隔的 key=value 記錄。\n'
        '\n'
        '    每行格式: key=value\n'
        '    空行分隔不同記錄。\n'
        '\n'
        '    Args:\n'
        '        raw: 原始文字\n'
        '\n'
        '    Returns:\n'
        '        記錄列表\n'
        '    """\n'
        '    records: list[dict[str, str]] = []\n'
        '    current: dict[str, str] = {}\n'
        '\n'
        '    for line in raw.split("\\n"):\n'
        '        # BUG 1: 沒有 strip()，導致有空白的行不會被視為空行\n'
        '        # BUG 2: 沒有 skip 真正的空行，會嘗試 split("=") 然後出錯\n'
        '        parts = line.split("=")\n'
        '        if len(parts) == 2:\n'
        '            current[parts[0]] = parts[1]\n'
        '        elif current:\n'
        '            records.append(current)\n'
        '            current = {}\n'
        '\n'
        '    if current:\n'
        '        records.append(current)\n'
        '\n'
        '    return records\n'
        '\n'
        '\n'
        'def get_field(records: list[dict[str, str]], index: int, field: str) -> str | None:\n'
        '    """取得指定記錄的欄位值。"""\n'
        '    if 0 <= index < len(records):\n'
        '        return records[index].get(field)\n'
        '    return None\n',
        encoding='utf-8',
    )

    # test_data_parser.py
    (sandbox / 'test_data_parser.py').write_text(
        'from data_parser import parse_records, get_field\n'
        '\n'
        '\n'
        'def test_parse_single_record() -> None:\n'
        '    raw = "name=Alice\\nemail=alice@test.com"\n'
        '    records = parse_records(raw)\n'
        '    assert len(records) == 1\n'
        '    assert records[0]["name"] == "Alice"\n'
        '    assert records[0]["email"] == "alice@test.com"\n'
        '\n'
        '\n'
        'def test_parse_multiple_records() -> None:\n'
        '    raw = "name=Alice\\nemail=a@test.com\\n\\nname=Bob\\nemail=b@test.com"\n'
        '    records = parse_records(raw)\n'
        '    assert len(records) == 2\n'
        '    assert records[0]["name"] == "Alice"\n'
        '    assert records[1]["name"] == "Bob"\n'
        '\n'
        '\n'
        'def test_parse_with_whitespace() -> None:\n'
        '    """行尾有空白應該被忽略。"""\n'
        '    raw = "name=Alice  \\nemail=alice@test.com  "\n'
        '    records = parse_records(raw)\n'
        '    assert len(records) == 1\n'
        '    assert records[0]["name"] == "Alice"\n'
        '    assert records[0]["email"] == "alice@test.com"\n'
        '\n'
        '\n'
        'def test_parse_with_blank_lines() -> None:\n'
        '    """多個空行應被正確處理。"""\n'
        '    raw = "name=Alice\\n\\n\\nname=Bob"\n'
        '    records = parse_records(raw)\n'
        '    assert len(records) == 2\n'
        '\n'
        '\n'
        'def test_parse_empty_input() -> None:\n'
        '    records = parse_records("")\n'
        '    assert records == []\n'
        '\n'
        '\n'
        'def test_get_field() -> None:\n'
        '    records = [{"name": "Alice", "email": "a@test.com"}]\n'
        '    assert get_field(records, 0, "name") == "Alice"\n'
        '    assert get_field(records, 0, "phone") is None\n'
        '    assert get_field(records, 5, "name") is None\n',
        encoding='utf-8',
    )


def evaluate(sandbox: Path, events: list[AgentEvent]) -> EvalResult:
    """評估修復結果 — 重點在是否完成完整的 debug 迴圈。"""
    details: dict[str, Any] = {}

    source = sandbox / 'data_parser.py'
    if not source.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'data_parser.py 不存在'},
        )

    content = source.read_text(encoding='utf-8')
    details['has_strip'] = '.strip()' in content
    details['handles_empty_line'] = (
        'not line' in content
        or 'line == ""' in content
        or "line == ''" in content
        or 'continue' in content
        or 'if line' in content
    )

    # 檢查 Agent 是否跑了多次測試（debug 迴圈）
    bash_test_count = 0
    for e in events:
        if e['type'] == 'tool_call' and e['data'].get('status') == 'completed':
            if e['data'].get('name') == 'bash':
                bash_test_count += 1
    details['bash_calls'] = bash_test_count
    details['likely_ran_tests_multiple_times'] = bash_test_count >= 2

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    score = 0.0
    if details['has_strip']:
        score += 0.2
    if details['handles_empty_line']:
        score += 0.2
    if passed:
        score += 0.4
    if details['likely_ran_tests_multiple_times']:
        score += 0.2  # 流程分：有 iterative debugging

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )

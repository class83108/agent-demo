"""T4 — Add Error Handling (Medium)。

file_processor.py 的 process() 函數直接開檔讀取，
沒有處理檔案不存在、空檔案、權限不足等邊界情況。
Agent 需要讀測試了解預期行為，加入適當的錯誤處理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent
from tests.eval.framework import EvalResult, run_pytest_in_sandbox

TASK_NAME: str = 'T4 - Add Error Handling'
TASK_LEVEL: str = 'medium'
TASK_PROMPT: str = (
    '執行 pytest 會發現多個測試失敗。\n'
    'file_processor.py 缺少錯誤處理，請加入適當的防護讓所有測試通過。'
)


def setup(sandbox: Path) -> None:
    """建立缺少錯誤處理的 file_processor 專案。"""
    # file_processor.py — 沒有任何防護
    (sandbox / 'file_processor.py').write_text(
        '"""檔案處理模組。"""\n'
        '\n'
        '\n'
        'def process(path: str) -> dict[str, object]:\n'
        '    """處理指定路徑的文字檔案。\n'
        '\n'
        '    讀取檔案內容，計算行數與字數。\n'
        '\n'
        '    Args:\n'
        '        path: 檔案路徑\n'
        '\n'
        '    Returns:\n'
        '        包含 lines、words、chars 的統計字典\n'
        '    """\n'
        '    with open(path) as f:\n'
        '        content = f.read()\n'
        '    lines = content.strip().split("\\n")\n'
        '    words = content.split()\n'
        '    return {\n'
        '        "lines": len(lines),\n'
        '        "words": len(words),\n'
        '        "chars": len(content),\n'
        '    }\n',
        encoding='utf-8',
    )

    # test_file_processor.py — 包含邊界案例測試
    (sandbox / 'test_file_processor.py').write_text(
        'import pytest\n'
        '\n'
        'from file_processor import process\n'
        '\n'
        '\n'
        'def test_process_normal_file(tmp_path: object) -> None:\n'
        '    """正常檔案應回傳正確統計。"""\n'
        '    from pathlib import Path\n'
        '    p = Path(str(tmp_path)) / "test.txt"\n'
        '    p.write_text("hello world\\nfoo bar\\n")\n'
        '    result = process(str(p))\n'
        '    assert result["lines"] == 2\n'
        '    assert result["words"] == 4\n'
        '\n'
        '\n'
        'def test_process_nonexistent_file() -> None:\n'
        '    """不存在的檔案應拋出 FileNotFoundError。"""\n'
        '    with pytest.raises(FileNotFoundError):\n'
        '        process("/nonexistent/file.txt")\n'
        '\n'
        '\n'
        'def test_process_empty_file(tmp_path: object) -> None:\n'
        '    """空檔案應回傳全零統計。"""\n'
        '    from pathlib import Path\n'
        '    p = Path(str(tmp_path)) / "empty.txt"\n'
        '    p.write_text("")\n'
        '    result = process(str(p))\n'
        '    assert result["lines"] == 0\n'
        '    assert result["words"] == 0\n'
        '    assert result["chars"] == 0\n'
        '\n'
        '\n'
        'def test_process_invalid_path_type() -> None:\n'
        '    """非字串路徑應拋出 TypeError。"""\n'
        '    with pytest.raises(TypeError):\n'
        '        process(123)  # type: ignore[arg-type]\n',
        encoding='utf-8',
    )


def evaluate(sandbox: Path, events: list[AgentEvent]) -> EvalResult:
    """評估錯誤處理實作結果。"""
    details: dict[str, Any] = {}

    source = sandbox / 'file_processor.py'
    if not source.exists():
        return EvalResult(
            task_name=TASK_NAME,
            task_level=TASK_LEVEL,
            passed=False,
            score=0.0,
            details={'error': 'file_processor.py 不存在'},
        )

    content = source.read_text(encoding='utf-8')
    # 檢查是否有基本的防護邏輯
    details['has_type_check'] = 'isinstance' in content or 'TypeError' in content
    details['has_empty_handling'] = 'len(' in content or '== ""' in content or "== ''" in content

    # 執行 pytest 驗證
    passed, output = run_pytest_in_sandbox(sandbox)
    details['pytest_passed'] = passed
    details['pytest_output'] = output[:1000]

    score = 1.0 if passed else 0.0

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=score,
        details=details,
    )

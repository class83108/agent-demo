"""全域測試設定。"""

from __future__ import annotations

import pytest
from dotenv import load_dotenv

# 載入 .env，確保測試時也能讀取 API 金鑰等環境變數
load_dotenv()


def pytest_addoption(parser: pytest.Parser) -> None:
    """新增自訂命令列參數。"""
    parser.addoption(
        '--run-smoke',
        action='store_true',
        default=False,
        help='執行 smoke test（會呼叫真實 API）',
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """根據命令列參數決定是否跳過 smoke test。"""
    if config.getoption('--run-smoke'):
        return

    skip_smoke = pytest.mark.skip(reason='需要加 --run-smoke 才會執行')
    for item in items:
        if 'smoke' in item.keywords:
            item.add_marker(skip_smoke)

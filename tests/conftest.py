"""Pytest 共用 fixtures。"""

import pytest


@pytest.fixture
def sample_message() -> str:
    """範例訊息 fixture。"""
    return 'Hello, Agent!'

"""Think 工具模組。

提供無副作用的思考記錄功能，讓 Agent 明確記錄推理過程。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def think_handler(thought: str) -> dict[str, Any]:
    """記錄 Agent 的思考內容。

    此工具不會產生任何副作用，僅將思考內容記錄在對話歷史中，
    幫助 Agent 在複雜任務中組織推理步驟。

    Args:
        thought: Agent 的思考內容

    Returns:
        包含思考確認的結構化結果
    """
    if not thought or not thought.strip():
        return {'thought': '', 'status': 'empty'}

    logger.debug('Agent 思考', extra={'thought_length': len(thought)})
    return {'thought': thought, 'status': 'recorded'}

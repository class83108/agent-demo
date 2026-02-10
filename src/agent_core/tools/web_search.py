"""Web Search 工具模組。

使用 Tavily API 進行網路搜尋，回傳結構化的搜尋結果。
需要設定 TAVILY_API_KEY 環境變數。
"""

from __future__ import annotations

import logging
from typing import Any, cast

from tavily import AsyncTavilyClient  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# 預設搜尋參數
DEFAULT_MAX_RESULTS: int = 5


async def web_search_handler(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    search_depth: str = 'basic',
    topic: str = 'general',
    api_key: str = '',
) -> dict[str, Any]:
    """執行網路搜尋並回傳結構化結果。

    Args:
        query: 搜尋查詢字串
        max_results: 最大結果數量（預設 5）
        search_depth: 搜尋深度（basic/advanced，預設 basic）
        topic: 搜尋主題（general/news/finance，預設 general）
        api_key: Tavily API key

    Returns:
        包含搜尋結果的結構化資料
    """
    if not query or not query.strip():
        return {'error': '搜尋查詢不能為空'}

    if not api_key:
        return {'error': '未設定 TAVILY_API_KEY，無法執行搜尋'}

    logger.info('執行網路搜尋', extra={'query': query, 'max_results': max_results})

    try:
        client = AsyncTavilyClient(api_key=api_key)
        # Tavily SDK 無型別 stub，cast 為 dict[str, Any]（反序列化邊界）
        response = cast(
            dict[str, Any],
            await client.search(  # type: ignore[reportUnknownMemberType]
                query=query,
                max_results=max_results,
                search_depth=search_depth,  # type: ignore[arg-type]
                topic=topic,  # type: ignore[arg-type]
                include_answer='basic',
            ),
        )

        # 整理搜尋結果
        raw_results = cast(list[dict[str, Any]], response.get('results', []))
        results: list[dict[str, str]] = []
        for item in raw_results:
            results.append(
                {
                    'title': str(item.get('title', '')),
                    'url': str(item.get('url', '')),
                    'content': str(item.get('content', '')),
                }
            )

        return {
            'query': query,
            'answer': str(response.get('answer', '')),
            'results': results,
            'result_count': len(results),
        }

    except Exception as e:
        error_type = type(e).__name__
        return {'error': f'{error_type}: {e}', 'query': query}

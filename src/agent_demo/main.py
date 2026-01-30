"""FastAPI 應用程序入口。

提供聊天 API 端點，支援 SSE 串流回應與會話管理。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_demo.agent import Agent, AgentConfig
from agent_demo.session import SessionManager
from agent_demo.tools.file_read import detect_language, read_file_handler
from agent_demo.tools.registry import ToolRegistry
from agent_demo.tools.setup import create_default_registry

# 在匯入 Anthropic client 之前加載 .env
load_dotenv()

logger = logging.getLogger(__name__)

# --- 配置 ---
REDIS_URL = 'redis://localhost:6381'
STATIC_DIR = 'static'
SANDBOX_DIR = 'workspace/sandbox'
IS_PRODUCTION = os.environ.get('ENV') == 'production'

# --- 全局單例 ---
session_manager = SessionManager(redis_url=REDIS_URL)
tool_registry: ToolRegistry | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """應用程序生命週期管理。"""
    global tool_registry

    logger.info('應用程序啟動')

    # 啟動時建立一次工具註冊表
    sandbox_root = Path(SANDBOX_DIR)
    tool_registry = create_default_registry(sandbox_root)

    yield

    await session_manager.close()
    logger.info('應用程序關閉')


app = FastAPI(title='Agent Chat API', lifespan=lifespan)


# --- 請求模型 ---
class ChatRequest(BaseModel):
    """聊天請求本體。"""

    message: str


# --- 生成會話 ID ---
def _get_or_create_session_id(session_id: str | None) -> tuple[str, bool]:
    """讀取或生成會話 ID。

    Args:
        session_id: Cookie 中的會話 ID

    Returns:
        會話 ID 與是否新建的旗標
    """
    if session_id:
        return session_id, False
    new_id = uuid.uuid4().hex
    logger.debug('生成新會話', extra={'session_id': new_id})
    return new_id, True


# --- SSE 事件格式化 ---
def _sse_event(event: str, data: Any) -> str:
    """格式化 SSE 事件。

    Args:
        event: 事件類型
        data: 事件數據（會自動 JSON 序列化）

    Returns:
        SSE 格式的字串
    """
    # 用 JSON 編碼確保換行符等特殊字元被正確傳輸
    encoded_data = json.dumps(data, ensure_ascii=False)
    return f'event: {event}\ndata: {encoded_data}\n\n'


# --- 串流生成器 ---
async def _stream_chat(
    message: str,
    session_id: str,
) -> AsyncIterator[str]:
    """從 Agent 串流回應並格式化為 SSE 事件。

    Args:
        message: 使用者訊息
        session_id: 會話識別符

    Yields:
        格式化的 SSE 事件字串
    """
    # 從 Redis 讀取歷史
    conversation = await session_manager.load(session_id)

    # 建立 Agent（使用全局工具註冊表，帶入歷史）
    agent = Agent(config=AgentConfig(), client=None, tool_registry=tool_registry)
    agent.conversation = list(conversation)

    try:
        async for token in agent.stream_message(message):
            yield _sse_event('token', token)

        # 串流完成，儲存更新後的歷史
        await session_manager.save(session_id, agent.conversation)
        yield _sse_event('done', '')

    except (ValueError, ConnectionError, PermissionError, TimeoutError, RuntimeError) as e:
        # 錯誤時傳出 SSE error 事件
        error_data = {'type': type(e).__name__, 'message': str(e)}
        yield _sse_event('error', error_data)


# --- API 路由 ---
@app.post('/api/chat/stream')
async def chat_stream(
    request: Request,
    session_id: str | None = Cookie(default=None),
) -> StreamingResponse:
    """SSE 串流聊天端點。

    Args:
        request: HTTP 請求
        session_id: 會話 Cookie

    Returns:
        SSE 串流回應
    """
    body: dict[str, Any] = await request.json()
    chat_req = ChatRequest(**body)

    sid, _ = _get_or_create_session_id(session_id)

    response = StreamingResponse(
        _stream_chat(chat_req.message, sid),
        media_type='text/event-stream',
    )

    # 設定 Cookie（每次都設定，確保過期時間更新）
    response.set_cookie(
        key='session_id',
        value=sid,
        path='/',  # 明確指定根路徑
        httponly=True,
        samesite='lax',
        secure=IS_PRODUCTION,
        max_age=86400,  # 24 小時，與 Redis SESSION_TTL 一致
    )

    return response


@app.get('/api/chat/history')
async def chat_history(
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """取得會話歷史端點。

    Args:
        session_id: 會話 Cookie

    Returns:
        對話歷史列表
    """
    if not session_id:
        return JSONResponse({'messages': []})

    conversation = await session_manager.load(session_id)

    # 將 MessageParam 轉換為前端友善的格式
    messages: list[dict[str, str]] = []
    for msg in conversation:
        role = msg.get('role', '')
        content = msg.get('content', '')

        if isinstance(content, str):
            # content 是字串，直接使用
            messages.append({'role': role, 'content': content})
        elif isinstance(content, list):
            # content 是 list（包含 tool_use 等），提取 text 部分
            text_parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    if isinstance(text, str):
                        text_parts.append(text)

            if text_parts:
                messages.append({'role': role, 'content': ''.join(text_parts)})

    logger.debug('取得會話歷史', extra={'session_id': session_id, 'messages': len(messages)})
    return JSONResponse({'messages': messages})


@app.post('/api/chat/reset')
async def chat_reset(
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """清除會話歷史端點。

    Args:
        session_id: 會話 Cookie

    Returns:
        清除結果
    """
    if not session_id:
        return JSONResponse({'status': 'ok', 'message': '無會話需清除'})

    await session_manager.reset(session_id)
    logger.info('會話歷史已清除', extra={'session_id': session_id})
    return JSONResponse({'status': 'ok', 'message': '歷史已清除'})


@app.get('/health')
async def health() -> JSONResponse:
    """健康檢查端點。"""
    return JSONResponse({'status': 'healthy'})


# --- 檔案瀏覽 API ---
def _build_tree(current_path: Path, sandbox_root: Path) -> list[dict[str, Any]]:
    """遞迴建立目錄樹結構。

    Args:
        current_path: 當前遍歷的路徑
        sandbox_root: sandbox 根目錄

    Returns:
        目錄樹結構列表
    """
    items: list[dict[str, Any]] = []

    # 跳過的目錄名稱
    skip_dirs = {'__pycache__', 'node_modules', '.git', '.venv', 'venv'}

    try:
        for entry in sorted(current_path.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
            # 跳過隱藏檔案和特定目錄
            if entry.name.startswith('.') or entry.name in skip_dirs:
                continue

            relative_path = str(entry.relative_to(sandbox_root))

            if entry.is_dir():
                items.append(
                    {
                        'name': entry.name,
                        'type': 'directory',
                        'path': relative_path,
                        'children': _build_tree(entry, sandbox_root),
                    }
                )
            else:
                items.append(
                    {
                        'name': entry.name,
                        'type': 'file',
                        'path': relative_path,
                        'language': detect_language(entry),
                    }
                )
    except PermissionError:
        logger.warning('無權限存取目錄', extra={'path': str(current_path)})

    return items


@app.get('/api/files/tree')
async def get_file_tree() -> JSONResponse:
    """取得 sandbox 目錄結構。

    Returns:
        包含目錄樹的 JSON 回應
    """
    sandbox_path = Path(SANDBOX_DIR).resolve()

    if not sandbox_path.exists():
        logger.warning('Sandbox 目錄不存在', extra={'path': SANDBOX_DIR})
        return JSONResponse({'root': SANDBOX_DIR, 'tree': []})

    tree = _build_tree(sandbox_path, sandbox_path)
    return JSONResponse({'root': SANDBOX_DIR, 'tree': tree})


@app.get('/api/files/content')
async def get_file_content(path: str) -> JSONResponse:
    """讀取檔案內容。

    Args:
        path: 檔案路徑（相對於 sandbox）

    Returns:
        包含檔案內容的 JSON 回應
    """
    sandbox_root = Path(SANDBOX_DIR).resolve()

    try:
        result = read_file_handler(path, sandbox_root)
        return JSONResponse(result)
    except FileNotFoundError as e:
        return JSONResponse({'error': str(e)}, status_code=404)
    except PermissionError as e:
        return JSONResponse({'error': str(e)}, status_code=403)
    except ValueError as e:
        return JSONResponse({'error': str(e)}, status_code=400)


@app.get('/api/files/modified')
async def get_modified_files(
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """取得會話中已修改的檔案列表。

    Args:
        session_id: 會話 Cookie

    Returns:
        已修改檔案列表
    """
    # 目前尚未實作 edit_file 工具，暫時回傳空列表
    # 待 edit_file 實作後，從 Redis 讀取 session:{id}:modified_files
    if not session_id:
        return JSONResponse({'modified_files': []})

    return JSONResponse({'modified_files': []})


# --- 伺務前端靜態文件 ---
app.mount('/', StaticFiles(directory=STATIC_DIR, html=True), name='static')

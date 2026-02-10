"""T11 — Web Crawler (Special)。

Agent 需要透過 web_fetch 工具爬取本地 HTTP 伺服器上的公司內部網路，
找出分散在不同頁面中的三段存取碼並組合出完整答案。

頁面結構：
  /           → 首頁，連結到 /engineering, /hr, /about
  /engineering → 存取碼第 1 部分 (ALPHA) + 連結到 /projects
  /hr          → 存取碼第 2 部分 (BRAVO)
  /projects    → 存取碼第 3 部分 (CHARLIE) + 連結到 /docs
  /about       → 干擾頁（無線索）
  /docs        → 干擾頁（無線索）

最佳路徑：4 次 fetch（首頁 + engineering + hr + projects）
"""

from __future__ import annotations

import http.server
import logging
import threading
from pathlib import Path
from typing import Any

from agent_core.types import AgentEvent, MessageParam
from tests.eval.framework import EvalResult

logger = logging.getLogger(__name__)

TASK_NAME: str = 'T11 - Web Crawler'
TASK_LEVEL: str = 'special'
TASK_PROMPT: str = ''  # 在 setup() 中動態設定（需 global 重新賦值）

TOOLS_CONFIG: dict[str, Any] = {
    'web_fetch_allowed_hosts': ['127.0.0.1'],
}

# 存取碼片段
CODE_PARTS: list[str] = ['ALPHA', 'BRAVO', 'CHARLIE']

# HTTP 伺服器參考（用於 evaluate 時清理）
_server: http.server.HTTPServer | None = None

# --- 頁面內容 ---

_PAGES: dict[str, str] = {
    '/': """\
<html>
<head><title>Acme Corp 內部網路</title></head>
<body>
<h1>歡迎來到 Acme Corp 內部系統</h1>
<p>請透過以下連結存取各部門頁面：</p>
<ul>
  <li><a href="/engineering">工程部</a></li>
  <li><a href="/hr">人力資源部</a></li>
  <li><a href="/about">關於我們</a></li>
</ul>
<p>提示：完整的系統存取碼分散在各部門頁面中，請逐一查閱。</p>
</body>
</html>""",
    '/engineering': """\
<html>
<head><title>工程部</title></head>
<body>
<h1>工程部</h1>
<p>負責產品開發與技術架構。</p>
<p>系統存取碼第一部分：<strong>ALPHA</strong></p>
<p>相關連結：<a href="/projects">查看專案列表</a></p>
</body>
</html>""",
    '/hr': """\
<html>
<head><title>人力資源部</title></head>
<body>
<h1>人力資源部</h1>
<p>負責招聘、培訓與員工關係。</p>
<p>系統存取碼第二部分：<strong>BRAVO</strong></p>
</body>
</html>""",
    '/projects': """\
<html>
<head><title>專案列表</title></head>
<body>
<h1>專案列表</h1>
<ul>
  <li>Project Phoenix - 下一代平台</li>
  <li>Project Atlas - 資料分析引擎</li>
</ul>
<p>系統存取碼第三部分：<strong>CHARLIE</strong></p>
<p>詳細文件：<a href="/docs">技術文件</a></p>
</body>
</html>""",
    '/about': """\
<html>
<head><title>關於 Acme Corp</title></head>
<body>
<h1>關於 Acme Corp</h1>
<p>Acme Corp 成立於 2020 年，專注於企業級軟體解決方案。</p>
<p>總部位於台北市。</p>
</body>
</html>""",
    '/docs': """\
<html>
<head><title>技術文件</title></head>
<body>
<h1>技術文件</h1>
<p>API 文件與系統架構說明正在建設中。</p>
<p>如有需求請聯繫工程部。</p>
</body>
</html>""",
}


class _IntranetHandler(http.server.BaseHTTPRequestHandler):
    """模擬公司內部網路的 HTTP handler。"""

    def do_GET(self) -> None:
        page = _PAGES.get(self.path)
        if page:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(page.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<html><body>404 Not Found</body></html>')

    def log_message(self, format: str, *args: Any) -> None:
        """抑制請求日誌。"""


def setup(sandbox: Path) -> None:
    """啟動本地 HTTP 伺服器並設定任務提示。"""
    global TASK_PROMPT, _server

    # 啟動 HTTP 伺服器（port 0 = OS 自動分配）
    server = http.server.HTTPServer(('127.0.0.1', 0), _IntranetHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _server = server

    # 記錄 port 到檔案（供除錯用）
    (sandbox / '.server_port').write_text(str(port), encoding='utf-8')

    # 動態設定任務提示（全域常數在 setup 時賦值，屬反序列化邊界）
    TASK_PROMPT = (  # type: ignore[reportConstantRedefinition]
        f'一個公司內部網路正在 http://127.0.0.1:{port} 上運行。\n'
        '請使用 web_fetch 工具探索這個內部網路，'
        '找出分散在不同頁面中的完整系統存取碼（由三個部分組成）。\n'
        '請回報完整的三段存取碼。'
    )

    logger.info('T11 HTTP 伺服器已啟動', extra={'port': port})


def evaluate(
    sandbox: Path,
    events: list[AgentEvent],
    conversation: list[MessageParam],
) -> EvalResult:
    """評估 Agent 的爬蟲結果。"""
    global _server

    details: dict[str, Any] = {}

    # 收集 agent 最終回覆文字
    final_text = ''
    for event in events:
        if event['type'] == 'text':
            final_text += event.get('data', {}).get('text', '')

    # 也從 tool_result 收集（agent 可能在工具結果中提到）
    # 但主要看最終文字回覆
    details['final_text_length'] = len(final_text)

    # --- 正確性評分（0.60）：找到存取碼片段 ---
    found_parts: list[str] = []
    for part in CODE_PARTS:
        if part in final_text.upper():
            found_parts.append(part)
    details['found_parts'] = found_parts
    details['found_count'] = len(found_parts)

    correctness_score = len(found_parts) * 0.20  # 每個 0.20，共 0.60

    # --- 工具使用評分（0.20）：實際使用 web_fetch ---
    web_fetch_calls = [
        e
        for e in events
        if e['type'] == 'tool_call'
        and e['data'].get('name') == 'web_fetch'
        and e['data'].get('status') == 'completed'
    ]
    web_fetch_count = len(web_fetch_calls)
    details['web_fetch_count'] = web_fetch_count

    tool_usage_score = 0.20 if web_fetch_count > 0 else 0.0

    # --- 效率評分（0.20）：fetch 次數越少越好 ---
    if web_fetch_count == 0:
        efficiency_score = 0.0
    elif web_fetch_count <= 5:
        efficiency_score = 0.20
    elif web_fetch_count <= 8:
        efficiency_score = 0.15
    elif web_fetch_count <= 12:
        efficiency_score = 0.10
    else:
        efficiency_score = 0.05
    details['efficiency_score'] = efficiency_score

    # 總分
    score = correctness_score + tool_usage_score + efficiency_score
    passed = len(found_parts) == len(CODE_PARTS) and web_fetch_count > 0

    details['correctness_score'] = correctness_score
    details['tool_usage_score'] = tool_usage_score

    # 清理伺服器
    if _server:
        _server.shutdown()
        _server = None

    return EvalResult(
        task_name=TASK_NAME,
        task_level=TASK_LEVEL,
        passed=passed,
        score=round(score, 2),
        details=details,
    )

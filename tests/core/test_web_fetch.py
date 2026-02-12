"""Web Fetch Tool 測試模組。

涵蓋：
- URL 驗證（scheme / 封鎖 IP / allowed_hosts 覆蓋）
- HTML 提取（bs4 解析 / 連結提取 / script 移除）
- 整合測試（本地 HTTP 伺服器）
"""

from __future__ import annotations

import http.server
import threading
from typing import Any

import allure
import pytest

from agent_core.tools.web_fetch import extract_text, validate_url, web_fetch_handler

# =============================================================================
# Rule: URL 驗證應確保安全性
# =============================================================================


@allure.feature('Web Fetch Tool')
@allure.story('URL 驗證應確保安全性')
class TestValidateUrl:
    """validate_url 單元測試。"""

    @allure.title('合法的 http/https URL 應通過')
    def test_valid_http_url(self) -> None:
        assert validate_url('https://example.com') == 'https://example.com'
        assert validate_url('http://example.com/path') == 'http://example.com/path'

    @allure.title('file:// scheme 應被拒絕')
    def test_file_scheme_rejected(self) -> None:
        with pytest.raises(ValueError, match='不支援的 URL scheme'):
            validate_url('file:///etc/passwd')

    @allure.title('ftp:// scheme 應被拒絕')
    def test_ftp_scheme_rejected(self) -> None:
        with pytest.raises(ValueError, match='不支援的 URL scheme'):
            validate_url('ftp://example.com/file')

    @allure.title('localhost 預設應被封鎖')
    def test_localhost_blocked(self) -> None:
        with pytest.raises(ValueError, match='被封鎖'):
            validate_url('http://localhost:8080')

    @allure.title('127.0.0.1 預設應被封鎖')
    def test_loopback_blocked(self) -> None:
        with pytest.raises(ValueError, match='被封鎖'):
            validate_url('http://127.0.0.1:3000')

    @allure.title('AWS metadata IP 應被封鎖')
    def test_aws_metadata_blocked(self) -> None:
        with pytest.raises(ValueError, match='被封鎖'):
            validate_url('http://169.254.169.254/latest/meta-data/')

    @allure.title('私有 IP 應被封鎖')
    def test_private_ip_blocked(self) -> None:
        with pytest.raises(ValueError, match='私有 IP'):
            validate_url('http://192.168.1.1')

    @allure.title('allowed_hosts 可覆蓋封鎖')
    def test_allowed_hosts_override(self) -> None:
        result = validate_url('http://127.0.0.1:8080', allowed_hosts=['127.0.0.1'])
        assert result == 'http://127.0.0.1:8080'

    @allure.title('含帳密的 URL 應被拒絕')
    def test_credentials_rejected(self) -> None:
        with pytest.raises(ValueError, match='帳號密碼'):
            validate_url('http://user:pass@example.com')

    @allure.title('空主機名稱應被拒絕')
    def test_empty_hostname(self) -> None:
        with pytest.raises(ValueError, match='缺少主機'):
            validate_url('http://')


# =============================================================================
# Rule: HTML 提取應正確轉換內容
# =============================================================================


@allure.feature('Web Fetch Tool')
@allure.story('HTML 提取應正確轉換內容')
class TestExtractText:
    """extract_text 單元測試。"""

    @allure.title('基本段落應正確提取')
    def test_basic_paragraph(self) -> None:
        html = '<html><body><p>Hello World</p></body></html>'
        text, _, _ = extract_text(html)
        assert 'Hello World' in text

    @allure.title('頁面標題應被提取')
    def test_title_extraction(self) -> None:
        html = '<html><head><title>我的頁面</title></head><body>內容</body></html>'
        _, title, _ = extract_text(html)
        assert title == '我的頁面'

    @allure.title('script 標籤內容應被移除')
    def test_script_removed(self) -> None:
        html = '<p>文字</p><script>alert("xss")</script><p>更多文字</p>'
        text, _, _ = extract_text(html)
        assert 'alert' not in text
        assert '文字' in text
        assert '更多文字' in text

    @allure.title('style 標籤內容應被移除')
    def test_style_removed(self) -> None:
        html = '<style>.red { color: red; }</style><p>內容</p>'
        text, _, _ = extract_text(html)
        assert 'color' not in text
        assert '內容' in text

    @allure.title('連結應被正確提取')
    def test_links_extracted(self) -> None:
        html = '<a href="/about">關於我們</a><a href="https://example.com">範例</a>'
        _, _, links = extract_text(html, base_url='http://localhost:8080')
        assert len(links) == 2
        assert links[0]['text'] == '關於我們'
        assert links[0]['href'] == 'http://localhost:8080/about'
        assert links[1]['href'] == 'https://example.com'

    @allure.title('相對連結應用 base_url 解析')
    def test_relative_links_resolved(self) -> None:
        html = '<a href="/page2">下一頁</a>'
        _, _, links = extract_text(html, base_url='http://localhost:3000/page1')
        assert links[0]['href'] == 'http://localhost:3000/page2'

    @allure.title('嵌套結構應正確處理')
    def test_nested_structure(self) -> None:
        html = """
        <div>
            <h1>標題</h1>
            <div>
                <p>段落一</p>
                <ul>
                    <li>項目 A</li>
                    <li>項目 B</li>
                </ul>
            </div>
        </div>
        """
        text, _, _ = extract_text(html)
        assert '標題' in text
        assert '段落一' in text
        assert '項目 A' in text
        assert '項目 B' in text

    @allure.title('空 HTML 應回傳空結果')
    def test_empty_html(self) -> None:
        text, title, links = extract_text('')
        assert text == ''
        assert title == ''
        assert links == []


# =============================================================================
# Rule: 整合測試（本地 HTTP 伺服器）
# =============================================================================


class _SimpleHandler(http.server.BaseHTTPRequestHandler):
    """測試用 HTTP handler。"""

    def do_GET(self) -> None:
        if self.path == '/':
            body = '<html><head><title>首頁</title></head><body>'
            body += '<h1>歡迎</h1><a href="/page2">第二頁</a>'
            body += '</body></html>'
            self._respond(200, body)
        elif self.path == '/page2':
            self._respond(200, '<html><body><p>第二頁內容</p></body></html>')
        elif self.path == '/plain':
            self._respond(200, '純文字內容', content_type='text/plain')
        elif self.path == '/large':
            self._respond(200, 'x' * 2_000_000)
        else:
            self._respond(404, '<html><body>Not Found</body></html>')

    def _respond(self, code: int, body: str, content_type: str = 'text/html') -> None:
        self.send_response(code)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, format: str, *args: Any) -> None:
        """抑制日誌輸出。"""


@pytest.fixture(scope='module')
def local_server() -> Any:
    """啟動本地 HTTP 伺服器。"""
    server = http.server.HTTPServer(('127.0.0.1', 0), _SimpleHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@allure.feature('Web Fetch Tool')
@allure.story('應能擷取本地伺服���的網頁內容')
class TestWebFetchIntegration:
    """web_fetch_handler 整合測試。"""

    @allure.title('成功擷取 HTML 頁面')
    async def test_fetch_html_page(self, local_server: int) -> None:
        result = await web_fetch_handler(
            url=f'http://127.0.0.1:{local_server}/',
            allowed_hosts=['127.0.0.1'],
        )
        assert result['status_code'] == 200
        assert result['title'] == '首頁'
        assert '歡迎' in result['content_text']
        assert len(result['links']) >= 1
        assert result['links'][0]['text'] == '第二頁'

    @allure.title('擷取純文字回應')
    async def test_fetch_plain_text(self, local_server: int) -> None:
        result = await web_fetch_handler(
            url=f'http://127.0.0.1:{local_server}/plain',
            allowed_hosts=['127.0.0.1'],
        )
        assert result['status_code'] == 200
        assert result['content_text'] == '純文字內容'
        assert result['links'] == []

    @allure.title('404 頁面應回傳狀態碼')
    async def test_fetch_404(self, local_server: int) -> None:
        result = await web_fetch_handler(
            url=f'http://127.0.0.1:{local_server}/nonexistent',
            allowed_hosts=['127.0.0.1'],
        )
        assert result['status_code'] == 404

    @allure.title('超過大小限制應回傳錯誤')
    async def test_fetch_too_large(self, local_server: int) -> None:
        result = await web_fetch_handler(
            url=f'http://127.0.0.1:{local_server}/large',
            max_size=1_000_000,
            allowed_hosts=['127.0.0.1'],
        )
        assert 'error' in result
        assert '過大' in result['error']

    @allure.title('未允許的 localhost 應回傳錯誤')
    async def test_fetch_localhost_blocked(self, local_server: int) -> None:
        result = await web_fetch_handler(
            url=f'http://127.0.0.1:{local_server}/',
        )
        assert 'error' in result
        assert '封鎖' in result['error']

    @allure.title('連線失敗應回傳錯誤')
    async def test_fetch_connection_error(self) -> None:
        result = await web_fetch_handler(
            url='http://192.0.2.1:1',  # TEST-NET，不會有服務
            timeout_seconds=2,
            allowed_hosts=['192.0.2.1'],
        )
        assert 'error' in result

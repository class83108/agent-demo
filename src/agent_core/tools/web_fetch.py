"""Web Fetch 工具模組。

使用 BeautifulSoup 將 HTML 轉換為可讀文字，
支援連結提取，讓 Agent 能跟隨連結探索網站。
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 安全限制常數
DEFAULT_TIMEOUT_SECONDS: int = 30
MAX_RESPONSE_SIZE: int = 1_000_000  # 1MB

# 預設封鎖的主機名稱
BLOCKED_HOSTS: set[str] = {
    'localhost',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
    '169.254.169.254',  # AWS metadata
    'metadata.google.internal',  # GCP metadata
}


def _is_private_ip(hostname: str) -> bool:
    """檢查是否為私有 IP 位址。"""
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def validate_url(
    url: str,
    allowed_hosts: list[str] | None = None,
) -> str:
    """驗證 URL 安全性。

    Args:
        url: 要驗證的 URL
        allowed_hosts: 允許的主機清單（覆蓋預設封鎖）

    Returns:
        驗證通過的 URL

    Raises:
        ValueError: URL 不安全或格式錯誤
    """
    parsed = urlparse(url)

    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'不支援的 URL scheme: {parsed.scheme}，僅允許 http/https')

    if parsed.username or parsed.password:
        raise ValueError('不允許 URL 中包含帳號密碼')

    hostname = parsed.hostname or ''
    if not hostname:
        raise ValueError('URL 缺少主機名稱')

    allowed: set[str] = set(allowed_hosts) if allowed_hosts else set()

    if hostname in BLOCKED_HOSTS and hostname not in allowed:
        raise ValueError(f'主機 {hostname} 被封鎖（安全限制）')

    if _is_private_ip(hostname) and hostname not in allowed:
        raise ValueError(f'不允許存取私有 IP 位址: {hostname}')

    return url


def extract_text(html: str, base_url: str = '') -> tuple[str, str, list[dict[str, str]]]:
    """將 HTML 轉換為可讀純文字，同時提取連結。

    Args:
        html: HTML 原始碼
        base_url: 基礎 URL，用於解析相對連結

    Returns:
        (純文字內容, 頁面標題, 連結清單) 的 tuple
        連結清單格式: [{'text': str, 'href': str}, ...]
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 提取標題
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else ''

    # 移除不需要的標籤
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    # 提取連結（在轉換為純文字之前）
    links: list[dict[str, str]] = []
    for a_tag in soup.find_all('a', href=True):
        href = str(a_tag['href'])
        if base_url and not urlparse(href).scheme:
            href = urljoin(base_url, href)
        link_text = a_tag.get_text(strip=True)
        if link_text and href:
            links.append({'text': link_text, 'href': href})

    # 提取純文字（separator 確保 block 元素間有換行）
    text = soup.get_text(separator='\n', strip=True)

    # 合併連續空行
    lines = text.split('\n')
    result_lines: list[str] = []
    prev_empty = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not prev_empty:
                result_lines.append('')
            prev_empty = True
        else:
            result_lines.append(stripped)
            prev_empty = False

    clean_text = '\n'.join(result_lines).strip()
    return clean_text, title, links


async def web_fetch_handler(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_size: int = MAX_RESPONSE_SIZE,
    allowed_hosts: list[str] | None = None,
) -> dict[str, Any]:
    """擷取網頁內容並轉換為純文字。

    Args:
        url: 要擷取的網頁 URL
        timeout: 超時秒數（預設 30）
        max_size: 最大回應大小（bytes，預設 1MB）
        allowed_hosts: 允許的主機清單（覆蓋預設封鎖）

    Returns:
        包含網頁內容的結構化結果
    """
    try:
        validated_url = validate_url(url, allowed_hosts)
    except ValueError as e:
        return {'error': str(e), 'url': url}

    logger.info('擷取網頁', extra={'url': validated_url})

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        ) as client:
            response = await client.get(validated_url)

            content_length = len(response.content)
            if content_length > max_size:
                return {
                    'error': f'回應過大: {content_length} bytes（上限 {max_size}）',
                    'url': validated_url,
                    'status_code': response.status_code,
                }

            content_type = response.headers.get('content-type', '')
            raw_text = response.text

            if 'text/html' in content_type or '<html' in raw_text[:500].lower():
                content_text, title, links = extract_text(raw_text, validated_url)
            else:
                content_text = raw_text
                title = ''
                links = []

            return {
                'url': validated_url,
                'status_code': response.status_code,
                'title': title,
                'content_text': content_text,
                'content_length': len(content_text),
                'links': links,
            }

    except httpx.TimeoutException:
        return {'error': f'請求超時（{timeout} 秒）', 'url': validated_url}
    except httpx.ConnectError as e:
        return {'error': f'連線失敗: {e}', 'url': validated_url}
    except httpx.HTTPError as e:
        return {'error': f'HTTP 錯誤: {e}', 'url': validated_url}

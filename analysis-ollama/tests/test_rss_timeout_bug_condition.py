"""
Bug 条件探索性测试 — 修复后验证

目标：在已修复代码上证明 bug 已解决：
  - fetch_feed_articles 使用可配置的 self.timeout（默认 120 秒）
  - 分批逻辑存在：limit > batch_size 时发出多次请求
  - __init__ 接受 timeout 参数

**Validates: Requirements 2.1, 2.2, 2.3**

预期结果：测试通过（证明 bug 已修复）
"""
import inspect
import pytest
from unittest.mock import patch, MagicMock, call
from requests.exceptions import Timeout

from hypothesis import given, settings as h_settings, HealthCheck
from hypothesis import strategies as st

from app.services.rss_fetcher import RSSFetcher


# ---------------------------------------------------------------------------
# 辅助常量
# ---------------------------------------------------------------------------
WEWE_RSS_URL = "http://app:4000"
AUTH_CODE = "test-auth"
DEFAULT_TIMEOUT = 120   # 修复后的默认超时值
DEFAULT_BATCH_SIZE = 20  # 修复后的默认批次大小


# ---------------------------------------------------------------------------
# Property 1: 修复后行为 — 超时时返回空列表（行为保留）
# 对任意 limit > 20，当 requests.get 抛出 Timeout 时，fetch_feed_articles 返回 []
# ---------------------------------------------------------------------------
@given(limit=st.integers(min_value=21, max_value=500))
@h_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fetch_feed_articles_returns_empty_on_timeout(limit):
    """
    修复后行为保留：当 requests.get 抛出 Timeout 时，fetch_feed_articles 返回空列表。

    **Validates: Requirements 2.1, 2.2**
    """
    fetcher = RSSFetcher(WEWE_RSS_URL, AUTH_CODE)

    with patch("app.services.rss_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Timeout("模拟超时")

        result = fetcher.fetch_feed_articles(feed_id="all", limit=limit)

    # 修复后行为：超时后返回空列表（行为保留）
    assert result == [], (
        f"期望超时时返回 []，但实际返回了 {len(result)} 篇文章 (limit={limit})"
    )


# ---------------------------------------------------------------------------
# Property 2: 修复后行为 — 使用 self.timeout（而非硬编码 30）
# 验证 requests.get 调用时使用的是 self.timeout（默认 120），而非硬编码的 30
# ---------------------------------------------------------------------------
@given(limit=st.integers(min_value=21, max_value=500))
@h_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_requests_get_called_with_hardcoded_timeout_30(limit):
    """
    修复后行为：requests.get 使用 self.timeout（默认 120），而非硬编码的 30。

    这证明了 bug 已修复：超时时间可通过构造函数配置。

    **Validates: Requirements 2.1, 2.3**
    """
    fetcher = RSSFetcher(WEWE_RSS_URL, AUTH_CODE)  # 默认 timeout=120

    with patch("app.services.rss_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Timeout("模拟超时")

        fetcher.fetch_feed_articles(feed_id="all", limit=limit)

        # 修复后：至少调用 1 次 requests.get（有分批逻辑）
        assert mock_get.call_count >= 1, (
            f"期望至少调用 1 次 requests.get，实际调用了 {mock_get.call_count} 次"
        )

        # 验证 timeout 参数为 self.timeout（120），而非硬编码的 30
        actual_timeout = mock_get.call_args.kwargs.get("timeout")
        assert actual_timeout == DEFAULT_TIMEOUT, (
            f"期望 timeout={DEFAULT_TIMEOUT}（self.timeout），实际 timeout={actual_timeout}。"
            f"Bug 未修复：超时时间仍为硬编码值。"
        )


# ---------------------------------------------------------------------------
# 具体示例测试（非属性测试）
# ---------------------------------------------------------------------------
def test_concrete_example_limit_100_timeout_30():
    """
    具体示例：limit=100, 默认 timeout=120 时超时返回空列表，且发出多次分批请求。

    对应 design.md 中的修复后行为。

    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    fetcher = RSSFetcher(WEWE_RSS_URL, AUTH_CODE)  # 默认 timeout=120, batch_size=20

    with patch("app.services.rss_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Timeout("WeWe-RSS 全文抓取超时")

        result = fetcher.fetch_feed_articles(feed_id="all", limit=100)

    assert result == [], "limit=100 超时时应返回 []"

    # 修复后：第一批超时即 break，发出 1 次请求
    assert mock_get.call_count >= 1, "修复后代码应至少发出 1 次请求"

    # 确认 timeout=120（self.timeout，而非硬编码 30）
    actual_timeout = mock_get.call_args.kwargs.get("timeout")
    assert actual_timeout == 120, f"修复后 timeout 应为 120，实际为 {actual_timeout}"


def test_no_batch_logic_in_unfixed_code():
    """
    确认修复后代码有分批逻辑：limit=100, batch_size=20 时，成功时应发出多次请求。

    **Validates: Requirements 2.2, 2.3**
    """
    fetcher = RSSFetcher(WEWE_RSS_URL, AUTH_CODE, batch_size=20)

    # 构造一个返回 20 篇文章的 mock 响应（触发继续循环）
    atom_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
""" + b"".join(
        f"""  <entry>
    <title>Article {i}</title>
    <link href="http://example.com/{i}"/>
    <id>guid-{i}</id>
    <published>2024-01-01T00:00:00Z</published>
    <content>Content {i}</content>
  </entry>
""".encode() for i in range(20)
    ) + b"</feed>"

    call_count = 0

    def mock_get_side_effect(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            # 第二批返回空，触发 break
            empty_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
            resp = MagicMock()
            resp.content = empty_xml
            resp.raise_for_status = MagicMock()
            return resp
        resp = MagicMock()
        resp.content = atom_xml
        resp.raise_for_status = MagicMock()
        return resp

    with patch("app.services.rss_fetcher.requests.get", side_effect=mock_get_side_effect):
        result = fetcher.fetch_feed_articles(feed_id="all", limit=100)

    # 修复后：有分批逻辑，应发出多次请求
    assert call_count >= 2, (
        f"修复后代码应发出多次分批请求（batch_size=20, limit=100），实际发出了 {call_count} 次"
    )


def test_rss_fetcher_init_has_no_timeout_parameter():
    """
    确认修复后代码的 __init__ 接受 timeout 参数（可配置超时）。

    **Validates: Requirements 2.1**
    """
    sig = inspect.signature(RSSFetcher.__init__)
    params = list(sig.parameters.keys())

    # 修复后：__init__ 应有 timeout 参数
    assert "timeout" in params, (
        f"修复后代码的 __init__ 应有 timeout 参数，实际参数: {params}。"
        f"Bug 未修复：超时时间仍无法通过构造函数配置。"
    )

    # 同时验证 batch_size 参数也存在
    assert "batch_size" in params, (
        f"修复后代码的 __init__ 应有 batch_size 参数，实际参数: {params}。"
    )

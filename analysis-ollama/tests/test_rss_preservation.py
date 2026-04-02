"""
保留属性测试 — 修复前运行，建立基线

目标：验证以下行为在修复前后保持不变：
  1. _parse_atom_feed 正确解析 Atom XML，返回包含所有字段的字典列表
  2. trigger_update=True 时，请求 URL 包含 &update=true
  3. auth_code 非空时，请求头包含 Authorization: Bearer {auth_code}
  4. requests.get 抛出 HTTPError（404/500）时，方法返回 [] 不抛异常

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

预期结果：所有测试通过（建立基线行为）
"""
import html as html_module
import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError

from hypothesis import given, settings as h_settings, HealthCheck, assume
from hypothesis import strategies as st

from app.services.rss_fetcher import RSSFetcher


# ---------------------------------------------------------------------------
# 辅助常量与工具函数
# ---------------------------------------------------------------------------
WEWE_RSS_URL = "http://app:4000"


def build_atom_xml(entries: list[dict]) -> bytes:
    """
    构建合法的 Atom XML，entries 为包含 title/url/guid 的字典列表。
    可选字段：published, content

    注意：content 字段使用 HTML 转义存储为文本节点，
    这样 ET 的 content_node.text 才能正确返回字符串值。
    """
    entry_blocks = []
    for e in entries:
        title = html_module.escape(e.get("title", "Test Title"))
        url = e.get("url", "https://example.com/article")
        guid = html_module.escape(e.get("guid", "urn:guid:test-001"))
        published = e.get("published", "2024-01-01T00:00:00Z")
        # HTML-escape the content so it's stored as a text node (not child elements)
        raw_content = e.get("content", "Test content")
        content = html_module.escape(raw_content)

        entry_blocks.append(f"""
  <entry>
    <title>{title}</title>
    <link href="{url}" />
    <id>{guid}</id>
    <published>{published}</published>
    <content type="html">{content}</content>
  </entry>""")

    entries_xml = "".join(entry_blocks)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>{entries_xml}
</feed>"""
    return xml.encode("utf-8")


def make_mock_response(content: bytes, status_code: int = 200) -> MagicMock:
    """创建模拟的 requests.Response 对象"""
    mock_resp = MagicMock()
    mock_resp.content = content
    mock_resp.status_code = status_code
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# Hypothesis 策略
# ---------------------------------------------------------------------------

# 生成合法的 XML 文本内容（避免 XML 特殊字符破坏结构）
safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters=" -_.",
    ),
    min_size=1,
    max_size=50,
)

# 生成合法的 URL
safe_url = st.builds(
    lambda path: f"https://example.com/{path}",
    path=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
        min_size=1,
        max_size=30,
    ),
)

# 生成合法的 GUID
safe_guid = st.builds(
    lambda uid: f"urn:guid:{uid}",
    uid=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
        min_size=1,
        max_size=30,
    ),
)

# 生成单个 Atom 条目字典
atom_entry_strategy = st.fixed_dictionaries({
    "title": safe_text,
    "url": safe_url,
    "guid": safe_guid,
})

# 生成非空 auth_code 字符串（可打印 ASCII，排除空白）
auth_code_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_.",
    ),
    min_size=1,
    max_size=64,
)


# ---------------------------------------------------------------------------
# 观察 1：_parse_atom_feed 返回包含所有必需字段的字典列表
# ---------------------------------------------------------------------------

class TestParseAtomFeedPreservation:
    """验证 _parse_atom_feed 解析行为不变"""

    def test_parse_single_entry_returns_all_fields(self):
        """
        具体示例：单条 Atom 条目解析后包含所有必需字段。

        **Validates: Requirements 3.1, 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml([{
            "title": "Test Article",
            "url": "https://example.com/article-1",
            "guid": "urn:guid:article-001",
            "published": "2024-03-15T10:00:00Z",
            "content": "Article content",
        }])

        result = fetcher._parse_atom_feed(xml_content, "feed-123")

        assert len(result) == 1
        article = result[0]

        # 验证所有必需字段存在
        assert "title" in article
        assert "url" in article
        assert "guid" in article
        assert "published_at" in article
        assert "html" in article
        assert "feed_id" in article

        # 验证字段值正确
        assert article["title"] == "Test Article"
        assert article["url"] == "https://example.com/article-1"
        assert article["guid"] == "urn:guid:article-001"
        assert article["html"] == "Article content"
        assert article["feed_id"] == "feed-123"

    def test_parse_multiple_entries(self):
        """
        具体示例：多条 Atom 条目均被正确解析。

        **Validates: Requirements 3.1, 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        entries = [
            {"title": f"Article {i}", "url": f"https://example.com/{i}", "guid": f"urn:guid:{i}"}
            for i in range(5)
        ]
        xml_content = build_atom_xml(entries)

        result = fetcher._parse_atom_feed(xml_content, "feed-abc")

        assert len(result) == 5
        for i, article in enumerate(result):
            assert article["title"] == f"Article {i}"
            assert article["url"] == f"https://example.com/{i}"
            assert article["guid"] == f"urn:guid:{i}"
            assert article["feed_id"] == "feed-abc"

    def test_parse_entry_without_content_returns_empty_html(self):
        """
        边界情况：没有 content 节点时，html 字段为空字符串。

        **Validates: Requirements 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>No Content</title>
    <link href="https://example.com/no-content" />
    <id>urn:guid:no-content</id>
    <published>2024-01-01T00:00:00Z</published>
  </entry>
</feed>"""

        result = fetcher._parse_atom_feed(xml, "feed-x")

        assert len(result) == 1
        assert result[0]["html"] == ""

    def test_parse_entry_missing_required_fields_is_skipped(self):
        """
        边界情况：缺少 title/link/id 的条目被跳过。

        **Validates: Requirements 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Valid Entry</title>
    <link href="https://example.com/valid" />
    <id>urn:guid:valid</id>
  </entry>
  <entry>
    <title>Missing Link and ID</title>
  </entry>
</feed>"""

        result = fetcher._parse_atom_feed(xml, "feed-y")

        # 只有合法条目被返回
        assert len(result) == 1
        assert result[0]["title"] == "Valid Entry"

    @given(entries=st.lists(atom_entry_strategy, min_size=1, max_size=10))
    @h_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_parsed_articles_have_all_required_fields(self, entries):
        """
        属性测试：对任意合法 Atom XML 条目，解析结果始终包含所有必需字段。

        **Validates: Requirements 3.1, 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml(entries)
        feed_id = "test-feed"

        result = fetcher._parse_atom_feed(xml_content, feed_id)

        # 每个解析结果都必须包含所有必需字段
        required_fields = {"title", "url", "guid", "published_at", "html", "feed_id"}
        for article in result:
            missing = required_fields - set(article.keys())
            assert not missing, f"解析结果缺少字段: {missing}"

        # feed_id 字段值必须与传入的 feed_id 一致
        for article in result:
            assert article["feed_id"] == feed_id

        # 解析数量应与输入条目数量一致（所有条目都有必需字段）
        assert len(result) == len(entries)

    @given(entries=st.lists(atom_entry_strategy, min_size=1, max_size=5))
    @h_settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_parsed_url_matches_input(self, entries):
        """
        属性测试：解析后的 url 字段与输入 Atom XML 中的 href 属性一致。

        **Validates: Requirements 3.2**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml(entries)

        result = fetcher._parse_atom_feed(xml_content, "feed-z")

        assert len(result) == len(entries)
        for article, entry in zip(result, entries):
            assert article["url"] == entry["url"]
            assert article["title"] == entry["title"]
            assert article["guid"] == entry["guid"]


# ---------------------------------------------------------------------------
# 观察 2：trigger_update=True 时，URL 包含 &update=true
# ---------------------------------------------------------------------------

class TestTriggerUpdatePreservation:
    """验证 trigger_update 参数行为不变"""

    def test_trigger_update_true_appends_update_param(self):
        """
        具体示例：trigger_update=True 时，请求 URL 包含 &update=true。

        **Validates: Requirements 3.3**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001", trigger_update=True)

            called_url = mock_get.call_args.args[0]
            assert "&update=true" in called_url, (
                f"trigger_update=True 时 URL 应包含 &update=true，实际 URL: {called_url}"
            )

    def test_trigger_update_false_no_update_param(self):
        """
        具体示例：trigger_update=False（默认）时，URL 不包含 &update=true。

        **Validates: Requirements 3.3**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001", trigger_update=False)

            called_url = mock_get.call_args.args[0]
            assert "&update=true" not in called_url, (
                f"trigger_update=False 时 URL 不应包含 &update=true，实际 URL: {called_url}"
            )

    def test_trigger_update_default_is_false(self):
        """
        具体示例：trigger_update 默认值为 False，URL 不包含 &update=true。

        **Validates: Requirements 3.3**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            # 不传 trigger_update，使用默认值
            fetcher.fetch_feed_articles(feed_id="feed-001")

            called_url = mock_get.call_args.args[0]
            assert "&update=true" not in called_url


# ---------------------------------------------------------------------------
# 观察 3：auth_code 非空时，请求头包含 Authorization: Bearer {auth_code}
# ---------------------------------------------------------------------------

class TestAuthCodePreservation:
    """验证认证头行为不变"""

    def test_auth_code_sets_authorization_header(self):
        """
        具体示例：auth_code 非空时，请求头包含正确的 Authorization 头。

        **Validates: Requirements 3.4**
        """
        auth_code = "my-secret-token"
        fetcher = RSSFetcher(WEWE_RSS_URL, auth_code)
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001")

            called_headers = mock_get.call_args.kwargs.get("headers", {})
            assert "Authorization" in called_headers, "请求头应包含 Authorization 字段"
            assert called_headers["Authorization"] == f"Bearer {auth_code}", (
                f"Authorization 头应为 'Bearer {auth_code}'，实际为 '{called_headers['Authorization']}'"
            )

    def test_empty_auth_code_no_authorization_header(self):
        """
        具体示例：auth_code 为空字符串时，请求头不包含 Authorization 字段。

        **Validates: Requirements 3.4**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001")

            called_headers = mock_get.call_args.kwargs.get("headers", {})
            assert "Authorization" not in called_headers, (
                "auth_code 为空时，请求头不应包含 Authorization 字段"
            )

    @given(auth_code=auth_code_strategy)
    @h_settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_auth_code_always_in_header(self, auth_code):
        """
        属性测试：对任意非空 auth_code，请求头始终包含正确的 Authorization: Bearer 头。

        **Validates: Requirements 3.4**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, auth_code)
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001")

            called_headers = mock_get.call_args.kwargs.get("headers", {})
            assert "Authorization" in called_headers, (
                f"auth_code='{auth_code}' 非空时，请求头应包含 Authorization 字段"
            )
            expected = f"Bearer {auth_code}"
            assert called_headers["Authorization"] == expected, (
                f"期望 Authorization='{expected}'，实际='{called_headers['Authorization']}'"
            )

    @given(auth_code=auth_code_strategy)
    @h_settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_auth_header_format_is_bearer(self, auth_code):
        """
        属性测试：Authorization 头始终使用 Bearer 格式。

        **Validates: Requirements 3.4**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, auth_code)
        xml_content = build_atom_xml([])
        mock_resp = make_mock_response(xml_content)

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_resp

            fetcher.fetch_feed_articles(feed_id="feed-001")

            called_headers = mock_get.call_args.kwargs.get("headers", {})
            auth_value = called_headers.get("Authorization", "")
            assert auth_value.startswith("Bearer "), (
                f"Authorization 头应以 'Bearer ' 开头，实际值: '{auth_value}'"
            )
            # Bearer 后面的 token 应与 auth_code 完全一致
            token = auth_value[len("Bearer "):]
            assert token == auth_code


# ---------------------------------------------------------------------------
# 观察 4：HTTPError（404/500）时，方法返回 [] 不抛异常
# ---------------------------------------------------------------------------

class TestHTTPErrorPreservation:
    """验证 HTTP 错误处理行为不变"""

    def _make_http_error(self, status_code: int) -> HTTPError:
        """创建带有 response 属性的 HTTPError"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        error = HTTPError(f"HTTP {status_code} Error")
        error.response = mock_response
        return error

    def test_http_404_returns_empty_list(self):
        """
        具体示例：服务返回 404 时，方法返回 [] 不抛异常。

        **Validates: Requirements 3.5**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.side_effect = self._make_http_error(404)

            result = fetcher.fetch_feed_articles(feed_id="nonexistent")

        assert result == [], f"HTTP 404 时应返回 []，实际返回: {result}"

    def test_http_500_returns_empty_list(self):
        """
        具体示例：服务返回 500 时，方法返回 [] 不抛异常。

        **Validates: Requirements 3.5**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.side_effect = self._make_http_error(500)

            result = fetcher.fetch_feed_articles(feed_id="feed-001")

        assert result == [], f"HTTP 500 时应返回 []，实际返回: {result}"

    def test_http_error_does_not_raise_exception(self):
        """
        具体示例：HTTP 错误不应向调用方抛出异常。

        **Validates: Requirements 3.5**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.side_effect = self._make_http_error(503)

            # 不应抛出任何异常
            try:
                result = fetcher.fetch_feed_articles(feed_id="feed-001")
            except Exception as e:
                pytest.fail(f"HTTP 错误时不应抛出异常，但抛出了: {type(e).__name__}: {e}")

        assert result == []

    @given(status_code=st.sampled_from([400, 401, 403, 404, 429, 500, 502, 503, 504]))
    @h_settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_any_http_error_returns_empty_list(self, status_code):
        """
        属性测试：对任意 HTTP 错误状态码，方法始终返回 [] 不抛异常。

        **Validates: Requirements 3.5**
        """
        fetcher = RSSFetcher(WEWE_RSS_URL, "")

        with patch("app.services.rss_fetcher.requests.get") as mock_get:
            mock_get.side_effect = self._make_http_error(status_code)

            try:
                result = fetcher.fetch_feed_articles(feed_id="feed-001")
            except Exception as e:
                pytest.fail(
                    f"HTTP {status_code} 错误时不应抛出异常，但抛出了: {type(e).__name__}: {e}"
                )

        assert result == [], (
            f"HTTP {status_code} 错误时应返回 []，实际返回: {result}"
        )

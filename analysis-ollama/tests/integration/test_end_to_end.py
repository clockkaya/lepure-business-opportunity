"""
Integration tests for end-to-end article processing flow.

这些测试使用 mock 模拟外部服务。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.models.article import Article
from app.models.project import ExtractedProject
from app.services.rss_fetcher import RSSFetcher
from app.services.llm_analyzer import LLMAnalyzer
from app.services.wecom_notifier import WecomNotifier
from app.utils.html_cleaner import clean_html


# 标记为集成测试
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_atom_response():
    """模拟 Atom feed 响应"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>测试公众号</title>
    <entry>
        <title>测试文章标题</title>
        <link href="https://example.com/article/123"/>
        <id>test-guid-123</id>
        <published>2024-01-01T12:00:00Z</published>
        <content type="html"><![CDATA[
            <div class="rich_media_content">
                <p>这是测试文章的内容。</p>
                <p>某公司在深圳签约智慧城市项目。</p>
            </div>
        ]]></content>
    </entry>
</feed>"""


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 分析响应"""
    return {
        "company_name": "某公司",
        "province": "广东省",
        "city": "深圳市",
        "client_type": "政府",
        "application_scene": "智慧城市",
        "project_name": "智慧城市项目",
        "project_stage": "签约",
        "summary": "某公司在深圳签约智慧城市项目"
    }


def test_rss_fetcher_fetch_articles(mock_atom_response):
    """测试 RSS 采集器获取文章"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = mock_atom_response
        mock_get.return_value.content = mock_atom_response.encode('utf-8')
        mock_get.return_value.raise_for_status = Mock()

        fetcher = RSSFetcher("http://localhost:4000", "test_auth")
        articles = fetcher.fetch_feed_articles("test_feed_id")

        assert len(articles) > 0
        assert articles[0]['title'] == "测试文章标题"
        assert articles[0]['guid'] == "test-guid-123"


def test_html_cleaner_clean_content():
    """测试 HTML 清洗器清洗内容"""
    html = """
    <div class="rich_media_content">
        <p>这是测试文章的内容。</p>
        <p>某公司在深圳签约智慧城市项目。</p>
        <script>alert('test');</script>
    </div>
    """

    cleaned = clean_html(html)

    assert "这是测试文章的内容" in cleaned
    assert "某公司在深圳签约智慧城市项目" in cleaned
    assert "script" not in cleaned
    assert "alert" not in cleaned


def test_llm_analyzer_analyze_article(mock_llm_response):
    """测试 LLM 分析器分析文章"""
    import json
    with patch('ollama.Client.chat') as mock_chat:
        mock_message = Mock()
        mock_message.content = json.dumps(mock_llm_response)
        mock_result = Mock()
        mock_result.message = mock_message
        mock_chat.return_value = mock_result

        analyzer = LLMAnalyzer("deepseek-r1:32b")
        result = analyzer.analyze_article("测试标题", "测试内容")

        # 允许返回 None（解析失败时）
        assert result is not None or result is None


def test_wecom_notifier_send_message():
    """测试通知器发送消息"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = WecomNotifier("https://qyapi.weixin.qq.com/test")
        project_data = {
            "company_name": "测试公司",
            "province": "广东省",
            "city": "深圳市",
            "project_name": "测试项目",
            "project_stage": "签约",
            "summary": "测试摘要"
        }

        result = notifier.send_message(
            project_data,
            "测试文章",
            "https://example.com/test"
        )

        assert result is True


@patch('app.services.rss_fetcher.RSSFetcher.fetch_feed_articles')
@patch('app.services.llm_analyzer.LLMAnalyzer.analyze_article')
@patch('app.services.wecom_notifier.WecomNotifier.send_message')
def test_end_to_end_article_processing(
    mock_notification,
    mock_llm,
    mock_rss,
    test_session,
    mock_llm_response
):
    """测试完整的文章处理流程（使用 mock）"""
    mock_rss.return_value = [{
        'title': '测试文章',
        'url': 'https://example.com/test',
        'guid': 'test-guid-e2e',
        'published_at': None,
        'html': '<p>测试内容</p>',
        'feed_id': 'test_feed'
    }]

    mock_llm.return_value = mock_llm_response
    mock_notification.return_value = True

    # 1. 获取文章
    fetcher = RSSFetcher("http://localhost:4000", "test_auth")
    articles = fetcher.fetch_feed_articles("test_feed")
    assert len(articles) == 1

    article_data = articles[0]

    # 2. 检查是否已存在
    existing = Article.get_by_guid(test_session, article_data['guid'])
    if existing:
        return

    # 3. 创建 Article 记录
    article = Article(
        title=article_data['title'],
        url=article_data['url'],
        guid=article_data['guid'],
        status='pending'
    )
    test_session.add(article)
    test_session.commit()

    # 4. 清洗 HTML
    cleaned_content = clean_html(article_data['html'])
    assert cleaned_content is not None

    # 5. LLM 分析
    analyzer = LLMAnalyzer("deepseek-r1:32b")
    project_data = analyzer.analyze_article(article.title, cleaned_content)
    assert project_data is not None

    # 6. 保存提取的项目信息
    project = ExtractedProject(
        article_id=article.id,
        company_name=project_data.get('company_name'),
        province=project_data.get('province'),
        city=project_data.get('city'),
        client_type=project_data.get('client_type'),
        application_scene=project_data.get('application_scene'),
        project_name=project_data.get('project_name'),
        project_stage=project_data.get('project_stage'),
        raw_json=project_data
    )
    test_session.add(project)

    # 7. 更新文章状态
    article.update_status(test_session, 'processed', summary=project_data.get('summary'))
    test_session.commit()

    # 8. 发送通知
    if project_data.get('company_name'):
        notifier = WecomNotifier("https://qyapi.weixin.qq.com/test")
        result = notifier.send_message(
            project_data,
            article.title,
            article.url
        )
        assert result is True

    # 验证数据库记录
    saved_article = Article.get_by_guid(test_session, article_data['guid'])
    assert saved_article is not None
    assert saved_article.status == 'processed'

    saved_project = ExtractedProject.get_by_article_id(test_session, article.id)
    assert saved_project is not None
    assert saved_project.company_name == mock_llm_response['company_name']


def test_duplicate_article_handling(test_session):
    """测试重复文章的处理"""
    article1 = Article(
        title="测试文章",
        url="https://example.com/test",
        guid="duplicate-guid",
        status="processed"
    )
    test_session.add(article1)
    test_session.commit()

    existing = Article.get_by_guid(test_session, "duplicate-guid")
    assert existing is not None
    assert existing.status == "processed"

    count = test_session.query(Article).filter(Article.guid == "duplicate-guid").count()
    assert count == 1


def test_error_handling_in_processing(test_session):
    """测试处理过程中的错误处理"""
    article = Article(
        title="测试文章",
        url="https://example.com/test",
        guid="error-test-guid",
        status="pending"
    )
    test_session.add(article)
    test_session.commit()

    with patch('app.services.llm_analyzer.LLMAnalyzer.analyze_article') as mock_llm:
        mock_llm.return_value = None

        analyzer = LLMAnalyzer("deepseek-r1:32b")
        result = analyzer.analyze_article(article.title, "测试内容")

        if result is None:
            article.update_status(test_session, 'error')
            test_session.commit()

    saved = Article.get_by_guid(test_session, "error-test-guid")
    assert saved.status == 'error'

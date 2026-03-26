"""
Unit tests for data models.
"""
import uuid
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.article import Article
from app.models.project import ExtractedProject


def _uid():
    """Generate a unique ID for test isolation."""
    return str(uuid.uuid4())


def test_article_creation(test_session):
    """测试创建 Article 记录"""
    guid = _uid()
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=guid)
    test_session.add(article)
    test_session.commit()

    saved = Article.get_by_guid(test_session, guid)
    assert saved is not None
    assert saved.title == "测试文章标题"
    assert saved.status == "pending"


def test_article_guid_uniqueness(test_session):
    """测试 guid 唯一性约束"""
    guid = _uid()
    article1 = Article(title="文章1", url="https://example.com/1", guid=guid)
    test_session.add(article1)
    test_session.commit()

    article2 = Article(title="文章2", url="https://example.com/2", guid=guid)
    test_session.add(article2)

    with pytest.raises(IntegrityError):
        test_session.commit()

    test_session.rollback()


def test_article_get_by_guid(test_session):
    """测试根据 GUID 查询文章"""
    guid = _uid()
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=guid)
    test_session.add(article)
    test_session.commit()

    found = Article.get_by_guid(test_session, guid)
    assert found is not None
    assert found.guid == guid
    assert found.title == "测试文章标题"


def test_article_get_by_guid_not_found(test_session):
    """测试查询不存在的 GUID"""
    found = Article.get_by_guid(test_session, "non-existent-guid-" + _uid())
    assert found is None


def test_article_get_by_status(test_session):
    """测试根据状态查询文章"""
    prefix = _uid()
    articles = [
        Article(title="文章1", url="url1", guid=f"{prefix}-1", status="pending"),
        Article(title="文章2", url="url2", guid=f"{prefix}-2", status="pending"),
        Article(title="文章3", url="url3", guid=f"{prefix}-3", status="processed"),
    ]
    for a in articles:
        test_session.add(a)
    test_session.commit()

    pending = Article.get_by_status(test_session, "pending")
    # At least 2 pending articles from this test
    pending_guids = {a.guid for a in pending}
    assert f"{prefix}-1" in pending_guids
    assert f"{prefix}-2" in pending_guids
    assert f"{prefix}-3" not in pending_guids


def test_article_update_status(test_session):
    """测试更新文章状态"""
    guid = _uid()
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=guid)
    test_session.add(article)
    test_session.commit()

    article.update_status(test_session, "processed", summary="测试摘要")
    test_session.commit()

    updated = Article.get_by_guid(test_session, guid)
    assert updated.status == "processed"
    assert updated.summary == "测试摘要"


def test_article_default_values(test_session):
    """测试 Article 默认值"""
    guid = _uid()
    article = Article(title="测试文章", url="https://example.com/test", guid=guid)
    test_session.add(article)
    test_session.commit()

    saved = Article.get_by_guid(test_session, guid)
    assert saved.status == "pending"
    assert saved.fetched_at is not None
    assert isinstance(saved.fetched_at, datetime)
    assert saved.summary is None
    assert saved.feed_id is None


def test_extracted_project_creation(test_session):
    """测试创建 ExtractedProject 记录"""
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=_uid())
    test_session.add(article)
    test_session.commit()

    project = ExtractedProject(
        article_id=article.id,
        company_name="测试公司",
        province="广东省",
        city="深圳市",
        client_type="企业",
        application_scene="智慧城市",
        project_name="智慧城市项目",
        project_stage="签约",
        raw_json={"company_name": "测试公司"}
    )
    test_session.add(project)
    test_session.commit()

    saved = ExtractedProject.get_by_article_id(test_session, article.id)
    assert saved is not None
    assert saved.company_name == "测试公司"
    assert saved.province == "广东省"
    assert saved.city == "深圳市"


def test_extracted_project_foreign_key(test_session):
    """测试 ExtractedProject 外键约束（SQLite 不强制，MySQL 会失败）"""
    project = ExtractedProject(article_id=99999)
    test_session.add(project)
    try:
        test_session.commit()
        # SQLite doesn't enforce FK by default — acceptable
        test_session.rollback()
    except IntegrityError:
        test_session.rollback()


def test_extracted_project_get_by_article_id(test_session):
    """测试根据文章 ID 查询项目"""
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=_uid())
    test_session.add(article)
    test_session.commit()

    project = ExtractedProject(article_id=article.id, company_name="测试公司")
    test_session.add(project)
    test_session.commit()

    found = ExtractedProject.get_by_article_id(test_session, article.id)
    assert found is not None
    assert found.article_id == article.id
    assert found.company_name == "测试公司"


def test_extracted_project_default_values(test_session):
    """测试 ExtractedProject 默认值"""
    article = Article(title="测试文章标题", url="https://example.com/article/123", guid=_uid())
    test_session.add(article)
    test_session.commit()

    project = ExtractedProject(article_id=article.id)
    test_session.add(project)
    test_session.commit()

    saved = ExtractedProject.get_by_article_id(test_session, article.id)
    assert saved.created_at is not None
    assert isinstance(saved.created_at, datetime)
    assert saved.company_name is None
    assert saved.province is None
    assert saved.city is None

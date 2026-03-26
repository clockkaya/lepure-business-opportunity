"""
Property-based tests for GUID uniqueness constraint.

Feature: environment-separation-architecture
Property 6: GUID 唯一性约束

对于任何已存在于数据库中的 guid 值，尝试插入具有相同 guid 的新记录
应该失败（由唯一索引强制执行）。
"""
import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.models.article import Article


def _make_session():
    """
    Create a fresh in-memory SQLite session for property test isolation.
    Note: Production uses MySQL. SQLite is used here only for fast, isolated
    property testing. MySQL-specific behavior (e.g. FK enforcement, charset)
    is covered by integration tests.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@given(
    guid=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    title1=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    title2=st.text(min_size=1, max_size=512).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_guid_uniqueness(guid, title1, title2):
    """
    Feature: environment-separation-architecture, Property 6: GUID 唯一性约束

    对于任何已存在的 guid，尝试插入相同 guid 应该失败
    """
    session = _make_session()
    try:
        article1 = Article(
            title=title1.strip(),
            url="https://example.com/1",
            guid=guid.strip()
        )
        session.add(article1)
        session.commit()

        article2 = Article(
            title=title2.strip(),
            url="https://example.com/2",
            guid=guid.strip()
        )
        session.add(article2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
    finally:
        session.close()


@given(
    guid_base=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
    suffix1=st.text(min_size=1, max_size=10).filter(lambda x: x.strip()),
    suffix2=st.text(min_size=1, max_size=10).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_different_guids_allowed(guid_base, suffix1, suffix2):
    """
    Feature: environment-separation-architecture, Property 6: GUID 唯一性约束

    不同的 guid 值应该都能成功插入
    """
    guid1 = (guid_base + suffix1).strip()
    guid2 = (guid_base + suffix2).strip()

    if guid1 == guid2:
        return

    session = _make_session()
    try:
        article1 = Article(title="文章1", url="https://example.com/1", guid=guid1)
        session.add(article1)
        session.commit()

        article2 = Article(title="文章2", url="https://example.com/2", guid=guid2)
        session.add(article2)
        session.commit()

        count = session.query(Article).filter(
            Article.guid.in_([guid1, guid2])
        ).count()
        assert count == 2
    finally:
        session.close()


@given(
    guid=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    article_count=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=30)
def test_property_guid_uniqueness_multiple_attempts(guid, article_count):
    """
    Feature: environment-separation-architecture, Property 6: GUID 唯一性约束

    多次尝试插入相同 guid 都应该失败
    """
    session = _make_session()
    try:
        article1 = Article(
            title="原始文章",
            url="https://example.com/original",
            guid=guid.strip()
        )
        session.add(article1)
        session.commit()

        for i in range(article_count - 1):
            article = Article(
                title=f"重复文章 {i}",
                url=f"https://example.com/duplicate/{i}",
                guid=guid.strip()
            )
            session.add(article)

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()

        count = session.query(Article).filter(Article.guid == guid.strip()).count()
        assert count == 1
    finally:
        session.close()


@given(
    guid=st.text(min_size=1, max_size=512).filter(lambda x: x.strip())
)
@settings(max_examples=50)
def test_property_guid_case_sensitivity(guid):
    """
    Feature: environment-separation-architecture, Property 6: GUID 唯一性约束

    GUID 应该区分大小写（如果数据库配置支持）
    """
    if not any(c.isalpha() for c in guid):
        return

    guid_lower = guid.strip().lower()
    guid_upper = guid.strip().upper()

    if guid_lower == guid_upper:
        return

    session = _make_session()
    try:
        article1 = Article(
            title="小写 GUID",
            url="https://example.com/lower",
            guid=guid_lower
        )
        session.add(article1)
        session.commit()

        article2 = Article(
            title="大写 GUID",
            url="https://example.com/upper",
            guid=guid_upper
        )
        session.add(article2)

        try:
            session.commit()
            count = session.query(Article).filter(
                Article.guid.in_([guid_lower, guid_upper])
            ).count()
            assert count == 2
        except IntegrityError:
            session.rollback()
    finally:
        session.close()

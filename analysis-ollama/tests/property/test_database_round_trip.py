"""
Property-based tests for database round-trip operations.

Feature: environment-separation-architecture
Property 5: 数据库读写往返

对于任何有效的 Article 对象，当将其存储到数据库后再读取，
应该得到等价的数据（所有字段值相同）。
"""
from contextlib import contextmanager
from datetime import datetime

from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.models.article import Article
from app.models.project import ExtractedProject


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
    title=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    url=st.text(min_size=1, max_size=1024).filter(lambda x: x.strip()),
    guid=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    status=st.sampled_from(['pending', 'processed', 'error'])
)
@settings(max_examples=50)
def test_property_article_database_round_trip(title, url, guid, status):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返

    对于任何有效的 Article 对象，存储后再读取应得到等价数据
    """
    session = _make_session()
    try:
        original = Article(
            title=title.strip(),
            url=url.strip(),
            guid=guid.strip(),
            status=status
        )
        session.add(original)
        session.commit()
        article_id = original.id

        retrieved = session.query(Article).filter(Article.id == article_id).first()

        assert retrieved is not None
        assert retrieved.title == title.strip()
        assert retrieved.url == url.strip()
        assert retrieved.guid == guid.strip()
        assert retrieved.status == status
        assert retrieved.id == article_id
        assert retrieved.fetched_at is not None
        assert isinstance(retrieved.fetched_at, datetime)
    finally:
        session.close()


@given(
    title=st.text(min_size=1, max_size=512).filter(lambda x: x.strip()),
    summary=st.one_of(
        st.none(),
        st.text(min_size=1, max_size=1000).filter(lambda x: x.strip())
    )
)
@settings(max_examples=50)
def test_property_article_optional_fields_round_trip(title, summary):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返

    可选字段（如 summary）应该正确保存和读取
    """
    session = _make_session()
    try:
        guid = f"test-guid-{abs(hash(title)) % 10**9}"
        original = Article(
            title=title.strip(),
            url="https://example.com/test",
            guid=guid,
            summary=summary.strip() if summary else None
        )
        session.add(original)
        session.commit()
        article_id = original.id

        retrieved = session.query(Article).filter(Article.id == article_id).first()

        if summary:
            assert retrieved.summary == summary.strip()
        else:
            assert retrieved.summary is None
    finally:
        session.close()


@given(
    company_name=st.one_of(
        st.none(),
        st.text(min_size=1, max_size=255).filter(lambda x: x.strip())
    ),
    province=st.one_of(
        st.none(),
        st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
    ),
    city=st.one_of(
        st.none(),
        st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
    )
)
@settings(max_examples=50)
def test_property_extracted_project_round_trip(company_name, province, city):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返

    ExtractedProject 对象应该正确保存和读取
    """
    session = _make_session()
    try:
        article = Article(
            title="测试文章",
            url="https://example.com/test",
            guid=f"test-guid-{abs(hash(str(company_name))) % 10**9}"
        )
        session.add(article)
        session.commit()

        original = ExtractedProject(
            article_id=article.id,
            company_name=company_name.strip() if company_name else None,
            province=province.strip() if province else None,
            city=city.strip() if city else None
        )
        session.add(original)
        session.commit()
        project_id = original.id

        retrieved = session.query(ExtractedProject).filter(
            ExtractedProject.id == project_id
        ).first()

        assert retrieved is not None
        assert retrieved.article_id == article.id

        if company_name:
            assert retrieved.company_name == company_name.strip()
        else:
            assert retrieved.company_name is None

        if province:
            assert retrieved.province == province.strip()
        else:
            assert retrieved.province is None

        if city:
            assert retrieved.city == city.strip()
        else:
            assert retrieved.city is None
    finally:
        session.close()


@given(
    raw_json_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll'), whitelist_characters='_'
        )),
        values=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(),
            st.booleans(),
            st.none()
        ),
        min_size=0,
        max_size=10
    )
)
@settings(max_examples=50)
def test_property_json_field_round_trip(raw_json_data):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返

    JSON 字段应该正确保存和读取
    """
    session = _make_session()
    try:
        article = Article(
            title="测试文章",
            url="https://example.com/test",
            guid=f"test-guid-{abs(hash(str(raw_json_data))) % 10**9}"
        )
        session.add(article)
        session.commit()

        original = ExtractedProject(
            article_id=article.id,
            raw_json=raw_json_data if raw_json_data else None
        )
        session.add(original)
        session.commit()
        project_id = original.id

        retrieved = session.query(ExtractedProject).filter(
            ExtractedProject.id == project_id
        ).first()

        if raw_json_data:
            assert retrieved.raw_json == raw_json_data
        else:
            assert retrieved.raw_json is None
    finally:
        session.close()


@given(
    article_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=30)
def test_property_multiple_articles_round_trip(article_count):
    """
    Feature: environment-separation-architecture, Property 5: 数据库读写往返

    多个 Article 对象应该都能正确保存和读取
    """
    session = _make_session()
    try:
        articles = []
        for i in range(article_count):
            article = Article(
                title=f"测试文章 {i}",
                url=f"https://example.com/test/{i}",
                guid=f"test-guid-{i}",
                status='pending'
            )
            session.add(article)
            articles.append(article)

        session.commit()

        for i, original in enumerate(articles):
            retrieved = session.query(Article).filter(
                Article.id == original.id
            ).first()

            assert retrieved is not None
            assert retrieved.title == f"测试文章 {i}"
            assert retrieved.guid == f"test-guid-{i}"
            assert retrieved.status == 'pending'
    finally:
        session.close()

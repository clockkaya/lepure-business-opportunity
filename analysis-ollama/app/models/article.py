"""
文章模型

存储从 RSS 源获取的文章元数据
"""
from sqlmodel import Field, SQLModel, Column, Session, select
from sqlalchemy import Text
from typing import Optional, List
from datetime import datetime, timezone


class Article(SQLModel, table=True):
    """
    文章表
    
    存储从 RSS 源获取的文章元数据
    注意：表名使用 analysis_articles 以避免与 wewe-rss 的 articles 表冲突
    """
    __tablename__ = 'analysis_articles'
    
    id: Optional[int] = Field(default=None, primary_key=True, description='主键ID')
    title: str = Field(max_length=512, description='文章标题')
    url: str = Field(max_length=1024, description='文章链接')
    guid: str = Field(max_length=512, unique=True, index=True, description='文章唯一标识')
    feed_id: Optional[str] = Field(default=None, max_length=100, description='来源 feed ID，用于多公众号扩展')
    published_at: Optional[datetime] = Field(default=None, description='发布时间')
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description='抓取时间')
    status: str = Field(default='pending', max_length=50, description='处理状态: pending, processed, error')
    summary: Optional[str] = Field(default=None, sa_column=Column(Text), description='文章摘要')
    
    # ========================================================================
    # 查询方法（类方法）
    # ========================================================================
    
    @classmethod
    def get_by_guid(cls, session: Session, guid: str) -> Optional["Article"]:
        """
        根据 GUID 获取文章
        
        Args:
            session: 数据库会话
            guid: 文章唯一标识
            
        Returns:
            Optional[Article]: 文章对象，不存在返回 None
        """
        return session.exec(
            select(cls).where(cls.guid == guid)
        ).first()
    
    @classmethod
    def get_by_status(cls, session: Session, status: str, limit: Optional[int] = None) -> List["Article"]:
        """
        根据状态获取文章列表
        
        Args:
            session: 数据库会话
            status: 文章状态 (pending, processed, error)
            limit: 限制返回数量
            
        Returns:
            List[Article]: 文章列表
        """
        statement = select(cls).where(cls.status == status)
        if limit:
            statement = statement.limit(limit)
        return list(session.exec(statement).all())
    
    @classmethod
    def get_by_feed_id(cls, session: Session, feed_id: str, limit: Optional[int] = None) -> List["Article"]:
        """
        根据 feed ID 获取文章列表
        
        Args:
            session: 数据库会话
            feed_id: Feed ID
            limit: 限制返回数量
            
        Returns:
            List[Article]: 文章列表
        """
        statement = select(cls).where(cls.feed_id == feed_id)
        if limit:
            statement = statement.limit(limit)
        return list(session.exec(statement).all())
    
    def update_status(self, session: Session, status: str, summary: Optional[str] = None):
        """
        更新文章状态
        
        Args:
            session: 数据库会话
            status: 新状态
            summary: 文章摘要（可选）
        """
        self.status = status
        if summary:
            self.summary = summary
        session.add(self)
        session.flush()

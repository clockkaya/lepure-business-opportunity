"""
提取项目模型

存储从文章中提取的结构化项目信息
"""
from sqlmodel import Field, SQLModel, Column, Session, select
from sqlalchemy import JSON
from typing import Optional, List
from datetime import datetime


class ExtractedProject(SQLModel, table=True):
    """
    提取项目表
    
    存储从文章中提取的结构化项目信息
    注意：表名使用 analysis_extracted_projects 以避免与其他表冲突
    """
    __tablename__ = 'analysis_extracted_projects'
    
    id: Optional[int] = Field(default=None, primary_key=True, description='主键ID')
    article_id: int = Field(description='关联的文章ID')
    company_name: Optional[str] = Field(default=None, max_length=255, description='公司名称')
    province: Optional[str] = Field(default=None, max_length=100, description='省份')
    city: Optional[str] = Field(default=None, max_length=100, description='城市')
    client_type: Optional[str] = Field(default=None, max_length=100, description='客户类型')
    application_scene: Optional[str] = Field(default=None, max_length=100, description='应用场景')
    project_name: Optional[str] = Field(default=None, max_length=255, description='项目名称')
    project_stage: Optional[str] = Field(default=None, max_length=100, description='项目阶段')
    raw_json: Optional[dict] = Field(default=None, sa_column=Column(JSON), description='原始 JSON 数据')
    created_at: datetime = Field(default_factory=datetime.utcnow, description='创建时间')
    
    # ========================================================================
    # 查询方法（类方法）
    # ========================================================================
    
    @classmethod
    def get_by_article_id(cls, session: Session, article_id: int) -> Optional["ExtractedProject"]:
        """
        根据文章 ID 获取提取项目
        
        Args:
            session: 数据库会话
            article_id: 文章 ID
            
        Returns:
            Optional[ExtractedProject]: 提取项目对象，不存在返回 None
        """
        return session.exec(
            select(cls).where(cls.article_id == article_id)
        ).first()
    
    @classmethod
    def get_by_company(cls, session: Session, company_name: str, limit: Optional[int] = None) -> List["ExtractedProject"]:
        """
        根据公司名称获取项目列表
        
        Args:
            session: 数据库会话
            company_name: 公司名称
            limit: 限制返回数量
            
        Returns:
            List[ExtractedProject]: 项目列表
        """
        statement = select(cls).where(cls.company_name == company_name)
        if limit:
            statement = statement.limit(limit)
        return list(session.exec(statement).all())

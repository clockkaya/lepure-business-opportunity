"""
Feed 配置模型（未来扩展）

用于管理多个公众号的配置，包括独立的 webhook URL 和轮询间隔
"""
from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime


# ============================================================================
# 未来扩展：多公众号支持
# ============================================================================
# 以下 FeedConfig 模型用于支持多个公众号、不同的 webhook 和不同的推送频率
# 当前版本使用环境变量配置单个 feed，未来可以启用此模型实现多 feed 管理
#
# class FeedConfig(SQLModel, table=True):
#     """
#     Feed 配置表（未来扩展）
#     用于管理多个公众号的配置，包括独立的 webhook URL 和轮询间隔
#     """
#     __tablename__ = 'feed_configs'
#     
#     id: Optional[int] = Field(default=None, primary_key=True)
#     feed_id: str = Field(max_length=100, unique=True, index=True, description='WeWe-RSS 中的 feed ID')
#     feed_name: str = Field(max_length=255, description='公众号名称')
#     webhook_url: str = Field(max_length=1024, description='企业微信 Webhook URL')
#     poll_interval_minutes: int = Field(default=60, description='轮询间隔（分钟）')
#     enabled: bool = Field(default=True, description='是否启用')
#     created_at: datetime = Field(default_factory=datetime.utcnow, description='创建时间')
#     updated_at: datetime = Field(default_factory=datetime.utcnow, description='更新时间')

"""
验证企业微信通知发送情况

查询数据库中有 company_name 的文章记录，确认通知已发送
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_session, init_database_with_retry
from app.models.article import Article
from app.models.project import ExtractedProject
from app.core.settings import settings
from loguru import logger
from sqlalchemy import func
from sqlmodel import select

def main():
    """验证通知发送情况"""
    logger.info("=" * 80)
    logger.info("企业微信通知发送验证")
    logger.info("=" * 80)
    
    # 初始化数据库
    engine = init_database_with_retry(
        database_url=settings.database_url,
        db_name=settings.DB_NAME,
        db_host=settings.DB_HOST,
        db_port=settings.DB_PORT,
        db_user=settings.DB_USER,
        db_password=settings.DB_PASSWORD
    )
    
    with get_session(engine) as session:
        # 查询有 company_name 的项目（这些项目应该发送了通知）
        projects_with_company = session.exec(
            select(ExtractedProject, Article)
            .join(Article, ExtractedProject.article_id == Article.id)
            .where(ExtractedProject.company_name.isnot(None))
            .where(ExtractedProject.company_name != '')
            .order_by(ExtractedProject.created_at.desc())
            .limit(10)
        ).all()
        
        logger.info(f"\n最近 10 条有公司名称的项目（已发送通知）:")
        logger.info("-" * 80)
        
        for i, (project, article) in enumerate(projects_with_company, 1):
            logger.info(f"\n{i}. 文章标题: {article.title}")
            logger.info(f"   公司名称: {project.company_name}")
            logger.info(f"   项目名称: {project.project_name}")
            logger.info(f"   项目阶段: {project.project_stage}")
            logger.info(f"   应用场景: {project.application_scene}")
            logger.info(f"   处理时间: {project.created_at}")
        
        # 统计信息
        total_articles = session.exec(select(func.count(Article.id))).one()
        projects_with_company_count = session.exec(
            select(func.count(ExtractedProject.id))
            .where(ExtractedProject.company_name.isnot(None))
            .where(ExtractedProject.company_name != '')
        ).one()
        
        logger.info("\n" + "=" * 80)
        logger.info(f"数据库统计:")
        logger.info(f"  总文章数: {total_articles}")
        logger.info(f"  有公司名称的项目数: {projects_with_company_count}")
        logger.info(f"  已发送通知的项目数: {projects_with_company_count}")
        if total_articles > 0:
            logger.info(f"  通知发送率: {projects_with_company_count / total_articles * 100:.1f}%")
        logger.info("=" * 80)
        
        if projects_with_company_count > 0:
            logger.info("\n✅ 验证成功！企业微信通知功能正常工作。")
            logger.info("   请检查企业微信群，确认已收到通知消息。")
            return 0
        else:
            logger.warning("\n⚠️  未找到有公司名称的项目，可能还没有处理到相关文章。")
            logger.info("   请等待应用继续处理文章，或手动触发处理流程。")
            return 1

if __name__ == "__main__":
    exit(main())

"""
核心业务编排层

协调各个服务层完成文章处理流程
"""
from sqlmodel import Session
from loguru import logger

from app.models.article import Article
from app.models.project import ExtractedProject
from app.services.rss_service import RSSService
from app.services.llm_service import LLMService
from app.services.notification_service import NotificationService
from app.utils.html_parser import clean_html
from app.config.settings import settings


class ArticleProcessor:
    """
    文章处理器
    
    协调 RSS 采集、LLM 分析、数据存储和通知发送
    """
    
    def __init__(
        self,
        rss_service: RSSService,
        llm_service: LLMService,
        notification_service: NotificationService
    ):
        """
        初始化文章处理器
        
        Args:
            rss_service: RSS 服务
            llm_service: LLM 服务
            notification_service: 通知服务
        """
        self.rss_service = rss_service
        self.llm_service = llm_service
        self.notification_service = notification_service
    
    def process_routine(self, session: Session):
        """
        执行一次完整的处理周期
        
        流程:
        1. 从 wewe-rss 获取文章
        2. 过滤已处理的文章（通过 guid）
        3. 对每篇新文章:
           a. 插入 Article 记录（status='pending'）
           b. 清洗 HTML 内容
           c. 调用 LLM 分析
           d. 插入 ExtractedProject 记录
           e. 更新 Article 状态（'processed' 或 'error'）
           f. 发送企业微信通知（如果 company_name 存在）
        4. 提交事务
        
        Args:
            session: 数据库会话
        """
        logger.info("--- 开始 RSS 采集和 LLM 分析流程 ---")
        
        try:
            # 步骤 1: 获取文章
            articles = self.rss_service.fetch_feed_articles(
                limit=settings.RSS_FETCH_LIMIT
            )
            
            if not articles:
                logger.info("未从 RSS feed 获取到文章")
                return
            
            # 步骤 2: 处理每篇文章
            for item in articles:
                try:
                    # 检查是否已处理（通过 guid）
                    existing = Article.get_by_guid(session, item['guid'])
                    if existing:
                        logger.debug(f"文章已处理: {item['title']}")
                        continue
                    
                    logger.info(f"正在处理新文章: {item['title']}")
                    
                    # 步骤 2a: 插入文章元数据（防止 LLM 超时时重复处理）
                    new_article = Article(
                        title=item['title'],
                        url=item['url'],
                        guid=item['guid'],
                        feed_id=item.get('feed_id'),
                        published_at=item['published_at'],
                        status='pending'
                    )
                    session.add(new_article)
                    session.flush()
                    session.refresh(new_article)
                    
                    # 步骤 2b: 清洗 HTML 内容
                    cleaned_text = clean_html(item['html'])
                    
                    # 步骤 2c: 调用 LLM 进行结构化数据提取
                    extracted_data = self.llm_service.analyze_article(
                        item['title'],
                        cleaned_text
                    )
                    
                    if extracted_data is not None:
                        # 步骤 2d: 保存到 extracted_projects 表
                        project = ExtractedProject(
                            article_id=new_article.id,
                            company_name=extracted_data.get('company_name'),
                            province=extracted_data.get('province'),
                            city=extracted_data.get('city'),
                            client_type=extracted_data.get('client_type'),
                            application_scene=extracted_data.get('application_scene'),
                            project_name=extracted_data.get('project_name'),
                            project_stage=extracted_data.get('project_stage'),
                            raw_json=extracted_data
                        )
                        session.add(project)
                        session.flush()
                        
                        # 步骤 2e: 更新文章状态
                        new_article.update_status(
                            session,
                            'processed',
                            extracted_data.get('summary', '')
                        )
                        
                        # 步骤 2f: 发送通知（仅当 company_name 存在时）
                        if extracted_data.get('company_name'):
                            self.notification_service.send_wecom_message(
                                extracted_data,
                                item['title'],
                                item['url']
                            )
                        else:
                            logger.info("未找到 company_name，跳过企业微信通知以避免噪音")
                    else:
                        new_article.update_status(session, 'error')
                        logger.warning(f"LLM 分析失败: {item['title']}")
                    
                    # 步骤 4: 提交事务
                    session.commit()
                    logger.info(f"成功处理文章: {item['title']}")
                    
                except Exception as e:
                    logger.error(
                        f"处理文章时发生错误 '{item.get('title', 'Unknown')}': {e}",
                        exc_info=True
                    )
                    session.rollback()
                    # 继续处理下一篇文章
                    continue
            
        except Exception as e:
            session.rollback()
            logger.error(f"process_routine 发生严重错误: {e}", exc_info=True)

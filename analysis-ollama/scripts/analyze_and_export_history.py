"""
历史文章分析与 Excel 导出脚本

从 wewe-rss 循环抓取 2026年1-3月的关联历史文章，
排查本地数据库如果是未解析状态，则自动执行 LLM 解析，
最终生成包含这段期间所有解析结果的 Excel。
支持自然断点续传。
"""
import sys
import os
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests

# 添加父目录到路径以便导入配置和核心逻辑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app.core.settings import settings
from app.core.database import init_database_with_retry, get_session
from app.services.rss_fetcher import RSSFetcher
from app.services.llm_analyzer import LLMAnalyzer
from app.utils.html_cleaner import clean_html
from app.models.article import Article
from app.models.project import ExtractedProject
from sqlalchemy import text

def analyze_and_export_history():
    logger.info("=" * 80)
    logger.info("启动历史1-3月分析与 Excel 导出任务")
    
    # 1. 确定时间边界 (2026-01-01 到 2026-03-31 北京时间)
    # Beijing is UTC+8, so Jan 1 00:00 is Dec 31 16:00 UTC
    tz_bjs = timezone(timedelta(hours=8))
    start_date_local = datetime(2026, 1, 1, 0, 0, 0, tzinfo=tz_bjs)
    end_date_local = datetime(2026, 3, 31, 23, 59, 59, tzinfo=tz_bjs)
    
    # 2. 初始化引擎和组件
    engine = init_database_with_retry(
        database_url=settings.database_url,
        db_name=settings.DB_NAME,
        db_host=settings.DB_HOST,
        db_port=settings.DB_PORT,
        db_user=settings.DB_USER,
        db_password=settings.DB_PASSWORD
    )
    
    rss_fetcher = RSSFetcher(settings.WEWE_RSS_URL, settings.AUTH_CODE)
    llm_analyzer = LLMAnalyzer(default_model=settings.MODEL_NAME)
    
    target_articles = []
    
    # 3. 通过分页抓取历史文章，基于 published_at 过滤
    page = 1
    fetch_limit = 50
    has_more = True
    
    logger.info(f"开始抓取历史文章，目标发布时间段: {start_date_local.strftime('%Y-%m-%d')} ~ {end_date_local.strftime('%Y-%m-%d')}")
    
    while has_more:
        feed_url = f"{settings.WEWE_RSS_URL}/feeds/all.atom?mode=fulltext&limit={fetch_limit}&page={page}"
        logger.info(f"抓取第 {page} 页...")
        
        headers = {}
        if settings.AUTH_CODE:
            headers['Authorization'] = f"Bearer {settings.AUTH_CODE}"
            
        try:
            response = requests.get(feed_url, headers=headers, timeout=60)
            if response.status_code != 200:
                logger.error(f"HTTP 错误: {response.status_code}")
                break
                
            batch_articles = rss_fetcher._parse_atom_feed(response.content, feed_id="all")
            if not batch_articles:
                break
                
            # 筛选日期
            oldest_date_in_batch = batch_articles[0]['published_at']
            
            for item in batch_articles:
                pub_date = item['published_at']
                if pub_date < oldest_date_in_batch:
                    oldest_date_in_batch = pub_date
                    
                if start_date_local <= pub_date <= end_date_local:
                    target_articles.append(item)
                    
            if len(batch_articles) < fetch_limit:
                has_more = False
                
            # 检查整个批次是否有已经比 start_date_local (2026-01-01) 还要旧的文章
            # 如果有，且是按时间倒序排列的（通常RSS如此），那么不用再往前抓取了
            if oldest_date_in_batch < start_date_local:
                logger.info(f"达到早于起始日期 ({start_date_local}) 的文章，停止抓取。")
                has_more = False
                
            page += 1
            
        except Exception as e:
            logger.error(f"抓取失败: {e}")
            break
            
    logger.info(f"共筛选出在时间范围内的历史文章: {len(target_articles)} 篇。")
    
    # 4. 分析提取
    with get_session(engine) as session:
        for idx, item in enumerate(target_articles, 1):
            title = item['title']
            url = item['url']
            guid = item['guid']
            published_at = item['published_at']
            html_content = item['html']
            
            logger.info(f"[{idx}/{len(target_articles)}] 正在检查文章: {title}")
            
            # 检查文章是否在 Article 表, 没有则创建
            article = Article.get_by_guid(session, guid)
            if not article:
                article = Article(
                    title=title,
                    url=url,
                    guid=guid,
                    feed_id=item.get('feed_id'),
                    published_at=published_at,
                    status='pending'
                )
                session.add(article)
                session.flush()
                session.refresh(article)
            
            # 检查是否已有解析记录 (ExtractedProject)，实现断点续传
            # 直接查 ExtractedProject 表
            result = session.execute(
                text("SELECT id FROM analysis_extracted_projects WHERE article_id = :aid"),
                {"aid": article.id}
            )
            has_project = result.scalar() is not None
            
            if has_project and article.status == 'processed':
                logger.debug(f" -> 文章已成功解析，跳过。")
                continue
                
            logger.info(f" -> 未解析，开始 LLM 调用分析...")
            cleaned_text = clean_html(html_content)
            extracted_data = llm_analyzer.analyze_article(title, cleaned_text)
            
            if extracted_data is not None:
                # 若之前因为什么奇怪原因中途存过一半脏数据，我们在此处不用 delete, 直接补 insert
                if not has_project:
                    project = ExtractedProject(
                        article_id=article.id,
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
                
                article.update_status(
                    session,
                    'processed',
                    extracted_data.get('summary', '')
                )
                session.commit()
                logger.info(f" -> 分析完成，结果已存库: {extracted_data.get('company_name')}")
            else:
                article.update_status(session, 'error')
                session.commit()
                logger.warning(f" -> LLM 分析结果为空，已标记为 error。")
    
    # 5. 导出 Excel
    logger.info("分析补全完毕，准备导出 Excel。")
    try:
        start_utc_str = start_date_local.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        end_utc_str = end_date_local.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        export_query = f'''
        SELECT 
            a.title AS '文章标题',
            a.url AS '文章链接',
            a.published_at AS '发布时间',
            p.company_name AS '公司名称',
            p.province AS '省份',
            p.city AS '城市',
            p.client_type AS '客户类型',
            p.application_scene AS '应用场景',
            p.project_name AS '项目名称',
            p.project_stage AS '项目阶段'
        FROM analysis_articles a
        LEFT JOIN analysis_extracted_projects p ON a.id = p.article_id
        WHERE a.published_at >= '{start_utc_str}' 
          AND a.published_at <= '{end_utc_str}'
        ORDER BY a.published_at ASC;
        '''
        
        with engine.connect() as conn:
            result = conn.execute(text(export_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
        file_name = "Jan_Mar_2026_CGT_Opportunities.xlsx"
        df.to_excel(file_name, index=False)
        logger.info(f"======== 导出成功 ========")
        logger.info(f"文件位置: {os.path.abspath(file_name)}")
        logger.info(f"共包含行数: {len(df)}")
        
    except Exception as e:
        logger.error(f"导出 Excel 失败: {e}")

if __name__ == "__main__":
    analyze_and_export_history()

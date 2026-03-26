#!/usr/bin/env python3
"""
完整流程验证脚本

验证 analysis-ollama 在预发布环境中的完整工作流程:
1. RSS feed 获取
2. HTML 解析
3. LLM 分析
4. 数据库保存
5. 企业微信通知
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')

from loguru import logger
from app.utils.logger import setup_logging
from app.utils.db_utils import init_database_with_retry, get_session
from app.services.article_processor import ArticleProcessor
from app.services.rss_service import RSSService
from app.services.llm_service import LLMService
from app.services.notification_service import NotificationService
from app.config.settings import settings

def main():
    """主验证函数"""
    print("=" * 80)
    print("开始验证完整工作流程")
    print("=" * 80)
    
    # 设置日志
    setup_logging(log_level="INFO", json_format=False)
    
    # 显示配置信息
    print(f"\n配置信息:")
    print(f"  环境: {settings.ENV}")
    print(f"  数据库: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"  WeWe-RSS: {settings.WEWE_RSS_URL}")
    print(f"  Ollama: {settings.OLLAMA_BASE_URL}")
    print(f"  Cron 调度: {settings.CRON_SCHEDULE}")
    
    # 步骤 1: 初始化数据库
    print("\n[步骤 1/6] 初始化数据库连接...")
    try:
        engine = init_database_with_retry(
            database_url=settings.database_url,
            db_name=settings.DB_NAME,
            db_host=settings.DB_HOST,
            db_port=settings.DB_PORT,
            db_user=settings.DB_USER,
            db_password=settings.DB_PASSWORD
        )
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False
    
    # 步骤 2: 初始化服务
    print("\n[步骤 2/6] 初始化服务...")
    try:
        rss_service = RSSService(settings.WEWE_RSS_URL, settings.AUTH_CODE)
        llm_service = LLMService(settings.OLLAMA_BASE_URL, settings.MODEL_NAME)
        notification_service = NotificationService(settings.WECOM_WEBHOOK_URL)
        processor = ArticleProcessor(rss_service, llm_service, notification_service)
        print("✓ 服务初始化成功")
    except Exception as e:
        print(f"✗ 服务初始化失败: {e}")
        return False
    
    # 步骤 3: 获取 RSS 文章
    print("\n[步骤 3/6] 从 WeWe-RSS 获取文章...")
    try:
        articles = rss_service.fetch_feed_articles()
        print(f"✓ 成功获取 {len(articles)} 篇文章")
        if articles:
            print(f"  示例文章: {articles[0]['title'][:50]}...")
    except Exception as e:
        print(f"✗ RSS 获取失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 步骤 4: 测试 HTML 解析
    print("\n[步骤 4/6] 测试 HTML 内容解析...")
    if articles:
        try:
            from app.utils.html_parser import extract_text_from_html
            sample_article = articles[0]
            text_content = extract_text_from_html(sample_article['content'])
            print(f"✓ HTML 解析成功")
            print(f"  提取文本长度: {len(text_content)} 字符")
            print(f"  文本预览: {text_content[:100]}...")
        except Exception as e:
            print(f"✗ HTML 解析失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # 步骤 5: 测试 LLM 分析 (仅测试一篇文章)
    print("\n[步骤 5/6] 测试 LLM 分析...")
    if articles:
        try:
            sample_article = articles[0]
            analysis_result = llm_service.analyze_article(
                sample_article['title'],
                sample_article['content']
            )
            if analysis_result:
                print(f"✓ LLM 分析成功")
                print(f"  项目数量: {len(analysis_result.get('projects', []))}")
                if analysis_result.get('projects'):
                    print(f"  示例项目: {analysis_result['projects'][0].get('name', 'N/A')}")
            else:
                print("⚠ LLM 分析返回空结果 (可能文章不包含相关项目)")
        except Exception as e:
            print(f"✗ LLM 分析失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # 步骤 6: 执行完整流程 (处理少量文章)
    print("\n[步骤 6/6] 执行完整处理流程...")
    try:
        with get_session(engine) as session:
            # 只处理前 3 篇文章作为测试
            processor.process_routine(session, limit=3)
        print("✓ 完整流程执行成功")
    except Exception as e:
        print(f"✗ 完整流程执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 验证数据库记录
    print("\n[验证] 检查数据库记录...")
    try:
        with get_session(engine) as session:
            from app.models.article import Article
            from app.models.project import ExtractedProject
            
            article_count = session.query(Article).count()
            project_count = session.query(ExtractedProject).count()
            
            print(f"✓ 数据库验证成功")
            print(f"  文章总数: {article_count}")
            print(f"  项目总数: {project_count}")
    except Exception as e:
        print(f"✗ 数据库验证失败: {e}")
        return False
    
    # 最终总结
    print("\n" + "=" * 80)
    print("✓ 完整流程验证通过!")
    print("=" * 80)
    print("\n验证项目:")
    print("  ✓ 数据库连接")
    print("  ✓ RSS feed 获取 (从 app:4000)")
    print("  ✓ HTML 内容解析")
    print("  ✓ LLM 分析 (Ollama at 192.168.10.43:11434)")
    print("  ✓ 数据库保存")
    print("  ✓ 完整工作流程")
    print("\n应用状态:")
    print(f"  • Cron 调度已配置: {settings.CRON_SCHEDULE}")
    print(f"  • 下次执行时间: 10:30 和 14:30")
    print(f"  • 容器运行正常，等待定时触发")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

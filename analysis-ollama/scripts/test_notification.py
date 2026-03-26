"""
测试企业微信通知发送

直接发送一条测试通知到企业微信群
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.notification_service import NotificationService
from app.config.settings import settings
from loguru import logger

def main():
    """发送测试通知"""
    logger.info("=" * 80)
    logger.info("企业微信通知测试")
    logger.info(f"Webhook URL: {settings.WECOM_WEBHOOK_URL}")
    logger.info("=" * 80)
    
    # 创建通知服务
    notification_service = NotificationService(settings.WECOM_WEBHOOK_URL)
    
    # 测试数据
    test_report_data = {
        'company_name': '测试公司',
        'project_name': '测试项目管线',
        'project_stage': 'IND 申报阶段',
        'application_scene': 'CAR-T 细胞治疗',
        'summary': '这是一条测试通知，用于验证企业微信 Webhook 配置是否正确。如果您在企业微信群中看到这条消息，说明通知功能已正常工作。'
    }
    
    test_article_title = '【测试】企业微信通知功能验证'
    test_article_url = 'https://example.com/test-article'
    
    # 发送通知
    logger.info("正在发送测试通知...")
    success = notification_service.send_wecom_message(
        report_data=test_report_data,
        article_title=test_article_title,
        article_url=test_article_url
    )
    
    if success:
        logger.info("✅ 测试通知发送成功！请检查企业微信群是否收到消息。")
        return 0
    else:
        logger.error("❌ 测试通知发送失败！请检查 Webhook URL 配置和网络连接。")
        return 1

if __name__ == "__main__":
    exit(main())

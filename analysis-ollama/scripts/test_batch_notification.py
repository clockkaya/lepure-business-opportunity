import sys
import os

# 将根目录添加到环境变量
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.wecom_notifier import WecomNotifier
from app.core.settings import settings
from loguru import logger

def main():
    logger.info("企业微信批处理表格通知测试")
    notifier = WecomNotifier(settings.WECOM_WEBHOOK_URL)
    
    test_batch = [
        {
            'report_data': {
                'company_name': '诺华制药',
                'province': '上海市',
                'city': '上海市',
                'client_type': '外资大药厂',
                'project_name': 'Kymriah (CAR-T)',
                'project_stage': '商业化阶段',
                'application_scene': 'B细胞淋巴瘤',
                'summary': '今日诺华宣布其首款CAR-T药品的全球生产网络再次扩张，这将加速其在国内的细胞治疗市场渗透率。'
            },
            'article_title': '诺华CAR-T疗法最新进展报道',
            'article_url': 'https://example.com/novartis'
        },
        {
            'report_data': {
                'company_name': '传奇生物',
                'province': '江苏省',
                'city': '南京市',
                'client_type': '国内生物科技先锋',
                'project_name': 'Carvykti',
                'project_stage': '商业化阶段',
                'application_scene': '多发性骨髓瘤',
                'summary': '传奇生物Q3营收逆势高速增长，Carvykti 在全球销售表现抢眼。值得关注后续管线扩展。'
            },
            'article_title': '传奇生物营收高速增长',
            'article_url': 'https://example.com/legend'
        }
    ]
    
    success = notifier.send_batch_message(test_batch)
    if success:
        logger.info("批量测试发送成功，请在企业微信群中查收排版。")
        return 0
    else:
        logger.error("批量发送失败，可能 Webhook URL 配置不正确或失效。")
        return 1

if __name__ == "__main__":
    exit(main())

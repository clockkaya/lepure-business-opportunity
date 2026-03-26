"""
通知服务

负责发送企业微信通知
"""
import requests
from typing import Dict, Any
from loguru import logger


class NotificationService:
    """
    通知服务类
    
    通过企业微信 Webhook 发送通知
    """
    
    def __init__(self, webhook_url: str):
        """
        初始化通知服务
        
        Args:
            webhook_url: 企业微信 Webhook URL
        """
        self.webhook_url = webhook_url
    
    def send_wecom_message(
        self,
        report_data: Dict[str, Any],
        article_title: str,
        article_url: str
    ) -> bool:
        """
        发送企业微信通知（Markdown 格式）
        
        Args:
            report_data: 提取的项目数据
            article_title: 文章标题
            article_url: 文章链接
            
        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        if not self.webhook_url:
            logger.warning("Webhook URL 未配置，跳过企业微信通知")
            return False
        
        company = report_data.get('company_name') or 'N/A'
        project = report_data.get('project_name') or 'N/A'
        stage = report_data.get('project_stage') or 'N/A'
        scene = report_data.get('application_scene') or 'N/A'
        summary = report_data.get('summary') or ''
        
        md_content = f"""**【CGT 行业动态捕捉】**
> **新闻原文**: [{article_title}]({article_url})

**📊 即时情报分析**
- **关联重点企业**: {company}
- **主攻应用场景**: {scene}
- **具体项目管线**: <font color="info">{project}</font>
- **所处临床阶段**: <font color="warning">{stage}</font>

**💡 价值摘要**: 
{summary}
"""
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": md_content
            }
        }
        
        try:
            logger.info(f"正在发送企业微信通知: {project}")
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"成功发送企业微信通知: {project}")
            return True
            
        except requests.exceptions.Timeout:
            logger.error(f"发送企业微信通知超时（10 秒）: {project}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"发送企业微信通知连接错误: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"发送企业微信通知 HTTP 错误: {e.response.status_code} - {e}")
            return False
        except Exception as e:
            logger.error(f"发送企业微信通知时发生意外错误: {e}", exc_info=True)
            return False


# ============================================================================
# 未来扩展：动态 Webhook 路由
# ============================================================================
# 以下功能用于支持根据 feed_id 动态路由到不同的 webhook
# 当前版本使用环境变量配置单个 webhook
# 未来可以启用此功能实现多 webhook 管理
#
# class DynamicNotificationService(NotificationService):
#     """
#     动态通知服务类（未来扩展）
#     
#     根据 feed_id 查找对应的 webhook URL，支持不同公众号推送到不同的企业微信群
#     """
#     
#     def __init__(self, db_session):
#         """
#         初始化动态通知服务
#         
#         Args:
#             db_session: 数据库会话，用于查询 feed 配置
#         """
#         super().__init__("")
#         self.db_session = db_session
#     
#     def send_wecom_message_dynamic(
#         self,
#         report_data: Dict[str, Any],
#         article_title: str,
#         article_url: str,
#         feed_id: str
#     ) -> bool:
#         """
#         发送企业微信通知（动态 webhook 路由）
#         
#         Args:
#             report_data: 提取的项目数据
#             article_title: 文章标题
#             article_url: 文章链接
#             feed_id: 来源 feed ID
#             
#         Returns:
#             bool: 发送成功返回 True，失败返回 False
#         """
#         from models.article import FeedConfig
#         
#         # 查询 feed 配置
#         feed_config = self.db_session.query(FeedConfig).filter(
#             FeedConfig.feed_id == feed_id
#         ).first()
#         
#         if not feed_config:
#             logger.warning(f"未找到 feed 配置: {feed_id}")
#             return False
#         
#         # 使用 feed 特定的 webhook URL
#         self.webhook_url = feed_config.webhook_url
#         
#         return self.send_wecom_message(report_data, article_title, article_url)

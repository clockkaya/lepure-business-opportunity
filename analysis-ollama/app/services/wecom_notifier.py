"""
企业微信通知器

负责发送企业微信 Webhook 通知
"""
from typing import Dict, Any, List

import requests
from loguru import logger


class WecomNotifier:
    """
    企业微信通知器

    通过企业微信 Webhook 发送通知
    """

    def __init__(self, webhook_url: str):
        """
        初始化通知器

        Args:
            webhook_url: 企业微信 Webhook URL
        """
        self.webhook_url = webhook_url

    def send_message(
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

    def send_batch_message(self, batch_data: List[Dict]) -> bool:
        """
        批量发送企业微信通知（通过上传 CSV 表格附件形式）

        Args:
            batch_data: 包含多个项目数据、标题和链接的字典列表

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        if not self.webhook_url:
            logger.warning("Webhook URL 未配置，跳过批处理企业微信通知")
            return False
            
        if not batch_data:
            return True

        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.webhook_url)
        key = parse_qs(parsed_url.query).get('key', [None])[0]
        if not key:
            logger.error("Webhook URL 中缺少 key 参数，无法调用文件上传接口")
            return False
            
        count = len(batch_data)
        import tempfile
        import os

        from datetime import datetime
        time_str = datetime.now().strftime('%y%m%d%H')
        filename = f'cgt_opportunity_{time_str}.xlsx'
        
        fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            wb = Workbook()
            ws = wb.active
            ws.title = "CGT行业动态"
            
            fieldnames = [
                '相关企业', '所在省份', '所在城市', '客户类型', 
                '应用场景', '项目管线', '临床阶段', '价值摘要', '新闻原文'
            ]
            ws.append(fieldnames)

            # 设置表头样式
            header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            header_font = Font(bold=True, color="000000")
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border

            # 写入数据并调整样式
            for item in batch_data:
                report_data = item.get('report_data', {})
                title = item.get('article_title') or '查看原文'
                url = item.get('article_url') or '#'
                
                row = [
                    report_data.get('company_name') or '——',
                    report_data.get('province') or '——',
                    report_data.get('city') or '——',
                    report_data.get('client_type') or '——',
                    report_data.get('application_scene') or '——',
                    report_data.get('project_name') or '——',
                    report_data.get('project_stage') or '——',
                    report_data.get('summary') or '——',
                    title
                ]
                ws.append(row)
                
                # 为该行添加基础样式
                for cell in ws[ws.max_row]:
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
                    
                # 为最后一列单独设置超链接格式
                if url != '#':
                    link_cell = ws.cell(row=ws.max_row, column=9)
                    link_cell.hyperlink = url
                    # 额外附加经典蓝色下划线的超链接视觉效果
                    link_cell.font = Font(color="0563C1", underline="single")

            # 调整各列的列宽，确保摘要等长文本能自动折行阅读
            col_widths = {
                'A': 18, 'B': 10, 'C': 10, 'D': 16, 
                'E': 16, 'F': 22, 'G': 12, 'H': 60, 'I': 45
            }
            for col_letter, width in col_widths.items():
                ws.column_dimensions[col_letter].width = width

            wb.save(temp_path)

            # 上传文件接口
            upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
            with open(temp_path, 'rb') as f:
                files = {'media': (filename, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                logger.info("正在上传附件到企业微信服务器...")
                resp = requests.post(upload_url, files=files, timeout=20)
                resp.raise_for_status()
                result = resp.json()

            if result.get("errcode") != 0:
                logger.error(f"上传附件失败: {result}")
                return False

            media_id = result.get("media_id")

            # 1. 优先发一则指引
            logger.info(f"正在发送企业微信批处理前导通知，共 {count} 条")
            text_payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"**【CGT 行业动态捕捉】 - 本次更新 {count} 条**\n\n数据已整合为表格，详见下方文件 ↓"
                }
            }
            requests.post(self.webhook_url, json=text_payload, timeout=10).raise_for_status()

            # 2. 发送刚才获取的附件媒体消息
            file_payload = {
                "msgtype": "file",
                "file": {
                    "media_id": media_id
                }
            }
            requests.post(self.webhook_url, json=file_payload, timeout=10).raise_for_status()

            logger.info(f"成功发送企业微信批处理 Excel 文件通知")
            return True

        except requests.exceptions.Timeout:
            logger.error("发送企业微信批处理文件通知超时")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"发送企业微信批处理文件 HTTP 错误: {e.response.status_code} - {e}")
            return False
        except Exception as e:
            logger.error(f"发送企业微信批处理通知时发生意外错误: {e}", exc_info=True)
            return False
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass


"""
HTML 解析工具

清洗微信文章 HTML，提取纯文本内容
"""
from bs4 import BeautifulSoup
from loguru import logger


def clean_html(html_content: str) -> str:
    """
    清洗微信文章 HTML，移除样式、广告、脚本，提取纯文本
    
    Args:
        html_content: 原始 HTML 字符串
        
    Returns:
        str: 清洗后的纯文本
        
    处理步骤:
    1. 移除 <script>, <style> 标签
    2. 移除 HTML 标签
    3. 解码 HTML 实体 (&nbsp; -> 空格)
    4. 移除多余的空白字符
    5. 保留段落结构 (\n\n)
    """
    if not html_content:
        logger.warning("提供的 HTML 内容为空")
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 微信文章核心内容通常在 <div class="rich_media_content"> 中
        core_content = soup.find('div', class_='rich_media_content')
        
        if not core_content:
            # 回退到提取所有内容
            logger.debug("未找到 rich_media_content div，使用完整内容")
            core_content = soup
        
        # 移除非信息性元素
        for tag in core_content.find_all(['script', 'style', 'iframe', 'video', 'audio', 'svg', 'img']):
            tag.decompose()
        
        # 提取文本（使用换行符分隔）
        text = core_content.get_text(separator='\n', strip=True)
        
        # 清理：将多个换行符转换为单个或双个换行符
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_txt = '\n'.join(lines)
        
        logger.debug(f"HTML 内容已清洗: {len(html_content)} 字符 -> {len(cleaned_txt)} 字符")
        return cleaned_txt
        
    except Exception as e:
        logger.error(f"清洗 HTML 内容时发生错误: {e}", exc_info=True)
        # 回退返回原始内容
        return html_content

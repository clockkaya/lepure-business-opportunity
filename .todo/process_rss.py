import requests
import html
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import time

# ================= Configuration =================
RSS_URL = 'http://localhost:4000/feeds/MP_WXS_3234367830.atom?mode=fulltext'
OLLAMA_HOST = '192.168.10.43'
OLLAMA_PORT = 11434
OLLAMA_MODEL = 'deepseek-r1:32b'
# =================================================

def fetch_rss_feed(url):
    print(f"[*] 1/4 正在获取 RSS 订阅源: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[-] 获取 RSS 失败: {e}")
        return None

def extract_latest_article(xml_data):
    print("[*] 2/4 正在解析 XML 提取最新文章...")
    try:
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(xml_data)
        
        # 查找最新的文章记录
        entry = root.find('atom:entry', ns)
        if not entry:
            print("[-] 订阅源中暂无文章。")
            return None, None
            
        title_element = entry.find('atom:title', ns)
        title = title_element.text if title_element is not None else "未知标题"
        
        content_element = entry.find('atom:content', ns)
        if content_element is not None:
            html_content = content_element.text or ""
        else:
            summary_element = entry.find('atom:summary', ns)
            html_content = summary_element.text if summary_element is not None else ""
            
        return title, html.unescape(html_content)
    except Exception as e:
        print(f"[-] XML 解析报错: {e}")
        return None, None

def extract_text_with_bs4(html_content):
    print("[*] 3/4 正在使用 BeautifulSoup 处理 HTML，提取纯文本...")
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除 script, style 等无用标签
    for script in soup(["script", "style"]):
        script.decompose()
        
    # 获取纯文本，并去掉多余空行
    lines = soup.get_text(separator='\n', strip=True).splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)

def ask_ollama(title, text_content):
    print(f"[*] 4/4 正在连接 Ollama 服务请求 LLM ({OLLAMA_MODEL})...")
    
    # 避免单次文本过长，截断至前2000字
    truncated_content = text_content[:2000]
    
    prompt = f"请简要总结以下微信公众号文章的核心内容。文章标题是《{title}》。\n\n文章内容：\n{truncated_content}"
    
    url = f'http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate'
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=120)  # LLM 可能比较慢
        response.raise_for_status()
        
        data = response.json()
        print("\n--- AI 响应内容 ---")
        print(data.get('response', '无返回响应'))
        print("-------------------")
        
        total_duration = data.get('total_duration')
        if total_duration:
            print(f"状态: 成功 | 模型耗时: {total_duration / 1e9:.2f}s | 总耗时: {time.time() - start_time:.2f}s\n")
            
    except Exception as e:
        print(f"[-] 请求 Ollama 服务出错: {e}")
        print("建议：")
        print(f"1. 确认目标服务器 {OLLAMA_HOST} 的 Ollama 正在运行。")
        print(f"2. 确认网络可通：ping {OLLAMA_HOST}")

def main():
    # 1. 获取 RSS
    xml_data = fetch_rss_feed(RSS_URL)
    if not xml_data: return
        
    # 2. 提取最近一篇文章的 HTML
    title, html_content = extract_latest_article(xml_data)
    if not title: return
    print(f"[+] 找到最新文章: 《{title}》")
    
    # 3. BS4 提取纯文本
    raw_text = extract_text_with_bs4(html_content)
    print(f"[+] 提取到纯文本长度: {len(raw_text)} 个字符")
    
    if len(raw_text) < 10:
        print("[-] 提取文本过短，可能该文章无正文内容。")
        return
        
    # 4. LLM 总结
    ask_ollama(title, raw_text)

if __name__ == '__main__':
    main()

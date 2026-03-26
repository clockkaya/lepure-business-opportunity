"""
RSS 服务

负责从 WeWe-RSS 获取文章，支持单个和多个 feed
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger


class RSSService:
    """
    RSS 服务类
    
    提供同步和异步的 RSS 文章获取功能
    支持单个 feed 和多个 feed 的并发处理
    """
    
    def __init__(self, wewe_rss_url: str, auth_code: str):
        """
        初始化 RSS 服务
        
        Args:
            wewe_rss_url: WeWe-RSS 服务地址
            auth_code: 认证代码
        """
        self.wewe_rss_url = wewe_rss_url
        self.auth_code = auth_code
    
    def fetch_feed_articles(self, feed_id: str = "all", trigger_update: bool = False, limit: int = 100) -> List[Dict]:
        """
        同步获取 feed 文章（单个 feed）
        
        Args:
            feed_id: Feed ID，默认为 "all" 获取所有文章
            trigger_update: 是否触发 WeWe-RSS 实时抓取微信公众号
                          - True: 触发实时抓取（响应慢，30秒以上）
                          - False: 仅读取数据库（响应快，推荐）
            limit: 返回文章数量限制，默认 100（WeWe-RSS API 默认是 30）
            
        Returns:
            List[Dict]: 文章列表
            [
                {
                    'title': 文章标题,
                    'url': 文章链接,
                    'guid': 文章唯一标识,
                    'published_at': 发布时间,
                    'html': HTML 内容,
                    'feed_id': Feed ID
                },
                ...
            ]
        """
        import requests
        
        # 构建 feed URL
        # limit: 返回文章数量（默认 30，可以增加到 100 或更多）
        # update=true: 触发 WeWe-RSS 立即去微信公众号抓取最新文章
        # update=false 或不传: 仅从 WeWe-RSS 数据库读取
        update_param = "&update=true" if trigger_update else ""
        feed_url = f"{self.wewe_rss_url}/feeds/{feed_id}.atom?mode=fulltext&limit={limit}{update_param}"
        logger.info(f"正在获取 RSS feed: {feed_url}")
        
        try:
            auth_header = {}
            if self.auth_code:
                auth_header['Authorization'] = f"Bearer {self.auth_code}"
            
            response = requests.get(feed_url, headers=auth_header, timeout=30)
            response.raise_for_status()
            
        except requests.exceptions.Timeout:
            logger.error(f"获取 RSS feed 超时（30 秒）")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接 RSS feed 失败: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {e}")
            return []
        except Exception as e:
            logger.error(f"获取 RSS feed 时发生意外错误: {e}", exc_info=True)
            return []
        
        try:
            articles = self._parse_atom_feed(response.content, feed_id)
            logger.info(f"成功获取 {len(articles)} 篇文章 (feed_id={feed_id})")
            return articles
            
        except ET.ParseError as e:
            logger.error(f"XML 解析错误: {e}")
            return []
        except Exception as e:
            logger.error(f"处理 RSS feed 时发生错误: {e}", exc_info=True)
            return []
    
    def _parse_atom_feed(self, content: bytes, feed_id: str) -> List[Dict]:
        """
        解析 Atom feed XML
        
        Args:
            content: XML 内容
            feed_id: Feed ID
            
        Returns:
            List[Dict]: 文章列表
        """
        root = ET.fromstring(content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        articles = []
        for entry in root.findall('atom:entry', namespace):
            title_node = entry.find('atom:title', namespace)
            link_node = entry.find('atom:link', namespace)
            guid_node = entry.find('atom:id', namespace)
            pub_node = entry.find('atom:published', namespace)
            content_node = entry.find('atom:content', namespace)
            
            if title_node is None or link_node is None or guid_node is None:
                logger.warning("跳过缺少必需字段的条目")
                continue
            
            title = title_node.text
            link = link_node.attrib.get('href', '')
            guid = guid_node.text
            published = pub_node.text if pub_node is not None else ""
            
            try:
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            except:
                pub_date = datetime.utcnow()
                logger.warning(f"无法解析发布日期: {title}，使用当前时间")
            
            html_content = content_node.text if content_node is not None else ""
            
            articles.append({
                'title': title,
                'url': link,
                'guid': guid,
                'published_at': pub_date,
                'html': html_content,
                'feed_id': feed_id
            })
        
        return articles
    
    async def fetch_all_feeds_async(self, max_concurrent: int = 5) -> Dict[str, List[Dict]]:
        """
        异步获取所有订阅的公众号文章（多 feed 并发处理）
        
        Args:
            max_concurrent: 最大并发数
            
        Returns:
            Dict[str, List[Dict]]: 按 feed_id 分组的文章列表
            {
                'feed_123': [article1, article2, ...],
                'feed_456': [article3, article4, ...],
            }
        """
        # 步骤 1: 获取所有 feed 列表
        feed_ids = await self._fetch_feed_list_async()
        
        if not feed_ids:
            logger.warning("未找到任何 feed")
            return {}
        
        logger.info(f"找到 {len(feed_ids)} 个 feed，开始并发处理（最大并发数: {max_concurrent}）")
        
        # 步骤 2: 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(feed_id: str):
            async with semaphore:
                return feed_id, await self._fetch_feed_async(feed_id)
        
        # 步骤 3: 并发获取所有 feed 的文章
        tasks = [fetch_with_semaphore(feed_id) for feed_id in feed_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 步骤 4: 整理结果
        feed_articles = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"获取 feed 时发生错误: {result}")
                continue
            
            feed_id, articles = result
            feed_articles[feed_id] = articles
        
        total_articles = sum(len(articles) for articles in feed_articles.values())
        logger.info(f"异步获取完成，共 {total_articles} 篇文章来自 {len(feed_articles)} 个 feed")
        
        return feed_articles
    
    async def _fetch_feed_list_async(self) -> List[str]:
        """
        异步获取所有 feed 列表
        
        Returns:
            List[str]: Feed ID 列表
        """
        # 调用 WeWe-RSS API 获取 feed 列表
        # GET /api/feeds 或 GET /feeds
        api_url = f"{self.wewe_rss_url}/api/feeds"
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.auth_code:
                    headers['Authorization'] = f"Bearer {self.auth_code}"
                
                async with session.get(api_url, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # 根据 WeWe-RSS API 响应格式提取 feed ID
                    # 假设响应格式为: {"feeds": [{"id": "feed_123", "title": "..."}, ...]}
                    # 或者: [{"id": "feed_123", "title": "..."}, ...]
                    if isinstance(data, dict) and 'feeds' in data:
                        feed_ids = [feed['id'] for feed in data['feeds'] if 'id' in feed]
                    elif isinstance(data, list):
                        feed_ids = [feed['id'] for feed in data if 'id' in feed]
                    else:
                        logger.warning(f"未知的 API 响应格式: {data}")
                        feed_ids = []
                    
                    logger.info(f"获取到 {len(feed_ids)} 个 feed")
                    return feed_ids
                    
        except asyncio.TimeoutError:
            logger.error(f"获取 feed 列表超时（30 秒）")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"获取 feed 列表失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取 feed 列表时发生意外错误: {e}", exc_info=True)
            return []
    
    async def _fetch_feed_async(self, feed_id: str) -> List[Dict]:
        """
        异步获取单个 feed 的文章
        
        Args:
            feed_id: Feed ID
            
        Returns:
            List[Dict]: 文章列表
        """
        feed_url = f"{self.wewe_rss_url}/feeds/{feed_id}.atom?mode=fulltext&update=true"
        logger.debug(f"正在异步获取 feed: {feed_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.auth_code:
                    headers['Authorization'] = f"Bearer {self.auth_code}"
                
                async with session.get(feed_url, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    content = await response.read()
                    
                    articles = self._parse_atom_feed(content, feed_id)
                    logger.debug(f"成功获取 {len(articles)} 篇文章 (feed_id={feed_id})")
                    return articles
                    
        except asyncio.TimeoutError:
            logger.error(f"获取 feed 超时（30 秒）: {feed_id}")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"获取 feed 失败 ({feed_id}): {e}")
            return []
        except Exception as e:
            logger.error(f"处理 feed 时发生错误 ({feed_id}): {e}", exc_info=True)
            return []
    
    async def process_feed_async(self, feed_id: str, process_callback):
        """
        异步处理单个 feed（获取文章并调用回调函数）
        
        Args:
            feed_id: Feed ID
            process_callback: 处理回调函数，接收文章列表作为参数
        """
        articles = await self._fetch_feed_async(feed_id)
        
        if articles:
            await process_callback(feed_id, articles)

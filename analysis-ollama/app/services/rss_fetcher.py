"""
RSS 采集器

负责从 WeWe-RSS 获取文章，支持单个和多个 feed
"""
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict

import aiohttp
import requests
from loguru import logger


class RSSFetcher:
    """
    RSS 采集器

    提供同步和异步的 RSS 文章获取功能
    支持单个 feed 和多个 feed 的并发处理
    """

    def __init__(self, wewe_rss_url: str, auth_code: str, timeout: int = 120, batch_size: int = 20):
        """
        初始化 RSS 采集器

        Args:
            wewe_rss_url: WeWe-RSS 服务地址
            auth_code: 认证代码
            timeout: 单次 HTTP 请求超时秒数，默认 120 秒
            batch_size: 每批次请求的文章数量，默认 20 篇
        """
        self.wewe_rss_url = wewe_rss_url
        self.auth_code = auth_code
        self.timeout = timeout
        self.batch_size = batch_size

    def fetch_feed_articles(self, feed_id: str = "all", trigger_update: bool = False, limit: int = 100) -> List[Dict]:
        """
        同步获取 feed 文章（单个 feed），分批循环请求

        WeWe-RSS 分页参数：limit=N&page=P（page 从 1 开始）
        trigger_update 会触发 WeWe-RSS 异步抓取，但不影响本次返回结果（fire-and-forget）

        Args:
            feed_id: Feed ID，默认为 "all" 获取所有文章
            trigger_update: 是否触发 WeWe-RSS 异步更新（不影响本次返回）
            limit: 返回文章数量上限，默认 100
        Returns:
            List[Dict]: 文章列表
        """
        all_articles = []
        page = 1

        while len(all_articles) < limit:
            batch_limit = min(self.batch_size, limit - len(all_articles))
            update_param = "&update=true" if trigger_update else ""
            feed_url = (
                f"{self.wewe_rss_url}/feeds/{feed_id}.atom"
                f"?mode=fulltext&limit={batch_limit}&page={page}{update_param}"
            )
            logger.info(f"正在获取 RSS feed 批次 page={page}, limit={batch_limit}: {feed_url}")

            try:
                auth_header = {}
                if self.auth_code:
                    auth_header['Authorization'] = f"Bearer {self.auth_code}"

                response = requests.get(feed_url, headers=auth_header, timeout=self.timeout)
                response.raise_for_status()

            except requests.exceptions.Timeout:
                logger.error(f"获取 RSS feed 超时（{self.timeout} 秒），page={page}")
                break
            except requests.exceptions.ConnectionError as e:
                logger.error(f"连接 RSS feed 失败: {e}")
                break
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP 错误: {e.response.status_code} - {e}")
                break
            except Exception as e:
                logger.error(f"获取 RSS feed 时发生意外错误: {e}", exc_info=True)
                break

            try:
                batch_articles = self._parse_atom_feed(response.content, feed_id)
                logger.info(f"批次 page={page} 获取 {len(batch_articles)} 篇文章")
                all_articles.extend(batch_articles)

                # 返回数量少于请求数量，说明已无更多数据
                if len(batch_articles) < batch_limit:
                    break

                page += 1

            except ET.ParseError as e:
                logger.error(f"XML 解析错误: {e}")
                break
            except Exception as e:
                logger.error(f"处理 RSS feed 时发生错误: {e}", exc_info=True)
                break

        logger.info(f"共获取 {len(all_articles)} 篇文章 (feed_id={feed_id})")
        return all_articles

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
            except Exception:
                pub_date = datetime.now(timezone.utc)
                # 使用 debug 级别，避免大量不规范 RSS 的干扰
                logger.debug(f"无法解析发布日期: {title}，已使用当前时间")

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
        """
        feed_ids = await self._fetch_feed_list_async()

        if not feed_ids:
            logger.warning("未找到任何 feed")
            return {}

        logger.info(f"找到 {len(feed_ids)} 个 feed，开始并发处理（最大并发数: {max_concurrent}）")

        semaphore = asyncio.Semaphore(max_concurrent)

        # 复用单个 ClientSession（CR-08 修复）
        async with aiohttp.ClientSession() as client_session:
            async def fetch_with_semaphore(fid: str):
                async with semaphore:
                    return fid, await self._fetch_feed_async(fid, client_session)

            tasks = [fetch_with_semaphore(fid) for fid in feed_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

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
        api_url = f"{self.wewe_rss_url}/api/feeds"

        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {}
                if self.auth_code:
                    headers['Authorization'] = f"Bearer {self.auth_code}"

                async with session.get(api_url, headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()

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
            logger.error(f"获取 feed 列表超时（{self.timeout} 秒）")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"获取 feed 列表失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取 feed 列表时发生意外错误: {e}", exc_info=True)
            return []

    async def _fetch_feed_async(self, feed_id: str, client_session: aiohttp.ClientSession) -> List[Dict]:
        """
        异步获取单个 feed 的文章

        Args:
            feed_id: Feed ID
            client_session: 复用的 aiohttp ClientSession

        Returns:
            List[Dict]: 文章列表
        """
        feed_url = f"{self.wewe_rss_url}/feeds/{feed_id}.atom?mode=fulltext"
        logger.debug(f"正在异步获取 feed: {feed_id}")

        try:
            headers = {}
            if self.auth_code:
                headers['Authorization'] = f"Bearer {self.auth_code}"

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with client_session.get(feed_url, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                content = await response.read()

                articles = self._parse_atom_feed(content, feed_id)
                logger.debug(f"成功获取 {len(articles)} 篇文章 (feed_id={feed_id})")
                return articles

        except asyncio.TimeoutError:
            logger.error(f"获取 feed 超时（{self.timeout} 秒）: {feed_id}")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"获取 feed 失败 ({feed_id}): {e}")
            return []
        except Exception as e:
            logger.error(f"处理 feed 时发生错误 ({feed_id}): {e}", exc_info=True)
            return []

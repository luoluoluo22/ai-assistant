from typing import Dict, List, Optional, Any
import logging
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import json
import time
from datetime import datetime
from app.core.config import settings
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class WebBrowserTool(BaseTool):
    """网页浏览工具，用于搜索和提取网页内容"""
    
    name: str = "web_browser"
    description: str = """网页浏览工具，支持以下操作：
    1. 搜索网页内容 (search)
    2. 提取网页内容 (extract)
    3. 搜索并提取内容 (search_and_extract)
    """
    
    # 添加字段定义
    max_retries: int = 3
    retry_delay: int = 2
    timeout: Optional[aiohttp.ClientTimeout] = None
    headers: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    serpapi_key: Optional[str] = None
    search_url: str = "https://serpapi.com/search.json"
    monthly_limit: int = 100
    search_count: int = 0
    last_reset: datetime = datetime.now()
    cache: Dict[str, Dict] = {}
    cache_ttl: int = 3600
    
    def __init__(self):
        """Initialize the tool."""
        super().__init__()
        self.timeout = aiohttp.ClientTimeout(total=60, connect=20)
        self.serpapi_key = settings.SERPAPI_KEY
        if not self.serpapi_key:
            logger.error("SERPAPI_KEY 未设置")
        logger.info("WebBrowserTool 初始化完成")

    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get the parameters schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "description": "操作类型（search/extract/search_and_extract）",
                "enum": ["search", "extract", "search_and_extract"],
                "required": True
            },
            "query": {
                "type": "string",
                "description": "搜索关键词",
                "required": False
            },
            "url": {
                "type": "string",
                "description": "要提取内容的网页 URL",
                "required": False
            },
            "num_results": {
                "type": "integer",
                "description": "返回的搜索结果数量",
                "required": False,
                "default": 5
            }
        }
    
    @property
    def examples(self) -> List[str]:
        """Get example usages of the tool."""
        return [
            "搜索 Python 相关文档",
            "提取指定网页的内容",
            "搜索并提取多个网页的内容"
        ]

    def _check_and_reset_counter(self):
        """检查并在需要时重置计数器"""
        now = datetime.now()
        if now.month != self.last_reset.month:
            self.search_count = 0
            self.last_reset = now

    def _check_cache(self, query: str) -> Optional[List[Dict]]:
        """检查缓存中是否有有效的搜索结果"""
        if query in self.cache:
            cache_data = self.cache[query]
            if time.time() - cache_data['timestamp'] < self.cache_ttl:
                return cache_data['results']
        return None

    def _update_cache(self, query: str, results: List[Dict]):
        """更新缓存"""
        self.cache[query] = {
            'results': results,
            'timestamp': time.time()
        }

    async def _retry_operation(self, operation_func, *args, **kwargs):
        """使用重试机制执行操作"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await operation_func(*args, **kwargs)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:  # 如果不是最后一次尝试
                    wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(f"网络错误，{wait_time}秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"操作在 {self.max_retries} 次尝试后仍然失败: {str(e)}")
            except Exception as e:
                logger.error(f"未预期的错误: {str(e)}")
                raise
        raise last_error

    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """执行网页浏览操作
        
        Args:
            operation: 操作类型 (search/extract/search_and_extract)
            **kwargs: 操作相关的参数
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        operations = {
            'search': self.search,
            'extract': self.extract_content,
            'search_and_extract': self.search_and_extract
        }
        
        if operation not in operations:
            return {
                'success': False,
                'message': f'不支持的操作类型: {operation}'
            }
            
        try:
            result = await operations[operation](**kwargs)
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            error_msg = f"执行 {operation} 操作失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }

    async def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """搜索网页
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果列表，每个结果包含标题、URL和摘要
        """
        try:
            # 检查 API 密钥
            if not self.serpapi_key:
                raise ValueError("SERPAPI_KEY 未设置，无法执行搜索")

            # 检查缓存
            cached_results = self._check_cache(query)
            if cached_results:
                logger.info("使用缓存的搜索结果")
                return cached_results[:num_results]
            
            # 检查搜索限制
            self._check_and_reset_counter()
            if self.search_count >= self.monthly_limit:
                logger.warning("已达到本月搜索限制")
                return []
            
            params = {
                'q': query,
                'num': num_results,
                'api_key': self.serpapi_key,
                'engine': 'google'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                try:
                    async with session.get(self.search_url, params=params, ssl=False) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise aiohttp.ClientError(f"搜索请求失败: HTTP {response.status}, {error_text}")
                            
                        data = await response.json()
                        
                        if 'error' in data:
                            raise Exception(f"SerpApi 错误: {data['error']}")
                        
                        # 增加搜索计数
                        self.search_count += 1
                        
                        results = []
                        for item in data.get('organic_results', [])[:num_results]:
                            results.append({
                                'title': item.get('title', ''),
                                'url': item.get('link', ''),
                                'snippet': item.get('snippet', '')
                            })
                        
                        # 更新缓存
                        self._update_cache(query, results)
                        
                        return results
                except asyncio.TimeoutError:
                    logger.error(f"搜索超时: {query}")
                    raise TimeoutError(f"搜索请求超时，请稍后重试")
                except aiohttp.ClientError as e:
                    logger.error(f"网络错误: {str(e)}")
                    raise ConnectionError(f"网络连接错误: {str(e)}")
                    
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise

    async def extract_content(self, url: str) -> Optional[Dict]:
        """提取网页内容
        
        Args:
            url: 网页URL
            
        Returns:
            Optional[Dict]: 提取的内容，包含标题和正文
        """
        try:
            logger.info(f"开始提取内容: {url}")
            connector = aiohttp.TCPConnector(ssl=False, force_close=True)  # 禁用 SSL 验证，强制关闭连接
            
            # 使用重试机制
            for attempt in range(self.max_retries):
                try:
                    async with aiohttp.ClientSession(
                        headers=self.headers,
                        timeout=self.timeout,
                        connector=connector
                    ) as session:
                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.error(f"HTTP错误: {response.status}, URL: {url}")
                                if attempt < self.max_retries - 1:
                                    wait_time = self.retry_delay * (2 ** attempt)
                                    logger.info(f"等待 {wait_time} 秒后重试...")
                                    await asyncio.sleep(wait_time)
                                    continue
                                return None
                                
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # 提取标题
                            title = ''
                            if soup.title:
                                title = soup.title.string
                            elif soup.find('h1'):
                                title = soup.find('h1').get_text().strip()
                            
                            # 移除不需要的元素
                            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                                tag.decompose()
                            
                            # 提取正文
                            paragraphs = []
                            
                            # 首先尝试查找文章主体
                            main_content = soup.find(['article', 'main', 'div[role="main"]'])
                            if not main_content:
                                main_content = soup
                            
                            # 提取段落
                            for p in main_content.find_all(['p', 'article', 'section', 'div']):
                                text = p.get_text().strip()
                                # 过滤无效内容
                                if text and len(text) > 50 and not any(x in text.lower() for x in ['copyright', '版权所有']):
                                    paragraphs.append(text)
                            
                            if not paragraphs:
                                # 如果没有找到合适的段落，尝试其他选择器
                                for p in main_content.find_all(text=True):
                                    text = p.strip()
                                    if text and len(text) > 50:
                                        paragraphs.append(text)
                            
                            if paragraphs:
                                content = '\n\n'.join(paragraphs[:10])  # 限制段落数量
                                logger.info(f"成功提取内容，标题长度: {len(title)}, 内容长度: {len(content)}")
                                return {
                                    'title': title,
                                    'content': content
                                }
                            else:
                                logger.warning(f"未找到有效内容: {url}")
                                return None
                                
                except asyncio.TimeoutError:
                    logger.error(f"提取内容超时: {url}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None
                except aiohttp.ClientError as e:
                    logger.error(f"提取内容网络错误: {url}, {str(e)}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    return None
                    
        except Exception as e:
            logger.error(f"提取内容失败: {url}, {str(e)}", exc_info=True)
            return None

    async def search_and_extract(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """搜索并提取网页内容
        
        Args:
            query: 搜索关键词
            num_results: 处理的搜索结果数量
            
        Returns:
            Dict[str, Any]: 汇总的搜索和提取结果
        """
        try:
            logger.info(f"开始执行搜索和提取操作: query={query}, num_results={num_results}")
            
            # 搜索网页
            search_results = await self.search(query, num_results)
            if not search_results:
                logger.warning("搜索未返回任何结果")
                return {
                    'query': query,
                    'results': [],
                    'summary': '未找到相关结果'
                }
            
            logger.info(f"搜索返回 {len(search_results)} 个结果，开始并发提取内容")
            
            # 并发提取内容
            async def process_url(result):
                try:
                    logger.info(f"正在处理: {result['url']}")
                    content = await self.extract_content(result['url'])
                    if content:
                        return {
                            'title': result['title'],
                            'url': result['url'],
                            'snippet': result['snippet'],
                            'content': content['content']
                        }
                    else:
                        logger.warning(f"无法提取内容: {result['url']}")
                        return {
                            'title': result['title'],
                            'url': result['url'],
                            'snippet': result['snippet'],
                            'content': '无法提取内容'
                        }
                except Exception as e:
                    logger.error(f"处理 URL {result['url']} 时失败: {str(e)}")
                    return {
                        'title': result['title'],
                        'url': result['url'],
                        'snippet': result['snippet'],
                        'content': f'处理失败: {str(e)}'
                    }

            # 使用 gather 并发处理所有 URL
            tasks = [process_url(result) for result in search_results]
            extracted_contents = await asyncio.gather(*tasks)
            
            # 过滤掉空结果
            extracted_contents = [content for content in extracted_contents if content['content']]
            
            # 生成摘要
            success_count = len([c for c in extracted_contents if c['content'] != '无法提取内容' and not c['content'].startswith('处理失败')])
            summary = f"找到 {len(search_results)} 个相关结果，成功提取 {success_count} 个网页的内容。"
            
            if self.search_count >= self.monthly_limit:
                summary += " 警告：已达到本月搜索限制。"
            else:
                summary += f" 本月剩余搜索次数：{self.monthly_limit - self.search_count}。"
            
            logger.info(f"搜索和提取完成: {summary}")
            
            return {
                'query': query,
                'results': extracted_contents,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"搜索和提取失败: {str(e)}", exc_info=True)
            return {
                'query': query,
                'results': [],
                'summary': f'处理失败: {str(e)}'
            }

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """运行工具的方法（必需）"""
        # 这个方法是为了满足 BaseTool 的要求
        # 实际的执行逻辑在 execute 方法中
        raise NotImplementedError("请使用 execute 方法代替")

    def get_tool_definition(self) -> Dict[str, Any]:
        """获取工具定义"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples
        } 
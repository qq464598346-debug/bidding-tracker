"""
爬虫基类 - 定义统一接口和公共方法
"""
import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from fake_useragent import UserAgent
from loguru import logger


class BaseCrawler(ABC):
    """
    所有爬虫的基类
    
    子类必须实现:
    - crawl() 方法: 执行采集并返回BiddingItem列表
    - source_name 属性: 数据源标识名
    
    基类提供:
    - HTTP请求封装（带反爬处理）
    - 随机延迟机制
    - 请求重试逻辑
    - 浏览器自动化支持
    """

    # 子类必须定义
    SOURCE_NAME: str = ""
    SOURCE_URL: str = ""

    def __init__(self, settings):
        self.settings = settings
        self.ua = UserAgent()
        
        # HTTP客户端配置
        self.client_config = {
            'timeout': 30.0,
            'follow_redirects': True,
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
        }

    def _get_headers(self, extra: dict = None) -> dict:
        """生成随机请求头"""
        headers = {**self.client_config['headers']}
        headers['User-Agent'] = self.ua.random
        if extra:
            headers.update(extra)
        return headers

    async def _fetch(
        self, 
        url: str, 
        method: str = 'GET', 
        params: dict = None,
        data: dict = None,
        extra_headers: dict = None,
        retry_times: int = 3
    ) -> Optional[str]:
        """
        异步HTTP请求，带重试和反爬
        
        Returns: 响应文本内容 或 None(失败)
        """
        for attempt in range(retry_times):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        headers=self._get_headers(extra_headers),
                        timeout=httpx.Timeout(self.settings.BROWSER_TIMEOUT / 1000)
                    )
                    
                    response.raise_for_status()
                    return response.text
                    
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP错误 [{e.response.status_code}] {url}")
                if e.response.status_code in (403, 429):
                    await asyncio.sleep(random.uniform(5, 15))  # 被限流时等待更久
                elif e.response.status_code >= 500:
                    await asyncio.sleep(random.uniform(2, 5))
                else:
                    return None
                    
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                logger.warning(f"连接失败 (尝试{attempt+1}/{retry_times}): {e}")
                
            except Exception as e:
                logger.error(f"请求异常: {e}")
            
            if attempt < retry_times - 1:
                delay = random.uniform(self.settings.CRAWL_DELAY_MIN, 
                                       self.settings.CRAWL_DELAY_MAX * (attempt + 1))
                await asyncio.sleep(delay)

        return None

    async def _delay(self):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(self.settings.CRAWL_DELAY_MIN, 
                               self.settings.CRAWL_DELAY_MAX)
        await asyncio.sleep(delay)

    @abstractmethod
    async def crawl(self, keywords: list = None, limit: int = None) -> List['BiddingItem']:
        """
        执行数据采集
        
        Args:
            keywords: 搜索关键词列表
            limit: 最大返回条数
        
        Returns:
            BiddingItem 列表
        """
        pass

    async def run(self, keywords: list = None, limit: int = None) -> dict:
        """
        运行爬虫并记录日志
        
        Returns: {"source": str, "count": int, "items": list}
        """
        from datetime import datetime
        
        start_time = time.time()
        started_at = datetime.now().isoformat()
        
        try:
            limit = limit or self.settings.MAX_ITEMS_PER_SOURCE
            items = await self.crawl(keywords=keywords, limit=limit)
            
            duration = time.time() - start_time
            
            result = {
                "source": self.SOURCE_NAME,
                "status": "success",
                "count": len(items),
                "items": items,
                "started_at": started_at,
                "duration": round(duration, 2)
            }
            
            logger.info(f"✅ [{self.SOURCE_NAME}] 采集完成: {len(items)}条, 耗时{duration:.1f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [{self.SOURCE_NAME}] 采集失败: {e}")
            
            import traceback
            traceback.print_exc()
            
            return {
                "source": self.SOURCE_NAME,
                "status": "error",
                "error": str(e),
                "count": 0,
                "items": [],
                "started_at": started_at,
                "duration": round(duration, 2)
            }

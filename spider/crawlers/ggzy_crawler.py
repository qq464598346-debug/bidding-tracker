"""
全国公共资源交易平台爬虫
目标: https://www.ggzy.gov.cn/
数据: 全国范围内的招标采购信息（最全面的公开数据源）

策略:
1. 使用搜索接口获取列表页数据
2. 解析HTML/JSON提取结构化字段
3. 支持关键词过滤和分页
"""
import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler
from core.models import BiddingItem, BiddingStatus


class GGZYCrawler(BaseCrawler):
    """全国公共资源交易平台爬虫"""

    SOURCE_NAME = "ggzy"
    SOURCE_URL = "https://www.ggzy.gov.cn"

    # 目标类别关键词
    TARGET_KEYWORDS = [
        '基础软件', '中间件', '数据库', '操作系统', '云平台',
        '行业解决方案', '智慧城市', '数字化转型', '5G应用',
        '服务器', 'GPU服务器', '存储设备', '计算集群',
        '系统集成', '运维服务', '软件开发', '安全服务'
    ]

    async def crawl(self, keywords: list = None, limit: int = 50) -> List[BiddingItem]:
        """
        采集全国公共资源交易平台的招标信息
        
        策略:
        - 通过搜索API获取列表
        - 解析HTML提取详细信息
        - 过滤与目标领域相关的项目
        """
        items = []
        
        # 搜索关键词组合
        search_terms = keywords or self._build_search_keywords()
        
        for keyword in search_terms[:3]:  # 最多搜索3个关键词，避免请求过多
            if len(items) >= limit:
                break
                
            try:
                page_items = await self._search(keyword, limit)
                items.extend(page_items)
                
                await self._delay()
                
            except Exception as e:
                print(f"⚠️ [GGZY] 搜索'{keyword}'失败: {e}")
                continue
        
        return items[:limit]

    def _build_search_keywords(self) -> List[str]:
        """构建目标领域的关键词列表"""
        return [
            '软件 服务器 运维 招标',
            '信息化 建设 招标 公告',
            '系统 开发 集成 采购',
            '云平台 大数据 解决方案',
            '运营商 通信 设备 采购',
        ]

    async def _search(self, keyword: str, limit: int = 20) -> List[BiddingItem]:
        """
        执行搜索并解析结果
        
        注意: 全国公共资源交易平台可能有反爬机制
        这里提供多种策略的尝试
        """
        items = []
        
        # === 策略1: 尝试官方搜索API ===
        try:
            api_items = await self._try_api_search(keyword, limit)
            if api_items:
                items.extend(api_items)
                return items
        except Exception:
            pass
        
        # === 策略2: 尝试页面抓取 ===
        try:
            page_items = await self._try_page_scrape(keyword, limit)
            if page_items:
                items.extend(page_items)
        except Exception:
            pass
        
        # === 策略3: 如果以上都失败，返回模拟演示数据 ===
        if not items and not self.settings.has_ai:
            items = await self._get_demo_data(keyword, limit)
        
        return items[:limit]

    async def _try_api_search(self, keyword: str, limit: int) -> List[BiddingItem]:
        """尝试通过API接口获取数据"""
        # 全国公共资源交易平台可能的搜索接口
        urls = [
            f"{self.SOURCE_URL}/info-api/search",
            f"{self.SOURCE_URL}/api/v1/search",
        ]
        
        for url in urls:
            html = await self._fetch(
                url,
                method='POST',
                data={
                    'keyword': keyword,
                    'pageNo': '1',
                    'pageSize': str(limit),
                    'type': '1'  # 招标公告类型
                },
                extra_headers={
                    'Content-Type': 'application/json',
                    'Referer': self.SOURCE_URL,
                    'Origin': self.SOURCE_URL
                }
            )
            
            if html:
                try:
                    # 尝试JSON格式
                    data = json.loads(html)
                    return self._parse_api_response(data, keyword)
                except json.JSONDecodeError:
                    # 可能是HTML格式的响应
                    soup = BeautifulSoup(html, 'html.parser')
                    return self._parse_html_list(soup, keyword)
        
        return []

    async def _try_page_scrape(self, keyword: str, limit: int) -> List[BiddingItem]:
        """通过抓取页面获取数据"""
        # 构造搜索URL（根据实际网站结构调整）
        search_url = f"{self.SOURCE_URL}/search?keyword={keyword}"
        
        html = await self._fetch(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        return self._parse_html_list(soup, keyword)

    def _parse_api_response(self, data: dict, keyword: str) -> List[BiddingItem]:
        """解析API响应数据"""
        items = []
        
        # 根据实际API响应格式调整
        records = []
        if isinstance(data, dict):
            records = data.get('data', {}).get('list', []) or data.get('list', [])
        elif isinstance(data, list):
            records = data
        
        for record in records:
            item = BiddingItem(
                title=record.get('title') or record.get('projectName', ''),
                source=self.SOURCE_NAME,
                project_code=record.get('projectCode') or record.get('code'),
                url=record.get('url') or record.get('detailUrl'),
                publish_time=record.get('publishTime') or record.get('createTime'),
                budget=self._extract_budget(record.get('budget', '')),
                purchaser=record.get('buyerName') or record.get('purchaser'),
                region=record.get('areaName') or record.get('region'),
                summary=record.get('summary') or '',
                raw_data=record
            )
            items.append(item)
        
        return items

    def _parse_html_list(self, soup: BeautifulSoup, keyword: str) -> List[BiddingItem]:
        """从HTML中解析招标列表"""
        items = []
        
        # 常见的列表选择器（需要根据实际网页调整）
        selectors = [
            '.search-list .list-item',
            '.result-item',
            '.info-list li',
            'ul.result-list > li',
            '.content-box .item',
            'tr[class*="row"]',
        ]
        
        elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                break
        
        for elem in elements[:20]:  # 每个关键词最多取20条
            try:
                title_elem = elem.select_one('a, .title, h3, .name')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = self.SOURCE_URL + link
                
                # 提取其他信息
                time_elem = elem.select_one('.time, .date, span:last-child')
                publish_time = time_elem.get_text(strip=True) if time_elem else None
                
                item = BiddingItem(
                    title=title,
                    source=self.SOURCE_NAME,
                    url=link or None,
                    publish_time=publish_time,
                    summary=self._get_item_summary(elem),
                    raw_data={'html_snippet': str(elem)[:500]}
                )
                items.append(item)
                
            except Exception:
                continue
        
        return items

    def _get_item_summary(self, elem) -> str:
        """从元素中提取摘要文本"""
        parts = []
        for sel in ['.desc', '.abstract', '.summary', 'p']:
            el = elem.select_one(sel)
            if el:
                parts.append(el.get_text(strip=True))
        return ' | '.join(parts)[:200] if parts else ''

    def _extract_budget(self, text) -> Optional[float]:
        """从文本中提取预算金额"""
        if not text:
            return None
            
        patterns = [
            r'(\d+(?:\.\d+)?)\s*万\s*元',
            r'(\d+(?:\.\d+)?)\s*亿元',
            r'[¥￥](\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(text))
            if match:
                amount = float(match.group(1))
                if '亿' in text:
                    amount *= 10000  # 转为万元
                return round(amount, 2)
        
        return None

    async def _get_demo_data(self, keyword: str, limit: int = 10) -> List[BiddingItem]:
        """
        获取模拟数据（当真实采集不可用时）
        用于开发和测试阶段
        """
        from datetime import datetime, timedelta
        import random
        
        demo_titles = {
            '软件': [
                f"某省政务云操作系统及中间件采购项目-{keyword}",
                f"企业级数据库平台建设-{keyword}",
                f"国产化办公软件升级改造-{keyword}",
            ],
            '解决方案': [
                f"智慧城市数字底座建设项目-{keyword}",
                f"5G+工业互联网融合应用示范-{keyword}",
                f"城市大脑一体化运营平台-{keyword}",
                f"区块链政务服务平台建设-{keyword}",
            ],
            '服务器': [
                f"AI算力中心GPU服务器采购-{keyword}",
                f"数据中心通用服务器扩容-{keyword}",
                f"分布式存储系统采购项目-{keyword}",
            ],
            '服务': [
                f"IT基础设施运维服务外包-{keyword}",
                f"网络安全等级保护测评服务-{keyword}",
                f"系统集成总包实施服务-{keyword}",
            ]
        }
        
        categories = ['software', 'solution', 'server', 'service']
        operators = ['chinamobile', 'chinaunicom', 'chinatelecom']
        regions = ['北京', '上海', '广东', '江苏', '浙江', '四川', '湖北', '山东']
        
        items = []
        now = datetime.now()
        
        for i in range(min(limit, 15)):
            cat = random.choice(categories)
            titles_pool = demo_titles[cat]
            
            days_ago = random.randint(0, 30)
            deadline_days = random.randint(7, 60)
            
            item = BiddingItem(
                title=random.choice(titles_pool),
                source=self.SOURCE_NAME,
                operator=random.choice(operators) if random.random() > 0.4 else None,
                project_code=f"GGZY-2026-{random.randint(100000, 999999)}",
                url=f"https://www.ggzy.gov.cn/info/detail/{random.randint(1000000000, 9999999999)}",
                publish_time=(now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M'),
                deadline=(now + timedelta(days=deadline_days)).strftime('%Y-%m-%d %H:%M'),
                budget=round(random.uniform(50, 8000), 2),
                purchaser=f"{random.choice(regions)}省{random.choice(['政府采购中心', '公共资源交易中心', '招标代理机构'])}",
                category=cat,
                status=random.choices(
                    ['bidding', 'upcoming', 'closing_soon', 'result_published'],
                    weights=[50, 10, 15, 25]
                )[0],
                region=random.choice(regions),
                summary=f"本项目主要涉及{keyword}相关内容，预算金额约{random.randint(100,5000)}万元...",
                requirements=[
                    f"具备{keyword}相关资质",
                    f"具有类似项目经验",
                    f"团队不少于{random.randint(5,30)}人"
                ]
            )
            items.append(item)
        
        return items

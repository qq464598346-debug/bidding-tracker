"""
中国电信阳光采购网爬虫
目标: https://caigou.chinatelecom.com.cn/

特点:
- 中国电信集中采购平台
- 供应商统一合作门户
- 支持招标公告和采购结果公示

策略:
1. 分析网站API接口
2. 使用浏览器自动化作为备选
3. 解析并标准化数据输出
"""
import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler
from core.models import BiddingItem, BiddingStatus, Operator


class ChinaTelecomCrawler(BaseCrawler):
    """中国电信阳光采购网爬虫"""

    SOURCE_NAME = "chinatelecom"
    SOURCE_URL = "https://caigou.chinatelecom.com.cn"

    # 可能的API路径
    API_PATHS = [
        "/MSS-PORTAL/public/listNotice",
        "/api/announcement/list",
        "/mss-portlet/notice/list",
        "/public/notice/query",
    ]

    async def crawl(self, keywords: list = None, limit: int = 50) -> List[BiddingItem]:
        """
        采集中国电信的招标信息
        """
        items = []

        try:
            # 策略1: API接口采集
            items = await self._api_crawl(limit)

        except Exception as e:
            print(f"⚠️ [中国电信] API采集失败: {e}")

            try:
                # 策略2: 浏览器自动化
                items = await self._browser_crawl(limit)
            except Exception as e2:
                print(f"⚠️ [中国电信] 浏览器采集失败: {e2}")
                items = await self._get_demo_data(keywords, limit)

        return items[:limit]

    async def _api_crawl(self, limit: int) -> List[BiddingItem]:
        """API接口方式采集"""
        items = []

        for api_path in self.API_PATHS:
            url = f"{self.SOURCE_URL}{api_path}"

            configs = [
                {
                    'method': 'GET',
                    'params': {
                        'currentPage': '1',
                        'pageSize': str(limit * 2),
                        'noticeType': '1',  # 招标公告
                        'searchKey': '',
                    }
                },
                {
                    'method': 'POST',
                    'data': {
                        'pageNo': 1,
                        'pageSize': limit * 2,
                        'keyword': '',
                        'category': ''
                    }
                },
            ]

            for config in configs:
                html = await self._fetch(
                    url,
                    method=config['method'],
                    params=config.get('params'),
                    data=config.get('data'),
                    extra_headers={
                        'Referer': self.SOURCE_URL,
                        'Origin': self.SOURCE_URL,
                        'Accept': '*/*',
                    }
                )

                if html and len(html) > 20:
                    parsed = self._parse_response(html)
                    if parsed:
                        items.extend(parsed)
                        break

            if items:
                break
            await self._delay()

        return items

    def _parse_response(self, content: str) -> List[BiddingItem]:
        """解析响应"""
        try:
            data = json.loads(content)
            return self._parse_json(data)
        except (json.JSONDecodeError, TypeError):
            pass
        
        soup = BeautifulSoup(content, 'html.parser')
        return self._parse_html(soup)

    def _parse_json(self, data) -> List[BiddingItem]:
        """解析JSON响应"""
        items = []
        
        records = []
        if isinstance(data, dict):
            records = (data.get('list') or data.get('rows') or 
                      data.get('records') or data.get('notices') or
                      data.get('data', {}).get('list') or [])
        elif isinstance(data, list):
            records = data

        for r in records:
            item = BiddingItem(
                title=(r.get('title') or r.get('noticeTitle') or 
                       r.get('projectName') or r.get('name') or ''),
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_TELECOM.value,

                project_code=r.get('projectCode') or r.get('noticeNo'),
                url=self._build_url(r),

                publish_time=(r.get('publishDate') or r.get('createTime') or
                             r.get('openTime')),
                deadline=r.get('bidDeadline') or r.get('endTime'),

                budget=self._extract_budget(r.get('budget') or r.get('amount')),
                purchaser=r.get('purchaseAgent') or r.get('organizerName'),

                raw_data=r
            )
            items.append(item)

        return items

    def _build_url(self, record) -> Optional[str]:
        """构建详情URL"""
        nid = (record.get('id') or record.get('noticeId') or 
               record.get('announcementId'))
        if not nid:
            return None
        patterns = [
            f"{self.SOURCE_URL}/MSS-PORTAL/public/noticeDetail?noticeId={nid}",
            f"{self.SOURCE_URL}/public/announcement/detail?id={nid}",
        ]
        return patterns[0]

    def _parse_html(self, soup: BeautifulSoup) -> List[BiddingItem]:
        """HTML解析"""
        items = []

        selectors = [
            '.notice-list li', '.search-result-item',
            '.announcement-item', 'table tbody tr',
            '[class*="notice"] [class*="item"]',
            '.list-container .item',
        ]

        elements = []
        for sel in selectors:
            elems = soup.select(sel)
            if elems:
                elements = elems
                break

        for el in elements[:25]:
            item = self._extract_item(el)
            if item:
                items.append(item)

        return items

    def _extract_item(self, elem) -> Optional[BiddingItem]:
        """提取单条元素"""
        link = elem.select_one('a[href*="detail"], a[href*="notice"], '
                               '.title a, h3 a, h4 a')
        if not link:
            return None
            
        href = link.get('href', '')
        if href and not href.startswith('http'):
            href = (self.SOURCE_URL + ('' if href.startswith('/') else '/') + href)

        time_text = ''
        for sel in ['.time', '.date', 'span:last-child']:
            t = elem.select_one(sel)
            if t:
                time_text = t.get_text(strip=True)
                break

        return BiddingItem(
            title=link.get_text(strip=True),
            source=self.SOURCE_NAME,
            operator=Operator.CHINA_TELECOM.value,
            url=href or None,
            publish_time=time_text or None,
            raw_data={'html_snippet': str(elem)[:500]}
        )

    async def _browser_crawl(self, limit: int) -> List[BiddingItem]:
        """浏览器自动化采集"""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.settings.HEADLESS)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()

                # 反检测
                await page.add_init_script("""
                    window.debugger = function() {};
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # 访问阳光采购网首页或搜索页
                urls_to_try = [
                    f"{self.SOURCE_URL}/MSS-PORTAL/public/announcementList",
                    f"{self.SOURCE_URL}/",
                ]
                
                for target in urls_to_try:
                    try:
                        await page.goto(target, wait_until='networkidle',
                                       timeout=self.settings.BROWSER_TIMEOUT)
                        
                        # 尝试搜索目标关键词
                        search_input = await page.query_selector(
                            'input[name="keyword"], input[type="text"], #searchInput')
                        if search_input:
                            await search_input.fill("软件 平台 服务器 云 计算 运维")
                            
                            btn = await page.query_selector('.search-btn, button[type="submit"]')
                            if btn:
                                await btn.click()
                                await page.wait_for_timeout(3000)

                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        items = self._parse_html(soup)
                        
                        if items:
                            await browser.close()
                            return items[:limit]
                    except Exception as e:
                        print(f"   访问{target}失败: {e}")
                        continue
                
                await browser.close()
                return []

        except ImportError:
            print("⚠️ Playwright未安装")
            return []
        except Exception as e:
            print(f"⚠️ 电信浏览器采集异常: {e}")
            return []

    def _extract_budget(self, text) -> Optional[float]:
        """提取金额"""
        if not text:
            return None
        m = re.search(r'([\d,.]+)\s*(万)?元?', str(text))
        if m:
            val = float(m.group(1).replace(',', ''))
            if m.group(2):
                return round(val, 2)
            return round(val / 10000, 2)
        return None

    async def _get_demo_data(self, keywords=None, limit=15) -> List[BiddingItem]:
        """中国电信演示数据"""
        from datetime import datetime, timedelta
        import random

        demo_projects = [
            ("天翼云4.0算力平台服务器扩容采购", "server", 4800, "中国电信云计算分公司"),
            ("政企AI大模型训练平台建设-软件开发", "software", 2200, "中国电信人工智能研究院"),
            ("智慧城市数字孪生平台解决方案集成项目", "solution", 1600, "某省电信公司"),
            ("全网核心数据库升级改造(国产化替代)", "software", 3200, "中国电信IT运营中心"),
            ("边缘云节点GPU计算设备采购(第三批)", "server", 2900, "天翼云科技有限公司"),
            ("网络安全防护体系运维服务(年度框架)", "service", 1100, "中国电信网络与信息安全部"),
            ("行业数字化中台PaaS层组件采购", "software", 1350, "中国电信政企信息服务事业群"),
            ("数据中心分布式存储系统采购", "server", 2100, "中国电信云计算分公司"),
            ("5G定制网端到端解决方案供应商入围选型", "solution+service", 1800, "中国联通5G应用创新中心"),
            ("DevOps持续交付流水线工具链平台", "software", 780, "中国电信软件开发中心"),
            ("IDC机房基础设施综合代维服务外包", "service", 1600, "某省电信公司"),
            ("量子通信安全服务平台开发与集成", "solution", 950, "中国电信研究院"),
            ("全闪存高性能存储阵列扩容采购", "server", 2500, "天翼云数据有限公司"),
            ("统一运维监控平台(AIOps)建设项目", "software+service", 1200, "中国电信IT部"),
            ("区块链BaaS平台建设与运营服务", "solution+service", 850, "中国电信区块链实验室"),
        ]

        regions = ["北京总部", "上海", "广东", "江苏", "浙江", "四川", "安徽", "福建"]
        now = datetime.now()
        items = []

        for i, (title, cat_str, budget, purchaser) in enumerate(demo_projects[:min(limit, len(demo_projects))]):
            category = cat_str.split('+')[0]
            days_ago = random.randint(0, 10)
            deadline_days = random.randint(8, 50)

            item = BiddingItem(
                title=title,
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_TELECOM.value,
                project_code=f"CT-{now.year}-{random.randint(10000,99999)}",
                url=f"https://caigou.chinatelecom.com.cn/MSS-PORTAL/public/noticeDetail?noticeId={random.randint(100000,999999)}",
                publish_time=(now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M'),
                deadline=(now + timedelta(days=deadline_days)).strftime('%Y-%m-%d %H:%M'),
                budget=budget * random.uniform(0.88, 1.12),
                purchaser=purchaser,
                category=category,
                status=random.choices(['bidding','closing_soon','result_published'], weights=[52,20,28])[0],
                region=random.choice(regions),
                summary=f"本采购属于{category}领域，预算约{int(budget)}万元...",
                requirements=["具备相关资质", "有运营商项目经验"],
                raw_data={'demo_data': True}
            )
            items.append(item)

        return items

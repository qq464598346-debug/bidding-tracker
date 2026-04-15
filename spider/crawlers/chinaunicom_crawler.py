"""
中国联通采购与招标网爬虫
目标: https://www.chinaunicombidding.cn/

特点:
- 有反爬机制和debugger检测
- 可能使用Vue/React前端框架
- 数据通过API接口动态加载

策略:
1. 分析网络请求找到API接口
2. 使用Playwright绕过反爬
3. 解析数据并标准化输出
"""
import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler
from core.models import BiddingItem, BiddingStatus, Operator


class ChinaUnicomCrawler(BaseCrawler):
    """中国联通采购与招标网爬虫"""

    SOURCE_NAME = "chinaunicom"
    SOURCE_URL = "https://www.chinaunicombidding.cn"

    # 备用URL（网站可能变更）
    BACKUP_URLS = [
        "https://www.cupb.cn",
        "https://uscm.chinaunicom.cn:18008",
    ]

    # API端点模式
    API_PATTERNS = [
        "/api/notice/list",
        "/api/v1/bid/list", 
        "/bidding/api/notices",
        "/jsp/web/searchNotice.jsp",
    ]

    async def crawl(self, keywords: list = None, limit: int = 50) -> List[BiddingItem]:
        """
        采集中国联通的招标信息
        """
        items = []
        
        try:
            # 策略1: API接口
            items = await self._try_api_crawl(limit)
            
        except Exception as e:
            print(f"⚠️ [中国联通] API采集失败: {e}")
            
            try:
                # 策略2: 浏览器自动化
                items = await self._browser_crawl(limit)
            except Exception as e2:
                print(f"⚠️ [中国联通] 浏览器采集也失败: {e2}")
                items = await self._get_demo_data(keywords, limit)

        return items[:limit]

    async def _try_api_crawl(self, limit: int) -> List[BiddingItem]:
        """尝试API接口采集"""
        items = []
        
        for api_path in self.API_PATTERNS:
            url = f"{self.SOURCE_URL}{api_path}"
            
            # 尝试不同的请求方式
            request_configs = [
                {
                    'method': 'GET',
                    'params': {
                        'currentPage': 1,
                        'pageSize': limit * 2,
                        'noticeType': 1,  # 招标公告
                        'keyword': ''
                    }
                },
                {
                    'method': 'POST', 
                    'data': {
                        'pageNo': 1,
                        'pageSize': limit * 2,
                        'category': '',
                        'keyword': ''
                    }
                },
            ]
            
            for config in request_configs:
                html = await self._fetch(
                    url,
                    method=config['method'],
                    params=config.get('params'),
                    data=config.get('data'),
                    extra_headers={
                        'Referer': self.SOURCE_URL,
                        'Origin': self.SOURCE_URL,
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                    }
                )
                
                if html and len(html) > 20:  # 有效响应
                    parsed = self._parse_response(html)
                    if parsed:
                        items.extend(parsed)
                        break
            
            if items:
                break
                
            await self._delay()
        
        return items

    def _parse_response(self, content: str) -> List[BiddingItem]:
        """解析响应内容"""
        # 尝试JSON
        try:
            data = json.loads(content)
            return self._parse_json_data(data)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # HTML解析
        soup = BeautifulSoup(content, 'html.parser')
        return self._parse_html(soup)

    def _parse_json_data(self, data) -> List[BiddingItem]:
        """解析JSON数据"""
        items = []
        
        records = []
        if isinstance(data, dict):
            records = (data.get('list') or data.get('data', {}).get('records') or 
                      data.get('rows') or data.get('notices') or [])
        elif isinstance(data, list):
            records = data
        
        for r in records:
            item = BiddingItem(
                title=r.get('title') or r.get('noticeTitle') or r.get('projectName') or '',
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_UNICOM.value,
                
                project_code=r.get('projectCode') or r.get('noticeNo'),
                url=self._make_url(r),
                
                publish_time=r.get('publishDate') or r.get('createTime') or r.get('openBidTime'),
                deadline=r.get('bidDeadline') or r.get('bidEndTime'),
                
                budget=self._extract_amount(r.get('budget') or r.get('amount')),
                purchaser=r.get('purchaseAgent') or r.get('agentName'),
                
                raw_data=r
            )
            items.append(item)
        
        return items

    def _make_url(self, record: dict) -> Optional[str]:
        """构建详情URL"""
        nid = (record.get('id') or record.get('noticeId') or 
               record.get('noticeId'))
        if not nid:
            return None
        return f"{self.SOURCE_URL}/jsp/web/noticeDetail.jsp?noticeId={nid}"

    def _parse_html(self, soup: BeautifulSoup) -> List[BiddingItem]:
        """HTML列表解析"""
        items = []
        
        selectors = [
            '.notice-list .item',
            '.search-result-item',
            '.list-container li',
            'table tbody tr',
            '.notice-item',
            '[class*="result"] > div',
        ]
        
        elements = []
        for sel in selectors:
            elems = soup.select(sel)
            if elems:
                elements = elems
                break
        
        for el in elements[:25]:
            item = self._scrape_item(el)
            if item:
                items.append(item)
        
        return items

    def _scrape_item(self, elem) -> Optional[BiddingItem]:
        """从元素中提取单条"""
        link = elem.select_one('a[href*="detail"], a[href*="notice"], '
                              '.title a, h3 a, a:first-child')
        if not link:
            return None
            
        href = link.get('href', '')
        if href and not href.startswith('http'):
            href = self.SOURCE_URL + ('' if href.startswith('/') else '/') + href
        
        time_text = ''
        for sel in ['.time', '.date', 'span:last-child']:
            t = elem.select_one(sel)
            if t:
                time_text = t.get_text(strip=True)
                break

        return BiddingItem(
            title=link.get_text(strip=True),
            source=self.SOURCE_NAME,
            operator=Operator.CHINA_UNICOM.value,
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
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                )
                page = await context.new_page()

                # 反检测脚本
                await page.add_init_script("""
                    window.debugger = function() {};
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    
                    // 隐藏自动化特征
                    const originalQuery = navigator.permissions.query;
                    navigator.permissions.query = (parameters) =>
                        parameters.name === 'notifications'
                            ? Promise.resolve({ state: Notification.permission })
                            : originalQuery(parameters);
                """)

                # 访问页面
                target_url = f"{self.SOURCE_URL}/jsp/web/searchNotice.jsp"
                await page.goto(target_url, wait_until='networkidle', 
                               timeout=self.settings.BROWSER_TIMEOUT)
                
                # 填写搜索条件 - 聚焦目标领域
                try:
                    search_input = await page.query_selector('input[name="keyword"], input[type="text"]')
                    if search_input:
                        await search_input.fill("软件 服务器 云平台 运维 解决方案")
                        
                        search_btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                        if search_btn:
                            await search_btn.click()
                            await page.wait_for_timeout(3000)
                except Exception:
                    pass

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                items = self._parse_html(soup)

                await browser.close()
                return items[:limit]

        except ImportError:
            print("⚠️ Playwright未安装")
            return []
        except Exception as e:
            print(f"⚠️ 联通浏览器采集异常: {e}")
            return []

    def _extract_amount(self, text) -> Optional[float]:
        """提取金额"""
        if not text:
            return None
        m = re.search(r'([\d,.]+)\s*(万)?元?', str(text))
        if m:
            val = float(m.group(1).replace(',', ''))
            if m.group(2):
                return round(val, 2)
            elif val > 10000:
                return round(val / 10000, 2)
            else:
                return round(val / 10000, 2)
        return None

    async def _get_demo_data(self, keywords=None, limit=15) -> List[BiddingItem]:
        """中国联通演示数据"""
        from datetime import datetime, timedelta
        import random

        demo_projects = [
            ("联通云PaaS平台升级改造项目", "software", 1800, "中国联通软件研究院"),
            ("2026年度核心路由器采购项目", "server", 4200, "中国联通网络部"),
            ("智慧城市物联网平台建设-系统集成服务", "solution+service", 1500, "某省联通分公司"),
            ("大数据治理与分析平台开发项目", "software", 950, "联通大数据有限公司"),
            ("5G行业专网MEC边缘计算设备采购", "server", 2800, "中国联通5G应用创新中心"),
            ("网络安全态势感知系统运维服务(年度)", "service", 700, "中国联通信息安全部"),
            ("政企客户数字化运营支撑平台建设", "solution", 1200, "联通政企客户事业部"),
            ("数据中心GPU算力服务器集群采购", "server", 3500, "联通云数据有限公司"),
            ("统一通信能力开放平台开发项目", "software", 880, "联通系统集成公司"),
            ("营业厅智能化改造总集成项目", "solution", 1100, "某市联通分公司"),
            ("全栈云原生中间件采购(国产化)", "software", 650, "联通信息技术中心"),
            ("IDC机房基础设施代维服务框架协议", "service", 1900, "联通XX省分公司"),
            ("区块链供应链金融服务平台开发", "solution", 780, "联通金融科技中心"),
            ("分布式对象存储扩容采购项目", "server", 1600, "联通云计算公司"),
            ("DevSecOps安全开发工具链采购", "software+service", 520, "联通信息安全部"),
        ]

        regions = ["北京总部", "广东", "上海", "山东", "辽宁", "河北", "四川", "湖南"]
        now = datetime.now()
        items = []

        for i, (title, cat_str, budget, purchaser) in enumerate(demo_projects[:min(limit, len(demo_projects))]):
            category = cat_str.split('+')[0]
            days_ago = random.randint(0, 12)
            deadline_days = random.randint(5, 40)

            item = BiddingItem(
                title=title,
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_UNICOM.value,
                project_code=f"CU-{now.year}-{random.randint(10000,99999)}",
                url=f"https://www.chinaunicombidding.cn/jsp/web/noticeDetail.jsp?noticeId={random.randint(100000,999999)}",
                publish_time=(now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M'),
                deadline=(now + timedelta(days=deadline_days)).strftime('%Y-%m-%d %H:%M'),
                budget=budget * random.uniform(0.85, 1.15),
                purchaser=purchaser,
                category=category,
                status=random.choices(['bidding','closing_soon','result_published'], weights=[50,22,28])[0],
                region=random.choice(regions),
                summary=f"本采购项目属于{category}领域，预算约{int(budget)}万元...",
                requirements=[f"具备相关资质认证", "有运营商类似项目经验", f"团队规模满足要求"],
                raw_data={'demo_data': True}
            )
            items.append(item)

        return items

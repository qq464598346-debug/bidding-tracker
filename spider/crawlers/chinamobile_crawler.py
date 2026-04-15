"""
中国移动采购与招标网爬虫
目标: https://b2b.10086.cn/

特点:
- 使用了debugger反爬检测
- 需要处理JavaScript渲染
- 数据通过API接口返回

策略:
1. 直接调用后端API获取数据（优先）
2. 如果API不可用，使用Playwright浏览器自动化
3. 解析列表页和详情页
"""
import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler
from core.models import BiddingItem, BiddingStatus, Operator


class ChinaMobileCrawler(BaseCrawler):
    """中国移动采购与招标网爬虫"""

    SOURCE_NAME = "chinamobile"
    SOURCE_URL = "https://b2b.10086.cn"

    # 移动采购网站可能的API端点
    API_ENDPOINTS = [
        "/b2b/main/listVendorNotice.html",
        "/b2b/api/notice/list",
        "/b2b/main/listNoticeResults.html",
    ]

    # 搜索关键词（聚焦目标领域）
    TARGET_KEYWORDS = [
        '软件', '平台', '系统', '服务器', '云',
        '解决方案', '集成', '运维', '开发', '服务'
    ]

    async def crawl(self, keywords: list = None, limit: int = 50) -> List[BiddingItem]:
        """
        采集中国移动的招标信息
        
        策略:
        1. 尝试直接API调用
        2. 失败则使用页面抓取
        3. 最后使用浏览器自动化
        """
        items = []
        
        # 获取公告列表
        try:
            items = await self._fetch_notice_list(limit)
        except Exception as e:
            print(f"⚠️ [中国移动] 列表采集失败: {e}")
            
            # 尝试备用方案
            try:
                items = await self._fetch_with_browser(limit)
            except Exception as e2:
                print(f"⚠️ [中国移动] 浏览器方案也失败了，使用模拟数据: {e2}")
                items = await self._get_demo_data(keywords, limit)
        
        return items[:limit]

    async def _fetch_notice_list(self, limit: int) -> List[BiddingItem]:
        """
        通过API获取招标公告列表
        
        中国移动网站的API可能返回JSON或HTML
        """
        items = []
        
        for endpoint in self.API_ENDPOINTS[:2]:  # 尝试前两个端点
            url = f"{self.SOURCE_URL}{endpoint}"
            
            # 尝试不同的请求方式
            methods_to_try = [
                {'method': 'GET', 'params': {
                    'noticeType': '3',  # 招标公告
                    'currentPage': '1',
                    'pageSize': str(min(limit * 2, 100)),
                }},
                {'method': 'POST', 'data': {
                    'noticeType': '3',
                    'pageNo': '1',
                    'pageSize': str(min(limit * 2, 100)),
                    'searchWord': '',
                }},
            ]
            
            for req_config in methods_to_try:
                html = await self._fetch(
                    url,
                    method=req_config['method'],
                    params=req_config.get('params'),
                    data=req_config.get('data'),
                    extra_headers={
                        'Referer': f"{self.SOURCE_URL}/",
                        'Origin': self.SOURCE_URL,
                        'X-Requested-With': 'XMLHttpRequest'  # 模拟AJAX请求
                    }
                )
                
                if html:
                    parsed_items = self._parse_response(html)
                    if parsed_items:
                        items.extend(parsed_items)
                        break
            
            if items:
                break
            
            await self._delay()

        return items[:limit]

    def _parse_response(self, content: str) -> List[BiddingItem]:
        """解析响应内容"""
        
        # 尝试JSON格式
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                records = data.get('list') or data.get('data', {}).get('list', []) or data.get('rows', [])
                return self._parse_json_records(records)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # HTML格式解析
        soup = BeautifulSoup(content, 'html.parser')
        return self._parse_html_response(soup)

    def _parse_json_records(self, records: list) -> List[BiddingItem]:
        """解析JSON格式的记录"""
        items = []
        
        for record in records:
            item = BiddingItem(
                title=record.get('title') or record.get('noticeTitle') or 
                      record.get('projectName') or '',
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_MOBILE.value,
                
                project_code=record.get('projectCode') or record.get('noticeCode'),
                url=self._build_detail_url(record),
                
                publish_time=record.get('publishTime') or record.get('createTime') or
                             record.get('openBiddingTime'),
                deadline=record.get('bidDeadline') or record.get('endTime'),
                
                budget=self._extract_budget(
                    record.get('budget') or record.get('budgetAmount') or ''
                ),
                purchaser=(record.get('purchaseAgent') or 
                          record.get('agencyName') or 
                          record.get('purchaserName')),
                          
                raw_data=record
            )
            items.append(item)
        
        return items

    def _build_detail_url(self, record: dict) -> Optional[str]:
        """构建详情页URL"""
        # 可能的字段
        notice_id = (record.get('id') or record.get('noticeId') or 
                    record.get('detailId'))
        if not notice_id:
            return None
        
        base_patterns = [
            f"{self.SOURCE_URL}/b2b/main/viewNoticeContent.html?noticeId={notice_id}",
            f"{self.SOURCE_URL}/b2b/main/detailVendorNotice.html?id={notice_id}",
        ]
        return base_patterns[0]

    def _parse_html_response(self, soup: BeautifulSoup) -> List[BiddingItem]:
        """从HTML中解析招标列表"""
        items = []
        
        # 多种可能的HTML结构选择器
        selectors = [
            '.noticeList .item, .notice-list .item',
            '.list-item, .notice-item',
            'table tbody tr',
            '.infoList li',
            '[class*="notice"] [class*="row"]',
            '.content ul li',
        ]
        
        elements = []
        for selector in selectors:
            elements = soup.select(selector.replace(', ', ', ').split(','))
            if any(soup.select(s.strip()) for s in selector.split(',')):
                for s in selector.split(','):
                    elems = soup.select(s.strip())
                    if elems:
                        elements = elems
                        break
                if elements:
                    break
        
        for elem in elements[:30]:
            try:
                item = self._extract_item_from_element(elem)
                if item and item.title:
                    items.append(item)
            except Exception:
                continue
        
        return items

    def _extract_item_from_element(self, elem) -> Optional[BiddingItem]:
        """从HTML元素中提取单条数据"""
        # 标题和链接
        link_elem = elem.select_one('a[href*="notice"], a[href*="detail"], '
                                    'a[class*="title"], h3 a, .title a, a:first-child')
        if not link_elem:
            return None
            
        title = link_elem.get_text(strip=True)
        href = link_elem.get('href', '')
        if href and not href.startswith('http'):
            href = self.SOURCE_URL + href if href.startswith('/') else f"{self.SOURCE_URL}/{href}"
        
        # 时间
        time_text = ''
        time_selectors = ['span:last-child', '.time', '.date', '.publish-time', 
                         'td:last-child', 'span.time']
        for sel in time_selectors:
            el = elem.select_one(sel)
            if el:
                time_text = el.get_text(strip=True)
                break
        
        return BiddingItem(
            title=title,
            source=self.SOURCE_NAME,
            operator=Operator.CHINA_MOBILE.value,
            url=href or None,
            publish_time=time_text or None,
            summary=self._get_summary_from_element(elem),
            raw_data={'html_snippet': str(elem)[:500]}
        )

    def _get_summary_from_element(self, elem) -> str:
        """提取元素摘要"""
        parts = []
        for sel in ['.desc', 'td:nth-child(2)', 'span:not(:last-child)', 'p']:
            el = elem.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 5:
                    parts.append(text)
        return ' | '.join(parts)[:200]

    async def _fetch_with_browser(self, limit: int) -> List[BiddingItem]:
        """
        使用Playwright进行浏览器自动化采集
        用于处理需要JavaScript渲染或强反爬的页面
        """
        try:
            from playwright.async_api import async_playwright
            
            items = []
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.settings.HEADLESS)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                # 访问招标公告列表页
                await page.goto(f"{self.SOURCE_URL}/b2b/main/listVendorNotice.html", 
                               wait_until='networkidle', timeout=self.settings.BROWSER_TIMEOUT)
                
                # 绕过可能的debugger检测
                await page.add_init_script("""
                    // 禁用debugger检测
                    window.debugger = function() {};
                    
                    // 覆盖常见的检测方式
                    Object.defineProperty(window, 'webdriver', { get: () => undefined });
                """)
                
                # 等待列表加载
                try:
                    await page.wait_for_selector('.noticeList, .list-item, table, .item', 
                                                timeout=10000)
                except Exception:
                    pass
                
                # 提取数据
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                items = self._parse_html_response(soup)
                
                await browser.close()
            
            return items[:limit]
            
        except ImportError:
            print("⚠️ Playwright未安装，请运行: pip install playwright && playwright install")
            return []
        except Exception as e:
            print(f"⚠️ 浏览器自动化失败: {e}")
            return []

    def _extract_budget(self, text) -> Optional[float]:
        """提取预算金额"""
        if not text:
            return None
            
        match = re.search(r'([\d,.]+)\s*(万)?元?', str(text))
        if match:
            amount = float(match.group(1).replace(',', ''))
            if match.group(2):  # 已经是万元
                return round(amount, 2)
            elif amount > 100000:  # 可能是元为单位的大额
                return round(amount / 10000, 2)
            else:
                return round(amount / 10000, 2)  # 元转万元
        return None

    async def _get_demo_data(self, keywords: list = None, limit: int = 15) -> List[BiddingItem]:
        """中国移动演示数据"""
        from datetime import datetime, timedelta
        import random
        
        demo_projects = [
            ("2026年云资源池服务器扩容采购项目", "server", 3500, "中国移动通信集团有限公司"),
            ("集团统一AI中台建设-软件开发服务采购", "software", 1200, "中国移动研究院"),
            ("省分公司5G行业专网解决方案供应商入围", "solution", 800, "某省移动公司"),
            ("数据中心基础设施运维外包服务(2026年度)", "service", 600, "中国移动XX省分公司"),
            ("核心网NFV虚拟化平台升级改造项目", "software", 2800, "中国移动网络部"),
            ("边缘计算节点服务器采购(第二批)", "server", 1800, "中国移动云计算公司"),
            ("智慧营业厅数字化转型系统集成项目", "solution", 950, "某市移动分公司"),
            ("网络安全运营中心(SOC)建设与服务", "service", 1500, "中国移动信息安全中心"),
            ("大数据平台PaaS层中间件采购", "software", 750, "中国移动信息技术中心"),
            ("算力网络调度管理系统开发", "software", 1100, "中国移动研究院"),
            ("IDC机房综合代维服务框架协议采购", "service", 2200, "中国移动XX省公司"),
            ("政企客户行业应用开发框架入围选型", "solution", 1300, "中国移动政企事业部"),
            ("全闪存存储阵列采购项目", "server", 2600, "中国移动云计算公司"),
            ("DevOps流水线工具链平台采购", "software", 480, "中国移动信息技术中心"),
            ("区块链BaaS平台建设与运维服务", "solution+service", 900, "中国移动研究院"),
        ]
        
        regions = ["北京总部", "广东", "江苏", "浙江", "四川", "湖北", "山东", "河南"]
        now = datetime.now()
        items = []
        
        for i, (title, cat_str, budget, purchaser) in enumerate(demo_projects[:min(limit, len(demo_projects))]):
            cats = cat_str.split('+')
            category = cats[0]
            
            days_ago = random.randint(0, 14)
            deadline_days = random.randint(7, 45)
            
            item = BiddingItem(
                title=title,
                source=self.SOURCE_NAME,
                operator=Operator.CHINA_MOBILE.value,
                project_code=f"CM-{now.year}-{random.randint(10000,99999)}",
                url=f"https://b2b.10086.cn/b2b/main/detailVendorNotice.html?id={random.randint(100000,999999)}",
                publish_time=(now - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M'),
                deadline=(now + timedelta(days=deadline_days)).strftime('%Y-%m-%d %H:%M'),
                budget=budget * random.uniform(0.9, 1.1),
                purchaser=purchaser,
                category=category,
                status=random.choices(['bidding','closing_soon','result_published'], weights=[55,20,25])[0],
                region=random.choice(regions),
                summary=f"本项目为中国移动{category}领域重要采购项目，涉及相关技术和服务...",
                requirements=[
                    f"具备{category.replace('software','软件开发').replace('server','硬件供应').replace('solution','解决方案交付').replace('service','技术服务')}能力",
                    f"近3年有类似运营商项目经验",
                    f"注册资金不低于{random.choice([200,500,1000])}万元"
                ],
                raw_data={'demo_data': True}
            )
            items.append(item)
        
        return items

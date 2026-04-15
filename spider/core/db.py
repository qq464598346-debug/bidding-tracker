"""
SQLite数据库管理 - 招投标数据持久化
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.models import BiddingItem


class Database:
    """
    SQLite数据库管理器
    负责所有数据的CRUD操作
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（懒加载）"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row  # 支持字典式访问
        return self._conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 主表：招投标信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bidding_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                operator TEXT,
                
                project_code TEXT UNIQUE,
                url TEXT UNIQUE,
                
                publish_time TEXT,
                deadline TEXT,
                open_time TEXT,
                
                budget REAL,
                purchaser TEXT,
                
                category TEXT DEFAULT 'other',
                status TEXT DEFAULT 'bidding',
                region TEXT,
                
                summary TEXT,
                requirements TEXT,          -- JSON数组
                
                raw_data TEXT,             -- JSON对象
                crawled_at TEXT,
                
                ai_tags TEXT,              -- JSON数组
                ai_confidence REAL DEFAULT 0,
                ai_relevance_score REAL DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引以加速查询
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_source ON bidding_items(source)",
            "CREATE INDEX IF NOT EXISTS idx_operator ON bidding_items(operator)",
            "CREATE INDEX IF NOT EXISTS idx_category ON bidding_items(category)",
            "CREATE INDEX IF NOT EXISTS idx_status ON bidding_items(status)",
            "CREATE INDEX IF NOT EXISTS idx_publish_time ON bidding_items(publish_time)",
            "CREATE INDEX IF NOT EXISTS idx_ai_relevance ON bidding_items(ai_relevance_score)",
            "CREATE INDEX IF NOT EXISTS idx_title_search ON bidding_items(title)",
        ]
        for idx in indexes:
            cursor.execute(idx)
        
        # 爬虫日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                items_count INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT,
                finished_at TEXT,
                duration_seconds REAL
            )
        """)
        
        conn.commit()
        print(f"✅ 数据库初始化完成: {self.db_path}")
        
        # ★ 首次启动时自动填充种子数据
        self._seed_if_empty()

    def init_tables(self):
        """公开方法：确保表结构已创建（供外部调用）"""
        self._init_db()

    def _seed_if_empty(self):
        """首次运行时自动填充演示数据（确保前端打开即有内容）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM bidding_items")
        count = cursor.fetchone()['cnt']
        
        if count > 0:
            return  # 已有数据，不填充
        
        print("🌱 首次运行，正在填充演示数据...")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        seed_data = [
            # === 中国移动 ===
            ('2026年云计算平台操作系统及中间件集中采购项目', 'chinamobile', 'chinamobile',
             'CM-RZ-2026-0218', None, '2026-04-12', '2026-05-05', None,
             12800, '中国移动通信集团采购服务中心', 'software', 'bidding', '全国',
             '本项目为中国移动2026年度云计算平台建设所需操作系统（含国产化操作系统）、数据库中间件、消息队列等基础软件产品的集中采购。',
             None, None, now, '["云计算","操作系统","中间件","国产化"]', 0.92, 0.88),
            
            ('智慧城市数字底座解决方案选型及实施服务采购', 'chinamobile', 'chinamobile',
             'CM-ZH-2026-0156', None, '2026-04-08', '2026-04-20', None,
             5630, '中国移动智慧家庭运营中心', 'solution', 'closing_soon', '广东/浙江/江苏',
             '为推进智慧城市建设试点工作，现面向全国遴选优秀的智慧城市数字底座解决方案供应商。方案需涵盖城市大数据中心、城市大脑中枢平台、物联网统一接入平台等核心模块。',
             None, None, now, '["智慧城市","数字化转型","IoT","大数据"]', 0.89, 0.85),
            
            ('AI算力集群服务器GPU/NPU扩容采购项目第二批', 'chinamobile', 'chinamobile',
             'CM-YN-2026-0389', None, '2026-04-10', '2026-05-02', None,
             24500, '中国移动云能力中心', 'server', 'bidding', '京津冀/长三角',
             '本批次采购AI训练推理服务器，包括但不限于：GPU训练服务器、NPU昇腾系列服务器、高性能推理服务器等。要求单节点算力不低于500TFLOPS（FP16）。',
             None, None, now, '["AI算力","GPU服务器","NPU","智算中心"]', 0.95, 0.91),
            
            ('网络安全运营中心安全服务外包采购2026-2027年度', 'chinamobile', 'chinamobile',
             'CM-AQ-2026-0072', None, '2026-04-06', '2026-04-28', None,
             3890, '中国移动信息安全中心', 'service', 'bidding', '全国',
             '采购内容包括：7×24小时安全监控值守服务、渗透测试服务、应急响应服务、安全评估服务、重保期安全保障服务等。',
             None, None, now, '["网络安全","SOC","渗透测试","安全运营"]', 0.87, 0.82),
            
            # === 中国联通 ===
            ('5G行业专网核心网设备及网管系统采购项目', 'chinaunicom', 'chinaunicom',
             'CU-WL-2026-0456', None, '2026-04-13', '2026-05-08', None,
             18200, '中国联通网络技术研究院', 'solution', 'bidding', '全国重点工业区域',
             '面向矿山、港口、电力等重点行业场景，采购5G行业专网核心网设备（UPF/AMF/SMF）、边缘计算MEC平台、网络切片管理系统等。',
             None, None, now, '["5G专网","MEC","网络切片","工业互联网"]', 0.93, 0.90),
            
            ('大数据平台升级改造——实时流计算引擎采购', 'chinaunicom', 'chinaunicom',
             'CU-DJ-2026-0189', None, '2026-04-09', '2026-04-22', None,
             4680, '中国联通大数据有限公司', 'software', 'closing_soon', '贵州/内蒙古数据中心',
             '采购企业级实时流计算引擎软件及配套工具链，支撑联通大数据平台的实时数据处理能力升级。支持每秒百万级事件处理吞吐量。',
             None, None, now, '["大数据","实时计算","Flink","流处理"]', 0.88, 0.84),
            
            ('通用服务器x86 ARM框架协议采购2026年上半年批次', 'chinaunicom', 'chinaunicom',
             'CG-CZ-2026-0067', None, '2026-04-07', '2026-04-30', None,
             32000, '中国联通集中采购中心', 'server', 'bidding', '全国',
             '本次框架协议采购涵盖通用型2路/4路服务器和ARM架构服务器，预计采购规模约3000台。要求通过联通内部兼容性测试认证。',
             None, None, now, '["通用服务器","x86","ARM","鲲鹏"]', 0.85, 0.80),
            
            ('政企客户ICT项目交付实施服务入围采购', 'chinaunicom', 'chinaunicom',
             'CU-ZQ-2026-0234', None, '2026-04-03', '2026-04-25', None,
             8500, '中国联通政企客户事业部', 'service', 'bidding', '各省分公司',
             '面向全国遴选具备政企ICT项目综合交付能力的系统集成服务商，服务范围包括需求调研与方案设计、软硬件系统集成等。',
             None, None, now, '["系统集成","ICT","项目管理","交付服务"]', 0.83, 0.78),
            
            # === 中国电信 ===
            ('天翼云4.0分布式云操作系统核心模块研发及采购', 'chinatelecom', 'chinatelecom',
             'CT-YS-2026-0567', None, '2026-04-14', '2026-05-10', None,
             15800, '中国电信云计算分公司', 'software', 'bidding', '北京/上海/广州/成都',
             '围绕天翼云4.0分布式云操作系统的关键核心技术进行联合研发和产品化采购。重点方向包括多云统一资源调度引擎、异构算力编排系统等。',
             None, None, now, '["天翼云","分布式云","Kubernetes","云原生"]', 0.94, 0.90),
            
            ('数字政府一体化政务服务平台建设二期采购', 'chinatelecom', 'chinatelecom',
             'CT-ZF-2026-0178', None, '2026-04-11', '2026-04-23', None,
             9600, '中国电信政法公安行业事业部', 'solution', 'closing_soon', '西南地区试点省份',
             '二期项目建设内容包括：政务数据共享交换平台升级、"一件事一次办"服务流程再造支撑、智能审批辅助系统、政务服务效能监测大屏等。',
             None, None, now, '["数字政府","一网通办","政务云","等保"]', 0.91, 0.87),
            
            ('智算中心高性能存储系统及全闪存阵列采购', 'chinatelecom', 'chinatelecom',
             'CT-SJ-2026-0345', None, '2026-04-08', '2026-05-01', None,
             27600, '中国电信数据中心运营中心', 'server', 'bidding', '上海/贵阳智算中心',
             '为满足大规模AI训练和推理的数据存取需求，采购高性能并行文件系统和全闪存存储阵列。聚合带宽不低于200GB/s，IOPS不低于2000万。',
             None, None, now, '["高性能存储","全闪存","并行文件系统","AI存储"]', 0.93, 0.89),
            
            ('全网IDC机房基础设施运维服务2026-2028年框架', 'chinatelecom', 'chinatelecom',
             'CT-YW-2026-0156', None, '2026-04-04', '2026-04-26', None,
             12500, '中国电信网络运行维护事业部', 'service', 'bidding', '全国31省IDC机房',
             '采购覆盖全国核心数据中心的机房基础设施运维服务，包括供配电系统巡检维护、暖通空调系统维保、动环监控系统管理等。',
             None, None, now, '["IDC运维","基础设施","机房管理","动环监控"]', 0.86, 0.81),
            
            # === 全国公共资源交易平台 ===
            ('量子通信保密专线技术服务采购金融行业试点', 'chinatelecom', 'ggzy',
             'CT-LZ-2026-0023', None, '2026-04-15', '2026-05-12', None,
             4200, '中国电信量子集团有限公司', 'service', 'bidding', '北京-上海-合肥',
             '面向金融行业客户提供量子密钥分发设备及量子保密通信专线组网技术服务，包含设备租赁、线路调测、安全运维等全套服务。',
             None, None, now, '["量子通信","QKD","金融科技","信息安全"]', 0.96, 0.93),
            
            ('企业级办公软件OA协同办公许可及定制开发采购', 'chinamobile', 'ggzy',
             'CM-XX-2026-0201', None, '2026-03-28', '2026-04-15', None,
             1560, '中国移动信息系统部', 'software', 'result_published', '总部及各省公司',
             '采购企业级协同办公软件系统，包括文档协作、流程审批、会议管理、即时通讯等功能模块的许可授权及二次开发和集成对接服务。',
             None, None, now, '["OA","协同办公","SaaS","数字化办公"]', 0.84, 0.79),
            
            ('区块链BaaS平台许可及技术支撑服务采购结果公示', 'chinaunicom', 'ggzy',
             'CU-YJ-2026-0045', None, '2026-03-25', '2026-04-10', None,
             2100, '中国联通研究院', 'solution', 'result_published', '总部',
             '采购区块链即服务平台BaaS软件许可、跨链服务组件、以及为期一年的技术支持和版本升级服务。用于支撑联通在供应链金融等方向的区块链应用创新。',
             None, None, now, '["区块链","BaaS","跨链","Web3"]', 0.87, 0.83),
            
            ('中小企业数字化转型SaaS服务市场平台开发采购', 'chinatelecom', 'ggzy',
             'CT-QY-2026-0089', None, '2026-03-31', '2026-04-12', None,
             3300, '中国电信中小企业事业部', 'solution', 'result_published', '全国',
             '构建面向中小企业的数字化转型一站式SaaS服务聚合平台，实现多品类SaaS应用的统一入驻、订购、计费和交付管理。',
             None, None, now, '["SaaS","中小企业","数字化转型","应用市场"]', 0.85, 0.80),
            
            ('边缘云节点通用服务器及加速卡采购华北片区', 'chinamobile', 'ggzy',
             'CM-BY-2026-0112', None, '2026-04-01', '2026-04-15', None,
             8900, '中国移动边缘计算技术实验室', 'server', 'ended', '华北五省市',
             '采购边缘云节点部署所需的通用型边缘服务器及AI推理加速卡，用于MEC节点的规模化部署和能力提升。',
             None, None, now, '["边缘计算","MEC","边缘服务器"]', 0.80, 0.75),
            
            ('自主研发DevOps流水线工具链平台建设采购', 'chinaunicom', 'ggzy',
             'CU-RJ-2026-0067', None, '2026-03-20', '2026-04-08', None,
             980, '中国联通软件研究院', 'software', 'ended', '总部研发中心',
             '采购代码仓库CI/CD引擎制品管理自动化测试等DevOps工具链的一体化管理平台软件许可及实施服务。',
             None, None, now, '["DevOps","CI/CD","研发效能"]', 0.78, 0.73),
        ]
        
        cursor.executemany("""
            INSERT INTO bidding_items (
                title, source, operator, project_code, url,
                publish_time, deadline, open_time,
                budget, purchaser, category, status, region,
                summary, requirements, raw_data, crawled_at,
                ai_tags, ai_confidence, ai_relevance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        
        conn.commit()
        print(f"🌱 已填充 {len(seed_data)} 条演示数据 — 点击「立即更新」可获取实时数据")

    def insert_or_update(self, item: BiddingItem) -> bool:
        """
        插入或更新一条数据
        通过project_code或url判断是否已存在
        
        Returns: True表示新增，False表示更新
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        data = item.to_dict()
        
        # 尝试通过唯一键查找已有记录
        existing_id = None
        if data.get('project_code'):
            cursor.execute("SELECT id FROM bidding_items WHERE project_code=?", 
                          (data['project_code'],))
            row = cursor.fetchone()
            if row:
                existing_id = row['id']
        elif data.get('url'):
            cursor.execute("SELECT id FROM bidding_items WHERE url=?", 
                          (data['url'],))
            row = cursor.fetchone()
            if row:
                existing_id = row['id']
        
        now = datetime.now().isoformat()
        is_new = existing_id is None
        
        if is_new:
            # 新增记录
            sql = """
                INSERT INTO bidding_items (
                    title, source, operator, project_code, url,
                    publish_time, deadline, open_time,
                    budget, purchaser, category, status, region,
                    summary, requirements, raw_data, crawled_at,
                    ai_tags, ai_confidence, ai_relevance_score, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                data.get('title', ''),
                data.get('source', ''),
                data.get('operator'),
                data.get('project_code'),
                data.get('url'),
                data.get('publish_time'),
                data.get('deadline'),
                data.get('open_time'),
                data.get('budget'),
                data.get('purchaser'),
                data.get('category', 'other'),
                data.get('status', 'bidding'),
                data.get('region'),
                data.get('summary'),
                json.dumps(data.get('requirements', []), ensure_ascii=False),
                json.dumps(data.get('raw_data', {}), ensure_ascii=False) if data.get('raw_data') else None,
                data.get('crawled_at'),
                json.dumps(data.get('ai_tags', []), ensure_ascii=False),
                data.get('ai_confidence', 0),
                data.get('ai_relevance_score', 0),
                now, now
            ))
        else:
            # 更新现有记录
            sql = """
                UPDATE bidding_items SET
                    title=?, source=?, operator=?,
                    publish_time=?, deadline=?, open_time=?,
                    budget=?, purchaser=?,
                    category=?, status=?, region=?,
                    summary=?, requirements=?, raw_data=?, crawled_at=?,
                    ai_tags=?, ai_confidence=?, ai_relevance_score=?,
                    updated_at=?
                WHERE id=?
            """
            cursor.execute(sql, (
                data.get('title', ''),
                data.get('source', ''),
                data.get('operator'),
                data.get('publish_time'),
                data.get('deadline'),
                data.get('open_time'),
                data.get('budget'),
                data.get('purchaser'),
                data.get('category', 'other'),
                data.get('status', 'bidding'),
                data.get('region'),
                data.get('summary'),
                json.dumps(data.get('requirements', []), ensure_ascii=False),
                json.dumps(data.get('raw_data', {}), ensure_ascii=False) if data.get('raw_data') else None,
                data.get('crawled_at'),
                json.dumps(data.get('ai_tags', []), ensure_ascii=False),
                data.get('ai_confidence', 0),
                data.get('ai_relevance_score', 0),
                now,
                existing_id
            ))
        
        conn.commit()
        return is_new

    def batch_insert(self, items: List[BiddingItem]) -> Dict[str, int]:
        """
        批量插入/更新数据
        Returns: {"new": N, "updated": M}
        """
        result = {"new": 0, "updated": 0}
        for item in items:
            if self.insert_or_update(item):
                result["new"] += 1
            else:
                result["updated"] += 1
        return result

    def query(
        self,
        keyword: Optional[str] = None,
        source: Optional[str] = None,
        operator: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        min_relevance: float = 0.0,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "publish_time",  # publish_time/budget/relevance/deadline
        order: str = "desc"
    ) -> Dict[str, Any]:
        """
        多条件查询招投标信息
        返回分页结果
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        # 关键词搜索 (标题+摘要)
        if keyword:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        # 数据源过滤
        if source and source != "all":
            conditions.append("source = ?")
            params.append(source)
        
        # 运营商过滤
        if operator and operator != "all":
            if operator == "none":
                conditions.append("operator IS NULL")
            else:
                conditions.append("operator = ?")
                params.append(operator)
        
        # 类别过滤
        if category and category != "all":
            conditions.append("category = ?")
            params.append(category)
        
        # 状态过滤
        if status and status != "all":
            conditions.append("status = ?")
            params.append(status)
        
        # AI相关度阈值
        if min_relevance > 0:
            conditions.append("ai_relevance_score >= ?")
            params.append(min_relevance)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # 排序映射
        sort_map = {
            "publish_time": "publish_time",
            "budget": "budget",
            "relevance": "ai_relevance_score",
            "deadline": "deadline",
            "crawled_at": "crawled_at"
        }
        order_by = f"{sort_map.get(sort_by, 'publish_time')} {order.upper()}"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM bidding_items {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 分页查询
        query_sql = f"""
            SELECT * FROM bidding_items {where_clause}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()
        
        # 转换为字典列表
        items = []
        for row in rows:
            item = dict(row)
            # 解析JSON字段
            for json_field in ['requirements', 'ai_tags', 'raw_data']:
                val = item.get(json_field)
                if val and isinstance(val, str):
                    try:
                        item[json_field] = json.loads(val)
                    except json.JSONDecodeError:
                        pass
            items.append(item)
        
        return {
            "total": total,
            "page_size": limit,
            "offset": offset,
            "items": items
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计数据概览
        用于前端Dashboard展示
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        stats = {}
        
        # 总数统计
        cursor.execute("SELECT COUNT(*) as cnt FROM bidding_items")
        stats['total'] = cursor.fetchone()['cnt']
        
        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM bidding_items WHERE DATE(created_at)=?", 
            (today,)
        )
        stats['today_new'] = cursor.fetchone()['cnt']
        
        # 本周新增
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM bidding_items WHERE created_at >= ?", 
            (week_ago,)
        )
        stats['week_new'] = cursor.fetchone()['cnt']
        
        # 各运营商统计
        cursor.execute("""
            SELECT operator, COUNT(*) as cnt 
            FROM bidding_items 
            GROUP BY operator
        """)
        stats['by_operator'] = {row['operator'] or '其他': row['cnt'] for row in cursor.fetchall()}
        
        # 各状态统计
        cursor.execute("""
            SELECT status, COUNT(*) as cnt 
            FROM bidding_items 
            GROUP BY status
        """)
        stats['by_status'] = dict(cursor.fetchall())
        
        # 各类别统计
        cursor.execute("""
            SELECT category, COUNT(*) as cnt 
            FROM bidding_items 
            GROUP BY category
        """)
        stats['by_category'] = dict(cursor.fetchall())
        
        # 总预算金额（万元）
        cursor.execute("SELECT COALESCE(SUM(budget), 0) as total_budget FROM bidding_items WHERE budget > 0")
        stats['total_budget'] = cursor.fetchone()['total_budget']
        
        # 即将截止（7天内）
        soon_deadline = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM bidding_items 
            WHERE deadline IS NOT NULL AND deadline <= ? AND status IN ('bidding', 'upcoming')
        """, (soon_deadline,))
        stats['closing_soon'] = cursor.fetchone()['cnt']
        
        return stats

    def log_crawl(self, source: str, status: str, count: int = 0, 
                  error: str = None, started_at: str = None, 
                  finished_at: str = None, duration: float = 0):
        """记录一次爬虫执行日志"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO crawl_logs (source, status, items_count, error_message, 
                                   started_at, finished_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, status, count, error, started_at, finished_at, duration))
        conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

"""
AI智能解析引擎
负责:
1. 智能分类 - 判断招标项目属于哪个类别
2. 相关度评分 - 判断项目是否属于目标领域（基础软件/行业解决方案/服务器/服务）
3. 关键信息提取 - 从标题和摘要中提取关键要素
4. 标签生成 - 自动生成便于检索的标签
"""
import re
import json
from typing import List, Dict, Any, Optional

from core.models import BiddingItem, Category, BiddingStatus


class AIEngineBase:
    """AI引擎基类"""

    # 目标领域关键词配置
    TARGET_KEYWORDS = {
        Category.SOFTWARE: [
            # 操作系统
            '操作系统', 'Linux', 'Windows Server', '麒麟', '统信', '中标麒麟',
            'openEuler', 'CentOS', 'RedHat', 'Ubuntu',
            # 中间件
            '中间件', '消息队列', 'Kafka', 'RabbitMQ', 'Redis', 'Nginx', 
            'Tomcat', 'Spring Boot', '微服务框架', '服务网格',
            # 数据库
            '数据库', 'MySQL', 'PostgreSQL', 'Oracle', 'MongoDB', '达梦', 
            '人大金仓', 'OceanBase', 'TiDB', '数据仓库', '大数据平台',
            # 开发工具
            '开发平台', 'IDE', 'DevOps', 'CI/CD', '容器化', 'Docker', 'Kubernetes',
            # 办公软件
            '办公软件', 'OA系统', '邮件系统', '文档管理', '协作平台',
        ],
        
        Category.SOLUTION: [
            # 行业解决方案关键词
            '智慧城市', '数字政府', '城市大脑', '一网通办', '一网统管',
            '5G应用', '5G专网', '5G+工业互联网',
            '数字化转型', '数字化平台', '信息化建设',
            '区块链', '分布式账本', '智能合约',
            '人工智能', 'AI平台', '机器学习', '深度学习', '大模型', 'LLM',
            '云计算', '云平台', '私有云', '混合云', '多云管理',
            '物联网', 'IoT平台', '边缘计算',
            '大数据', '数据分析', '数据中台', '数据治理',
            '网络安全', '安全运营中心', 'SOC', '态势感知', '零信任',
            'ERP', 'CRM', 'SCM', '企业资源计划', '客户关系管理',
        ],
        
        Category.SERVER: [
            # 服务器硬件
            '服务器', '机架式服务器', '刀片服务器', 'GPU服务器', 'AI服务器',
            '算力服务器', '通用服务器', '存储服务器',
            # 存储
            '存储设备', '磁盘阵列', 'SAN存储', 'NAS存储', '全闪存',
            '分布式存储', '对象存储', '备份一体机',
            # 网络设备
            '交换机', '路由器', '防火墙', '负载均衡', 'SDN',
            '光传输', 'OTN', 'PTN', 'SPN',
            # 计算相关
            '高性能计算', 'HPC', '超算', '算力集群', '智算中心',
        ],
        
        Category.SERVICE: [
            # 服务类关键词
            '运维服务', '运行维护', 'O&M', 'IT运维', '网络运维',
            '系统集成', '总集成', '解决方案交付', '项目实施',
            '安全服务', '等保测评', '渗透测试', '安全加固', '应急响应',
            '咨询服务', '技术咨询', '方案设计', '架构设计',
            'IDC服务', '机房托管', '带宽服务', 'CDN服务',
            '软件开发', '定制开发', '外包开发', '软件实施',
            '培训服务', '技术支持', '驻场服务',
            '云服务', 'SaaS', 'PaaS', 'IaaS',
        ]
    }

    # 运营商识别关键词
    OPERATOR_KEYWORDS = {
        'chinamobile': ['中国移动', '中国移动通信集团', '移动通信', 'CMCC'],
        'chinaunicom': ['中国联通', '中国联合网络通信', '联通', 'China Unicom'],
        'chinatelecom': ['中国电信', '中国电信集团公司', '电信', 'CTCC', 'China Telecom']
    }
    
    # 金额提取正则（支持多种格式）
    AMOUNT_PATTERNS = [
        r'预算[金额：:\s]*(\d+(?:\.\d+)?)\s*[万]?元',
        r'最高限价[：:\s]*(\d+(?:\.\d+)?)\s*[万]?元',
        r'[采购|投资]金额[：:\s]*(\d+(?:\.\d+)?)\s*[万]?元',
        r'(?:约|大约|不超过)[\s]*(\d+(?:\.\d+)?)\s*(?:万)?元',
        r'\$\s*([\d,]+(?:\.\d+)?)',  # 美元格式
    ]

    def analyze(self, item: BiddingItem) -> BiddingItem:
        """
        对一条招标数据进行完整分析
        
        子类可覆盖此方法以接入真实AI模型
        """
        text_to_analyze = f"{item.title} {item.summary or ''}"
        
        # 1. 智能分类
        item.category = self._classify_category(text_to_analyze)
        
        # 2. 运营商识别
        item.operator = self._identify_operator(text_to_analyze)
        if not item.operator and item.source in ('chinamobile', 'chinaunicom', 'chinatelecom'):
            item.operator = item.source
        
        # 3. 状态推断（如果未设置）
        if item.status == BiddingStatus.BIDDING.value:
            item.status = self._infer_status(text_to_analyze).value
        
        # 4. 相关度评分
        item.ai_relevance_score = self._calc_relevance_score(item)
        
        # 5. 生成标签
        item.ai_tags = self._generate_tags(text_to_analyze, item)
        
        # 6. 置信度
        item.ai_confidence = min(0.95, 0.7 + item.ai_relevance_score * 0.25)
        
        return item

    def _classify_category(self, text: str) -> str:
        """
        基于关键词的分类器
        Returns: Category enum value
        """
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.TARGET_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[category] = score
        
        # 找到得分最高的类别
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return Category.OTHER.value

    def _identify_operator(self, text: str) -> Optional[str]:
        """从文本中识别运营商"""
        for op_id, keywords in self.OPERATOR_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return op_id
        return None

    def _infer_status(self, text: str) -> BiddingStatus:
        """从文本推断状态"""
        return BiddingStatus.from_text(text)

    def _calc_relevance_score(self, item: BiddingItem) -> float:
        """
        计算与目标领域的基础相关度评分 (0-1)
        考虑因素：
        1. 类别匹配度
        2. 关键词命中数
        3. 是否为三大运营商
        """
        score = 0.0
        text = f"{item.title} {item.summary or ''}".lower()
        
        # 类别基础分
        if item.category != Category.OTHER.value:
            score += 0.4
        
        # 关键词密度
        all_keywords = [kw for kws in self.TARGET_KEYWORDS.values() for kw in kws]
        hits = sum(1 for kw in all_keywords if kw.lower() in text)
        keyword_score = min(hits / 5, 0.4)  # 最多贡献0.4分
        score += keyword_score
        
        # 运营商加分
        if item.operator and item.operator != 'none':
            score += 0.15
        
        # 预算金额加分（说明是大项目）
        if item.budget and item.budget > 100:
            score += 0.05
        
        return round(min(score, 1.0), 2)

    def _generate_tags(self, text: str, item: BiddingItem) -> List[str]:
        """生成标签列表"""
        tags = []
        
        # 基于类别添加标签
        category_labels = {
            'software': '基础软件',
            'solution': '行业方案',
            'server': '服务器/硬件',
            'service': 'IT服务'
        }
        if item.category in category_labels:
            tags.append(category_labels[item.category])
        
        # 基于运营商添加标签
        operator_names = {
            'chinamobile': '中国移动',
            'chinaunicom': '中国联通',
            'chinatelecom': '中国电信'
        }
        if item.operator in operator_names:
            tags.append(operator_names[item.operator])
        
        # 技术关键词标签
        tech_keywords = ['5G', 'AI', '云计算', '大数据', '区块链', '物联网', 
                         '网络安全', '智慧城市', '数字化转型', '容器', '微服务',
                         '国产化', '信创', '自主可控', 'GPU', '算力']
        for kw in tech_keywords:
            if kw.lower() in text.lower():
                tags.append(kw)
        
        # 规模标签
        if item.budget:
            if item.budget >= 10000:
                tags.append('亿元级')
            elif item.budget >= 1000:
                tags.append('千万级')
            elif item.budget >= 100:
                tags.append('百万级')
        
        return list(set(tags))[:8]  # 最多8个标签

    def batch_analyze(self, items: List[BiddingItem]) -> List[BiddingItem]:
        """批量分析"""
        return [self.analyze(item) for item in items]


class OpenAIEngine(AIEngineBase):
    """
    OpenAI增强版AI引擎
    当配置了OpenAI API Key时使用，提供更精准的分析能力
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def analyze(self, item: BiddingItem) -> BiddingItem:
        """使用OpenAI进行增强分析"""
        try:
            prompt = f"""请分析以下招投标信息的结构化数据，返回JSON格式。

标题：{item.title}
摘要：{item.summary or '无'}
来源：{item.source}
预算：{item.budget or '未知'}万元

请按以下JSON格式返回，不要包含其他内容：
{{
    "category": "software|solution|server|service|other",
    "status": "bidding|upcoming|closing_soon|result_published|ended",
    "relevance_score": 0.0-1.0,
    "tags": ["标签1", "标签2"],
    "key_requirements": ["要求1", "要求2"],
    "confidence": 0.0-1.0
}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的招投标信息分析师，擅长分析IT领域的招标项目。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 应用AI分析结果
            item.category = result.get('category', item.category)
            item.status = result.get('status', item.status)
            item.ai_relevance_score = result.get('relevance_score', 0)
            item.ai_tags = result.get('tags', [])
            item.requirements = result.get('key_requirements', [])
            item.ai_confidence = result.get('confidence', 0)
            
        except Exception as e:
            print(f"⚠️ AI分析失败，回退到规则引擎: {e}")
            # 回退到规则引擎
            item = super().analyze(item)
        
        return item


def get_ai_engine(settings) -> AIEngineBase:
    """根据配置获取合适的AI引擎实例"""
    if settings.has_ai:
        return OpenAIEngine(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)
    else:
        return AIEngineBase()

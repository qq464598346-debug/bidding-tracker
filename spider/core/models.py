"""
数据模型定义
统一的数据结构，用于所有爬虫模块和API接口
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class BiddingStatus(str, Enum):
    """招标状态枚举"""
    BIDDING = "bidding"           # 招标中
    UPCOMING = "upcoming"        # 即将开始（预告）
    CLOSING_SOON = "closing_soon"  # 即将截止
    RESULT_PUBLISHED = "result_published"  # 已公示结果
    ENDED = "ended"              # 已结束/流标

    @property
    def label(self) -> str:
        labels = {
            "bidding": "招标中",
            "upcoming": "即将开始",
            "closing_soon": "即将截止",
            "result_published": "已公示",
            "ended": "已结束",
        }
        return labels.get(self.value, self.value)

    @classmethod
    def from_text(cls, text: str) -> 'BiddingStatus':
        """从文本推断状态"""
        text = text.lower()
        if any(k in text for k in ['中标', '成交', '结果公示', '候选人', '中标人']):
            return cls.RESULT_PUBLISHED
        if any(k in text for k in ['变更', '澄清', '补充']):
            return cls.BIDDING
        if any(k in text for k in ['预告', '计划', '拟建', '意向']):
            return cls.UPCOMING
        if any(k in text for k in ['终止', '废标', '流标', '取消']):
            return cls.ENDED
        # 默认为招标中
        return cls.BIDDING


class Operator(str, Enum):
    """运营商枚举"""
    CHINA_MOBILE = "chinamobile"
    CHINA_UNICOM = "chinaunicom"
    CHINA_TELECOM = "chinatelecom"

    @property
    def name_cn(self) -> str:
        names = {
            "chinamobile": "中国移动",
            "chinaunicom": "中国联通",
            "chinatelecom": "中国电信",
        }
        return names.get(self.value, self.value)

    @property
    def color(self) -> str:
        colors = {
            "chinamobile": "#0091DA",   # 移动蓝
            "chinaunicom": "#E60012",   # 联通红
            "chinatelecom": "#FF6B00",  # 电信橙
        }
        return colors.get(self.value, "#666")


class Category(str, Enum):
    """项目类别枚举"""
    SOFTWARE = "software"             # 基础软件
    SOLUTION = "solution"             # 行业解决方案
    SERVER = "server"                 # 服务器硬件
    SERVICE = "service"               # 服务类
    OTHER = "other"                   # 其他

    @property
    def label(self) -> str:
        labels = {
            "software": "基础软件",
            "solution": "行业解决方案",
            "server": "服务器",
            "service": "服务",
            "other": "其他",
        }
        return labels.get(self.value, self.value)


@dataclass
class BiddingItem:
    """
    统一的招标数据模型
    所有爬虫输出都必须转换为这个格式
    """
    # ====== 基础信息 ======
    title: str                          # 项目名称
    source: str                         # 数据来源 (ggzy/chinamobile/chinaunicom/chinatelecom)
    operator: Optional[str] = None      # 运营商 (Operator enum value or None for national platform)
    
    # ====== 编号与链接 ======
    project_code: Optional[str] = None  # 项目编号
    url: Optional[str] = None           # 详情页URL
    
    # ====== 时间信息 ======
    publish_time: Optional[str] = None  # 发布时间 (ISO格式或原始字符串)
    deadline: Optional[str] = None      # 投标截止时间
    open_time: Optional[str] = None     # 开标时间
    
    # ====== 金额与采购方 ======
    budget: Optional[float] = None      # 预算金额（万元）
    purchaser: Optional[str] = None     # 采购单位/招标代理机构
    
    # ====== 分类与状态 ======
    category: str = Category.OTHER.value
    status: str = BiddingStatus.BIDDING.value
    region: Optional[str] = None        # 省份/地区
    
    # ====== 详细内容 ======
    summary: Optional[str] = None       # 摘要/主要内容
    requirements: Optional[List[str]] = field(default_factory=list)  # 关键要求
    
    # ====== 元数据 ======
    raw_data: Optional[Dict[str, Any]] = field(default=None, repr=False)  # 原始数据备份
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # AI增强字段
    ai_tags: List[str] = field(default_factory=list)     # AI标签
    ai_confidence: float = 0.0                           # AI分类置信度
    ai_relevance_score: float = 0.0                      # 与目标领域的相关度评分(0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        d = asdict(self)
        # 处理requirements默认值
        d['requirements'] = self.requirements or []
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BiddingItem':
        """从字典创建实例"""
        return cls(**data)

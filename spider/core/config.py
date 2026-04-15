"""
全局配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    """全局配置 - 支持环境变量覆盖默认值"""

    # ====== 项目路径 ======
    ROOT_DIR = Path(__file__).parent.parent
    DATA_DIR = ROOT_DIR / "data"
    LOG_DIR = ROOT_DIR / "logs"

    # ====== AI配置 ======
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def has_ai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    # ====== 爬虫配置 ======
    CRAWL_DELAY_MIN: float = float(os.getenv("CRAWL_DELAY_MIN", "1"))
    CRAWL_DELAY_MAX: float = float(os.getenv("CRAWL_DELAY_MAX", "3"))
    MAX_ITEMS_PER_SOURCE: int = int(os.getenv("MAX_ITEMS_PER_SOURCE", "50"))
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

    # ====== 数据库 ======
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "bidding.db"))

    # ====== API服务 ======
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = 0
    API_DEBUG: bool = os.getenv("API_DEBUG", "true").lower() == "true"

    # ====== 定时任务 ======
    CRON_INTERVAL_MINUTES: int = int(os.getenv("CRON_INTERVAL_MINUTES", "60"))

    def __post_init__(self):
        """初始化后创建必要目录"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


# 全局单例
settings = Settings()

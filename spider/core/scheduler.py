"""
定时任务调度器
负责定期执行数据采集任务
"""
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger


class CrawlScheduler:
    """
    爬虫定时调度器
    
    功能:
    - 定时触发全量采集
    - 支持动态调整采集间隔
    - 记录每次执行状态
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.scheduler = None
        self._running = False
        
    def start(self):
        """启动定时调度"""
        if self.settings.CRON_INTERVAL_MINUTES <= 0:
            logger.info("⏰ 定时采集未启用 (CRON_INTERVAL_MINUTES=0)")
            return
            
        if self._running:
            logger.warning("⚠️ 调度器已在运行中")
            return
            
        self.scheduler = BackgroundScheduler()
        
        # 添加定时采集任务
        self.scheduler.add_job(
            self._run_scheduled_crawl,
            'interval',
            minutes=self.settings.CRON_INTERVAL_MINUTES,
            id='crawl_job',
            name='招投标数据定时采集',
            next_run_time=datetime.now()  # 首次启动后立即执行一次
        )
        
        self.scheduler.start()
        self._running = True
        
        logger.info(f"✅ 定时调度已启动，每 {self.settings.CRON_INTERVAL_MINUTES} 分钟执行一次采集")
    
    def stop(self):
        """停止调度"""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("⏹️ 定时调度已停止")
    
    def _run_scheduled_crawl(self):
        """执行定时采集（在后台线程中运行）"""
        import asyncio
        
        def run_in_thread():
            try:
                from crawlers.coordinator import CrawlCoordinator
                
                logger.info("🔄 [定时任务] 开始执行采集...")
                start_time = time.time()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                coordinator = CrawlCoordinator(self.settings)
                results = loop.run_until_complete(coordinator.crawl_all())
                
                duration = time.time() - start_time
                logger.info(
                    f"✅ [定时任务] 采集完成! "
                    f"共{results['total']}条, 耗时{duration:.1f}秒"
                )
                
                # 记录到数据库
                from core.db import Database
                db = Database(self.settings.DATABASE_PATH)
                for source, count in results.items():
                    if source != 'total':
                        db.log_crawl(
                            source=source,
                            status='success',
                            count=count,
                            started_at=datetime.now().isoformat(),
                            finished_at=datetime.now().isoformat(),
                            duration=duration
                        )
                db.close()
                
                loop.close()
                
            except Exception as e:
                logger.error(f"❌ [定时任务] 采集失败: {e}")
                
                # 记录错误日志
                try:
                    from core.db import Database
                    db = Database(self.settings.DATABASE_PATH)
                    db.log_crawl(
                        source='all',
                        status='error',
                        error=str(e),
                        started_at=datetime.now().isoformat()
                    )
                    db.close()
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

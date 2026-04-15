"""
爬虫协调器 v4.0 - 统一调度乙方宝+百度寻标宝数据源
负责:
1. 并发执行多个爬虫（3个运营商 x 2个数据源）
2. 汇总去重
3. 数据持久化
"""
import asyncio
import time
from typing import List, Dict, Any

from core.models import BiddingItem
from core.db import Database


class CrawlCoordinator:
    """
    爬虫协调器 v4.0
    
    数据源配置:
    - 乙方宝 (yifangbao): 3个运营商页面（移动/联通/电信各一个）
    - 百度寻标宝 (xunbiaobao): 按关键词搜索三大运营商
    
    共6个采集任务并发执行
    """

    # 爬虫任务配置: (名称, 爬虫类, 参数)
    CRAWLER_TASKS = [
        # === 乙方宝数据源 ===
        ('yfb_mobile', 'crawlers.yifangbao_crawler.YifangbaoCrawler', {'operator_key': 'chinamobile'}),
        ('yfb_unicom', 'crawlers.yifangbao_crawler.YifangbaoCrawler', {'operator_key': 'chinaunicom'}),
        ('yfb_telecom', 'crawlers.yifangbao_crawler.YifangbaoCrawler', {'operator_key': 'chinatelecom'}),
        
        # === 百度寻标宝数据源 ===
        ('xbb_mobile', 'crawlers.xunbiaobao_crawler.XunbiaobaoCrawler', {'operator_key': 'chinamobile'}),
        ('xbb_unicom', 'crawlers.xunbiaobao_crawler.XunbiaobaoCrawler', {'operator_key': 'chinaunicom'}),
        ('xbb_telecom', 'crawlers.xunbiaobao_crawler.XunbiaobaoCrawler', {'operator_key': 'chinatelecom'}),
    ]

    def __init__(self, settings):
        self.settings = settings
        self.db = Database(settings.DATABASE_PATH)

    def _create_crawler(self, crawler_class_path: str, kwargs: dict):
        """动态导入并创建爬虫实例"""
        module_path, class_name = crawler_class_path.rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        crawler_class = getattr(module, class_name)
        return crawler_class(self.settings, **kwargs)

    async def crawl_all(self, sources: list = None, keywords: list = None) -> Dict[str, Any]:
        """
        执行全量或指定源的数据采集
        
        Args:
            sources: 要采集的任务列表，None表示全部
            keywords: 搜索关键词
            
        Returns:
            {"total": N, "yfb_mobile": n1, "xbb_mobile": n2, ...}
        """
        target_tasks = []
        
        if sources:
            for task_id in sources:
                for t in self.CRAWLER_TASKS:
                    if t[0] == task_id:
                        target_tasks.append(t)
                        break
        else:
            target_tasks = self.CRAWLER_TASKS
        
        print(f"\n{'='*60}")
        print(f"  🚀 开始招投标数据采集 — {len(target_tasks)} 个数据源")
        print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # 并发执行所有爬虫任务
        tasks = []
        for task_id, crawler_class_path, crawler_kwargs in target_tasks:
            try:
                crawler = self._create_crawler(crawler_class_path, crawler_kwargs)
                tasks.append(self._crawl_single(task_id, crawler, keywords))
            except Exception as e:
                print(f"❌ [{task_id}] 创建爬虫失败: {e}")
                self.db.log_crawl(
                    source=task_id, status='error',
                    error=str(e),
                    started_at=__import__('datetime').datetime.now().isoformat()
                )
                continue
        
        # 并发等待结果
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理和汇总结果
        all_items = []
        source_counts = {}
        
        for i, result in enumerate(results_list):
            task_id = target_tasks[i][0]
            
            if isinstance(result, Exception):
                print(f"❌ [{task_id}] 采集异常: {result}")
                source_counts[task_id] = 0
                continue
            
            if not isinstance(result, dict):
                source_counts[task_id] = 0
                continue
                
            items = result.get('items', [])
            status = result.get('status', 'unknown')
            
            if items and status == 'success':
                print(f"✅ [{task_id}] 获取 {len(items)} 条数据")
                
                # 存储到数据库
                stats = self.db.batch_insert(items)
                all_items.extend(items)
                source_counts[task_id] = len(items)
                
                print(f"   └─ 存储: 新增{stats['new']}条, 更新{stats['updated']}条")
                
                self.db.log_crawl(
                    source=task_id,
                    status='success',
                    count=len(items),
                    started_at=result.get('started_at'),
                    finished_at=__import__('datetime').datetime.now().isoformat(),
                    duration=result.get('duration', 0)
                )
            else:
                err_msg = result.get('error', '未知错误')
                print(f"⚠️ [{task_id}] 未获取到数据: {err_msg}")
                source_counts[task_id] = 0
                
                self.db.log_crawl(
                    source=task_id,
                    status='error',
                    error=err_msg,
                    started_at=result.get('started_at'),
                )

        total_duration = time.time() - start_time
        unique_count = len(all_items)
        source_counts['total'] = unique_count
        
        # 输出汇总报告
        print(f"\n{'='*60}")
        print(f"  🎉 全部采集完成!")
        print(f"{'─'*60}")
        print(f"  📊 总计有效数据: {unique_count} 条")
        print(f"  ⏱️  总耗时: {total_duration:.1f}秒")
        print(f"  📈 各数据源:")
        for k, v in source_counts.items():
            if k != 'total':
                icon = {'yfb':'📋','xbb':'🔍'}.get(k.split('_')[0], '📡')
                op_name = {'mobile':'移动','unicom':'联通','telecom':'电信'}.get(k.split('_')[1],'')
                print(f"     {icon} {k}: {v} 条 ({op_name})")
        print(f"{'='*60}\n")
        
        self.db.close()
        return source_counts

    async def _crawl_single(self, task_id: str, crawler, keywords: list) -> dict:
        """执行单个采集任务"""
        return await crawler.run(keywords=keywords)

    async def crawl_incremental(self) -> Dict[str, Any]:
        """增量采集（仅获取最新数据）"""
        return await self.crawl_all()

    def get_latest_data(self, limit: int = 50, **filters) -> List[BiddingItem]:
        """从数据库获取最新数据（同步接口，供API调用）"""
        db = Database(self.settings.DATABASE_PATH)
        result = db.query(limit=limit, **filters)
        db.close()
        
        items = []
        for item_data in result.get('items', []):
            items.append(BiddingItem.from_dict(item_data))
        return items

    def get_stats_sync(self) -> Dict[str, Any]:
        """获取统计数据（同步接口）"""
        db = Database(self.settings.DATABASE_PATH)
        stats = db.get_stats()
        db.close()
        return stats


# 导入datetime用于日志
from datetime import datetime

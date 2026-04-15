# ============================================
# 运营商招投标智能监控系统 v4.0
# 数据源: 乙方宝 + 百度寻标宝
# ============================================
# 用法:
#   pip install -r requirements.txt
#   python main.py              # 启动爬虫+API服务（默认端口8765）
#   python main.py --crawl     # 仅运行一次采集
#   python main.py --api       # 仅启动API服务
#   python main.py --port 8080 # 指定API端口
# ============================================

import sys
import os
import io

# 修复Windows控制台编码问题（支持emoji/中文输出）
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

import asyncio
import argparse
from pathlib import Path

# 确保项目根目录在Python路径中
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import Settings
from core.scheduler import CrawlScheduler
from api.server import APIServer


async def run_crawl_once(settings: Settings):
    """执行一次完整的采集任务"""
    from crawlers.coordinator import CrawlCoordinator
    
    print("\n" + "=" * 60)
    print("  🚀 开始执行招投标数据采集...")
    print("  📡 数据源: 乙方宝 + 百度寻标宝 (6个采集任务)")
    print("=" * 60)
    
    coordinator = CrawlCoordinator(settings)
    results = await coordinator.crawl_all()
    
    total = sum(v for k, v in results.items() if k != 'total')
    print(f"\n✅ 采集完成! 共获取 {total} 条数据")
    return results


def start_api_server(settings: Settings):
    """启动API服务器"""
    server = APIServer(settings)
    server.run()


def main():
    parser = argparse.ArgumentParser(description="运营商招投标智能监控系统 v4.0")
    parser.add_argument("--crawl", action="store_true", help="仅运行一次数据采集")
    parser.add_argument("--api", action="store_true", help="仅启动API服务")
    parser.add_argument("--port", type=int, default=8765, help="API服务端口 (默认: 8765)")
    args = parser.parse_args()
    
    settings = Settings()
    settings.API_PORT = args.port
    
    if args.crawl:
        # 仅采集模式
        asyncio.run(run_crawl_once(settings))
    elif args.api:
        # 仅API模式
        start_api_server(settings)
    else:
        # 默认模式: 先初始化数据，然后启动定时任务+API
        print("📡 运营商招投标智能监控系统 v4.0")
        print("   数据源: 乙方宝(yfbzb.com) + 百度寻标宝(baidu.com)")
        print("=" * 60)
        
        # 确保数据库已初始化并填充种子数据
        from core.db import Database
        db = Database(settings.DATABASE_PATH)
        db.init_tables()
        db.close()
        
        # 首次启动时先做一次全量采集
        print("\n🚀 开始首次全量采集（乙方宝 + 寻标宝，6个数据源并发）...")
        try:
            results = asyncio.run(run_crawl_once(settings))
            total = sum(v for k, v in results.items() if k != 'total')
            if total > 0:
                print(f"\n🎉 采集成功！共获取 {total} 条最新招标信息")
            else:
                print("\n⚠️ 未获取到新数据，将使用数据库已有数据展示")
                print("   💡 可通过前端「🔄立即更新」按钮或 POST /api/crawl 手动触发采集")
        except Exception as e:
            print(f"\n⚠️ 首次采集遇到问题: {e}")
            print("   ✅ 已使用内置演示数据作为后备")
            print("   💡 可通过前端「🔄立即更新」按钮手动触发采集")
        
        # 启动调度器（后台定时采集）
        scheduler = CrawlScheduler(settings)
        scheduler.start()
        
        # 启动API服务（主线程阻塞）
        print("\n" + "=" * 56)
        print("  🌐 API服务就绪 — 前端可开始访问")
        print(f"     http://localhost:{settings.API_PORT}")
        print("=" * 56 + "\n")
        start_api_server(settings)


if __name__ == "__main__":
    main()
